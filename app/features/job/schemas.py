from datetime import datetime

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    type: str = Field(..., description="Job type, resolve ke task function di registry")
    payload: dict = Field(default_factory=dict, description="Input job")


class JobResponse(BaseModel):
    id: int
    type: str
    status: str
    payload: dict
    result: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None