import time

import httpx

from app.core.config.openai import OpenAISettings
from app.core.exceptions.llm import (
    LLmAuthenticationException,
    LLMProviderException,
    LLMRateLimitException,
    LLMTimeoutException,
)
from app.core.logging.logger import logger
from app.core.metrics.llm import (
    llm_input_tokens_total,
    llm_output_tokens_total,
    llm_request_duration_seconds,
    llm_request_total,
)
from app.core.rate_limiter.limiter import RateLimiter
from app.core.retry.executor import RetryExecutor
from app.domain.llm import LLMRequest, LLMResponse, TokenUsage


class OpenAIClient:

    def __init__(
        self,
        http: httpx.AsyncClient,
        settings: OpenAISettings,
        retry_executor: RetryExecutor,
        rate_limiter: RateLimiter,
    ):
        self._http = http
        self._settings = settings
        self._retry = retry_executor
        self._rate_limiter = rate_limiter

    async def chat(self, request: LLMRequest):
        start = time.monotonic()
        is_fail = False

        try:
            payload = self._build_payload(request)

            logger.info("llm_request_started", model=self._settings.chat.model)

            data = await self._retry.execute(
                lambda: self._send_with_limit(payload), operation_name="openai_chat"
            )

            logger.debug("llm_request_response", response=data)

        except httpx.TimeoutException as e:
            is_fail = True
            raise LLMTimeoutException(
                details={
                    "model": self._settings.chat.model,
                    "timeout": self._settings.http.read,
                }
            ) from e
        except httpx.HTTPStatusError as e:
            is_fail = True
            if e.response.status_code == 429:
                raise LLMRateLimitException() from e
            elif e.response.status_code == 401:
                raise LLmAuthenticationException() from e
            else:
                raise LLMProviderException() from e
        except Exception as e:
            is_fail = True
            raise LLMProviderException(
                details={
                    "model": self._settings.chat.model,
                    "exception": type(e).__name__,
                }
            ) from e

        finally:
            duration = time.monotonic() - start

            llm_request_total.labels(
                model=self._settings.chat.model,
                status="error" if is_fail else "success",
                provider="openai",
            ).inc()

            llm_request_duration_seconds.labels(
                model=self._settings.chat.model, provider="openai"
            ).observe(duration)

            if is_fail:
                logger.error("llm_request_failed", exc_info=True)

        return self._to_domain(data)

    async def _send_with_limit(self, payload):

        await self._rate_limiter.acquire()

        return await self._send(payload)

    def _build_payload(self, request: LLMRequest) -> dict:

        logger.info("llm_request_started", model=self._settings.chat.model)

        return {
            "model": self._settings.chat.model,
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ],
            "max_tokens": self._settings.chat.max_tokens,
        }

    async def _send(self, payload: dict) -> dict:

        response = await self._http.post(
            url=f"{self._settings.base_url}/v1/chat/completions",
            headers=self._header(),
            json=payload,
        )

        response.raise_for_status()

        return response.json()

    def _to_domain(self, data: dict) -> LLMResponse:

        llm_input_tokens_total.labels(model=data["model"], provider="openai").inc(
            data["usage"]["prompt_tokens"]
        )

        llm_output_tokens_total.labels(model=data["model"], provider="openai").inc(
            data["usage"]["completion_tokens"]
        )

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data["model"],
            finish_reason=data["choices"][0]["finish_reason"],
            usage=TokenUsage(
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                total_tokens=data["usage"]["total_tokens"],
            ),
        )

    def _header(self) -> dict:
        return {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
