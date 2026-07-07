# HELIOS — capa de broadcast del ecosistema AIMarket

<!-- aicom-readme-badges -->
<p align="center">
  <a href="https://github.com/alexar76/helios/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/alexar76/helios/ci.yml?branch=main&label=CI" alt="CI" /></a>
  <a href="https://github.com/alexar76/helios/actions/workflows/pages.yml"><img src="https://img.shields.io/github/actions/workflow/status/alexar76/helios/pages.yml?branch=main&label=Pages" alt="Pages deploy" /></a>
  <a href="https://alexar76.github.io/helios/"><img src="https://img.shields.io/badge/landing-gallery-e84a1a" alt="Landing" /></a>
  <a href="https://www.youtube.com/@My-AI-Factory"><img src="https://img.shields.io/badge/YouTube-@My--AI--Factory-ff0000" alt="Canal de YouTube" /></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.11-brightgreen.svg" alt="Python >=3.11" />
  <img src="https://img.shields.io/badge/tests-39%20passed-brightgreen" alt="39 tests passed" />
  <a href="docs/badges/coverage.svg"><img src="docs/badges/coverage.svg" alt="Cobertura de tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
</p>
<!-- /aicom-readme-badges -->

> **Plantilla dentro, vídeo con voz fuera, cola en YouTube — privado hasta que apruebes.**  
> MIT · self-hosted · solo publicación · sin bots de engagement.

🌐 **Idioma:** [English](README.md) · [Русский](README-ru.md) · **Español**

**Landing:** [alexar76.github.io/helios](https://alexar76.github.io/helios/) · **GitHub:** [alexar76/helios](https://github.com/alexar76/helios) · **YouTube:** [@My-AI-Factory](https://www.youtube.com/@My-AI-Factory) · [lista de reproducción](https://www.youtube.com/playlist?list=PLQAJcI3MYJxM)

| | |
|---|---|
| **Rol** | Render MP4 desde plantillas yaml → subida a YouTube (private) → approve del operador → public |
| **Monitor** | [Alien Monitor](https://magic-ai-factory.com/monitor/) — clic en **HELIOS** → estadísticas del canal |
| **Integración** | [helios-integration-es.md](https://github.com/alexar76/aicom/blob/main/docs/ecosystem/helios-integration-es.md) |

## Por qué existe HELIOS

El ecosistema `alexar76` cambia constantemente: releases, oráculos, cursos, showcase. El pipeline manual en PromoMaterials no escala. **HELIOS** es el satélite de broadcast dedicado: cola de trabajos, audit log, human gate antes de publicar.

## Charter (reglas obligatorias)

1. **POST-only** — solo nuestro canal; sin likes, comentarios ni bots.
2. **Template-only** — vídeo solo desde yaml verificados; el VO está fijado en la plantilla.
3. **Private-first** — upload siempre `private`; public solo con `helios approve`.
4. **Human gate** — el operador revisa en Studio antes de approve.
5. **Fail-soft** — si HELIOS cae, Factory y DIOSCURI siguen funcionando.

## Inicio rápido

```bash
cd helios
pip install -e ".[dev]"
cp helios.config.example.yaml helios.config.yaml
cp .env.example .env

helios auth
helios backfill-scan
helios backfill-enqueue -n 10
helios worker
helios approve job_backfill_e10
```

## Documentación

| Doc | Descripción |
|-----|-------------|
| [docs/setup-es.md](docs/setup-es.md) | Instalación, OAuth, Docker |
| [docs/usage-es.md](docs/usage-es.md) | CLI, horario, Director |
| [docs/architecture-es.md](docs/architecture-es.md) | Arquitectura y modelo de datos |
| [docs/security-es.md](docs/security-es.md) | Modelo de amenazas |
| [docs/runbook-es.md](docs/runbook-es.md) | Runbook del operador |

## Licencia

MIT — [LICENSE](LICENSE).
