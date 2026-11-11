import pytest

from probe.providers.config import LLMConfig, load_llm_config


def test_load_llm_config_uses_environment_over_defaults(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PROBE_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("PROBE_LLM_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("PROBE_LLM_TIMEOUT", "15")
    monkeypatch.setenv("PROBE_LLM_RETRIES", "3")
    monkeypatch.setenv("PROBE_LLM_ENABLED", "true")

    config = load_llm_config()

    assert isinstance(config, LLMConfig)
    assert config.provider == "openrouter"
    assert config.model == "openai/gpt-4o-mini"
    assert config.api_key == "test-key"
    assert config.timeout == 15.0
    assert config.retries == 3
    assert config.enabled is True


def test_load_llm_config_rejects_missing_key_for_openrouter(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("PROBE_LLM_PROVIDER", "openrouter")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        load_llm_config()


def test_load_llm_config_allows_disable(monkeypatch):
    monkeypatch.setenv("PROBE_LLM_ENABLED", "false")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    config = load_llm_config()

    assert config.enabled is False
    assert config.provider == "openrouter"
    assert config.api_key is None
