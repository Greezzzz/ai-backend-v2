# Observability — Satu Cerita: Trace, Metrik, Log di ai-backend-v2

Dokumen ini menjelaskan stack observability project **sebagai satu kesatuan** —
bukan tiga tool terpisah. Satu request yang masuk ke app kita bisa dilihat dari
3 sudut, dan ketiganya nyambung lewat **trace id yang sama**:

| Sudut pandang | Menjawab | Tool | UI |
|---------------|----------|------|-----|
| **Trace** | "Di dalam satu request, panggilan apa saja yang terjadi, urutannya, dan lambatnya di mana?" | OpenTelemetry → Jaeger | `localhost:16686` |
| **Metrik** | "Secara agregat, sehat nggak? error naik? token boros?" | prometheus_client → Prometheus | `localhost:9090` |
| **Log** | "Detail kejadian per request (apa nilai variabelnya, errornya apa)" | logging JSON → stdout | terminal / `docker logs` |

Acuan utama dokumen ini adalah **file-file nyata di repo ini** — setiap bagian
nyambung ke path yang bisa langsung dibuka.

---

## 1. Mental model: 3 jalur, 1 trace id

```
                        ┌─────────────── satu request ───────────────┐
                        │                                             │
  HTTP request masuk    │                                             │
      │                 ▼                                             │
   TraceMiddleware ──► span OTel (server) ──► OTLP HTTP ──► Jaeger    │  TRACE
   (app/middleware/trace.py)                 (4318)                   │
      │                                                                 │
      ▼                                                                 │
   Handler / UseCase                                                     │
      │  ┌─ logger.info("event", ...) ──► stdout JSON (bawa trace_id)   │  LOG
      │  └─ metrik.inc() / .observe() ──► /metrics                      │
      │                                                    │ scrape     │  METRIK
      ▼                                                    ▼            │
   Panggilan LLM ──► child span (llm.openai.chat)    Prometheus         │
   (httpx instrumented)                                 │ query        │
                                                       ▼                │
                                                  Grafana               │
                        └────────────────────────────────────────────────┘
```

**Kenapa satu trace id?** Karena `AppLogger` (di `app/core/logging/app_logger.py`)
otomatis menulis `trace_id` dari `get_trace_id()` (`app/core/context/trace.py`)
ke setiap log. Fungsi itu prioritasnya:
1. **OTel span aktif** → trace id-nya (format 32 hex) — *sama persis dengan yang
   muncul di Jaeger*.
2. Fallback ContextVar → trace id custom.

Artinya: **cari trace id di log, paste di Jaeger, ketemu seluruh span request
itu.** Header respons `X-Trace-Id` juga membawa trace id yang sama, jadi klien
bisa mengkorelasikan.

> WSL note: env var inline (`OTEL_ENABLED=true python ...`) tidak tembus ke
> Python Windows — set lewat `.env` atau `os.environ`.

---

## 2. TRACE — OpenTelemetry → Jaeger

### 2.1 Alur

```
app/main.py
  HTTPXClientInstrumentor().instrument()   # semua panggilan httpx = child span
  FastAPIInstrumentor.instrument_app(app)  # 1 span server per request

app/core/lifespan.py
  setup_otel(settings.otel)                # pasang TracerProvider

app/core/observability/llm.py
  instrument_llm_call(...)                 # span manual utk panggilan LLM
```

### 2.2 Setup (file nyata)

| Hal | File | Catatan |
|-----|------|---------|
| Inisialisasi OTel | `app/core/observability/otel.py` | `OTEL_ENABLED=true` → OTLP ke collector; selain itu → console (dev) |
| Config | `app/core/config/otel.py` | `exporter_otlp_endpoint` default `http://localhost:4318`, `service_name=ai-backend-v2` |
| Instrumentasi otomatis | `app/main.py` | httpx + FastAPI |
| Span LLM manual | `app/core/observability/llm.py` | atribut: provider/model/token usage/`llm.estimated.input_tokens` |
| Trace id ter-unifikasi | `app/core/context/trace.py`, `app/middleware/trace.py` | log == header == Jaeger |
| Service Jaeger | `docker-compose.yml` (`jaeger`) + `deploy/jaeger-config.yml` | image `jaegertracing/jaeger`, OTLP HTTP `4318`, UI `16686` |

**Cara menjalankan:**
1. `docker compose up -d jaeger`
2. Di `.env`: `OTEL_ENABLED=true` (endpoint default `http://localhost:4318` sudah benar).
3. Restart app → kirim request → buka `localhost:16686`, cari service
   `ai-backend-v2`.

### 2.3 Span yang ada

| Span | Dibuat di | Isi penting |
|------|-----------|-------------|
| Server (per request) | `FastAPIInstrumentor` | method, route, status |
| `llm.{provider}.{chat\|stream}` | `instrument_llm_call` | `llm.model`, `llm.provider`, `gen_ai.usage.input_tokens` (aktual), `gen_ai.usage.output_tokens`, `llm.estimated.input_tokens` (estimasi tokenizer lokal) |
| HTTP keluar (ke provider LLM) | `HTTPXClientInstrumentor` | otomatis, jadi child span di dalam span LLM |

