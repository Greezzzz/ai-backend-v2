# Learn — Memahami ai-backend-v2 dari A sampai Z

Dokumen ini menjelaskan **cara kerja sistem** — bukan daftar file, tapi
**alur data, transformasi, dan korelasi antar kode**. Baca ini seperti
dijelaskan tech lead: dimulai dari mental model, lalu satu request hidup
dari masuk sampai keluar, kemudian tiap subsistem.

Cara baca: kalau mau detail implementasi, buka path yang disebut. Dokumen ini
menjelaskan *kenapa* dan *bagaimana nyambungnya*, bukan menyalin kodenya.

---

## 1. Mental model: satu kalimat per layer

```
HTTP request masuk
   ↓
app/api/router.py      → ini cuma "pintu": path + auth + delegasi
   ↓
features/*/router.py   → baca request, panggil usecase, bentuk response
   ↓
features/*/usecase.py  → ORKESTRASI: atur urutan kerja, panggil service/repo
   ↓
features/*/service.py  → LOGIKA BISNIS murni (tanpa tahu HTTP/DB)
   ↓
features/*/repository.py → SATU-SATUNYA yang sentuh DB (SQLAlchemy)
   ↓
PostgreSQL / Redis / LLM API
```

- `app/domain/` — **kontrak murni Python** (dataclass/protocol), tidak tahu
  FastAPI/SQLAlchemy. Semua layer boleh import ini.
- `app/core/` — fondasi lintas fitur: config, security, exceptions, metrics,
  observability, retry, rate limit.
- `app/llm/` + `app/provider/` — dunia luar: client LLM (OpenAI-compatible,
  Anthropic), tokenizer, embedding.
- `app/features/` — tiap fitur bisnis (auth, chat, job, rag) berdiri sendiri:
  router → usecase → service → repository → model.

**Aturan emas yang dipakai di project ini:**
1. Repository = satu-satunya yang boleh query DB.
2. Usecase = orkestrator, tidak tahu detail HTTP atau SQL.
3. Domain = murni, tidak boleh import framework.
4. `BusinessException` + `ErrorCode` = kontrak error seragam.

---

## 2. Request lifecycle: register → login → chat → stream

Ikuti satu pengguna dari nol. Ini alur lengkap yang paling penting dipahami.

### 2.1 Register
```
POST /api/auth/register
  → app/features/auth/router.py      (validasi body via RegisterRequest schema)
  → AuthService.register             (service.py)
      → cek username/email duplikat  (repository.get_by_username)
      → hash password                (app/core/security/password.py, pwdlib argon2)
      → simpan User                  (repository.create + session.commit)
  → response UserResponse {id, username, email}
```
Transformasi penting: **password polos → hash** di service. Plaintext tidak
pernah disimpan.

### 2.2 Login + single session
```
POST /api/auth/login  (form-encoded)
  → AuthService.login
      → verifikasi password           (verify_password)
      → generate session_id           (app/core/security/session.py:
                                        uuid + epoch_ms + 6 alfanumerik)
      → simpan session:{user_id} → session_id di Redis
                                        (app/core/security/session_store.py,
                                         TTL = refresh expiry 60 menit)
      → buat access_token + refresh_token
                                        (app/core/security/jwt.py)
      → TokenResponse {access_token, refresh_token}
```
**Kenapa Redis?** Single session = satu user hanya boleh punya satu session aktif.
Login baru menimpa value `session:{user_id}` di Redis → token lama otomatis
invalid. Kalau cuma JWT, kita tidak bisa "mencabut" token yang sudah terbit.

JWT berisi `sub` (user id) + `sid` (session id) + `exp`. Token itu sendiri
**stateless** — tapi validasinya nyambung ke Redis (lihat 2.3).

