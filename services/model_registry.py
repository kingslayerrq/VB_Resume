import json
import os
from typing import Optional

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "model_providers.json")


def load_provider_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_provider_config(provider: str) -> Optional[dict]:
    registry = load_provider_registry()
    return registry.get(provider)


def get_provider_models(provider: str) -> list[str]:
    config = get_provider_config(provider) or {}
    return list(config.get("models", []))


def get_provider_types() -> dict:
    registry = load_provider_registry()
    return {name: cfg.get("type", "service") for name, cfg in registry.items()}
