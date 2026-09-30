"""Camera model shared by Blender, the projection compositor and the vector
graphics layer, so every layer agrees on the same pixel for the same point.

Conventions
-----------
World: metres, Z up. yaw=0/pitch=0 looks down +Y; positive yaw turns left
(counter-clockwise seen from above); pitch -90 looks straight down with +Y
at the top of frame. Camera space follows Blender: x right, y up, looking
down -z. Pixel space: origin top-left, x right, y down, pixel centres at
+0.5. Depth is planar (distance along the view axis), matching the Z pass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from . import easing

SENSOR_H = 24.0  # mm, vertical sensor fit for every format


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)


# Columns = camera x (right), y (up), z (backward) in world, for yaw=pitch=0.
_BASE = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)


def rotation(yaw_deg: float, pitch_deg: float, roll_deg: float = 0.0) -> np.ndarray:
    """World-from-camera rotation (columns are camera axes in world)."""
    return _rz(math.radians(yaw_deg)) @ _rx(math.radians(pitch_deg)) @ _BASE @ _rz(math.radians(roll_deg))


def ypr_look_at(pos, target) -> tuple[float, float]:
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    yaw = math.degrees(math.atan2(-f[0], f[1]))
    pitch = math.degrees(math.asin(np.clip(f[2], -1, 1)))
    return yaw, pitch


@dataclass(frozen=True)
class CamState:
    pos: tuple[float, float, float]
    yaw: float
    pitch: float
    vfov: float                      # vertical FOV (deg) of the 16:9 master
    roll: float = 0.0
    focus: float | None = None       # metres; None = everything sharp
    fstop: float = 11.0

    @staticmethod
    def look(pos, target, vfov, roll=0.0, focus=None, fstop=11.0) -> "CamState":
        yaw, pitch = ypr_look_at(pos, target)
        if focus == "target":
            focus = float(np.linalg.norm(np.asarray(target, float) - np.asarray(pos, float)))
        return CamState(tuple(map(float, pos)), yaw, pitch, vfov, roll, focus, fstop)

    def with_(self, **kw) -> "CamState":
        return replace(self, **kw)


class View:
    """A camera state rendered at a given pixel size / format reframe."""

    def __init__(self, cam: CamState, width: int, height: int, fov_scale: float = 1.0,
                 yaw_offset: float = 0.0, pitch_offset: float = 0.0, roll_offset: float = 0.0):
        self.cam = cam
        self.W, self.H = int(width), int(height)
        v = math.radians(cam.vfov)
        self.vfov = 2 * math.atan(math.tan(v / 2) * fov_scale)
        self.fy = (self.H / 2) / math.tan(self.vfov / 2)
        self.fx = self.fy
        self.cx, self.cy = self.W / 2, self.H / 2
        self.R = rotation(cam.yaw + yaw_offset, cam.pitch + pitch_offset, cam.roll + roll_offset)
        self.t = np.asarray(cam.pos, dtype=np.float64)

    # --- intrinsics -----------------------------------------------------
    @property
    def lens_mm(self) -> float:
        return (SENSOR_H / 2) / math.tan(self.vfov / 2)

    @property
    def hfov(self) -> float:
        return 2 * math.atan(math.tan(self.vfov / 2) * self.W / self.H)

    @property
    def forward(self) -> np.ndarray:
        return -self.R[:, 2]

    def matrix_world(self) -> np.ndarray:
        m = np.eye(4)
        m[:3, :3] = self.R
        m[:3, 3] = self.t
        return m

    # --- transforms -----------------------------------------------------
    def to_cam(self, P):
        return (np.asarray(P, dtype=np.float64) - self.t) @ self.R

    def project(self, P):
        """World points (...,3) -> (x, y, depth). depth<=0 means behind camera."""
        Pc = self.to_cam(P)
        z = -Pc[..., 2]
        zs = np.where(np.abs(z) < 1e-9, 1e-9, z)
        x = self.cx + self.fx * Pc[..., 0] / zs
        y = self.cy - self.fy * Pc[..., 1] / zs
        return x, y, z

    def unproject(self, x, y, depth):
        Xc = (x - self.cx) / self.fx * depth
        Yc = -(y - self.cy) / self.fy * depth
        Pc = np.stack([Xc, Yc, -depth], axis=-1)
        return Pc @ self.R.T + self.t

    def pixel_grid(self, ss: int = 1):
        """Pixel-centre coordinates for an ss-times supersampled buffer, in this view's pixels."""
        xs = (np.arange(self.W * ss) + 0.5) / ss
        ys = (np.arange(self.H * ss) + 0.5) / ss
        return np.meshgrid(xs, ys)

    def coc_px(self, depth):
        """Circle-of-confusion diameter in pixels for planar depth (m)."""
        if self.cam.focus is None:
            return np.zeros_like(np.asarray(depth, dtype=np.float32))
        f = self.lens_mm / 1000.0
        S = max(self.cam.focus, f * 1.01)
        N = self.cam.fstop
        d = np.maximum(np.asarray(depth, dtype=np.float64), 1e-3)
        c_m = np.abs(d - S) / d * (f * f) / (N * (S - f))
        px_per_m = self.H / (SENSOR_H / 1000.0)
        return (c_m * px_per_m).astype(np.float32)

    def scaled(self, s: float) -> "View":
        v = View.__new__(View)
        v.__dict__.update(self.__dict__)
        v.W, v.H = int(round(self.W * s)), int(round(self.H * s))
        v.fx, v.fy = self.fx * s, self.fy * s
        v.cx, v.cy = v.W / 2, v.H / 2
        return v


