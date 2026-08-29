from pydantic import BaseModel


class EmbeddingSettings(BaseModel):
    """Config embedding OpenAI.

    DeepSeek (provider chat) tidak punya endpoint embedding → embedding pakai
    OpenAI (text-embedding-3-small, 1536 dim). `base_url` opsional: kosongkan
    untuk api.openai.com default, atau isi endpoint OpenAI-compatible (mis.
    proxy / server lokal).
    """
    api_key: str
    model: str = "text-embedding-3-small"
    dim: int = 1536
    base_url: str | None = None
