from openai import AsyncOpenAI

from app.core.config.embedding import EmbeddingSettings


class OpenAIEmbeddingClient:
    """Embedding via OpenAI API (`text-embedding-3-small`).

    AsyncOpenAI menangani retry & timeout sendiri; hasilnya list vektor sesuai
    urutan input. `base_url` opsional untuk endpoint OpenAI-compatible.
    """

    def __init__(
        self,
        settings: EmbeddingSettings,
    ):
        self._settings = settings
        client_kwargs: dict = {"api_key": settings.api_key}

        # SDK OpenAI butuh base_url dengan path /v1 (mis. https://api.openai.com/v1).
        # Di .env kita menulis tanpa /v1 (konsisten dengan CHAT_BASE_URL) — tambahkan.
        if settings.base_url:
            base_url = settings.base_url.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            client_kwargs["base_url"] = base_url

        self._client = AsyncOpenAI(**client_kwargs)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._settings.model,
            input=texts,
        )

        return [item.embedding for item in response.data]
