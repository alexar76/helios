# HELIOS — instalación

🌐 [English](setup.md) · [Русский](setup-ru.md)

## Requisitos

Python 3.11+, ffmpeg, TTS (`say` en macOS o `edge-tts` en Linux).

## Instalación

```bash
cd helios
pip install -e ".[dev]"
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env
```

## OAuth YouTube

```bash
helios auth
```

## Docker

```bash
docker compose up -d --build
```

Contenedor: non-root, rootfs de solo lectura, `cap_drop: ALL`.

**`docker compose up` solo inicia `helios serve`** (`/health`). El pipeline (scout, render, upload) requiere **cron del worker** — ver [setup.md](setup.md) § Worker cron.

## Worker cron (obligatorio)

```bash
(crontab -l 2>/dev/null; echo "0 * * * * docker exec helios helios worker >> /var/log/helios-worker.log 2>&1") | crontab -
```

## Monitor

```bash
helios serve --port 8791
ALIEN_HELIOS_URL=http://host:8791
```
