from pydantic import BaseModel

from app.core.config.retry import RetrySettings


class OpenAISettings(BaseModel):
    api_key: str
    base_url: str
    http: HttpSettings
    chat: ChatSettings
    limit: LimitSettings
    retry: RetrySettings

class HttpSettings(BaseModel):
    connect: int
    write: int
    read: int
    pool: int

class ChatSettings(BaseModel):
    model: str
    temperature: float
    max_tokens: int

class LimitSettings(BaseModel):
    max_connections: int
    max_keepalive_connections: int
    keep_alive_expiry: int