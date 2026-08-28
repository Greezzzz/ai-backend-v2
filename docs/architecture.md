# Arsitektur — ai-backend-v2

Dokumen ini menjelaskan arsitektur project. Diperbarui di tiap fase.

## 1. Alur request secara keseluruhan

```
HTTP Request
    ↓
FastAPI app (app/main.py)
    ↓
TraceMiddleware  → buat/inject trace_id (ContextVar), log start, ukur latency
    ↓
Router (app/api/router.py) → /health, /metrics, /chat/*
    ↓
Dependency Injection (Depends) — wiring otomatis dari atas ke bawah
    ↓
UseCase (features/chat/usecase.py) — orkestrasi alur bisnis
    ├── Service (ChatService) → LLMProtocol → OpenAIClient
    │       ├── RateLimiter    (token bucket, asyncio.Lock)
    │       ├── RetryExecutor  (exponential backoff + jitter)
    │       └── httpx.AsyncClient (dari lifespan, disimpan di app.state)
    ├── ModelResolver → ModelProfile + TokenCounter
    │       └── ContextManager (potong history agar muat token budget)
    └── Repository (Conversation/Message) → AsyncSession → PostgreSQL
    ↓
JSON Response (atau error → app_exception_handler → ErrorResponse)
```

## 2. Lapisan (layers)

| Layer | Folder | Tanggung jawab |
|---|---|---|
| **API** | `app/api` | Routing, kontrak HTTP |
| **Core** | `app/core` | Fondasi lintas fitur: config, db, exception, logging, rate limit, retry, metrics |
| **Domain** | `app/domain` | Business rules murni, tanpa framework. "Hati" aplikasi |
| **Application** | `app/application` | Orkestrasi use case + logika aplikasi |
| **Features** | `app/features` | Fitur per domain bisnis (chat) |
| **Infrastructure** | `app/infrastructure` | Implementasi teknis (tokenizer) |
| **LLM / Provider** | `app/llm`, `app/provider` | Abstraksi LLM + implementasi provider |

**Aturan arah dependensi**: layer atas boleh tahu layer bawah, tapi layer bawah tidak boleh
tahu layer atas. `domain` tidak pernah import `fastapi`/`sqlalchemy` → gampang di-test dan
diganti implementasinya.

## 3. Komponen kunci

### 3.1 LLM abstraction (Protocol)

```
LLMProtocol (app/llm/protocol.py)
    ↑
OpenAIClient (app/llm/openai_client.py)
MockClient   (app/llm/mock_client.py)
```

- Service hanya tahu `LLMProtocol` → tidak peduli provider siapa.
- `OpenAIClient.chat()` di-wrap 3 lapis proteksi: rate limiter (token bucket),
  retry (backoff + jitter), dan mapping error (429→RateLimit, 401→Auth, timeout→504,
  lainnya→ProviderError).

### 3.2 Model resolution & context (model-aware)

```
ModelRegistry (domain/model_profile.py)  → model → ModelProfile
TokenCounterRegistry (domain/token_counter.py) → model → TokenCounter
                    ↓
           ModelResolver (domain/model_resolver.py)
                    ↓
        ResolvedModel { profile, token_counter }
```

- `ModelProfile` membawa `context_window` & `max_output_tokens` — **sumber kebenaran
  konfigurasi model**, bukan hardcode.
- `ChatUseCase.chat()`: resolve model → buat `ContextBudget` dari profile → `ContextManager`
  memilih pesan yang muat di budget (pesan lama dibuang duluan).
- Budget: `context_window - reserved_output - safety_margin` = ruang input.

### 3.3 Database

- `app/core/database/`: `engine.py` (async engine, `pool_pre_ping`), `session.py`
  (async_sessionmaker, `expire_on_commit=False`), `base.py` (DeclarativeBase).
- `app/api/dependencies/database.py`: `get_db` — yield session per request, auto close.
- Model `Conversation` & `Message` di `features/chat/model.py`, migration di `alembic/`.

### 3.4 Observability

- **Trace**: `TraceMiddleware` → `trace_id` (ContextVar). Bisa di-inject via header
  `X-Trace-Id`, di-echo balik di response header `X-Trace-Id`. OpenTelemetry
  (OTel) terpasang: span server per request + LLM span + OTLP ke Jaeger v2.
- **Logging**: `JsonFormatter` → semua log JSON, otomatis bawa `trace_id`.
- **Metrics** (Prometheus): HTTP (total, duration), LLM (total, duration, input/output
  tokens), retry (attempts, exhausted), rate limiter (tokens available).
  Endpoint: `GET /metrics` (dilindungi `X-API-Key`).
