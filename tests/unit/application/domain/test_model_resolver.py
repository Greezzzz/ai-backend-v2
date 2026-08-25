import pytest

from app.domain.model_profile import ModelProfile, ModelRegistry
from app.domain.model_resolver import ModelResolver
from app.domain.token_counter import TokenCounterRegistry
from app.infrastructure.tokenizer.deepseek.v4.token_counter import (
    DeepSeekV4TokenCounter,
)


def test_model_resolver():
    profile = ModelProfile(
        provider="hungingface",
        model="deepseek-v4-flash",
        context_window=128_000,
        max_output_tokens=1_094,
    )

    model_registry = ModelRegistry(profiles=[profile])

    counter = DeepSeekV4TokenCounter()

    token_counter_registry = TokenCounterRegistry(
        counters={"deepseek-v4-flash": counter}
    )

    resolver = ModelResolver(
        model_registry=model_registry, token_counter_registry=token_counter_registry
    )

    result = resolver.resolve("deepseek-v4-flash")

    assert result.profile is profile
    assert result.token_counter is counter


def test_model_unknown():

    resolver = ModelResolver(
        model_registry=ModelRegistry([]),
        token_counter_registry=TokenCounterRegistry({}),
    )

    with pytest.raises(ValueError):
        resolver.resolve("unknown-model")
