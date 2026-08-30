# Grafana — Memahami Dashboard & Metrik Kita

Dokumen ini menjelaskan **apa yang kita ukur, kenapa, dan cara membacanya** —
dari sudut pandang yang bisa kamu pakai saat buka Grafana atau debugging
produksi. Bukan daftar JSON, tapi **cerita di balik setiap angka**.

---

## 1. Mental model: metrik → Prometheus → Grafana

```
App (FastAPI)                    Prometheus                  Grafana
┌─────────────────┐   scrape   ┌──────────────────┐   query  ┌─────────────────┐
│ /metrics        │ ─────────▶ │ simpan time series│ ───────▶ │ dashboard/panel │
│ (Prometheus fmt)│  tiap 15s  │ + PromQL         │          │ (visualisasi)   │
└─────────────────┘            └──────────────────┘          └─────────────────┘
```

- **App** expose `/metrics` (proteksi `X-API-Key`).
- **Prometheus** scrape tiap 15 detik, simpan history, bisa di-query (UI di
  `localhost:9090`).
- **Grafana** cuma visualisasi — baca dari Prometheus, tidak menyimpan sendiri.
  UI di `localhost:3000` (admin/admin dev).

Dashboard auto-provision dari `deploy/grafana-provisioning/dashboards/*.json` —
edit JSON lalu `docker compose restart grafana` → dashboard muncul.

---

## 2. Dashboard: API Overview

**Tujuan:** "Apakah API sehat dan dipakai?" — pandangan pertama saat buka Grafana.

