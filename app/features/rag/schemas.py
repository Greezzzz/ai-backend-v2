from datetime import datetime

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, description="Isi dokumen teks")


class DocumentUploadResponse(BaseModel):
    document_id: int


class DocumentResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
