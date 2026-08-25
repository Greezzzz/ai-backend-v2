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

---

## Keputusan yang sengaja TIDAK diambil (anti-over-engineering)

| Hal | Alasan |
|---|---|
| Generic repository base class | Bikin abstraksi yang belum perlu; eksplisit lebih gampang dipelajari |
| Service locator / DI framework | FastAPI Depends + wiring eksplisit sudah cukup |
| Mypy strict + typing lengkap semua file | Cukup jalanin sekali-sekali buat cari bug |
| Refactor ChatUseCase lebih "clean" | Struktur sekarang sudah bagus untuk belajar |
| Abstraksi berlapis untuk yang belum butuh (YAGNI) | Hemat kompleksitas |
