"""LLM client — multi-provider, same preset pattern as DIOSCURI."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import httpx

from helios.config import LlmConfig


class LlmBudgetExceeded(Exception):
    pass


class LlmClient:
    def __init__(self, cfg: LlmConfig, *, state_path: str | None = None) -> None:
        self.cfg = cfg
        self._calls_today = 0
        self._date = date.today().isoformat()
        self._state_path = state_path

    def _check_budget(self) -> None:
        today = date.today().isoformat()
        if today != self._date:
            self._date = today
            self._calls_today = 0
        if self._calls_today >= self.cfg.max_calls_per_day:
            raise LlmBudgetExceeded("daily LLM budget exceeded")

    def _openai_chat(self, *, base_url: str, api_key: str, model: str, messages: list[dict[str, str]]) -> str:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 512}
        url = f"{base_url.rstrip('/')}/chat/completions"
        with httpx.Client(timeout=60.0) as client:
            r = client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        self._calls_today += 1
        return data["choices"][0]["message"]["content"].strip()

    def _anthropic_chat(self, *, api_key: str, model: str, messages: list[dict[str, str]]) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        system = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_msgs.append(m)
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": 512,
            "messages": user_msgs or [{"role": "user", "content": ""}],
        }
        if system:
            body["system"] = system
        with httpx.Client(timeout=60.0) as client:
            r = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        self._calls_today += 1
        block = data.get("content", [{}])[0]
        return block.get("text", "").strip()

    def chat(self, messages: list[dict[str, str]]) -> str:
        self._check_budget()
        provider = self.cfg.provider.lower()
        try:
            if provider == "anthropic":
                if not self.cfg.api_key:
                    raise ValueError("ANTHROPIC_API_KEY required")
                return self._anthropic_chat(api_key=self.cfg.api_key, model=self.cfg.model, messages=messages)
            return self._openai_chat(
                base_url=self.cfg.base_url,
                api_key=self.cfg.api_key,
                model=self.cfg.model,
                messages=messages,
            )
        except Exception:
            if self.cfg.fallback_provider:
                fb = self.cfg.fallback_provider.lower()
                if fb == "anthropic" and self.cfg.fallback_api_key:
                    return self._anthropic_chat(
                        api_key=self.cfg.fallback_api_key,
                        model=self.cfg.fallback_model,
                        messages=messages,
                    )
                return self._openai_chat(
                    base_url=self.cfg.fallback_base_url,
                    api_key=self.cfg.fallback_api_key,
                    model=self.cfg.fallback_model,
                    messages=messages,
                )
            raise

    def json_chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        text = self.chat(messages)
        # Extract first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        return {"raw": text}
