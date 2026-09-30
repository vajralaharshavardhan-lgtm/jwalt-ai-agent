"""S04 ENGINEERING (12.0-16.0 s): the space as a coordinated system.
An exploded axonometric of the fit-out: floor finishes, walls/partitions/
joinery, ceilings/lighting and MEP services separate vertically as
translucent layers of precise linework, each named with a restrained
leader and label, then settle back together. Pure vector: it rhymes with
the opening drawing and reads as engineering, not as a render."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import skia

from .. import config, easing as E
from ..camera import CamPath, CamState
from ..graphics import titles
from ..scene.dims import AXIS_X, XP, XW, Z_CEIL
from .base import Cue, Shot as _Shot

T0, T1 = 12.0, 16.0
CENTER = np.array([AXIS_X + 0.4, 4.5, 3.6])
SEP = (12.35, 13.75)       # layers separate
JOIN = (14.95, 15.85)      # layers settle back
DRAW_ON = (12.0, 12.55)

# (key, label, z offset when exploded)
LAYERS = [("floor", "FLOOR FINISHES", 0.0), ("walls", "WALLS · PARTITIONS · JOINERY", 1.5),
          ("ceiling", "CEILINGS · LIGHTING", 4.1), ("mep", "MEP SERVICES", 5.6)]


def _orbit(az, el, dist, vfov, shift=3.4, lift=-0.4):
    """Camera on an orbit around the model; the aim point is pushed to the
    camera's right so the model sits left of centre, leaving the right third
    for the layer labels."""
    a, e = np.radians(az), np.radians(el)
    pos = CENTER + dist * np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])
    fwd = (CENTER - pos) / np.linalg.norm(CENTER - pos)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    aim = CENTER + right * shift + np.array([0, 0, 2.4 + lift])
    return CamState.look(tuple(pos), tuple(aim), vfov)


PATH = CamPath([(T0, _orbit(-34.0, 27.0, 30.5, 38.0, lift=-1.9)), (T1, _orbit(-20.0, 31.0, 29.0, 37.0, lift=-1.9))],
               ease=E.cubic_bezier(0.3, 0.0, 0.3, 1.0))
REFRAME = {"9x16": {"yaw": 9.0, "fov_scale": 1.55}, "1x1": {"yaw": 4.0}}


@lru_cache(maxsize=1)
def layer_lines():
    d = np.load(config.LINEWORK)
    segs, owner = d["segs"].astype(np.float64), d["owner"]
    names, groups, lays = d["names"].astype(str), d["groups"].astype(str), d["layers"].astype(str)
    key = np.full(len(names), "", dtype=object)
    for k, (n, g, L) in enumerate(zip(names, groups, lays)):
        if g in ("site", "boards", "exterior", "furniture") or L in ("exterior",) or n.startswith(("sheer", "curtain")):
            continue
        if n.startswith(("tile_", "screed", "skirting")):
            key[k] = "floor"
        elif g == "mep" or L == "mep":
            key[k] = "mep"
        elif L in ("ceiling", "lighting") or n.startswith("slat_") or (g == "framing" and n.startswith("ceil_")):
            key[k] = "ceiling"
        elif L in ("walls", "facade", "partition", "joinery") and not n.startswith(("terrace", "facade_spandrel")):
            key[k] = "walls"
    out = {}
    for lk, _, _ in LAYERS:
        m = key[owner] == lk
        s = segs[m].copy()
        if lk == "walls":
            s[:, :, 2] = np.clip(s[:, :, 2], 0.0, Z_CEIL)
        out[lk] = s
    return out


def _explode(t):
    return float(E.ARCH(E.lin(*SEP, t))) * (1 - float(E.in_out_cubic(E.lin(*JOIN, t))))


class Shot(_Shot):
    id = "s04_engineering"
    reframe = REFRAME

    def cam(self, t):
        return PATH(t)

    def draw(self, t, g):
        L = layer_lines()
        ex = _explode(t)
        on = float(E.out_cubic(E.lin(*DRAW_ON, t)))
        out = 1 - float(E.smoothstep(E.lin(15.55, 15.98, t)))
        vis = on * out
        if vis <= 0.002:
            return
        # translucent planes first (painter's order bottom -> top), then linework
        fills = [("floor", np.array([[XW, 0.0, 0.0], [XP, 0.0, 0.0], [XP, 9.2, 0.0], [XW, 9.2, 0.0]])),
                 ("ceiling", np.array([[XW, 0.0, Z_CEIL], [XP, 0.0, Z_CEIL], [XP, 9.0, Z_CEIL], [XW, 9.0, Z_CEIL]]))]
        for i, (key, label, dz) in enumerate(LAYERS):
            z = dz * ex
            for fk, poly in fills:
                if fk == key:
                    self._fill(g, poly + np.array([0, 0, z]), g.pal["line"], 0.07 * vis)
            s = L[key].copy()
            s[:, :, 2] += z
            n = len(s)
            # draw-on bottom-up in the first half second
            prog = None
            if on < 1:
                zz = (s[:, :, 2].min(1) - s[:, :, 2].min()) / max(np.ptp(s[:, :, 2]), 1e-3)
                prog = np.clip((on * 1.6 - zz * 0.6), 0, 1)
            g.lines3d(s, g.pal["line"], width=0.7, alpha=0.78 * vis, progress=prog, glow=1.0, glow_alpha=0.18,
                      fade_depth=(24.0, 48.0))
            self._label(g, t, i, key, label, z, vis)
        titles.chapter(g, "ENGINEERING", t, 12.55, 14.75, y_frac=0.9 if g.fmt.key == "16x9" else None)

    def _fill(self, g, poly, color, alpha):
        P, D, valid = g.project_segments(np.stack([poly, np.roll(poly, -1, 0)], 1))
        if not valid.all() or alpha <= 0.002:
            return
        path = skia.Path()
        path.moveTo(*map(float, P[0, 0]))
        for p in P[:, 1]:
            path.lineTo(float(p[0]), float(p[1]))
        path.close()
        g.dirty = True
        g.c.drawPath(path, g.paint(color, alpha, fill=True))

    def _label(self, g, t, i, key, label, z, vis):
        t_in = 12.95 + 0.17 * i
        t_out = 14.95 - 0.08 * (3 - i)
        a = float(E.smoothstep(E.lin(t_in, t_in + 0.4, t))) * (1 - float(E.smoothstep(E.lin(t_out, t_out + 0.35, t)))) * vis
        if a <= 0.01:
            return
        zref = {"floor": 0.0, "walls": 1.4, "ceiling": Z_CEIL, "mep": 4.3}[key]
        # anchor on the model's right-hand (east) edge, mid-depth
        anchor = np.array([XP, 4.5, zref + z])
        x, y, d = g.view.project(anchor)
        if d <= 0:
            return
        u = g.u
        col = g.pal["accent"]
        vertical = g.fmt.key == "9x16"
        x_text = g.W * (0.70 if g.fmt.key == "16x9" else 0.66) if not vertical else g.W - 64 * u
        grow = float(E.out_expo(E.lin(t_in, t_in + 0.5, t)))
        xe = x + (x_text - 14 * u - x) * grow
        g.line2d((x, y), (xe, y), col, alpha=0.75 * a, width=0.7)
        g.c.drawCircle(float(x), float(y), 2.2 * u, g.paint(col, a, fill=True))
        g.dirty = True
        if vertical:
            g.text(f"{i + 1:02d}", x_text, y + 4 * u, role="label", size=12, color=g.pal["warm_white"], alpha=a, align="left",
                   tracking=0.2)
            return
        g.text(f"{i + 1:02d}", x_text, y - 10 * u, role="label", size=11, color=g.pal["line_dim"], alpha=a, align="left",
               tracking=0.2)
        g.text(label, x_text, y + 12 * u, role="label", size=13, color=g.pal["warm_white"], alpha=a, align="left",
               tracking=0.3)

    def cues(self):
        c = [Cue(T0, "cut_hit", 0.9), Cue(12.0, "draw_texture", 0.7, {"dur": 0.55}), Cue(SEP[0], "mech_rise", 1.0, {"dur": SEP[1] - SEP[0]}),
             Cue(12.55, "title_in", 0.8)]
        c += [Cue(12.95 + 0.17 * i, "tick", 0.55) for i in range(len(LAYERS))]
        c += [Cue(JOIN[0], "mech_fall", 0.9, {"dur": JOIN[1] - JOIN[0]}), Cue(JOIN[1] - 0.06, "lock", 0.9)]
        return c
