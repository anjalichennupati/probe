from types import SimpleNamespace

import pytest

from probe.providers.base import ProviderError
from probe.providers.openrouter import OpenRouterProvider


class DummyResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return __import__("json").dumps(self.payload).encode("utf-8")


def test_openrouter_complete_returns_text(monkeypatch):
    payload = {
        "choices": [{"message": {"content": "ranked"}}],
        "model": "openai/gpt-4o-mini",
    }

    def fake_urlopen(req, timeout=None):
        assert timeout == 30.0
        return DummyResponse(payload)

    monkeypatch.setattr("probe.providers.openrouter.urlopen", fake_urlopen)

    provider = OpenRouterProvider(api_key="abc", model="openai/gpt-4o-mini", timeout=30)
    response = provider.complete([{"role": "user", "content": "hello"}])

    assert response.text == "ranked"
    assert response.model == "openai/gpt-4o-mini"


def test_openrouter_retries_rate_limit_and_raises(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(req, timeout=None):
        calls["count"] += 1
        if calls["count"] < 3:
            raise __import__("urllib.error").error.HTTPError(
                url="https://example.com",
                code=429,
                msg="Too Many Requests",
                hdrs={},
                fp=None,
            )
        return DummyResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("probe.providers.openrouter.urlopen", fake_urlopen)

    provider = OpenRouterProvider(api_key="abc", model="openai/gpt-4o-mini", timeout=30, retries=2)
    response = provider.complete([{"role": "user", "content": "hello"}])

    assert response.text == "ok"
    assert calls["count"] == 3


def test_openrouter_raises_typed_errors_for_auth(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise __import__("urllib.error").error.HTTPError(
            url="https://example.com",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr("probe.providers.openrouter.urlopen", fake_urlopen)

    provider = OpenRouterProvider(api_key="bad", model="openai/gpt-4o-mini")

    with pytest.raises(ProviderError):
        provider.complete([{"role": "user", "content": "hello"}])
