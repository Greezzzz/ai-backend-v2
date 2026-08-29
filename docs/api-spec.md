# API Spek — ai-backend-v2

Dokumen ini untuk integrasi klien (mobile app). Base URL: `http://<host>:8000`.

## Konvensi Umum

- **Auth**: endpoint `/api/*` (kecuali `register`/`login`) butuh `Authorization: Bearer <access_token>`.
- **Single session**: setiap login/refresh membuat `session_id` baru di Redis. Token lama langsung **tidak valid** (401) begitu ada login/refresh baru. Logout menghapus session.
- **Token**: `access_token` berlaku **30 menit**, `refresh_token` berlaku **60 menit**. Gunakan `refresh_token` untuk mendapatkan pasangan token baru.
- **Format error** (semua endpoint, kecuali 429 rate-limit HTTP):
  ```json
  {
    "code": "AUTHENTICATION_ERROR",
    "message": "Authentication required",
    "details": null
  }
  ```
- **429 (HTTP rate limit)**: `RateLimitMiddleware` per-IP (in-memory, default 60 req/menit).
- **Trace**: klien bisa kirim `X-Trace-Id` (trace id milik klien). Response selalu
  membawa:
  - `X-Trace-Id` — trace id **server** (OpenTelemetry; sama dengan yang ada di
    log & Jaeger). Cari nilai ini di Jaeger untuk melihat trace penuh.
  - `X-Client-Trace-Id` — echo dari `X-Trace-Id` yang dikirim klien (hanya ada
    kalau klien mengirimnya).
  - Alternatif standar: kirim header `traceparent` (W3C) → trace id server otomatis
    sama dengan trace id klien, dan atribut `client.trace_id` di Jaeger mencatat
    `X-Trace-Id` klien.

---

## 1. Auth

### 1.1 Register — `POST /api/auth/register` (publik)

Body:
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "supersecret123"
}
```
- `username`: 3–50 karakter. `email`: valid. `password`: 8–128 karakter.

Response `200`:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com"
}
```

Errors:
- `409 USER_ALREADY_EXISTS` — username/email sudah dipakai.

### 1.2 Login — `POST /api/auth/login` (publik, form-encoded)

Body (form-urlencoded, bukan JSON):
```
username=johndoe&password=supersecret123
```

Response `200`:
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

Errors:
- `401 INVALID_CREDENTIALS` — username/password salah.

### 1.3 Refresh — `POST /api/auth/refresh`

Body:
```json
{ "refresh_token": "<jwt>" }
```

Response `200` — pasangan token baru (session dirotasi):
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

Errors:
- `401 AUTHENTICATION_ERROR` — refresh token invalid/expired.

> Catatan: setelah refresh, access token lama (sebelum refresh) tidak valid.

### 1.4 Logout — `POST /api/auth/logout` (auth)

Response `204 No Content` (hapus session dari Redis). Setelah ini semua token user tidak valid.

### 1.5 Me — `GET /api/auth/me` (auth)

Response `200`:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com"
}
```

---

## 2. Chat

Auth: semua endpoint chat butuh JWT.

### 2.1 Kirim pesan — `POST /api/chat/conversations`

Body:
```json
{
  "message": "Halo, apa itu RAG?",
  "conversation_id": null,
  "document_id": null
}
```
- `message`: 3–1000 karakter. `conversation_id`: opsional; `null`/tidak ada → buat percakapan baru.
- `document_id`: opsional; id dokumen (RAG) milik user. Kalau diisi saat **membuat
  percakapan baru**, dokumen **terikat ke percakapan** — pesan berikutnya di
  percakapan yang sama otomatis memakai dokumen itu, klien tidak perlu kirim ulang.

Response `200`:
```json
{
  "conversation_id": 12,
  "data": {
    "content": "RAG adalah Retrieval-Augmented Generation...",
    "model": "deepseek-v4-flash",
    "usage": { "input_tokens": 123, "output_tokens": 45, "total_tokens": 168 },
    "finish_reason": "stop"
  },
  "context_result": {
    "estimated_tokens": 168,
    "messages": [
      { "role": "user", "content": "Halo, apa itu RAG?" }
    ]
  }
}
```
- `data.usage`: bisa `null` (tergantung provider). `data.content`: teks jawaban.
- `context_result.messages`: pesan yang dikirim ke LLM (setelah pemangkasan context), `context_result.estimated_tokens`: estimasi token input.

Errors:
- `404 CONVERSATION_NOT_FOUND` — `conversation_id` tidak ada / bukan milik user.
- `401 AUTHENTICATION_ERROR` — token invalid/session tidak aktif.

### 2.2 Streaming chat — `POST /api/chat/stream`

Body sama dengan 2.1. Response: **SSE** (`text/event-stream`).

Format event (setiap event diakhiri `\n\n`):
```
data: {"delta": "RAG adalah "}

data: {"delta": "Retrieval-Augmented "}

data: {"delta": "Generation..."}

data: {"usage": {"input_tokens": 123, "output_tokens": 45, "total_tokens": 168}}

