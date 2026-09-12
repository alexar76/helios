"""Editorial scheduling — quota, interval, backfill pause (no LLM)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from helios.calliope import Calliope
from helios.config import HeliosConfig, LlmConfig
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
        ],
        "demoUrls": {},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _cfg(tmp: Path, kb_path: Path, **overrides: object) -> HeliosConfig:
    base = dict(
        data_dir=tmp / "data",
        config_path=tmp / "cfg.yaml",
        dry_run=False,
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
        calliope_backfill_pause_threshold=2,
        mnemosyne_path=kb_path,
        youtube_client_secret=None,
        youtube_token=None,
        api_key="",
        http_port=8791,
    )
    base.update(overrides)
    return HeliosConfig(**base)


def test_editorial_skips_when_backfill_over_threshold(tmp_path: Path) -> None:
    kb_path = tmp_path / "mnemosyne.json"
    _kb(kb_path)
    cfg = _cfg(tmp_path, kb_path, calliope_backfill_pause_threshold=1)
    store = QueueStore(cfg.data_dir, file_roots=[])
    for i in range(2):
        store.enqueue(
            template="promo-backfill",
            vars={"episode": f"E{i}"},
            idempotency_key=f"bf:{i}",
            phase="backfill",
        )
    muse = Calliope(cfg, store)
    result = muse.run_editorial_if_due()
    assert result["action"] == "skipped"
    assert "backfill_pause" in result["reason"]


def test_editorial_respects_scout_interval(tmp_path: Path) -> None:
    kb_path = tmp_path / "mnemosyne.json"
    _kb(kb_path)
    cfg = _cfg(tmp_path, kb_path)
    store = QueueStore(cfg.data_dir, file_roots=[])
    muse = Calliope(cfg, store)
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    muse._save_editorial_state({"last_scout_at": recent, "week_key": muse._iso_week_key()})
    result = muse.run_editorial_if_due()
    assert result["action"] == "skipped"
    assert result["reason"].startswith("interval:")


def test_editorial_weekly_quota_resets(tmp_path: Path) -> None:
    kb_path = tmp_path / "mnemosyne.json"
    _kb(kb_path)
    cfg = _cfg(tmp_path, kb_path)
    store = QueueStore(cfg.data_dir, file_roots=[])
    muse = Calliope(cfg, store)
    muse._save_editorial_state({"week_key": "2020-W01", "enqueued_this_week": 3})
    status = muse.editorial_status()
    assert status["enqueued_this_week"] == 0
    assert status["quota_left"] == 3


def test_editorial_status_shows_pause(tmp_path: Path) -> None:
    kb_path = tmp_path / "mnemosyne.json"
    _kb(kb_path)
    cfg = _cfg(tmp_path, kb_path, calliope_backfill_pause_threshold=0)
    store = QueueStore(cfg.data_dir, file_roots=[])
    store.enqueue(template="promo-backfill", vars={"episode": "E1"}, idempotency_key="bf:1", phase="backfill")
    status = Calliope(cfg, store).editorial_status()
    assert status["paused_for_backfill"] is True
    assert status["scout_due"] is False
