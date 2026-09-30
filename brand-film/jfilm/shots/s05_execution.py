"""S05 EXECUTION (16.0-21.5 s): four locked-off match-cut studies of the
fit-out being built, each ending on a precise mechanical 'lock':
  a) wall: studs -> boards -> reeded oak panels pressed home in a cascade
  b) ceiling: open services -> finished ceiling, a downlight comes on
  c) floor: screed -> stone tiles set in a travelling wave, sun across them
  d) partition: a glass panel slides home in its bronze channel"""
from __future__ import annotations

import numpy as np

from .. import easing as E
from ..camera import CamPath, CamState
from ..graphics import titles
from ._util import lights, projector, translate
from .base import Cue, LayerSpec, Plate, Shot as _Shot

A0, B0, C0, D0, END = 16.0, 17.4, 18.8, 20.2, 21.5

CAM_A = CamState.look((3.62, 6.85, 1.38), (2.0, 8.9, 1.55), 40.0)
CAM_B = CamState.look((-2.15, 6.45, 1.50), (-1.95, 8.15, 3.8), 46.0)
CAM_C = CamState.look((-2.35, 1.15, 0.44), (-4.6, 4.4, 0.02), 40.0)
CAM_D = CamState.look((3.25, 3.05, 1.42), (5.4, 5.3, 1.55), 44.0)
PATHS = [CamPath([(a, c), (b, c.with_(vfov=c.vfov * 0.92))]) for a, b, c in
         ((A0, B0, CAM_A), (B0, C0, CAM_B), (C0, D0, CAM_C), (D0, END, CAM_D))]

# 5a timing
A_BOARD, A_FIN = 16.42, 16.80
PANELS = ["reed_1_0", "reed_1_1", "reed_1_2", "reed_1_3", "reed_1_4", "reed_1_5"]
PANEL_T0, PANEL_STEP, PANEL_DUR = 16.80, 0.05, 0.26
A_LIGHT = 17.16
# 5b
B_FIN, B_LIGHT = 17.95, 18.25
# 5c
C_WAVE, C_SPEED, C_TILE = 18.95, 7.5, 0.20
C_ORIGIN = np.array([-2.7, 1.6])
# 5d
D_PANEL, D_SLIDE, D_LIGHT = "glass_part_2", (20.35, 20.95), 20.98


def _tile_centres():
    """Tile centres from the model dimensions (same grid as room._finish_floor)."""
    from ..scene.dims import MEET, XP, XW, Y0
    out = []
    k = 0
    for (ra, rb, qa, qb) in [(XW, XP, Y0, 9.2), (XP, MEET[1], MEET[2], MEET[3])]:
        for x in np.arange(XW, rb - 1e-6, 1.2):
            for y in np.arange(Y0, qb - 1e-6, 0.6):
                xa, xb = max(x, ra), min(x + 1.2, rb)
                ya, yb = max(y, qa), min(y + 0.6, qb)
                if xb - xa < 0.03 or yb - ya < 0.03:
                    continue
                out.append((f"tile_{k}", (xa + xb) / 2, (ya + yb) / 2))
                k += 1
    return out


TILES = _tile_centres()


