# PLAN — ai-backend-v2

> Dokumen rencana implementasi `ai-backend-v2`.
>
> **Sumber kebenaran: `goals.md`** — 8 pilar kompetensi yang harus dikuasai.
> `roadmap.md` adalah kendaraan untuk mencapai goals itu — **bukan bible**; boleh
> disesuaikan/dikesampingkan kalau tidak mendukung goals.
> Analisis kekurangan `ai-backend` (pro/cons) dipakai sebagai daftar perbaikan.
>
> Tujuan akhir: kamu paham arsitektur backend AI dan **mampu membuatnya sendiri**.

---

## 1. Ringkasan

- **Dari mana kita mulai**: fondasi `ai-backend` (code yang sudah jalan, 16 test lolos).
- **Ke mana kita pergi**: backend AI yang memenuhi 8 pilar goals — Python/FastAPI, DB
  relasional+vektor, integrasi LLM, background jobs, observability, containerization,
  security — plus integrasi mobile.
- **Cara kita jalan**: incremental. Setiap milestone = diskusi → rencana → implementasi →
  test → dokumentasi → review. **Tidak ada milestone yang dilewati tanpa diskusi dulu.**
- **Prinsip utama**: semua keputusan desain dicatat sebagai catatan belajar (kenapa pilih
  ini, apa trade-off-nya), supaya kamu bisa bikin sendiri setelahnya. Belajar > kerapian
  berlebihan: kami sengaja **menghindari over-engineering** yang bikin project susah dibaca
  dan dipelajari.

---

## 2. Landasan — goals.md (yang wajib dikuasai)

| # | Pilar goals | Kompetensi yang harus dikuasai |
|---|---|---|
| 1 | Python & fondasi | struktur data, OOP, error handling, **async/await** (LLM lambat → jangan blokir) |
| 2 | API Design & FastAPI | REST, HTTP semantics, status code, **auth (JWT/OAuth2)**, validasi input |
| 3 | DB Relasional & Vektor | PostgreSQL, **Vector DB**, **Redis** (cache + queue) |
| 4 | Integrasi LLM | SDK provider, **streaming response**, retry logic, API key management |
| 5 | Background Jobs | **Celery/RQ**, agent loop asinkron, notifikasi saat selesai |
| 6 | Observability | Sentry/Prometheus/Grafana/LangSmith-Langfuse, catat **setiap LLM call** (input, output, cost, latency) |
| 7 | Containerization | **Docker**, dasar CI/CD (GitHub Actions), deploy ke platform murah (Railway/Render) |
| 8 | Keamanan | secret management, **rate limiting per user**, validasi input (cegah prompt injection) |

> Catatan penting: beberapa poin masih *basic knowledge* — goals minta dicari **best
> practice**-nya, lalu diuji lewat **case studies** yang kita ciptakan sendiri (lihat bagian 8).

---

## 3. Landasan — Arsitektur ai-backend (yang kita bawa ke v2)

### 3.1 Alur request secara keseluruhan

```
HTTP Request
    ↓
FastAPI app (app/main.py)
    ↓
TraceMiddleware  → buat/inject trace_id (ContextVar), log start, ukur latency
    ↓
Router (app/api/router.py) → /chat, /metrics, /get_db
    ↓
Dependency Injection (Depends) — wiring otomatis dari atas ke bawah
    ↓
UseCase (features/chat/usecase.py) — orkestrasi alur bisnis
    ├── Service (ChatService) → LLMProtocol → OpenAIClient
    │       ├── RateLimiter    (token bucket, asyncio.Lock)
    │       ├── RetryExecutor  (exponential backoff + jitter)
    │       └── httpx.AsyncClient (dari lifespan, disimpan di app.state)
    ├── ContextManager (potong history agar muat token budget)
    │       └── TokenCounter (DeepSeekV4TokenCounter)
    └── Repository (Conversation/Message) → AsyncSession → PostgreSQL
    ↓
JSON Response (atau error → app_exception_handler → ErrorResponse)
```

### 3.2 Lapisan (layers) dan tanggung jawabnya

