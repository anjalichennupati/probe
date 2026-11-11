from __future__ import annotations

from probe.providers.base import BaseProvider, ProviderConfigurationError
from probe.providers.config import LLMConfig, load_llm_config
from probe.providers.openrouter import OpenRouterProvider

REGISTERED_PROVIDERS = {
    "openrouter": OpenRouterProvider,
}

OPENROUTER_MODEL_ALIASES = {
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4o": "openai/gpt-4o",
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
}


def normalize_model_name(provider: str, model: str) -> str:
    provider_name = str(provider).lower()
    normalized_model = str(model).strip()
    if provider_name == "openrouter":
        if normalized_model.startswith(("openai/", "anthropic/", "google/", "meta/")):
            return normalized_model
        return OPENROUTER_MODEL_ALIASES.get(normalized_model.lower(), normalized_model)
    return normalized_model


def build_provider(config: LLMConfig | None = None, **kwargs: object) -> BaseProvider:
    """Construct the configured provider."""
    resolved_config = config or load_llm_config()
    if not resolved_config.enabled:
        raise ProviderConfigurationError("LLM ranking is disabled. Enable it to construct a provider.")

    provider_name = str(resolved_config.provider).lower()
    if provider_name not in REGISTERED_PROVIDERS:
        raise ProviderConfigurationError(
            f"Unsupported LLM provider '{resolved_config.provider}'. Supported providers: {sorted(REGISTERED_PROVIDERS)}"
        )

    provider_cls = REGISTERED_PROVIDERS[provider_name]
    model_name = normalize_model_name(provider_name, kwargs.get("model", resolved_config.model))

    return provider_cls(
        api_key=kwargs.get("api_key", resolved_config.api_key),
        model=model_name,
        timeout=kwargs.get("timeout", resolved_config.timeout),
        retries=kwargs.get("retries", resolved_config.retries),
    )


def get_provider() -> BaseProvider:
    """Construct the configured provider from the active environment."""
    return build_provider(load_llm_config())


__all__ = ["REGISTERED_PROVIDERS", "build_provider", "get_provider", "normalize_model_name"]