class Shot(_Shot):
    id = "s05_execution"

    def part(self, t):
        return 0 if t < B0 else 1 if t < C0 else 2 if t < D0 else 3

    def cam(self, t):
        return PATHS[self.part(t)](t)

    def stills(self):
        s = [projector("s05a_raw", CAM_A, "raw"), projector("s05a_board", CAM_A, "boarded"),
             projector("s05a_fin", CAM_A, "finished"),
             projector("s05b_raw", CAM_B, "raw"), projector("s05b_fin", CAM_B, "finished"),
             projector("s05c_raw", CAM_C, "raw"), projector("s05c_fin", CAM_C, "finished_empty"),
             projector("s05d_A", CAM_D, "finished", glass_camera=True, hide=(D_PANEL,)),
             projector("s05d_B", CAM_D, "finished", glass_camera=True)]
        return s

    # ------------------------------------------------------------------
    def plate(self, t):
        return [self._a, self._b, self._c, self._d][self.part(t)](t)

    def _a(self, t):
        if t < A_BOARD:
            return Plate("raw", [LayerSpec("s05a_raw", lights(daylight=1.0, work=1.0))], exposure=0.2)
        if t < A_FIN:
            return Plate("boarded", [LayerSpec("s05a_board", lights(daylight=1.0, work=1.0))], exposure=0.2)
        poses, fades, hide = {}, {}, set()
        for i, n in enumerate(PANELS):
            u = E.lin(PANEL_T0 + i * PANEL_STEP, PANEL_T0 + i * PANEL_STEP + PANEL_DUR, t)
            if u <= 0:
                hide.add(n)
                continue
            if u < 1:
                off = -0.16 * (1 - float(E.out_expo(u)))
                poses[n] = translate(dy=off, base=_default_pose(n))
                fades[n] = float(E.smoothstep(E.lin(0.0, 0.45, u)))
        down = float(E.smoothstep(E.lin(A_LIGHT, A_LIGHT + 0.22, t)))
        fin = LayerSpec("s05a_fin", lights(daylight=1.0, down=down, cove=1.0))
        brd = LayerSpec("s05a_board", lights(daylight=1.0))
        return Plate({"always", "shell", "finish", "furniture", "exterior", "boards"}, [fin, brd], hide=hide,
                     poses=poses, fades=fades, exposure=0.2)

    def _b(self, t):
        if t < B_FIN:
            return Plate("raw", [LayerSpec("s05b_raw", lights(daylight=1.0, work=1.0))], exposure=0.35)
        on = float(E.smoothstep(E.lin(B_LIGHT, B_LIGHT + 0.22, t)))
        return Plate("finished", [LayerSpec("s05b_fin", lights(daylight=1.0, down=on, cove=0.6 + 0.4 * on, niche=on))],
                     exposure=0.35)

    def _c(self, t):
        """Screed -> stone. Walls and ceiling are already finished (as on a
        real site, floors go down late); site boxes leave as the wave passes."""
        poses, fades, hide = {}, {}, set()
        last = C_WAVE
        for name, x, y in TILES:
            T = C_WAVE + np.hypot(x - C_ORIGIN[0], y - C_ORIGIN[1]) / C_SPEED
            last = max(last, T) if np.hypot(x - C_ORIGIN[0], y - C_ORIGIN[1]) < 9 else last
            u = E.lin(T, T + C_TILE, t)
            if u <= 0:
                hide.add(name)
            elif u < 1:
                poses[name] = translate(dz=0.035 * (1 - float(E.out_cubic(u))), base=_default_pose(name))
                fades[name] = float(E.smoothstep(E.lin(0, 0.6, u)))
        for name in _site_names():
            a = 1 - float(E.smoothstep(E.lin(19.55, 19.8, t)))
            if a <= 0:
                hide.add(name)
            elif a < 1:
                fades[name] = a
        fin = LayerSpec("s05c_fin", lights(daylight=1.0, cove=0.5), 1.0)
        raw = LayerSpec("s05c_raw", lights(daylight=1.0, cove=0.0), 1e-3)
        return Plate({"always", "shell", "finish", "exterior", "site"}, [fin, raw], hide=hide, poses=poses,
                     fades=fades, exposure=0.1)

    def _d(self, t):
        u = float(E.ARCH(E.lin(*D_SLIDE, t)))
        dy = 1.2 * (1 - u)
        cam = self.cam(t)
        c = np.array(cam.pos)

        def covered(P):
            # does the camera ray to P cross the sliding pane's current rectangle?
            x_pl = 5.405
            d = P - c
            s = (x_pl - c[0]) / np.where(np.abs(d[:, 0]) < 1e-9, 1e-9, d[:, 0])
            hit = c + d * s[:, None]
            inside = (s > 0) & (s < 1) & (hit[:, 1] > 4.815 + dy) & (hit[:, 1] < 5.985 + dy) & (hit[:, 2] > 0.025) & (hit[:, 2] < 3.74)
            return inside.astype(np.float32)

        m = float(E.smoothstep(E.lin(D_LIGHT, D_LIGHT + 0.3, t)))
        L = lights(daylight=1.0, cove=1.0, down=1.0, niche=1.0, meeting=m)
        return Plate("finished", [LayerSpec("s05d_A", L, lambda P: 1 - covered(P) + 1e-4, wildcard=True),
                                  LayerSpec("s05d_B", L, lambda P: covered(P) + 1e-4, wildcard=True)], exposure=0.1)

    def draw(self, t, g):
        titles.chapter(g, "EXECUTION", t, 16.3, 18.1)

    def post(self, t):
        return {"motion_blur": False}

    def cues(self):
        c = [Cue(A0, "cut", 0.7), Cue(A_BOARD, "cut_hit", 0.8), Cue(A_FIN, "cut_hit", 0.8), Cue(16.3, "title_in", 0.7)]
        c += [Cue(PANEL_T0 + i * PANEL_STEP + PANEL_DUR * 0.55, "lock", 0.55 + 0.1 * (i == 4)) for i in range(len(PANELS))]
        c += [Cue(A_LIGHT, "light_on", 0.5), Cue(B0, "cut", 0.6), Cue(B_FIN, "cut_hit", 0.8), Cue(B_LIGHT, "electric", 0.8),
              Cue(C0, "cut", 0.6), Cue(C_WAVE, "tile_wave", 0.8, {"dur": 0.9}), Cue(D0, "cut", 0.6),
              Cue(D_SLIDE[0], "glass_slide", 0.8, {"dur": D_SLIDE[1] - D_SLIDE[0]}), Cue(D_SLIDE[1] - 0.02, "glass_lock", 0.9),
              Cue(D_LIGHT, "light_on", 0.45)]
        return c


_POSES: dict[str, np.ndarray] = {}


def _default_pose(name: str) -> np.ndarray:
    """Default world matrix of an object (read once from the built scene)."""
    if name not in _POSES:
        import bpy
        _POSES[name] = np.array(bpy.data.objects[name].matrix_world)
    return _POSES[name]


def _site_names():
    import bpy
    return [o.name for o in bpy.data.objects if o.get("jf_group") == "site"]
