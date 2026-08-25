# Memory — ai-backend-v2

## Project Overview

Project utama belajar backend AI Engineer. Dibangun dari fondasi `ai-backend` (v1).
**Sumber kebenaran: `goals.md`** (8 pilar kompetensi). `roadmap.md` = kendaraan teknis,
bukan bible — urutan fase boleh disesuaikan kalau goals lebih baik dilayani (lihat PLAN.md).

Status roadmap saat ini:
- Phase 0–3: ✅ selesai (fondasi, FastAPI, DB, LLM integration).
- Phase 4: ✅ **Fase A selesai & terverifikasi** (integrasi ModelResolver → ContextManager →
  ChatUseCase, bug B1–B7, API test, docs). Verifikasi end-to-end dengan `.env` + DB asli:
  unit+api 16 passed, integration 5 passed, smoke test `/health` `/metrics` `/get_db` OK.
- **Fase B selesai & terverifikasi**: auth JWT + API key + rate limit HTTP. 33 test hijau
  (unit + api + integration), smoke test end-to-end register→login→chat OK.
- Fase berikutnya (PLAN.md): C (streaming), D (jobs+Redis), E (RAG), dst.

Dokumen kunci: `PLAN.md` (rencana fase A–L), `README.md` (setup/run),
`docs/architecture.md` (arsitektur), `docs/decisions.md` (ADR).

## Arsitektur & keputusan kunci (Fase A & B)

- **Layered**: `app/api → core → domain → application → features → infrastructure`
  (+ `llm/`, `provider/`). `domain` murni Python tanpa framework.
- **Model-aware context budget**: `ChatUseCase.chat()` resolve model via `ModelResolver`
  → dapat `ModelProfile` (context_window, max_output_tokens) → bangun `ContextBudget`.
  Jangan hardcode angka budget (16_000, 0.7, 1024) — sumber kebenaran di `ModelProfile`
  dan registry di `features/chat/dependencies.py`. `DEFAULT_MODEL` ada di
  `domain/model_profile.py` (jangan pindah ke dependencies — menyebabkan circular import).
- **Registry model**: `ModelRegistry` + `TokenCounterRegistry` + `ModelResolver`
  (`app/domain/`). Default model: `deepseek-v4-flash` (context 128k, max output 4096).
- **Tokenizer singleton**: `DeepSeekV4TokenCounter` di-cache di module-level
  (`_token_counter_cache` di `features/chat/dependencies.py`) — jangan instantiate ulang
  (AutoTokenizer.from_pretrained berat).
- **Error contract**: conversation not found → `BusinessException` + `ErrorCode.CONVERSATION_NOT_FOUND` (404), bukan ValueError.
- **Chat flow**: router → usecase (resolve model → build context → LLM → simpan pesan) →
  repository → DB. `POST /api/chat/conversations` menerima `message`, `conversation_id?`, `model?`.
- **Auth (Fase B)**:
  - `/health` publik; `/metrics` API key (header `X-API-Key`); `/api/*` JWT (Bearer);
    register/login publik.
  - Proteksi JWT dipasang di **level router chat** (bukan global /api) — kalau global,
    register/login ikut ke-proteksi.
  - Password: `pwdlib[argon2]` (`PasswordHash.recommended()`). JWT: `pyjwt` HS256.
  - Rate limit HTTP: `RateLimitMiddleware` in-memory sliding window per IP (semua request
    kecuali `/metrics`). Migrasi ke Redis di Fase D.
  - Settings baru: `JWT_SECRET_KEY`, `API_KEY`, `HTTP_RATE_LIMIT_REQUESTS_PER_MINUTE`
    (default dev aman di settings.py; wajib diisi `.env` untuk production).

## Hal yang sengaja TIDAK dilakukan (anti-over-engineering)

- Generic repository base class, DI framework, service locator.
- Mypy strict; typing lengkap di semua file (cukup ruff check ringan / mypy sesekali).
- Abstraksi berlapis untuk hal yang belum butuh (YAGNI).
- Menghapus `practice/` yang sengaja crash — itu materi belajar.

## Common Workflows

- Setup: buat `.env` (salin format dari ai-backend, isi sendiri) → `uv sync` →
  `uv run alembic upgrade head`.
- Run server: `uv run python -m uvicorn app.main:app --reload`.
- Test: `uv run pytest -v`. Di WSL tanpa uv di PATH:
  `../ai-backend/.venv/Scripts/python.exe -m pytest tests/unit tests/api -v`
  (integration butuh DB + `.env`).
- Smoke test tanpa server sungguhan: pakai `TestClient` dari FastAPI (uvicorn Windows
  tidak bisa di-hit lewat port di WSL).
- Jangan membaca/menyalin isi `.env` — hanya runtime via pydantic-settings.
- Setiap task: diskusi dulu dengan user sebelum implementasi.
