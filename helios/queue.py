"""Job queue store — atomic JSON writes, idempotency, daily cap."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from helios.security import (
    validate_existing_file,
    validate_idempotency_key,
    validate_job_id,
    validate_source,
    validate_template_id,
    validate_vars,
)

JobStatus = Literal[
    "pending", "rendering", "uploading", "awaiting_approval",
    "published", "failed", "skipped",
]

STALE_RENDERING_MIN = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return date.today().isoformat()


@dataclass
class Job:
    id: str
    idempotency_key: str
    status: JobStatus
    template: str
    vars: dict[str, str] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    youtube: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    video_id: str | None = None
    error: str | None = None
    source: str = "cli"
    retries: int = 0
    # Backfill: skip render, upload pre-rendered file
    render_path: str | None = None
    srt_path: str | None = None
    script_path: str | None = None
    phase: str = "steady"  # backfill | steady | creator

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Job:
        return cls(
            id=d["id"],
            idempotency_key=d.get("idempotency_key", d["id"]),
            status=d.get("status", "pending"),
            template=d.get("template", ""),
            vars=d.get("vars") or {},
            output=d.get("output") or {},
            youtube=d.get("youtube") or {},
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            video_id=d.get("video_id"),
            error=d.get("error"),
            source=d.get("source", "cli"),
            retries=int(d.get("retries") or 0),
            render_path=d.get("render_path"),
            srt_path=d.get("srt_path"),
            script_path=d.get("script_path"),
            phase=d.get("phase", "steady"),
        )


class QueueStore:
    def __init__(self, data_dir: Path, *, file_roots: list[Path] | None = None) -> None:
        self.data_dir = data_dir
        self.file_roots = file_roots or []
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.queue_path = data_dir / "queue.json"
        self.upload_state_path = data_dir / "upload_state.json"
        self._lock_path = data_dir / ".worker.lock"

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _load_queue(self) -> dict[str, Any]:
        if not self.queue_path.exists():
            return {"jobs": [], "version": 1}
        return json.loads(self.queue_path.read_text(encoding="utf-8"))

    def _save_queue(self, data: dict[str, Any]) -> None:
        self._atomic_write(self.queue_path, data)

    def list_jobs(self, *, status: str | None = None) -> list[Job]:
        jobs = [Job.from_dict(j) for j in self._load_queue().get("jobs", [])]
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at)

    def get_job(self, job_id: str) -> Job | None:
        jid = validate_job_id(job_id)
        for j in self.list_jobs():
            if j.id == jid:
                return j
        return None

    def find_by_idempotency(self, key: str) -> Job | None:
        for j in self.list_jobs():
            if j.idempotency_key == key and j.status not in ("failed", "skipped"):
                return j
        return None

    def enqueue(
        self,
        *,
        template: str,
        vars: dict[str, str] | None = None,
        youtube: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        source: str = "cli",
        render_path: str | None = None,
        srt_path: str | None = None,
        script_path: str | None = None,
        phase: str = "steady",
        job_id: str | None = None,
    ) -> Job:
        tid = validate_template_id(template) if template else "promo-backfill"
        safe_vars = validate_vars(vars or {})
        safe_source = validate_source(source)
        ikey = validate_idempotency_key(idempotency_key) if idempotency_key else f"{tid}:{uuid4().hex[:12]}"
        existing = self.find_by_idempotency(ikey)
        if existing:
            return existing

        safe_render: str | None = None
        safe_srt: str | None = None
        safe_script: str | None = None
        if render_path:
            if not self.file_roots:
                raise ValueError("render_path requires file_roots on QueueStore")
            safe_render = str(validate_existing_file(render_path, self.file_roots))
        if srt_path:
            if not self.file_roots:
                raise ValueError("srt_path requires file_roots on QueueStore")
            safe_srt = str(validate_existing_file(srt_path, self.file_roots))
        if script_path:
            sp = Path(script_path).resolve()
            scripts_root = (self.data_dir / "scripts").resolve()
            try:
                sp.relative_to(scripts_root)
            except ValueError as exc:
                raise ValueError("script_path must be under data/scripts") from exc
            if not sp.is_file():
                raise FileNotFoundError(f"script not found: {script_path}")
            safe_script = str(sp)

        now = _now_iso()
        jid = validate_job_id(job_id) if job_id else f"job_{now[:10].replace('-', '')}_{uuid4().hex[:8]}"
        job = Job(
            id=jid,
            idempotency_key=ikey,
            status="pending",
            template=tid,
            vars=safe_vars,
            youtube=youtube or {},
            created_at=now,
            updated_at=now,
            source=safe_source,
            render_path=safe_render,
            srt_path=safe_srt,
            script_path=safe_script,
            phase=phase,
        )
        data = self._load_queue()
        data.setdefault("jobs", []).append(job.to_dict())
        self._save_queue(data)
        return job

    def update_job(self, job: Job) -> None:
        job.updated_at = _now_iso()
        data = self._load_queue()
        jobs = data.get("jobs", [])
        for i, j in enumerate(jobs):
            if j["id"] == job.id:
                jobs[i] = job.to_dict()
                break
        else:
            jobs.append(job.to_dict())
        data["jobs"] = jobs
        self._save_queue(data)

    def recover_stale(self) -> int:
        """Return rendering jobs stuck >30min to pending."""
        count = 0
        cutoff = datetime.now(timezone.utc).timestamp() - STALE_RENDERING_MIN * 60
        for job in self.list_jobs(status="rendering"):
            try:
                ts = datetime.fromisoformat(job.updated_at.replace("Z", "+00:00")).timestamp()
            except ValueError:
                ts = 0
            if ts < cutoff:
                job.status = "pending"
                self.update_job(job)
                count += 1
        return count

    def acquire_lock(self) -> bool:
        if self._lock_path.exists():
            return False
        self._lock_path.write_text(str(os.getpid()), encoding="utf-8")
        return True

    def release_lock(self) -> None:
        self._lock_path.unlink(missing_ok=True)

    def load_upload_state(self) -> dict[str, Any]:
        if not self.upload_state_path.exists():
            return {"videos": {}, "playlists": {}, "daily": {"date": _today(), "upload_count": 0}}
        return json.loads(self.upload_state_path.read_text(encoding="utf-8"))

    def save_upload_state(self, state: dict[str, Any]) -> None:
        self._atomic_write(self.upload_state_path, state)

    def daily_upload_count(self) -> int:
        state = self.load_upload_state()
        daily = state.get("daily") or {}
        if daily.get("date") != _today():
            return 0
        return int(daily.get("upload_count") or 0)

    def increment_daily_upload(self) -> None:
        state = self.load_upload_state()
        daily = state.setdefault("daily", {})
        if daily.get("date") != _today():
            daily["date"] = _today()
            daily["upload_count"] = 0
        daily["upload_count"] = int(daily.get("upload_count") or 0) + 1
        self.save_upload_state(state)

    def can_upload_today(self, max_per_day: int) -> bool:
        return self.daily_upload_count() < max_per_day

    def pending_count(self) -> int:
        return len([j for j in self.list_jobs() if j.status == "pending"])
