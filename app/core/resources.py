from dataclasses import dataclass
import httpx

from app.core.config.settings import Settings


@dataclass
class Resources:
    settings: Settings
    http_client: httpx.AsyncClient