"""HELIOS CLI — typer entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from helios import __version__
from helios.audit import AuditLog
from helios.backfill import enqueue_backfill, scan_backlog
from helios.config import load_config, file_roots
from helios.calliope import Calliope
from helios.director import Director
from helios.queue import QueueStore
from helios.worker import approve_job, run_worker
from helios.youtube.auth import auth_only

app = typer.Typer(help="HELIOS — broadcast pipeline for AIMarket ecosystem")
calliope_app = typer.Typer(help="CALLIOPE — ecosystem screenwriter (MNEMOSYNE-grounded)")
app.add_typer(calliope_app, name="calliope")


@app.command()
def auth() -> None:
    """YouTube OAuth (one-time)."""
    cfg = load_config()
    if not cfg.youtube_client_secret or not cfg.youtube_token:
        typer.echo("Set YOUTUBE_CLIENT_SECRET and YOUTUBE_TOKEN env vars", err=True)
        raise typer.Exit(1)
    title = auth_only(client_secret=cfg.youtube_client_secret, token_path=cfg.youtube_token)
    typer.echo(f"Authenticated as: {title}")


@app.command()
def enqueue(
    template: str = typer.Option("release-short", "--template", "-t"),
    repo: Optional[str] = typer.Option(None, "--repo"),
    tag: Optional[str] = typer.Option(None, "--tag"),
    summary: Optional[str] = typer.Option(None, "--summary"),
    episode: Optional[str] = typer.Option(None, "--episode"),
) -> None:
    """Add a render+upload job to the queue."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    audit = AuditLog(cfg.data_dir / "audit.jsonl")

    vars: dict[str, str] = {}
    youtube: dict = {"privacy": "private"}
    ikey = None

    if repo and tag:
        vars = {"repo": repo, "tag": tag, "url": f"https://github.com/{cfg.github_owner}/{repo}/releases/tag/{tag}"}
        if summary:
            vars["summary"] = summary
        youtube["title"] = f"{repo} {tag} shipped" + (f" — {summary[:60]}" if summary else "")
        youtube["tags"] = ["AIAgents", "OpenSource"]
        ikey = f"release:{cfg.github_owner}/{repo}:{tag}"
    elif episode:
        vars["episode"] = episode
        ikey = f"episode:{episode}"

    job = store.enqueue(
        template=template,
        vars=vars,
        youtube=youtube,
        idempotency_key=ikey,
        source="cli",
    )
    audit.append("job.enqueued", job_id=job.id, actor="cli", data={"template": template})
    typer.echo(job.id)


@app.command("backfill-scan")
def backfill_scan() -> None:
    """List PromoMaterials episodes pending upload."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    pending = scan_backlog(cfg, store)
    typer.echo(f"Pending backfill: {len(pending)} episodes")
    for p in pending[:20]:
        typer.echo(f"  {p['episode']} (S{p['season']})")
    if len(pending) > 20:
        typer.echo(f"  ... and {len(pending) - 20} more")


@app.command("backfill-enqueue")
def backfill_enqueue(
    limit: int = typer.Option(10, "--limit", "-n", help="Max jobs to enqueue (default batch 10)"),
) -> None:
    """Enqueue PromoMaterials backlog as upload-only jobs."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    audit = AuditLog(cfg.data_dir / "audit.jsonl")
    ids = enqueue_backfill(cfg, store, limit=limit)
    for jid in ids:
        audit.append("job.enqueued", job_id=jid, actor="cli", data={"phase": "backfill"})
    typer.echo(f"Enqueued {len(ids)} backfill job(s)")


@app.command()
def worker(
    max_jobs: Optional[int] = typer.Option(None, "--max-jobs", help="Override daily cap for this run"),
) -> None:
    """Process pending jobs (cron: @hourly)."""
    cfg = load_config()
    code = run_worker(cfg, max_jobs=max_jobs)
    raise typer.Exit(code)


@app.command()
def approve(job_id: str) -> None:
    """private → public on YouTube."""
    cfg = load_config()
    job = approve_job(cfg, job_id, actor="operator")
    typer.echo(f"Published: https://youtu.be/{job.video_id}")


