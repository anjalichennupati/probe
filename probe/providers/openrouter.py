from __future__ import annotations

import json
from typing import Any, Iterable, Mapping
from urllib import request
from urllib.error import HTTPError, URLError

urlopen = request.urlopen

from probe.providers.base import (
    AuthenticationError,
    BaseProvider,
    InvalidResponseError,
    ProviderFailureError,
    ProviderResponse,
    RateLimitError,
    TimeoutError,
)

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(BaseProvider):
    """Concrete OpenRouter chat-completions implementation."""

    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "openai/gpt-4o-mini",
        timeout: float = 30.0,
        retries: int = 2,
        base_url: str = DEFAULT_OPENROUTER_BASE_URL,
    ) -> None:
        super().__init__(model=model, api_key=api_key, timeout=timeout, retries=retries)
        self.base_url = base_url

    def build_request_payload(
        self,
        messages: str | list[dict[str, Any]] | Iterable[Mapping[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        normalized_messages = self._normalize_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": normalized_messages,
        }
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        return payload

    @staticmethod
    def extract_text(message: Mapping[str, Any]) -> str:
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_chunks: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        text_chunks.append(text)
                elif isinstance(part, str):
                    text_chunks.append(part)
            return "".join(text_chunks)
        return ""

    def parse_response_body(self, body: bytes, *, expected_json: bool = True) -> Any:
        if not body:
            raise InvalidResponseError("OpenRouter returned an empty response body.")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            if expected_json:
                raise InvalidResponseError("OpenRouter response was not valid JSON.") from exc
            return body.decode("utf-8", errors="replace")

    def complete(
        self,
        messages: str | list[dict[str, Any]] | Iterable[Mapping[str, Any]],
        **kwargs: Any,
    ) -> ProviderResponse:
        if not self.api_key:
            raise AuthenticationError("OPENROUTER_API_KEY is required before making a request.")

        payload = self.build_request_payload(messages, **kwargs)
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        request_obj = request.Request(self.base_url, data=data, headers=headers, method="POST")

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request_obj, timeout=self.timeout) as response:
                    body = response.read()
                    parsed = self.parse_response_body(body)
                    if not isinstance(parsed, dict) or "choices" not in parsed:
                        raise InvalidResponseError("OpenRouter response did not include choices.")
                    choices = parsed.get("choices") or []
                    if not choices or not isinstance(choices, list):
                        raise InvalidResponseError("OpenRouter returned no choices.")
                    first_choice = choices[0]
                    if not isinstance(first_choice, dict):
                        raise InvalidResponseError("OpenRouter returned malformed choice data.")
                    message = first_choice.get("message") or {}
                    if not isinstance(message, dict):
                        raise InvalidResponseError("OpenRouter returned an invalid message payload.")
                    text = self.extract_text(message)
                    if text == "" and "content" in message:
                        text = str(message["content"])
                    parsed_obj = None
                    if isinstance(text, str) and text.lstrip().startswith(("{", "[")):
                        try:
                            parsed_obj = json.loads(text)
                        except json.JSONDecodeError:
                            parsed_obj = None
                    return ProviderResponse(
                        text=text,
                        raw=parsed,
                        model=str(parsed.get("model") or self.model),
                        provider=self.name,
                        usage=parsed.get("usage") if isinstance(parsed, dict) else None,
                        parsed=parsed_obj,
                    )
            except HTTPError as exc:
                last_error = exc
                code = getattr(exc, "code", None)
                if code == 401 or code == 403:
                    raise AuthenticationError(f"OpenRouter rejected the API key or request: {code}") from exc
                if code == 429:
                    if attempt < self.retries:
                        continue
                    raise RateLimitError("OpenRouter rate limited the request.") from exc
                if attempt < self.retries and code is not None and 500 <= int(code) <= 599:
                    continue
                raise ProviderFailureError(f"OpenRouter request failed with HTTP {code}.") from exc
            except TimeoutError as exc:
                last_error = exc
                if attempt < self.retries:
                    continue
                raise TimeoutError("OpenRouter request timed out.") from exc
            except URLError as exc:
                last_error = exc
                if attempt < self.retries:
                    continue
                raise ProviderFailureError(f"OpenRouter network error: {exc.reason}") from exc
            except InvalidResponseError:
                raise
            except Exception as exc:  # pragma: no cover - fallback for unexpected provider issues
                last_error = exc
                if attempt < self.retries:
                    continue
                raise ProviderFailureError(f"OpenRouter request failed unexpectedly: {exc}") from exc

        if last_error is not None:
            raise ProviderFailureError(f"OpenRouter request failed: {last_error}")
        raise ProviderFailureError("OpenRouter request failed without a response.")


__all__ = ["OpenRouterProvider"]
