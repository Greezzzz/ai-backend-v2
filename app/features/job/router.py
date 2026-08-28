from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.features.job.dependencies import get_job_usecase
from app.features.job.schemas import JobCreateRequest, JobResponse
from app.features.job.usecase import JobUseCase

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=JobResponse, response_model_exclude_none=True, status_code=201)
async def create_job(req: JobCreateRequest, usecase: JobUseCase = Depends(get_job_usecase)):
    job = await usecase.create_job(type_=req.type, payload=req.payload)
    return job


@router.get("/{id}", response_model=JobResponse, response_model_exclude_none=True)
async def get_job(id: int, usecase: JobUseCase = Depends(get_job_usecase)):
    return await usecase.get_job(job_id=id)