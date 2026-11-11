import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from probe.providers.config import load_llm_config
from probe.providers.registry import build_provider


def main() -> None:
    print("OPENROUTER_API_KEY set:", bool(os.getenv("OPENROUTER_API_KEY")))

    try:
        config = load_llm_config()
    except ValueError as exc:
        print("configuration_error:", str(exc))
        raise SystemExit(1) from None
    print("provider:", config.provider)
    print("model:", config.model)
    print("enabled:", config.enabled)
    print("timeout:", config.timeout)
    print("retries:", config.retries)

    provider = build_provider(config)
    print("provider_class:", type(provider).__name__)
    print("provider_model:", provider.model)

    payload = provider.build_request_payload([
        {"role": "user", "content": "Say hello in one word."}
    ])
    print("request_payload:", payload)


if __name__ == "__main__":
    main()
