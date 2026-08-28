from fastapi import Depends

from app.core.config.dependencies import get_resources
from app.core.retry.executor import RetryExecutor
from app.llm.ollama_embedding_client import OllamaEmbeddingClient
from app.provider.openai.dependencies import get_retry_executor


def get_ollama_embedding_client(
    resources=Depends(get_resources),
    retry: RetryExecutor = Depends(get_retry_executor),
) -> OllamaEmbeddingClient:
    return OllamaEmbeddingClient(
        http=resources.http_client,
        settings=resources.settings.embedding,
        retry_executor=retry,
    )
