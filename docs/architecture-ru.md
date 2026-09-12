# HELIOS — архитектура

🌐 [English](architecture.md) · [Español](architecture-es.md)

## Компоненты

| Модуль | Файл | Ответственность |
|--------|------|-----------------|
| CLI | `cli.py` | Команды оператора |
| Queue | `queue.py` | Jobs, idempotency, daily cap |
| Worker | `worker.py` | Пайплайн обработки |
| Renderer | `renderer/` | TTS, ffmpeg, субтитры |
| YouTube | `youtube/` | OAuth, upload, stats |
| Director | `director.py` | LLM-ревью метаданных |
| Security | `security.py` | Валидация и sandbox путей |

Крупнейшие файлы ~250 строк — без god-files, каждый модуль отдельно.

## Модель Job

Статусы: `pending` → `rendering` → `uploading` → `awaiting_approval` → `published`.

## Файлы данных (`data/`)

`queue.json`, `upload_state.json`, `audit.jsonl`, `youtube_stats.json`, `renders/`.

## Интеграции

- **Alien Monitor** — poll `GET /health`
- **DIOSCURI** — append в `HELIOS_QUEUE_PATH`
- **PromoMaterials** — контент и backfill
