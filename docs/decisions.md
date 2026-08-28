# Keputusan Desain (ADR) — ai-backend-v2

Format: **Konteks → Keputusan → Konsekuensi**. Dokumen ini bertambah di tiap fase.

---

## ADR-001: Protocol dibanding ABC untuk abstraction

- **Status**: diterima (warisan ai-backend, docs/decision.md)
- **Konteks**: butuh abstraction untuk LLM client, token counter, rate limiter, retry policy.
- **Keputusan**: pakai `typing.Protocol` (structural typing), bukan `ABC`.
- **Konsekuensi**:
  - ✅ Fleksibel, third-party friendly, tanpa hierarki inheritance.
  - ❌ Tidak ada validasi runtime — mengandalkan type checker (mypy) & IDE.
  - Pelajaran: structural typing = "yang penting punya method itu", bukan "harus turunan kelas ini".

## ADR-002: Layered architecture (domain tanpa framework)

- **Status**: diterima (warisan ai-backend)
- **Konteks**: aplikasi bakal tumbuh (chat, RAG, agent, memory). Butuh pemisahan concern.
- **Keputusan**: 7 layer (api/core/domain/application/features/infrastructure/llm-provider).
  Aturan: layer bawah tidak tahu layer atas; `domain` murni Python.
- **Konsekuensi**:
  - ✅ Domain gampang di-test & diganti implementasinya.
  - ✅ Alur dependensi jelas.
  - ❌ Kadang terasa verbose untuk fitur kecil (trade-off yang kita terima demi belajar).

## ADR-003: Repository pattern untuk akses DB

- **Status**: diterima (warisan ai-backend)
- **Konteks**: use case butuh baca/tulis conversation & message.
- **Keputusan**: `ConversationRepository` & `MessageRepository` membungkus query SQLAlchemy.
- **Konsekuensi**:
  - ✅ Use case tidak tahu SQL; query gampang di-test & di-mock.
  - ❌ Satu method per kebutuhan (bukan generic base class) — sengaja, biar eksplisit.

## ADR-004: Wiring DI eksplisit (tanpa framework DI)

- **Status**: diterima
- **Konteks**: FastAPI `Depends` sudah cukup; menghindari over-engineering.
- **Keputusan**: semua wiring di `features/chat/dependencies.py`, eksplisit per dependency.
- **Konsekuensi**:
  - ✅ Gampang dibaca: satu file menunjukkan seluruh rantai dependency.
  - ✅ Gampang di-override di test.
  - ❌ Ada boilerplate — trade-off yang kita terima.

## ADR-005: Context budget model-aware (dari ModelProfile, bukan hardcode)

- **Status**: diterima (Fase A)
- **Konteks**: awalnya `ContextBudget` hardcode `16_000` di dependencies. Padahal
  `ModelProfile` sudah punya `context_window` & `max_output_tokens`.
- **Keputusan**: `ChatUseCase.chat()` resolve model via `ModelResolver`, lalu bangun budget
  dari profile model yang dipilih. `ContextManager` tetap murni (hanya terima budget + counter).
- **Konsekuensi**:
  - ✅ Aplikasi otomatis menyesuaikan model apa pun (tinggal tambah profile di registry).
  - ✅ Satu sumber kebenaran konfigurasi model.
  - ❌ Budget bergantung pada model yang diminta request (`model` field) — default ke
    model yang dikonfigurasi.

## ADR-006: Tokenizer singleton (cache)

- **Status**: diterima (Fase A)
- **Konteks**: `DeepSeekV4TokenCounter` memanggil `AutoTokenizer.from_pretrained` (download
  HF + init berat). Di-instantiate tiap request sebelumnya.
- **Keputusan**: cache instance di module-level `_token_counter_cache`.
- **Konsekuensi**:
  - ✅ Init tokenizer hanya sekali per proses.
  - ❌ State global sederhana (bukan dependency injection murni) — cukup untuk sekarang.