| Layer | Folder | Tanggung jawab | Contoh file |
|---|---|---|---|
| **API** | `app/api` | Routing, kontrak HTTP | `router.py`, `metrics.py`, `dependencies/database.py` |
| **Core** | `app/core` | Fondasi lintas fitur: config, db, exception, logging, rate limit, retry, metrics | `config/settings.py`, `database/`, `exceptions/`, `retry/` |
| **Domain** | `app/domain` | Business rules murni, tanpa framework. Ini "hati" aplikasi | `llm.py`, `model_profile.py`, `model_resolver.py`, `token.py` |
| **Application** | `app/application` | Orkestrasi use case + logika aplikasi | `context/manager.py`, `context/budget.py` |
| **Features** | `app/features` | Fitur per domain bisnis (chat) | `chat/` (router, usecase, service, repository, model) |
| **Infrastructure** | `app/infrastructure` | Implementasi teknis (tokenizer, dll) | `tokenizer/deepseek/v4/` |
| **LLM / Provider** | `app/llm`, `app/provider` | Abstraksi LLM + implementasi provider spesifik | `llm/protocol.py`, `llm/openai_client.py` |

**Aturan arah dependensi**: layer atas boleh tahu layer bawah, tapi layer bawah **tidak boleh**
tahu layer atas. `domain` tidak pernah import `fastapi` atau `sqlalchemy`. Ini yang bikin
domain gampang di-test dan diganti implementasinya.

### 3.3 Pola & konvensi yang menjadi standar v2

1. **Protocol, bukan ABC** — abstraction pakai `typing.Protocol` (structural typing).
   Trade-off: tidak ada validasi runtime, mengandalkan type checker/IDE.
   Contoh: `LLMProtocol`, `TokenCounterProtocol`, `RateLimiter`, `RetryPolicy`.
2. **Layered architecture** — pemisahan concern sesuai tabel 3.2.
3. **Repository pattern** — akses DB lewat repository, bukan query langsung di use case.
4. **Dependency Injection via FastAPI `Depends`** — wiring di `dependencies.py` per fitur.
5. **Exception terstruktur** — `AppException` base + `ErrorCode` enum + handler global.
6. **Structured JSON logging** — `JsonFormatter`, tiap log bawa `trace_id`.
7. **Observability sejak awal** — metrik Prometheus (HTTP, LLM, retry, rate limiter).
8. **Reliability pattern** — rate limiter token bucket + retry exponential backoff + jitter.
9. **Settings via pydantic-settings + `.env`** (tidak dibaca isinya, hanya dipakai runtime).

### 3.4 Prinsip belajar: jangan over-clean

Kita sengaja **tidak** melakukan hal-hal ini, karena bikin belajar & maintenance lebih susah:

- ❌ Generic repository base class / service locator / DI framework — wiring eksplisit
  sekarang lebih gampang dipelajari.
- ❌ Mypy strict + typing lengkap di semua file — cukup jalanin sekali-sekali buat cari bug.
- ❌ Refactor `ChatUseCase` jadi lebih "clean" — strukturnya sudah bagus untuk belajar.
- ❌ Hapus `practice/` yang sengaja crash (duck typing) — itu materi belajar, bukan bug.
- ❌ Abstraksi berlapis untuk hal yang belum butuh (YAGNI).

---

## 4. Analisis Pro/Cons ai-backend (input perbaikan)

### 4.1 Kekurangan — Bug & correctness (wajib dibenerin: ini salah, bukan preferensi)

| # | Masalah | Perbaikan |
|---|---|---|
| B1 | `MockClient` crash: `request.message` padahal field-nya `messages` | Perbaiki + test |
| B2 | `ModelRegistry.get` error message kehilangan f-string (`"unsuported model : {model}"`) + typo | Perbaiki pesan |
| B3 | `DeepSeekV4TokenCounter` mencetak `print()` debug tiap request | Hapus print, jadi log debug |
| B4 | Migration no-op (`pass`) + `drop_table('users')` yang tidak konsisten | Rapikan migration |
| B5 | `alembic/env.py` jalan `asyncio.run` saat import, offline mode di-comment | Rapikan |
| B6 | Metrik salah label: error non-httpx tercatat `success` (`isFail` tidak ter-set) | Perbaiki label metrik |
| B7 | `BusinessValidationException` signature `int \| 400` — annotation, bukan default → crash | Perbaiki default |

