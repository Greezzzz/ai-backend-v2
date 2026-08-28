import httpx

from app.core.config.embedding import EmbeddingSettings
from app.core.exceptions.llm import (
    LLMProviderException,
    LLMTimeoutException,
)
from app.core.logging.logger import logger
from app.core.retry.executor import RetryExecutor


class OllamaEmbeddingClient:
    """Embedding lokal via Ollama (`/api/embed`).

    Gratis & tanpa API key — DeepSeek tidak punya endpoint embedding dan
    kita tidak punya key OpenAI. Model default: nomic-embed-text (768 dim).
    """

    def __init__(
        self,
        http: httpx.AsyncClient,
        settings: EmbeddingSettings,
        retry_executor: RetryExecutor,
    ):
        self._http = http
        self._settings = settings
        self._retry = retry_executor

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {
            "model": self._settings.model,
            "input": texts,
        }

        try:
            data = await self._retry.execute(
                lambda: self._post(payload),
                operation_name="ollama_embed",
            )
        except httpx.TimeoutException as e:
            raise LLMTimeoutException(details={"model": self._settings.model}) from e
        except httpx.HTTPStatusError as e:
            raise LLMProviderException(
                details={
                    "model": self._settings.model,
                    "status": e.response.status_code,
                }
            ) from e

        embeddings = data.get("embeddings", [])

        if len(embeddings) != len(texts):
            logger.warning(
                "embed_mismatch",
                expected=len(texts),
                got=len(embeddings),
            )

        return [list(vec) for vec in embeddings]

    async def _post(self, payload: dict) -> dict:
        response = await self._http.post(
            url=f"{self._settings.base_url}/api/embed",
            json=payload,
        )

        response.raise_for_status()

        return response.json()