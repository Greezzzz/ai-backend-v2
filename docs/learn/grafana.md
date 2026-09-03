# Grafana — Memahami Dashboard & Metrik Kita

Dokumen ini menjelaskan **apa yang kita ukur, kenapa, dan cara membacanya** —
dari sudut pandang yang bisa kamu pakai saat buka Grafana atau debugging
produksi. Bukan daftar JSON, tapi **cerita di balik setiap angka**.

> Dokumen ini **mengikuti dashboard aktual** di
> `deploy/grafana-provisioning/dashboards/*.json`. Kalau dashboard diubah,
> dokumen ini harus ikut diubah.

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

> **Label path & noise bot:** middleware HTTP (`app/middleware/trace.py`)
> mencatat label `path` sebagai **template route** (mis.
> `/api/chat/conversations/{conversation_id}`), bukan path mentah. Request yang
> tidak match route mana pun (scanner/bot internet) dikelompokkan `unmatched`
> dan **tidak dihitung** ke metrik HTTP — begitu juga request `/metrics`
> (scrape Prometheus sendiri). Jadi metrik HTTP hanya berisi trafik API asli.

---

## 2. Dashboard: API Overview

**Tujuan:** "Apakah API sehat dan dipakai?" — pandangan pertama saat buka Grafana.

