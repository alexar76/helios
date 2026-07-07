"""Unit tests for HELIOS queue."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helios.queue import QueueStore


@pytest.fixture
def store(tmp_path: Path) -> QueueStore:
    return QueueStore(tmp_path)


def test_enqueue_idempotent(store: QueueStore) -> None:
    j1 = store.enqueue(template="release-short", vars={"repo": "aicom", "tag": "v0.1"}, idempotency_key="test:1")
    j2 = store.enqueue(template="release-short", vars={"repo": "aicom", "tag": "v0.1"}, idempotency_key="test:1")
    assert j1.id == j2.id
    assert len(store.list_jobs()) == 1


def test_daily_cap(store: QueueStore) -> None:
    assert store.can_upload_today(9) is True
    for _ in range(9):
        store.increment_daily_upload()
    assert store.can_upload_today(9) is False
    assert store.daily_upload_count() == 9


def test_atomic_queue_write(store: QueueStore) -> None:
    store.enqueue(template="release-short", vars={"repo": "x", "tag": "v1"}, idempotency_key="a")
    data = json.loads(store.queue_path.read_text())
    assert len(data["jobs"]) == 1


def test_render_path_requires_roots(tmp_path: Path) -> None:
    store = QueueStore(tmp_path)
    with pytest.raises(ValueError, match="file_roots"):
        store.enqueue(
            template="promo-backfill",
            render_path="/etc/passwd",
            idempotency_key="x:1",
        )


def test_render_path_validated(tmp_path: Path) -> None:
    root = tmp_path / "promo"
    root.mkdir()
    video = root / "v.mp4"
    video.write_bytes(b"x")
    store = QueueStore(tmp_path / "data", file_roots=[root])
    job = store.enqueue(
        template="promo-backfill",
        render_path=str(video),
        idempotency_key="x:2",
    )
    assert job.render_path == str(video.resolve())


def test_worker_lock(store: QueueStore) -> None:
    assert store.acquire_lock() is True
    assert store.acquire_lock() is False
    store.release_lock()
    assert store.acquire_lock() is True
    store.release_lock()