- **Stack (docker-compose)**: Prometheus scrape `/metrics` (target
  `host.docker.internal:8000`, header `X-API-Key` di `deploy/prometheus.yml`),
  UI `localhost:9090`. Grafana (UI `localhost:3000`, admin/admin dev) membaca
  dari Prometheus, data source auto-provision di `deploy/grafana-provisioning/`.
  Dashboard auto-provision (JSON): API Overview, LLM & Tokens, Health &
  Reliability di `deploy/grafana-provisioning/dashboards/`.
- **Metrik LLM detail**: `llm_error_total{error_type,model,provider}`
  (timeout/rate_limit/auth/provider) + `chat_messages_sent_total{role}`.

### 3.5 Exception & error contract

```
AppException (base) → code, message, status_code, details
ErrorCode (enum)     → LLM_TIMEOUT, LLM_RATE_LIMIT, ..., CONVERSATION_NOT_FOUND
app_exception_handler → JSON { code, message, details }
```

Semua error aplikasi keluar dengan kontrak yang sama, konsisten untuk client (mobile/web).

## 4. Alur dependency injection (chat)

```
get_db → AsyncSession
get_token_counter (singleton) → TokenCounterProtocol
get_model_registry → ModelRegistry
get_token_counter_registry → TokenCounterRegistry
get_model_resolver → ModelResolver
get_openai_client → LLMProtocol (OpenAIClient: http + settings + retry + rate limiter)
get_chat_service → ChatService
get_chat_usecase → ChatUseCase(service, session, context_manager, resolver, budget)
```

Semua wiring eksplisit di `features/chat/dependencies.py` — sengaja tidak pakai framework DI
biar gampang dibaca & dipelajari.

## 5. Perubahan penting di v2 (vs ai-backend)

- `MockClient` diperbaiki (bug `request.message` → `request.messages[-1].content`).
- `ModelRegistry.get` error message pakai f-string (bug).
- `DeepSeekV4TokenCounter` tidak lagi `print()` debug tiap request.
- `OpenAIClient` menangkap semua error (bukan cuma httpx) → label metrik `error` benar.
- `BusinessValidationException` default value benar (`status_code=400`).
- `alembic/env.py` pakai mode offline/online yang benar.
- Migration no-op `aae5ca8edd94` diisi perbaikan schema yang konsisten.
- Rename `rate_limiter/dependecies.py` → `dependencies.py`.
- Chat: `ModelResolver` terintegrasi → budget model-aware; `model` field di request;
  conversation not found → `BusinessException` 404 (bukan ValueError).
- Tambah `/health`, API test, dev deps (ruff/mypy) terpisah.

## 6. Auth & Security (Fase B)

### 6.1 Skema proteksi endpoint

| Endpoint | Proteksi |
|---|---|
| `GET /health` | **Publik** (tanpa auth) |
| `GET /metrics` | **API key** statis (header `X-API-Key`) |
| `POST /api/auth/register`, `/api/auth/login` | **Publik** (tanpa JWT) |
| `/api/chat/*`, `/api/auth/me` | **JWT** (Bearer token) |

### 6.2 Alur auth

```
register → hash password (Argon2 via pwdlib) → simpan User
login    → verifikasi password → buat JWT (sub=user id, exp) → return token
request  → Authorization: Bearer <token> → get_current_user → decode & load user
```

- **Password**: `pwdlib[argon2]` (`PasswordHash.recommended()`) — standar modern FastAPI.
- **JWT**: `pyjwt`, HS256, secret dari settings (`JWT_SECRET_KEY`), expire menit.
- **Dependency**: `get_current_user` (JWT) di `api/dependencies/auth.py`; `require_api_key`
  (untuk `/metrics`).
- **Scope**: auth router (register/login) publik; chat router butuh JWT (dipasang di level
  router chat).

### 6.3 Rate limit (HTTP layer, in-memory)

- `RateLimitMiddleware` — semua request, kecuali `/metrics` (sudah dilindungi API key).
- Identity: client IP (`X-Forwarded-For` jika ada, fallback `request.client.host`).
- Algorithm: **sliding window** sederhana (`InMemoryRateLimitStore`) — limit request per
  menit dari settings (`HTTP_RATE_LIMIT_REQUESTS_PER_MINUTE`, default 60).
