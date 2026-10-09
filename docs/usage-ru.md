# HELIOS — использование и CLI

🌐 [English](usage.md) · [Español](usage-es.md)

## Расписание и Director

| Фаза | Что | Каденция |
|------|-----|----------|
| **Backfill** | Загрузка готовых рендеров из PromoMaterials (31 эпизод) | макс. 9 видео/день |
| **Steady** | `release-short` на GitHub releases | по событию + worker каждый час |

**Director** — LLM (`HELIOS_LLM_PROVIDER=deepseek`):
- Ревью title/description перед upload
- Приоритет очереди (backfill → steady)
- **Не генерирует** текст озвучки

```bash
helios schedule
```

## Команды

```bash
helios enqueue --template release-short --repo aicom --tag v0.4.0 --summary "…"
helios backfill-scan
helios backfill-enqueue -n 10
helios worker
helios approve job_backfill_e10
helios status
helios serve --port 8791
```

## Коды выхода

| Код | Значение |
|-----|----------|
| 0 | OK |
| 1 | Ошибка |
| 2 | Дневной лимит upload — повторить завтра |

## Интеграция DIOSCURI

```bash
HELIOS_SYNDICATION=1
HELIOS_QUEUE_PATH=/data/helios-queue.jsonl
```

## LLM-провайдеры

Как у DIOSCURI: `deepseek`, `anthropic`, `openai-compatible`, `ollama`, `lmstudio`, `llamacpp`.
