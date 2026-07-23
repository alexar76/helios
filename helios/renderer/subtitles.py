"""Subtitle generation and burn-in."""

from __future__ import annotations

import subprocess
from pathlib import Path

from helios.renderer import format as fmt


def srt_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(entries: list[tuple[float, float, str]]) -> str:
    lines: list[str] = []
    for i, (start, end, text) in enumerate(entries, 1):
        lines += [str(i), f"{srt_time(start)} --> {srt_time(end)}", text, ""]
    return "\n".join(lines)


def make_caption_png(text: str, out_png: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    bar_h = fmt.caption_bar_h()
    img = Image.new("RGBA", (fmt.W, bar_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, fmt.W, bar_h), fill=(11, 14, 23, 210))
    font_size = 44 if fmt.FORMAT == "shorts" else 38
    line_step = 50 if fmt.FORMAT == "shorts" else 44
    max_lines = 3 if fmt.FORMAT == "shorts" else 2
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    words = text.split()
    lines, cur = [], []
    for w in words:
        cur.append(w)
        probe = " ".join(cur)
        bbox = draw.textbbox((0, 0), probe, font=font)
        if bbox[2] - bbox[0] > fmt.W - 80:
            if len(cur) > 1:
                cur.pop()
                lines.append(" ".join(cur))
                cur = [w]
            else:
                lines.append(probe)
                cur = []
    if cur:
        lines.append(" ".join(cur))
    lines = lines[:max_lines]
    y = (bar_h - line_step * len(lines)) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((fmt.W - tw) // 2, y), line, fill=(255, 255, 255, 255), font=font)
        y += line_step
    img.save(out_png)


def overlay_caption(video: Path, caption: str, out: Path) -> None:
    cap_png = video.with_name(video.stem + "_cap.png")
    make_caption_png(caption, cap_png)
    bar_h = fmt.caption_bar_h()
    cmd = [
        "ffmpeg", "-y", "-i", str(video), "-i", str(cap_png),
        "-filter_complex",
        f"[1:v]scale={fmt.W}:{bar_h}[cap];[0:v][cap]overlay=0:{fmt.H-bar_h}:format=auto",
        "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
