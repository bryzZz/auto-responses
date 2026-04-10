from __future__ import annotations

import json
from abc import ABC, abstractmethod
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.models import LLMConfig


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class StubLLMClient(BaseLLMClient):
    def generate(self, prompt: str) -> str:
        return prompt


class OllamaLLMClient(BaseLLMClient):
    def __init__(self, settings: LLMConfig) -> None:
        self.settings = settings

    def generate(self, prompt: str) -> str:
        if not self.settings.model.strip():
            raise RuntimeError("LLM model is not configured in config/app.yaml")

        payload = {
            "model": self.settings.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature,
                "num_predict": self.settings.max_tokens,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            self.settings.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(
                "Could not reach local LLM endpoint. "
                "Check that Ollama is running and endpoint is correct."
            ) from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON from LLM endpoint: {body[:500]}") from exc

        text = str(parsed.get("response", "")).strip()
        if not text:
            raise RuntimeError(f"LLM returned empty response: {body[:500]}")
        return text
