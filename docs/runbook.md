# HELIOS runbook

🌐 [Русский](runbook-ru.md) · [Español](runbook-es.md)

## Worker cron (required)

`docker compose up` **does not** run the worker. Without hourly cron, scout/render/upload never happen.

```bash
(crontab -l 2>/dev/null; echo "0 * * * * docker exec helios helios worker >> /var/log/helios-worker.log 2>&1") | crontab -
docker exec helios helios worker --max-jobs 1
tail -20 /var/log/helios-worker.log
```

## Phase 1: Backfill PromoMaterials (current)

**Backlog:** S1 E10–E12 (3) + S2 S2E01–S2O17 (28) = **31 episodes** already rendered.

```bash
# 1. Scan
helios backfill-scan

# 2. Enqueue batch (10 jobs; worker uploads max 9/day)
helios backfill-enqueue -n 10

# 3. Run worker (cron: @hourly)
helios worker

# 4. Review in YouTube Studio, then approve each
helios approve job_backfill_e10
```

Repeat until `helios backfill-scan` shows 0 pending. ETA: ~4 days at 9 uploads/day.

## Phase 2: Steady state

Editorial runs automatically on each `helios worker` cron tick (when backfill queue ≤ 8):

```bash
helios calliope editorial-status   # weekly quota, scout due?
helios schedule
```

Default: scout every **3 days**, enqueue **1** new CALLIOPE script per run, max **3/week**. Ideas log: `data/editorial/scout_log.jsonl`.

```bash
# Release short on new tag
helios enqueue --template release-short --repo aicom --tag v0.5.0 --summary "…"
helios worker
helios approve JOB_ID   # after Studio review
```

Target: **2–4 public videos/week** (approve in batches; uploads stay private until `helios approve`).

## Daily cap

YouTube allows ~6–10 full uploads/day per project. HELIOS default: **9/day** (`limits.max_uploads_per_day`).

Exit code `2` = daily limit reached (worker exits cleanly, retry tomorrow).

## Alien Monitor

```bash
helios serve --port 8791
# Monitor env: ALIEN_HELIOS_URL=http://host:8791
```

Click HELIOS node → subscribers, views, videos (cached, refreshed by worker).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No new videos for days; scout due; `pending: 0` | **Worker cron missing** — see § Worker cron above |
| `uploadLimitExceeded` | Wait 24h; verify phone in YouTube Studio |
| `invalidCredentials` | `helios auth` — re-OAuth |
| Director rejects metadata | `helios reject` or fix title in job youtube fields |
| ffmpeg not found | Install ffmpeg + ffprobe |
