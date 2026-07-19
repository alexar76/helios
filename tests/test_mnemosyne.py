"""MNEMOSYNE reader tests."""

from __future__ import annotations

import json
from pathlib import Path

from helios.knowledge.mnemosyne import MnemosyneReader


def _write_kb(path: Path) -> None:
    data = {
        "version": 2,
        "chunks": [
            {
                "id": "argus#readme#0",
                "repo": "argus",
                "source": "readme",
                "title": "argus README",
                "url": "https://github.com/alexar76/argus#readme",
                "text": "ARGUS personal agent WARDEN MCP firewall Telegram offline",
                "updatedAt": "2026-07-07T10:00:00Z",
            },
            {
                "id": "dioscuri#release#0",
                "repo": "dioscuri",
                "source": "release",
                "title": "dioscuri v0.2.0",
                "url": "https://github.com/alexar76/dioscuri/releases/tag/v0.2.0",
                "text": "Twin community agents CASTOR POLLUX MNEMOSYNE",
                "updatedAt": "2026-07-07T09:00:00Z",
            },
        ],
        "seenReleases": ["dioscuri@v0.2.0"],
        "demoUrls": {"argus": "https://magic-ai-factory.com/argus/"},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_mnemosyne_search(tmp_path: Path) -> None:
    kb_path = tmp_path / "mnemosyne.json"
    _write_kb(kb_path)
    kb = MnemosyneReader(kb_path)
    hits = kb.search("ARGUS MCP firewall", k=3)
    assert hits
    assert hits[0].chunk.repo == "argus"
    assert kb.repos_with_demos()["argus"].startswith("https://")


def test_mnemosyne_missing_file(tmp_path: Path) -> None:
    kb = MnemosyneReader(tmp_path / "missing.json")
    assert kb.chunks == []
    assert kb.search("anything") == []
