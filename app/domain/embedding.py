from typing import Protocol


class EmbeddingProtocol(Protocol):
    """Abstraksi embedding provider — menghasilkan vektor dari teks."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
