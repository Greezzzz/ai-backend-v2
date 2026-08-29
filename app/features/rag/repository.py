from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.rag.model import Document, DocumentChunk


class RAGRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self,
        user_id: int,
        title: str,
        content: str,
    ) -> Document:
        document = Document(user_id=user_id, title=title, content=content)
        self.session.add(document)
        await self.session.flush()
        return document

    async def create_chunks(
        self,
        document_id: int,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
            self.session.add(
                DocumentChunk(
                    document_id=document_id,
                    index=index,
                    content=content,
                    embedding=embedding,
                )
            )

    async def get_document(
        self,
        document_id: int,
        user_id: int,
    ) -> Document | None:
        result = await self.session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def search_chunks(
        self,
        user_id: int,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[DocumentChunk]:
        """Cari chunk paling relevan via cosine distance pgvector (`<=>`).

        Hanya chunk milik user (join Document + filter user_id).
        """
        result = await self.session.execute(
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.user_id == user_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        return list(result.scalars().all())
