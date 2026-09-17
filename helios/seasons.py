"""Seasonal programming — Helios main content is theme seasons, not release spam."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Season:
    id: str
    title: str
    themes: list[str] = field(default_factory=list)
    repos: list[str] = field(default_factory=list)
    weeks: int = 4
    start: date | None = None

    def prompt_block(self) -> str:
        themes = ", ".join(self.themes) if self.themes else "(open)"
        repos = ", ".join(self.repos) if self.repos else "(any ecosystem repo)"
        return (
            f"CURRENT SEASON: {self.title} (id={self.id})\n"
            f"Season themes (prefer these angles): {themes}\n"
            f"Season focus repos: {repos}\n"
            "At least 60% of pitches must fit this season. "
            "Release-notes recaps are low priority unless they unlock a season theme."
        )


DEFAULT_SEASONS: list[dict[str, Any]] = [
    {
        "id": "trust-and-proof",
        "title": "Trust & Proof",
        "themes": [
            "verifiable oracles",
            "AWR work receipts",
            "provenance",
            "who can rewrite history",
        ],
        "repos": ["oracles", "platon", "aimarket-hub", "aimarket-protocol"],
        "weeks": 4,
    },
    {
        "id": "agents-that-act",
        "title": "Agents That Act",
        "themes": [
            "personal agents",
            "MCP security",
            "ARGUS / WARDEN",
            "invoke as a contract",
        ],
        "repos": ["argus", "aimarket-mcp", "aimarket-oracle-gateway", "dioscuri"],
        "weeks": 4,
    },
    {
        "id": "the-map",
        "title": "The Map",
        "themes": [
            "ecosystem map",
            "Alien Monitor",
            "how satellites connect",
            "Factory vs Hub vs twins",
        ],
        "repos": ["alien-monitor", "aicom", "aicom-landing", "metis"],
        "weeks": 3,
    },
    {
        "id": "markets-and-memory",
        "title": "Markets & Memory",
        "themes": [
            "agent economy",
            "ACEX / Pulse",
            "MNEMOSYNE grounding",
            "THEOROS canon vs ops",
        ],
        "repos": ["acex", "pulse-terminal", "dioscuri", "theoros", "helios"],
        "weeks": 3,
    },
]


def parse_seasons(raw: list[Any] | None) -> list[Season]:
    src = raw if raw else DEFAULT_SEASONS
    out: list[Season] = []
    for item in src:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or "").strip()
        title = str(item.get("title") or sid).strip()
        if not sid or not title:
            continue
        start_raw = item.get("start")
        start: date | None = None
        if isinstance(start_raw, date):
            start = start_raw
        elif isinstance(start_raw, str) and start_raw.strip():
            try:
                start = date.fromisoformat(start_raw.strip()[:10])
            except ValueError:
                start = None
        out.append(
            Season(
                id=sid[:64],
                title=title[:120],
                themes=[str(t)[:80] for t in (item.get("themes") or [])][:12],
                repos=[str(r)[:64] for r in (item.get("repos") or [])][:12],
                weeks=max(1, int(item.get("weeks") or 4)),
                start=start,
            )
        )
    return out


def current_season(seasons: list[Season], today: date | None = None) -> Season | None:
    """Pick active season: dated windows win; else rotate by ISO week blocks."""
    if not seasons:
        return None
    today = today or datetime.now(timezone.utc).date()

    dated = [s for s in seasons if s.start is not None]
    if dated:
        # Walk forward from each start for `weeks`; last matching wins.
        active: Season | None = None
        for s in dated:
            assert s.start is not None
            end = s.start.toordinal() + s.weeks * 7
            if s.start.toordinal() <= today.toordinal() < end:
                active = s
        if active:
            return active

    # Undated rotation: weighted by weeks from a fixed epoch (2026-01-05 = Mon).
    epoch = date(2026, 1, 5)
    days = max(0, (today - epoch).days)
    cycle = sum(s.weeks for s in seasons) or 1
    week_in_cycle = (days // 7) % cycle
    cursor = 0
    for s in seasons:
        cursor += s.weeks
        if week_in_cycle < cursor:
            return s
    return seasons[0]
