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
  `X-Trace-Id`, di-echo balik di response header `X-Trace-Id`.
- **Logging**: `JsonFormatter` → semua log JSON, otomatis bawa `trace_id`.
- **Metrics** (Prometheus): HTTP (total, duration), LLM (total, duration, input/output
  tokens), retry (attempts, exhausted), rate limiter (tokens available).
  Endpoint: `GET /metrics`.

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
