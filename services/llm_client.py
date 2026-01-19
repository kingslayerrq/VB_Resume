import json
import os
from typing import Optional, Type

import requests
from openai import OpenAI
from pydantic import BaseModel


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
        response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        parsed = json.loads(content)
        if schema is not None:
            return schema.model_validate(parsed).model_dump()
        return parsed

    raise ValueError(f"Unsupported model provider: {provider}")