### 4.2 Kekurangan — Security (gap paling serius)

| # | Masalah | Perbaikan (di fase masing-masing) |
|---|---|---|
| S1 | Tidak ada auth sama sekali (chat & metrics terbuka) | Auth JWT/API key (Fase B) |
| S2 | `/metrics` bocorin internal ke publik | Proteksi endpoint metrics |
| S3 | Rate limit cuma di layer LLM, bukan per-user di HTTP | Rate limit per-user di HTTP layer |
| S4 | Payload lengkap di-log (`llm_request_payload`) | Logging tanpa data sensitif |
| S5 | Tidak ada CORS config, tidak ada limit ukuran request | Konfigurasi dasar |

### 4.3 Kekurangan — Performance

| # | Masalah | Perbaikan |
|---|---|---|
| P1 | `ContextManager.build_context` O(n²) — re-encode seluruh kandidat tiap iterasi | Hitung incremental / sekali encode |
| P2 | `DeepSeekV4TokenCounter` di-instantiate tiap request (`AutoTokenizer.from_pretrained` berat) | Singleton / cache, tangani offline |

### 4.4 Kekurangan — Engineering hygiene (bukan blokir, tapi bikin belajar lebih enak)

| # | Masalah | Perbaikan |
|---|---|---|
| H1 | Tidak ada test untuk layer API (middleware, exception handler, wiring DI) | Tambah API test |
| H2 | Tidak ada type-check/lint; pytest di dependencies utama | Pisah dev deps, tambah ruff/mypy ringan |
| H3 | Magic numbers hardcode (`16_000`, `0.7`, `1024`, `message[:50]`) | Dari config/ModelProfile |
| H4 | Tidak ada pagination / list conversation | Tambah endpoint list + pagination |
| H5 | Tidak ada `/health` | Tambah health check |
| H6 | README kosong | Tulis dokumentasi |
| H7 | Dead code: `ChatUseCase.execute`, `create_conversation` tidak dipakai; nama `get_conversations(id)` membingungkan | Rapikan/hapus |

---

## 5. Prioritas eksekusi (hasil penyatuan goals + roadmap + analisis)

> Urutan ini adalah **jalan utama**. Roadmap tetap jadi referensi teknis, tapi goals-lah yang
> menentukan apa yang dikerjakan lebih dulu.

### FASE A — Phase 4 selesai + beresin bug (fondasi semua yang lain)

**Kenapa pertama**: context management & multi-provider adalah fondasi RAG, agent, memory.
Beresin bug B1–B7 sekalian jadi materi "kenapa type checking penting".

**Pekerjaan**
1. Rapikan bug B1–B7.
2. Integrasi penuh `ModelResolver` → `ContextManager` → `ChatUseCase`:
   - budget context **model-aware** (dari `ModelProfile`, bukan hardcode `16_000`).
   - `ChatService.ask` pakai `max_output_tokens` dari profile.
   - H3 (magic numbers) selesai di sini.
3. P2: tokenizer jadi singleton/cache.
4. H1: tambah API test (middleware, exception handler, wiring DI).
5. H2: pisah dev deps; tambah ruff/mypy ringan.
6. H7: rapikan dead code.
7. Update `docs/architecture.md` + `docs/decisions.md`.

**Konsep yang dipelajari**: token budget (`context_window - reserved_output - safety_margin`),
chain dependency injection, structural typing, kenapa bug B1–B7 terjadi.

---

### FASE B — Security dasar: Auth + rate limit per-user (goals pilar 2 & 8)

**Kenapa kedua**: goals eksplisit minta auth & per-user rate limit; ini prasyarat project
layak dipakai multi-user. Tanpa ini, project cuma cocok single-user/belajar.

