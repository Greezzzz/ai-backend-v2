import json
import time
from collections.abc import AsyncIterator

import httpx

from app.core.config.llm import LLMSettings
from app.core.exceptions.llm import (
    LLmAuthenticationException,
    LLMProviderException,
    LLMRateLimitException,
    LLMTimeoutException,
)
from app.core.logging.logger import logger
from app.core.metrics.llm import (
    llm_error_total,
    llm_input_tokens_total,
    llm_output_tokens_total,
    llm_request_duration_seconds,
    llm_request_total,
)
from app.core.observability.llm import _set_token_usage, instrument_llm_call
from app.core.rate_limiter.limiter import RateLimiter
from app.core.retry.executor import RetryExecutor
from app.domain.llm import LLMRequest, LLMResponse, TokenUsage

_PROVIDER = "anthropic"
_VERSION_HEADER = "2023-06-01"


class AnthropicClient:

    def __init__(
        self,
        http: httpx.AsyncClient,
        settings: LLMSettings,
        retry_executor: RetryExecutor,
        rate_limiter: RateLimiter,
    ):
        self._http = http
        self._settings = settings
        self._retry = retry_executor
        self._rate_limiter = rate_limiter
        self._last_usage: TokenUsage | None = None

    @property
    def last_usage(self) -> TokenUsage | None:
        """Token usage dari event `message_start` (dikirim di awal stream)."""
        return self._last_usage

    async def chat(self, request: LLMRequest) -> LLMResponse:
        start = time.monotonic()
        is_fail = False

        async with instrument_llm_call(
            provider=_PROVIDER,
            model=self._settings.chat.model,
            operation="chat",
        ) as span:
            try:
                payload = self._build_payload(request)

                logger.info("llm_request_started", model=self._settings.chat.model)

                data = await self._retry.execute(
                    lambda: self._send_with_limit(payload), operation_name="anthropic_chat"
                )

                logger.debug("llm_request_response", response=data)

            except httpx.TimeoutException as e:
                is_fail = True
                self._inc_llm_error("timeout")
                raise LLMTimeoutException(
                    details={
                        "model": self._settings.chat.model,
                        "timeout": self._settings.http.read,
                    }
                ) from e
            except httpx.HTTPStatusError as e:
                is_fail = True
                if e.response.status_code == 429:
                    self._inc_llm_error("rate_limit")
                    raise LLMRateLimitException() from e
                elif e.response.status_code in (401, 403):
                    self._inc_llm_error("auth")
                    raise LLmAuthenticationException() from e
                else:
                    self._inc_llm_error("provider")
                    raise LLMProviderException() from e
            except Exception as e:
                is_fail = True
                self._inc_llm_error("provider")
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
                    provider=_PROVIDER,
                ).inc()

                llm_request_duration_seconds.labels(
                    model=self._settings.chat.model, provider=_PROVIDER
                ).observe(duration)

                if is_fail:
                    logger.error("llm_request_failed", exc_info=True)

            response = self._to_domain(data)
            _set_token_usage(span, response.usage)

        return response

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        start = time.monotonic()
        payload = self._build_stream_payload(request)
        self._last_usage = None

        logger.info("llm_stream_started", model=self._settings.chat.model)

        async with instrument_llm_call(
            provider=_PROVIDER,
            model=self._settings.chat.model,
            operation="stream",
        ):
            try:
                await self._rate_limiter.acquire()

                async for line in self._send_stream(payload):
                    delta = self._parse_stream_event(line)
                    if delta:
                        yield delta

                    usage = self._parse_stream_usage(line)
                    if usage is not None:
                        self._last_usage = usage

            except httpx.TimeoutException as e:
                self._inc_llm_error("timeout")
                raise LLMTimeoutException(
                    details={
                        "model": self._settings.chat.model,
                        "timeout": self._settings.http.read,
                    }
                ) from e
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    self._inc_llm_error("rate_limit")
                    raise LLMRateLimitException() from e
                elif e.response.status_code in (401, 403):
                    self._inc_llm_error("auth")
                    raise LLmAuthenticationException() from e
                else:
                    self._inc_llm_error("provider")
                    raise LLMProviderException() from e
            except Exception as e:
                self._inc_llm_error("provider")
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
                    status="success",
                    provider=_PROVIDER,
                ).inc()
                llm_request_duration_seconds.labels(
                    model=self._settings.chat.model, provider=_PROVIDER
                ).observe(duration)

    async def _send_stream(self, payload: dict) -> AsyncIterator[str]:
        """Buka stream ke Anthropic dan yield baris SSE mentah.

        WAJIB pakai `http.stream()` (async context manager) — response dari
        post() tidak mendukung aiter_lines untuk streaming. Timeout read stream
        sengaja lebih longgar (per-request) daripada read global, sama seperti
        OpenAI client.
        """
        stream_timeout = httpx.Timeout(
            connect=self._settings.http.connect,
            read=self._settings.http.stream_read,
            write=self._settings.http.write,
            pool=self._settings.http.pool,
        )

        async with self._http.stream(
            "POST",
            url=f"{self._settings.base_url}/v1/messages",
            headers=self._headers(),
            json=payload,
            timeout=stream_timeout,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                yield line

    @staticmethod
    def _parse_stream_event(line: str) -> str | None:
        """Ambil teks delta dari satu event SSE Anthropic.

        Alur stream: `message_start` → `content_block_delta` (delta.text) →
        `message_stop`. Baris event lain / JSON tidak valid → None (jangan crash).
        """
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None

        if data.get("type") == "content_block_delta":
            delta = data.get("delta") or {}
            return delta.get("text") or None

        return None

    @staticmethod
    def _parse_stream_usage(line: str) -> TokenUsage | None:
        """Ambil token usage dari event `message_start` (di awal stream).

        Anthropic mengirim `message.usage` di event pertama (`message_start`),
        bukan di akhir — jadi ditangkap sejak awal stream.
        """
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None

        if data.get("type") != "message_start":
            return None

        message = data.get("message") or {}
        usage = message.get("usage") or {}

        if not usage:
            return None

        return TokenUsage(
            input_tokens=usage.get("input_tokens") or 0,
            output_tokens=usage.get("output_tokens") or 0,
            total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        )

    def _build_stream_payload(self, request: LLMRequest) -> dict:
        messages, system = self._split_system(request)

        return {
            "model": self._settings.chat.model,
            "messages": messages,
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self._settings.chat.max_output_tokens
            ),
            "stream": True,
            **({"system": system} if system else {}),
            **(
                {"temperature": request.temperature}
                if request.temperature is not None
                else {}
            ),
        }

    async def _send_with_limit(self, payload: dict):
        await self._rate_limiter.acquire()

        return await self._send(payload)

    def _build_payload(self, request: LLMRequest) -> dict:
        messages, system = self._split_system(request)

        logger.info("llm_request_started", model=self._settings.chat.model)

        return {
            "model": self._settings.chat.model,
            "messages": messages,
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self._settings.chat.max_output_tokens
            ),
            **({"system": system} if system else {}),
            **(
                {"temperature": request.temperature}
                if request.temperature is not None
                else {}
            ),
        }

    @staticmethod
    def _split_system(
        request: LLMRequest,
    ) -> tuple[list[dict], str]:
        """Pisahkan pesan system dari chat history.

        Anthropic tidak menerima role `system` di dalam `messages`; ia memakai
        field top-level `system`.
        """
        system_parts = [m.content for m in request.messages if m.role == "system"]
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
            if msg.role != "system"
        ]
        return messages, "\n".join(system_parts)

    async def _send(self, payload: dict) -> dict:
        response = await self._http.post(
            url=f"{self._settings.base_url}/v1/messages",
            headers=self._headers(),
            json=payload,
        )

        response.raise_for_status()

        return response.json()

    @staticmethod
    def _to_domain(data: dict) -> LLMResponse:
        content_blocks = data.get("content") or []
        text = "".join(
            block.get("text", "")
            for block in content_blocks
            if block.get("type") == "text"
        )

        usage = data.get("usage") or {}
        input_tokens = usage.get("input_tokens") or 0
        output_tokens = usage.get("output_tokens") or 0

        llm_input_tokens_total.labels(model=data["model"], provider=_PROVIDER).inc(
            input_tokens
        )
        llm_output_tokens_total.labels(model=data["model"], provider=_PROVIDER).inc(
            output_tokens
        )

        return LLMResponse(
            content=text,
            model=data["model"],
            finish_reason=data.get("stop_reason"),
            usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )

    def _headers(self) -> dict:
        return {
            "x-api-key": self._settings.api_key,
            "anthropic-version": _VERSION_HEADER,
            "Content-Type": "application/json",
        }

    def _inc_llm_error(self, error_type: str) -> None:
        llm_error_total.labels(
            error_type=error_type,
            model=self._settings.chat.model,
            provider=_PROVIDER,
        ).inc()