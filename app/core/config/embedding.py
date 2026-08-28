from pydantic import BaseModel


class EmbeddingSettings(BaseModel):
    """Config embedding via API lokal (Ollama, OpenAI-compatible).

    DeepSeek (provider chat) tidak punya endpoint embedding, dan kita tidak
    punya API key OpenAI → embedding lokal pakai Ollama (`/api/embed`).
    """
    base_url: str
    model: str
    dim: int