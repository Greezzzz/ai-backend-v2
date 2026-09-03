# docs/learn — Belajar ai-backend-v2

Kumpulan dokumen untuk **memahami project ini dari nol** — bukan dokumentasi
API, tapi penjelasan cara kerja, alur data, dan infrastruktur observability,
selalu dengan acuan ke file nyata di repo.

## Urutan baca

| Urutan | File | Isi | Buat apa |
|--------|------|-----|----------|
| 1 | `learn.md` | Cara kerja sistem: layer, alur data, request lifecycle, tiap subsistem | Paham "gimana aplikasi ini bekerja" dari request masuk sampai keluar |
| 2 | `observability.md` | Satu cerita observability project: tracing (OTel/Jaeger), metrics (Prometheus), visualisasi (Grafana), setup, referensi metrik | Paham & bisa pakai stack observability kita |
| 3 | `grafana.md` | Cara baca tiap dashboard & metrik: "angka ini cerita apa" | Lancar waktu buka Grafana / debugging |

> Path di dalam dokumen (mis. `app/features/chat/usecase.py`) relatif ke **root
> repo**, bukan ke folder ini — biar gampang langsung dibuka.

## Prasyarat

- Infra observability jalan: `docker compose up -d` (postgres, redis, prometheus,
  grafana, jaeger).
- App jalan di host: `uv run python -m uvicorn app.main:app --reload`.
