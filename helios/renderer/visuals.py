"""Visual segments — video, image, card."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from helios.security import safe_subprocess_arg

W, H = 1920, 1080
FPS = 30


def _run(cmd: list[str]) -> None:
    safe = [safe_subprocess_arg(str(c)) for c in cmd]
    subprocess.run(safe, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def vf_scale_pad() -> str:
    return (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0b0e17"
    )


def kenburns_filter(frames: int) -> str:
    return (
        f"{vf_scale_pad()},"
        f"zoompan=z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS}"
    )


def make_card_image(visual: dict[str, Any], out_png: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    color = visual.get("color", "#0b0e17")
    text = visual.get("text", "")
    h = color.lstrip("#")
    rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    img = Image.new("RGB", (W, H), rgb)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 44)
    except OSError:
        font = ImageFont.load_default()
    lines = text.split("\n")
    y = (H - 56 * len(lines)) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y), line, fill=(230, 233, 242), font=font)
        y += 56
    img.save(out_png)


def make_visual(visual: dict[str, Any], duration: float, out_mp4: Path) -> None:
    vtype = visual.get("type", "video")
    frames = max(1, int(duration * FPS) + 1)

    if vtype == "card":
        png = out_mp4.with_suffix(".png")
        make_card_image(visual, png)
        _run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(png),
            "-vf", vf_scale_pad(), "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "1",
            "-pix_fmt", "yuv420p", "-an", str(out_mp4),
        ])
        return

    path = Path(visual["path"])
    ext = path.suffix.lower()

    if vtype == "image" or ext in {".png", ".jpg", ".jpeg", ".webp"}:
        kb = visual.get("kenburns", True)
        vf = kenburns_filter(frames) if kb else vf_scale_pad()
        _run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(path),
            "-vf", vf, "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "1",
            "-pix_fmt", "yuv420p", "-an", str(out_mp4),
        ])
        return

    inp: list[str] = ["ffmpeg", "-y"]
    if visual.get("loop"):
        inp += ["-stream_loop", "-1"]
    inp += ["-i", str(path)]
    if visual.get("start") is not None:
        inp += ["-ss", str(visual["start"])]
    if visual.get("end") is not None:
        inp += ["-to", str(visual["end"])]
    inp += [
        "-vf", vf_scale_pad(), "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "ultrafast", "-threads", "1",
        "-pix_fmt", "yuv420p", "-an", str(out_mp4),
    ]
    _run(inp)
