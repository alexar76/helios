"""LLM client — multi-provider, same preset pattern as DIOSCURI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from helios.config import LlmConfig

JSON_MODE_SUFFIX = "Respond with a single valid JSON object and nothing else."


class LlmBudgetExceeded(Exception):
    pass


def _extract_trailing_json(text: str) -> str | None:
    """Last balanced `{…}` slice in text that parses as JSON, if any."""
    last_brace = text.rfind("{")
    if last_brace < 0:
        return None
    for end in range(len(text), last_brace, -1):
        slice_ = text[last_brace:end].strip()
        if not slice_.endswith("}"):
            continue
        try:
            json.loads(slice_)
            return slice_
        except json.JSONDecodeError:
            continue
    return None


def _extract_openai_text(data: dict[str, Any]) -> str:
    message = (data.get("choices") or [{}])[0].get("message") or {}
    content = (message.get("content") or "").strip()
    if content:
        return content
    reasoning = (message.get("reasoning_content") or "").strip()
    if not reasoning:
        return ""
    return _extract_trailing_json(reasoning) or reasoning


class LlmClient:
    def __init__(self, cfg: LlmConfig, *, state_path: str | None = None) -> None:
        self.cfg = cfg
        self._calls_today = 0
        self._date = datetime.now(timezone.utc).date().isoformat()
        self._state_path = state_path

    def _check_budget(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if today != self._date:
            self._date = today
            self._calls_today = 0
        if self._calls_today >= self.cfg.max_calls_per_day:
            raise LlmBudgetExceeded("daily LLM budget exceeded")

    def _openai_chat(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        url = f"{base_url.rstrip('/')}/chat/completions"
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        self._calls_today += 1
        return _extract_openai_text(data)

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

    def chat(self, messages: list[dict[str, str]], *, max_tokens: int = 1024) -> str:
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
                max_tokens=max_tokens,
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
                    max_tokens=max_tokens,
                )
            raise

    def json_chat(self, messages: list[dict[str, str]], *, max_tokens: int = 4096) -> dict[str, Any]:
        enriched = list(messages)
        if enriched and enriched[0].get("role") == "system":
            enriched = [{**enriched[0], "content": enriched[0]["content"] + "\n" + JSON_MODE_SUFFIX}, *enriched[1:]]
        self._check_budget()
        provider = self.cfg.provider.lower()
        try:
            if provider == "anthropic":
                text = self._anthropic_chat(api_key=self.cfg.api_key, model=self.cfg.model, messages=enriched)
            else:
                text = self._openai_chat(
                    base_url=self.cfg.base_url,
                    api_key=self.cfg.api_key,
                    model=self.cfg.model,
                    messages=enriched,
                    max_tokens=max_tokens,
                    json_mode=True,
                )
        except Exception:
            if self.cfg.fallback_provider:
                fb = self.cfg.fallback_provider.lower()
                if fb == "anthropic" and self.cfg.fallback_api_key:
                    text = self._anthropic_chat(
                        api_key=self.cfg.fallback_api_key,
                        model=self.cfg.fallback_model,
                        messages=enriched,
                    )
                else:
                    text = self._openai_chat(
                        base_url=self.cfg.fallback_base_url,
                        api_key=self.cfg.fallback_api_key,
                        model=self.cfg.fallback_model,
                        messages=enriched,
                        max_tokens=max_tokens,
                        json_mode=True,
                    )
            else:
                raise
        text = text.strip()
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        parsed = _extract_trailing_json(text)
        if parsed:
            return json.loads(parsed)
        return {"raw": text}
