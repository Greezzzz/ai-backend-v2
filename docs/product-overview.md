# AI Backend — Ringkasan Produk

Dokumen ini menjelaskan **apa yang bisa dilakukan sistem ini** untuk kamu
sebagai pengguna. Ditulis non-teknis — fokus ke fitur, bukan implementasi.

---

## 1. Apa ini?

Sebuah **backend AI** yang menyediakan layanan percakapan (chat) dengan
kecerdasan buatan. Kamu bisa:

- **Chat** dengan AI — tanya apa saja, dapat jawaban.
- **Streaming** — jawaban muncul kata per kata (seperti mengetik), bukan
  menunggu selesai semua.
- **Upload dokumen** — beri AI sebuah dokumen teks, lalu tanya seputar isi
  dokumen itu; jawabannya berdasarkan dokumen kamu.

## 2. Fitur yang tersedia sekarang

### 2.1 Chat & Riwayat Percakapan
- Kirim pesan → AI menjawab.
- Setiap percakapan punya **riwayat** — kamu bisa buka lagi percakapan lama
  dan lanjut dari sana.
- Daftar percakapan dengan **preview pesan terakhir** — tahu isi percakapan
  tanpa membukanya.

### 2.2 Streaming Jawaban
- Jawaban AI tampil **bertahap** (real-time), bukan nunggu loading lama.
- Aplikasi klien bisa menampilkan efek "mengetik" — UX lebih natural.

### 2.3 RAG — Chat dengan Dokumen
- **Upload dokumen teks** → dapat ID dokumen.
- **Chat dengan konteks dokumen** — lampirkan ID dokumen saat bertanya, dan AI
  menjawab **berdasarkan isi dokumen kamu** (bukan jawaban umum).
- Dokumen **milik kamu** — tidak bisa diakses pengguna lain.

### 2.4 Akun & Keamanan
- **Register / Login** dengan email & password.
- **Single session** — satu akun aktif di satu perangkat pada satu waktu.
- **Refresh token** — sesi tetap aman saat token habis masa berlaku.
- **Logout** — hentikan sesi kapan saja.

## 3. Cara pakai (untuk pengembang/klien)

Sistem ini diakses lewat **API** (REST + SSE untuk streaming). Spesifikasi
lengkap: `docs/api-spec.md`.

### Alur dasar

```
1. Register  → POST /api/auth/register
2. Login     → POST /api/auth/login          → dapat access_token
3. Kirim pesan
   - biasa   → POST /api/chat/conversations  {message}
   - stream  → POST /api/chat/stream         {message}   (SSE)
4. Daftar percakapan → GET /api/chat/conversations
5. Detail percakapan → GET /api/chat/conversations/{id}   (riwayat pesan)
6. Upload dokumen    → POST /api/rag/documents            → document_id
7. Chat + dokumen    → POST /api/chat/conversations       {message, document_id}
```

### Endpoint ringkas

| Method | Path | Fungsi |
|--------|------|--------|
| POST | `/api/auth/register` | Buat akun |
| POST | `/api/auth/login` | Login (dapat token) |
| POST | `/api/auth/refresh` | Perbarui token |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Info akun |
| POST | `/api/chat/conversations` | Kirim pesan / buat percakapan |
| GET | `/api/chat/conversations` | Daftar percakapan + preview |
| GET | `/api/chat/conversations/{id}` | Riwayat pesan percakapan |
| POST | `/api/chat/stream` | Chat streaming (SSE) |
| POST | `/api/rag/documents` | Upload dokumen (RAG) |
| GET | `/api/rag/documents/{id}` | Detail dokumen |
| POST | `/api/jobs` | Buat background job |
| GET | `/api/jobs/{id}` | Cek status job |

Semua endpoint `/api/*` butuh token (`Authorization: Bearer <access_token>`),
kecuali `register` dan `login`.

## 4. Infrastruktur (untuk kepercayaan teknis)

Sistem ini bukan sekadar "chat API" — dibangun dengan fondasi yang bisa
dioperasikan:

- **Autentikasi** — JWT + session di Redis (single session, refresh, logout).
- **Observability** — setiap request punya `trace_id` yang bisa dilacak dari
  log sampai dashboard tracing (Jaeger).
- **Monitoring** — metrik penggunaan (Prometheus + Grafana): jumlah request,
  latensi, token LLM, error, aktivitas RAG.
- **Keamanan prompt** — konten dokumen diperlakukan sebagai data tidak
  tepercaya (dilindungi dari prompt injection via dokumen).
- **Deployment** — containerized (Docker), pipeline CI/CD (Jenkins), jalan di
  server produksi.

## 5. Status & rencana

**Selesai & berjalan:**
- Chat + streaming + riwayat percakapan
- Auth lengkap (register, login, single session, refresh, logout)
- RAG (upload dokumen + chat dengan konteks dokumen)
- Observability (tracing, metrik, dashboard)

**Rencana berikutnya (prioritas):**
- RAG lanjutan: multi-dokumen, hapus dokumen, evaluasi kualitas jawaban
- Tracking biaya (token → harga per model)
- Guardrail keamanan lebih lanjut (filter output, classifier)
- Integrasi mobile app

---

*Dokumen ini menyertai backend `ai-backend-v2` — API untuk klien mobile/web.*
