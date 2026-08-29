from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.features.rag.service import RagService
from app.llm.embedding_dependencies import get_embedding_client
from app.llm.openai_embedding_client import OpenAIEmbeddingClient


def get_rag_service(
    session: AsyncSession = Depends(get_db),
    embedding_client: OpenAIEmbeddingClient = Depends(get_embedding_client),
) -> RagService:
    return RagService(
        session=session,
        embedding_client=embedding_client,
    )
