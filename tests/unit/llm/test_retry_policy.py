"""Unit test retry policy: exponential backoff + full jitter.

Delay tanpa jitter harus eksak sesuai rumus backoff (dan di-cap max_delay).
Dengan jitter, delay = random.uniform(0, backoff) — diuji dengan mock.
"""

import random
from unittest.mock import patch

from app.core.config.retry import RetrySettings
from app.provider.anthropic.retry_policy import AnthropicRetryPolicy
from app.provider.openai.retry_policy import OpenAIRetryPolicy

BASE_DELAY = 0.5
MULTIPLIER = 2.0
MAX_DELAY = 8.0


def _settings(enable_jitter: bool) -> RetrySettings:
    return RetrySettings(
        max_attempt=3,
        base_delay=BASE_DELAY,
        multiplier=MULTIPLIER,
        max_delay=MAX_DELAY,
        enable_jitter=enable_jitter,
    )


def _expected_backoff(attempt: int) -> float:
    """Rumus backoff murni (sebelum jitter)."""
    return min(BASE_DELAY * MULTIPLIER ** (attempt - 1), MAX_DELAY)


def test_no_jitter_delay_is_exact_backoff():
    for policy_cls in (OpenAIRetryPolicy, AnthropicRetryPolicy):
        policy = policy_cls(_settings(enable_jitter=False))
        for attempt in (1, 2, 3, 4):
            assert policy.next_delay(attempt) == _expected_backoff(attempt)


def test_jitter_delay_is_random_between_zero_and_backoff():
    for policy_cls in (OpenAIRetryPolicy, AnthropicRetryPolicy):
        policy = policy_cls(_settings(enable_jitter=True))
        for attempt in (1, 2, 3):
            backoff = _expected_backoff(attempt)
            # mock: kembalikan nilai spesifik di dalam rentang
            with patch.object(random, "uniform", return_value=0.25):
                assert policy.next_delay(attempt) == 0.25
            # pastikan panggilan memakai rentang 0..backoff
            with patch.object(random, "uniform") as mock_uniform:
                policy.next_delay(attempt)
                mock_uniform.assert_called_once_with(0, backoff)


def test_jitter_respects_max_delay_cap():
    policy = OpenAIRetryPolicy(_settings(enable_jitter=True))
    # attempt besar → backoff = max_delay (8.0), jitter tetap di dalam [0, 8]
    with patch.object(random, "uniform") as mock_uniform:
        policy.next_delay(100)
        mock_uniform.assert_called_once_with(0, MAX_DELAY)
