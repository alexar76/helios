#!/usr/bin/env python3
"""Migrate upload_state.json from PromoMaterials into HELIOS data dir."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate PromoMaterials YouTube state to HELIOS")
    parser.add_argument("--promo", type=Path, default=Path("../PromoMaterials/youtube/ecosystem-series"))
    parser.add_argument("--helios-data", type=Path, default=Path("./data"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    promo = args.promo.resolve()
    target = args.helios_data / "upload_state.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    merged: dict = {"videos": {}, "playlists": {}, "daily": {"date": "", "upload_count": 0}}

    for name in ("upload_state.json", "upload_state_season2.json"):
        src = promo / name
        if not src.exists():
            continue
        state = json.loads(src.read_text(encoding="utf-8"))
        merged["videos"].update(state.get("videos", {}))
        for k, v in state.get("playlists", {}).items():
            merged["playlists"].setdefault(k, v)
        print(f"  merged {src.name}: {len(state.get('videos', {}))} videos")

    if args.dry_run:
        print(f"Would write {target} with {len(merged['videos'])} videos")
        return

    if target.exists():
        backup = target.with_suffix(".json.bak")
        shutil.copy2(target, backup)
        print(f"  backup → {backup}")

    target.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Migrated → {target} ({len(merged['videos'])} videos, {len(merged['playlists'])} playlists)")


if __name__ == "__main__":
    main()
