"""Shot interface. Each shot module defines one `Shot` subclass describing:

  cam(t)        -> CamState (the camera, in 16:9 master terms)
  reframe       -> per-format yaw/pitch/fov overrides for 9:16 and 1:1
  stills()      -> projector stills it needs (jfilm.render.stills.StillSpec)
  plate(t)      -> Plate recipe for the photoreal layer (or None = black)
  draw(t, g)    -> vector graphics / typography on top (jfilm.graphics)
  post(t)       -> lens + grade tweaks
  cues()        -> sound cues (absolute seconds) the audio mix syncs to

Times passed to these methods are ABSOLUTE film seconds.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .. import config
from ..camera import CamState


@dataclass
class LayerSpec:
    still: str                                   # StillSpec.name
    lights: dict[str, float]                     # light-group mix
    weight: float | Callable = 1.0               # scalar, or f(P world (N,3)) -> (N,) weights
    ref_poses: dict[str, np.ndarray] = field(default_factory=dict)  # object -> 4x4 pose in that still
    wildcard: bool = False    # still rendered with camera-visible glass: accept see-through (id 0) pixels


@dataclass
class Plate:
    state: str | set
    layers: list[LayerSpec]
    hide: set = field(default_factory=set)
    hide_prefix: tuple = ()
    show: set = field(default_factory=set)
    poses: dict[str, np.ndarray] = field(default_factory=dict)   # object -> CURRENT 4x4 world matrix
    fades: dict[str, float] = field(default_factory=dict)        # object -> alpha (objects fading in/out)
    env: float = 1.0                                            # daylight weight of sky/city lookup
    exposure: float = 0.0                                       # EV applied before the display transform
    alpha: Callable | None = None                               # f(P world (N,3)) -> reveal alpha (over black)
    sky_alpha: float = 1.0                                      # reveal alpha for sky pixels


@dataclass
class Cue:
    t: float
    kind: str
    gain: float = 1.0
    params: dict = field(default_factory=dict)


class Shot:
    id = ""
    reframe: dict = {}

    def __init__(self):
        cfg = config.load()
        e = cfg.shot(self.id)
        self.start, self.end, self.title = e.start, e.end, e.title
        self.cfg = cfg

    # helpers
    def u(self, t: float) -> float:
        """Normalised shot time 0..1."""
        return float(np.clip((t - self.start) / (self.end - self.start), 0.0, 1.0))

    def local(self, t: float) -> float:
        return t - self.start

    # interface
    def cam(self, t: float) -> CamState:
        raise NotImplementedError

    def stills(self) -> list:
        return []

    def plate(self, t: float):
        return None

    def draw(self, t: float, g) -> None:
        pass

    def post(self, t: float) -> dict:
        return {}

    def cues(self) -> list[Cue]:
        return []


_cache: dict[str, Shot] = {}


def get(shot_id: str) -> Shot:
    if shot_id not in _cache:
        mod = importlib.import_module(f"jfilm.shots.{shot_id}")
        _cache[shot_id] = mod.Shot()
    return _cache[shot_id]


def all_shots() -> list[Shot]:
    return [get(s.id) for s in config.load().shots]


def at(t: float) -> Shot:
    return get(config.load().shot_at(t).id)
