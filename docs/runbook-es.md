# HELIOS runbook (ES)

🌐 [English](runbook.md) · [Русский](runbook-ru.md)

## Fase 1: Backfill

```bash
helios backfill-scan
helios backfill-enqueue -n 10
helios worker
helios approve job_id
```

## Fase 2: Steady

```bash
helios enqueue --template release-short --repo aicom --tag v0.5.0
helios worker
```

Límite: 9 uploads/día. Exit code `2` = límite diario.