| Panel | Query (PromQL) | Cerita di baliknya |
|-------|----------------|--------------------|
| Request rate by path | `sum(rate(http_request_total{path!="/metrics"}[5m])) by (path)` | Endpoint mana yang paling dipakai? Naik/turunnya trafik. |
| Error rate by path (5xx) | `sum(rate(http_request_total{status_code=~"5..",path!="/metrics"}[5m])) by (path)` | Endpoint mana yang error? Server error = bug/infra. |
| Error rate (%) | `sum(rate(...5xx...)) / sum(rate(...total...)) * 100` | Persentase request gagal. Ambang wajar ~<1%; di atas itu = ada masalah. |
| Total requests (1h) | `sum(increase(http_request_total[1h]))` | Volume absolut — buat lihat tren harian. |
| P95 latency by path | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path))` | **95% request selesai dalam X detik.** Endpoint lambat ketahuan di sini. |

**Cara baca:** kalau error rate naik + P95 latency naik di path yang sama →
kemungkinan endpoint itu bermasalah (bukan trafik tinggi).

> Kenapa `/metrics` di-exclude? Itu endpoint internal (di-scrape Prometheus tiap
> 15s) — kalau ikut, dia bakal mendominasi grafik dan menyesatkan.

---

## 3. Dashboard: LLM & Tokens

**Tujuan:** "LLM kita sehat dan tidak boros?" — fokus AI.

| Panel | Query | Cerita |
|-------|-------|--------|
| LLM requests by status | `sum(rate(llm_request_total[5m])) by (status)` | Sukses vs error. Status `error` di sini = request LLM gagal total. |
| LLM P95 latency | `histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket[5m])) by (le))` | Seberapa lambat model menjawab. Naik = model lagi berat/provider lambat. |
| Token usage rate (in vs out) | `sum(rate(llm_input_tokens_total[5m]))` + `sum(rate(llm_output_tokens_total[5m]))` | **Ini proksi biaya kita.** Input = konteks/history, output = jawaban. |
| Token ratio (out/in) | `out / in * 100` | Output dibanding input. Ratio tinggi = model "banyak bicara" (chat), rendah = banyak konteks (RAG). |
| LLM errors by type | `sum(rate(llm_error_total[5m])) by (error_type)` | **Jenis error**: `timeout`, `rate_limit`, `auth`, `provider`. Rate limit naik = kita kena batas provider; auth naik = API key salah. |
| Chat messages (1h) | `sum(increase(chat_messages_sent_total[1h]))` | Aktivitas chat riil (user + assistant pesan disimpan). |

**Cara baca:** token ratio tinggi + input tokens naik drastis = history makin
panjang (budget context bekerja). Error `rate_limit` muncul = perlu naikkan
limit atau kurangi parallelism.

> **Catatan biaya**: kita belum punya harga per model (price registry ditunda).
> `llm_input/output_tokens_total` adalah proksi — kalau mau angka rupiah/dollar,
> tinggal kalikan dengan harga model (pekerjaan berikutnya).

---

## 4. Dashboard: Health & Reliability

**Tujuan:** "Infra kita stabil?" — retry, rate limit, ketersediaan.

| Panel | Query | Cerita |
|-------|-------|--------|
| Scrape target up | `up{job="ai-backend-v2"}` | **1 = Prometheus bisa reach app.** 0 = app mati/port beda. Cek ini dulu kalau semua panel kosong! |
| Retry attempts | `sum(rate(retry_attempts_total[5m])) by (operation)` | Berapa kali kita coba ulang panggilan (LLM/embedding). Naik = provider tidak stabil. |
| Retry exhausted | `sum(rate(retry_exhausted_total[5m])) by (operation)` | **Retry habis = request gagal total.** Ini yang bikin 5xx. |
| Rate limiter tokens available | `rate_limiter_tokens_available` | Token bucket internal. **0 = semua request LLM antri/tertahan** (kita throttle diri sendiri). |
| 4xx error rate | `sum(rate(http_request_total{status_code=~"4..",path!="/metrics"}[5m])) by (path)` | Error klien (404/401/400). Naik mendadak = klien bug atau ada yang salah panggil API. |

**Cara baca:** urutan debug yang benar: **Scrape up → Retry exhausted → Rate
limiter**. Kalau `up` = 0, semua panel lain tidak relevan.

---

## 5. Dashboard: RAG

**Tujuan:** "Fitur RAG kita bekerja dan berguna?" — visibility untuk subsistem
terbaru.

| Panel | Query | Cerita |
|-------|-------|--------|
| Documents uploaded (1h) | `sum(increase(rag_documents_total[1h]))` | Berapa dokumen masuk. |
| Chunks indexed (1h) | `sum(increase(rag_chunks_total[1h]))` | Berapa potongan teks di-embed + disimpan. **Naik = dokumen besar.** |
| Retrieval hit rate (%) | `hits / (hits + misses) * 100` | **Seberapa sering pencarian menemukan chunk.** Rendah = embedding/dokumen kurang relevan, atau pertanyaan di luar topik dokumen. |
| Retrieval rate | `sum(rate(rag_retrieval_duration_seconds_count[5m])) by (top_k)` | Frekuensi retrieval per request chat. |
| Retrieval P95 duration | `histogram_quantile(0.95, sum(rate(rag_retrieval_duration_seconds_bucket[5m])) by (le))` | Seberapa cepat cari chunk (embed query + cosine search). Lambat = embedding API/DB. |
| Retrieval hits vs misses | `rate(hits)` + `rate(misses)` | Overlay langsung: kapan search kosong. |

**Cara baca:** hit rate rendah + hits/misses berdekatan → pertanyaan user sering
tidak nyambung dengan isi dokumen. Bukan bug, tapi sinyal kualitas data
(chunking terlalu kecil, dokumen kurang relevan, atau pertanyaan di luar scope).

---

## 6. Kalau semua panel kosong — urutan cek

1. **`docker compose ps`** — semua service jalan?
2. **App jalan?** `curl -H "X-API-Key: <key>" localhost:8000/metrics` → ada output?
3. **Prometheus bisa scrape?** UI `localhost:9090` → Status → Targets → `ai-backend-v2` → **UP**?
4. **Dashboard pilih waktu yang benar?** Panel default `last 1h` — kalau tidak ada
   trafik di jam itu, panel kosong (bukan error).
5. **Sudah restart app setelah tambah metrik baru?** Metrik baru (`rag_*`,
   `llm_error_total`) hanya muncul setelah proses app di-restart.

---

## 7. Menambah metrik/dashboard baru (pola cepat)

1. **Metrik**: buat file di `app/core/metrics/` (pola `Counter`/`Histogram`/`Gauge`),
   lalu `.inc()`/`.observe()` di titik yang relevan.
2. **Dashboard**: salin JSON panel dari dashboard yang ada (mis. panel `stat` atau
   `timeseries`), ganti `expr`-nya. Simpan di
   `deploy/grafana-provisioning/dashboards/`.
3. `docker compose restart grafana` → dashboard muncul.
4. **Restart app** → metrik mulai terisi.

Aturan label Prometheus: pilih label yang **terbatas jumlah nilainya**
(`model`, `status`, `error_type`). Jangan pakai label yang unik per-request
(mis. conversation_id) — itu bikin kardinalitas meledak dan Prometheus lemot.