**Kegunaan praktis:** bandingkan `gen_ai.usage.input_tokens` (aktual dari
provider) vs `llm.estimated.input_tokens` (estimasi tokenizer lokal) per request
— untuk memeriksa akurasi `CHAT_TOKEN_CORRECTION`.

---

## 3. METRIK — prometheus_client → Prometheus → Grafana

### 3.1 Alur

```
App (Python)                        Prometheus (container)        Grafana (container)
  app/core/metrics/*.py                scrape /metrics tiap 15s      query PromQL
  .inc() / .observe() / .set()   ──►   simpan time series      ──►   dashboard/panel
  endpoint /metrics (X-API-Key)
```

- **App** expose `/metrics` (format Prometheus, dilindungi header `X-API-Key`).
- **Prometheus** scrape tiap 15 detik (`deploy/prometheus.yml`), simpan history,
  bisa di-query. UI `localhost:9090`.
- **Grafana** cuma visualisasi — baca dari Prometheus (data source
  auto-provision), tidak menyimpan sendiri. UI `localhost:3000` (admin/admin dev).

### 3.2 Cara bikin metrik baru (pola project)

Semua metrik didefinisikan di `app/core/metrics/` — satu file per domain:

1. Buat objek metrik (pilih tipe):
   ```python
   # app/core/metrics/chat.py (contoh nyata)
   from prometheus_client import Counter

   chat_messages_sent_total = Counter(
       "chat_messages_sent_total",        # nama — unik global
       "Total number of chat messages persisted",  # help
       ["role"],                          # label (HATI-HATI: lihat aturan di bawah)
   )
   ```
2. Di titik yang relevan di kode, panggil:
   ```python
   chat_messages_sent_total.labels(role="user").inc()
   # Histogram: .observe(durasi)  |  Gauge: .set(nilai)
   ```
3. **Restart app** → metrik muncul di `/metrics` → panel Grafana bisa pakai.

**Aturan emas label Prometheus:** pakai label yang **nilainya terbatas**
(`model`, `status`, `error_type`, `role`). **JANGAN** pakai label unik per
request (mis. `conversation_id`) — itu high-cardinality, bikin Prometheus
boros memori & lemot. Detail per request bukan tempatnya metrik; itu kerjaan
trace (Jaeger) atau log.

### 3.3 Tipe metrik

| Tipe | Dipakai buat | Method |
|------|--------------|--------|
| `Counter` | "Berapa kali / berapa total" (hanya naik) | `.inc()`, `.inc(n)` |
| `Histogram` | Distribusi durasi/ukuran (bisa dihitung quantile) | `.observe(n)` |
| `Gauge` | Nilai yang bisa naik-turun (mis. token tersedia) | `.set(n)` |

---

## 4. GRAFANA — connect & dashboard

### 4.1 Data source

`deploy/grafana-provisioning/datasources/prometheus.yml`:
```yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090   # nama service docker-compose
    isDefault: true
    access: proxy
```
Grafana container di-mount folder provisioning (`docker-compose.yml`), jadi data
source & dashboard ter-registrasi otomatis saat container start.

### 4.2 Dashboard auto-provision

Dashboard berupa file JSON di `deploy/grafana-provisioning/dashboards/`,
di-mount ke `/var/lib/grafana/dashboards`, dan didaftarkan lewat
`deploy/grafana-provisioning/dashboards/dashboards.yml` (provider `type: file`).

| Dashboard | File | Fokus |
|-----------|------|-------|
| API Overview | `api-overview.json` | Request rate, error rate, latency per path |
| LLM & Tokens | `llm-tokens.json` | Request LLM, token usage, token estimation error |
| Health & Reliability | `health.json` | Scrape up, retry, rate limiter |
| RAG | `rag.json` | Dokumen, chunk, retrieval hit rate |

**Cara edit:** ubah JSON → `docker compose restart grafana` → dashboard
ke-sync (provider `updateIntervalSeconds`).

---

## 5. Referensi metrik project

### 5.1 HTTP (`app/core/metrics/http.py`)

| Metrik | Tipe | Label | Query contoh | Panel |
|--------|------|-------|--------------|-------|
| `http_request_total` | Counter | method, path, status_code | `sum(rate(http_request_total[5m])) by (path)` | Request rate / error rate |
| `http_request_duration_seconds` | Histogram | method, path | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | P95 latency |

### 5.2 LLM (`app/core/metrics/llm.py`)

| Metrik | Tipe | Label | Query contoh | Panel |
|--------|------|-------|--------------|-------|
| `llm_request_total` | Counter | model, status, provider | `sum(rate(llm_request_total[5m])) by (status)` | LLM requests by status |
| `llm_request_duration_seconds` | Histogram | model, provider | `histogram_quantile(...)` | LLM P95 latency |
| `llm_input_tokens_total` | Counter | model, provider | `sum(rate(llm_input_tokens_total[5m]))` | Token usage rate (in) |
| `llm_output_tokens_total` | Counter | model, provider | `sum(rate(llm_output_tokens_total[5m]))` | Token usage rate (out) |
| `llm_error_total` | Counter | error_type, model, provider | `sum(rate(llm_error_total[5m])) by (error_type)` | LLM errors by type |
| `llm_token_estimation_error` | Histogram | model, provider | `histogram_quantile(0.95, sum(rate(llm_token_estimation_error_bucket[5m])) by (le))` | Token estimation error quantiles |

