"""Audit log tests."""

from __future__ import annotations

import json
from pathlib import Path

from helios.audit import AuditLog


def test_audit_append(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append("job.enqueued", job_id="job_1", actor="cli", data={"template": "release-short"})
    log.append("youtube.uploaded", job_id="job_1", data={"video_id": "abc"})
    lines = (tmp_path / "audit.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["kind"] == "job.enqueued"
    assert first["job_id"] == "job_1"
    assert "ts" in first
