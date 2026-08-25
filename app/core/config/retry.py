from pydantic import BaseModel

class RetrySettings(BaseModel):
    max_attempt: int
    base_delay: float
    multiplier: float
    max_delay: float
    enable_jitter: bool = True