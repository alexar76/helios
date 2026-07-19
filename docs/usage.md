# HELIOS — usage & CLI

🌐 [Русский](usage-ru.md) · [Español](usage-es.md)

## Schedule & Director

| Role | Who | What |
|------|-----|------|
| **CALLIOPE** | LLM screenwriter (DeepSeek) | Pitches topics, writes VO scripts grounded in **MNEMOSYNE** (DIOSCURI KB) |
| **Director** | LLM ops (DeepSeek) | Reviews title/description before upload; prioritizes queue |
| **Operator** | Human | Studio review → `helios approve` |

| Phase | What | Cadence |
|-------|------|---------|
| **Backfill** | Upload existing PromoMaterials renders (31 episodes) | up to 9 uploads/day (private until approve) |
| **Editorial** | CALLIOPE auto-scout on worker cron | every **3 days** → **1 script/run**, max **3/week** |
| **Creator** | Manual scout / pitch / enqueue | on demand |
| **Release hook** | Any ecosystem repo release (via DIOSCURI MNEMOSYNE) | `release-short` on tag — argus, oracles, dioscuri, … |

**Growth target (steady state):** 2–4 **public** videos/week after operator approve — not daily spam. Backfill clears the backlog first; editorial pauses while `pending_backfill > backfill_pause_threshold` (default 8).

```bash
helios calliope editorial-status   # quota, interval, pause state
helios calliope run-editorial      # force scout now (--force skips interval only)
helios schedule                    # includes editorial line
```

**CALLIOPE** reads `mnemosyne.json` (same file DIOSCURI syncs from GitHub + live demos):

```bash
helios calliope stats
helios calliope scout              # editorial: evergreen ideas from whole ecosystem
helios calliope scout --enqueue-top 1   # scout + write + queue top idea
helios calliope pitch
helios calliope write "What's new in ARGUS" --repo argus
helios calliope enqueue "DIOSCURI twin agents" --repo dioscuri
helios worker
```

Set `DIOSCURI_DATA_DIR=/data` or `HELIOS_MNEMOSYNE_PATH=/data/mnemosyne.json`.

**Director** — LLM agent (`HELIOS_LLM_PROVIDER=deepseek`) that:
- Reviews title/description before upload (policy, length, tone)
- Prioritizes queue (backfill → creator → steady)
- Does **not** write scripts (that's CALLIOPE for new videos; PromoMaterials yaml for backfill)

```bash
helios schedule
```

## Commands

```bash
# Queue
helios enqueue --template release-short --repo aicom --tag v0.4.0 --summary "WARDEN fixes"
helios backfill-scan
helios backfill-enqueue -n 10

# Process
helios worker                    # cron: @hourly
helios worker --max-jobs 3       # override cap for one run

# Review
helios status
helios status --job job_backfill_e10
helios approve job_backfill_e10
helios reject job_... --reason "bad audio"

# Auth & health
helios auth
helios serve --port 8791
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | OK |
| 1 | Error |
| 2 | Daily upload limit reached (retry tomorrow) |

## Job lifecycle

```
pending → rendering → uploading → awaiting_approval → published
                              ↘ failed / skipped
```

## DIOSCURI integration

```bash
# dioscuri .env
HELIOS_SYNDICATION=1
HELIOS_QUEUE_PATH=/data/helios-queue.jsonl
```

Worker ingests the jsonl file on each run (fail-soft append from DIOSCURI).

## LLM providers

Same preset pattern as DIOSCURI:

| Provider | Env |
|----------|-----|
| deepseek (default) | `DEEPSEEK_API_KEY` |
| anthropic | `ANTHROPIC_API_KEY` |
| openai-compatible | `HELIOS_LLM_BASE_URL`, `HELIOS_LLM_API_KEY` |
| ollama / lmstudio / llamacpp | localhost, keyless |

Optional failover: `HELIOS_LLM_FALLBACK_PROVIDER=ollama`
