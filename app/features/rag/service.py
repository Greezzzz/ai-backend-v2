import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.business import BusinessException
from app.core.exceptions.error_codes import ErrorCode
from app.core.metrics.rag import (
    rag_chunks_total,
    rag_documents_total,
    rag_retrieval_duration_seconds,
    rag_retrieval_hits_total,
    rag_retrieval_misses_total,
)
from app.features.rag.chunking import chunk_text
from app.features.rag.model import Document, DocumentChunk
from app.features.rag.repository import RAGRepository
from app.llm.openai_embedding_client import OpenAIEmbeddingClient


class RagService:

    def __init__(
        self,
        session: AsyncSession,
        embedding_client: OpenAIEmbeddingClient,
    ):
        self.session = session
        self.repository = RAGRepository(session)
        self.embedding_client = embedding_client

    async def upload_document(
        self,
        user_id: int,
        title: str,
        content: str,
    ) -> int:
        chunks = chunk_text(content)

        if not chunks:
            raise BusinessException(
                message="Document content is empty.",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )

        embeddings = await self.embedding_client.embed(chunks)

        document = await self.repository.create_document(
            user_id=user_id,
            title=title,
            content=content,
        )
        await self.repository.create_chunks(
            document_id=document.id,
            chunks=chunks,
            embeddings=embeddings,
        )
        await self.session.commit()

        rag_documents_total.labels(model=self.embedding_client._settings.model).inc()
        rag_chunks_total.inc(len(chunks))

        return document.id

    async def get_document(
        self,
        document_id: int,
        user_id: int,
    ) -> Document | None:
        return await self.repository.get_document(document_id, user_id)

    async def retrieve(
        self,
        user_id: int,
        document_id: int,
        question: str,
        top_k: int = 3,
    ) -> list[DocumentChunk]:
        """Embed pertanyaan → cari chunk paling relevan milik user."""
        if await self.repository.get_document(document_id, user_id) is None:
            raise BusinessException(
                message=f"Document with id {document_id} not found.",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=404,
            )

        start = time.monotonic()

        [query_embedding] = await self.embedding_client.embed([question])

        result = await self.repository.search_chunks(
            user_id=user_id,
            document_id=document_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

        rag_retrieval_duration_seconds.labels(top_k=top_k).observe(
            time.monotonic() - start
        )
        rag_retrieval_hits_total.inc(len(result))

        if len(result) == 0:
            rag_retrieval_misses_total.inc()

        return result
