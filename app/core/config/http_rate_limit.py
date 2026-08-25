from pydantic import BaseModel


class HttpRateLimitSettings(BaseModel):
    requests_per_minute: int