**Pekerjaan**
1. **Auth JWT** sederhana: register/login (hash password), dependency `get_current_user`.
   - S1 selesai: chat & metrics butuh token (metrics bisa dibatasi role/endpoint).
2. **Rate limit per-user** di HTTP layer: token bucket per identity (bukan cuma global LLM).
   - S3 selesai.
3. S5: CORS config + limit ukuran request.
4. S4: logging tanpa data sensitif (payload di-scrub).
5. Test: auth gagal/tanpa token, rate limit per user.

**Konsep yang dipelajari**: JWT vs OAuth2 (kapan pakai apa), password hashing, dependency
security, rate limit strategy per-identity.

---

### FASE C — Streaming response (goals pilar 4)

**Kenapa ketiga**: LLM modern harus streaming (token demi token); goals eksplisit minta.

**Pekerjaan**
1. `LLMProtocol.stream_chat` (async generator) + implementasi provider.
2. Endpoint `POST /chat/stream` → `StreamingResponse` (SSE).
3. Tangani: client disconnect, cancellation, error di tengah stream, partial response.
4. Test: consume stream, disconnect.

**Konsep yang dipelajari**: SSE vs WebSocket, async generator, cancellation, backpressure.

---

### FASE D — Background jobs + Redis (goals pilar 3 & 5)

**Kenapa keempat**: agent loop & task panjang tidak bisa sinkron di HTTP request; Redis
sekaligus buat cache. Ini membedakan "backend AI" dari backend biasa.

**Pekerjaan**
1. **Redis** masuk: caching (pertanyaan serupa → hemat biaya LLM) + queue.
2. **RQ** (Redis Queue) — rekomendasi: ringan, cukup untuk belajar. Celery opsional nanti.
3. `Job` model + lifecycle: created → queued → running → succeeded / failed.
4. Worker untuk document ingestion & embedding (nyambung ke RAG).
5. API: `POST /jobs`, `GET /jobs/{id}`.
6. Test: job lifecycle (mock worker).

**Konsep yang dipelajari**: queue vs langsung di request, job lifecycle, idempotency, retry job.

---

### FASE E — Vector DB + RAG (goals pilar 3)

**Kenapa kelima**: ini milestone terbesar dan paling membedakan backend AI. Goals sebut
Pinecone/Qdrant/Weaviate/pgvector — pilihan kita **pgvector** (satu DB untuk semua, tidak
tambah infra dulu, paling praktis sesuai goals).

**Pekerjaan**
1. `EmbeddingProtocol` + implementasi.
2. Pipeline ingestion: `DocumentParser` → `Chunker` (size + overlap) → `EmbeddingService`.
3. DB: migration pgvector (`vector` column, HNSW index), model `DocumentChunk`.
4. `VectorStore` (repository): simpan + query kosinus.
5. `RetrievalService`: query → embed → top-k → threshold.
6. **ContextManager extension**: budget untuk `system + RAG + history + current user`.
7. Advanced (bertahap): metadata filtering, hybrid search (BM25 + vector), reranking.
8. Evaluasi retrieval: hit@k, precision@k (dasar).
9. Menjawab pertanyaan dari Notes.md: "Bagaimana menentukan Top-K, chunk size, overlap,
   dan mengevaluasi retrieval?"

**Konsep yang dipelajari**: embedding & dimensi vector, cosine similarity, semantic space,
chunking + overlap, HNSW/ANN vs exact search, context pollution, pgvector.

---

### FASE F — Agent Architecture (roadmap Phase 7; mendukung goals pilar 5)

**Pekerjaan**
1. `ToolProtocol` + `ToolRegistry`.
2. Tools awal: calculator, search, database query, document retrieval (RAG).
3. `AgentLoop`: iterasi terbatas, validasi tool_call, tangani tool gagal/halusinasi,
   stopping condition.
4. Prompt template tool calling (fondasi sudah ada di `encoding_dsv4.py`).
5. Unit test: loop berhenti benar, tool error handling, max iteration.

**Konsep yang dipelajari**: agent loop & state management; tool calling format
(OpenAI function calling vs DSML); hallucinated tool call → validasi.

