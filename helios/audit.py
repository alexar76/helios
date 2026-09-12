"""Append-only audit log — one JSON line per event."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, kind: str, *, job_id: str | None = None, actor: str = "system", data: dict[str, Any] | None = None) -> None:
        entry = {
            "ts": _now_iso(),
            "kind": kind,
            "actor": actor,
        }
        if job_id:
            entry["job_id"] = job_id
        if data:
            entry["data"] = data
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
