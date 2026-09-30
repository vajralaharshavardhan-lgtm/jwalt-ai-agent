"""S01 VISION (0-3.6 s): black; one precise line; the plan draws itself and
illuminates; VISION; the walls begin to rise out of the drawing."""
from __future__ import annotations

from .. import easing as E
from ..graphics import titles
from . import _opening as O
from .base import Cue, Shot as _Shot


class Shot(_Shot):
    id = "s01_vision"
    reframe = O.REFRAME

    def cam(self, t):
        return O.PATH(t)

    def draw(self, t, g):
        fade = 1 - E.smoothstep(E.lin(*O.PLAN_FADE, t))
        O.draw_plan(g, t, fade)
        O.draw_wire(g, t)
        titles.chapter(g, "VISION", t, 1.22, 2.9)

    def cues(self):
        c = [Cue(0.0, "ambience_in", 1.0), Cue(0.42, "first_line", 1.0)]
        c += [Cue(0.95 + 0.07 * i, "tick", 0.35 + 0.05 * (i % 3)) for i in range(8)]
        c += [Cue(1.22, "title_in", 0.8), Cue(1.5, "draw_texture", 0.6, {"dur": 1.2}),
              Cue(2.25, "illuminate", 0.8), Cue(2.72, "rise", 1.0, {"dur": 1.6})]
        return c
