from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.job.model import Job


class JobRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        type_: str,
        payload: dict,
    ) -> Job:
        job = Job(type=type_, payload=payload)

        self.session.add(job)

        await self.session.flush()

        return job

    async def get_by_id(
        self,
        job_id: int,
    ) -> Job | None:
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )

        return result.scalar_one_or_none()