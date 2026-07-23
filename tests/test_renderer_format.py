"""Dual-layout format helpers for HELIOS renderer."""

from __future__ import annotations

from helios.renderer import format as fmt


def test_set_format_landscape() -> None:
    fmt.set_format("16:9")
    assert fmt.FORMAT == "landscape"
    assert (fmt.W, fmt.H) == (1920, 1080)
    assert fmt.caption_bar_h() == 120


def test_set_format_shorts() -> None:
    fmt.set_format("9:16")
    assert fmt.FORMAT == "shorts"
    assert (fmt.W, fmt.H) == (1080, 1920)
    assert fmt.caption_bar_h() == 180
    fmt.set_format("landscape")  # restore


def test_resolve_visual_asset_prefers_shorts_sibling(tmp_path) -> None:
    land = tmp_path / "diagram.png"
    short = tmp_path / "diagram-shorts.png"
    land.write_bytes(b"x")
    short.write_bytes(b"y")
    fmt.set_format("shorts")
    chosen = fmt.resolve_visual_asset({"path": str(land)})
    assert chosen == str(short)
    fmt.set_format("landscape")
    chosen_l = fmt.resolve_visual_asset({"path": str(land)})
    assert chosen_l == str(land)


def test_resolve_visual_asset_explicit_shorts_missing_falls_back(tmp_path) -> None:
    """An explicit path_shorts that fails to resolve must not crash the render:
    it falls back to the sibling *-shorts / base path (documented lookup order)."""
    land = tmp_path / "diagram.png"
    short = tmp_path / "diagram-shorts.png"
    land.write_bytes(b"x")
    short.write_bytes(b"y")

    def raising_resolver(rel: str) -> str:
        raise FileNotFoundError(rel)

    fmt.set_format("shorts")
    chosen = fmt.resolve_visual_asset(
        {"path": str(land), "path_shorts": "nope-shorts.png"},
        resolve_rel=raising_resolver,
    )
    assert chosen == str(short)  # fell back to sibling, did not raise
    fmt.set_format("landscape")
