from pydantic import BaseModel

class RateLimiterSettings(BaseModel):
    capacity: int
    refill_per_second: float
    acquire_timeout: float