### 2.3 Setiap request terproteksi (mis. chat)
```
GET /api/chat/conversations
  → router chat punya dependencies=[Depends(get_current_user)]
  → app/api/dependencies/auth.py::get_current_user
      1. decode JWT → payload {sub, sid}      (jwt.decode)
      2. cek session:{sub} di Redis == sid    (kalau beda → 401)
      3. load User dari DB                     (UserRepository.get_by_id)
  → usecase pakai user.id sebagai "siapa yang minta"
```
Ini **sumber kebenaran identitas**: semua endpoint yang butuh user memakai
`user.id` dari `get_current_user`, bukan dari body request. Jangan pernah
percaya `user_id` yang dikirim klien.

**Sebelum sampai ke router/auth**, tiap request lewat `RateLimitMiddleware`
(dipasang di `app/main.py`, exclude `/metrics`):
- Identity = **IP client** (`X-Forwarded-For` pertama kalau ada proxy, fallback
  `request.client.host`) — method `_client_key()` di
  `app/middleware/rate_limit.py`.
- Limit diambil dari `.env`: `HTTP_RATE_LIMIT_REQUESTS_PER_MINUTE` (dibaca
  `settings.http_rate_limit.requests_per_minute`).
- Store: sliding window **in-memory** (`app/core/rate_limiter/http_store.py`) —
  per proses app, hilang saat restart.
- Kalau lewat → **429** `{code: "RATE_LIMIT_EXCEEDED"}` + header `Retry-After: 60`.
- Ini **rate limit request dari client** — beda dengan rate limiter ke LLM
  (lihat §5.4).

### 2.4 Chat biasa
```
POST /api/chat/conversations  {message, conversation_id?, document_id?}
  → ChatUseCase.chat  (app/features/chat/usecase.py)
  → _prepare_chat
      1. conversation_id kosong → buat Conversation baru (title = pesan[:50])
         ada → load + cek milik user (404 kalau bukan)
      2. kalau document_id diisi → RAG retrieve (lihat §6)
      3. append pesan user
      4. resolve model → token counter → ContextBudget (lihat §5.3)
      5. ContextManager.build_context → potong history kalau melebihi budget
  → ChatService.ask → LLM client.chat (lihat §5)
  → _save_messages: simpan pesan user + assistant
  → ChatResponse {conversation_id, data(LLMResponse), context_result}
```
Perhatikan **urutan transformasi**:
`input user → ChatMessage → [dipotong budget] → LLMRequest → LLMResponse →
disimpan ke DB → ChatResponse`.

### 2.5 Streaming chat
```
POST /api/chat/stream  (body sama)
  → ChatUseCase.stream_chat  → ASYNC GENERATOR
      yield data: {"delta": "..."}     → potongan teks
      yield data: {"usage": {...}}     → token usage (lihat §7)
      yield data: [DONE]
```
Yang sama dengan chat biasa: `_prepare_chat` dipakai bareng (jangan duplikasi).
Yang beda: response-nya SSE (`text/event-stream`), dan pesan assistant disimpan
**setelah stream selesai** (akumulasi delta), bukan sebelum.

**Streaming itu async generator** — setiap `yield` = satu event SSE yang dikirim
ke klien. Starlette yang meneruskan; kalau klien disconnect, generator di-close
otomatis.

---

## 3. Auth: refresh & logout (kenapa desainnya begini)

```
POST /api/auth/refresh {refresh_token}
  → AuthService.refresh
      → decode refresh_token (valid 60 menit)
      → _issue_tokens: session_id BARU → timpa Redis → token baru
  → TokenResponse baru

POST /api/auth/logout  (butuh access token valid)
  → AuthService.logout → hapus session:{user_id} dari Redis
  → 204
```

**Rotasi session**: setiap refresh, session_id diganti. Ini artinya:
- Refresh token lama tidak bisa dipakai ulang (session sudah berganti).
- Access token lama langsung mati (Redis berisi session_id baru).
- Logout menghapus session → semua token user tidak valid.

File terkait: `app/core/security/session.py` (generator id),
`app/core/security/session_store.py` (Redis CRUD), `app/core/security/jwt.py`
(create/decode token).

---

## 4. Konfigurasi & dependency injection: bagaimana semua tersambung

