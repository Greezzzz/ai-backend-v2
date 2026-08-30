import pytest

from app.domain.model_profile import ModelProfile, ModelRegistry
from app.domain.token_counter import TokenCounterRegistry
from app.infrastructure.tokenizer.deepseek.v4.token_counter import (
    DeepSeekV4TokenCounter,
)


def test_model_profile():

    profile = ModelProfile(
        provider="hungingface",
        context_window=128_000,
        model="deepseek-v4-flash",
        max_output_tokens=4_096,
    )

    assert profile.provider == "hungingface"
    assert profile.model == "deepseek-v4-flash"
    assert profile.max_output_tokens == 4_096
    assert profile.context_window == 128_000


def test_model_registry():
    profile = ModelProfile(
        provider="hungingface",
        context_window=128_000,
        model="deepseek-v4-flash",
        max_output_tokens=4_096,
    )

    registry = ModelRegistry([profile])

    result = registry.get("deepseek-v4-flash")

    assert result == profile


def test_unknown_model():
    registry = ModelRegistry([])

    with pytest.raises(ValueError):
        registry.get("unknown-model")


def test_registry():
    counter = DeepSeekV4TokenCounter()

    registry = TokenCounterRegistry(
        counters={
            "deepseek-v4-flash": counter,
        }
    )

    result = registry.get("deepseek-v4-flash")

    assert result == counter
