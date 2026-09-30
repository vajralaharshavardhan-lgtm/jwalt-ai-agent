"""S02 DESIGN (3.6-8.0 s): the walls finish rising around the descending
camera, the interior draws itself, surfaces fill in from the floor up
(structural 'clay'), then materials sweep from the back wall toward us and
the lighting comes up: cove in sequence, wall-washers, niche."""
from __future__ import annotations

import numpy as np

from .. import easing as E
from ..graphics import titles
from ..scene.dims import Z_COFFER
from . import _opening as O
from ._util import lights, projector, smooth_front
from .base import Cue, LayerSpec, Plate, Shot as _Shot

T_A, T_B = 5.45, 8.0
COVE_T = (6.95, 7.08, 7.21, 7.34)


class Shot(_Shot):
    id = "s02_design"
    reframe = O.REFRAME

    def cam(self, t):
        return O.PATH(t)

    def stills(self):
        A, B = O.PATH(T_A), O.PATH(T_B)
        clay = dict(clay=True, hide_prefix=("glass_",))
        return [projector("s02_clay_A", A, **clay), projector("s02_clay_B", B, **clay),
                projector("s02_fin_A", A), projector("s02_fin_B", B)]

    # --- timing helpers ---
    def clay_height(self, t):
        return -0.25 + (Z_COFFER + 0.7) * float(E.ARCH(E.lin(*O.CLAY, t)))

    def mat_front(self, t):
        return 9.9 - 11.2 * float(E.ARCH(E.lin(*O.MAT, t)))

    def plate(self, t):
        if t < O.CLAY[0]:
            return None
        wB = float(E.smoothstep(E.lin(5.7, 7.7, t)))
        wA = 1 - wB
        yf = self.mat_front(t)

        def m(P):
            return smooth_front(-P[:, 1], -yf, 1.4)

        seq = [float(E.smoothstep(E.lin(c, c + 0.5, t))) for c in COVE_T]
        fin_l = lights(daylight=0.55 + 0.45 * float(E.smoothstep(E.lin(6.5, 7.7, t))), cove_seq=seq,
                       down=float(E.smoothstep(E.lin(7.3, 7.85, t))), niche=float(E.smoothstep(E.lin(7.45, 8.0, t))),
                       meeting=float(E.smoothstep(E.lin(7.5, 8.0, t))))
        clay_l = lights(daylight=0.9)
        layers = [
            LayerSpec("s02_clay_A", clay_l, lambda P, w=wA: w * (1 - m(P))),
            LayerSpec("s02_clay_B", clay_l, lambda P, w=wB: w * (1 - m(P))),
            LayerSpec("s02_fin_A", fin_l, lambda P, w=wA: w * m(P)),
            LayerSpec("s02_fin_B", fin_l, lambda P, w=wB: w * m(P)),
        ]
        h = self.clay_height(t)
        mat_on = float(E.smoothstep(E.lin(*O.MAT, t)))
        return Plate(state="finished", layers=layers, env=0.35 + 0.65 * mat_on,
                     alpha=lambda P: smooth_front(P[:, 2], h, 0.45),
                     sky_alpha=float(np.clip((h - 0.4) / 2.0, 0, 1)))

    def draw(self, t, g):
        fade = 1 - E.smoothstep(E.lin(*O.PLAN_FADE, t))
        O.draw_plan(g, t, fade)
        out = 1 - float(E.smoothstep(E.lin(*O.LINES_OUT, t)))
        clay_on = float(E.smoothstep(E.lin(O.CLAY[0], O.CLAY[0] + 0.8, t)))
        O.draw_wire(g, t, occlude=t > O.CLAY[0], alpha=out * (1 - 0.45 * clay_on))
        # a restrained scan line on the floor marks where material is being applied
        yf = self.mat_front(t)
        env = float(E.fade_window(t, O.MAT[0], O.MAT[1], 0.25, 0.35))
        if env > 0.01:
            seg = np.array([[[-6.0, yf, 0.004], [5.4, yf, 0.004]]])
            g.lines3d(seg, g.pal["accent"], width=1.0, alpha=0.75 * env, glow=3.0, glow_alpha=0.5, occlude=True)
        titles.chapter(g, "DESIGN", t, 4.35, 6.35)

    def cues(self):
        c = [Cue(4.35, "title_in", 0.8), Cue(3.6, "draw_texture", 0.5, {"dur": 1.6}),
             Cue(5.0, "swell", 0.7, {"dur": 1.4}), Cue(6.25, "sweep", 0.8, {"dur": 1.0})]
        c += [Cue(x, "light_on", 0.45) for x in COVE_T] + [Cue(7.3, "light_on", 0.55), Cue(7.45, "light_on", 0.5)]
        return c
