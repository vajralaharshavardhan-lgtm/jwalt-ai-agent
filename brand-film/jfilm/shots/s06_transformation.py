"""S06 TRANSFORMATION (21.5-27.5 s): one continuous dolly into the space
while it completes around us. A completion front travels from the camera to
the back wall; as it passes, each element arrives with a small physical
motion (tiles set down, panels pressed home, ceiling lifted into place,
furniture lowered), site equipment leaves, work lights give way to the
architectural lighting -- the niche glows last."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .. import easing as E
from ..camera import CamPath, CamState
from ..scene.dims import AXIS_X
from ._util import lights, projector, smooth_front, translate
from .base import Cue, LayerSpec, Plate, Shot as _Shot

T0, T1 = 21.5, 27.5
FRONT = (21.6, 25.75)         # front leaves the camera -> reaches the back wall
Y_START, Y_END = 1.3, 9.3

CAM_S = CamState.look((AXIS_X, 0.55, 1.62), (AXIS_X, 9.0, 1.47), 50.0)
CAM_E = CamState.look((AXIS_X, 2.60, 1.40), (AXIS_X, 9.0, 1.40), 45.0)
PATH = CamPath([(T0, CAM_S), (T1, CAM_E)], ease=E.cubic_bezier(0.35, 0.0, 0.25, 1.0))

_u = np.linspace(0, 1, 2001)
FRONT_EASE = E.cubic_bezier(0.3, 0.0, 0.35, 1.0)
_eased = np.asarray(FRONT_EASE(_u))


def front_y(t):
    return Y_START + (Y_END - Y_START) * float(FRONT_EASE(E.lin(*FRONT, t)))


def time_at(y):
    """When the front reaches depth y (inverse of front_y)."""
    v = np.clip((y - Y_START) / (Y_END - Y_START), 0, 1)
    return FRONT[0] + (FRONT[1] - FRONT[0]) * np.interp(v, _eased, _u)


# per-category arrival delays and motions
LAG = {"floor": 0.0, "joinery": 0.12, "walls": 0.10, "partition": 0.14, "ceiling": 0.22, "lighting": 0.30,
       "mep": 0.2, "furniture": 0.50}
DUR = 0.30


@lru_cache(maxsize=1)
def _objects():
    import bpy
    fin, site = [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        g = ob.get("jf_group")
        if g not in ("finish", "furniture", "site", "mep", "framing") or ob.get("jf_glass"):
            continue
        V = np.array([v.co[:] for v in ob.data.vertices])
        if len(V) == 0:
            continue
        M = np.array(ob.matrix_world)
        W = V @ M[:3, :3].T + M[:3, 3]
        yc = float(np.clip(W[:, 1].mean(), -1, 9.5))
        layer = ob.get("jf_layer", "")
        if g == "site":
            site.append((ob.name, float(time_at(yc)) - 0.12, M, True))
        elif g in ("mep", "framing"):
            # rough-in leaves once the finish covering its far end has arrived
            site.append((ob.name, float(time_at(W[:, 1].max())) + 0.4, M, False))
        else:
            cat = "furniture" if g == "furniture" or layer == "furniture" else layer
            T = float(time_at(W[:, 1].min() if layer in ("ceiling", "joinery") else yc)) + LAG.get(cat, 0.15)
            fin.append((ob.name, T, cat, M))
    # a piece of furniture lands as one unit (sofa plinth, body and cushions
    # together), at the time of its nearest part
    first: dict[str, float] = {}
    for name, T, cat, _ in fin:
        if cat == "furniture":
            first[_piece(name)] = min(T, first.get(_piece(name), T))
    fin = [(n, first[_piece(n)] if c == "furniture" else T, c, M) for n, T, c, M in fin]
    return fin, site


def _piece(name: str) -> str:
    """Arrival group. The lounge set (rug, sofa, tables) lands together: the
    rug under the sofa is never seen by any still, so it cannot be shown
    before the sofa sits on it."""
    parts = name.split("_")
    head = parts[1] if parts[0] == "bowl" and len(parts) > 1 else parts[0]
    return "sofa" if head in ("rug", "sofa", "table", "side") else head


def _motion(cat, u, M, name):
    k = 1 - float(E.out_expo(u))
    if cat == "floor":
        return translate(dz=0.03 * k, base=M)
    if cat == "joinery" and name.startswith("reed_"):
        return translate(dy=-0.12 * k, base=M)
    if cat == "ceiling":
        return translate(dz=-0.14 * k, base=M)
    if cat == "furniture":
        return translate(dz=0.09 * k, base=M)
    return translate(dz=0.0, base=M)


class Shot(_Shot):
    id = "s06_transformation"

    def cam(self, t):
        return PATH(t)

    def stills(self):
        A, B = PATH(T0), PATH(T1)
        return [projector("s06_raw_A", A, "raw"), projector("s06_raw_B", B, "raw"),
                projector("s06_empty_A", A, "finished_empty"), projector("s06_empty_B", B, "finished_empty"),
                projector("s06_fin_A", A, "finished"), projector("s06_fin_B", B, "finished")]

    def plate(self, t):
        fin, site = _objects()
        hide, poses, fades = set(), {}, {}
        for name, T, cat, M in fin:
            u = E.lin(T, T + DUR, t)
            if u <= 0:
                hide.add(name)
            elif u < 1:
                poses[name] = _motion(cat, float(u), M, name)
                fades[name] = float(E.smoothstep(E.lin(0, 0.55, u)))
        for name, T, M, visible_exit in site:
            u = E.lin(T, T + 0.25, t)
            if u >= 1:
                hide.add(name)
            elif u > 0 and visible_exit:
                fades[name] = 1 - float(E.smoothstep(u))
        yf = front_y(t)
        wB = float(E.smoothstep(E.lin(T0 + 1.0, T1 - 0.8, t)))
        wA = 1 - wB
        # furniture shadows arrive with the sofa (the piece that casts them)
        t_sofa = min(T for n, T, c, _ in fin if _piece(n) == "sofa")
        wf = float(E.smoothstep(E.lin(t_sofa + 0.1, t_sofa + DUR + 0.15, t)))

        def f(P):
            return smooth_front(P[:, 1], yf, 0.9)

        work = 1 - float(E.smoothstep(E.lin(time_at(3.0), time_at(7.2), t)))
        raw_l = lights(daylight=1.0, work=work)
        cove = [float(E.smoothstep(E.lin(time_at(y), time_at(y) + 0.5, t))) for y in (2.6, 7.4, 4.6, 5.2)]
        fin_l = lights(daylight=1.0, cove_seq=cove,
                       down=float(E.smoothstep(E.lin(time_at(8.3), time_at(8.3) + 0.45, t))),
                       niche=float(E.smoothstep(E.lin(FRONT[1] + 0.05, FRONT[1] + 0.75, t))),
                       meeting=float(E.smoothstep(E.lin(time_at(4.0), time_at(4.0) + 0.5, t))))
        layers = [
            LayerSpec("s06_raw_A", raw_l, lambda P: wA * (1 - f(P)) + 1e-4),
            LayerSpec("s06_raw_B", raw_l, lambda P: wB * (1 - f(P)) + 1e-4),
            LayerSpec("s06_empty_A", fin_l, lambda P: wA * f(P) * (1 - wf) + 1e-4),
            LayerSpec("s06_empty_B", fin_l, lambda P: wB * f(P) * (1 - wf) + 1e-4),
            LayerSpec("s06_fin_A", fin_l, lambda P: wA * f(P) * wf + 1e-4),
            LayerSpec("s06_fin_B", fin_l, lambda P: wB * f(P) * wf + 1e-4),
        ]
        state = {"always", "shell", "mep", "framing", "site", "finish", "furniture", "exterior"}
        return Plate(state, layers, hide=hide, poses=poses, fades=fades, exposure=0.35)

    def post(self, t):
        return {"motion_blur": True}

    def cues(self):
        c = [Cue(T0, "cut", 0.5), Cue(FRONT[0], "transform_bed", 1.0, {"dur": FRONT[1] - FRONT[0] + 1.2})]
        c += [Cue(float(time_at(y)), "lock", 0.28) for y in np.arange(0.8, 9.0, 0.9)]
        c += [Cue(float(time_at(y)), "light_on", 0.4) for y in (2.6, 4.6, 5.2, 7.4)]
        c += [Cue(FRONT[1] + 0.05, "niche_glow", 0.8)]
        return c
