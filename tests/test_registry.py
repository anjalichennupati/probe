from probe.providers.config import LLMConfig
from probe.providers.openrouter import OpenRouterProvider
from probe.providers.registry import build_provider


def test_registry_builds_openrouter_provider():
    config = LLMConfig(
        provider="openrouter",
        model="openai/gpt-4o-mini",
        api_key="abc",
        timeout=30,
        retries=2,
        enabled=True,
    )

    provider = build_provider(config)

    assert isinstance(provider, OpenRouterProvider)
    assert provider.model == "openai/gpt-4o-mini"
    assert provider.timeout == 30.0
    assert provider.retries == 2
