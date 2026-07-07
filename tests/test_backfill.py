"""Backfill scanner tests with fixture PromoMaterials layout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from helios.backfill import enqueue_backfill, scan_backlog
from helios.config import HeliosConfig, LlmConfig
from helios.queue import QueueStore


def _make_promo(tmp_path: Path) -> Path:
    series = tmp_path / "youtube" / "ecosystem-series"
    series.mkdir(parents=True)
    (series / "out").mkdir()
    video = series / "out" / "E10-test.mp4"
    video.write_bytes(b"fake")
    (series / "out" / "E10-test.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHI\n")
    meta = {
        "channel": {"handle": "@test", "default_privacy": "private"},
        "playlists": {"main": {"title": "Main"}},
        "upload_order": ["E10"],
        "episodes": {
            "E10": {
                "video": "out/E10-test.mp4",
                "srt": "out/E10-test.srt",
                "playlist": "main",
                "title": "Test episode",
                "description": "desc",
                "tags": ["test"],
            }
        },
    }
    (series / "upload_metadata.yaml").write_text(yaml.dump(meta))
    return tmp_path


def _cfg(promo: Path, data: Path) -> HeliosConfig:
    return HeliosConfig(
        data_dir=data,
        config_path=data / "cfg.yaml",
        dry_run=True,
        channel_handle="@test",
        default_category="28",
        default_language="en",
        max_uploads_per_day=9,
        max_job_retries=2,
        asset_roots=[promo],
        templates_dir=data / "templates",
        promo_materials_dir=promo,
        github_owner="alexar76",
        repos_allowlist=[],
        webhook_url="",
        notify_on_status=[],
        worker_poll_interval_sec=300,
        llm=LlmConfig(),
        director_enabled=False,
        calliope_enabled=False,
        calliope_editorial_enabled=False,
        calliope_scout_interval_days=3,
        calliope_weekly_enqueue_quota=3,
        calliope_scout_ideas_per_run=5,
        calliope_auto_enqueue_per_run=1,
        calliope_backfill_pause_threshold=8,
        mnemosyne_path=None,
        youtube_client_secret=None,
        youtube_token=None,
        api_key="",
        http_port=8791,
    )


def test_scan_backlog_finds_pending(tmp_path: Path) -> None:
    promo = _make_promo(tmp_path / "promo")
    data = tmp_path / "data"
    cfg = _cfg(promo, data)
    store = QueueStore(data, file_roots=[promo])
    pending = scan_backlog(cfg, store)
    assert len(pending) == 1
    assert pending[0]["episode"] == "E10"


def test_enqueue_backfill_creates_job(tmp_path: Path) -> None:
    promo = _make_promo(tmp_path / "promo")
    data = tmp_path / "data"
    cfg = _cfg(promo, data)
    store = QueueStore(data, file_roots=[promo])
    ids = enqueue_backfill(cfg, store, limit=1)
    assert len(ids) == 1
    job = store.get_job(ids[0])
    assert job is not None
    assert job.phase == "backfill"
    assert job.render_path is not None


def test_scan_skips_uploaded(tmp_path: Path) -> None:
    promo = _make_promo(tmp_path / "promo")
    data = tmp_path / "data"
    cfg = _cfg(promo, data)
    store = QueueStore(data, file_roots=[promo])
    state = store.load_upload_state()
    state["videos"]["E10"] = {"videoId": "abc", "title": "x"}
    store.save_upload_state(state)
    pending = scan_backlog(cfg, store)
    assert len(pending) == 0