```
app/core/config/settings.py   → Settings (pydantic-settings, baca .env)
  ├─ .chat        → LLMSettings (semua CHAT_*: model, api_key, timeout, retry)
  ├─ .jwt         → JwtSettings
  ├─ .embedding   → EmbeddingSettings
  ├─ .redis       → RedisSettings
  ├─ .otel        → OtelSettings
  └─ .rate_limit  → RateLimiterSettings
```

**Satu sumber kebenaran**: `.env` → `Settings` → property → dipakai semua layer.
Tidak ada yang hardcode di kode.

**Resources** (`app/core/resources.py`): objek yang lahir di `lifespan`
(`app/core/lifespan.py`) dan disimpan di `app.state.resources`:
- `settings` — konfigurasi
- `http_client` — satu `httpx.AsyncClient` dipakai semua client LLM
- (plus `app.state.redis`, `app.state.db_*`)

**DI tanpa framework**: semua "get_x" di file `dependencies.py` adalah function
yang FastAPI panggil otomatis (Depends). Contoh rantai untuk chat:
```
get_chat_usecase
  → get_chat_service → get_chat_client (app/llm/factory.py)
       → CHAT_PROVIDER=openai → OpenAIClient
       → CHAT_PROVIDER=anthropic → AnthropicClient
  → get_db → session SQLAlchemy per-request
  → get_model_resolver → registry model + token counter
  → get_rag_service → embedding client + RAG repository
```

**Kunci**: ganti `.env` → ganti perilaku. `CHAT_PROVIDER` menentukan client,
`CHAT_MODEL` menentukan model + tokenizer, `EMBEDDING_*` menentukan embedding.

---

## 5. Layer LLM: provider, tokenizer, retry, rate limit

### 5.1 Provider dispatch
`app/llm/factory.py::get_chat_client` memilih client berdasarkan `CHAT_PROVIDER`:
- `openai` → `OpenAIClient` — format `/v1/chat/completions` (DeepSeek, Ollama,
  dan semua provider OpenAI-compatible pakai format ini).
- `anthropic` → `AnthropicClient` — format Messages API: header `x-api-key` +
  `anthropic-version`, `system` terpisah dari `messages`, `max_tokens` wajib.

Keduanya implement `LLMProtocol` (`app/llm/protocol.py`) — kontrak `chat()` +
`stream_chat()`. **Ini kenapa domain tidak tahu provider**: usecase cuma tahu
`LLMProtocol`.

### 5.2 Tokenizer: model menentukan cara hitung
`app/features/chat/dependencies.py::_get_default_token_counter`:
- model mengandung "deepseek" → `DeepSeekV4TokenCounter`
  (transformers `AutoTokenizer`, butuh download model, ada koreksi 79 token).
- model lain → `OpenAITokenCounter` (tiktoken, ringan, tanpa download).

Tokenizer dipakai `ContextManager` untuk **memperkirakan** token pesan sebelum
dikirim ke LLM. Ini bukan hitungan server — estimasi lokal untuk budgeting.

### 5.3 Context budget: kenapa history bisa terpotong
`app/application/context/budget.py` + `manager.py`:
```
ModelProfile (context_window, max_output_tokens dari .env)
  → ContextBudget (context_window - reserved_output) * safety_margin
  → ContextManager: masukkan pesan satu per satu selama masih muat budget
  → ContextResult {messages (yang muat), estimated_tokens}
```
Ini mencegah request melebihi context window model. History lama dibuang dulu,
pesan terbaru selalu dipertahankan.

### 5.4 Retry & rate limit (ke provider LLM)
- `RetryExecutor` (`app/core/retry/`) — exponential backoff + jitter, kebijakan
  per provider (`app/provider/{openai,anthropic}/retry_policy.py`).
- `RateLimiter` (`app/core/rate_limiter/limiter.py`) — **token bucket**, dipakai
  INTERNAL di client LLM untuk membatasi panggilan keluar ke provider
  (jangan dikelirukan dengan `RateLimitMiddleware` HTTP di §2.3 yang membatasi
  request masuk dari client per IP).
