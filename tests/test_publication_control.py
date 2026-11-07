"""An operator's unpublish decision survives automatic worker cycles."""

from dataclasses import replace

import pytest

from helios.audit import AuditLog
from helios.config import load_config
from helios.queue import QueueStore
from helios import worker


@pytest.fixture
def publication(tmp_path, monkeypatch):
    monkeypatch.setenv("HELIOS_DATA_DIR", str(tmp_path))
    cfg = replace(
        load_config(tmp_path / "missing.yaml"), data_dir=tmp_path,
        dry_run=False, auto_approve=True, director_enabled=False,
        calliope_enabled=False, calliope_editorial_enabled=False,
        youtube_client_secret=tmp_path / "client.json",
        youtube_token=tmp_path / "token.json",
    )
    calls = []
    monkeypatch.setattr(worker, "get_youtube", lambda **kwargs: object())
    monkeypatch.setattr(worker, "publish_video", lambda yt, vid, privacy: calls.append((vid, privacy)))
    monkeypatch.setattr(worker.YoutubeStatsCache, "refresh", lambda *args: None)
    store = QueueStore(tmp_path)
    job = store.enqueue(template="release-short", idempotency_key="publication:1")
    job.video_id = "video1"
    job.status = "published"
    job.youtube["privacy"] = "public"
    store.update_job(job)
    store.save_upload_state({"videos": {job.id: {"video_id": job.video_id, "privacy": "public"}}})
    AuditLog(tmp_path / "audit.jsonl").append("youtube.approved", job_id=job.id, actor="operator")
    return cfg, store, job, calls


def test_unpublish_survives_worker_restart_until_explicit_approval(publication):
    cfg, store, job, calls = publication
    hidden = worker.unpublish_job(cfg, job.id)
    assert hidden.status == "unpublished"
    assert store.load_upload_state()["videos"][job.id]["privacy"] == "private"

    # A fresh worker/store represents the next scheduled process, twice.
    assert worker.run_worker(cfg) == 0
    assert worker.run_worker(cfg) == 0
    assert calls == [(job.video_id, "private")]
    assert store.get_job(job.id).youtube["privacy"] == "private"

    restored = worker.approve_job(cfg, job.id)
    assert restored.status == "published"
    assert calls[-1] == (job.video_id, "public")


def test_stale_auto_approval_cannot_override_unpublish(publication):
    cfg, store, job, calls = publication
    job.status = "awaiting_approval"
    store.update_job(job)
    stale = store.get_job(job.id)
    worker.unpublish_job(cfg, job.id)
    worker._publish_job(cfg, store, stale, AuditLog(cfg.data_dir / "audit.jsonl"), actor="auto")
    assert calls == [(job.video_id, "private")]
    assert store.get_job(job.id).status == "unpublished"


def test_auto_approval_still_publishes_new_backlog(publication):
    cfg, store, job, calls = publication
    job.status = "awaiting_approval"
    job.youtube["privacy"] = "private"
    store.update_job(job)
    assert worker.run_worker(cfg) == 0
    assert calls == [(job.video_id, "public")]
    assert store.get_job(job.id).status == "published"


def test_failed_youtube_unpublish_keeps_last_confirmed_local_state(publication, monkeypatch):
    cfg, store, job, calls = publication

    def fail(*args):
        raise RuntimeError("YouTube refused the privacy update")

    monkeypatch.setattr(worker, "publish_video", fail)
    with pytest.raises(RuntimeError, match="refused"):
        worker.unpublish_job(cfg, job.id)
    assert store.get_job(job.id).status == "published"
    assert store.get_job(job.id).youtube["privacy"] == "public"
    assert store.load_upload_state()["videos"][job.id]["privacy"] == "public"
    assert "youtube.unpublished" not in (cfg.data_dir / "audit.jsonl").read_text()


def test_legacy_withdrawal_is_recovered_before_auto_approval(publication):
    cfg, store, job, calls = publication
    # Shape persisted by HELIOS before this fix: private, but queued for approval.
    job.status = "awaiting_approval"
    job.youtube["privacy"] = "private"
    store.update_job(job)
    AuditLog(cfg.data_dir / "audit.jsonl").append("youtube.unpublished", job_id=job.id)
    assert worker.run_worker(cfg) == 0
    assert worker.run_worker(cfg) == 0
    assert calls == []
    assert store.get_job(job.id).status == "unpublished"
    assert store.load_upload_state()["videos"][job.id]["privacy"] == "private"
    worker.approve_job(cfg, job.id)
    assert calls == [(job.video_id, "public")]
    assert store.get_job(job.id).status == "published"


def test_legacy_recovery_preserves_a_later_explicit_approval(publication):
    cfg, store, job, calls = publication
    job.status = "awaiting_approval"
    store.update_job(job)
    audit = AuditLog(cfg.data_dir / "audit.jsonl")
    audit.append("youtube.unpublished", job_id=job.id)
    audit.append("youtube.approved", job_id=job.id, actor="operator")
    assert worker._recover_unpublished_jobs(store, audit) is True
    assert store.get_job(job.id).status == "awaiting_approval"
    assert worker.run_worker(cfg) == 0
    assert store.get_job(job.id).status == "published"
    assert calls == [(job.video_id, "public")]


@pytest.mark.parametrize("damaged", [
    '{"kind":"youtube.unpublished","job_id":', 'null\n', '{invalid}\n',
    '{"kind":"youtube.unpublished","job_id":""}\n',
])
def test_uncertain_legacy_audit_never_triggers_auto_approval(publication, damaged, capsys):
    cfg, store, job, calls = publication
    job.status = "awaiting_approval"
    store.update_job(job)
    with (cfg.data_dir / "audit.jsonl").open("a") as events:
        events.write(damaged)
    assert worker.run_worker(cfg) == 0
    assert calls == []
    assert store.get_job(job.id).status == "awaiting_approval"
    assert "automatic approval paused" in capsys.readouterr().err
    # Recovery uncertainty affects automatic publication; an explicit decision still works.
    worker.approve_job(cfg, job.id)
    assert calls == [(job.video_id, "public")]


def test_missing_legacy_audit_cannot_trigger_auto_approval(publication, capsys):
    cfg, store, job, calls = publication
    job.status = "awaiting_approval"
    store.update_job(job)
    (cfg.data_dir / "audit.jsonl").unlink()
    assert worker.run_worker(cfg) == 0
    assert calls == []
    assert "automatic approval paused" in capsys.readouterr().err
