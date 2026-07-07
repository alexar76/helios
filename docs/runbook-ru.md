# HELIOS runbook (RU)

🌐 [English](runbook.md) · [Español](runbook-es.md)

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
| `uploadLimitExceeded` | Подождать 24ч; проверить телефон в Studio |
| `invalidCredentials` | `helios auth` |
| ffmpeg not found | `brew install ffmpeg` |