@app.command()
def reject(job_id: str, reason: str = typer.Option("rejected", "--reason")) -> None:
    """Mark job as skipped."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    job = store.get_job(job_id)
    if not job:
        raise typer.Exit(1)
    job.status = "skipped"
    job.error = reason
    store.update_job(job)
    typer.echo(f"Rejected: {job_id}")


@app.command()
def status(job_id: Optional[str] = typer.Option(None, "--job")) -> None:
    """Queue status or single job."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    director = Director(cfg, store)

    if job_id:
        job = store.get_job(job_id)
        if not job:
            typer.echo("not found", err=True)
            raise typer.Exit(1)
        typer.echo(json.dumps(job.to_dict(), indent=2))
        return

    sched = director.schedule_summary()
    typer.echo(json.dumps({
        "pending": store.pending_count(),
        "uploaded_today": sched["uploaded_today"],
        "daily_cap": sched["daily_cap"],
        "phase": sched["phase"],
        "pending_backfill": sched["pending_backfill"],
        "pending_creator": sched.get("pending_creator", 0),
        "director": sched["director"],
        "calliope": cfg.calliope_enabled,
        "mnemosyne": str(cfg.mnemosyne_path) if cfg.mnemosyne_path else None,
    }, indent=2))


@app.command()
def schedule() -> None:
    """Show Director schedule and who runs the show."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    director = Director(cfg, store)
    sched = director.schedule_summary()
    typer.echo("HELIOS broadcast schedule")
    typer.echo("=" * 40)
    typer.echo(f"Phase:        {sched['phase']} (backfill until PromoMaterials backlog cleared)")
    typer.echo(f"Director:     LLM {sched['director']} ({cfg.llm.provider}/{cfg.llm.model})")
    typer.echo(f"Calliope:     {'enabled' if cfg.calliope_enabled else 'disabled'} (screenwriter)")
    if cfg.mnemosyne_path:
        typer.echo(f"MNEMOSYNE:    {cfg.mnemosyne_path}")
    typer.echo(f"Daily cap:    {sched['daily_cap']} uploads/day (YouTube quota margin)")
    typer.echo(f"Today:        {sched['uploaded_today']}/{sched['daily_cap']} uploaded")
    typer.echo(f"Backfill:     {sched['pending_backfill']} episodes queued")
    typer.echo(f"Creator:      {sched.get('pending_creator', 0)} Calliope jobs queued")
    typer.echo(f"Steady:       {sched['pending_steady']} new jobs queued")
    if cfg.calliope_editorial_enabled:
        ed = Calliope(cfg, store).editorial_status()
        typer.echo(f"Editorial:    quota {ed['enqueued_this_week']}/{ed['weekly_quota']} this week"
                   f" · scout {'due' if ed['scout_due'] else 'waiting'}"
                   + (" · paused (backfill)" if ed["paused_for_backfill"] else ""))
    typer.echo(f"Next batch:   {', '.join(sched['next_batch'][:10]) or '(none)'}")


@calliope_app.command("scout")
def calliope_scout(
    limit: int = typer.Option(5, "--limit", "-n", help="Number of ideas to generate"),
    enqueue_top: int = typer.Option(0, "--enqueue-top", help="Write script + enqueue top N ideas"),
) -> None:
    """Editorial scout — evergreen ideas from the whole ecosystem (not just releases)."""
    cfg = load_config()
    store = QueueStore(cfg.data_dir, file_roots=file_roots(cfg))
    muse = Calliope(cfg, store)
    ctx = muse._editorial_context()
    typer.echo(f"MNEMOSYNE: {len(ctx['repos_in_kb'])} repos · published {len(ctx['published_episodes'])} · pending jobs {ctx['pending_jobs']}")

    if enqueue_top > 0:
        ids = muse.scout_and_enqueue(top=enqueue_top)
        typer.echo(f"Enqueued {len(ids)} job(s): {', '.join(ids)}")
        typer.echo("Run: helios worker")
        return

    pitches = muse.scout(limit=limit)
    for i, p in enumerate(pitches, 1):
        typer.echo(f"\n{i}. [{p.priority}] {p.topic}")
        typer.echo(f"   {p.hook}")
        if p.repos:
            typer.echo(f"   repos: {', '.join(p.repos)}")
    typer.echo(f"\nLog: {cfg.data_dir / 'editorial' / 'scout_log.jsonl'}")


@calliope_app.command("editorial-status")
def calliope_editorial_status() -> None:
    """Editorial cadence — weekly quota, scout interval, backfill pause."""
    cfg = load_config()
    store = QueueStore(cfg.data_dir, file_roots=file_roots(cfg))
    muse = Calliope(cfg, store)
    typer.echo(json.dumps(muse.editorial_status(), indent=2))


@calliope_app.command("run-editorial")
def calliope_run_editorial(
    force: bool = typer.Option(False, "--force", help="Run scout even if interval not elapsed"),
) -> None:
    """Run editorial scout now (respects weekly enqueue quota)."""
    cfg = load_config()
    store = QueueStore(cfg.data_dir, file_roots=file_roots(cfg))
    audit = AuditLog(cfg.data_dir / "audit.jsonl")
    muse = Calliope(cfg, store)
    result = muse.run_editorial_if_due(force=force)
    audit.append("editorial.manual", data=result)
    typer.echo(json.dumps(result, indent=2))
    if result.get("job_ids"):
        typer.echo("Run: helios worker")


@calliope_app.command("pitch")
def calliope_pitch(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Focus area for topic ideas"),
) -> None:
    """Suggest video topics grounded in MNEMOSYNE (ecosystem KB)."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    muse = Calliope(cfg, store)
    kb = muse.kb.stats()
    typer.echo(f"MNEMOSYNE: {kb['chunks']} chunks, {len(kb['repos'])} repos, loaded={kb['loaded']}")
    pitches = muse.pitch(query=query)
    for i, p in enumerate(pitches, 1):
        typer.echo(f"\n{i}. [{p.priority}] {p.topic}")
        typer.echo(f"   {p.hook}")
        if p.repos:
            typer.echo(f"   repos: {', '.join(p.repos)}")


