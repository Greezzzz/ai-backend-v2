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


async def _read_error_body(error: httpx.HTTPStatusError) -> str | None:
    """Ambil response body dari error, aman untuk response streaming.

    `http.stream()` menghasilkan response yang belum di-read — akses `.text`
    langsung memicu `ResponseNotRead`. `aread()` dulu, lalu baca.
    """
    try:
        await error.response.aread()
        return error.response.text[:500]
    except Exception:
        return None


class OpenAIClient:

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
        """Token usage dari chunk stream terakhir yang membawa `usage` (jika ada)."""
        return self._last_usage

    async def chat(self, request: LLMRequest):
        start = time.monotonic()
        is_fail = False

        async with instrument_llm_call(
            provider="openai",
            model=self._settings.chat.model,
            operation="chat",
            estimated_tokens=request.estimated_tokens,
        ) as span:
            try:
                payload = self._build_payload(request)

                logger.info("llm_request_started", model=self._settings.chat.model)

                data = await self._retry.execute(
                    lambda: self._send_with_limit(payload), operation_name="openai_chat"
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
                elif e.response.status_code == 401:
                    self._inc_llm_error("auth")
                    raise LLmAuthenticationException() from e
                else:
                    self._inc_llm_error("provider")
                    raise LLMProviderException(
                        details={
                            "model": self._settings.chat.model,
                            "status_code": e.response.status_code,
                            "response_body": await _read_error_body(e),
                        }
                    ) from e
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
                    provider="openai",
                ).inc()

                llm_request_duration_seconds.labels(
                    model=self._settings.chat.model, provider="openai"
                ).observe(duration)

                if is_fail:
                    logger.error("llm_request_failed", exc_info=True)

            response = self._to_domain(data)
            _set_token_usage(span, response.usage)

        return response

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        """Streaming chat: yield delta teks.

        Catatan desain:
        - Rate limit di-acquire sekali sebelum stream mulai.
        - Retry hanya berlaku untuk kegagalan SEBELUM stream mulai
          (provider tidak mendukung resume mid-stream).
        - Error di tengah stream di-raise, diteruskan sebagai event SSE oleh caller.
        """
        start = time.monotonic()
        payload = self._build_stream_payload(request)
        logger.info("Payload", payload=payload)
        self._last_usage = None

        logger.info("llm_stream_started", model=self._settings.chat.model)

        async with instrument_llm_call(
            provider="openai",
            model=self._settings.chat.model,
            operation="stream",
            estimated_tokens=request.estimated_tokens,
        ):
            try:
                await self._rate_limiter.acquire()

                async for line in self._send_stream(payload):
                    if not line.startswith("data:"):
                        continue

                    data = line[5:].strip()

                    if data == "[DONE]":
                        break

                    delta = self._parse_stream_delta(data)
                    if delta:
                        yield delta

                    # Chunk usage bisa muncul di posisi mana pun (awal/tengah/
                    # akhir) — deteksi via kehadiran field `usage`, bukan
                    # ketiadaan choices (chunk usage tetap punya choices kosong).
                    usage = self._parse_stream_usage(data)
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
                elif e.response.status_code == 401:
                    self._inc_llm_error("auth")
                    raise LLmAuthenticationException() from e
                else:
                    self._inc_llm_error("provider")
                    raise LLMProviderException(
                        details={
                            "model": self._settings.chat.model,
                            "status_code": e.response.status_code,
                            "response_body": await _read_error_body(e),
                        }
                    ) from e
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
                    provider="openai",
                ).inc()
                llm_request_duration_seconds.labels(
                    model=self._settings.chat.model, provider="openai"
                ).observe(duration)

    async def _send_stream(self, payload: dict) -> AsyncIterator[str]:
        """Buka stream ke provider dan yield baris SSE mentah.

        WAJIB pakai `http.stream()` (async context manager), bukan `post()` —
        response dari post() tidak mendukung aiter_lines untuk streaming.

        Timeout read stream sengaja lebih longgar (per-request) daripada timeout
        read global: model reasoning bisa diam lama sebelum token pertama keluar,
        dan jeda antar-chunk tidak boleh dianggap timeout.
        """
        stream_timeout = httpx.Timeout(
            connect=self._settings.http.connect,
            read=self._settings.http.stream_read,
            write=self._settings.http.write,
            pool=self._settings.http.pool,
        )

        async with self._http.stream(
            "POST",
            url=f"{self._settings.base_url}/v1/chat/completions",
            headers=self._header(),
            json=payload,
            timeout=stream_timeout,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                yield line

    def _build_stream_payload(self, request: LLMRequest) -> dict:
        return {
            "model": self._settings.chat.model,
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ],
            "max_completion_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self._settings.chat.max_output_tokens
            ),
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self._settings.chat.temperature
            ),
            "stream": True,
            "stream_options": {"include_usage": True},
        }

    @staticmethod
    def _parse_stream_delta(data: str) -> str | None:
        """Ambil delta teks dari satu chunk SSE.

        Model reasoning (mis. DeepSeek-V4) mengirim `delta.reasoning_content`
        dulu (proses berpikir), lalu `delta.content` (jawaban akhir). Kita
        baca keduanya supaya stream tidak kosong.
        """
        import json

        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            return None

        choices = chunk.get("choices") or []

        if not choices:
            return None

        delta = choices[0].get("delta") or {}

        return delta.get("content") or delta.get("reasoning_content")

    @staticmethod
    def _parse_stream_usage(data: str) -> TokenUsage | None:
        """Ambil token usage dari satu chunk SSE, jika field `usage` ada.

        Chunk usage (OpenAI/DeepSeek dengan `stream_options.include_usage`)
        punya `choices` (delta kosong) PLUS `usage` di level atas — jadi deteksi
        berdasarkan kehadiran `usage`, bukan ketiadaan choices. Posisi chunk
        bebas (awal/tengah/akhir).
        """
        import json

        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            return None

        usage = chunk.get("usage")

        if not usage:
            return None

        return TokenUsage(
            input_tokens=usage.get("prompt_tokens") or 0,
            output_tokens=usage.get("completion_tokens") or 0,
            total_tokens=usage.get("total_tokens") or 0,
        )

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
            "max_completion_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self._settings.chat.max_output_tokens
            ),
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self._settings.chat.temperature
            ),
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

        message = data["choices"][0].get("message") or {}

        return LLMResponse(
            # Model reasoning (DeepSeek-V4) bisa mengirim jawaban di
            # `reasoning_content` dan `content` kosong — fallback supaya
            # jawaban akhir tidak tertukar dengan teks berpikir.
            content=message.get("content") or message.get("reasoning_content") or "",
            model=data["model"],
            finish_reason=data["choices"][0].get("finish_reason"),
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

    def _inc_llm_error(self, error_type: str) -> None:
        llm_error_total.labels(
            error_type=error_type,
            model=self._settings.chat.model,
            provider="openai",
        ).inc()
