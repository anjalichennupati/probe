from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 2


def parse_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"Invalid boolean value for {field_name}: {value!r}")


def read_pyproject_settings() -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[2]
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return {}
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)
    return data.get("tool", {}).get("probe", {}).get("llm", {})


def parse_timeout(value: Any, *, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid value for {field_name}: {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return parsed


def parse_retry_count(value: Any, *, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid value for {field_name}: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero.")
    return parsed


@dataclass
class LLMConfig:
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    api_key: str | None = None
    timeout: float = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES
    enabled: bool = True


def load_llm_config() -> LLMConfig:
    pyproject_settings = read_pyproject_settings()
    provider = os.getenv("PROBE_LLM_PROVIDER") or pyproject_settings.get("provider") or DEFAULT_PROVIDER
    model = os.getenv("PROBE_LLM_MODEL") or pyproject_settings.get("model") or DEFAULT_MODEL
    enabled_value = os.getenv("PROBE_LLM_ENABLED")
    if enabled_value is None:
        enabled = pyproject_settings.get("enabled", True)
    else:
        enabled = parse_bool(enabled_value, field_name="PROBE_LLM_ENABLED")

    api_key = os.getenv("OPENROUTER_API_KEY")
    timeout_value = os.getenv("PROBE_LLM_TIMEOUT")
    if timeout_value is None:
        timeout = parse_timeout(pyproject_settings.get("timeout", DEFAULT_TIMEOUT), field_name="timeout")
    else:
        timeout = parse_timeout(timeout_value, field_name="PROBE_LLM_TIMEOUT")

    retries_value = os.getenv("PROBE_LLM_RETRIES")
    if retries_value is None:
        retries = parse_retry_count(pyproject_settings.get("retries", DEFAULT_RETRIES), field_name="retries")
    else:
        retries = parse_retry_count(retries_value, field_name="PROBE_LLM_RETRIES")

    if provider != DEFAULT_PROVIDER:
        raise ValueError(f"Unsupported provider '{provider}'. Only '{DEFAULT_PROVIDER}' is currently supported.")
    if not enabled:
        return LLMConfig(
            provider=provider,
            model=model,
            api_key=None,
            timeout=timeout,
            retries=retries,
            enabled=False,
        )
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required when LLM ranking is enabled.")

    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        timeout=timeout,
        retries=retries,
        enabled=True,
    )


__all__ = ["LLMConfig", "load_llm_config"]
