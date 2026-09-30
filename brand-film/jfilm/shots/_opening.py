"""Shared by S01 (VISION) and S02 (DESIGN): one continuous camera move from
the drawing board down into the space, the floor plan, and the rising /
drawing-on wireframe. Keeping it in one module guarantees the two shots are
a single unbroken gesture."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .. import config, easing as E
from ..camera import CamPath, CamState
from ..graphics import plan as PL
from ..scene.dims import AXIS_X, Z_CEIL

# --- the camera: plan view -> swoop -> eye level at the entrance ---------------
PATH = CamPath([
    (0.00, CamState((1.55, 3.25, 38.0), 0.0, -90.0, 28.0)),
    (2.85, CamState((1.45, 3.35, 33.5), 0.0, -90.0, 28.0)),
    (4.15, CamState((0.45, 2.35, 11.0), 0.0, -63.0, 34.0)),
    (5.25, CamState((AXIS_X, 1.30, 3.45), 0.0, -32.0, 40.0)),
    (8.00, CamState((AXIS_X, 0.72, 1.45), 0.0, -0.8, 46.0)),
])


def roll_9x16(t: float) -> float:
    """Vertical cut: the plan is turned 90 degrees so its long side runs up
    the phone screen, then unwinds as the camera tilts into the room."""
    return -90.0 * (1 - E.smootherstep(E.lin(2.75, 4.6, t)))


def plan_phase(t: float) -> float:
    """1 while the camera looks straight down at the drawing, easing to 0."""
    return 1 - float(E.smootherstep(E.lin(2.75, 4.6, t)))


REFRAME = {
    # vertical: plan turned to run up the screen, centred across, pulled back for margins
    "9x16": {"roll": roll_9x16, "dy": lambda t: 1.5 * plan_phase(t), "dz": lambda t: 7.0 * plan_phase(t)},
    "1x1": {"dz": lambda t: 6.5 * plan_phase(t)},
}

# --- timing ---------------------------------------------------------------------
RISE = (2.72, 4.35)          # walls extrude out of the plan
PLAN_FADE = (3.7, 4.7)
DRAW = (3.55, 5.15)          # interior linework draws on, bottom-up
CLAY = (4.95, 6.05)          # surfaces fill in, floor to ceiling
MAT = (6.25, 7.30)           # materials sweep from the back wall toward camera
LINES_OUT = (6.35, 7.25)


@lru_cache(maxsize=1)
def plan_data():
    pl = PL.build()
    segs, ts, te, style = PL.flatten(pl)
    return pl, segs, ts, te, style


STYLE = {  # width px@1080, alpha, colour key, glow
    "wall": (1.35, 1.0, "line", 2.2),
    "line": (1.0, 0.92, "line", 1.6),
    "thin": (0.75, 0.8, "line", 0.0),
    "hair": (0.55, 0.62, "line", 0.0),
    "dash": (0.6, 0.62, "line", 0.0),
    "grid": (0.45, 0.16, "line", 0.0),
    "axis": (0.5, 0.42, "line_dim", 0.0),
    "dim": (0.6, 0.62, "line_dim", 0.0),
}


def draw_plan(g, t: float, fade: float = 1.0):
    if fade <= 0.002:
        return
    pl, segs, ts, te, style = plan_data()
    prog = np.clip((t - ts) / np.maximum(te - ts, 1e-4), 0, 1)
    # "illumination": the drawing brightens and gains a soft glow once complete
    lit = E.smoothstep(E.lin(2.2, 2.9, t))
    for st, (w, a, ck, glow) in STYLE.items():
        sel = style == st
        if not sel.any():
            continue
        g.lines3d(segs[sel], g.pal[ck], width=w, alpha=a * fade * (0.82 + 0.18 * lit), progress=prog[sel],
                  glow=glow * (0.4 + 0.6 * lit), glow_alpha=0.28 + 0.2 * lit, heads=0.9 if st == "wall" else 0.0)
    # poche fills
    for f in pl.fills:
        a = E.smoothstep(E.lin(f.t0, f.t0 + f.dur, t)) * fade * 0.16
        if a > 0.002:
            _fill_poly(g, f.pts, g.pal["line"], a)
    # labels (screen-space, upright)
    for lb in pl.labels:
        a = E.smoothstep(E.lin(lb.t0, lb.t0 + lb.dur, t)) * fade
        if a <= 0.002:
            continue
        x, y, z = g.view.project(np.array([lb.pos[0], lb.pos[1], 0.0]))
        if z <= 0:
            continue
        col = g.pal["line_dim"] if lb.style in ("dim", "dim_v") else g.pal["line"]
        size = lb.size * min(1.0, 30.0 / max(z, 1e-3)) ** 0.0
        g.text(lb.text, float(x), float(y) + size * 0.36 * g.u, role="label", size=size, color=col,
               alpha=a * (0.85 if lb.style == "room" else 0.75), tracking=0.28 if lb.style == "room" else 0.08)


def _fill_poly(g, pts, color, alpha):
    import skia
    P, D, valid = g.project_segments(np.stack([pts, np.roll(pts, -1, 0)], 1))
    if not valid.all():
        return
    path = skia.Path()
    path.moveTo(*map(float, P[0, 0]))
    for p in P[:, 1]:
        path.lineTo(float(p[0]), float(p[1]))
    path.close()
    g.dirty = True
    g.c.drawPath(path, g.paint(color, alpha, fill=True))


# --- 3D wireframe ------------------------------------------------------------------

@lru_cache(maxsize=1)
def linework():
    d = np.load(config.LINEWORK)
    segs = d["segs"].astype(np.float64)
    owner = d["owner"]
    names, groups, layers = d["names"], d["groups"], d["layers"]
    return segs, owner, names, groups, layers


@lru_cache(maxsize=1)
def wire_sets():
    segs, owner, names, groups, layers = linework()
    g = groups[owner]
    L = layers[owner]
    n = names[owner]
    rise = ((g == "shell") & np.isin(L, ["walls", "facade"])) | ((g == "finish") & (L == "partition"))
    ns = n.astype(str)

    def starts(*prefixes):
        m = np.zeros(len(ns), bool)
        for pfx in prefixes:
            m |= np.char.startswith(ns, pfx)
        return m

    rise &= ~starts("fin_")
    interior = (g == "finish") & np.isin(L, ["joinery", "ceiling"]) | (g == "furniture")
    interior |= (g == "finish") & (L == "furniture")
    interior &= ~starts("sheer", "curtain", "meet_bulk")
    # per-object draw start: bottom-up with a gentle left-to-right drift
    lo = np.full(len(names), np.inf)
    xc = np.zeros(len(names))
    for k in range(len(names)):
        m = owner == k
        if m.any():
            lo[k] = segs[m][:, :, 2].min()
            xc[k] = segs[m][:, :, 0].mean()
    zkey = np.clip(lo / Z_CEIL, 0, 1.2)
    start = DRAW[0] + (DRAW[1] - DRAW[0] - 0.35) * (0.78 * zkey + 0.22 * np.clip((xc + 6) / 16, 0, 1))
    return rise, interior, start


def rise_height(t: float) -> float:
    return float(E.ARCH(E.lin(*RISE, t)))


def draw_wire(g, t: float, occlude: bool = False, alpha: float = 1.0):
    if alpha <= 0.002:
        return
    segs, owner, names, groups, layers = linework()
    rise, interior, start = wire_sets()
    h = rise_height(t)
    col = g.pal["line"]
    if h > 0.001:
        s = segs[rise].copy()
        s[:, :, 2] = np.minimum(s[:, :, 2], Z_CEIL + 0.8) * h
        g.lines3d(s, col, width=0.9, alpha=0.9 * alpha, occlude=occlude, glow=1.4, glow_alpha=0.25,
                  fade_depth=(6.0, 40.0))
    st = start[owner[interior]]
    prog = np.clip((t - st) / 0.35, 0, 1)
    if prog.max() > 0:
        # ceiling linework only once the camera is below it (keeps the swoop clean)
        cam_z = g.view.t[2]
        s = segs[interior]
        ceil_obj = s[:, :, 2].min(1) > Z_CEIL - 0.05
        a = np.where(ceil_obj, np.clip((Z_CEIL + 0.5 - cam_z) / 1.0, 0, 1), 1.0) * 0.85 * alpha
        g.lines3d(s, col, width=0.75, alpha=a, progress=prog, occlude=occlude, glow=1.0, glow_alpha=0.22,
                  fade_depth=(5.0, 30.0))
