"""Ingest jobs from external shared queue (DIOSCURI / GitHub Actions)."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

from helios.audit import AuditLog
from helios.queue import QueueStore


def ingest_external_queue(
    store: QueueStore,
    audit: AuditLog,
    *,
    path: Path | None = None,
    file_roots: list[Path] | None = None,
) -> int:
    """Read HELIOS_QUEUE_PATH jsonl, enqueue jobs, truncate processed lines."""
    raw = (os.environ.get("HELIOS_QUEUE_PATH") or "").strip()
    qpath = path if path is not None else (Path(raw) if raw else None)
    if not qpath or not qpath.exists():
        return 0

    try:
        qfile = open(qpath, "a+", encoding="utf-8")
        writable = True
    except PermissionError:
        try:
            qfile = open(qpath, "r", encoding="utf-8")
            writable = False
        except PermissionError as exc:
            audit.append(
                "ingest.error",
                data={"error": f"permission denied: {exc}", "path": str(qpath)},
            )
            return 0

    with qfile:
        fcntl.flock(qfile.fileno(), fcntl.LOCK_EX)
        qfile.seek(0)
        content = qfile.read()
        lines = content.splitlines()
        if not lines:
            return 0

        remaining: list[str] = []
        count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                if file_roots and payload.get("render_path"):
                    from helios.security import validate_existing_file
                    validate_existing_file(payload["render_path"], file_roots)
                if file_roots and payload.get("srt_path"):
                    from helios.security import validate_existing_file
                    validate_existing_file(payload["srt_path"], file_roots)
                job = store.enqueue(
                    template=payload.get("template", "release-short"),
                    vars=payload.get("vars"),
                    youtube=payload.get("youtube"),
                    idempotency_key=payload.get("idempotency_key"),
                    source=payload.get("source", "external"),
                    render_path=payload.get("render_path"),
                    srt_path=payload.get("srt_path"),
                    phase=payload.get("phase", "steady"),
                )
                audit.append("job.ingested", job_id=job.id, actor=payload.get("source", "external"))
                count += 1
            except Exception as exc:
                remaining.append(line)
                audit.append("ingest.error", data={"error": str(exc), "line": line[:200]})

        if not writable:
            audit.append(
                "ingest.warn",
                data={
                    "path": str(qpath),
                    "reason": "read-only; queue not truncated (fix file mode/owner)",
                    "ingested": count,
                },
            )
            return count

        qfile.seek(0)
        qfile.truncate()
        qfile.write("\n".join(remaining) + ("\n" if remaining else ""))
        qfile.flush()

    return count