## ADR-007: Error contract konsisten via AppException + ErrorCode

- **Status**: diterima (Fase A, sebagian warisan)
- **Konteks**: "conversation not found" tadinya `ValueError` (jadi 500). Padahal sudah ada
  sistem exception terstruktur.
- **Keputusan**: `BusinessException` + `ErrorCode.CONVERSATION_NOT_FOUND` → response 404
  dengan kontrak `{code, message, details}`.
- **Konsekuensi**:
  - ✅ Client (mobile/web) bisa handle error secara terprogram.
  - ✅ Konsisten dengan error LLM/rate-limit yang lain.

## ADR-008: Logging JSON + trace_id (warisan, dipertahankan)

- **Status**: diterima
- **Konteks**: observability butuh log terstruktur yang bisa di-parse & di-trace.
- **Keputusan**: `JsonFormatter` + `trace_id` (ContextVar) di semua log.
- **Konsekuensi**:
  - ✅ Mudah di-query (korelasi request lewat trace_id).
  - ❌ Log mentah kurang "manusiawi" — dinilai lewat tooling (jq, Grafana, dll).

## ADR-009: Password hashing pakai pwdlib[argon2]

- **Status**: diterima (Fase B)
- **Konteks**: butuh hash password untuk register/login. Di Java user biasa pakai bcrypt.
- **Keputusan**: `pwdlib` dengan backend Argon2 (`PasswordHash.recommended()`) — standar
  FastAPI, bukan `bcrypt` package langsung.
- **Konsekuensi**:
  - ✅ Argon2 memory-hard → lebih tahan GPU/ASIC daripada bcrypt; tidak ada limit 72 byte.
  - ✅ API modern pwdlib (hash/verify rapi), yang dipakai docs FastAPI.
  - ❌ Lebih lambat & boros memori (memang desainnya — password hashing harus mahal).
  - Trade-off vs bcrypt: bcrypt matang & familiar, tapi Argon2 lebih kuat & jadi rekomendasi
    OWASP. Diputuskan Argon2 karena user sudah paham konsep hashing.

## ADR-010: JWT untuk endpoint /api, API key untuk /metrics, /health publik

- **Status**: diterima (Fase B)
- **Konteks**: butuh membedakan level proteksi. Goals minta auth JWT/OAuth2; mobile butuh token.
- **Keputusan**:
  - `/health` publik (health check harus selalu bisa diakses).
  - `/metrics` dilindungi **API key statis** (cukup, internal-only; tidak butuh user session).
  - `/api/*` (chat, me) dilindungi **JWT** — setiap user punya token sendiri.
  - register/login publik (prasyarat untuk dapat token).
- **Konsekuensi**:
  - ✅ Skala proteksi sesuai kebutuhan; JWT siap untuk mobile (Fase K).
  - ✅ Metrics tidak bocor ke publik.
  - ❌ API key statis = satu key untuk semua (bukan per-user) — cukup untuk internal.

## ADR-011: Rate limit HTTP in-memory (sliding window), semua request

- **Status**: diterima (Fase B)
- **Konteks**: goals minta rate limiting per user; mencegah spam & biaya LLM meledak.
- **Keputusan**: `RateLimitMiddleware` global (semua request kecuali `/metrics`) memakai
  `InMemoryRateLimitStore` — sliding window per client IP.
- **Konsekuensi**:
  - ✅ Sederhana, tanpa dependency baru; melindungi seluruh endpoint.
  - ❌ In-memory → state hilang saat restart; tidak shared antar instance.
  - Rencana: migrasi ke Redis (Fase D) untuk distributed rate limit.

## ADR-012: Proteksi JWT dipasang di level router chat, bukan global /api

- **Status**: diterima (Fase B)
- **Konteks**: register/login harus publik, chat harus privat. Dependency global di `/api`
  akan ikut memproteksi register/login (karena include_router menggabungkan dependency).
