"""Worker — process queue with daily cap, backfill-first."""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path
from typing import Any

from helios.audit import AuditLog
from helios.backfill import _series_dir, _load_meta
from helios.calliope import Calliope
from helios.config import HeliosConfig, file_roots, load_config
from helios.director import Director
from helios.ingest import ingest_external_queue
from helios.notify import Notifier
from helios.queue import Job, QueueStore
from helios.renderer import render_script, render_template
from helios.youtube.auth import get_youtube
from helios.youtube.stats import YoutubeStatsCache
from helios.youtube.upload import upload_job, publish_video


class DailyLimitReached(Exception):
    pass


def _channel_dict(cfg: HeliosConfig) -> dict[str, Any]:
    return {
        "handle": cfg.channel_handle,
        "default_category": cfg.default_category,
        "default_language": cfg.default_language,
    }


def _playlists_meta(cfg: HeliosConfig) -> dict[str, Any] | None:
    try:
        series = _series_dir(cfg)
        return _load_meta(series, 1).get("playlists")
    except FileNotFoundError:
        return None


def process_job(cfg: HeliosConfig, store: QueueStore, job: Job, audit: AuditLog, director: Director) -> None:
    render_dir = cfg.data_dir / "renders" / job.id
    privacy = job.youtube.get("privacy", "private")

    # Director metadata review
    review = director.review_metadata(job)
    if not review.get("approve", True):
        job.status = "skipped"
        job.error = review.get("reason", "director rejected")
        store.update_job(job)
        audit.append("job.skipped", job_id=job.id, data=review)
        return

    # Render phase
    if job.render_path:
        video_path = Path(job.render_path)
        srt_path = Path(job.srt_path) if job.srt_path else None
    elif job.script_path:
        job.status = "rendering"
        store.update_job(job)
        audit.append("render.start", job_id=job.id, data={"script": job.script_path})
        if cfg.dry_run:
            audit.append("render.dry_run", job_id=job.id)
            job.status = "awaiting_approval"
            store.update_job(job)
            return
        paths = render_script(cfg, Path(job.script_path), job.vars, render_dir)
        video_path = paths["video"]
        srt_path = paths.get("srt")
        audit.append("render.done", job_id=job.id, data={"file": str(video_path), "source": "calliope"})
    else:
        job.status = "rendering"
        store.update_job(job)
        audit.append("render.start", job_id=job.id)
        template_path = cfg.templates_dir / f"{job.template}.yaml"
        if not template_path.exists():
            raise FileNotFoundError(f"template not found: {template_path}")
        if cfg.dry_run:
            audit.append("render.dry_run", job_id=job.id)
            job.status = "awaiting_approval"
            store.update_job(job)
            return
        paths = render_template(cfg, template_path, job.vars, render_dir)
        video_path = paths["video"]
        srt_path = paths.get("srt")
        audit.append("render.done", job_id=job.id, data={"file": str(video_path)})

    if cfg.dry_run:
        job.status = "awaiting_approval"
        store.update_job(job)
        return

    if not store.can_upload_today(cfg.max_uploads_per_day):
        job.status = "pending"
        store.update_job(job)
        raise DailyLimitReached()

    # Upload phase
    job.status = "uploading"
    store.update_job(job)
    if not cfg.youtube_client_secret or not cfg.youtube_token:
        raise FileNotFoundError("YOUTUBE_CLIENT_SECRET and YOUTUBE_TOKEN required")

    youtube = get_youtube(client_secret=cfg.youtube_client_secret, token_path=cfg.youtube_token)
    state = store.load_upload_state()
    episode_key = job.vars.get("episode", job.id)

    vid = upload_job(
        youtube,
        video_path=video_path,
        srt_path=srt_path,
        youtube_meta=job.youtube,
        channel=_channel_dict(cfg),
        state=state,
        playlists_meta=_playlists_meta(cfg),
        privacy=privacy,
        episode_key=episode_key,
    )
    store.save_upload_state(state)
    store.increment_daily_upload()

    job.video_id = vid
    job.error = None
    store.update_job(job)
    audit.append("youtube.uploaded", job_id=job.id, data={"video_id": vid, "privacy": privacy})

    if cfg.auto_approve:
        _publish_job(cfg, store, job, audit, actor="auto")
    else:
        job.status = "awaiting_approval"
        store.update_job(job)


