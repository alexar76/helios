"""Operator notifications — webhook, inbox file, stdout."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from helios.config import HeliosConfig
from helios.queue import Job

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, cfg: HeliosConfig) -> None:
        self.cfg = cfg
        self.inbox = cfg.data_dir / "inbox.jsonl"

    def _append_inbox(self, payload: dict) -> None:
        self.inbox.parent.mkdir(parents=True, exist_ok=True)
        with self.inbox.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _webhook(self, text: str) -> None:
        if not self.cfg.webhook_url:
            return
        try:
            httpx.post(self.cfg.webhook_url, json={"content": text}, timeout=10.0)
        except Exception as exc:
            log.warning("webhook notify failed: %s", exc)

    def notify_approval(self, job: Job) -> None:
        if "awaiting_approval" not in self.cfg.notify_on_status:
            return
        vid = job.video_id or "?"
        title = job.youtube.get("title", job.id)
        text = (
            f"HELIOS: ready for review\n"
            f"job: {job.id}\n"
            f"title: {title}\n"
            f"studio: https://studio.youtube.com/video/{vid}/edit\n"
            f"approve: helios approve {job.id}"
        )
        print(text, flush=True)
        self._append_inbox({"kind": "awaiting_approval", "job_id": job.id, "video_id": vid, "title": title})
        self._webhook(text)

    def notify_failed(self, job: Job) -> None:
        if "failed" not in self.cfg.notify_on_status:
            return
        text = f"HELIOS: job failed\njob: {job.id}\nerror: {job.error}"
        print(text, flush=True)
        self._append_inbox({"kind": "failed", "job_id": job.id, "error": job.error})
        self._webhook(text)
