from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.business import BusinessException
from app.core.exceptions.error_codes import ErrorCode
from app.features.job.model import Job
from app.features.job.repository import JobRepository
from app.features.job.tasks import JOB_TASKS


class JobUseCase:

    def __init__(
        self,
        session: AsyncSession,
        enqueue: Callable[[str, int, dict], None],
    ):
        self.session = session
        self.repository = JobRepository(session)
        self.enqueue = enqueue

    async def create_job(self, type_: str, payload: dict) -> Job:
        if type_ not in JOB_TASKS:
            raise BusinessException(
                message=f"Unknown job type: {type_}",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )

        job = await self.repository.create(type_, payload)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        self.enqueue(type_, job.id, payload)

        return job

    async def get_job(self, job_id: int) -> Job:
        job = await self.repository.get_by_id(job_id)

        if job is None:
            raise BusinessException(
                message=f"Job with id {job_id} not found.",
                code=ErrorCode.JOB_NOT_FOUND,
                status_code=404,
            )

        return job