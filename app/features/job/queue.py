from redis import Redis
from rq import Queue

from app.core.config.settings import Settings, get_settings
from app.features.job.tasks import JOB_TASKS

QUEUE_NAME = "ai-jobs"

# RQ butuh koneksi redis sync (app pakai redis.asyncio untuk hal lain).
_redis_conn: Redis | None = None


def _get_sync_redis(settings: Settings) -> Redis:
    global _redis_conn

    if _redis_conn is None:
        _redis_conn = Redis.from_url(settings.redis.url)

    return _redis_conn


def get_job_queue(settings: Settings = get_settings()) -> Queue:
    return Queue(QUEUE_NAME, connection=_get_sync_redis(settings))


def enqueue_job(type_: str, job_id: int, payload: dict, settings: Settings = get_settings()) -> None:
    """Taruh job ke antrian RQ. Task function di-resolve dari registry.

    KeyError (type tidak dikenal) dibiarkan → usecase validasi type
    sebelum enqueue; ini jaring pengaman terakhir.
    """
    task = JOB_TASKS[type_]
    get_job_queue(settings).enqueue(task, job_id, payload)