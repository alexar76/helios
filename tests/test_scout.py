"""Editorial scout context tests."""

from __future__ import annotations

import json
from pathlib import Path

from helios.calliope import Calliope
from helios.config import HeliosConfig, LlmConfig
from helios.knowledge.mnemosyne import MnemosyneReader
from helios.queue import QueueStore


def _kb(path: Path) -> None:
    data = {
        "version": 2,
        "chunks": [
            {
                "id": "argus#readme#0",
                "repo": "argus",
                "source": "readme",
                "title": "argus README",
                "url": "https://github.com/alexar76/argus",
                "text": "ARGUS personal agent",
                "updatedAt": "2026-07-07T10:00:00Z",
            },
            {
                "id": "oracles#readme#0",
                "repo": "oracles",
                "source": "readme",
                "title": "oracles README",
                "url": "https://github.com/alexar76/oracles",
                "text": "math oracles MCP",
                "updatedAt": "2026-07-07T09:00:00Z",
            },
        ],
        "demoUrls": {"argus": "https://magic-ai-factory.com/argus/"},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _cfg(tmp: Path, kb_path: Path) -> HeliosConfig:
    return HeliosConfig(
        data_dir=tmp / "data",
        config_path=tmp / "cfg.yaml",
        dry_run=True,
        channel_handle="@test",
        default_category="28",
        default_language="en",
        max_uploads_per_day=9,
        max_job_retries=2,
        asset_roots=[],
        templates_dir=tmp / "templates",
        promo_materials_dir=None,
        github_owner="alexar76",
        repos_allowlist=[],
        webhook_url="",
        notify_on_status=[],
        worker_poll_interval_sec=300,
        llm=LlmConfig(),
        director_enabled=False,
        calliope_enabled=True,
        calliope_editorial_enabled=True,
        calliope_scout_interval_days=3,
        calliope_weekly_enqueue_quota=3,
        calliope_scout_ideas_per_run=5,
        calliope_auto_enqueue_per_run=1,
        calliope_backfill_pause_threshold=8,
        mnemosyne_path=kb_path,
        youtube_client_secret=None,
        youtube_token=None,
        api_key="",
        http_port=8791,
    )


def test_editorial_context_lists_repos(tmp_path: Path) -> None:
    kb_path = tmp_path / "mnemosyne.json"
    _kb(kb_path)
    cfg = _cfg(tmp_path, kb_path)
    store = QueueStore(cfg.data_dir, file_roots=[])
    state = store.load_upload_state()
    state["videos"]["E09"] = {"videoId": "x", "title": "t"}
    store.save_upload_state(state)
    muse = Calliope(cfg, store)
    ctx = muse._editorial_context()
    assert "argus" in ctx["repos_in_kb"]
    assert "E09" in ctx["published_episodes"]


def test_mnemosyne_list_repos(tmp_path: Path) -> None:
    kb_path = tmp_path / "mnemosyne.json"
    _kb(kb_path)
    kb = MnemosyneReader(kb_path)
    assert kb.list_repos() == ["argus", "oracles"]
    assert "ARGUS" in kb.repo_summary("argus")
