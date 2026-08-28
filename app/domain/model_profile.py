from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    context_window: int
    max_output_tokens: int | None = None


class ModelRegistry:
    def __init__(self, profiles: list[ModelProfile]):
        self._profiles = {profile.model: profile for profile in profiles}

    def get(self, model: str) -> ModelProfile:
        profile = self._profiles.get(model)

        if profile is None:
            raise ValueError(f"unsupported model : {model}")

        return profile
