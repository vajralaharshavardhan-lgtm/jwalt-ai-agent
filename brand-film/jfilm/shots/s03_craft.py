"""S03 CRAFT (8.0-12.0 s): three macro studies of the finished space, each a
locked-off camera with a slow push and a single lighting event:
  a) raking light across the reeded oak as the wall-washers come up
  b) the travertine niche, bronze reveal and oak console as the niche glows
  c) the coffer: the cove comes on circuit by circuit along the oak slats"""
from __future__ import annotations

from .. import easing as E
from ..camera import CamPath, CamState
from ..graphics import titles
from ._util import lights, projector
from .base import Cue, LayerSpec, Plate, Shot as _Shot

A0, B0, C0, END = 8.0, 9.35, 10.7, 12.0

CAM_A = CamState.look((-3.95, 8.40, 1.50), (-2.35, 8.87, 1.70), 21.0, focus=1.05, fstop=2.0)
CAM_B = CamState.look((1.22, 8.14, 1.04), (0.22, 9.02, 0.88), 24.0, focus=1.28, fstop=2.2)
CAM_C = CamState.look((2.55, 1.85, 1.62), (1.55, 3.02, 4.28), 30.0, focus=2.9, fstop=3.2)

PATHS = [
    CamPath([(A0, CAM_A), (B0, CAM_A.with_(vfov=19.2, focus=1.15))]),
    CamPath([(B0, CAM_B), (C0, CAM_B.with_(vfov=22.4))]),
    CamPath([(C0, CAM_C), (END, CAM_C.with_(vfov=28.0))]),
]


class Shot(_Shot):
    id = "s03_craft"

    def part(self, t):
        return 0 if t < B0 else (1 if t < C0 else 2)

    def cam(self, t):
        return PATHS[self.part(t)](t)

    def stills(self):
        return [projector("s03a", CAM_A, cover_v=1.5, density=1.1, samples=32),
                projector("s03b", CAM_B, cover_v=1.5, density=1.1, samples=32),
                projector("s03c", CAM_C, cover_v=1.5, density=1.1, samples=32)]

    def plate(self, t):
        k = self.part(t)
        if k == 0:
            L = lights(daylight=1.0, down=float(E.smoothstep(E.lin(8.35, 8.95, t))), niche=1.0, cove=1.0)
            return Plate("finished", [LayerSpec("s03a", L)], exposure=0.15)
        if k == 1:
            L = lights(daylight=1.0, down=1.0, cove=1.0, niche=float(E.smoothstep(E.lin(9.62, 10.2, t))))
            return Plate("finished", [LayerSpec("s03b", L)], exposure=0.0)
        seq = [float(E.smoothstep(E.lin(c, c + 0.45, t))) for c in (10.95, 11.12, 11.29, 11.46)]
        L = lights(daylight=0.8, down=1.0, niche=1.0, cove_seq=[seq[0], seq[2], seq[3], seq[1]])
        return Plate("finished", [LayerSpec("s03c", L)], exposure=0.1)

    def post(self, t):
        return {"dof": True, "motion_blur": False}

    def draw(self, t, g):
        titles.chapter(g, "CRAFT", t, 8.35, 10.25)

    def cues(self):
        return [Cue(A0, "cut", 0.6), Cue(8.35, "light_on", 0.55), Cue(8.35, "title_in", 0.7),
                Cue(B0, "cut", 0.6), Cue(9.62, "light_on", 0.55), Cue(C0, "cut", 0.6)] + \
               [Cue(c, "light_on", 0.4) for c in (10.95, 11.12, 11.29, 11.46)]
