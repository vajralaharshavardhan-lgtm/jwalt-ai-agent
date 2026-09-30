"""Easing curves. Motion in the film uses a small, consistent vocabulary:
slow architectural in/outs (sine / cubic-bezier) and precise mechanical
settles (expo out). No bounce, no overshoot on typography."""
from __future__ import annotations

import math

import numpy as np


def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def lin(a: float, b: float, t):
    """Normalised position of t inside [a, b], clamped to 0..1."""
    if b <= a:
        return np.where(np.asarray(t) >= b, 1.0, 0.0) if isinstance(t, np.ndarray) else float(t >= b)
    return clamp01((t - a) / (b - a))


def smoothstep(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def smootherstep(x):
    x = clamp01(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def in_out_sine(x):
    x = clamp01(x)
    return 0.5 - 0.5 * np.cos(np.pi * x)


def out_sine(x):
    return np.sin(clamp01(x) * np.pi / 2)


def in_sine(x):
    return 1 - np.cos(clamp01(x) * np.pi / 2)


def out_cubic(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def in_cubic(x):
    return clamp01(x) ** 3


def in_out_cubic(x):
    x = clamp01(x)
    return np.where(x < 0.5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2)


def out_quint(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 5


def out_expo(x):
    x = clamp01(x)
    return np.where(x >= 1, 1.0, 1 - np.power(2.0, -10 * x))


def in_out_expo(x):
    x = clamp01(x)
    return np.where(
        x <= 0, 0.0,
        np.where(x >= 1, 1.0,
                 np.where(x < 0.5, np.power(2.0, 20 * x - 10) / 2, (2 - np.power(2.0, -20 * x + 10)) / 2)))


def cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float):
    """CSS-style cubic-bezier(p1x, p1y, p2x, p2y) easing function."""

    def bez(t, a1, a2):
        return 3 * (1 - t) ** 2 * t * a1 + 3 * (1 - t) * t ** 2 * a2 + t ** 3

    def dbez(t, a1, a2):
        return 3 * (1 - t) ** 2 * a1 + 6 * (1 - t) * t * (a2 - a1) + 3 * t ** 2 * (1 - a2)

    def f(x):
        x = np.asarray(clamp01(x), dtype=np.float64)
        t = x.copy()
        for _ in range(8):  # Newton
            d = dbez(t, p1x, p2x)
            d = np.where(np.abs(d) < 1e-6, 1e-6, d)
            t = clamp01(t - (bez(t, p1x, p2x) - x) / d)
        y = bez(t, p1y, p2y)
        return float(y) if y.ndim == 0 else y

    return f


# The film's two signature curves.
ARCH = cubic_bezier(0.45, 0.0, 0.15, 1.0)     # architectural: patient start, long settle
TYPE = cubic_bezier(0.2, 0.0, 0.0, 1.0)       # typography: quick lift, soft landing


def fade_window(t, t_in, t_out, ramp_in=0.4, ramp_out=0.4, curve=smoothstep):
    """0 -> 1 -> 0 envelope: rises over [t_in, t_in+ramp_in], falls over [t_out-ramp_out, t_out]."""
    return curve(lin(t_in, t_in + ramp_in, t)) * (1 - curve(lin(t_out - ramp_out, t_out, t)))


def mix(a, b, w):
    return a + (b - a) * w


def deg(x):
    return math.radians(x)