def _publish_job(
    cfg: HeliosConfig,
    store: QueueStore,
    job: Job,
    audit: AuditLog,
    *,
    actor: str,
) -> None:
    if not job.video_id:
        raise ValueError("job has no video_id — not uploaded yet")
    if cfg.dry_run:
        job.status = "published"
        job.youtube["privacy"] = "public"
        store.update_job(job)
        audit.append("youtube.approved", job_id=job.id, actor=actor, data={"video_id": job.video_id, "dry_run": True})
        return

    youtube = get_youtube(client_secret=cfg.youtube_client_secret, token_path=cfg.youtube_token)
    publish_video(youtube, job.video_id, "public")
    job.status = "published"
    job.youtube["privacy"] = "public"
    store.update_job(job)
    state = store.load_upload_state()
    ep = job.vars.get("episode", job.id)
    if ep in state.get("videos", {}):
        state["videos"][ep]["privacy"] = "public"
        store.save_upload_state(state)
    audit.append("youtube.approved", job_id=job.id, actor=actor, data={"video_id": job.video_id})


def run_worker(cfg: HeliosConfig | None = None, *, max_jobs: int | None = None) -> int:
    cfg = cfg or load_config()
    store = QueueStore(cfg.data_dir, file_roots=file_roots(cfg))
    audit = AuditLog(cfg.data_dir / "audit.jsonl")
    notifier = Notifier(cfg)
    director = Director(cfg, store)

    if not store.acquire_lock():
        return 0

    exit_code = 0
    processed = 0
    try:
        store.recover_stale()
        ingested = ingest_external_queue(store, audit, file_roots=file_roots(cfg))
        if ingested:
            audit.append("ingest.done", data={"count": ingested})

        if cfg.calliope_enabled and cfg.calliope_editorial_enabled:
            try:
                editorial = Calliope(cfg, store).run_editorial_if_due()
                if editorial.get("action") != "skipped":
                    audit.append("editorial.done", data=editorial)
            except Exception as exc:
                audit.append("editorial.error", data={"error": str(exc)})

        pending = store.list_jobs(status="pending")
        ordered = director.prioritize(pending)
        limit = max_jobs or cfg.max_uploads_per_day

        for job in ordered[:limit]:
            if not store.can_upload_today(cfg.max_uploads_per_day):
                exit_code = 2
                break
            try:
                process_job(cfg, store, job, audit, director)
                processed += 1
                if job.status == "awaiting_approval":
                    notifier.notify_approval(job)
                elif job.status == "published" and cfg.auto_approve:
                    title = job.youtube.get("title", job.id)
                    print(
                        f"HELIOS: published\njob: {job.id}\ntitle: {title}\n"
                        f"watch: https://youtu.be/{job.video_id}",
                        flush=True,
                    )
            except DailyLimitReached:
                exit_code = 2
                break
            except Exception as exc:
                job.retries += 1
                err = f"{type(exc).__name__}: {exc}"
                if "uploadLimitExceeded" in err or "uploadLimit" in err:
                    job.status = "pending"
                    exit_code = 2
                elif job.retries >= cfg.max_job_retries:
                    job.status = "failed"
                    job.error = err
                    notifier.notify_failed(job)
                else:
                    job.status = "pending"
                store.update_job(job)
                audit.append("job.error", job_id=job.id, data={"error": err, "retries": job.retries})

        if cfg.auto_approve and not cfg.dry_run:
            for job in store.list_jobs(status="awaiting_approval"):
                try:
                    _publish_job(cfg, store, job, audit, actor="auto")
                    title = job.youtube.get("title", job.id)
                    print(
                        f"HELIOS: published (backlog)\njob: {job.id}\ntitle: {title}\n"
                        f"watch: https://youtu.be/{job.video_id}",
                        flush=True,
                    )
                except Exception as exc:
                    audit.append(
                        "approve.error",
                        job_id=job.id,
                        data={"error": f"{type(exc).__name__}: {exc}"},
                    )
    finally:
        store.release_lock()

    # Refresh YouTube stats cache (lazy for monitor)
    if cfg.youtube_client_secret and cfg.youtube_token and not cfg.dry_run:
        try:
            yt = get_youtube(client_secret=cfg.youtube_client_secret, token_path=cfg.youtube_token)
            YoutubeStatsCache(cfg.data_dir / "youtube_stats.json").refresh(yt)
        except Exception:
            pass

    return exit_code if processed == 0 and exit_code else 0


def approve_job(cfg: HeliosConfig, job_id: str, *, actor: str = "operator") -> Job:
    store = QueueStore(cfg.data_dir, file_roots=file_roots(cfg))
    audit = AuditLog(cfg.data_dir / "audit.jsonl")
    job = store.get_job(job_id)
    if not job:
        raise ValueError(f"job not found: {job_id}")
    _publish_job(cfg, store, job, audit, actor=actor)
    return job
