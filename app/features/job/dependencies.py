from collections.abc import Callable

from fastapi import Depends

from app.api.dependencies.database import get_db
from app.core.config.settings import Settings, get_settings
from app.features.job.queue import enqueue_job
from app.features.job.usecase import JobUseCase


def get_enqueue_job(
    settings: Settings = Depends(get_settings),
) -> Callable[[str, int, dict], None]:
    """Resolver untuk fungsi enqueue. Dipisah supaya test bisa override
    dengan fake queue (tanpa Redis beneran)."""
    def _enqueue(type_: str, job_id: int, payload: dict) -> None:
        enqueue_job(type_, job_id, payload, settings=settings)

    return _enqueue


async def get_job_usecase(
    session=Depends(get_db),
    enqueue: Callable[[str, int, dict], None] = Depends(get_enqueue_job),
) -> JobUseCase:
    return JobUseCase(
        session=session,
        enqueue=enqueue,
    )