# ai-backend-v2

Backend AI untuk belajar — dibangun di atas fondasi `ai-backend` dan mengikuti `goals.md`
(8 pilar kompetensi) + `roadmap.md` (kendaraan teknis). Tujuan utamanya **belajar**: kamu
harus paham arsitekturnya dan bisa membuatnya sendiri setelahnya.

## Stack

- **Python 3.14** + `uv` (package manager & venv)
- **FastAPI** (async web framework) + Uvicorn
- **PostgreSQL** + SQLAlchemy 2 (async) + Alembic (migration)
- **OpenAI-compatible LLM client** (httpx langsung, bukan SDK — supaya paham HTTP-nya)
- **transformers** (tokenizer DeepSeek-V4 untuk token counting)
- **Prometheus** (metrik), structured JSON logging, trace_id (ContextVar)

## Struktur project

```
app/
├── main.py                  # entry point FastAPI
├── api/                     # router, metrics, dependencies
├── core/                    # config, database, exceptions, logging,
│                            #   rate_limiter, retry, metrics, middleware
├── domain/                  # business rules murni (tanpa framework)
├── application/             # orkestrasi use case (context manager)
├── features/chat/           # fitur chat (router → usecase → service → repository)
├── llm/                     # LLMProtocol + OpenAI client + mock
├── provider/openai/         # retry policy provider
├── infrastructure/tokenizer # tokenizer DeepSeek-V4
└── middleware/              # trace middleware
```

Penjelasan arsitektur lengkap: [docs/architecture.md](docs/architecture.md)
Keputusan desain: [docs/decisions.md](docs/decisions.md)
Rencana & fase: [PLAN.md](PLAN.md)

## Setup

```bash
# install dependency (membuat .venv)
uv sync

# buat file .env dari template (isi sendiri, jangan di-commit)
# minimal: CHAT_API_KEY, CHAT_BASE_URL, CHAT_MODEL, DB_* (lihat app/core/config/)
```

> `.env` tidak dibaca isinya oleh siapapun — hanya dipakai runtime lewat pydantic-settings.

## Menjalankan

```bash
# migration database
uv run alembic upgrade head

# server dev (hot reload)
uv run python -m uvicorn app.main:app --reload

# test
uv run pytest -v

# lint & type check (ringan)
uv run ruff check .
uv run mypy .
```

## Logging — cara akses log

Kita belum integrasi ke Sentry / log aggregator — log ditulis sebagai **JSON ke
stdout** (setup: `app/core/logging/config.py`, formatter `JsonFormatter`), bukan
ke file. Tiap baris = satu event, otomatis membawa `trace_id` (korelasi ke
Jaeger, lihat `docs/learn/observability.md`).

Cara lihat:

- **Dev (host):** log muncul di terminal tempat uvicorn jalan
  (`uv run python -m uvicorn app.main:app --reload`). Filter event:
  ```bash
  # event token_estimation saja (contoh filter event)
  uv run python -m uvicorn app.main:app 2>&1 | grep '"event": "token_estimation"'
  ```
- **Docker (deploy):**
  ```bash
  # log app / worker
  docker compose -f docker-compose.prod.yml logs -f app
  docker compose -f docker-compose.prod.yml logs -f worker
  ```
- Karena stdout, log **tidak tersimpan permanen** — hilang saat proses/container
  berhenti. Kalau butuh riwayat & pencarian terpusat, pasang log aggregator
  (mis. Loki) atau Sentry (belum — lihat `PLAN.md`).

> Format tiap baris JSON, contoh: `{"timestamps": ..., "level": "INFO",
> "logger": "ai-backend", "event": "token_estimation", "trace_id": "...",
> "conversation_id": 1, "estimated_tokens": ..., "actual_tokens": ...}`

## Deploy (manual ke homelab / server docker)

Build image app + jalankan semua service via compose production.

### Prasyarat (di server)

- Docker + Docker Compose terinstall.
- Project sudah di-clone (kalau belum: `git clone ... && git pull` — pastikan
  `Dockerfile` sudah ada, tidak kosong).
