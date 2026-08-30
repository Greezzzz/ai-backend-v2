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

## Deploy (manual ke homelab / server docker)

Build image app + jalankan semua service via compose production:

```bash
# 1. build & verifikasi image (lokal dulu)
docker build -t ai-backend-v2:test .
docker run --rm ai-backend-v2:test python -c "import app.main"  # perlu env vars

# 2. di server (mis. /opt/ai-backend):
#    - salin docker-compose.prod.yml + deploy/ (config jaeger/prometheus/grafana)
#    - buat .env (salin .env.example, isi nilai PRODUKSI — lihat catatan di bawah)
scp docker-compose.prod.yml deploy/ user@server:/opt/ai-backend/

# 3. di server
cd /opt/ai-backend
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec app alembic upgrade head

# 4. cek
curl http://localhost:8000/health
```

> **`.env` produksi**: isi `DB_HOST=postgres`, `DB_PORT=5432`,
> `REDIS_URL=redis://redis:6379/0` (nama service compose, bukan localhost).
> `API_KEY` di `deploy/prometheus-prod.yml` harus sama dengan `.env`.
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
