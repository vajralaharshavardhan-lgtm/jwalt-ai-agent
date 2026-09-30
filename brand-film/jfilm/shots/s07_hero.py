"""S07 HERO (27.5-32.0 s): the finished space, slow diagonal dolly in
low western sun -- raking light through the fins across stone and oak, the
cove and niche glowing. No text; the space is the message."""
from __future__ import annotations

from .. import easing as E
from ..camera import CamPath, CamState
from ._util import lights, projector
from .base import Cue, LayerSpec, Plate, Shot as _Shot

T0, T1 = 27.5, 32.0
CAM_S = CamState.look((4.35, 0.78, 1.52), (-2.3, 7.4, 1.25), 44.0, focus=7.6, fstop=4.0)
CAM_E = CamState.look((3.40, 1.72, 1.32), (-2.3, 7.4, 1.20), 41.5, focus=6.4, fstop=4.0)
CAM_X = CamState.look((3.08, 2.02, 1.26), (-2.3, 7.4, 1.18), 40.8, focus=6.0, fstop=4.0)   # S08 drift
PATH = CamPath([(T0, CAM_S), (T1, CAM_E), (T1 + 2.0, CAM_X)], ease=None)

FULL = lights(daylight=1.0, cove=1.0, down=1.0, niche=1.0, meeting=1.0)


def hero_layers(t, daylight=1.0):
    wB = float(E.smoothstep(E.lin(T0 + 0.6, T1, t)))
    L = dict(FULL)
    L["daylight"] = daylight
    return [LayerSpec("s07_A", L, 1 - wB + 1e-4), LayerSpec("s07_B", L, wB + 1e-4)]


class Shot(_Shot):
    id = "s07_hero"

    def cam(self, t):
        return PATH(t)

    def stills(self):
        return [projector("s07_A", CAM_S, density=1.1, samples=32), projector("s07_B", CAM_E, density=1.1, samples=32)]

    def plate(self, t):
        return Plate("finished", hero_layers(t), exposure=0.05)

    def cues(self):
        return [Cue(T0, "hero_open", 1.0), Cue(T0 + 0.4, "music_peak", 1.0)]
