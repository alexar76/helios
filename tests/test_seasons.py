"""Season rotation for Helios content programming."""

from __future__ import annotations

from datetime import date

from helios.seasons import current_season, parse_seasons


def test_default_seasons_rotate() -> None:
    seasons = parse_seasons(None)
    assert len(seasons) >= 4
    s = current_season(seasons, today=date(2026, 1, 5))
    assert s is not None
    assert s.id == "trust-and-proof"


def test_dated_season_window() -> None:
    seasons = parse_seasons(
        [
            {
                "id": "agents-that-act",
                "title": "Agents",
                "themes": ["MCP"],
                "repos": ["argus"],
                "weeks": 2,
                "start": "2026-08-01",
            },
            {
                "id": "the-map",
                "title": "Map",
                "themes": ["monitor"],
                "repos": ["alien-monitor"],
                "weeks": 2,
                "start": "2026-08-15",
            },
        ]
    )
    assert current_season(seasons, today=date(2026, 8, 4)).id == "agents-that-act"
    assert current_season(seasons, today=date(2026, 8, 16)).id == "the-map"


def test_season_prompt_mentions_themes() -> None:
    s = parse_seasons(None)[0]
    block = s.prompt_block()
    assert "CURRENT SEASON" in block
    assert s.title in block
