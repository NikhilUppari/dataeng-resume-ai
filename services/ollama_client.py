from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 360) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return response.ok
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [model.get("name", "") for model in models if model.get("name")]
        except requests.RequestException:
            return []

    def has_model(self, model: str) -> bool:
        models = self.list_models()
        return model in models or f"{model}:latest" in models

    def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.35, "top_p": 0.85},
        }
        if system:
            payload["system"] = system
        try:
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        except requests.Timeout as exc:
            raise OllamaError(f"Ollama timed out after {self.timeout} seconds for model '{model}'") from exc
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed for model '{model}': {exc}") from exc
        if not response.ok:
            message = response.text.strip() or response.reason
            raise OllamaError(f"Ollama request failed for model '{model}': {message}")
        return response.json().get("response", "").strip()

    def generate_json(self, model: str, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        text = self.generate(model, prompt, system=system)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}