def view_for(cam: CamState, fmt, reframe: dict | None = None, scale: float = 1.0, t: float | None = None) -> View:
    """View of `cam` in output format `fmt` (jfilm.config.Format). Reframe
    values may be numbers or callables of film time t."""
    rf = (reframe or {}).get(fmt.key, {})

    def val(k, d):
        v = rf.get(k, d)
        return float(v(t)) if callable(v) else float(v)

    v = View(cam, round(fmt.width * scale), round(fmt.height * scale),
             fov_scale=val("fov_scale", fmt.fov_scale),
             yaw_offset=val("yaw", 0.0), pitch_offset=val("pitch", 0.0), roll_offset=val("roll", 0.0))
    d = np.array([val("dx", 0.0), val("dy", 0.0), val("dz", 0.0)])
    if d.any():
        v.t = v.t + d
    return v


# --- paths --------------------------------------------------------------

class CamPath:
    """Keyframed camera on a time-parameterised cubic Hermite spline
    (non-uniform Catmull-Rom tangents): velocity is continuous through every
    key, and the move starts/stops with zero velocity unless `end_tangents`
    is False -- the way a dolly or crane is actually operated.

    `ease` optionally re-times the whole move (e.g. easing.ARCH)."""

    def __init__(self, keys: list[tuple[float, CamState]], ease=None, end_tangents: bool = True):
        keys = sorted(keys, key=lambda k: k[0])
        self.times = np.array([k[0] for k in keys], dtype=np.float64)
        self.states = [k[1] for k in keys]
        self.ease = ease
        yaws = np.unwrap(np.radians([s.yaw for s in self.states]))
        rows = []
        for s, yw in zip(self.states, yaws):
            rows.append([*s.pos, math.degrees(yw), s.pitch, s.vfov, s.roll,
                         s.focus if s.focus is not None else np.nan, s.fstop])
        self.vals = np.array(rows, dtype=np.float64)
        # fill undefined focus by nearest defined key (keeps the spline finite)
        f = self.vals[:, 7]
        if np.isnan(f).all():
            self.has_focus = False
            self.vals[:, 7] = 0.0
        else:
            self.has_focus = True
            idx = np.where(~np.isnan(f))[0]
            for i in range(len(f)):
                if np.isnan(f[i]):
                    f[i] = f[idx[np.argmin(np.abs(idx - i))]]
        n = len(self.times)
        self.m = np.zeros_like(self.vals)
        for i in range(n):
            if 0 < i < n - 1:
                self.m[i] = (self.vals[i + 1] - self.vals[i - 1]) / (self.times[i + 1] - self.times[i - 1])
            elif not end_tangents and n > 1:
                j0, j1 = (0, 1) if i == 0 else (n - 2, n - 1)
                self.m[i] = (self.vals[j1] - self.vals[j0]) / (self.times[j1] - self.times[j0])

    @property
    def start(self):
        return float(self.times[0])

    @property
    def end(self):
        return float(self.times[-1])

    def __call__(self, t: float) -> CamState:
        n = len(self.times)
        if self.ease is not None and n > 1:
            t0, t1 = self.times[0], self.times[-1]
            t = t0 + float(self.ease((t - t0) / (t1 - t0))) * (t1 - t0)
        if n == 1 or t <= self.times[0]:
            v = self.vals[0]
        elif t >= self.times[-1]:
            v = self.vals[-1]
        else:
            i = int(np.clip(np.searchsorted(self.times, t, side="right") - 1, 0, n - 2))
            d = self.times[i + 1] - self.times[i]
            s = (t - self.times[i]) / d
            h00 = 2 * s ** 3 - 3 * s ** 2 + 1
            h10 = s ** 3 - 2 * s ** 2 + s
            h01 = -2 * s ** 3 + 3 * s ** 2
            h11 = s ** 3 - s ** 2
            v = h00 * self.vals[i] + h10 * d * self.m[i] + h01 * self.vals[i + 1] + h11 * d * self.m[i + 1]
        focus = float(v[7]) if self.has_focus else None
        return CamState((float(v[0]), float(v[1]), float(v[2])), float(v[3]), float(v[4]), float(v[5]),
                        float(v[6]), focus, float(v[8]))
