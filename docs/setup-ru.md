# HELIOS — установка

🌐 [English](setup.md) · [Español](setup-es.md)

## Требования

| Зависимость | Версия |
|-------------|--------|
| Python | 3.11+ |
| ffmpeg + ffprobe | системный пакет |
| TTS | macOS `say` (v1) или `edge-tts` (Linux Docker) |

## Установка

```bash
cd helios
pip install -e ".[dev]"
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env
```

## Секреты (`.env`)

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `YOUTUBE_CLIENT_SECRET` | да* | Путь к OAuth client JSON |
| `YOUTUBE_TOKEN` | да* | Путь к token JSON |
| `DEEPSEEK_API_KEY` | для Director | LLM-ревью метаданных |
| `HELIOS_LLM_PROVIDER` | нет | `deepseek` (по умолчанию), `anthropic`, `openai-compatible`, `ollama` |
| `HELIOS_DRY_RUN` | нет | `1` = без upload |

\* Не нужны при `HELIOS_DRY_RUN=1`.

## YouTube OAuth

```bash
helios auth
```

## Docker

```bash
docker compose up -d --build
curl http://localhost:8791/health
```

Контейнер: non-root, read-only rootfs, `cap_drop: ALL`.

## Путь к PromoMaterials

```yaml
promo_materials_dir: ../PromoMaterials
```

## Миграция upload_state

```bash
python3 scripts/migrate_from_promo_materials.py
```

## Alien Monitor

```bash
helios serve --port 8791
ALIEN_HELIOS_URL=http://host:8791
```
