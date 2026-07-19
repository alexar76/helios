# HELIOS — architecture

🌐 [Русский](architecture-ru.md) · [Español](architecture-es.md)

## Components

```
Triggers                    HELIOS core                      Output
─────────                   ───────────                      ──────
CLI (helios enqueue)   →    Queue store    →    Renderer    →   MP4 + SRT
DIOSCURI jsonl         →    Worker         →    Uploader    →   YouTube (private)
GitHub Action          →    Director (LLM) →    Notifier    →   webhook / inbox
cron worker            →    Audit log      →    Stats cache →   Monitor /health
```

| Module | File | Responsibility |
|--------|------|----------------|
| CLI | `helios/cli.py` | Operator commands |
| Queue | `helios/queue.py` | Jobs, idempotency, daily cap, lock |
| Worker | `helios/worker.py` | Process pipeline |
| Renderer | `helios/renderer/` | TTS, ffmpeg, subtitles |
| YouTube | `helios/youtube/` | OAuth, upload, captions, stats |
| Director | `helios/director.py` | LLM metadata review + prioritization |
| Security | `helios/security.py` | Input validation, path sandbox |
| Health | `helios/health.py` | `GET /health` only (v0.1) |

**Largest modules:** `queue.py` (~250 lines), `cli.py` (~220), `worker.py` (~210), `config.py` (~195). No monolithic god files — each concern is a separate module.

## Job model

```json
{
  "id": "job_backfill_e10",
  "idempotency_key": "backfill:s1:E10",
  "status": "awaiting_approval",
  "template": "promo-backfill",
  "phase": "backfill",
  "render_path": "/promo/.../E10.mp4",
  "youtube": { "title": "...", "privacy": "private" }
}
```

## Data files (`data/`)

| File | Purpose |
|------|---------|
| `queue.json` | All jobs (atomic write) |
| `upload_state.json` | videoId map, playlists, daily counter |
| `audit.jsonl` | Append-only event log |
| `youtube_stats.json` | Cached channel stats for Monitor |
| `inbox.jsonl` | Operator notifications |
| `renders/{job_id}/` | Per-job render output |

## Integrations

| System | Direction | Mechanism |
|--------|-----------|-----------|
| Alien Monitor | Monitor → HELIOS | Poll `GET /health` |
| DIOSCURI | DIOSCURI → HELIOS | Append `HELIOS_QUEUE_PATH` jsonl |
| PromoMaterials | Content only | `asset_roots`, backfill scanner |

## TTS

| Platform | Engine |
|----------|--------|
| macOS | `say` |
| Linux Docker | `edge-tts` (optional pip extra) |
