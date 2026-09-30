"""Projection compositor ("render once, project many").

A shot's photoreal frames are built from a few converged Cycles stills
("projector stills"). For every output frame we render only a cheap
visibility buffer (object id + depth) from the moving camera, rebuild each
pixel's world position, and look that point up in the stills that saw it.
Diffuse light is view-independent, so a slow camera move, lighting changes
(light-group mixing) and objects sliding into place all stay physically
consistent -- with zero per-frame noise or flicker.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from numba import njit, prange

from ..camera import CamState, View
from . import exr

BG_DEPTH = 1e5


# --- visibility buffer --------------------------------------------------------

def read_gbuffer(path) -> tuple[np.ndarray, np.ndarray]:
    L = exr.read(path)
    comb = next(v for k, v in L.items() if k.endswith("Combined"))
    depth = next(v for k, v in L.items() if k.endswith("Depth"))
    ids = (np.rint(comb[..., 0] * 255).astype(np.int32) + 256 * np.rint(comb[..., 1] * 255).astype(np.int32))
    ids[comb[..., 3] < 0.5] = 0
    depth = depth.astype(np.float32)
    depth[ids == 0] = np.float32(1e10)
    return ids, depth


# --- projector stills ---------------------------------------------------------

def view_to_json(v: View) -> dict:
    c = v.cam
    return {"pos": list(c.pos), "yaw": c.yaw, "pitch": c.pitch, "vfov_master": c.vfov, "roll": c.roll,
            "W": v.W, "H": v.H, "vfov": float(np.degrees(v.vfov))}


def view_from_json(d: dict) -> View:
    cam = CamState(tuple(d["pos"]), d["yaw"], d["pitch"], d["vfov"], d.get("roll", 0.0))
    return View(cam, d["W"], d["H"], fov_scale=1.0)


class Still:
    def __init__(self, path: str | Path, view: View | None = None):
        path = Path(path)
        L = exr.read(path)
        if view is None:
            view = view_from_json(json.loads(path.with_suffix(".json").read_text()))
        self.path = path
        self.view = view
        # light groups kept at half precision; groups that contribute nothing
        # to this view (e.g. meeting-room light from a macro angle) are dropped
        self.groups = {}
        for k, v in L.items():
            if k.startswith("lg_") and float(v[..., :3].max()) > 1e-6:
                self.groups[k[3:]] = np.ascontiguousarray(v[..., :3], dtype=np.float16)
        self.combined = None
        self.depth = np.ascontiguousarray(L["depth"].astype(np.float32))
        nrm = L.get("normal")
        self.normal = None if nrm is None else np.ascontiguousarray(nrm[..., :3].astype(np.float32))
        self.ids = np.rint(L["index"]).astype(np.int32)
        self.H, self.W = self.depth.shape
        if (self.W, self.H) != (view.W, view.H):
            raise ValueError(f"{path.name}: still {self.W}x{self.H} != view {view.W}x{view.H}")
        self._mix_cache: tuple | None = None

    def mix(self, weights: dict[str, float]) -> np.ndarray:
        key = tuple(sorted((k, round(float(v), 5)) for k, v in weights.items()))
        if self._mix_cache and self._mix_cache[0] == key:
            return self._mix_cache[1]
        out = np.zeros((self.H, self.W, 3), np.float32)
        for g, w in weights.items():
            if w and g in self.groups:
                out += self.groups[g].astype(np.float32) * np.float32(w)
        self._mix_cache = (key, out)
        return out


@dataclass
class Layer:
    """One projector still contributing to a frame."""
    still: Still
    lights: dict[str, float]
    weight: float | np.ndarray | object = 1.0   # scalar, per-pixel array, or f(P (N,3)) -> (N,)
    ref: dict[int, np.ndarray] = field(default_factory=dict)  # object id -> 4x4 pose the still was rendered at
    image: np.ndarray | None = None             # override pre-mixed radiance (H,W,3)
    wildcard: bool = False                      # accept id-0 (glass / see-through) still pixels


@dataclass
class Env:
    """Equirectangular environment (sky + distant city) looked up by direction."""
    image: np.ndarray                      # (H, W, 3) linear
    ids: set = field(default_factory=set)  # object ids treated as 'at infinity'

    def lookup(self, dirs: np.ndarray) -> np.ndarray:
        d = dirs / np.linalg.norm(dirs, axis=-1, keepdims=True)
        lon = np.arctan2(d[..., 1], d[..., 0])            # Blender equirect: -X at centre? see make_env()
        lat = np.arcsin(np.clip(d[..., 2], -1, 1))
        H, W = self.image.shape[:2]
        u = ((-lon / (2 * np.pi)) + 0.5) * W - 0.5
        v = (0.5 - lat / np.pi) * H - 0.5
        return remap_points(self.image, u, v, border=cv2.BORDER_WRAP)


def remap_points(img: np.ndarray, mx: np.ndarray, my: np.ndarray, interp=cv2.INTER_LINEAR,
                 border=cv2.BORDER_REPLICATE) -> np.ndarray:
    """cv2.remap for an arbitrary-length list of sample points (cv2 limits
    map dimensions to < 32767, so points are laid out in 4096-wide rows)."""
    n = mx.size
    cols = 4096
    rows = (n + cols - 1) // cols
    pad = rows * cols - n
    fx = np.concatenate([mx.ravel().astype(np.float32), np.zeros(pad, np.float32)]).reshape(rows, cols)
    fy = np.concatenate([my.ravel().astype(np.float32), np.zeros(pad, np.float32)]).reshape(rows, cols)
    out = cv2.remap(img, fx, fy, interp, borderMode=border)
    ch = 1 if out.ndim == 2 else out.shape[2]
    return out.reshape(rows * cols, ch)[:n] if ch > 1 else out.reshape(-1)[:n]


@njit(parallel=True, fastmath=True, cache=True)
def _sample_kernel(P, N, tid, R, t, fx, fy, cx, cy, ids, depth, nrm, img, tol_abs, tol_rel, wildcard, use_n,
                   out_c, out_w):
    H, W = ids.shape
    for i in prange(P.shape[0]):
        d0 = P[i, 0] - t[0]
        d1 = P[i, 1] - t[1]
        d2 = P[i, 2] - t[2]
        xc = d0 * R[0, 0] + d1 * R[1, 0] + d2 * R[2, 0]
        yc = d0 * R[0, 1] + d1 * R[1, 1] + d2 * R[2, 1]
        z = -(d0 * R[0, 2] + d1 * R[1, 2] + d2 * R[2, 2])
        out_w[i] = 0.0
        if z <= 0.02:
            continue
        mx = cx + fx * xc / z - 0.5
        my = cy - fy * yc / z - 0.5
        if mx <= -0.5 or mx >= W - 0.5 or my <= -0.5 or my >= H - 0.5:
            continue
        x0 = int(np.floor(mx))
        y0 = int(np.floor(my))
        ax = mx - x0
        ay = my - y0
        tol = tol_abs + tol_rel * z
        c0 = 0.0
        c1 = 0.0
        c2 = 0.0
        ws = 0.0
        for k in range(4):
            dx = k & 1
            dy = k >> 1
            xi = min(max(x0 + dx, 0), W - 1)
            yi = min(max(y0 + dy, 0), H - 1)
            wb = (ax if dx else 1.0 - ax) * (ay if dy else 1.0 - ay)
            sid = ids[yi, xi]
            dd = depth[yi, xi]
            ok = sid == tid[i] and abs(dd - z) < tol
            if ok and use_n:
                ok = nrm[yi, xi, 0] * N[i, 0] + nrm[yi, xi, 1] * N[i, 1] + nrm[yi, xi, 2] * N[i, 2] > 0.55
            if not ok and wildcard and sid == 0 and dd < z + tol:
                ok = True
            if ok:
                c0 += wb * img[yi, xi, 0]
                c1 += wb * img[yi, xi, 1]
                c2 += wb * img[yi, xi, 2]
                ws += wb
        if ws > 1e-4:
            out_c[i, 0] = c0 / ws
            out_c[i, 1] = c1 / ws
            out_c[i, 2] = c2 / ws
            out_w[i] = min(ws * 4.0, 1.0)


def sample_still(still: Still, img: np.ndarray, P: np.ndarray, target_ids: np.ndarray,
                 N: np.ndarray | None = None, tol_abs: float = 0.015, tol_rel: float = 0.006,
                 wildcard: bool = False):
    """Look up world points P (N,3) whose visible object id is target_ids (N,)
    in `still` (id + depth + normal agreement, bilinear over agreeing texels).
    Returns colour (N,3) and weight (N,) in [0,1] (0 = unseen)."""
    v = still.view
    n = len(P)
    out_c = np.zeros((n, 3), np.float32)
    out_w = np.zeros(n, np.float32)
    use_n = N is not None and still.normal is not None
    Nn = np.ascontiguousarray(N, np.float32) if use_n else np.zeros((1, 3), np.float32)
    nrm = still.normal if use_n else np.zeros((1, 1, 3), np.float32)
    _sample_kernel(np.ascontiguousarray(P, np.float32), Nn, np.ascontiguousarray(target_ids, np.int32),
                   v.R.astype(np.float64), v.t.astype(np.float64), float(v.fx), float(v.fy), float(v.cx), float(v.cy),
                   still.ids, still.depth, nrm, np.ascontiguousarray(img, np.float32), float(tol_abs), float(tol_rel),
                   bool(wildcard), bool(use_n), out_c, out_w)
    return out_c, out_w


@njit(parallel=True, fastmath=True, cache=True)
def _positions_normals(depth, ids, R, t, fx, fy, cx, cy, P, N):
    """World positions and same-object finite-difference normals (toward camera)."""
    H, W = depth.shape
    for y in prange(H):
        for x in range(W):
            d = depth[y, x]
            if d > 1e5:
                d = 0.0
            xc = (x + 0.5 - cx) / fx * d
            yc = -(y + 0.5 - cy) / fy * d
            zc = -d
            for k in range(3):
                P[y, x, k] = R[k, 0] * xc + R[k, 1] * yc + R[k, 2] * zc + t[k]
    for y in prange(H):
        for x in range(W):
            me = ids[y, x]
            # horizontal tangent
            hx = 0.0
            hy = 0.0
            hz = 0.0
            if x + 1 < W and ids[y, x + 1] == me:
                hx = P[y, x + 1, 0] - P[y, x, 0]
                hy = P[y, x + 1, 1] - P[y, x, 1]
                hz = P[y, x + 1, 2] - P[y, x, 2]
            elif x > 0 and ids[y, x - 1] == me:
                hx = P[y, x, 0] - P[y, x - 1, 0]
                hy = P[y, x, 1] - P[y, x - 1, 1]
                hz = P[y, x, 2] - P[y, x - 1, 2]
            vx = 0.0
            vy = 0.0
            vz = 0.0
            if y + 1 < H and ids[y + 1, x] == me:
                vx = P[y + 1, x, 0] - P[y, x, 0]
                vy = P[y + 1, x, 1] - P[y, x, 1]
                vz = P[y + 1, x, 2] - P[y, x, 2]
            elif y > 0 and ids[y - 1, x] == me:
                vx = P[y, x, 0] - P[y - 1, x, 0]
                vy = P[y, x, 1] - P[y - 1, x, 1]
                vz = P[y, x, 2] - P[y - 1, x, 2]
            nx = vy * hz - vz * hy
            ny = vz * hx - vx * hz
            nz = vx * hy - vy * hx
            ln = (nx * nx + ny * ny + nz * nz) ** 0.5
            if ln < 1e-12:
                N[y, x, 0] = 0.0
                N[y, x, 1] = 0.0
                N[y, x, 2] = 0.0
                continue
            nx /= ln
            ny /= ln
            nz /= ln
            if nx * (t[0] - P[y, x, 0]) + ny * (t[1] - P[y, x, 1]) + nz * (t[2] - P[y, x, 2]) < 0:
                nx = -nx
                ny = -ny
                nz = -nz
            N[y, x, 0] = nx
            N[y, x, 1] = ny
            N[y, x, 2] = nz


def normals_from_positions(P: np.ndarray, ids: np.ndarray, view: View) -> np.ndarray:
    """World normals of a (H,W,3) position buffer using same-object neighbours,
    oriented toward the camera."""
    def diff(axis):
        fwd = np.roll(P, -1, axis) - P
        bwd = P - np.roll(P, 1, axis)
        same_f = np.roll(ids, -1, axis) == ids
        same_b = np.roll(ids, 1, axis) == ids
        nf = np.linalg.norm(fwd, axis=-1)
        nb = np.linalg.norm(bwd, axis=-1)
        use_f = same_f & (~same_b | (nf <= nb))
        return np.where(use_f[..., None], fwd, bwd)
    n = np.cross(diff(1), diff(0)).astype(np.float32)
    ln = np.linalg.norm(n, axis=-1, keepdims=True)
    n = n / np.maximum(ln, 1e-12)
    to_cam = view.t - P
    flip = np.einsum("hwc,hwc->hw", n, to_cam) < 0
    n[flip] *= -1
    return n.astype(np.float32)


def shade(view: View, ids: np.ndarray, depth: np.ndarray, layers: list[Layer], env=None,
          env_lights: float = 1.0, moving: dict[int, tuple[np.ndarray, np.ndarray]] | None = None,
          max_id: int = 70000, env_ids: set | None = None, only: np.ndarray | None = None):
    """Build linear radiance for a (supersampled) visibility buffer.

    moving: object id -> (CURRENT 4x4 world matrix, DEFAULT/build 4x4 matrix).
            A point on a moving object is carried back to the pose it had in
            each still (layer.ref[id] if given, else the default pose).
    only:   optional boolean mask restricting which pixels are shaded.
    Returns (rgb (H,W,3), coverage (H,W)).
    """
    H, W = ids.shape
    xs, ys = view.pixel_grid()
    if (xs.shape[0], xs.shape[1]) != (H, W):
        raise ValueError("visibility buffer size does not match view")
    fg = depth < BG_DEPTH
    env_mask = np.zeros_like(fg)
    env_ids = env_ids if env_ids is not None else getattr(env, "ids", set())
    if env is not None and env_ids:
        lut = np.zeros(max_id, bool)
        lut[list(env_ids)] = True
        env_mask = lut[ids] & fg
    geo_mask = fg & ~env_mask
    if only is not None:
        geo_mask &= only
    rgb = np.zeros((H, W, 3), np.float32)
    cover = np.zeros((H, W), np.float32)

    idx = np.nonzero(geo_mask.ravel())[0]
    if len(idx):
        Pfull = np.empty((H, W, 3), np.float32)
        Nfull = np.empty((H, W, 3), np.float32)
        _positions_normals(np.ascontiguousarray(depth, np.float32), np.ascontiguousarray(ids, np.int32),
                           view.R.astype(np.float64), view.t.astype(np.float64), float(view.fx), float(view.fy),
                           float(view.cx), float(view.cy), Pfull, Nfull)
        P = Pfull.reshape(-1, 3)[idx]
        N = Nfull.reshape(-1, 3)[idx]
        del Pfull, Nfull
        tid = ids.ravel()[idx]
        mv = None
        if moving:
            lut = np.zeros(max_id, bool)
            lut[list(moving.keys())] = True
            mv = lut[tid]
            if not mv.any():
                mv = None
        acc = np.zeros((len(idx), 3), np.float32)
        wacc = np.zeros(len(idx), np.float32)
        cacc = np.zeros(len(idx), np.float32)
        for L in layers:
            Pl, Nl = P, N
            if mv is not None:
                Pl, Nl = P.copy(), N.copy()
                mids = tid[mv]
                Pm, Nm = P[mv], N[mv]
                po, no = np.empty_like(Pm), np.empty_like(Nm)
                for oid in np.unique(mids):
                    sel = mids == oid
                    cur, dflt = moving[int(oid)]
                    ref = L.ref.get(int(oid), dflt)
                    T = ref @ np.linalg.inv(cur)
                    po[sel] = Pm[sel] @ T[:3, :3].T + T[:3, 3]
                    no[sel] = Nm[sel] @ T[:3, :3].T
                Pl[mv], Nl[mv] = po, no
            img = L.image if L.image is not None else L.still.mix(L.lights)
            c, w = sample_still(L.still, img, Pl, tid, Nl, wildcard=L.wildcard)
            if callable(L.weight):
                lw = np.asarray(L.weight(P), np.float32)
            elif isinstance(L.weight, np.ndarray):
                lw = L.weight.ravel()[idx].astype(np.float32)
            else:
                lw = np.float32(L.weight)
            # coverage = did any contributing still actually see this point;
            # the blend weight only decides the mix (a 1e-4 fallback layer is
            # still a real observation, not a hole)
            cacc = np.maximum(cacc, w * (lw > 0))
            w = w * lw
            acc += c * w[:, None]
            wacc += w
        good = wacc > 1e-12
        acc[good] /= wacc[good, None]
        rgb.reshape(-1, 3)[idx] = acc
        cover.ravel()[idx] = cacc

    if env is not None:
        sky = ~fg | env_mask
        if only is not None:
            sky &= only
        sidx = np.nonzero(sky.ravel())[0]
        if len(sidx):
            dirs = view.unproject(xs.ravel()[sidx], ys.ravel()[sidx], np.ones(len(sidx))) - view.t
            rgb.reshape(-1, 3)[sidx] = env.lookup(dirs) * np.float32(env_lights)
            cover.ravel()[sidx] = 1.0
    return rgb, cover


def fill_holes(rgb: np.ndarray, cover: np.ndarray, thresh: float = 0.5, iters: int = 6) -> np.ndarray:
    """Pull colour into uncovered pixels from covered neighbours (normalised
    convolution, a few widening passes). Holes are tiny with good projector
    placement; this just keeps them from reading as black specks."""
    w = (cover >= thresh).astype(np.float32)
    if w.min() >= 1:
        return rgb
    out = rgb * w[..., None]
    acc_w = w.copy()
    k = 3
    num = out.copy()
    den = acc_w.copy()
    for _ in range(iters):
        num = cv2.blur(num, (k, k))
        den = cv2.blur(den, (k, k))
        k = k * 2 + 1
        fill = (acc_w < 1) & (den > 1e-3)
        if not fill.any():
            break
        out[fill] = num[fill] / den[fill, None]
        acc_w[fill] = 1
        num = out * acc_w[..., None]
        den = acc_w.copy()
    return out


def downsample(img: np.ndarray, ss: int) -> np.ndarray:
    if ss == 1:
        return img
    H, W = img.shape[:2]
    return cv2.resize(img, (W // ss, H // ss), interpolation=cv2.INTER_AREA)
