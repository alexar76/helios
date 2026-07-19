"""Core episode build — TTS + ffmpeg + subtitles."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from helios.config import HeliosConfig
from helios.renderer import tts as tts_mod
from helios.renderer import visuals as vis_mod
from helios.renderer.subtitles import build_srt, overlay_caption
from helios.security import resolve_asset_path, safe_subprocess_arg, substitute_vars


def _run(cmd: list[str]) -> None:
    safe = [safe_subprocess_arg(str(c)) for c in cmd]
    subprocess.run(safe, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _mux_av(video: Path, audio: Path, out: Path) -> None:
    _run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(audio),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out),
    ])


def _concat(parts: list[Path], out: Path) -> None:
    lst = out.with_suffix(".txt")
    with lst.open("w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    lst.unlink(missing_ok=True)


def build_from_template(
    cfg: HeliosConfig,
    template: dict[str, Any],
    vars: dict[str, str],
    out_dir: Path,
) -> dict[str, Path]:
    defaults = template.get("defaults", {})
    voice = defaults.get("voice", "Daniel")
    rate = int(defaults.get("voice_rate", 175))
    work = out_dir / ".work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    parts: list[Path] = []
    srt_entries: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for idx, seg in enumerate(template.get("segments", []), 1):
        vo = substitute_vars(seg["vo"].strip(), vars)
        caption = substitute_vars(seg.get("caption", vo).strip().upper(), vars)
        visual = dict(seg.get("visual", {}))
        if "path" in visual:
            rel = substitute_vars(visual["path"], vars)
            visual["path"] = str(resolve_asset_path(rel, cfg.asset_roots))
        if visual.get("type") == "card" and "text" in visual:
            visual["text"] = substitute_vars(visual["text"], vars)

        wav = work / f"{idx:02d}.wav"
        dur = tts_mod.tts_wav(vo, voice, rate, wav) + 0.25
        vis = work / f"{idx:02d}_v.mp4"
        vis_mod.make_visual(visual, dur, vis)
        mux = work / f"{idx:02d}_mux.mp4"
        _mux_av(vis, wav, mux)
        seg_out = work / f"{idx:02d}_seg.mp4"
        overlay_caption(mux, caption, seg_out)
        parts.append(seg_out)
        srt_entries.append((t_cursor, t_cursor + dur, caption))
        t_cursor += dur

    raw = work / "raw.mp4"
    _concat(parts, raw)
    video = out_dir / "video.mp4"
    shutil.copy2(raw, video)
    srt = out_dir / "video.srt"
    srt.write_text(build_srt(srt_entries), encoding="utf-8")
    meta = {"duration": round(t_cursor, 2), "template": template.get("id")}
    (out_dir / "video.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    return {"video": video, "srt": srt}