- Response 429: `{code, message, details}` + header `Retry-After`.
- Catatan: in-memory → state hilang saat restart; **migrasi ke Redis di Fase D** (distributed).

### 6.4 Error contract auth

| Situasi | HTTP | Code |
|---|---|---|
| Login gagal (username/password salah) | 401 | `INVALID_CREDENTIALS` |
| Token JWT tidak valid / expired / user tidak ada | 401 | `AUTHENTICATION_ERROR` |
| API key salah / tidak ada | 401 | `AUTHENTICATION_ERROR` |
| Register username/email sudah ada | 409 | `USER_ALREADY_EXISTS` |
| Rate limit HTTP tercapai | 429 | `RATE_LIMIT_EXCEEDED` |

### 6.5 File utama Fase B

- `app/core/security/password.py` — pwdlib (Argon2)
- `app/core/security/jwt.py` — create/decode token
- `app/core/config/auth.py` + `app/core/config/http_rate_limit.py` — settings
- `app/features/auth/` — model, repository, service, schemas, router, dependencies
- `app/api/dependencies/auth.py` — `get_current_user`, `require_api_key`
- `app/core/rate_limiter/http_store.py` + `app/middleware/rate_limit.py` — rate limit
- Migration `a1b2c3d4e5f6` — tabel `users`

## 7. Streaming (Fase C)

### 7.1 Alur

```
POST /api/chat/stream (JWT)
  → ChatUseCase.stream_chat
  → siapkan conversation + context (sama seperti chat biasa)
  → ChatService.stream_ask → LLMProtocol.stream_chat (async generator)
  → OpenAIClient: rate limit acquire → httpx stream → parse delta → yield
  → FastAPI StreamingResponse (SSE)
  → client terima `data: {"delta": "..."}\n\n` ... `data: [DONE]\n\n`
  → setelah stream selesai: simpan user + assistant (teks penuh) ke DB
```

### 7.2 Format SSE (OpenAI-style)

```
data: {"delta": "Mock "}

data: {"delta": "halo "}

...

data: [DONE]
```

Error di tengah stream: `data: {"error": "..."}` lalu stream ditutup (bukan diam-diam putus).

### 7.3 Keputusan desain streaming

- **Endpoint terpisah** `POST /api/chat/stream` (bukan flag di chat biasa) — response type beda.
- **Persist setelah stream selesai** — teks penuh diakumulasi, lalu disimpan; session DB tetap
  hidup selama stream (dependency `get_db` ditutup setelah response selesai).
- **Retry hanya pre-stream** — provider tidak mendukung resume mid-stream; begitu token
  mengalir, stream dianggap "take it or leave it" (error event kalau putus).
- **Rate limit di-acquire sekali** sebelum stream mulai.
- **Cancellation** — saat client disconnect, async generator di-close otomatis oleh
  Starlette (resource HTTP client ikut dilepas).

### 7.4 File utama Fase C

- `app/llm/protocol.py` — `stream_chat` di LLMProtocol
- `app/llm/openai_client.py` — `stream_chat` (httpx `aiter_lines`, parse delta)
- `app/features/chat/service.py` — `stream_ask`
- `app/features/chat/usecase.py` — `stream_chat` (persist + error event)
- `app/features/chat/router.py` — `POST /api/chat/stream`

### 7.5 Catatan: format SSE tidak seragam antar provider

Penting untuk Fase G (multi-provider). Streaming response **tidak sama** antar provider:

**Dua keluarga besar format:**
1. **OpenAI-compatible** (OpenAI, DeepSeek, Ollama, vLLM, LM Studio):
   `data: {chunk}\n\n`, chunk punya `choices[0].delta`, penutup `data: [DONE]`.
   - Tapi isi `delta` beda: OpenAI → `delta.content`; DeepSeek reasoning →
     `delta.reasoning_content` dulu lalu `delta.content`; ada juga `delta.tool_calls`,
     `delta.role` di chunk pertama.
2. **Anthropic** — format beda total: `event:` + `data:` bergantian
   (`content_block_delta` → `{"delta": {"text": "..."}}`), penutup `event: message_stop`.

**Varian lain yang harus ditangani parser:**
- Chunk `usage` di akhir (tanpa delta) → parser harus return None, bukan crash.
- Baris `keep-alive`/komentar (`: ping`) atau baris kosong → di-skip.
- Beberapa `data:` dalam satu baris (jarang) → perlu split hati-hati.
- Penutup bervariasi: `[DONE]`, `data: [DONE]`, atau event `done`.

