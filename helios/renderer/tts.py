"""Text-to-speech — macOS say (v1), edge-tts fallback on Linux."""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from helios.security import sanitize_text, safe_subprocess_arg


def _probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def tts_wav(text: str, voice: str, rate: int, out_wav: Path) -> float:
    # VO is prose (THEOROS columns include ';'). Do NOT run it through
    # safe_subprocess_arg — that rejects statement-like punctuation. Feed TTS
    # via a temp file / library API so shell metacharacters never reach argv.
    cleaned = sanitize_text(text, max_len=2000).strip()
    if not cleaned:
        raise ValueError("empty TTS text")
    voice = safe_subprocess_arg(voice)
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    if platform.system() == "Darwin" and shutil.which("say"):
        aiff = out_wav.with_suffix(".aiff")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as fh:
            fh.write(cleaned)
            script_path = Path(fh.name)
        try:
            subprocess.run(
                ["say", "-v", voice, "-r", str(rate), "-f", str(script_path), "-o", str(aiff)],
                check=True,
            )
        finally:
            script_path.unlink(missing_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(aiff), str(out_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        aiff.unlink(missing_ok=True)
        return _probe_duration(out_wav)

    # Linux / Docker: edge-tts if available
    try:
        import asyncio
        import edge_tts  # type: ignore

        async def _gen() -> None:
            communicate = edge_tts.Communicate(cleaned, voice="en-US-GuyNeural", rate=f"+{rate - 150}%")
            mp3 = out_wav.with_suffix(".mp3")
            await communicate.save(str(mp3))
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(mp3), str(out_wav)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            mp3.unlink(missing_ok=True)

        asyncio.run(_gen())
        return _probe_duration(out_wav)
    except ImportError:
        raise RuntimeError("TTS unavailable: macOS say or pip install edge-tts")
