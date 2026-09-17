# HELIOS — couche de diffusion de l’écosystème AIMarket

> 🌐 [English](README.md) · [Русский](README-ru.md) · [Español](README-es.md) · **Français** · [中文](README-zh.md) · [Glossaire](https://github.com/alexar76/aicom/blob/main/docs/localization-glossary.md)


> **Template en entrée → vidéo voisée → file YouTube — private by default jusqu’à approve.**  
> MIT · auto-hébergé · publication seule · pas de bots d’engagement.

**Landing :** [alexar76.github.io/helios](https://alexar76.github.io/helios/) · **GitHub :** [alexar76/helios](https://github.com/alexar76/helios) · **YouTube :** [@My-AI-Factory](https://www.youtube.com/@My-AI-Factory)

| | |
|---|---|
| **Rôle** | Rendu MP4 depuis des templates yaml → upload YouTube (private by default) → approve opérateur → public |
| **Monitor** | [Alien Monitor](https://monitor.modelmarket.dev/) — clic sur **HELIOS** → stats chaîne |
| **Intégration** | [helios-integration.md](https://github.com/alexar76/aicom/blob/main/docs/ecosystem/helios-integration.md) |

## Pourquoi HELIOS

L’écosystème `alexar76` change en continu : releases, oracles, cours, showcases. Le pipeline manuel PromoMaterials ne scale pas. **HELIOS** est le satellite de diffusion : file de jobs, audit log, human gate avant publication.

```
PromoMaterials (contenu)  →  HELIOS (moteur)  →  YouTube (private)  →  approve  →  public
DIOSCURI (release)        →  shared queue     →  helios worker
```

## Charter (règles obligatoires)

1. **POST-only** — uniquement sa propre chaîne ; aucun like/commentaire/follow.
2. **Template-only** — vidéos uniquement depuis yaml validés ; VO fixé dans le template.
3. **Private-first** — upload toujours `private` ; public seulement via `helios approve`.
4. **Human gate** — l’opérateur visionne dans Studio avant approve.
5. **Fail-soft** — si HELIOS tombe, Factory et DIOSCURI continuent.

## Capacités

| Capacité | Description |
|-------------|----------|
| File | Idempotency, plafond journalier (~9/jour), lock crash-safe |
| Rendu | TTS (`say` sur macOS) + ffmpeg + sous-titres |
| YouTube API | Upload resumable, SRT, playlists |
| Backfill | Upload d’épisodes déjà rendus depuis PromoMaterials |
| Director | Revue LLM des métadonnées (DeepSeek) — **n’écrit pas** la VO |
| Alien Monitor | Stats de chaîne en cache sur le nœud du graphe |
| Audit | `data/audit.jsonl` append-only |

## Démarrage rapide

```bash
cd helios
pip install -e ".[dev]"
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env
helios auth
docker compose up -d --build
helios backfill-scan
helios backfill-enqueue -n 10
docker exec helios helios worker
helios approve job_backfill_e10
```

## Documentation

| Doc | Description |
|----------|----------|
| [docs/setup.md](docs/setup.md) / setup-ru | Install, OAuth, Docker |
| [docs/usage.md](docs/usage.md) | CLI, planning, Director |
| [docs/architecture.md](docs/architecture.md) | Architecture |
| [docs/security.md](docs/security.md) | Menaces & contrôles |
| [docs/runbook.md](docs/runbook.md) | Runbook opérateur |

## Place dans l’écosystème

```
aicom           → construit les produits
dioscuri        → Q&A + KERYX (texte)
PromoMaterials  → scripts & assets
helios          → rendu + YouTube  ← vous êtes ici
alien-monitor   → graphe 3D + live stats
```

## Licence

MIT — [LICENSE](LICENSE).