- **Keputusan**: proteksi JWT dipasang di `chat_router` (dan `me`), sedangkan auth router
  dibiarkan publik.
- **Konsekuensi**:
  - ✅ Eksplisit & gampang dibaca — tiap router tahu proteksinya sendiri.
  - ❌ Harus ingat memasang proteksi di router baru (bukan otomatis).

## ADR-013: Streaming pakai SSE + endpoint terpisah

- **Status**: diterima (Fase C)
- **Konteks**: goals pilar 4 minta streaming response (token demi token).
- **Keputusan**:
  - **SSE** (server-sent events, satu arah) — cukup untuk chat; WebSocket (dua arah) tidak
    dibutuhkan sekarang.
  - **Endpoint terpisah** `POST /api/chat/stream` (bukan flag `stream: bool` di chat biasa)
    karena response type beda (SSE vs JSON).
  - **Format OpenAI-style**: `data: {json}\n\n` + `data: [DONE]` — familiar, siap untuk
    mobile (Fase K).
  - **Persist setelah stream selesai**: teks penuh diakumulasi, lalu simpan user + assistant.
- **Konsekuensi**:
  - ✅ Client (termasuk mobile) gampang adaptasi; auto-reconnect SSE.
  - ✅ Alur chat & stream berbagi `_prepare_chat` yang sama (konsisten).
  - ❌ Response type berbeda → client harus tahu endpoint mana yang dipakai.

## ADR-014: Retry hanya pre-stream (tidak ada mid-stream retry)

- **Status**: diterima (Fase C)
- **Konteks**: diskusi desain — apakah bisa retry kalau stream putus di tengah?
- **Keputusan**: retry hanya untuk kegagalan SEBELUM token pertama mengalir
  (timeout connect, 429, network). Begitu stream mulai, kalau putus → kirim event
  `data: {"error": ...}` ke client, bukan retry.
- **Konsekuensi**:
  - ✅ Sederhana & jujur terhadap kemampuan provider (tidak ada resume API).
  - ✅ Client tahu persis kapan gagal.
  - ❌ Recovery mid-stream jadi tanggung jawab client (request ulang / tampilkan error) —
    relevan untuk reconnect di Fase K.

## ADR-015: Format SSE tidak seragam antar provider (parser per provider)

- **Status**: diterima (Fase C, berlaku untuk Fase G)
- **Konteks**: streaming response antar provider **tidak sama** — ada dua keluarga format
  (OpenAI-compatible vs Anthropic), dan bahkan di dalam OpenAI-compatible isi `delta` beda
  (`content` vs `reasoning_content`), plus varian (chunk usage, keep-alive, penutup berbeda).
- **Keputusan**:
  - `LLMProtocol.stream_chat` menyeragamkan semua jadi `AsyncIterator[str]` (delta teks) —
    service & usecase tidak peduli format internal.
  - Parsing delta **provider-aware**: hidup di dalam masing-masing client, bukan di service.
  - Di Fase G, tiap provider punya parser sendiri (OpenAI-compatible, Anthropic, dll).
- **Konsekuensi**:
  - ✅ Abstraksi tetap bersih; menambah provider = tinggal implementasi client + parser.
  - ✅ Temuan konkret sudah dipakai: DeepSeek reasoning → baca `reasoning_content`
    fallback `content`; JSON invalid → return None (jangan crash).
  - ❌ Setiap provider baru butuh parser & test sendiri (tidak otomatis).

## ADR-016: Redis via Docker + `redis.asyncio` di app, sync di RQ

- **Status**: diterima (Fase D)
- **Konteks**: butuh Redis untuk queue background job (dan nantinya cache, rate limit
  distributed). Tapi app FastAPI memakai `asyncio`, sedangkan RQ/`redis-py` sync.
