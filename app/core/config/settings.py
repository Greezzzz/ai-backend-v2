from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.auth import ApiKeySettings, JwtSettings
from app.core.config.embedding import EmbeddingSettings
from app.core.config.http_rate_limit import HttpRateLimitSettings
from app.core.config.llm import (
    ChatSettings,
    HttpSettings,
    LimitSettings,
    LLMSettings,
)
from app.core.config.otel import OtelSettings
from app.core.config.rate_limit import RateLimiterSettings
from app.core.config.redis import RedisSettings
from app.core.config.retry import RetrySettings


class Settings(BaseSettings):

    chat_provider: str = "openai"
    chat_api_key: str
    chat_model: str
    chat_base_url: str
    chat_temp: float
    chat_context_window: int
    chat_max_output_tokens: int
    chat_token_correction: int
    chat_conn_timeout: int
    chat_write_timeout: int
    chat_read_timeout: int
    chat_stream_read_timeout: int = 300
    chat_pool_timeout: int
    chat_max_connections: int
    chat_max_keepalive_connections: int
    chat_keep_alive_expiry: int
    chat_retry_max_attempt: int
    chat_retry_base_delay: float
    chat_retry_multiplier: float
    chat_retry_max_delay: float
    chat_retry_enable_jitter: bool
    chat_rate_limit_capacity: int
    chat_rate_limit_refill_per_second: float
    chat_rate_limit_acquire_timeout: float

    # Auth
    # Default hanya untuk dev/belajar; WAJIB diisi di .env untuk production.
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 60
    api_key: str = "dev-api-key"

    # HTTP rate limit (per client)
    http_rate_limit_requests_per_minute: int

    # Redis (queue + cache). Default untuk dev; ganti sesuai environment.
    redis_url: str = "redis://localhost:6379/0"

    # Embedding (RAG) via Ollama lokal — gratis, tanpa API key.
    # DeepSeek tidak punya endpoint embedding & kita tidak punya key OpenAI.
    embedding_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # OpenTelemetry (tracing). Default mati; nyalakan dengan OTEL_ENABLED=true
    # dan arahkan OTEL_EXPORTER_OTLP_ENDPOINT ke collector (Jaeger, dsb).
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "ai-backend-v2"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def chat(self) -> LLMSettings:
        return LLMSettings(
            api_key=self.chat_api_key,
            base_url=self.chat_base_url,
            chat=ChatSettings(
                max_output_tokens=self.chat_max_output_tokens,
                model=self.chat_model,
                temperature=self.chat_temp,
            ),
            http=HttpSettings(
                connect=self.chat_conn_timeout,
                pool=self.chat_pool_timeout,
                write=self.chat_write_timeout,
                read=self.chat_read_timeout,
                stream_read=self.chat_stream_read_timeout,
            ),
            limit=LimitSettings(
                keep_alive_expiry=self.chat_keep_alive_expiry,
                max_keepalive_connections=self.chat_max_keepalive_connections,
                max_connections=self.chat_max_connections,
            ),
            retry=RetrySettings(
                max_attempt=self.chat_retry_max_attempt,
                base_delay=self.chat_retry_base_delay,
                multiplier=self.chat_retry_multiplier,
                max_delay=self.chat_retry_max_delay,
                enable_jitter=self.chat_retry_enable_jitter,
            ),
        )

    @property
    def rate_limit(self) -> RateLimiterSettings:
        return RateLimiterSettings(
            capacity=self.chat_rate_limit_capacity,
            acquire_timeout=self.chat_rate_limit_acquire_timeout,
            refill_per_second=self.chat_rate_limit_refill_per_second,
        )

    @property
    def jwt(self) -> JwtSettings:
        return JwtSettings(
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            access_token_expire_minutes=self.jwt_access_token_expire_minutes,
            refresh_token_expire_minutes=self.jwt_refresh_token_expire_minutes,
        )

    @property
    def api_key_settings(self) -> ApiKeySettings:
        return ApiKeySettings(key=self.api_key)

    @property
    def http_rate_limit(self) -> HttpRateLimitSettings:
        return HttpRateLimitSettings(
            requests_per_minute=self.http_rate_limit_requests_per_minute,
        )

    @property
    def redis(self) -> RedisSettings:
        return RedisSettings(url=self.redis_url)

    @property
    def embedding(self) -> EmbeddingSettings:
        return EmbeddingSettings(
            base_url=self.embedding_base_url,
            model=self.embedding_model,
            dim=self.embedding_dim,
        )

    @property
    def otel(self) -> OtelSettings:
        return OtelSettings(
            enabled=self.otel_enabled,
            exporter_otlp_endpoint=self.otel_exporter_otlp_endpoint,
            service_name=self.otel_service_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