---

### FASE G — Multi-Provider lengkap (roadmap Phase 5; mendukung pilar 4)

> Catatan: Fase G sengaja **setelah** RAG & Agent — karena alur yang sudah jalan (chat)
> cukup pakai satu provider dulu. Multi-provider jadi bernilai saat butuh routing cost/fallback
> untuk RAG & agent.

**Pekerjaan**
1. `ProviderRegistry`: nama provider → factory client.
2. `OpenAIProvider` (generalisasi OpenAIClient) + `AnthropicProvider` + DeepSeek
   (OpenAI-compatible).
3. `TokenizerRegistry` diperluas: tiktoken (OpenAI), tokenizer Anthropic.
4. `ModelRegistry` diisi profile banyak model.
5. **Model routing**: default / cost-aware / fallback.
6. **Fallback**: provider A gagal → provider B.
7. Unit test: registry, router, fallback (mock provider gagal).

**Konsep yang dipelajari**: polymorphism lewat Protocol, registry/factory pattern,
OpenAI-compatible vs provider-specific, routing & fallback, cost-aware.

---

### FASE H — Memory & Advanced Context (roadmap Phase 10)

**Pekerjaan**
1. **Short-term**: sliding window (dari ContextManager) disempurnakan.
2. **Long-term**: `MemoryExtractor` (LLM ringkas fakta penting) → simpan → `MemoryRetriever`
   (tarik fakta relevan saat chat).
3. **Context budget allocation**: system + recent history + relevant old history (memory) +
   RAG + current user.
4. Summarization / compression untuk history panjang.
5. Test: budget allocation, ekstraksi & retrieval memory (mock LLM).

**Konsep yang dipelajari**: short vs long-term memory, summarization, compression, relevance
scoring.

---

### FASE I — Observability & Evaluasi lengkap (goals pilar 6; roadmap Phase 11)

**Pekerjaan**
1. **Per-LLM-call tracking**: trace_id, model, provider, latency, input/output/total tokens,
   cost (token × harga model), status — ke metrik & log (fondasi sudah ada di ai-backend).
2. Metrik tambahan: error rate LLM, token usage, cost, cache hit, retrieval latency.
3. Eksplorasi **Langfuse / LangSmith / OpenTelemetry / Sentry** — pilih satu yang
   diintegrasikan.
4. **Evaluation**: dataset + ground truth; metrik relevance, faithfulness, retrieval quality,
   hallucination. Bisa mulai LLM-as-judge sederhana.

**Konsep yang dipelajari**: observability vs monitoring, tracing terdistribusi, cost tracking,
evaluasi RAG & jawaban.

---

### FASE J — Containerization & Deployment (goals pilar 7; roadmap Phase 14)

**Pekerjaan**
1. `Dockerfile` + `docker-compose.yml` (saat ini **file kosong**): FastAPI, PostgreSQL
   (+pgvector), Redis, worker.
2. CI/CD: GitHub Actions — test, lint, build image, deploy.
3. Health check (`/health`, H5 selesai), graceful shutdown, secrets via env.
4. Migration otomatis saat deploy (`alembic upgrade head`).
5. Deploy ke platform murah (Railway/Render) sesuai goals.

**Konsep yang dipelajari**: containerization, CI/CD pipeline, environment & secrets,
deployment strategy.

---

### FASE K — Mobile Integration (goals: "Integrasi dalam mobile jangan lupa")

**Pekerjaan**
1. API contract stabil: versioning, pagination (H4), error contract (sudah ada).
2. Auth token/session untuk mobile (dari Fase B).
3. Streaming SSE untuk chat mobile (dari Fase C).
4. Reconnect & offline handling dasar (idempotency di backend).

**Konsep yang dipelajari**: mobile-backend contract, token/session, SSE reconnect, idempotency.

---

### FASE L — Architecture Review & Case Studies (roadmap Phase 16)

**Tujuan**: menguji arsitektur dengan sengaja membuat masalah. Ini jawaban goals:
"temukan masalah dan solusinya dari case studies yang kamu ciptakan."

