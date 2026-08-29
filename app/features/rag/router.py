from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.core.exceptions.business import BusinessException
from app.core.exceptions.error_codes import ErrorCode
from app.features.auth.model import User
from app.features.rag.dependencies import get_rag_service
from app.features.rag.schemas import (
    DocumentResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
)
from app.features.rag.service import RagService

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    req: DocumentUploadRequest,
    user: User = Depends(get_current_user),
    service: RagService = Depends(get_rag_service),
):
    document_id = await service.upload_document(
        user_id=user.id,
        title=req.title,
        content=req.content,
    )
    return DocumentUploadResponse(document_id=document_id)


@router.get("/documents/{id}", response_model=DocumentResponse)
async def get_document(
    id: int,
    user: User = Depends(get_current_user),
    service: RagService = Depends(get_rag_service),
):
    document = await service.get_document(document_id=id, user_id=user.id)

    if document is None:
        raise BusinessException(
            message=f"Document with id {id} not found.",
            code=ErrorCode.VALIDATION_ERROR,
            status_code=404,
        )

    return DocumentResponse(
        id=document.id,
        user_id=document.user_id,
        title=document.title,
        created_at=document.created_at,
    )
