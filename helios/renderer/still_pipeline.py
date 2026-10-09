"""Thesis still cards / text tables — never crop 16:9 type into 9:16.

Port of PromoMaterials `_assets/still_pipeline.py`.

Left-aligned thesis cards (`still_card`, `20-thesis.jpg`, “Not docs. Rooms.”)
clip if you crop them to 9:16. Shorts showed “ooms.” / “ipped a page…”.
Row tables (“The sensor was lying.” + four claims) clip the same way: the
right-hand cells disappear under YouTube’s like/share column.

Rules:
  - still_card() writes 16:9 and a native 1080×1920 sibling (*-shorts.jpg).
  - Portrait type stays inside text_safe_rect() (Shorts chrome inset).
  - portrait_from_landscape() is for LIVE UI screenshots only.
  - resolve_visual_asset() refuses a 9:16 file that is a crop of a still card.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

LANDSCAPE = (1920, 1080)
PORTRAIT = (1080, 1920)

_STILL_STEM = re.compile(
    r"(?:^|-)(thesis|even|heat|softstar|soft-star|signed|not-chat|gates|two-doors|"
    r"seventeen|twod|estimate|bom|card|lying|legend|thirty|classes)(?:-shorts)?$",
    re.I,
)

# YouTube Shorts chrome: top search, right like/share, bottom title + caption.
_SAFE_PORTRAIT = (72, 220, 200, 520)  # left, top, right, bottom
_SAFE_LANDSCAPE = (64, 56, 64, 80)

_FONT_CANDIDATES = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", True),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", False),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", True),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", True),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", False),
    ("/Library/Fonts/Arial.ttf", False),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    prefer_bold = [p for p, is_bold in _FONT_CANDIDATES if is_bold == bold]
    rest = [p for p, _ in _FONT_CANDIDATES if p not in prefer_bold]
    for path in prefer_bold + rest:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_safe_rect(size: tuple[int, int]) -> tuple[int, int, int, int]:
    """x, y, max_w, max_h — keep table type off YouTube Shorts chrome."""
    w, h = size
    left, top, right, bottom = _SAFE_PORTRAIT if h > w else _SAFE_LANDSCAPE
    return left, top, max(80, w - left - right), max(80, h - top - bottom)


def _break_word(
    d: ImageDraw.ImageDraw, word: str, fnt: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    chunks: list[str] = []
    cur = ""
    for ch in word:
        trial = cur + ch
        if d.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            if cur:
                chunks.append(cur)
            cur = ch
    if cur:
        chunks.append(cur)
    return chunks or [word]


def wrap_text(d: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=fnt) <= max_width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        if d.textlength(word, font=fnt) > max_width:
            lines.extend(_break_word(d, word, fnt, max_width))
            cur = ""
        else:
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]


def _void(size: tuple[int, int], void: tuple[int, int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    w, h = size
    im = Image.new("RGB", (w, h), void)
    wash = Image.new("RGB", (w, h), void)
    d2 = ImageDraw.Draw(wash)
    cx, cy = w // 2, h // 2
    scale = min(w, h) / 1080
    r0, g0, b0 = void
    for r, a in ((980, 18), (580, 28), (280, 42)):
        rr = int(r * scale)
        d2.ellipse(
            (cx - rr, cy - rr, cx + rr, cy + rr),
            fill=(min(255, r0 + a), min(255, g0 + a), min(255, b0 + a + 8)),
        )
    im = Image.blend(im, wash, 0.55)
    return im, ImageDraw.Draw(im)


def render_still_card(
    dest: Path,
    kicker: str,
    title: str,
    lines: list[tuple[str, tuple[int, int, int]]],
    *,
    accent: tuple[int, int, int],
    ink: tuple[int, int, int],
    void: tuple[int, int, int],
    size: tuple[int, int],
) -> None:
    w, h = size
    portrait = h > w
    x0, y0, max_w, max_h = text_safe_rect(size)
    title_size = 52 if portrait else 48
    body_size = 36 if portrait else 34
    kicker_size = 28
    im: Image.Image | None = None
    for _ in range(8):
        im, d = _void(size, void)
        d.rectangle((0, 0, 8 if portrait else 6, h), fill=accent)
        tf = font(title_size, True)
        bf = font(body_size)
        y = y0
        d.text((x0, y), kicker, font=font(kicker_size), fill=accent)
        y += kicker_size + (28 if portrait else 18)
        for part in wrap_text(d, title, tf, max_w):
            d.text((x0, y), part, font=tf, fill=ink)
            y += title_size + 8
        y += 36 if portrait else 28
        for text, color in lines:
            for part in wrap_text(d, text, bf, max_w):
                d.text((x0, y), part, font=bf, fill=color)
                y += body_size + 16
            y += 14 if portrait else 8
        if y <= y0 + max_h or (title_size <= 36 and body_size <= 26):
            break
        title_size = max(36, title_size - 4)
        body_size = max(26, body_size - 2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert im is not None
    im.save(dest, quality=94)


def still_card(
    dest: Path,
    kicker: str,
    title: str,
    lines: list[tuple[str, tuple[int, int, int]]],
    accent: tuple[int, int, int] = (120, 230, 255),
    *,
    ink: tuple[int, int, int] = (244, 248, 255),
    void: tuple[int, int, int] = (6, 8, 18),
    size: tuple[int, int] | None = None,
    write_shorts: bool = True,
) -> None:
    """Write a 16:9 thesis card and, by default, a native 9:16 sibling.

    Never crop the 16:9 file to make the shorts file.
    """
    dest = Path(dest)
    size = size or LANDSCAPE
    render_still_card(dest, kicker, title, lines, accent=accent, ink=ink, void=void, size=size)
    if write_shorts and size[0] > size[1] and "-shorts" not in dest.stem:
        shorts = dest.with_name(f"{dest.stem}-shorts{dest.suffix}")
        render_still_card(
            shorts, kicker, title, lines, accent=accent, ink=ink, void=void, size=PORTRAIT
        )


def looks_like_still_card(im: Image.Image) -> bool:
    """Left accent bar + dark field = editorial type card, not a UI screenshot."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    if w < 600 or h < 400:
        return False
    bar_w = 4
    bar = rgb.crop((0, h // 6, bar_w, 5 * h // 6))
    field = rgb.crop((48, h // 6, min(w // 3, 480), 5 * h // 6))
    bar_stat = ImageStat.Stat(bar)
    field_stat = ImageStat.Stat(field)
    bar_lum = sum(bar_stat.mean) / 3
    field_lum = sum(field_stat.mean) / 3
    bar_var = sum(bar_stat.var) / 3
    return bar_var < 2500 and bar_lum > field_lum + 18 and field_lum < 80


def _mse(a: Image.Image, b: Image.Image, *, top_frac: float = 1.0) -> float:
    a = a.convert("RGB")
    b = b.convert("RGB").resize(a.size, Image.Resampling.LANCZOS)
    if top_frac < 1:
        h = max(1, int(a.size[1] * top_frac))
        a = a.crop((0, 0, a.size[0], h))
        b = b.crop((0, 0, b.size[0], h))
    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    return sum(m * m for m in stat.mean) / 3.0


def is_text_card_crop(portrait: Path | Image.Image, landscape: Path | Image.Image) -> bool:
    """True when the 9:16 file is a vertical strip cropped from a still card."""
    p_im = portrait.convert("RGB") if isinstance(portrait, Image.Image) else Image.open(portrait).convert("RGB")
    l_im = landscape.convert("RGB") if isinstance(landscape, Image.Image) else Image.open(landscape).convert("RGB")
    pw, ph = p_im.size
    lw, lh = l_im.size
    if lw / max(lh, 1) < 1.3:
        return False
    if pw / max(ph, 1) > 0.72:
        return False
    if not looks_like_still_card(l_im):
        return False
    strip_w = max(1, int(lh * 9 / 16))
    if strip_w >= lw:
        return False
    lefts = {0, (lw - strip_w) // 2}
    for frac in (0.08, 0.12, 0.18, 0.22, 0.28, 0.42):
        lefts.add(max(0, min(lw - strip_w, int(lw * frac))))
    for left in sorted(lefts):
        strip = l_im.crop((left, 0, left + strip_w, lh))
        if _mse(p_im, strip, top_frac=0.45) < 40:
            return True
    return False


def portrait_from_landscape(
    landscape: Path,
    dest: Path,
    *,
    bias: float | str = 0.18,
    force: bool = False,
) -> None:
    """Crop a live UI screenshot to 9:16. Refuses still/thesis cards."""
    src = Path(landscape)
    dest = Path(dest)
    im = Image.open(src).convert("RGB")
    stem = src.stem.replace("-shorts", "")
    if not force and (_STILL_STEM.match(stem) or looks_like_still_card(im)):
        raise SystemExit(
            f"Refusing to crop {src.name} → {dest.name}. "
            "Left-aligned still cards clip in 9:16 (type becomes 'ooms.'). "
            "Use still_pipeline.still_card() which writes a native *-shorts.jpg."
        )
    w, h = im.size
    target = 9 / 16
    if isinstance(bias, str):
        frac = {"left": 0.12, "center": 0.5, "right": 0.88}.get(bias, 0.18)
    else:
        frac = float(bias)
    if w / h > target:
        nw = int(h * target)
        left = max(0, min(w - nw, int(w * frac)))
        im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / target)
        top = (h - nh) // 6
        im = im.crop((0, top, w, min(h, top + nh)))
    im = im.resize(PORTRAIT, Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, quality=94)
