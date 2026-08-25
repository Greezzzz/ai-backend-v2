from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.auth import ApiKeySettings, JwtSettings
from app.core.config.http_rate_limit import HttpRateLimitSettings
from app.core.config.openai import (
    ChatSettings,
    HttpSettings,
    LimitSettings,
    OpenAISettings,
)
from app.core.config.rate_limit import RateLimiterSettings
from app.core.config.retry import RetrySettings


class Settings(BaseSettings):

    openai_api_key: str
    openai_model: str
    openai_base_url: str
    openai_temp: float
    openai_max_token: int
    openai_conn_timeout: int
    openai_write_timeout: int
    openai_read_timeout: int
    openai_pool_timeout: int
    openai_max_connections: int
    openai_max_keepalive_connections: int
    openai_keep_alive_expiry: int
    openai_retry_max_attempt: int
    openai_retry_base_delay: float
    openai_retry_multiplier: float
    openai_retry_max_delay: float
    openai_retry_enable_jitter: bool
    openai_rate_limit_capacity: int
    openai_rate_limit_refill_per_second: float
    openai_rate_limit_acquire_timeout: float

    # Auth
    # Default hanya untuk dev/belajar; WAJIB diisi di .env untuk production.
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    api_key: str = "dev-api-key"

    # HTTP rate limit (per client)
    http_rate_limit_requests_per_minute: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def openai(self) -> OpenAISettings:
        return OpenAISettings(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
            chat= ChatSettings(
                max_tokens= self.openai_max_token,
                model=self.openai_model,
                temperature=self.openai_temp
            ),
            http=HttpSettings(
                connect=self.openai_conn_timeout,
                pool=self.openai_pool_timeout,
                write=self.openai_write_timeout,
                read=self.openai_read_timeout
            ),
            limit=LimitSettings(
                keep_alive_expiry= self.openai_keep_alive_expiry,
                max_keepalive_connections= self.openai_max_keepalive_connections,
                max_connections= self.openai_max_connections
            ),
            retry=RetrySettings(
                max_attempt=self.openai_retry_max_attempt,
                base_delay=self.openai_retry_base_delay,
                multiplier=self.openai_retry_multiplier,
                max_delay=self.openai_retry_max_delay,
                enable_jitter=self.openai_retry_enable_jitter
            )
        )

    @property
    def rate_limit(self) -> RateLimiterSettings:
        return RateLimiterSettings(
            capacity=self.openai_rate_limit_capacity,
            acquire_timeout=self.openai_rate_limit_acquire_timeout,
            refill_per_second=self.openai_rate_limit_refill_per_second
        )

    @property
    def jwt(self) -> JwtSettings:
        return JwtSettings(
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            access_token_expire_minutes=self.jwt_access_token_expire_minutes,
        )

    @property
    def api_key_settings(self) -> ApiKeySettings:
        return ApiKeySettings(key=self.api_key)

    @property
    def http_rate_limit(self) -> HttpRateLimitSettings:
        return HttpRateLimitSettings(
            requests_per_minute=self.http_rate_limit_requests_per_minute,
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()