- Keduanya di-wrap di client: `chat()` = retry di sekitar rate-limited send.
  **Streaming: retry hanya sebelum stream mulai** (provider tidak bisa resume
  mid-stream).

### 5.5 Error mapping
`app/llm/openai_client.py` (dan anthropic): error httpx → `LLM*Exception`
(`app/core/exceptions/llm.py`): timeout→504, 429→rate limit, 401→auth, lain→502.
Ini yang bikin klien bisa bedakan penyebab error — dan metrik `llm_error_total`
mencatat jenisnya.

---

## 6. RAG: dari teks mentah ke jawaban berkonteks

Ini alur transformasi paling menarik — ikuti datanya:

### 6.1 Upload dokumen
```
POST /api/rag/documents  {title, content}  (auth, milik user)
  → RagService.upload_document
      1. chunk_text(content)          → list[str]
         (app/features/rag/chunking.py, 500 char + overlap 50)
      2. embedding_client.embed(chunks) → list[list[float]] (1536 dim)
         (app/llm/openai_embedding_client.py → OpenAI /v1/embeddings)
      3. simpan Document + DocumentChunk (embedding = Vector(1536))
         (app/features/rag/repository.py)
  → {document_id}
```

**Transformasi**: `teks panjang → potongan (chunk) → vektor → baris pgvector`.

### 6.2 Retrieval saat chat
```
chat {message, document_id}
  → ChatUseCase._prepare_chat
      1. verifikasi dokumen milik user   (404 kalau bukan)
      2. embed pertanyaan user → 1 vektor
      3. search_chunks: cosine_distance(embedding, query) ORDER BY ASC LIMIT 3
         (pgvector operator <=>)
      4. chunk teratas → system message:
         "Gunakan konteks berikut untuk menjawab pertanyaan user: ..."
  → LLM menjawab DENGAN konteks dokumen
```

**Transformasi**: `pertanyaan → vektor → jarak cosine ke semua chunk → 3 chunk
paling dekat → prompt context → jawaban grounded`.

### 6.3 Kenapa dipisah embedding vs chat
Embedding dan chat adalah **dua provider berbeda**:
- Embedding: OpenAI `text-embedding-3-small` (atau endpoint OpenAI-compatible
  via `EMBEDDING_BASE_URL`, client otomatis tambah `/v1`).
- Chat: `CHAT_PROVIDER` (DeepSeek/OpenAI/Anthropic).

Bisa dicampur bebas — RAG cuma soal "ubah teks jadi vektor, simpan, cari yang
dekat". Provider chat tidak peduli vektor itu dari mana.

---

## 7. Streaming usage: bagaimana kita tahu token yang dipakai

```
LLM stream → chunk SSE berisi usage (posisi bebas: awal/tengah/akhir)
  → OpenAIClient._parse_stream_usage  (deteksi field "usage" di chunk mana pun)
  → simpan ke client._last_usage
  → ChatUseCase setelah stream:
      1. tulis ke Prometheus (llm_input/output_tokens_total)
      2. yield data: {"usage": {...}} SEBELUM [DONE]
```
Kenapa tidak hitung dari delta? **chunk != token** — satu chunk bisa berisi 0,
1, atau banyak token. Hanya provider yang tahu angka sebenarnya, lewat
`stream_options: {include_usage: true}`.

---

## 8. Background jobs: Redis + RQ

```
POST /api/jobs {type: "echo", payload}
  → JobUseCase.create_job
      → simpan Job di DB (status=queued)     ← DB = sumber kebenaran
      → enqueue ke Redis (RQ queue)
  → 201 {id, status: queued}

python -m app.jobs.worker   (proses terpisah!)
  → RQ worker ambil job dari queue
  → task function (app/features/job/tasks.py) jalankan
  → update status di DB: queued → running → succeeded/failed
```

**Dua koneksi Redis** (`app/core/config/redis.py` + ADR-016):
- App: `redis.asyncio` (untuk session auth, dsb).
- RQ worker: `redis.Redis` **sync** (API RQ sinkron).

**Kenapa DB jadi sumber kebenaran?** Kalau Redis restart, antrian hilang — tapi
status job tetap bisa di-query dari DB. RQ cuma "delivery", bukan "rekam".

