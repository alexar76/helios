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


def test_still_card_native_shorts_is_not_a_crop(tmp_path) -> None:
    from helios.renderer.still_pipeline import is_text_card_crop, still_card

    land = tmp_path / "20-thesis.jpg"
    still_card(
        land,
        "S53 · THE HALL",
        "Not docs. Rooms.",
        [("Seventeen rooms. One family.", (180, 196, 220))],
    )
    short = tmp_path / "20-thesis-shorts.jpg"
    assert short.is_file()
    assert not is_text_card_crop(short, land)

    fmt.set_format("shorts")
    chosen = fmt.resolve_visual_asset({"path": str(land)})
    assert chosen == str(short)
    fmt.set_format("landscape")


def test_cropped_still_card_falls_back_to_landscape(tmp_path) -> None:
    from PIL import Image

    from helios.renderer.still_pipeline import is_text_card_crop, still_card

    land = tmp_path / "20-thesis.jpg"
    still_card(
        land,
        "S53 · THE HALL",
        "Not docs. Rooms.",
        [("Seventeen rooms. One family.", (180, 196, 220))],
        write_shorts=False,
    )
    im = Image.open(land)
    w, h = im.size
    strip_w = int(h * 9 / 16)
    left = int(w * 0.18)
    crop = im.crop((left, 0, left + strip_w, h)).resize((1080, 1920))
    short = tmp_path / "20-thesis-shorts.jpg"
    crop.save(short, quality=94)

    assert is_text_card_crop(short, land)

    fmt.set_format("shorts")
    chosen = fmt.resolve_visual_asset({"path": str(land)})
    assert chosen == str(land)
    fmt.set_format("landscape")


def test_shorts_table_stays_in_safe_rect(tmp_path) -> None:
    from PIL import Image

    from helios.renderer.still_pipeline import PORTRAIT, still_card, text_safe_rect

    dest = tmp_path / "21-lying.jpg"
    still_card(
        dest,
        "THE PROBLEM",
        "The sensor was lying.",
        [
            ("A reading can look confident and still be wrong.", (244, 248, 255)),
            ("If payment lands before plausibility, the lie wins.", (232, 90, 74)),
            ("Oracles without refusal are just telemetry with a tip jar.", (168, 158, 142)),
            ("Refund is part of the product.", (232, 197, 71)),
        ],
    )
    table = Image.open(tmp_path / "21-lying-shorts.jpg")
    assert table.size == PORTRAIT
    x, y, mw, mh = text_safe_rect(PORTRAIT)
    px = table.load()
    overflow = 0
    for yy in range(0, table.size[1], 3):
        for xx in range(12, table.size[0], 3):
            if x <= xx < x + mw and y <= yy < y + mh:
                continue
            r, g, b = px[xx, yy]
            if (r + g + b) / 3 > 140:
                overflow += 1
    assert overflow <= 40, overflow


def test_wrap_text_breaks_overlong_word() -> None:
    from PIL import Image, ImageDraw

    from helios.renderer.still_pipeline import font, wrap_text

    im = Image.new("RGB", (200, 80))
    d = ImageDraw.Draw(im)
    fnt = font(36, True)
    parts = wrap_text(d, "supercalifragilisticexpialidocious", fnt, 120)
    assert len(parts) > 1
    assert all(d.textlength(p, font=fnt) <= 120 for p in parts)
