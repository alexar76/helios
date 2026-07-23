"""HELIOS Director — LLM-assisted queue prioritization and metadata review.

The Director does NOT write voiceover scripts — that is CALLIOPE's job for new videos.
It reviews titles/descriptions for policy compliance and orders the queue.
Default model: DeepSeek (HELIOS_LLM_PROVIDER=deepseek).
"""

from __future__ import annotations

from typing import Any

from helios.config import HeliosConfig
from helios.llm import LlmClient, LlmBudgetExceeded
from helios.queue import Job, QueueStore

DIRECTOR_SYSTEM = """You are HELIOS Director — broadcast operations for an open-source AI ecosystem YouTube channel.
Rules:
- POST-only: we upload to our own channel, never engagement bots.
- Template-only: you never invent voiceover text.
- Private-first: all uploads stay private until human approve.
- Review metadata only: title ≤100 chars, no clickbait, no false claims, MIT/open-source tone.
Respond with JSON only: {"approve": true|false, "reason": "...", "priority": 0-100}
priority 100 = upload first (backlog episodes in season order).
"""


class Director:
    def __init__(self, cfg: HeliosConfig, store: QueueStore) -> None:
        self.cfg = cfg
        self.store = store
        self.llm = LlmClient(cfg.llm) if cfg.director_enabled else None

    def review_metadata(self, job: Job) -> dict[str, Any]:
        """Review youtube metadata before upload. Fail-open if LLM unavailable."""
        if not self.llm or not job.youtube:
            return {"approve": True, "reason": "director disabled or no metadata", "priority": 50}
        title = job.youtube.get("title", "")
        desc = (job.youtube.get("description") or "")[:500]
        try:
            result = self.llm.json_chat([
                {"role": "system", "content": DIRECTOR_SYSTEM},
                {"role": "user", "content": f"Template: {job.template}\nTitle: {title}\nDescription: {desc}"},
            ])
            return {
                "approve": bool(result.get("approve", True)),
                "reason": str(result.get("reason", "")),
                "priority": int(result.get("priority", 50)),
            }
        except LlmBudgetExceeded:
            return {"approve": True, "reason": "LLM budget exceeded — fail-open", "priority": 50}
        except Exception as exc:
            return {"approve": True, "reason": f"director error — fail-open: {exc}", "priority": 50}

    def prioritize(self, jobs: list[Job]) -> list[Job]:
        """Order pending jobs: backfill → creator → steady."""
        backfill = [j for j in jobs if j.phase == "backfill"]
        creator = [j for j in jobs if j.phase == "creator"]
        steady = [j for j in jobs if j.phase not in ("backfill", "creator")]

        def episode_key(j: Job) -> tuple[int, str]:
            eid = j.vars.get("episode", j.id)
            return (0 if eid.startswith("E") else 1, eid)

        backfill.sort(key=episode_key)
        creator.sort(key=lambda j: j.created_at)
        steady.sort(key=lambda j: j.created_at)
        return backfill + creator + steady

    def schedule_summary(self) -> dict[str, Any]:
        """Human-readable schedule for operator."""
        pending = self.store.list_jobs(status="pending")
        backfill = [j for j in pending if j.phase == "backfill"]
        creator = [j for j in pending if j.phase == "creator"]
        steady = [j for j in pending if j.phase not in ("backfill", "creator")]
        uploaded_today = self.store.daily_upload_count()
        return {
            "phase": "backfill" if backfill else ("creator" if creator else "steady"),
            "pending_backfill": len(backfill),
            "pending_creator": len(creator),
            "pending_steady": len(steady),
            "uploaded_today": uploaded_today,
            "daily_cap": self.cfg.max_uploads_per_day,
            "next_batch": [j.id for j in self.prioritize(pending)[: self.cfg.max_uploads_per_day]],
            "director": "enabled" if self.cfg.director_enabled else "disabled",
        }