**Pekerjaan** — 6 case study:
1. **LLM timeout** → retry → masih gagal → fallback. Apakah alurnya benar?
2. **Context overflow**: history 100K + RAG 30K + request → bagaimana ContextManager memangkas?
3. **Cost explosion**: 100 request/menit → model mahal → bagaimana routing & budget bekerja?
4. **Provider down**: OpenAI mati → fallback DeepSeek.
5. **Prompt injection**: dokumen berisi instruksi jahat → apakah trust boundary bekerja?
6. **RAG bad result**: chunk tidak relevan → bagaimana retrieval dievaluasi & diperbaiki?

**Konsep yang dipelajari**: failure testing, trade-off analysis, arsitektur sebagai keputusan
yang bisa diuji.

---

## 6. Strategi eksekusi per Fase

```
1. Diskusi      — bahas scope, keputusan desain, dan konsep (kamu baca PLAN + docs)
2. Rencana      — detail file & langkah di docs/ (update architecture.md, decisions.md)
3. Implementasi — code mengikuti konvensi section 3.3
4. Test         — unit + integration + api test (wajib hijau)
5. Dokumentasi  — tulis konsep yang dipelajari di README/docs + practice/ latihan
6. Review       — kamu coba jelaskan ulang / tanya; baru lanjut fase berikutnya
```

Setiap fase berhenti di review. **Tidak ada loncat fase tanpa persetujuan.**

---

## 7. Cara menjalankan & test (standar v2)

```bash
# install & sync dependency (uv)
uv sync

# jalankan server
uv run python -m uvicorn app.main:app --reload

# migration
uv run alembic upgrade head

# test
uv run pytest -v

# lint/type check (ringan, bukan wajib tiap commit)
uv run ruff check .
uv run mypy .
```

Dokumentasi lengkap command (`uv`, `alembic`) sudah ada di `uv.md` / `alembic.md` ai-backend
— akan disalin & disesuaikan ke v2.

---

## 8. Best practice & case studies (menjawab goals: "coba temukan praktik best practice")

> Goals minta: "beberapa hal masih basic knowledge, coba temukan praktik secara best practice
> coba temukan masalah dan solusinya dari case studies yang kamu ciptakan."
> Ini adalah daftar **case studies yang kita ciptakan** untuk menguji best practice. Detail
> lengkapnya akan ditulis per fase di `docs/case-studies.md`.

| Case study | Best practice yang diuji | Fase |
|---|---|---|
| CS1 — LLM timeout → retry → fallback | Retry policy, exponential backoff + jitter, circuit breaker | G, L |
| CS2 — Context overflow (100K history + RAG) | ContextManager budget, sliding window, summarization | A, H |
| CS3 — Cost explosion (100 req/menit, model mahal) | Cost-aware routing, rate limit per user, caching | B, D, G |
| CS4 — Provider down | Multi-provider fallback, health check | G, J |
| CS5 — Prompt injection lewat dokumen | Trust boundary, input validation, instruction hierarchy | B, E |
| CS6 — RAG bad result | Retrieval evaluation, chunk optimization, reranking | E, I |
| CS7 — Reconnect/offline mobile | SSE reconnect, idempotency | K |

---

## 9. Catatan & risiko

- **Scope besar** → eksekusi bertahap. Fase A dan B adalah fondasi semua fase berikut.
- **Dependency baru muncul bertahap**: pgvector (E), Redis (D), tool observability (I),
  Docker (J).
- **`.env` tidak dibaca/diubah** — hanya dipakai runtime lewat pydantic-settings.
- **Dokumentasi adalah deliverable utama** — code tanpa penjelasan = tidak belajar.
- Semua keputusan desain penting dicatat di `docs/decisions.md` (format ADR:
  Konteks → Keputusan → Konsekuensi).
- **Roadmap boleh dikesampingkan** kalau goals lebih baik dilayani dengan urutan lain.
  Contoh nyata di PLAN ini: Multi-Provider (roadmap Phase 5) digeser setelah RAG & Agent
  (Fase G), karena alur chat yang ada cukup satu provider dulu.