| Panel | Query (PromQL) | Cerita di baliknya |
|-------|----------------|--------------------|
| Request rate by path | `sum(rate(http_request_total{path!="/metrics"}[5m])) by (path)` | Endpoint mana yang paling dipakai? Naik/turunnya trafik. Path = template route. |
| Error rate by path (5xx) | `sum(rate(http_request_total{status_code=~"5..",path!="/metrics"}[5m])) by (path)` | Endpoint mana yang error? Server error = bug/infra. |
| Error rate (%) | `sum(rate(...5xx...)) / sum(rate(...total...)) * 100` | Persentase request gagal. Ambang wajar ~<1%; di atas itu = ada masalah. |
| Total requests (last 24h) | `sum(increase(http_request_total[24h]))` | Volume absolut 24 jam — buat lihat tren harian. |
| P95 latency by path | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path))` | **95% request selesai dalam X detik.** Endpoint lambat ketahuan di sini. |

**Cara baca:** kalau error rate naik + P95 latency naik di path yang sama →
kemungkinan endpoint itu bermasalah (bukan trafik tinggi).

---

## 3. Dashboard: LLM & Tokens

**Tujuan:** "LLM kita sehat dan tidak boros?" — fokus AI.

| Panel | Query | Cerita |
|-------|-------|--------|
| LLM requests by status | `sum(rate(llm_request_total[5m])) by (status)` | Sukses vs error. Status `error` di sini = request LLM gagal total. |
| LLM P95 latency | `histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket[5m])) by (le))` | Seberapa lambat model menjawab. Naik = model lagi berat/provider lambat. |
| Token usage rate (in vs out) | `sum(rate(llm_input_tokens_total[5m]))` + `sum(rate(llm_output_tokens_total[5m]))` | **Ini proksi biaya kita.** Input = konteks/history, output = jawaban. |
| LLM errors by type | `sum(rate(llm_error_total[5m])) by (error_type)` | **Jenis error**: `timeout`, `rate_limit`, `auth`, `provider`. Rate limit naik = kita kena batas provider; auth naik = API key salah. |
| Chat messages (last 24h) | `sum(increase(chat_messages_sent_total[24h]))` | Aktivitas chat riil 24 jam (user + assistant pesan disimpan). |
| Token estimation error \|actual−estimated\| (p50/p95) | `histogram_quantile(0.5/0.95, sum(rate(llm_token_estimation_abs_error_bucket[5m])) by (le))` | **Besar selisih** antara estimasi input token (tokenizer lokal) vs aktual (dari usage provider), diambil nilai absolut. p50 = setengah request bedanya di bawah nilai ini. |
| Avg token estimation error (actual−estimated, 5m) | `sum(rate(llm_token_estimation_error_sum[5m])) / sum(rate(llm_token_estimation_error_count[5m]))` | **Arah bias** estimasi. Positif = rata-rata estimasi lebih kecil dari aktual (undercount), negatif = overcount. |

**Cara baca estimation error (penting):**
- Ada **dua** metrik: `llm_token_estimation_error` (bertanda, bisa negatif) dan
  `llm_token_estimation_abs_error` (nilai absolut, selalu ≥ 0).
- `histogram_quantile` **tidak valid untuk data negatif** (Prometheus menganggap
  semua observasi ≥ 0) — jadi panel p50/p95 memakai metrik **absolut**.
- Untuk lihat arah bias (undercount/overcount), pakai panel **rata-rata** yang
  memakai metrik bertanda.
- Nilai ~0 = estimasi tokenizer lokal akurat. Konsisten positif = estimasi
  selalu lebih kecil (mis. `CHAT_TOKEN_CORRECTION` kurang), negatif = kebalikannya.

> **Catatan biaya**: kita belum punya harga per model (price registry ditunda).
> `llm_input/output_tokens_total` adalah proksi — kalau mau angka rupiah/dollar,
> tinggal kalikan dengan harga model (pekerjaan berikutnya).

---

## 4. Dashboard: RAG

**Tujuan:** "Fitur RAG kita bekerja dan berguna?" — visibility untuk subsistem
terbaru.

| Panel | Query | Cerita |
|-------|-------|--------|
| Documents uploaded (last 24h) | `sum(increase(rag_documents_total[24h]))` | Berapa dokumen masuk (24 jam). |
| Chunks indexed (last 24h) | `sum(increase(rag_chunks_total[24h]))` | Berapa potongan teks di-embed + disimpan (24 jam). **Naik = dokumen besar.** |
| Retrieval hit rate (%) | `hits / (hits + misses) * 100` | **Seberapa sering pencarian menemukan chunk.** Rendah = embedding/dokumen kurang relevan, atau pertanyaan di luar topik dokumen. |
| Retrieval rate | `sum(rate(rag_retrieval_duration_seconds_count[5m])) by (top_k)` | Frekuensi retrieval per request chat (dipisah `top_k`). |
| Retrieval P95 duration | `histogram_quantile(0.95, sum(rate(rag_retrieval_duration_seconds_bucket[5m])) by (le))` | Seberapa cepat cari chunk (embed query + cosine search). Lambat = embedding API/DB. |
| Retrieval hits vs misses | `sum(rate(rag_retrieval_hits_total[5m]))` + `sum(rate(rag_retrieval_misses_total[5m]))` | Overlay langsung: kapan search kosong. |

**Cara baca:** hit rate rendah + hits/misses berdekatan → pertanyaan user sering
tidak nyambung dengan isi dokumen. Bukan bug, tapi sinyal kualitas data
(chunking terlalu kecil, dokumen kurang relevan, atau pertanyaan di luar scope).

---

## 5. Kalau semua panel kosong — urutan cek

1. **`docker compose ps`** — semua service jalan?
2. **App jalan?** `curl -H "X-API-Key: <key>" localhost:8000/metrics` → ada output?
3. **Prometheus bisa scrape?** UI `localhost:9090` → Status → Targets → `ai-backend-v2` → **UP**?
4. **Dashboard pilih waktu yang benar?** Panel default `last 1h` — kalau tidak ada
   trafik di jam itu, panel kosong (bukan error).
5. **Sudah restart app setelah tambah metrik baru?** Metrik baru (`rag_*`,
   `llm_error_total`, `llm_token_estimation_abs_error`) hanya muncul setelah
   proses app di-restart.

---

## 6. Menambah metrik/dashboard baru (pola cepat)

1. **Metrik**: buat file di `app/core/metrics/` (pola `Counter`/`Histogram`/`Gauge`),
   lalu `.inc()`/`.observe()` di titik yang relevan.
2. **Dashboard**: salin JSON panel dari dashboard yang ada (mis. panel `stat` atau
   `timeseries`), ganti `expr`-nya. Simpan di
   `deploy/grafana-provisioning/dashboards/`.
3. `docker compose restart grafana` → dashboard muncul.
4. **Restart app** → metrik mulai terisi.
5. **Update dokumen ini** (tabel panel) supaya tetap sinkron dengan dashboard.

Aturan label Prometheus: pilih label yang **terbatas jumlah nilainya**
(`model`, `status`, `error_type`). Jangan pakai label yang unik per-request
(mis. conversation_id) — itu bikin kardinalitas meledak dan Prometheus lemot.
