# HELIOS — broadcast-слой экосистемы AIMarket

<!-- aicom-readme-badges -->
<p align="center">
  <a href="https://github.com/alexar76/helios/actions/workflows/ci.yml"><img src="https://github.com/alexar76/helios/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/alexar76/helios/actions/workflows/pages.yml"><img src="https://github.com/alexar76/helios/actions/workflows/pages.yml/badge.svg" alt="Pages deploy" /></a>
  <a href="https://alexar76.github.io/helios/"><img src="https://img.shields.io/badge/landing-gallery-e84a1a" alt="Landing gallery" /></a>
  <a href="https://www.youtube.com/@My-AI-Factory"><img src="https://img.shields.io/badge/YouTube-@My--AI--Factory-ff0000" alt="YouTube канал" /></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.11-brightgreen.svg" alt="Python >=3.11" />
  <img src="https://img.shields.io/badge/tests-39%20passed-brightgreen" alt="39 tests passed" />
  <a href="docs/badges/coverage.svg"><img src="docs/badges/coverage.svg" alt="Покрытие тестами" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
</p>
<!-- /aicom-readme-badges -->

> **Шаблон на входе → озвученное видео → очередь на YouTube — private, пока не approve.**  
> MIT · self-hosted · только публикация · без engagement-ботов.

🌐 **Язык:** [English](README.md) · **Русский** · [Español](README-es.md)

**Landing:** [alexar76.github.io/helios](https://alexar76.github.io/helios/) · **GitHub:** [alexar76/helios](https://github.com/alexar76/helios) · **YouTube:** [@My-AI-Factory](https://www.youtube.com/@My-AI-Factory) · [плейлист](https://www.youtube.com/playlist?list=PLQAJcI3MYJxM)

| | |
|---|---|
| **Роль** | Рендер MP4 из yaml-шаблонов → загрузка на YouTube (private) → approve оператором → public |
| **Monitor** | [Alien Monitor](https://magic-ai-factory.com/monitor/) — клик по **HELIOS** → статистика канала |
| **Интеграция** | [helios-integration-ru.md](https://github.com/alexar76/aicom/blob/main/docs/ecosystem/helios-integration-ru.md) |

## Зачем HELIOS

Экосистема `alexar76` постоянно меняется: релизы, оракулы, курсы, showcase. Ручной пайплайн `build_series.py` + `upload_youtube.py` в PromoMaterials не масштабируется. **HELIOS** — отдельный broadcast-сателлит: очередь заданий, audit log, human gate перед публикацией.

```
PromoMaterials (контент)  →  HELIOS (движок)  →  YouTube (private)  →  approve  →  public
DIOSCURI (релиз)          →  shared queue     →  helios worker
```

## Charter (обязательные правила)

1. **POST-only** — только свой канал; никаких лайков, комментов, подписок.
2. **Template-only** — видео только из проверенных yaml; текст VO фиксирован в шаблоне.
3. **Private-first** — upload всегда `private`; public только через `helios approve`.
4. **Human gate** — оператор смотрит видео в Studio перед approve.
5. **Fail-soft** — если HELIOS упал, Factory и DIOSCURI работают дальше.

## Возможности

| Возможность | Описание |
|-------------|----------|
| Очередь | Idempotency, дневной лимит (~9/день), crash-safe lock |
| Рендер | TTS (`say` на macOS) + ffmpeg + субтитры |
| YouTube API | Resumable upload, SRT, плейлисты |
| Backfill | Загрузка уже отрендеренных эпизодов из PromoMaterials |
| Director | LLM-ревью метаданных (DeepSeek) — **не пишет VO** |
| Alien Monitor | Кешированная статистика канала на узле графа |
| Audit | Append-only `data/audit.jsonl` |

## Быстрый старт

```bash
cd helios
pip install -e ".[dev]"
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env
# YOUTUBE_CLIENT_SECRET, YOUTUBE_TOKEN, DEEPSEEK_API_KEY

helios auth
docker compose up -d --build
# обязательно: hourly worker (serve alone is not enough)
(crontab -l 2>/dev/null; echo "0 * * * * docker exec helios helios worker >> /var/log/helios-worker.log 2>&1") | crontab -

helios backfill-scan
helios backfill-enqueue -n 10
docker exec helios helios worker
helios approve job_backfill_e10
```

## Документация

| Документ | Описание |
|----------|----------|
| [docs/setup-ru.md](docs/setup-ru.md) | Установка, OAuth, Docker |
| [docs/usage-ru.md](docs/usage-ru.md) | CLI, расписание, Director |
| [docs/architecture-ru.md](docs/architecture-ru.md) | Архитектура и модель данных |
| [docs/security-ru.md](docs/security-ru.md) | Модель угроз и контроли |
| [docs/runbook-ru.md](docs/runbook-ru.md) | Runbook оператора |

## Место в экосистеме

```
aicom           → строит продукты
dioscuri        → Q&A + KERYX (текст)
PromoMaterials  → сценарии и ассеты
helios          → рендер + YouTube  ← вы здесь
alien-monitor   → 3D-граф + live stats
```

## Лицензия

MIT — [LICENSE](LICENSE).
