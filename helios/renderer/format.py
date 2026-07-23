"""Canvas format — landscape 16:9 or native shorts 9:16 (dual-layout diagrams)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

W = 1920
H = 1080
FORMAT = "landscape"  # or "shorts"


def set_format(fmt: str) -> None:
    """landscape|16:9 → 1920×1080 · shorts|9:16 → 1080×1920."""
    global W, H, FORMAT
    key = (fmt or "landscape").strip().lower()
    if key in {"shorts", "9:16", "portrait", "vertical"}:
        W, H, FORMAT = 1080, 1920, "shorts"
    else:
        W, H, FORMAT = 1920, 1080, "landscape"


def caption_bar_h() -> int:
    return 180 if FORMAT == "shorts" else 120


def resolve_visual_asset(
    visual: dict[str, Any],
    *,
    resolve_rel: Any = None,
) -> str | None:
    """Prefer dual-layout *-shorts.png when FORMAT=shorts.

    Lookup order:
      1. visual.path_shorts (explicit relative or absolute)
      2. sibling *-shorts next to path (foo.png → foo-shorts.png)
      3. visual.path (caller scale-pads into 9:16)
    """
    path = visual.get("path")
    if FORMAT != "shorts":
        return path

    explicit = visual.get("path_shorts")
    if explicit:
        if resolve_rel is not None and not Path(str(explicit)).is_absolute():
            try:
                return str(resolve_rel(str(explicit)))
            except (FileNotFoundError, ValueError):
                pass  # explicit shorts missing/unsafe → fall back to sibling/base (steps 2–3)
        else:
            return str(explicit)

    if not path:
        return path

    p = Path(str(path))
    alt = p.with_name(f"{p.stem}-shorts{p.suffix}")
    if alt.is_file():
        return str(alt)
    if resolve_rel is not None and not p.is_absolute():
        try:
            return str(resolve_rel(str(alt)))
        except (FileNotFoundError, ValueError):
            pass
    return path
