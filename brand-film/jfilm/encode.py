"""Frames + soundtrack -> deliverables.

16:9 master  : ProRes 422 HQ (.mov, PCM audio)  -- for editing / broadcast handoff
all formats  : H.264 High, CRF 16, BT.709, AAC 320k (.mp4) -- web / social ready
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import config


def _run(cmd):
    print("  $", " ".join(str(c) for c in cmd[:6]), "...")
    subprocess.run([str(c) for c in cmd], check=True)


def encode(fmt_key: str, frames_dir: Path, preview: bool = False):
    cfg = config.load()
    out = config.MASTERS
    out.mkdir(parents=True, exist_ok=True)
    audio = config.AUDIO_OUT / "master.wav"
    have_audio = audio.exists()
    tag = f"JWALT_BrandFilm_{fmt_key}{'_preview' if preview else ''}"
    src = ["-framerate", str(cfg.fps), "-i", str(Path(frames_dir) / "f_%04d.png")]
    aud = ["-i", str(audio)] if have_audio else []
    color = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    mp4 = out / f"{tag}.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", *src, *aud,
          "-c:v", "libx264", "-preset", "slow" if not preview else "fast", "-crf", "16" if not preview else "22",
          "-profile:v", "high", "-pix_fmt", "yuv420p", "-vf", "scale=in_range=full:out_range=tv",
          *color, "-movflags", "+faststart",
          *(["-c:a", "aac", "-b:a", "320k", "-ar", "48000"] if have_audio else []), "-shortest", str(mp4)])
    if fmt_key == "16x9" and not preview:
        mov = out / f"{tag}_ProRes422HQ.mov"
        _run(["ffmpeg", "-y", "-loglevel", "error", *src, *aud,
              "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le", "-vendor", "apl0",
              "-vf", "scale=in_range=full:out_range=tv", *color,
              *(["-c:a", "pcm_s24le"] if have_audio else []), "-shortest", str(mov)])
    print("encoded:", mp4)
    return mp4
