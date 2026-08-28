from pydantic import BaseModel


class RedisSettings(BaseModel):
    url: str