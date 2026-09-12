"""YouTube stats cache tests."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

from helios.youtube.stats import YoutubeStatsCache


def test_cache_get_empty(tmp_path: Path) -> None:
    cache = YoutubeStatsCache(tmp_path / "yt.json")
    data = cache.get()
    assert data["stale"] is True
    assert data["subscribers"] == 0


def test_cache_refresh_uses_ttl(tmp_path: Path) -> None:
    cache_path = tmp_path / "yt.json"
    cache = YoutubeStatsCache(cache_path, ttl_sec=3600)
    cache_path.write_text(json.dumps({
        "subscribers": 100,
        "views": 5000,
        "videos": 10,
        "cached_at": "2026-07-07T10:00:00Z",
        "_fetched_at": time.time(),
        "stale": False,
    }))
    cache._load()
    yt = MagicMock()
    result = cache.refresh(yt)
    assert result["subscribers"] == 100
    yt.channels.assert_not_called()


def test_cache_refresh_fetches(tmp_path: Path) -> None:
    cache = YoutubeStatsCache(tmp_path / "yt.json", ttl_sec=0)
    yt = MagicMock()
    yt.channels.return_value.list.return_value.execute.return_value = {
        "items": [{
            "snippet": {"title": "Test Channel"},
            "statistics": {"subscriberCount": "42", "viewCount": "1000", "videoCount": "5"},
        }]
    }
    result = cache.refresh(yt)
    assert result["subscribers"] == 42
    assert result["stale"] is False