data: [DONE]
```

- `data: {"delta": "..."}` — potongan teks jawaban.
- `data: {"usage": {...}}` — token usage seluruh request (muncul sebelum `[DONE]`;
  bisa tidak ada kalau stream terputus).
- `data: {"error": "..."}` — error di tengah stream (stream berhenti).
- `data: [DONE]` — selesai.

### 2.3 Daftar percakapan — `GET /api/chat/conversations` (auth)

Response `200` (urut terbaru dulu, max 50):
```json
{
  "conversations": [
    {
      "id": 12,
      "title": "Halo, apa itu RAG?",
      "created_at": "2026-08-27T10:00:00Z",
      "document_id": 3,
      "last_message": "RAG adalah Retrieval-Augmented Generation..."
    },
    {
      "id": 11,
      "title": "Pesan pertama",
      "created_at": "2026-08-26T09:00:00Z",
      "document_id": null,
      "last_message": "Mock pesan pertama"
    }
  ]
}
```
- `last_message`: preview pesan terakhir (bisa `null` kalau percakapan kosong).
- `document_id`: dokumen (RAG) yang terikat ke percakapan (`null` kalau tidak ada).
  Klien bisa pakai ini saat membuka percakapan lama untuk tahu dokumen-nya.

### 2.4 Detail percakapan — `GET /api/chat/conversations/{id}` (auth)

Response `200` — metadata + **seluruh riwayat pesan** (urut dari terlama):
```json
{
  "id": 12,
  "user_id": 1,
  "title": "Halo, apa itu RAG?",
  "created_at": "2026-08-27T10:00:00Z",
  "document_id": 3,
  "messages": [
    {
      "id": 100,
      "conversation_id": 12,
      "role": "user",
      "content": "Halo, apa itu RAG?",
      "created_at": "2026-08-27T10:00:01Z"
    },
    {
      "id": 101,
      "conversation_id": 12,
      "role": "assistant",
      "content": "RAG adalah Retrieval-Augmented Generation...",
      "created_at": "2026-08-27T10:00:02Z"
    }
  ]
}
```
- `messages`: daftar lengkap pesan percakapan, `role` = `user` | `assistant`.

Errors:
- `404 CONVERSATION_NOT_FOUND` — tidak ada / bukan milik user.

---

## 2b. RAG (dokumen)

Auth: semua endpoint RAG butuh JWT. Dokumen **milik user** — user lain tidak bisa
mengakses dokumen kamu.

### 2b.1 Upload dokumen — `POST /api/rag/documents`

Body:
```json
{
  "title": "tentang-ceo",
  "content": "Nama panggilan CEO kami adalah Grezz..."
}
```

Response `200`:
```json
{ "document_id": 1 }
```
> Dokumen di-chunk, tiap chunk di-embed (OpenAI `text-embedding-3-small`), dan
> disimpan ke pgvector.

> **Keamanan**: konten dokumen diperlakukan sebagai **data tidak tepercaya**.
> Saat dipakai di chat, konteks dokumen dibungkus tag `<context>...</context>`
> dengan instruksi agar model tidak mengikuti instruksi di dalamnya (pertahanan
> terhadap prompt injection via dokumen).

### 2b.2 Detail dokumen — `GET /api/rag/documents/{id}`

Response `200`:
```json
{
  "id": 1,
  "user_id": 525,
  "title": "tentang-ceo",
  "created_at": "2026-08-28T12:00:00Z"
}
```

Errors:
- `404 VALIDATION_ERROR` — dokumen tidak ada / bukan milik user.

---

## 3. Jobs (background)

Auth: semua endpoint jobs butuh JWT.

### 3.1 Buat job — `POST /api/jobs`

Body:
```json
{
  "type": "echo",
  "payload": { "message": "hello" }
}
```
- `type`: nama task di registry (saat ini: `echo`). `payload`: input task.

Response `201`:
```json
{
  "id": 1,
  "type": "echo",
  "status": "queued",
  "payload": { "message": "hello" },
  "created_at": "2026-08-27T10:00:00Z",
  "updated_at": "2026-08-27T10:00:00Z"
}
```
> `result`, `error`, `started_at`, `finished_at` muncul hanya kalau terisi
> (contoh saat `status: "succeeded"` → `result` + `finished_at` muncul).

Errors:
- `400 VALIDATION_ERROR` — `type` tidak dikenal.

### 3.2 Cek job — `GET /api/jobs/{id}` (auth)

Response `200` — sama dengan 3.1, `status` bisa `queued | running | succeeded | failed`. `result`/`error` terisi sesuai status.

Errors:
- `404 JOB_NOT_FOUND` — job tidak ada.

---

## 4. Lain-lain

### 4.1 Health — `GET /health` (publik)

Response `200`:
```json
{ "status": "ok" }
```

### 4.2 Metrics — `GET /metrics` (API key)

Header: `X-API-Key: <api_key>`. Response: Prometheus text format. `401` tanpa key benar.

---

## Status Code & Error Code Ringkas

| Status | Code | Kondisi |
|--------|------|---------|
| 400 | `VALIDATION_ERROR` | input invalid / job type tidak dikenal |
| 401 | `AUTHENTICATION_ERROR` | token invalid, session tidak aktif, atau refresh invalid |
| 401 | `INVALID_CREDENTIALS` | login salah |
| 401 | `LLM_AUTHENTICATION_ERROR` | API key LLM ditolak provider |
| 404 | `CONVERSATION_NOT_FOUND` | percakapan tidak ada / bukan milik user |
| 404 | `JOB_NOT_FOUND` | job tidak ada |
| 409 | `USER_ALREADY_EXISTS` | register duplikat |
| 429 | `RATE_LIMIT_EXCEEDED` / `LLM_RATE_LIMIT` | rate limit HTTP / LLM |
| 502 | `LLM_PROVIDER_ERROR` | error provider LLM |
| 504 | `LLM_TIMEOUT` | timeout LLM |
