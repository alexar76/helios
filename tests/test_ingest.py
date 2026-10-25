"""External queue ingest tests."""

from __future__ import annotations

import json
from pathlib import Path

from helios.audit import AuditLog
from helios.ingest import ingest_external_queue
from helios.queue import QueueStore


def test_ingest_external_queue(tmp_path: Path) -> None:
    qfile = tmp_path / "queue.jsonl"
    qfile.write_text(
        json.dumps({
            "template": "release-short",
            "vars": {"repo": "aicom", "tag": "v0.1.0", "url": "https://example.com", "summary": "test"},
            "idempotency_key": "release:aicom:v0.1.0",
            "source": "dioscuri",
        }) + "\n",
        encoding="utf-8",
    )

    store = QueueStore(tmp_path / "data", file_roots=[tmp_path])
    audit = AuditLog(tmp_path / "data" / "audit.jsonl")
    count = ingest_external_queue(store, audit, path=qfile, accept_release_shorts=True)
    assert count == 1
    assert store.pending_count() == 1
    assert qfile.read_text().strip() == ""


def test_ingest_skips_release_shorts_when_disabled(tmp_path: Path) -> None:
    qfile = tmp_path / "queue.jsonl"
    qfile.write_text(
        json.dumps({
            "template": "release-short",
            "vars": {"repo": "aicom", "tag": "v0.1.0"},
            "idempotency_key": "release:aicom:v0.1.0",
            "source": "dioscuri",
        })
        + "\n"
        + json.dumps({
            "template": "theoros-short",
            "vars": {"chapter": "1", "hook": "h", "body": "b", "debate": "d", "column": "col"},
            "idempotency_key": "theoros:1",
            "source": "dioscuri-theoros",
            "phase": "creator",
        })
        + "\n",
        encoding="utf-8",
    )
    store = QueueStore(tmp_path / "data", file_roots=[tmp_path])
    audit = AuditLog(tmp_path / "data" / "audit.jsonl")
    count = ingest_external_queue(store, audit, path=qfile, accept_release_shorts=False)
    assert count == 2
    jobs = store.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].template == "theoros-short"
    assert qfile.read_text().strip() == ""


def test_ingest_permission_denied(tmp_path: Path) -> None:
    qfile = tmp_path / "queue.jsonl"
    qfile.write_text('{"template":"release-short","idempotency_key":"x","source":"dioscuri"}\n', encoding="utf-8")
    qfile.chmod(0o000)

    store = QueueStore(tmp_path / "data", file_roots=[tmp_path])
    audit = AuditLog(tmp_path / "data" / "audit.jsonl")
    count = ingest_external_queue(store, audit, path=qfile)

    assert count == 0
    assert store.pending_count() == 0
    kinds = [json.loads(line)["kind"] for line in audit.path.read_text().splitlines()]
    assert "ingest.error" in kinds

    qfile.chmod(0o644)


def test_a_queue_producer_cannot_choose_the_upload_privacy(tmp_path: Path) -> None:
    """GCVE-110-PYPI-2026-021897: `youtube.privacy` from the shared queue reached the upload,
    so a producer could publish without `helios approve`."""
    qfile = tmp_path / "queue.jsonl"
    qfile.write_text(json.dumps({
        "template": "theoros-short",
        "vars": {"chapter": "1", "hook": "h", "body": "b", "debate": "d", "column": "col"},
        "youtube": {"title": "t", "privacy": "public"},
        "idempotency_key": "theoros:public",
        "source": "dioscuri",
    }) + "\n", encoding="utf-8")
    store = QueueStore(tmp_path / "data", file_roots=[tmp_path])
    audit = AuditLog(tmp_path / "data" / "audit.jsonl")
    assert ingest_external_queue(store, audit, path=qfile, accept_release_shorts=True) == 1
    job = store.list_jobs()[0]
    assert job.youtube == {"title": "t", "privacy": "private"}
    events = [json.loads(line) for line in (tmp_path / "data" / "audit.jsonl").read_text().splitlines()]
    ignored = [e for e in events if e["kind"] == "ingest.privacy_ignored"]
    assert ignored and ignored[0]["data"] == {"requested": "public", "source": "dioscuri"}


def test_the_worker_uploads_private_whatever_the_job_asks(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace

    from helios import worker

    video = tmp_path / "v.mp4"
    video.write_bytes(b"\0")
    store = QueueStore(tmp_path / "data", file_roots=[tmp_path])
    audit = AuditLog(tmp_path / "data" / "audit.jsonl")
    job = store.enqueue(template="theoros-short", youtube={"title": "t", "privacy": "public"},
                        render_path=str(video))
    seen = {}
    monkeypatch.setattr(worker, "_video_luma_qc", lambda path: {"ok": True})
    monkeypatch.setattr(worker, "get_youtube", lambda **kw: object())
    monkeypatch.setattr(worker, "_channel_dict", lambda cfg: {})
    monkeypatch.setattr(worker, "_playlists_meta", lambda cfg: None)

    def fake_upload(youtube, **kw):
        seen["privacy"] = kw["privacy"]
        return "vid123"

    monkeypatch.setattr(worker, "upload_job", fake_upload)
    cfg = SimpleNamespace(data_dir=tmp_path / "data", dry_run=False, max_uploads_per_day=10,
                          youtube_client_secret="s", youtube_token="t", auto_approve=False)
    director = SimpleNamespace(review_metadata=lambda job: {"approve": True})
    worker.process_job(cfg, store, job, audit, director)
    assert seen["privacy"] == "private"
    assert store.get_job(job.id).status == "awaiting_approval"
