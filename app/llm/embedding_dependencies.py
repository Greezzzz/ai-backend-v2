from fastapi import Depends

from app.core.config.dependencies import get_resources
from app.core.resources import Resources
from app.llm.openai_embedding_client import OpenAIEmbeddingClient


def get_embedding_client(
    resources: Resources = Depends(get_resources),
) -> OpenAIEmbeddingClient:
    return OpenAIEmbeddingClient(
        settings=resources.settings.embedding,
    )
