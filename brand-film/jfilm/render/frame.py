"""Per-frame assembly: plate (projection) -> lens (DOF, shutter) -> AgX ->
vector graphics -> film finishing. One FrameRenderer per process/format."""
from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from .. import config
from ..camera import View, view_for
from ..graphics.canvas import Graphics
from ..shots import base
from . import exr, post
from . import project as PJ


class FrameRenderer:
    def __init__(self, fmt_key: str, preview: bool = False):
        self.cfg = config.load()
        self.fmt = self.cfg.formats[fmt_key]
        self.preview = preview
        self.scale = 0.5 if preview else 1.0
        self.ss = 1 if preview else int(self.cfg.render["gbuffer_supersample"])
        self._stills: dict[str, PJ.Still] = {}
        self._env = None
        self._scene = False
        self.gb_dir = config.GBUF / f"p{os.getpid()}"
        self.gb_dir.mkdir(parents=True, exist_ok=True)

    # --- scene / assets --------------------------------------------------------------
    def _ensure_scene(self):
        if self._scene:
            return
        import bpy

        from .. import scene as S
        from . import blender as B
        S.build_scene()
        B.setup_workbench_ids()
        reg = S.registry()
        self.id_of = {r["name"]: r["id"] for r in reg}
        self.env_ids = {r["id"] for r in reg if r["group"] == "exterior"}
        self.default_mw = {ob.name: np.array(ob.matrix_world) for ob in bpy.data.objects}
        self.max_id = max(self.id_of.values()) + 2
        self._scene = True

    def still(self, name: str) -> PJ.Still:
        s = self._stills.get(name)
        if s is None:
            path = config.STILLS / f"{name}{'_preview' if self.preview else ''}.exr"
            if not path.exists():
                raise FileNotFoundError(f"still {path.name} not rendered (run: render.py stills)")
            s = PJ.Still(path)
            if len(self._stills) > 7:
                self._stills.pop(next(iter(self._stills)))
            self._stills[name] = s
        return s

    def env(self):
        if self._env is None:
            from .stills import CubeEnv
            self._env = CubeEnv(self.preview)
        return self._env

    # --- plate -------------------------------------------------------------------------
    def _gbuffer(self, view: View, tag: str):
        from . import blender as B
        path = self.gb_dir / f"{tag}.exr"
        B.render_ids(view, path)
        return PJ.read_gbuffer(path)

    def render_plate(self, plate: base.Plate, view: View):
        import bpy

        from .. import scene as S
        self._ensure_scene()
        hide = set(plate.hide)
        if plate.hide_prefix:
            hide |= {o.name for o in bpy.data.objects if o.name.startswith(plate.hide_prefix)}
        fade_names = {n for n, a in plate.fades.items()}
        S.apply_state(plate.state, hide=hide | fade_names, show=set(plate.show))
        for ob in bpy.data.objects:
            if ob.get("jf_glass"):
                ob.hide_render = True
        saved = []
        for name, M in plate.poses.items():
            ob = bpy.data.objects[name]
            saved.append((ob, ob.matrix_world.copy()))
            import mathutils
            ob.matrix_world = mathutils.Matrix(np.asarray(M).tolist())
        vss = view.scaled(self.ss) if self.ss != 1 else view
        try:
            ids, depth = self._gbuffer(vss, "base")
            layers = []
            for ls in plate.layers:
                ref = {self.id_of[n]: np.asarray(M) for n, M in ls.ref_poses.items()}
                layers.append(PJ.Layer(self.still(ls.still), ls.lights, ls.weight, ref=ref, wildcard=ls.wildcard))
            moving = {self.id_of[n]: (np.asarray(M), self.default_mw[n]) for n, M in plate.poses.items() if n in self.id_of}
            env = self.env() if plate.env > 0 else None
            rgb, cover = PJ.shade(vss, ids, depth, layers, env=env, env_lights=plate.env, moving=moving,
                                  env_ids=self.env_ids, max_id=self.max_id)
            if fade_names:
                for n in fade_names:
                    if n in bpy.data.objects:
                        bpy.data.objects[n].hide_render = False
                ids1, depth1 = self._gbuffer(vss, "fade")
                lut = np.zeros(self.max_id, np.float32)
                for n, a in plate.fades.items():
                    if n in self.id_of:
                        lut[self.id_of[n]] = float(np.clip(a, 0, 1))
                diff = (ids1 != ids) & (lut[ids1] > 0)
                if diff.any():
                    rgb1, cov1 = PJ.shade(vss, ids1, depth1, layers, env=env, env_lights=plate.env, moving=moving,
                                          env_ids=self.env_ids, max_id=self.max_id, only=diff)
                    # what lies behind a fading object may be unseen by every
                    # still: fill both passes first, or the hole blends in as black
                    rgb = PJ.fill_holes(rgb, cover)
                    rgb1 = PJ.fill_holes(rgb1, np.where(diff, cov1, 0))
                    a = (lut[ids1] * diff)[..., None]
                    rgb = rgb * (1 - a) + rgb1 * a
                    cover = np.ones_like(cover)
                    depth = np.where(diff & (lut[ids1] > 0.5), depth1, depth)
        finally:
            for ob, m in saved:
                ob.matrix_world = m
        if plate.alpha is not None:
            xs, ys = vss.pixel_grid()
            fg = depth < PJ.BG_DEPTH
            A = np.zeros(depth.shape, np.float32)
            if fg.any():
                P = vss.unproject(xs[fg], ys[fg], depth[fg].astype(np.float64))
                A[fg] = np.asarray(plate.alpha(P), np.float32)
            A[~fg] = float(plate.sky_alpha)
            rgb = rgb * A[..., None]
        rgb = PJ.fill_holes(rgb, cover)
        rgb = PJ.downsample(rgb, self.ss)
        if self.ss > 1:
            H, W = depth.shape
            depth = depth.reshape(H // self.ss, self.ss, W // self.ss, self.ss).min(axis=(1, 3))
        return rgb, depth

    # --- lens --------------------------------------------------------------------------
    def _flow(self, shot, t, view: View, depth: np.ndarray) -> np.ndarray:
        dt = 1.0 / (2 * self.cfg.fps)      # 180-degree shutter
        H, W = depth.shape
        xs, ys = view.pixel_grid()
        d = np.where(depth < PJ.BG_DEPTH, depth, 1e4).astype(np.float64)
        P = view.unproject(xs, ys, d)
        va = view_for(shot.cam(t - dt / 2), self.fmt, shot.reframe, self.scale, t - dt / 2)
        vb = view_for(shot.cam(t + dt / 2), self.fmt, shot.reframe, self.scale, t + dt / 2)
        xa, ya, _ = va.project(P)
        xb, yb, _ = vb.project(P)
        return np.stack([xb - xa, yb - ya], -1).astype(np.float32)

    # --- frame --------------------------------------------------------------------------
    def render(self, t: float, frame_index: int = 0) -> np.ndarray:
        # shots read the Blender scene (object lists, default poses) inside
        # plate(); build it first so a worker that starts mid-film sees it
        self._ensure_scene()
        shot = base.at(t)
        cam = shot.cam(t)
        view = view_for(cam, self.fmt, shot.reframe, self.scale, t)
        plate = shot.plate(t)
        pp = shot.post(t) or {}
        depth = None
        bg = np.array(self.cfg.palette["black"], np.float32)
        override = (self.cfg.raw.get("overrides") or {}).get(shot.id) or {}
        if override.get("footage"):
            from . import footage
            disp = footage.frame(override, t, shot, view.W, view.H)
            plate = None
        elif plate is not None:
            lin, depth = self.render_plate(plate, view)
            if cam.focus and pp.get("dof", True):
                coc = view.coc_px(depth) * pp.get("dof_scale", 1.0)
                lin = post.depth_of_field(lin, depth, cam.focus, coc, max_coc=28 * self.scale)
            if pp.get("motion_blur", True):
                lin = post.motion_blur(lin, self._flow(shot, t, view, depth))
            disp = exr.display(lin, look=pp.get("look", "AgX - Medium High Contrast"),
                               exposure=plate.exposure + pp.get("exposure", 0.0))
            fade = pp.get("plate_opacity", 1.0)
            if fade < 1:
                disp = disp * fade + bg * (1 - fade)
        if plate is None and not override.get("footage"):
            disp = np.empty((view.H, view.W, 3), np.float32)
            disp[:] = bg
        g = Graphics(view, self.fmt, t, depth=depth)
        shot.draw(t, g)
        if g.dirty:
            rgba = g.rgba()
            disp = disp * (1 - rgba[..., 3:4]) + rgba[..., :3]
        r = self.cfg.render
        disp = post.grade(disp, **pp.get("grade", {}))
        disp = post.halation(disp, pp.get("halation", r["halation"]))
        disp = post.chromatic(disp, pp.get("ca", 0.55) * self.scale)
        disp = post.vignette(disp, pp.get("vignette", r["vignette"]))
        disp = post.grain(disp, pp.get("grain", r["grain"]), frame_index)
        if "overlay" in pp:
            disp = pp["overlay"](disp)
        return disp


def write_png(path: Path, img: np.ndarray):
    a = np.clip(img, 0, 1)
    cv2.imwrite(str(path), (a[..., ::-1] * 255 + 0.5).astype(np.uint8), [cv2.IMWRITE_PNG_COMPRESSION, 1])