**Kenapa abstraksi kita aman:** `LLMProtocol.stream_chat` sudah menyeragamkan semua jadi
`AsyncIterator[str]` (delta teks). Service & usecase tidak peduli format internal — perbedaan
format hidup di dalam masing-masing client (Fase G: buat parser per provider).

---

## 8. Background Jobs & Redis (Fase D)

### 8.1 Alur submit & eksekusi job

```
Client (JWT)
    ↓ POST /api/jobs {type, payload}
router.py → JobUseCase.create_job
    ├── validasi type (ada di JOB_TASKS?) → 400 kalau tidak
    ├── JobRepository.create → Job(status="queued") → commit DB   ← DB = sumber kebenaran
    └── enqueue_job → rq.Queue("ai-jobs") → Redis
                          ↓ (pop)
        RQ worker (app.jobs.worker) → job function dari JOB_TASKS
            └── buka session DB sendiri
                ├── mark_running → commit
                ├── proses (echo: payload → result)
                ├── mark_succeeded(result) | mark_failed(error) → commit
Client → GET /api/jobs/{id} → JobResponse (status terbaru dari DB)
```

### 8.2 Job lifecycle

| Status | Arti | Di-set oleh |
|---|---|---|
| `queued` | Dibuat; antri di Redis (atau belum diambil worker) | `create_job` (usecase) |
| `running` | Worker sedang memproses | task (mark_running) |
| `succeeded` | Selesai; `result` terisi | task (mark_succeeded) |
| `failed` | Gagal; `error` terisi | task (mark_failed) |

**DB adalah sumber kebenaran** — RQ hanya antrian (state Redis). Status lifecycle disimpan
di tabel `jobs` dan di-update worker. Job tetap bisa di-query walau Redis restart / worker mati.

### 8.3 Redis wiring (dua koneksi berbeda)

- **App (FastAPI)**: `redis.asyncio.from_url(settings.redis.url)` di `lifespan` →
  `app.state.redis`, ditutup via `aclose()` saat shutdown. Dipakai nanti untuk caching.
- **RQ (worker & enqueue)**: `redis.Redis` **sync** — API RQ sinkron. Dibuat dari
  `settings.redis.url` di `app/features/job/queue.py` & `app/jobs/worker.py`.
- `REDIS_URL` di settings (default `redis://localhost:6379/0`) & `.env-example`.
- `docker-compose.yml` menyediakan `redis:7-alpine` di port `6379`.

### 8.4 Error contract job

- Type tidak dikenal → `BusinessException` + `ErrorCode.VALIDATION_ERROR` → **400**.
- Job tidak ditemukan → `BusinessException` + `ErrorCode.JOB_NOT_FOUND` → **404**.
- Endpoint `/api/jobs*` dilindungi JWT (sama seperti chat).

### 8.5 Worker: proses terpisah & kendala Windows

- Worker adalah proses terpisah dari FastAPI (`python -m app.jobs.worker`) — RQ memanggil
  fungsi task **sync**, yang membuka engine/session DB-nya sendiri via `asyncio.run()`.
- **Kendala nyata**: RQ worker default (`Worker`) & `SpawnWorker` butuh `os.fork`/`os.wait4`
  yang **tidak ada di Windows**. Environment belajar ini = WSL + python Windows, jadi dipakai
  `SimpleWorker` (eksekusi job di proses yang sama, tanpa fork).
- **Konsekuensi**: satu job crash bisa menimpa worker (tidak ter-isolasi). Cukup untuk belajar;
  saat deploy Linux (Fase J) ganti ke `Worker` (fork) untuk isolasi proses.
- Retry pada job level (create → requeue) belum disertakan; idempotency menjadi bagian rencana
  Fase berikut (mirip latency RAG/agent jobs).

### 8.6 File utama Fase D

- `app/features/job/model.py` — `Job` + helper `mark_running/succeeded/failed`
- `app/features/job/repository.py` — create & get_by_id
- `app/features/job/tasks.py` — `JOB_TASKS` registry + `echo_job` (template worker)
- `app/features/job/queue.py` — `rq.Queue("ai-jobs")` + `enqueue_job`
- `app/features/job/usecase.py` — `create_job`, `get_job`
- `app/features/job/router.py` — `POST /api/jobs`, `GET /api/jobs/{id}`
- `app/jobs/worker.py` — entry worker RQ
- `app/core/config/redis.py`, `app/core/lifespan.py`, `docker-compose.yml`
