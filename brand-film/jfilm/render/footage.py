"""Real-footage override: replace any shot's picture with a real J-WALT
photograph or video clip, keeping that shot's titles, the film's grade and
grain. Configured in film.yaml:

  overrides:
    s07_hero:
      footage: assets/projects/hero.jpg      # .jpg/.png/.tif or .mp4/.mov
      from: [0.00, 0.00, 1.00, 1.00]         # crop window at shot start (x, y, w, h, normalised)
      to:   [0.04, 0.03, 0.92, 0.92]         # crop window at shot end  (slow push-in)
      offset: 0.0                            # seconds into a video clip
      exposure: 0.0                          # stops

The window is cover-fitted to each output format, so one wide photo serves
16:9, 9:16 and 1:1 (keep the subject near the centre for the vertical cut).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .. import config, easing as E


@lru_cache(maxsize=4)
def _image(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR | cv2.IMREAD_ANYDEPTH)
    if img is None:
        raise FileNotFoundError(path)
    img = img[..., ::-1].astype(np.float32)
    return img / (65535.0 if img.max() > 255 else 255.0)


def _video_frame(path: str, sec: float) -> np.ndarray:
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(sec, 0) * 1000.0)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot read {path} at {sec:.2f}s")
    return fr[..., ::-1].astype(np.float32) / 255.0


def frame(ov: dict, t: float, shot, W: int, H: int) -> np.ndarray:
    """Display-referred RGB (H, W, 3) for the override at film time t."""
    src = str(config.ROOT / ov["footage"])
    u = float(E.in_out_sine((t - shot.start) / max(shot.end - shot.start, 1e-6)))
    if Path(src).suffix.lower() in (".mp4", ".mov", ".m4v", ".mxf"):
        img = _video_frame(src, float(ov.get("offset", 0.0)) + (t - shot.start))
    else:
        img = _image(src)
    ih, iw = img.shape[:2]
    a = np.array(ov.get("from", [0, 0, 1, 1]), float)
    b = np.array(ov.get("to", [0.03, 0.03, 0.94, 0.94]), float)
    x, y, w, h = a + (b - a) * u
    # cover-fit the window to the output aspect
    win_w, win_h = w * iw, h * ih
    target = W / H
    if win_w / win_h > target:
        nw = win_h * target
        x = x * iw + (win_w - nw) / 2
        y = y * ih
        win_w = nw
    else:
        nh = win_w / target
        y = y * ih + (win_h - nh) / 2
        x = x * iw
        win_h = nh
    M = np.array([[W / win_w, 0, -x * W / win_w], [0, H / win_h, -y * H / win_h]], np.float32)
    out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    ev = float(ov.get("exposure", 0.0))
    if ev:
        lin = np.where(out <= 0.04045, out / 12.92, ((out + 0.055) / 1.055) ** 2.4) * 2 ** ev
        out = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    return np.clip(out, 0, 1).astype(np.float32)
