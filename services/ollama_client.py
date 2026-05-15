from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 90) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return response.ok
        except requests.RequestException:
            return False

    def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.35, "top_p": 0.85},
        }
        if system:
            payload["system"] = system
        response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        response.raise_for_status()
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
