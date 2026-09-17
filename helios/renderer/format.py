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


def _reject_still_card_crop(candidate: str | None, landscape: str | None) -> str | None:
    """If *-shorts is a 9:16 crop of a left-aligned thesis card, use landscape (scale-pad).

    Cropping “Not docs. Rooms.” into 9:16 clips to “ooms.” Native still_card()
    siblings are kept; a detected crop falls back to the 16:9 file.
    """
    if not candidate or not landscape or candidate == landscape:
        return candidate
    try:
        from helios.renderer.still_pipeline import is_text_card_crop

        cand = Path(str(candidate))
        land = Path(str(landscape))
        if not cand.is_file() or not land.is_file():
            return candidate
        if cand.resolve() == land.resolve():
            return candidate
        if is_text_card_crop(cand, land):
            return str(land)
    except (OSError, ValueError, ImportError):
        return candidate
    return candidate


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

    A 9:16 *crop* of a left-aligned still card is rejected: it clips type
    (“Not docs. Rooms.” → “ooms.”). Native *-shorts.jpg from still_card() is kept.
    """
    path = visual.get("path")
    if FORMAT != "shorts":
        return path

    chosen: str | None = None
    explicit = visual.get("path_shorts")
    if explicit:
        if resolve_rel is not None and not Path(str(explicit)).is_absolute():
            try:
                chosen = str(resolve_rel(str(explicit)))
            except (FileNotFoundError, ValueError):
                chosen = None  # explicit shorts missing/unsafe → fall back to sibling/base
        else:
            chosen = str(explicit)

    if chosen is None:
        if not path:
            return path
        p = Path(str(path))
        alt = p.with_name(f"{p.stem}-shorts{p.suffix}")
        if alt.is_file():
            chosen = str(alt)
        elif resolve_rel is not None and not p.is_absolute():
            try:
                chosen = str(resolve_rel(str(alt)))
            except (FileNotFoundError, ValueError):
                chosen = None
        if chosen is None:
            chosen = path

    return _reject_still_card_crop(chosen, path if path is None else str(path))
