# HELIOS runbook (RU)

🌐 [English](runbook.md) · [Español](runbook-es.md)

## Worker cron (обязательно)

`docker compose up` **не** запускает worker. Без hourly cron пайплайн молчит (scout, render, upload).

```bash
(crontab -l 2>/dev/null; echo "0 * * * * docker exec helios helios worker >> /var/log/helios-worker.log 2>&1") | crontab -
docker exec helios helios worker --max-jobs 1   # сразу после установки
tail -f /var/log/helios-worker.log
```

## Фаза 1: Backfill PromoMaterials

**Бэклог:** S1 E10–E12 (3) + S2 (28) = **31 эпизод**.

```bash
python3 scripts/migrate_from_promo_materials.py
helios backfill-scan
helios backfill-enqueue -n 10
helios worker
helios approve job_backfill_e10
```

Повторять ~4 дня (9 upload/день).

## Фаза 2: Steady state

```bash
helios enqueue --template release-short --repo aicom --tag v0.5.0 --summary "…"
helios worker
```

## Лимит

YouTube ~6–10 upload/день. HELIOS default: **9/день**. Exit code `2` = лимит, retry завтра.

## Troubleshooting

| Симптом | Решение |
|---------|---------|
| Нет новых видео днями, `pending: 0`, scout due | **Нет cron worker** — см. § Worker cron выше |
| `uploadLimitExceeded` | Подождать 24ч; проверить телефон в Studio |
| `invalidCredentials` | `helios auth` |
| ffmpeg not found | `brew install ffmpeg` |
