"""Automated QA for rendered frames (keyframes now, full renders later).

Checks per frame:
  format       1920x1080, fully opaque
  black        share of near-black pixels (flags black / failed frames)
  fringing     colour off the paper<->ink axis inside type-only regions
               (catches LCD subpixel antialiasing on text)
  safe area    type/ink pixels in type-only regions must sit inside the 5%
               action-safe box
  logo edge    10-90% edge transition width across the wordmark (end frame)

Usage: python analysis/qa_frames.py output/keyframes/*.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PAPER = np.array([0xF2, 0xF0, 0xEB], float)
INK = np.array([0x1D, 0x1D, 0x1B], float)
RED = np.array([0xBE, 0x1B, 0x20], float)
SAFE = (96, 54, 1824, 1026)            # x0, y0, x1, y1 (5% action-safe)

# type-only regions per keyframe (where no photograph is expected)
REGIONS = {
    "kf1": [(0, 0, 830, 1080)],
    "kf2": [(0, 0, 830, 1080)],
    "kf3": [(0, 0, 1920, 1080)],
    "kf4": [(0, 0, 1920, 1080)],
}


def axis_residual(px):
    """Distance of each colour from the paper-ink line (0 = pure neutral type)."""
    d = INK - PAPER
    v = px - PAPER
    t = np.clip((v @ d) / (d @ d), 0, 1)[..., None]
    return np.linalg.norm(v - t * d, axis=-1)


def edge_width(gray_row):
    """10-90% transition width (px) of the steepest edge in a 1-D profile."""
    g = gray_row.astype(float)
    k = int(np.argmax(np.abs(np.diff(g))))
    lo, hi = max(0, k - 6), min(len(g), k + 8)
    seg = g[lo:hi]
    a, b = seg.min(), seg.max()
    if b - a < 60:
        return None
    n = (seg - a) / (b - a)
    if n[0] > n[-1]:
        n = n[::-1]
    x = np.arange(len(n))
    return float(np.interp(0.9, n, x) - np.interp(0.1, n, x))


def check(path):
    im = Image.open(path)
    rgba = np.asarray(im.convert("RGBA")).astype(float)
    px = rgba[..., :3]
    key = Path(path).stem[:3]
    out = {"file": Path(path).name}
    out["format"] = f"{im.width}x{im.height} {'opaque' if rgba[..., 3].min() == 255 else 'HAS ALPHA'}"
    lum = px @ np.array([0.2126, 0.7152, 0.0722])
    out["near_black_%"] = round(float((lum < 16).mean() * 100), 3)

    fr, unsafe = [], 0
    for (x0, y0, x1, y1) in REGIONS.get(key, []):
        reg = px[y0:y1, x0:x1]
        res = axis_residual(reg)
        red = np.linalg.norm(reg - RED, axis=-1) < 60          # the logo / datum are allowed colour
        # also allow the antialiased blend of red into paper
        v = reg - PAPER
        d = RED - PAPER
        t = np.clip((v @ d) / (d @ d), 0, 1)[..., None]
        on_red_axis = np.linalg.norm(v - t * d, axis=-1) < 8
        mask = ~(red | on_red_axis)
        fr.append(float(np.percentile(res[mask], 99.9)))
        inkish = (np.linalg.norm(reg - PAPER, axis=-1) > 40)
        ys, xs = np.nonzero(inkish)
        xs, ys = xs + x0, ys + y0
        unsafe += int(((xs < SAFE[0]) | (xs > SAFE[2]) | (ys < SAFE[1]) | (ys > SAFE[3])).sum())
    out["fringe_p99.9"] = round(max(fr), 2) if fr else None
    out["ink_outside_safe_px"] = unsafe

    if key == "kf4":
        gray = lum
        rows = [int(r) for r in np.linspace(445, 510, 14)]
        widths = [w for r in rows if (w := edge_width(gray[r, 640:1340])) is not None]
        out["logo_edge_10_90_px"] = round(float(np.median(widths)), 2) if widths else None
    return out


def main(files):
    bad = False
    for f in files:
        r = check(f)
        flags = []
        if "HAS ALPHA" in r["format"] or not r["format"].startswith("1920x1080"):
            flags.append("FORMAT")
        if r["near_black_%"] > 5:
            flags.append("BLACK")
        if r["fringe_p99.9"] is not None and r["fringe_p99.9"] > 6:
            flags.append("FRINGE")
        if r["ink_outside_safe_px"] > 0:
            flags.append("SAFE-AREA")
        if r.get("logo_edge_10_90_px") and r["logo_edge_10_90_px"] > 1.6:
            flags.append("SOFT-LOGO")
        bad |= bool(flags)
        print(("FAIL " + ",".join(flags) if flags else "ok  "), r)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