- Port bebas: `8000, 5432, 6379, 16686, 4318, 4317, 9090, 3000`.

### Langkah 1 — Masuk ke project & pastikan terbaru

```bash
cd /path/ke/ai-backend-v2
git pull
```

### Langkah 2 — Buat `.env` produksi

```bash
cp .env-example .env
nano .env    # atau vim
```

Ubah nilai yang penting (perbedaan utama dari lokal: **nama service**, bukan
`localhost`):

```ini
# LLM — isi key & model asli
CHAT_API_KEY=sk-key-asli
CHAT_MODEL=gpt-5-nano
CHAT_BASE_URL=https://api.openai.com
CHAT_TEMP=1                   # gpt-5: hanya default (1) yang didukung
CHAT_TOKEN_CORRECTION=0       # gpt-5 tidak butuh koreksi 79 ala DeepSeek

# DB — NAMA SERVICE, bukan localhost
DB_HOST=postgres
DB_PORT=5432

# Auth — generate secret kuat
JWT_SECRET_KEY=$(openssl rand -hex 32)

# API key metrics — WAJIB sama dengan deploy/prometheus-prod.yml
API_KEY=ganti-dengan-key-kuat

# Redis — nama service
REDIS_URL=redis://redis:6379/0

# Embedding
EMBEDDING_API_KEY=sk-key-asli

# Tracing (opsional — false dulu)
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
```

### Langkah 3 — Build & start semua service

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Ini build image app dan start: app, worker, postgres, redis, jaeger,
prometheus, grafana. Cek status:

```bash
docker compose -f docker-compose.prod.yml ps
```

### Langkah 4 — Jalankan migrasi database

DB di server masih kosong, jadi buat tabel:

```bash
docker compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Langkah 5 — Verifikasi

```bash
curl http://localhost:8000/health
# → {"status": "ok"}

# smoke test: register → login → chat
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"supersecret123"}'
```

### Langkah 6 — Perintah operasional

```bash
# log app
docker compose -f docker-compose.prod.yml logs -f app

# log worker
docker compose -f docker-compose.prod.yml logs -f worker

# restart setelah ubah .env
docker compose -f docker-compose.prod.yml up -d

# stop semua
docker compose -f docker-compose.prod.yml down

# reset total (HAPUS volume DB!)
docker compose -f docker-compose.prod.yml down -v
```

### Reset data Prometheus (kosongkan history metrik)

Berguna kalau dashboard penuh time series lama yang tidak relevan (mis. sisa
noise bot sebelum normalisasi path). Hanya menghapus **volume Prometheus**,
tidak menyentuh DB aplikasi:

```bash
# stop & hapus container prometheus
docker compose -f docker-compose.prod.yml stop prometheus
docker compose -f docker-compose.prod.yml rm -f prometheus

# hapus volume data prometheus (riwayat metrik hilang)
docker volume rm ai-backend-v2-prod_prometheus-data

# start ulang — metrik mulai kosong, terisi lagi tiap scrape
docker compose -f docker-compose.prod.yml up -d prometheus
```

> Nama volume mengikuti prefix project compose (`ai-backend-v2-prod_`).
> Cek dulu dengan `docker volume ls | grep prometheus` kalau ragu.
> Alternatif tanpa hapus: biarkan — Prometheus otomatis membersihkan data
> lebih lama dari `retention` (default 15 hari).

### Troubleshooting: `password authentication failed for user "postgres"`

Error ini muncul saat app/alembic tidak bisa login ke postgres, padahal
`.env` sudah benar (`DB_PASSWORD` sesuai). Penyebabnya hampir selalu:

**`POSTGRES_PASSWORD` di compose HANYA dipakai saat volume postgres pertama
kali dibuat.** Setelah volume ada, password yang tersimpan di dalam volume
itulah yang berlaku — mengubah env compose/`.env` tidak mengubah password
yang tersimpan.

Jadi kalau volume pernah dibuat dari state dengan password berbeda (mis. ada
container lain yang sempat init volume, atau volume di-reset dengan env beda),
app akan ditolak walau `.env` sudah `postgres`.

**Cek dulu** — apakah password yang dipakai app == password tersimpan:

```bash
# password yang dipakai app
docker exec ai-backend-v2-prod-app-1 printenv DB_PASSWORD

