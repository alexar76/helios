"""Director prioritization and schedule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from helios.config import HeliosConfig, LlmConfig
from helios.director import Director
from helios.queue import Job, QueueStore


def _cfg(tmp_path: Path) -> HeliosConfig:
    return HeliosConfig(
        data_dir=tmp_path,
        config_path=tmp_path / "cfg.yaml",
        dry_run=True,
        channel_handle="@test",
        default_category="28",
        default_language="en",
        max_uploads_per_day=9,
        max_job_retries=2,
        asset_roots=[],
        templates_dir=tmp_path / "templates",
        promo_materials_dir=None,
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


def test_prioritize_backfill_first(tmp_path: Path) -> None:
    store = QueueStore(tmp_path)
    director = Director(_cfg(tmp_path), store)
    jobs = [
        Job(id="j1", idempotency_key="a", status="pending", template="release-short", phase="steady", created_at="2026-01-02"),
        Job(id="j2", idempotency_key="b", status="pending", template="promo-backfill", phase="backfill", vars={"episode": "E10"}, created_at="2026-01-01"),
        Job(id="j3", idempotency_key="c", status="pending", template="promo-backfill", phase="backfill", vars={"episode": "E11"}, created_at="2026-01-03"),
    ]
    ordered = director.prioritize(jobs)
    assert ordered[0].phase == "backfill"
    assert ordered[-1].phase == "steady"


def test_review_metadata_fail_open_without_llm(tmp_path: Path) -> None:
    store = QueueStore(tmp_path)
    director = Director(_cfg(tmp_path), store)
    job = Job(id="j", idempotency_key="k", status="pending", template="release-short", youtube={"title": "test"})
    review = director.review_metadata(job)
    assert review["approve"] is True


def test_schedule_summary_backfill_phase(tmp_path: Path) -> None:
    store = QueueStore(tmp_path)
    store.enqueue(template="promo-backfill", vars={"episode": "E10"}, idempotency_key="bf:1", phase="backfill")
    director = Director(_cfg(tmp_path), store)
    sched = director.schedule_summary()
    assert sched["phase"] == "backfill"
    assert sched["pending_backfill"] == 1
