"""GitHub fetch cache helpers (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from helios.knowledge.github_fetch import corpus_from_fetch


def test_corpus_from_fetch(tmp_path: Path) -> None:
    root = tmp_path / "fetch"
    root.mkdir()
    (root / "argus.json").write_text(
        json.dumps({
            "repo": "argus",
            "fetched_at": "2026-08-04T12:00:00Z",
            "readme": "ARGUS is a personal agent gateway.",
            "release": "Latest release: v0.1.0 — ship",
        }),
        encoding="utf-8",
    )
    text = corpus_from_fetch(tmp_path, repos=["argus"])
    assert "ARGUS is a personal agent" in text
    assert corpus_from_fetch(tmp_path, repos=["missing"]) == ""
