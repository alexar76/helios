"""Scan PromoMaterials backlog and enqueue backfill upload jobs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from helios.config import HeliosConfig, file_roots
from helios.queue import QueueStore


def _series_dir(cfg: HeliosConfig) -> Path:
    if cfg.promo_materials_dir:
        return cfg.promo_materials_dir / "youtube" / "ecosystem-series"
    for root in cfg.asset_roots:
        candidate = root / "youtube" / "ecosystem-series"
        if candidate.exists():
            return candidate
        candidate = root / "PromoMaterials" / "youtube" / "ecosystem-series"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("PromoMaterials ecosystem-series not found — set promo_materials_dir or asset_roots")


def _load_meta(series: Path, season: int) -> dict[str, Any]:
    name = "upload_metadata.yaml" if season == 1 else "upload_metadata-season2.yaml"
    return yaml.safe_load((series / name).read_text(encoding="utf-8"))


def _load_state(series: Path, season: int) -> dict[str, Any]:
    name = "upload_state.json" if season == 1 else "upload_state_season2.json"
    path = series / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"videos": {}, "playlists": {}}


def _migrate_playlists(store: QueueStore, series: Path) -> None:
    """Import S1 playlist IDs into helios upload_state."""
    s1_state = series / "upload_state.json"
    if not s1_state.exists():
        return
    s1 = json.loads(s1_state.read_text(encoding="utf-8"))
    state = store.load_upload_state()
    for key, pid in (s1.get("playlists") or {}).items():
        state.setdefault("playlists", {})[key] = pid
    store.save_upload_state(state)


def scan_backlog(cfg: HeliosConfig, store: QueueStore) -> list[dict[str, Any]]:
    """Return pending episodes not yet in helios queue or upload state."""
    series = _series_dir(cfg)
    _migrate_playlists(store, series)
    helios_state = store.load_upload_state()
    uploaded = set(helios_state.get("videos", {}).keys())
    existing_jobs = {j.idempotency_key for j in store.list_jobs()}

    pending: list[dict[str, Any]] = []
    for season in (1, 2):
        meta_path = series / ("upload_metadata.yaml" if season == 1 else "upload_metadata-season2.yaml")
        if not meta_path.exists():
            continue
        meta = _load_meta(series, season)
        promo_state = _load_state(series, season)
        promo_uploaded = set(promo_state.get("videos", {}).keys())

        for eid in meta.get("upload_order", []):
            if eid in uploaded or eid in promo_uploaded:
                continue
            ep = meta["episodes"].get(eid)
            if not ep:
                continue
            video = series / ep["video"]
            srt = series / ep["srt"]
            if not video.exists():
                continue
            ikey = f"backfill:s{season}:{eid}"
            if ikey in existing_jobs:
                continue
            pending.append({
                "episode": eid,
                "season": season,
                "video": str(video),
                "srt": str(srt) if srt.exists() else None,
                "youtube": {
                    "title": ep["title"],
                    "description": ep.get("description", ""),
                    "tags": ep.get("tags", []),
                    "playlist": ep.get("playlist"),
                    "privacy": "private",
                },
                "idempotency_key": ikey,
            })
    return pending


def enqueue_backfill(cfg: HeliosConfig, store: QueueStore, *, limit: int | None = None) -> list[str]:
    """Enqueue all pending PromoMaterials episodes as backfill jobs."""
    pending = scan_backlog(cfg, store)
    if limit:
        pending = pending[:limit]
    ids: list[str] = []
    for item in pending:
        job = store.enqueue(
            template="promo-backfill",
            vars={"episode": item["episode"], "season": str(item["season"])},
            youtube=item["youtube"],
            idempotency_key=item["idempotency_key"],
            source="promo-materials",
            render_path=item["video"],
            srt_path=item.get("srt"),
            phase="backfill",
            job_id=f"job_backfill_{item['episode'].lower()}",
        )
        ids.append(job.id)
    return ids