- **Keputusan**: dua koneksi berbeda:
  - **App**: `redis.asyncio.from_url` di `lifespan` (ke `app.state.redis`), untuk operasi
    async (cache).
  - **RQ**: `redis.Redis` **sync** (di `queue.py` & `worker.py`) karena API RQ sinkron.
  - Redis dijalankan via `docker-compose.yml` (`redis:7-alpine`, port `6379`).
- **Konsekuensi**:
  - ✅ Tidak mencampur event loop: async app vs sync worker masing-masing punya client benar.
  - ✅ Redis diasumsikan tersedia saat app start (lifespan connect) — konsekuensi: kalau Redis
    mati, app bisa gagal start; diterima untuk dev, mitigasi nanti di observability (Fase I).
  - ❌ Dua client Redis (async & sync) = sedikit duplikasi konfigurasi.

## ADR-017: DB sebagai sumber kebenaran status job (RQ hanya antrian)

- **Status**: diterima (Fase D)
- **Konteks**: job punya lifecycle `queued → running → succeeded/failed`. Kalau status
  cuma hidup di RQ/Redis, hilang saat Redis restart; dan query history job jadi susah.
- **Keputusan**: simpan status & metadata job di tabel `jobs` (DB Postgres). RQ hanya
  mengantri "panggil function ini dengan argumen ini"; worker meng-update status di DB
  (create → queued, fetch → mark_running, selesai → mark_succeeded/failed).
- **Konsekuensi**:
  - ✅ Job tetap bisa di-query walau Redis/worker mati; DB jadi single source of truth.
  - ✅ Gampang buat list/history job, audit, dan recovery nanti.
  - ❌ Worker butuh akses DB sendiri (buka engine/session terpisah via `asyncio.run()`) —
    tidak bisa reuse session dari request FastAPI.

## ADR-018: RQ (bukan Celery) + worker generik `echo` dulu

- **Status**: diterima (Fase D)
- **Konteks**: PLAN minta RQ (ringan) untuk belajar, Celery opsional nanti; worker ingestion
  RAG butuh fondasi yang jelas.
- **Keputusan**:
  - **RQ**, bukan Celery — ringan, cukup untuk belajar; migrasi ke Celery mungkin di Fase J.
  - **Worker generik `echo`** (bukti lifecycle) sekarang; worker ingestion/embedding baru di
    Fase E. Task function di-resolve dari registry `JOB_TASKS` sesuai `type`.
- **Konsekuensi**:
  - ✅ Bukti end-to-end lifecycle queued→running→succeeded bisa ditest tanpa fitur berat.
  - ✅ `_run_job` di `tasks.py` jadi template worker RAG (buka session → running → proses →
    succeeded/failed).
  - ❌ Tambahan konsep baru (queue) memperbesar scope; ditunda caching chat & migrasi rate
    limit ke Redis ke fase berikut.
  - **Kendala Windows (belajar penting):** RQ worker default & `SpawnWorker` butuh `os.fork` /
    `os.wait4` yang tidak ada di Windows. Karena environment belajar = WSL + python Windows,
    kita pakai `SimpleWorker` (in-process, tanpa fork — tapi tanpa isolasi proses per job).
    Saat deploy Linux (Fase J) ganti ke `Worker` (fork) agar job crash tidak menimpa worker.

---

## Keputusan yang sengaja TIDAK diambil (anti-over-engineering)

| Hal | Alasan |
|---|---|
| Generic repository base class | Bikin abstraksi yang belum perlu; eksplisit lebih gampang dipelajari |
| Service locator / DI framework | FastAPI Depends + wiring eksplisit sudah cukup |
| Mypy strict + typing lengkap semua file | Cukup jalanin sekali-sekali buat cari bug |
| Refactor ChatUseCase lebih "clean" | Struktur sekarang sudah bagus untuk belajar |
| Abstraksi berlapis untuk yang belum butuh (YAGNI) | Hemat kompleksitas |
