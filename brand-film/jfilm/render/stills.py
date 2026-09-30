"""Projector stills: spec, cache, render.

A StillSpec fully describes one converged Cycles render (camera, state,
resolution, samples). Renders are cached by a content hash, so changing a
shot only re-renders the stills that actually changed."""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .. import config
from ..camera import CamState, View

SCENE_VERSION = "2026-09-30.8"   # bump when geometry/materials/lights change


@dataclass(frozen=True)
class StillSpec:
    name: str
    cam: CamState
    width: int
    height: int
    state: str = "finished"
    hide: tuple[str, ...] = ()
    hide_prefix: tuple[str, ...] = ()
    show: tuple[str, ...] = ()
    clay: bool = False
    glass_camera: bool = False
    samples: int = 24
    xforms: tuple = ()        # ((object name, 4x4 as tuple), ...) pose used for this still
    note: str = ""

    def view(self, scale: float = 1.0) -> View:
        return View(self.cam, round(self.width * scale), round(self.height * scale))

    def key(self, preview: bool) -> str:
        d = asdict(self)
        d["cam"] = asdict(self.cam)
        d["_v"] = SCENE_VERSION
        d["_p"] = preview
        return hashlib.sha1(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:16]


def still_path(spec: StillSpec, preview: bool) -> Path:
    return config.STILLS / f"{spec.name}{'_preview' if preview else ''}.exr"


def is_current(spec: StillSpec, preview: bool) -> bool:
    p = still_path(spec, preview)
    meta = p.with_suffix(".json")
    if not (p.exists() and meta.exists()):
        return False
    return json.loads(meta.read_text()).get("key") == spec.key(preview)


def render(spec: StillSpec, preview: bool = False, force: bool = False) -> Path:
    """Render (or reuse) a still. Must run inside a process with the scene built."""
    import bpy

    from .. import scene as S
    from . import blender as B
    from .project import view_to_json

    cfg = config.load()
    out = still_path(spec, preview)
    if not force and is_current(spec, preview):
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    scale = cfg.render["still_scale_preview"] if preview else 1.0
    samples = cfg.render["still_samples_preview"] if preview else spec.samples
    view = spec.view(scale)
    hide = set(spec.hide) | {o.name for o in bpy.data.objects if spec.hide_prefix and o.name.startswith(spec.hide_prefix)}
    S.apply_state(spec.state, hide=hide, show=set(spec.show), glass_camera=spec.glass_camera)
    restore = _apply_xforms(spec.xforms)
    vl = bpy.context.scene.view_layers[0]
    vl.material_override = _clay_material() if spec.clay else None
    t0 = time.time()
    try:
        B.render_still(view, out, samples=samples)
    finally:
        vl.material_override = None
        _restore_xforms(restore)
    meta = view_to_json(view)
    meta.update({"key": spec.key(preview), "name": spec.name, "state": spec.state, "seconds": round(time.time() - t0, 1),
                 "samples": samples, "preview": preview})
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    return out


def _clay_material():
    import bpy

    from ..scene import materials as M
    return M.get("clay")


def _apply_xforms(xforms):
    import bpy
    import mathutils
    saved = []
    for name, mat in xforms:
        ob = bpy.data.objects[name]
        saved.append((ob, ob.matrix_world.copy()))
        ob.matrix_world = mathutils.Matrix([list(mat[i * 4:(i + 1) * 4]) for i in range(4)])
    return saved


def _restore_xforms(saved):
    for ob, m in saved:
        ob.matrix_world = m


# --- environment cube (sky + distant city) --------------------------------------

ENV_CENTER = (-6.4, 4.5, 1.5)
_FACES = {"px": (-90.0, 0.0), "nx": (90.0, 0.0), "py": (0.0, 0.0), "ny": (180.0, 0.0), "pz": (0.0, 90.0), "nz": (0.0, -90.0)}


def env_specs(size: int = 1024, samples: int = 16) -> list[StillSpec]:
    return [StillSpec(name=f"env_{k}", cam=CamState(ENV_CENTER, yaw, pitch, 90.0), width=size, height=size,
                      state="env", samples=samples) for k, (yaw, pitch) in _FACES.items()]


class CubeEnv:
    """Direction lookup into six 90-degree faces rendered with our own View
    maths (so no panorama-convention guesswork)."""

    def __init__(self, preview: bool = False):
        from . import exr
        self.faces = []
        for spec in env_specs():
            p = still_path(spec, preview)
            L = exr.read(p)
            v = View(spec.cam, *L["lg_daylight"].shape[1::-1])
            self.faces.append((v, np.ascontiguousarray(L["lg_daylight"][..., :3])))

    def lookup(self, dirs: np.ndarray) -> np.ndarray:
        from .project import remap_points
        d = dirs / np.linalg.norm(dirs, axis=-1, keepdims=True)
        out = np.zeros(d.shape, np.float32)
        best = np.full(len(d), -1.0)
        choice = np.full(len(d), -1)
        for i, (v, _) in enumerate(self.faces):
            s = d @ v.forward
            upd = s > best
            best[upd] = s[upd]
            choice[upd] = i
        for i, (v, img) in enumerate(self.faces):
            sel = choice == i
            if not sel.any():
                continue
            x, y, _ = v.project(v.t + d[sel])
            out[sel] = remap_points(img, x - 0.5, y - 0.5)
        return out
