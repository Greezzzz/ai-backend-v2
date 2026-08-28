"""Entry point worker RQ: `python -m app.jobs.worker`.

Menjalankan RQ worker untuk queue "ai-jobs". Task didaftarkan di
`JOB_TASKS` (app/features/job/tasks.py) dan di-pick oleh RQ berdasarkan
nama modul + fungsi saat enqueue.

Kenapa `SimpleWorker`, bukan `Worker`:
- `Worker` & `SpawnWorker` butuh `os.fork` / `os.wait4` yang TIDAK ada di
  Windows. Environment kita (belajar) berjalan di WSL + python Windows,
  jadi satu-satunya yang jalan adalah `SimpleWorker` (eksekusi job di
  proses yang sama, tanpa fork).
- Trade-off: tidak ada isolasi proses antar job (satu job crash bisa
  menimpa worker). Cukup untuk belajar/dev; ganti ke `Worker` (fork, lebih
  aman & efisien) saat deploy Linux (Fase J).
"""

from redis import Redis
from rq import SimpleWorker

from app.core.config.settings import get_settings
from app.features.job.queue import QUEUE_NAME
from app.features.job.tasks import JOB_TASKS  # noqa: F401  (register task functions)


def main() -> None:
    settings = get_settings()
    connection = Redis.from_url(settings.redis.url)

    worker = SimpleWorker(
        [QUEUE_NAME],
        connection=connection,
    )

    worker.work()


if __name__ == "__main__":
    main()