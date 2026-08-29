from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.business import BusinessException
from app.core.exceptions.error_codes import ErrorCode
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

        [query_embedding] = await self.embedding_client.embed([question])

        return await self.repository.search_chunks(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )
