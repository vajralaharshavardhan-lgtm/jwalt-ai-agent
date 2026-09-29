"""Automated QA for the encoded film.

  streams     codec, resolution, frame rate, pixel format, colour tags, audio format
  sync        video vs audio duration (must agree within one frame)
  black       near-black frames
  flashes     single-frame flashes (a frame unlike both neighbours that are alike)
  jumps       large frame-to-frame changes (a hard cut where none is designed)
  stutter     a still frame in the middle of motion (dropped/duplicated frame)
  audio       integrated loudness, true peak, clipped samples
  sheet       contact sheet every 0.5s for visual review

Usage: FFMPEG=/path/to/ffmpeg python analysis/qa_video.py output/film.mp4 [sheet.jpg]
"""
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "audio"))
from score import lufs, true_peak  # noqa: E402

FF = os.environ.get("FFMPEG", "ffmpeg")
W, H = 480, 270


def probe(path):
    err = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    v = re.search(r"Video: (\w+).*?, (\w+)\(([^)]*)\).*?, (\d+)x(\d+).*?, ([\d.]+) fps", err)
    a = re.search(r"Audio: (\w+).*?, (\d+) Hz, (\w+)", err)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return {
        "video": v.groups() if v else None, "audio": a.groups() if a else None,
        "duration": int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else None,
    }


def frames(path):
    raw = subprocess.run([FF, "-v", "error", "-i", path, "-vf", f"scale={W}:{H}:flags=area", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def audio(path):
    data = subprocess.run([FF, "-v", "error", "-i", path, "-vn", "-f", "f32le", "-ac", "2", "-ar", "48000", "-"],
                          capture_output=True).stdout
    return np.frombuffer(data, np.float32).reshape(-1, 2).astype(np.float64)


def main(path, sheet=None):
    info = probe(path)
    fr = frames(path)
    fps = float(info["video"][5]) if info["video"] else 60.0
    n = len(fr)
    g = fr.astype(np.float32).mean(3)
    lum = g.mean((1, 2))
    d = np.r_[0, np.abs(np.diff(g, axis=0)).mean((1, 2))]
    skip = np.r_[0, 0, np.abs(g[2:] - g[:-2]).mean((1, 2))]

    issues = []
    black = np.nonzero(lum < 16)[0]
    if len(black):
        issues.append(f"black frames at {[round(i / fps, 3) for i in black[:10]]}")
    flashes = [i for i in range(1, n - 1) if d[i] > 4 and d[i + 1] > 4 and skip[i + 1] < 0.35 * min(d[i], d[i + 1])]
    if flashes:
        issues.append(f"single-frame flashes at {[round(i / fps, 3) for i in flashes]}")
    jumps = [i for i in range(1, n) if d[i] > 12]
    if jumps:
        issues.append(f"frame jumps (mean change >12/255) at {[round(i / fps, 3) for i in jumps]}")
    moving = (np.r_[d[1:], 0] > 0.15) & (np.r_[0, d[:-1]] > 0.15)
    stutter = [i for i in range(1, n - 1) if moving[i] and d[i] < 0.02]
    if stutter:
        issues.append(f"stutter (still frame inside motion) at {[round(i / fps, 3) for i in stutter[:20]]}")

    a = audio(path)
    loud, tp = lufs(a), 20 * np.log10(true_peak(a))
    clipped = int((np.abs(a) >= 0.999).sum())
    adur = len(a) / 48000
    vdur = n / fps
    if abs(adur - vdur) > 1 / fps + 0.03:        # AAC priming tolerance
        issues.append(f"A/V duration mismatch: video {vdur:.3f}s audio {adur:.3f}s")
    if tp > -1.0:
        issues.append(f"true peak {tp:.2f} dBTP above -1")
    if clipped:
        issues.append(f"{clipped} clipped samples")

    print(f"file      {os.path.basename(path)}  {os.path.getsize(path) / 1e6:.1f} MB  {info['duration']}s")
    print(f"video     {info['video']}  frames {n}  ({vdur:.3f}s)")
    print(f"audio     {info['audio']}  {adur:.3f}s  {loud:.2f} LUFS  true peak {tp:.2f} dBTP")
    print(f"motion    mean change/frame {d.mean():.3f}  max {d.max():.2f} at {np.argmax(d) / fps:.3f}s")
    top = np.argsort(d)[::-1][:6]
    print("largest   " + ", ".join(f"{i / fps:.3f}s:{d[i]:.2f}" for i in sorted(top)))
    print("RESULT    " + ("PASS" if not issues else "ISSUES\n  - " + "\n  - ".join(issues)))

    if sheet:
        step = int(fps / 2)
        idx = list(range(0, n, step))
        cols, tw, th = 8, 320, 180
        rows = -(-len(idx) // cols)
        im = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + 22) + 6), (30, 30, 30))
        dr = ImageDraw.Draw(im)
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        for k, i in enumerate(idx):
            x, y = 6 + (k % cols) * (tw + 6), 6 + (k // cols) * (th + 22)
            im.paste(Image.fromarray(fr[i]).resize((tw, th), Image.LANCZOS), (x, y))
            dr.text((x, y + th + 3), f"{i / fps:.1f}s", fill=(220, 220, 220), font=f)
        im.save(sheet, quality=88)
    return not issues


if __name__ == "__main__":
    ok = main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    sys.exit(0 if ok else 1)
