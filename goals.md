## 1. Bahasa Pemrograman & Fondasi

- *Python* — pilihan paling masuk akal karena seluruh ekosistem AI (LangChain, Hugging Face, LlamaIndex) berbasis Python
- Kuasai dulu: struktur data, OOP, penanganan error (try/except), dan *async/await* — ini krusial karena panggilan ke LLM API biasanya lambat (beberapa detik), backend harus bisa menangani banyak permintaan bersamaan tanpa saling memblokir

## 2. API Design & Web Framework

- *FastAPI* (Python) — pilihan paling umum untuk backend AI Agent karena native mendukung async dan otomatis menghasilkan dokumentasi API
- Konsep wajib: REST API design, HTTP methods/status code, autentikasi (JWT/OAuth2), validasi input (penting untuk mencegah prompt injection masuk lewat parameter API)

## 3. Database — Relasional & Vektor

- *PostgreSQL* — dasar penyimpanan data terstruktur (data pengguna, riwayat transaksi/konsultasi)
- *Vector Database* — ini yang membedakan backend AI Agent dari backend biasa: Pinecone, Qdrant, Weaviate, atau pgvector (ekstensi PostgreSQL, paling praktis kalau ingin satu database untuk semuanya)
- *Redis* — untuk caching (mengurangi biaya panggilan LLM berulang untuk pertanyaan serupa) dan sebagai antrian sederhana

## 4. Integrasi dengan LLM Provider

- SDK resmi Anthropic/OpenAI — memahami streaming response (menampilkan jawaban token demi token, bukan menunggu selesai semua), retry logic (LLM API kadang timeout/rate-limited), dan manajemen API key yang aman (tidak pernah hardcode di kode)

## 5. Background Jobs & Message Queue

- *Celery* atau *RQ (Redis Queue)* — agent loop yang butuh banyak langkah (Perceive→Reason→Plan→Act→Observe) tidak bisa dijalankan sinkron di satu request HTTP; butuh sistem antrian tugas latar belakang
- Ini juga dasar untuk fitur seperti "proses analisis ide bisnis lalu kirim notifikasi saat selesai"

## 6. Observability & Logging

- Terhubung langsung ke pilar Evaluasi/Safety yang sudah kita bahas: *Sentry* (error tracking), *Prometheus + Grafana* (metrik), atau layanan khusus AI seperti *LangSmith/Langfuse* yang sudah kita sebut sebelumnya
- Wajib dikuasai: cara mencatat setiap panggilan LLM (input, output, biaya token, latensi) untuk debugging dan evaluasi kualitas

## 7. Containerization & Deployment

- *Docker* — mengemas backend supaya bisa dijalankan konsisten di mana saja
- Dasar CI/CD (GitHub Actions) dan satu cloud platform (mulai dari yang gratis/murah seperti Railway atau Render sebelum masuk AWS/GCP yang lebih kompleks)

## 8. Keamanan

- Manajemen secret (environment variable, bukan hardcode), rate limiting per pengguna (mencegah penyalahgunaan/biaya membengkak), validasi dan sanitasi input sebelum masuk ke context LLM (lapisan pertahanan terhadap prompt injection)




beberapa hal masih basic knowledge, coba temukan praktik secara best practice coba temukan masalah dan solusinya dari case studies yang kamu ciptakan.

Integrasi dalam mobile jangan lupa