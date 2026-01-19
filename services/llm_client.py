import json
import os
from typing import Optional, Type

import requests
from openai import OpenAI
from pydantic import BaseModel

from services.model_registry import get_provider_config


DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL = "llama3.1:8b"


def resolve_llm_settings(llm_settings: Optional[dict]) -> dict:
    if not llm_settings:
        return {"provider": DEFAULT_PROVIDER, "model": DEFAULT_MODEL, "api_key": None}
    return {
        "provider": llm_settings.get("provider", DEFAULT_PROVIDER),
        "model": llm_settings.get("model", DEFAULT_MODEL),
        "api_key": llm_settings.get("api_key"),
    }


def is_provider_available(provider: str, api_key: Optional[str], timeout: float = 1.0) -> bool:
    config = get_provider_config(provider)
    if not config:
        return False

    requires_key = config.get("requires_api_key", False)
    if requires_key and not api_key:
        return False

    base_url = config.get("base_url")
    health_path = config.get("health_path")
    if not base_url or not health_path:
        return True

    url = f"{base_url}{health_path}"
    headers = {}
    if provider == "openai" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return response.ok
    except requests.RequestException:
        return False


def is_model_available(
    provider: str,
    model: str,
    api_key: Optional[str],
    timeout: float = 2.0,
) -> bool:
    config = get_provider_config(provider)
    if not config:
        return False

    check = config.get("model_check", {})
    check_type = check.get("type")
    base_url = config.get("base_url")
    path = check.get("path")
    if not base_url or not path or not check_type:
        return False

    headers = {}
    if provider == "openai" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if check_type == "ollama_show":
        try:
            response = requests.post(
                f"{base_url}{path}",
                json={"name": model},
                timeout=timeout,
            )
            return response.ok
        except requests.RequestException:
            return False

    if check_type == "openai_list":
        if not api_key:
            return False
        try:
            response = requests.get(f"{base_url}{path}", headers=headers, timeout=timeout)
            if not response.ok:
                return False
            data = response.json()
            models = {item.get("id") for item in data.get("data", [])}
            return model in models
        except requests.RequestException:
            return False

    return False


def chat_json(
    system_prompt: str,
    user_prompt: str,
    llm_settings: Optional[dict],
    schema: Optional[Type[BaseModel]] = None,
    temperature: float = 0.2,
) -> dict:
    settings = resolve_llm_settings(llm_settings)
    provider = settings["provider"]
    model = settings["model"]
    api_key = settings.get("api_key")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if provider == "openai":
        if not (api_key or os.environ.get("OPENAI_API_KEY")):
            raise ValueError("OpenAI API Key is missing.")

        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        if schema is not None:
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema,
                temperature=temperature,
            )
            return completion.choices[0].message.parsed.model_dump()

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return json.loads(completion.choices[0].message.content)

    if provider == "ollama":
        payload = {
            "model": model,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature},
        }
        base_url = get_provider_config(provider).get("base_url", "http://localhost:11434")
        response = requests.post(f"{base_url}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        parsed = json.loads(content)
        if schema is not None:
            return schema.model_validate(parsed).model_dump()
        return parsed

    raise ValueError(f"Unsupported model provider: {provider}")