> `error_type` bernilai: `timeout`, `rate_limit`, `auth`, `provider`.
> `llm_token_estimation_error` = **aktual − estimasi**; positif = undercount.

### 5.3 Chat (`app/core/metrics/chat.py`)

| Metrik | Tipe | Label | Query contoh | Panel |
|--------|------|-------|--------------|-------|
| `chat_messages_sent_total` | Counter | role | `sum(increase(chat_messages_sent_total[24h]))` | Chat messages |

### 5.4 RAG (`app/core/metrics/rag.py`)

| Metrik | Tipe | Label | Query contoh | Panel |
|--------|------|-------|--------------|-------|
| `rag_documents_total` | Counter | model | `sum(increase(rag_documents_total[1h]))` | Documents uploaded |
| `rag_chunks_total` | Counter | — | `sum(increase(rag_chunks_total[1h]))` | Chunks indexed |
| `rag_retrieval_duration_seconds` | Histogram | top_k | `histogram_quantile(...)` | Retrieval P95 duration |
| `rag_retrieval_hits_total` | Counter | — | `hits/(hits+misses)` | Retrieval hit rate |
| `rag_retrieval_misses_total` | Counter | — | `misses/(hits+misses)` | Retrieval hit rate |

### 5.5 Retry & rate limiter

| Metrik | Tipe | Label | File |
|--------|------|-------|------|
| `retry_attempts_total` | Counter | attempt, operation | `app/core/metrics/retry.py` |
| `retry_exhausted_total` | Counter | operation, exception_type | `app/core/metrics/retry.py` |
| `rate_limiter_tokens_available` | Gauge | — | `app/core/metrics/rate_limiter.py` |

---

## 6. Infra lokal (docker-compose) — peta service

Semua di `docker-compose.yml`:

| Service | Image | Port host | Dipakai buat |
|---------|-------|-----------|--------------|
| `redis` | redis:7-alpine | 6379 | session auth, RQ queue |
| `postgres` | pgvector/pgvector:pg16 | **5433**→5432 | DB utama + pgvector (RAG) |
| `jaeger` | jaegertracing/jaeger | 16686 (UI), 4318 (OTLP HTTP), 4317 (gRPC) | tracing |
| `prometheus` | prom/prometheus | 9090 | simpan metrik |
| `grafana` | grafana/grafana | 3000 | dashboard |

Config Prometheus: `deploy/prometheus.yml`. App jalan di **host** (uvicorn
Windows) → target `host.docker.internal:8000`, kirim header `X-API-Key` yang
**harus sama** dengan `API_KEY` di `.env`.

> Catatan: field header di Prometheus 3.x adalah `http_headers` (bukan
> `http_config`/`headers`).

---

## 7. Troubleshooting

### Semua panel Grafana kosong
Urutan cek:
1. `docker compose ps` — semua service jalan?
2. App jalan? `curl -H "X-API-Key: <key>" localhost:8000/metrics` → ada output?
3. Prometheus bisa scrape? UI `localhost:9090` → Status → Targets →
   `ai-backend-v2` → **UP**?
4. Waktu dashboard benar? Panel default `last 1h` — kalau tidak ada trafik, panel
   kosong (bukan error).
5. Sudah restart app setelah tambah metrik baru? Metrik baru baru muncul setelah
   proses app di-restart.

### Trace tidak muncul di Jaeger
1. `.env` `OTEL_ENABLED=true`? (bukan inline env di WSL)
2. `docker compose up -d jaeger` jalan?
3. Cari service `ai-backend-v2` (bukan default).
4. Kalau pakai `TestClient`/unit test — lifespan tidak jalan, jadi tidak ada OTel.

### Log tidak muncul / tidak ada trace_id
1. `setup_logging()` dipanggil di lifespan — kalau app tidak lewat lifespan,
   format log default (bukan JSON).
2. `trace_id` bernilai `null` kalau tidak ada span OTel aktif & ContextVar kosong.

### Metrik muncul ganda / aneh setelah ganti kode
- Metrik Prometheus **tidak bisa di-unregister** dengan mudah; kalau define ulang
  dengan nama sama di proses yang sama → error. Restart proses app kalau ganti
  definisi metrik.

---

## 8. Ringkasan alur

```
TRACE  : request → FastAPIInstrumentor (server span) → instrument_llm_call
         (LLM span) → HTTPXClientInstrumentor (http span) → OTLP → Jaeger
METRIK : app/core/metrics/*.py → .inc/.observe → /metrics → scrape Prometheus
         (15s) → query Grafana
LOG    : AppLogger → JsonFormatter (bawa trace_id) → stdout
```

**Korelasi lintas tool:** `trace_id` yang sama ada di log (field `trace_id`),
header respons (`X-Trace-Id`), dan Jaeger. Metrik tidak punya trace id — itu
agregat, bukan per-request.
