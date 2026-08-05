"""Episode renderer — port of PromoMaterials build_series.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from helios.config import HeliosConfig


def load_template(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def render_script(
    cfg: HeliosConfig,
    script_path: Path,
    vars: dict[str, str],
    out_dir: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Path]:
    """Render CALLIOPE-generated script yaml to video.mp4 + video.srt."""
    data = load_template(script_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return {"video": out_dir / "video.mp4", "srt": out_dir / "video.srt"}

    from helios.renderer.episode import build_from_template

    return build_from_template(cfg, data, vars, out_dir)


def render_template(
    cfg: HeliosConfig,
    template_path: Path,
    vars: dict[str, str],
    out_dir: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Path]:
    """Render template to video.mp4 + video.srt. Returns paths."""
    return render_script(cfg, template_path, vars, out_dir, dry_run=dry_run)
