"""The floor plan, generated from the same dimensions as the 3D model and
drawn on the floor plane (z=0), so when the camera tilts the drawing is
already in true perspective and becomes the room.

Every primitive carries its own draw-on timing (film seconds)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..scene.dims import (AXIS_X, CHAIRS, COFFER_OPEN, MEET, MULLIONS_Y, NICHE, PARTITION_Y, SOFA, TABLE_C, XP, XW,
                          Y_PANEL, YB)

Z = 0.0


@dataclass
class Stroke:
    pts: np.ndarray            # (N,3) polyline
    t0: float
    dur: float
    style: str = "line"        # wall | line | thin | hair | dash | axis | dim
    closed: bool = False
    dash: tuple | None = None  # (on, off) metres


@dataclass
class Fill:
    pts: np.ndarray            # (N,3) polygon
    t0: float
    dur: float
    style: str = "poche"


@dataclass
class Label:
    pos: tuple
    text: str
    t0: float
    dur: float = 0.5
    size: float = 13.0
    style: str = "label"


@dataclass
class Plan:
    strokes: list = field(default_factory=list)
    fills: list = field(default_factory=list)
    labels: list = field(default_factory=list)


def P(*xy):
    return np.array([[x, y, Z] for x, y in xy], dtype=np.float64)


def rect(x0, y0, x1, y1):
    return P((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))


def circle(cx, cy, r, n=72, a0=0.0, a1=2 * math.pi):
    a = np.linspace(a0, a1, n)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full_like(a, Z)], -1)


def rot_rect(cx, cy, w, d, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    pts = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2), (-w / 2, -d / 2)]
    return P(*[(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts])


def build() -> Plan:
    pl = Plan()
    S, F, Lb = pl.strokes.append, pl.fills.append, pl.labels.append
    x0n, x1n, _, yback = NICHE

    # 1. the first line: back-wall finished face, drawn outward from the axis
    S(Stroke(P((AXIS_X, Y_PANEL), (XW, Y_PANEL)), 0.42, 0.62, "wall"))
    S(Stroke(P((AXIS_X, Y_PANEL), (XP, Y_PANEL)), 0.42, 0.62, "wall"))

    # 2. structure (cut walls) outlines + poche
    walls = [
        (XW - 0.14, YB, 9.65, 9.3),         # back blockwork
        (XW - 0.14, -0.25, -1.5, 0.0),      # front left
        (0.9, -0.25, 9.65, 0.0),            # front right
        (9.4, -0.25, 9.65, 9.3),            # meeting back
        (XP + 0.02, MEET[2] - 0.2, 9.4, MEET[2]),
        (XP + 0.02, MEET[3], 9.4, MEET[3] + 0.2),
        (XP, -0.25, XP + 0.2, MEET[2] - 0.2),
        (XP, MEET[3] + 0.2, XP + 0.2, YB),
    ]
    for i, (a, b, c, d) in enumerate(walls):
        t0 = 0.92 + 0.07 * i
        S(Stroke(rect(a, b, c, d), t0, 0.55, "wall", closed=True))
        F(Fill(rect(a, b, c, d)[:-1], 2.25 + 0.03 * i, 0.5))
    # niche recess cut into the back wall
    S(Stroke(P((x0n, Y_PANEL), (x0n, yback), (x1n, yback), (x1n, Y_PANEL)), 1.18, 0.4, "wall"))
    # reeded lining (double line) and console
    S(Stroke(P((XW, Y_PANEL + 0.03), (x0n, Y_PANEL + 0.03)), 1.35, 0.5, "thin"))
    S(Stroke(P((x1n, Y_PANEL + 0.03), (XP, Y_PANEL + 0.03)), 1.35, 0.5, "thin"))
    S(Stroke(rect(x0n + 0.12, Y_PANEL + 0.01, x1n - 0.12, yback - 0.03), 1.55, 0.35, "thin", closed=True))

    # 3. facade: glass line, mullions, fins
    S(Stroke(P((XW - 0.085, -0.25), (XW - 0.085, 9.3)), 1.05, 0.6, "thin"))
    S(Stroke(P((XW - 0.095, -0.25), (XW - 0.095, 9.3)), 1.08, 0.6, "hair"))
    for i, y in enumerate(MULLIONS_Y):
        S(Stroke(rect(XW - 0.14, y - 0.03, XW - 0.02, y + 0.03), 1.25 + 0.02 * i, 0.2, "thin", closed=True))
    for i, y in enumerate(np.arange(-0.25, 9.3, 0.5)):
        S(Stroke(rect(XW - 0.62, y - 0.025, XW - 0.18, y + 0.025), 1.45 + 0.012 * i, 0.18, "hair", closed=True))

    # 4. glass partition + meeting room door gap
    S(Stroke(P((XP + 0.005, PARTITION_Y[0]), (XP + 0.005, PARTITION_Y[-1])), 1.3, 0.45, "thin"))
    for i, y in enumerate(PARTITION_Y):
        S(Stroke(rect(XP - 0.03, y - 0.015, XP + 0.04, y + 0.015), 1.45 + 0.02 * i, 0.15, "thin", closed=True))

    # 5. entrance: double doors with swings
    for hinge, sign in ((-1.5, 1), (0.9, -1)):
        tip = hinge + sign * 1.2
        S(Stroke(P((hinge, 0.0), (hinge, 1.2)), 1.5, 0.25, "thin"))
        a0, a1 = (0.0, math.pi / 2) if sign > 0 else (math.pi / 2, math.pi)
        arc = circle(hinge, 0.0, 1.2, 40, a0, a1)
        S(Stroke(arc if sign > 0 else arc[::-1], 1.62, 0.35, "hair"))

    # 6. furniture
    tx, ty = TABLE_C
    S(Stroke(rect(tx - 1.95, ty - 1.45, tx + 1.95, ty + 1.45), 1.62, 0.55, "hair", closed=True))
    S(Stroke(rect(tx - 1.87, ty - 1.37, tx + 1.87, ty + 1.37), 1.66, 0.55, "hair", closed=True))
    sx, sy = SOFA
    S(Stroke(rect(sx - 1.35, sy - 0.49, sx + 1.35, sy + 0.49), 1.7, 0.45, "line", closed=True))
    S(Stroke(P((sx - 1.19, sy - 0.49), (sx - 1.19, sy + 0.49)), 1.9, 0.15, "thin"))
    S(Stroke(P((sx + 1.19, sy - 0.49), (sx + 1.19, sy + 0.49)), 1.9, 0.15, "thin"))
    S(Stroke(P((sx - 1.19, sy + 0.31), (sx + 1.19, sy + 0.31)), 1.95, 0.25, "thin"))
    S(Stroke(P((sx, sy - 0.49), (sx, sy + 0.31)), 2.0, 0.12, "hair"))
    S(Stroke(circle(tx, ty, 0.56), 1.78, 0.4, "line", closed=True))
    S(Stroke(circle(tx - 0.12, ty + 0.08, 0.19, 48), 2.05, 0.25, "hair", closed=True))
    S(Stroke(circle(sx + 1.62, sy - 0.1, 0.22, 48), 1.92, 0.25, "thin", closed=True))
    for k, (cx, cy, rot) in enumerate(CHAIRS):
        S(Stroke(rot_rect(cx, cy, 0.74, 0.72, rot), 1.82 + 0.06 * k, 0.35, "line", closed=True))
        a = math.radians(rot)
        bx, by = cx + 0.30 * math.sin(a), cy - 0.30 * math.cos(a)
        S(Stroke(rot_rect(bx, by, 0.74, 0.13, rot), 1.95 + 0.06 * k, 0.25, "thin", closed=True))
    mt = (7.35, 5.4)
    S(Stroke(rect(mt[0] - 0.55, mt[1] - 1.5, mt[0] + 0.55, mt[1] + 1.5), 1.85, 0.35, "line", closed=True))
    for side in (-1, 1):
        for dy in (-0.95, 0.0, 0.95):
            cx = mt[0] + side * 0.85
            S(Stroke(rect(cx - 0.25, mt[1] + dy - 0.25, cx + 0.25, mt[1] + dy + 0.25), 2.0 + 0.02 * (dy + 1), 0.2, "thin", closed=True))
    S(Stroke(rect(MEET[1] - 0.47, mt[1] - 1.2, MEET[1] - 0.02, mt[1] + 1.2), 2.05, 0.3, "thin", closed=True))

    # 7. above the cut plane (dashed): coffer, slot diffuser
    cx0, cx1, cy0, cy1 = COFFER_OPEN
    S(Stroke(rect(cx0, cy0, cx1, cy1), 1.9, 0.7, "dash", closed=True, dash=(0.22, 0.12)))
    S(Stroke(rect(cx0 - 0.2, cy0 - 0.2, cx1 + 0.2, cy1 + 0.2), 1.98, 0.7, "dash", closed=True, dash=(0.08, 0.1)))
    S(Stroke(P((-5.2, 0.8), (-5.2, 8.2)), 2.05, 0.4, "dash", dash=(0.3, 0.12)))

    # 8. floor tile grid (hairline, very faint) inside the lounge
    for i, x in enumerate(np.arange(XW + 1.2, XP, 1.2)):
        S(Stroke(P((x, 0.0), (x, Y_PANEL)), 1.9 + 0.012 * i, 0.5, "grid"))
    for j, y in enumerate(np.arange(0.6, Y_PANEL, 0.6)):
        S(Stroke(P((XW, y), (XP, y)), 1.95 + 0.008 * j, 0.5, "grid"))

    # 9. grid axes with bubbles, dimension strings, room labels
    axes_x = [("A", XW), ("B", AXIS_X), ("C", XP), ("D", 9.4)]
    axes_y = [("1", 0.0), ("2", 4.5), ("3", YB)]
    ytop, ybot = 10.5, -1.7
    for i, (name, x) in enumerate(axes_x):
        S(Stroke(P((x, ybot), (x, ytop)), 1.95 + 0.05 * i, 0.55, "axis", dash=(0.9, 0.12)))
        S(Stroke(circle(x, ytop + 0.34, 0.34, 48), 2.2 + 0.05 * i, 0.3, "dim", closed=True))
        Lb(Label((x, ytop + 0.34), name, 2.35 + 0.05 * i, size=15))
    xl, xr = -7.9, 11.0
    for i, (name, y) in enumerate(axes_y):
        S(Stroke(P((xl, y), (xr, y)), 2.0 + 0.05 * i, 0.55, "axis", dash=(0.9, 0.12)))
        S(Stroke(circle(xl - 0.34, y, 0.34, 48), 2.25 + 0.05 * i, 0.3, "dim", closed=True))
        Lb(Label((xl - 0.34, y), name, 2.4 + 0.05 * i, size=15))

    def dim_h(xa, xb, y, text, t0):
        S(Stroke(P((xa, y), (xb, y)), t0, 0.4, "dim"))
        for x in (xa, xb):
            S(Stroke(P((x - 0.12, y - 0.12), (x + 0.12, y + 0.12)), t0 + 0.2, 0.12, "dim"))
            S(Stroke(P((x, y - 0.25), (x, y + 0.25)), t0 + 0.1, 0.15, "dim"))
        Lb(Label(((xa + xb) / 2, y + 0.28), text, t0 + 0.25, size=13, style="dim"))

    def dim_v(ya, yb, x, text, t0):
        S(Stroke(P((x, ya), (x, yb)), t0, 0.4, "dim"))
        for y in (ya, yb):
            S(Stroke(P((x - 0.12, y - 0.12), (x + 0.12, y + 0.12)), t0 + 0.2, 0.12, "dim"))
            S(Stroke(P((x - 0.25, y), (x + 0.25, y)), t0 + 0.1, 0.15, "dim"))
        Lb(Label((x - 0.36, (ya + yb) / 2), text, t0 + 0.25, size=13, style="dim_v"))

    dim_h(XW, XP, -1.05, "11 400", 2.15)
    dim_h(XP, 9.4, -1.05, "4 000", 2.25)
    dim_h(x0n, x1n, 9.95, "2 400", 2.3)
    dim_v(0.0, YB, -7.1, "9 000", 2.2)
    Lb(Label((AXIS_X, 2.05), "LOUNGE", 2.3, size=12, style="room"))
    Lb(Label((7.4, 3.0), "MEETING", 2.38, size=12, style="room"))

    # dashes -> expand into strokes with their own sub-timing
    out = []
    for st in pl.strokes:
        if st.dash is None:
            out.append(st)
            continue
        on, off = st.dash
        pts = st.pts
        seglen = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        total = seglen.sum()
        cum = np.concatenate([[0], np.cumsum(seglen)])
        s = 0.0
        while s < total:
            e = min(s + on, total)
            a = _along(pts, cum, s)
            b = _along(pts, cum, e)
            out.append(Stroke(np.array([a, b]), st.t0 + st.dur * s / total, st.dur * (e - s) / total, st.style))
            s = e + off
    pl.strokes = out
    return pl


def _along(pts, cum, s):
    i = int(np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(pts) - 2))
    seg = cum[i + 1] - cum[i]
    u = 0.0 if seg < 1e-9 else (s - cum[i]) / seg
    return pts[i] + (pts[i + 1] - pts[i]) * u


def flatten(pl: Plan):
    """All strokes -> flat segment arrays with per-segment draw windows."""
    segs, ts, te, style = [], [], [], []
    for st in pl.strokes:
        pts = st.pts
        L = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        tot = L.sum()
        if tot <= 0:
            continue
        cum = np.concatenate([[0], np.cumsum(L)])
        for i in range(len(pts) - 1):
            segs.append((pts[i], pts[i + 1]))
            ts.append(st.t0 + st.dur * cum[i] / tot)
            te.append(st.t0 + st.dur * cum[i + 1] / tot)
            style.append(st.style)
    return np.array(segs), np.array(ts), np.array(te), np.array(style)
