"""Lens + film finishing. Restraint is the point: every effect here is a
small physical imperfection (defocus, shutter blur, halation, grain,
fall-off) of the kind a cinema camera produces, not a stylised filter."""
from __future__ import annotations

import math

import cv2
import numpy as np


def _disc(r: float) -> np.ndarray:
    R = max(1, int(math.ceil(r)))
    y, x = np.mgrid[-R:R + 1, -R:R + 1]
    d = np.sqrt(x * x + y * y)
    k = np.clip(r + 0.5 - d, 0, 1).astype(np.float32)   # anti-aliased disc
    return k / k.sum()


def depth_of_field(rgb: np.ndarray, depth: np.ndarray, focus: float, coc: np.ndarray,
                   max_coc: float = 28.0) -> np.ndarray:
    """Layered scatter-as-gather DOF in linear light (so highlights bloom
    into proper bokeh discs). coc = CoC diameter (px) per pixel."""
    coc = np.clip(coc, 0, max_coc)
    if coc.max() < 0.75:
        return rgb
    radii = [0.0, 0.8, 1.6, 3.0, 5.0, 8.0, 12.0, 18.0, 28.0]
    radii = [r for r in radii if r <= max_coc + 1e-6]
    r_px = coc * 0.5
    near = depth < focus
    out = np.zeros_like(rgb)
    alpha = np.zeros(rgb.shape[:2], np.float32)

    def layer_masks(side_mask):
        ms = []
        for i, r in enumerate(radii):
            lo = 0.0 if i == 0 else (radii[i - 1] + r) / 2
            hi = (r + radii[i + 1]) / 2 if i + 1 < len(radii) else 1e9
            m = side_mask & (r_px >= lo) & (r_px < hi)
            ms.append((r, m.astype(np.float32)))
        return ms

    # far field: farthest (largest blur) first, then toward focus
    for r, m in reversed(layer_masks(~near)):
        if m.max() == 0:
            continue
        if r < 0.5:
            c, a = rgb * m[..., None], m
        else:
            k = _disc(r)
            c = cv2.filter2D(rgb * m[..., None], -1, k, borderType=cv2.BORDER_REFLECT)
            a = cv2.filter2D(m, -1, k, borderType=cv2.BORDER_REFLECT)
        out = out * (1 - a[..., None]) + c
        alpha = alpha * (1 - a) + a
    # near field on top: from focus outward (nearest objects last)
    for r, m in layer_masks(near):
        if m.max() == 0:
            continue
        if r < 0.5:
            c, a = rgb * m[..., None], m
        else:
            k = _disc(r)
            c = cv2.filter2D(rgb * m[..., None], -1, k, borderType=cv2.BORDER_REFLECT)
            a = cv2.filter2D(m, -1, k, borderType=cv2.BORDER_REFLECT)
        out = out * (1 - a[..., None]) + c
        alpha = alpha * (1 - a) + a
    good = alpha > 1e-4
    out[good] /= alpha[good, None]
    out[~good] = rgb[~good]
    return out


def motion_blur(rgb: np.ndarray, flow: np.ndarray, taps: int = 9) -> np.ndarray:
    """Gather along per-pixel screen motion over the shutter interval."""
    mag = np.sqrt((flow ** 2).sum(-1))
    if mag.max() < 0.35:
        return rgb
    H, W = rgb.shape[:2]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    acc = np.zeros_like(rgb)
    for s in np.linspace(-0.5, 0.5, taps):
        acc += cv2.remap(rgb, gx + flow[..., 0] * s, gy + flow[..., 1] * s, cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)
    return acc / taps


# --- display-space finishing -----------------------------------------------------

def _lum(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def grade(img: np.ndarray, warmth: float = 0.02, contrast: float = 0.06, black: float = 0.012,
          saturation: float = 0.94, split_shadow=(0.0, 0.004, 0.010), split_high=(0.012, 0.004, -0.010)) -> np.ndarray:
    """Gentle print-like grade on display-referred sRGB (0..1)."""
    x = np.clip(img, 0, 1)
    L = _lum(x)[..., None]
    x = L + (x - L) * saturation
    # soft S-curve around mid grey
    x = x + contrast * np.sin((x - 0.5) * np.pi) * 0.5 * (1 - np.abs(2 * x - 1))
    # split tone: cool-neutral shadows, warm highlights (restrained -- no teal/orange)
    w_sh = np.clip(1 - L * 2.2, 0, 1)
    w_hi = np.clip((L - 0.45) * 1.8, 0, 1)
    x = x + w_sh * np.array(split_shadow, np.float32) + w_hi * np.array(split_high, np.float32)
    x = x * (1 + np.array([warmth, warmth * 0.35, -warmth * 0.4], np.float32))
    x = black + x * (1 - black)
    return np.clip(x, 0, 1).astype(np.float32)


def halation(img: np.ndarray, strength: float = 0.18, threshold: float = 0.72) -> np.ndarray:
    """Film halation: bright edges bleed a thin warm-red glow."""
    if strength <= 0:
        return img
    H, W = img.shape[:2]
    s = H / 1080.0
    L = _lum(img)
    bright = np.clip((L - threshold) / (1 - threshold), 0, 1) ** 1.5
    src = img * bright[..., None]
    small = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    g1 = cv2.GaussianBlur(small, (0, 0), 3.0 * s)
    g2 = cv2.GaussianBlur(small, (0, 0), 10.0 * s)
    glow = cv2.resize(0.65 * g1 + 0.35 * g2, (W, H), interpolation=cv2.INTER_LINEAR)
    tint = np.array([1.0, 0.45, 0.22], np.float32)
    return np.clip(img + glow * tint * strength, 0, 1)


def vignette(img: np.ndarray, amount: float = 0.22) -> np.ndarray:
    """Natural lens fall-off, normalised to the half-diagonal so every
    aspect ratio darkens its corners by the same amount."""
    if amount <= 0:
        return img
    H, W = img.shape[:2]
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot(x - W / 2, y - H / 2) / math.hypot(W / 2, H / 2)
    f = 1 - amount * np.clip((r - 0.3) / 0.7, 0, 1) ** 1.6
    return img * f[..., None]


def chromatic(img: np.ndarray, px: float = 0.6) -> np.ndarray:
    """Lateral CA: red scaled out, blue scaled in, by `px` at the corners."""
    if px <= 0:
        return img
    H, W = img.shape[:2]
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    R = math.hypot(cx, cy)
    out = img.copy()
    for ch, k in ((0, px / R), (2, -px / R)):
        mx = cx + (x - cx) * (1 + k)
        my = cy + (y - cy) * (1 + k)
        out[..., ch] = cv2.remap(img[..., ch], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out


def grain(img: np.ndarray, amount: float, frame: int) -> np.ndarray:
    """Luminance-weighted film grain with a little structure (not pixel noise)."""
    if amount <= 0:
        return img
    H, W = img.shape[:2]
    rng = np.random.default_rng(1009 + frame * 7919)
    n = rng.standard_normal((H, W)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 0.65 * H / 1080.0)
    n /= max(n.std(), 1e-6)
    chroma = cv2.GaussianBlur(rng.standard_normal((H, W, 3)).astype(np.float32), (0, 0), 1.2)
    L = _lum(img)
    w = 0.35 + 0.65 * (4 * L * (1 - L))          # strongest in mid-tones
    g = (n[..., None] * 0.85 + chroma * 0.15) * (amount * w)[..., None]
    return np.clip(img + g, 0, 1)