# password tersimpan di volume (lewat socket trust di dalam container)
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d ai_backend_v2 -c 'select 1'
```

**Fix cepat (tanpa hapus data)** — set ulang password user `postgres` di
container berjalan, supaya sama dengan `.env`:

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d ai_backend_v2 \
  -c "ALTER USER postgres PASSWORD 'postgres';"
```

lalu jalankan migrasi lagi:

```bash
docker compose -f docker-compose.prod.yml exec -T app alembic upgrade head
```

**Fix permanen** — pakai password kuat & satu sumber, jangan `postgres`:

1. Generate password: `openssl rand -hex 24`
2. Isi `DB_PASSWORD=<password>` di `.env` server, dan ubah
   `docker-compose.prod.yml` supaya `POSTGRES_PASSWORD` membaca dari `.env`:
   ```yaml
   environment:
     POSTGRES_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD di .env}
   ```
3. Reset volume postgres sekali (data hilang — pastikan DB kosong / siap
   dibuang):
   ```bash
   docker compose -f docker-compose.prod.yml down
   docker volume rm ai-backend-v2-prod_pgdata
   docker compose -f docker-compose.prod.yml up -d
   docker compose -f docker-compose.prod.yml exec -T app alembic upgrade head
   ```

> Tes `psql` lewat socket di dalam container **bukan** bukti password benar —
> pg_hba memakai `trust` untuk koneksi local (socket). App konek lewat TCP
> dari container lain yang kena aturan `scram-sha-256`, jadi yang menentukan
> adalah password tersimpan di volume.

### URL setelah deploy

| Service | URL |
|---------|-----|
| App API | `http://<ip-homelab>:8000` |
| API docs | `http://<ip-homelab>:8000/docs` |
| Jaeger | `http://<ip-homelab>:16686` |
| Prometheus | `http://<ip-homelab>:9090` |
| Grafana | `http://<ip-homelab>:3000` (admin/admin) |

### Debug kalau gagal — urutan cek

1. `docker compose ... ps` — semua jalan?
2. `docker compose ... logs app` — error app (biasanya `.env` kurang atau DB).
3. `docker compose ... logs postgres` — postgres sehat?
4. **Paling umum**: `.env` masih `localhost` bukan nama service → app tidak bisa
   reach DB/Redis. Fix `.env`, lalu `docker compose ... up -d` (recreate app).

> **Catatan**: `deploy/prometheus-prod.yml` punya `X-API-Key` hardcoded
> (`masak-nasi-goreng`) — pastikan `API_KEY` di `.env` sama, atau Prometheus
> dapat 401 di `/metrics`.
> Worker jalan sebagai service terpisah (`python -m app.jobs.worker`) — image sama.

## Endpoint utama

| Method | Path | Fungsi |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/metrics` | Metrik Prometheus |
| POST | `/chat/conversations` | Kirim pesan (buat/isi conversation) |
| GET | `/chat/conversations/{id}` | Ambil conversation |
| GET | `/get_db` | Cek koneksi DB |

## Status roadmap

- Phase 0–3: ✅ selesai (fondasi, FastAPI, DB, LLM integration)
- Phase 4: 🟡 ~95% (Fase A: integrasi ModelResolver → ContextManager → ChatUseCase done,
  sisa: review & test integration dengan DB asli)
- Phase 5+: lihat [PLAN.md](PLAN.md) Fase B–L

## Catatan belajar

- Catatan konsep (RAG, embedding, HNSW, chunk, dll): `Notes.md` di ai-backend (sumber asli).
- Latihan konsep per fase: folder `practice/`.
