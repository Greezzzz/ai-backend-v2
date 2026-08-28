import asyncio
from collections.abc import Callable

from app.core.database.config import DatabaseSettings
from app.core.database.engine import create_engine
from app.core.database.session import create_session_factory
from app.features.job.model import Job
from app.features.job.repository import JobRepository


def _run_job(job_id: int, payload: dict, process: Callable[[dict], str]) -> None:
    """Template lifecycle job: DB sebagai sumber kebenaran status.

    Buka session DB → mark_running → jalankan proses → mark_succeeded.
    Error → mark_failed. Dipakai semua task worker (echo, nanti ingestion).
    """
    engine = create_engine(DatabaseSettings())
    session_factory = create_session_factory(engine)

    async def _do() -> None:
        async with session_factory() as session:
            repo = JobRepository(session)
            job = await repo.get_by_id(job_id)

            if job is None:
                return

            job.mark_running()
            await session.commit()

            try:
                result = process(payload)
                job.mark_succeeded(result)
            except Exception as e:  # noqa: BLE001
                job.mark_failed(str(e) or type(e).__name__)

            await session.commit()

    try:
        asyncio.run(_do())
    finally:
        asyncio.run(engine.dispose())


def echo_job(job_id: int, payload: dict) -> None:
    """Job generik: echo payload sebagai hasil — bukti lifecycle queue worker."""

    def _process(payload: dict) -> str:
        text = payload.get("text", "")
        # Simulasi kerja asinkron kecil (bukan blokir); bukti queue berjalan.
        return f"echo: {text}"

    _run_job(job_id, payload, _process)


JOB_TASKS: dict[str, Callable[[int, dict], None]] = {
    "echo": echo_job,
}