@calliope_app.command("write")
def calliope_write(
    topic: str = typer.Argument(..., help="Episode topic"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Save script yaml path"),
) -> None:
    """Write a grounded episode script (VO + segments + YouTube metadata)."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    muse = Calliope(cfg, store)
    script = muse.write(topic=topic, query=query, repo=repo)
    if out:
        script.save(out)
        path = out
    else:
        path = muse.save_script(script)
    typer.echo(f"Script: {path}")
    typer.echo(f"Title:  {script.title}")
    typer.echo(f"Segments: {len(script.segments)}")
    for i, seg in enumerate(script.segments, 1):
        typer.echo(f"  {i}. {seg['vo'][:80]}...")


@calliope_app.command("enqueue")
def calliope_enqueue(
    topic: str = typer.Argument(..., help="Episode topic"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
) -> None:
    """Write script + enqueue render/upload job (private until approve)."""
    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    audit = AuditLog(cfg.data_dir / "audit.jsonl")
    muse = Calliope(cfg, store)
    script = muse.write(topic=topic, query=query, repo=repo)
    job_id = muse.enqueue(script, source="calliope")
    audit.append("calliope.enqueued", job_id=job_id, data={"topic": topic, "title": script.title})
    typer.echo(job_id)
    typer.echo(f"Title: {script.title}")
    typer.echo("Run: helios worker")


@calliope_app.command("stats")
def calliope_stats() -> None:
    """MNEMOSYNE knowledge base stats (shared with DIOSCURI)."""
    cfg = load_config()
    store = QueueStore(cfg.data_dir, file_roots=file_roots(cfg))
    muse = Calliope(cfg, store)
    typer.echo(json.dumps(muse.kb.stats(), indent=2))


@app.command()
def serve(port: Optional[int] = typer.Option(None, "--port")) -> None:
    """HTTP server: GET /health for Alien Monitor."""
    import time

    from helios.health import create_health_server
    from helios.youtube.stats import YoutubeStatsCache

    cfg = load_config()
    roots = file_roots(cfg)
    store = QueueStore(cfg.data_dir, file_roots=roots)
    stats_cache = YoutubeStatsCache(cfg.data_dir / "youtube_stats.json")
    started = time.monotonic()

    def snapshot() -> dict:
        return {
            "uptimeSec": int(time.monotonic() - started),
            "queue_pending": store.pending_count(),
            "dryRun": cfg.dry_run,
            "youtube": stats_cache.get(),
        }

    p = port or cfg.http_port
    create_health_server(p, snapshot)
    typer.echo(f"HELIOS health on :{p}/health")
    while True:
        time.sleep(3600)


@app.callback()
def main(version: bool = typer.Option(False, "--version", "-V")) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


if __name__ == "__main__":
    app()
