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
    count = ingest_external_queue(store, audit, path=qfile)
    assert count == 1
    assert store.pending_count() == 1
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
