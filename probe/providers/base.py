from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


class ProviderError(Exception):
    """Base class for provider failures."""


class ProviderConfigurationError(ProviderError, ValueError):
    """Raised when provider configuration is missing or invalid."""


class AuthenticationError(ProviderError):
    """Raised when the provider rejects the supplied credentials."""


class RateLimitError(ProviderError):
    """Raised when a provider throttles the request."""


class TimeoutError(ProviderError):
    """Raised when a provider request times out."""


class InvalidResponseError(ProviderError):
    """Raised when the provider returns malformed or unusable output."""


class ProviderFailureError(ProviderError):
    """Raised when a provider fails unexpectedly."""


@dataclass(frozen=True)
class ProviderResponse:
    """Normalized response returned by a provider."""

    text: str
    raw: Any = None
    model: str | None = None
    provider: str | None = None
    usage: dict[str, Any] | None = None
    parsed: Any = None


class BaseProvider(ABC):
    """Abstract provider layer for LLM-backed features."""

    name = "base"

    def __init__(self, *, model: str, api_key: str | None, timeout: float, retries: int) -> None:
        self.model = model
        self.api_key = api_key
        self.timeout = float(timeout)
        self.retries = int(retries)

    @staticmethod
    def _normalize_messages(
        messages: str | Iterable[Mapping[str, Any]] | list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]

        normalized: list[dict[str, str]] = []
        for item in messages:
            if not isinstance(item, Mapping):
                raise InvalidResponseError(
                    "Each message must be a mapping with 'role' and 'content'."
                )
            role = str(item.get("role", "user"))
            content = item.get("content")
            if content is None:
                raise InvalidResponseError("Each message must include 'content'.")
            normalized.append({"role": role, "content": str(content)})
        return normalized

    @abstractmethod
    def complete(
        self,
        messages: str | list[dict[str, Any]] | Iterable[Mapping[str, Any]],
        **kwargs: Any,
    ) -> ProviderResponse:
        """Send messages to the provider and return a normalized response."""

    def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Convenience wrapper around complete for a single user prompt."""
        return self.complete([{"role": "user", "content": prompt}], **kwargs)

    def structured(
        self,
        messages: str | list[dict[str, Any]] | Iterable[Mapping[str, Any]],
        schema: Mapping[str, Any],
        *,
        name: str = "structured_response",
        strict: bool = True,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Request provider JSON output conforming to the provided schema."""
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": strict,
                "schema": dict(schema),
            },
        }
        return self.complete(messages, response_format=response_format, **kwargs)