---

## 9. Observability: satu trace id dari log sampai Jaeger

```
Klien kirim: X-Trace-Id (opsional) atau traceparent (W3C)
  ↓
app/middleware/trace.py
  → FastAPIInstrumentor buat OTel server span
  → get_trace_id() (app/core/context/trace.py):
      prefer OTel span trace id → fallback ContextVar
  → response header:
      X-Trace-Id        = trace id SERVER (OTel, sama dengan Jaeger)
      X-Client-Trace-Id = echo trace id klien
  → kalau klien kirim X-Trace-Id, dicatat sebagai atribut client.trace_id di span
  ↓
app/core/observability/llm.py::instrument_llm_call
  → setiap panggilan LLM jadi child span: llm.{provider}.{chat|stream}
  → atribut: model, provider, token usage, status error
  ↓
OTLP HTTP → Jaeger v2 (docker-compose, UI localhost:16686)
```

**Korelasi log ↔ trace**: `AppLogger` menulis `trace_id` dari `get_trace_id()`.
Karena itu sekarang log, header, dan Jaeger memakai **trace id yang sama** —
cari di Jaeger pakai trace id dari log pasti ketemu.

### Metrik
- App expose `/metrics` (Prometheus format, proteksi `X-API-Key`).
- Prometheus scrape `host.docker.internal:8000` (header key di
  `deploy/prometheus.yml`).
- Grafana baca dari Prometheus, dashboard auto-provision
  (`deploy/grafana-provisioning/dashboards/`): API Overview, LLM & Tokens, RAG.

---

## 10. Peta file penting (korelasi cepat)

| Mau lihat | Buka |
|-----------|------|
| Settings & env | `app/core/config/settings.py`, `.env-example` |
| Layanan yang hidup saat app start | `app/core/lifespan.py` |
| Pintu masuk semua route | `app/api/router.py` |
| Siapa yang minta (auth) | `app/api/dependencies/auth.py` |
| Alur chat lengkap | `app/features/chat/usecase.py` |
| Pilih client LLM | `app/llm/factory.py` |
| Format request ke OpenAI | `app/llm/openai_client.py` |
| Format request ke Anthropic | `app/llm/anthropic_client.py` |
| Pilih tokenizer | `app/features/chat/dependencies.py` |
| Hitung budget context | `app/application/context/` |
| RAG upload & retrieve | `app/features/rag/service.py` + `repository.py` |
| Chunking | `app/features/rag/chunking.py` |
| Session auth (Redis) | `app/core/security/session_store.py` |
| Jobs + worker | `app/features/job/`, `app/jobs/worker.py` |
| Trace id unifikasi | `app/core/context/trace.py`, `app/middleware/trace.py` |
| OTel setup | `app/core/observability/otel.py`, `llm.py` |
| Infra lokal | `docker-compose.yml`, `deploy/` |

---

## 11. Ringkasan alur data utama

**Chat biasa:** `request → (auth) → usecase → context build → LLM → DB → response`

**Stream:** `request → usecase → async generator → SSE delta → usage → [DONE] → DB`

**RAG:** `dokumen → chunk → embedding → pgvector → (pertanyaan → vektor → cosine
search → context) → LLM → jawaban`

**Auth:** `register → login → session di Redis + JWT → tiap request validasi → refresh
rotasi → logout hapus`

**Observability:** `tiap request → span OTel → (log + Jaeger) ; metrik → Prometheus →
Grafana`

---

## 12. Sebelum deploy (pekerjaan yang tersisa)

1. **Dockerfile** untuk app + worker (belum ada).
2. `.env` production: secret key kuat, `API_KEY` di `deploy/prometheus.yml`
   harus sama, `OTEL_ENABLED`, dsb.
3. Rate limit HTTP masih in-memory (per proses) — untuk multi-instance perlu
   Redis (sudah dicatat sebagai pekerjaan berikutnya).
4. Cost tracking token (harga per model) belum ada — kandidat fase berikutnya.
