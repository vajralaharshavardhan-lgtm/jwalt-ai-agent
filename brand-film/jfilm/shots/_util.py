"""Helpers shared by shot modules."""
from __future__ import annotations

import math

import numpy as np

from ..camera import CamState
from ..render.stills import StillSpec
from ..scene.lights import COVE


def projector(name: str, cam: CamState, state: str = "finished", cover_v: float = 1.5, cover_h: float = 1.08,
              density: float = 1.0, samples: int = 24, **kw) -> StillSpec:
    """A projector still around `cam` that covers the 16:9 master (with
    `cover_h` margin) and the taller 9:16 / 1:1 reframes (`cover_v`)."""
    tv = math.tan(math.radians(cam.vfov) / 2)
    vfov_p = 2 * math.degrees(math.atan(tv * cover_v))
    H = int(round(1080 * density * cover_v / 2) * 2)
    W = int(round(H * (16 / 9 * cover_h) / cover_v / 2) * 2)
    return StillSpec(name=name, cam=cam.with_(vfov=vfov_p, focus=None), width=W, height=H, state=state,
                     samples=samples, **kw)


def lights(daylight=1.0, cove=0.0, down=0.0, niche=0.0, meeting=0.0, work=0.0, cove_seq=None) -> dict:
    d = {"daylight": daylight, "down": down, "niche": niche, "meeting": meeting, "work": work}
    for i, g in enumerate(COVE):
        d[g] = cove_seq[i] if cove_seq is not None else cove
    return d


def translate(dx=0.0, dy=0.0, dz=0.0, base: np.ndarray | None = None) -> np.ndarray:
    M = np.eye(4) if base is None else np.array(base, dtype=np.float64)
    M = M.copy()
    M[:3, 3] += (dx, dy, dz)
    return M


def smooth_front(coord, pos: float, width: float):
    """1 where coord < pos (already passed), 0 ahead, soft over `width`."""
    x = np.clip((pos - coord) / max(width, 1e-6) + 0.5, 0, 1)
    return x * x * (3 - 2 * x)
