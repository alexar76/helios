# HELIOS — setup

🌐 [Русский](setup-ru.md) · [Español](setup-es.md)

## Requirements

| Dependency | Version |
|------------|---------|
| Python | 3.11+ |
| ffmpeg + ffprobe | system package |
| TTS | macOS `say` (v1) or `edge-tts` (Linux Docker) |

## Install

```bash
cd helios
pip install -e ".[dev]"
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env
```

## Secrets (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `YOUTUBE_CLIENT_SECRET` | yes* | Path to Google OAuth client JSON |
| `YOUTUBE_TOKEN` | yes* | Path to authorized token JSON |
| `DEEPSEEK_API_KEY` | for Director | LLM metadata review |
| `HELIOS_LLM_PROVIDER` | no | `deepseek` (default), `anthropic`, `openai-compatible`, `ollama`, `lmstudio`, `llamacpp` |
| `HELIOS_DRY_RUN` | no | `1` = render plan only, no upload |

\* Not required when `HELIOS_DRY_RUN=1`.

## YouTube OAuth (one-time)

1. Create project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **YouTube Data API v3**
3. Create OAuth desktop credentials → save as `client_secret.json`
4. Run:

```bash
helios auth
```

Token saved to path in `YOUTUBE_TOKEN`.

## Docker

```bash
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env
docker compose up -d --build
curl http://localhost:8791/health
```

Container runs as non-root (`uid 10001`), read-only rootfs, `cap_drop: ALL`.

**`docker compose up` only starts `helios serve`** (port 8791, `/health` for Alien Monitor).  
Render, upload, and editorial scout **do not run automatically** — you must **schedule the worker** (see below).

## Worker cron (required after Docker)

Without hourly `helios worker`, the queue never drains: CALLIOPE scout (every 3 days), render, and YouTube upload will not happen.

On the host where the `helios` container runs:

```bash
# hourly — scout when due, render, upload (private)
(crontab -l 2>/dev/null; echo "0 * * * * docker exec helios helios worker >> /var/log/helios-worker.log 2>&1") | crontab -
crontab -l | grep helios
```

Verify after the first tick (or run once immediately):

```bash
docker exec helios helios worker --max-jobs 1
tail -20 /var/log/helios-worker.log
docker exec helios helios schedule
```

Publishing to the channel: default is manual `helios approve job_xxx` (private → public).  
Auto-publish: `channel.auto_approve: true` or `HELIOS_AUTO_APPROVE=1` in `.env`.

## PromoMaterials path

In `helios.config.yaml`:

```yaml
promo_materials_dir: ../PromoMaterials
asset_roots:
  - ../PromoMaterials
```

Adjust if PromoMaterials lives elsewhere relative to the monorepo.

## Migrate existing upload state

```bash
python3 scripts/migrate_from_promo_materials.py
```

Imports `upload_state.json` playlist IDs and uploaded episode map into `data/upload_state.json`.

## Alien Monitor

```bash
helios serve --port 8791
```

Monitor env:

```bash
ALIEN_HELIOS_URL=http://host:8791
ALIEN_HELIOS_YOUTUBE_URL=https://www.youtube.com/@My-AI-Factory
```
