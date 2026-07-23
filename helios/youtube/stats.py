"""YouTube channel statistics — cached, lazy refresh."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class YoutubeStatsCache:
    def __init__(self, cache_path: Path, *, ttl_sec: int = 300) -> None:
        self.cache_path = cache_path
        self.ttl_sec = ttl_sec

    def _load(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self) -> dict[str, Any]:
        """Return cached stats immediately (lazy load pattern for Monitor)."""
        cached = self._load()
        if cached:
            return cached
        return {
            "subscribers": 0,
            "views": 0,
            "videos": 0,
            "cached_at": None,
            "stale": True,
        }

    def refresh(self, youtube) -> dict[str, Any]:
        """Fetch fresh channel stats from YouTube Data API."""
        now = time.time()
        cached = self._load()
        cached_at = cached.get("_fetched_at", 0)
        if cached and (now - cached_at) < self.ttl_sec:
            return cached

        try:
            resp = youtube.channels().list(part="statistics,snippet", mine=True).execute()
            item = resp["items"][0]
            stats = item.get("statistics", {})
            data = {
                "subscribers": int(stats.get("subscriberCount") or 0),
                "views": int(stats.get("viewCount") or 0),
                "videos": int(stats.get("videoCount") or 0),
                "title": item.get("snippet", {}).get("title", ""),
                "cached_at": _now_iso(),
                "_fetched_at": now,
                "stale": False,
            }
            self._save(data)
            return data
        except Exception as exc:
            if cached:
                cached["stale"] = True
                cached["error"] = str(exc)
                return cached
            return {
                "subscribers": 0,
                "views": 0,
                "videos": 0,
                "cached_at": _now_iso(),
                "stale": True,
                "error": str(exc),
            }
