# HELIOS — arquitectura

🌐 [English](architecture.md) · [Русский](architecture-ru.md)

Módulos separados (~250 líneas máx.): `queue`, `worker`, `renderer`, `youtube`, `director`, `security`.

Estados del job: `pending` → `rendering` → `uploading` → `awaiting_approval` → `published`.

Integraciones: Alien Monitor (`/health`), DIOSCURI (cola jsonl), PromoMaterials (backfill).
