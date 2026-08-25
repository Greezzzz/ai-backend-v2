from dataclasses import dataclass


from app.domain.model_profile import ModelProfile, ModelRegistry
from app.domain.token_counter import TokenCounterRegistry
from app.domain.token import TokenCounterProtocol


@dataclass(frozen=True)
class ResolvedModel:
    profile: ModelProfile
    token_counter: TokenCounterProtocol


class ModelResolver:

    def __init__(
        self,
        model_registry: ModelRegistry,
        token_counter_registry: TokenCounterRegistry,
    ):
        self._model_registry = model_registry
        self._token_counter_registry = token_counter_registry

    def resolve(self, model: str) -> ResolvedModel:
        profile = self._model_registry.get(model)
        token_counter = self._token_counter_registry.get(model)

        return ResolvedModel(
            profile=profile,
            token_counter=token_counter,
        )
