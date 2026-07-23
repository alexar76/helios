# HELIOS — uso y CLI

🌐 [English](usage.md) · [Русский](usage-ru.md)

## Horario y Director

| Fase | Qué | Cadencia |
|------|-----|----------|
| **Backfill** | Subir renders existentes de PromoMaterials | máx. 9 vídeos/día |
| **Steady** | `release-short` en releases de GitHub | bajo demanda + worker horario |

```bash
helios schedule
```

## Comandos

```bash
helios enqueue --template release-short --repo aicom --tag v0.4.0
helios backfill-enqueue -n 10
helios worker
helios approve job_id
```

## Integración DIOSCURI

```bash
HELIOS_SYNDICATION=1
HELIOS_QUEUE_PATH=/data/helios-queue.jsonl
```
