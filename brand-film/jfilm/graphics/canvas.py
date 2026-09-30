"""Vector graphics layer (skia): hairlines, projected 3D linework with depth
occlusion, and typography with tracking. All sizes are authored for a
1080-pixel short side and scale with the output format."""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import skia

from .. import config
from ..camera import View

_TAG_WGHT = (ord("w") << 24) | (ord("g") << 16) | (ord("h") << 8) | ord("t")


@lru_cache(maxsize=32)
def typeface(path: str, weight: float) -> skia.Typeface:
    tf = skia.Typeface.MakeFromFile(path)
    co = skia.FontArguments.VariationPosition.Coordinates(
        [skia.FontArguments.VariationPosition.Coordinate(_TAG_WGHT, float(weight))])
    args = skia.FontArguments()
    args.setVariationDesignPosition(skia.FontArguments.VariationPosition(co))
    return tf.makeClone(args)


def rgb255(c, a=1.0):
    return skia.Color4f(float(c[0]), float(c[1]), float(c[2]), float(np.clip(a, 0, 1)))


class Graphics:
    def __init__(self, view: View, fmt, t: float, depth: np.ndarray | None = None, preview_scale: float = 1.0):
        self.view = view
        self.fmt = fmt
        self.t = t
        self.W, self.H = view.W, view.H
        self.depth = depth
        self.cfg = config.load()
        self.pal = self.cfg.palette
        self.u = min(self.W, self.H) / 1080.0
        info = skia.ImageInfo.Make(self.W, self.H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
        self.surface = skia.Surface.MakeRaster(info)
        self.c = self.surface.getCanvas()
        self.c.clear(skia.ColorTRANSPARENT)
        self.dirty = False

    # --- output ------------------------------------------------------------
    def rgba(self) -> np.ndarray:
        img = self.surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                                        alphaType=skia.kPremul_AlphaType)
        return img.astype(np.float32) / 255.0

    # --- paints -------------------------------------------------------------
    def paint(self, color, alpha=1.0, width=1.0, glow=0.0, cap=skia.Paint.kButt_Cap, fill=False):
        p = skia.Paint(AntiAlias=True)
        p.setColor4f(rgb255(color, alpha))
        p.setStyle(skia.Paint.kFill_Style if fill else skia.Paint.kStroke_Style)
        p.setStrokeWidth(max(0.35, width * self.u))
        p.setStrokeCap(cap)
        if glow > 0:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, glow * self.u))
        return p

    def stroke_path(self, path: skia.Path, color, alpha, width, glow=0.0, glow_alpha=0.35):
        if alpha <= 0.002:
            return
        self.dirty = True
        if glow > 0:
            self.c.drawPath(path, self.paint(color, alpha * glow_alpha, width * 2.2, glow=glow))
        self.c.drawPath(path, self.paint(color, alpha, width))

    # --- 2D ------------------------------------------------------------------
    def line2d(self, p0, p1, color, alpha=1.0, width=1.0, glow=0.0):
        path = skia.Path()
        path.moveTo(*p0)
        path.lineTo(*p1)
        self.stroke_path(path, color, alpha, width, glow)

    def rect_fill(self, x0, y0, x1, y1, color, alpha):
        if alpha <= 0.002:
            return
        self.dirty = True
        self.c.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), self.paint(color, alpha, fill=True))

    # --- projected 3D linework -------------------------------------------------------
    def project_segments(self, segs: np.ndarray, near: float = 0.05):
        """segs (N,2,3) world -> screen (N,2,2), depth (N,2), valid (N,), clipped at near plane."""
        v = self.view
        a = v.to_cam(segs[:, 0])
        b = v.to_cam(segs[:, 1])
        za, zb = -a[:, 2], -b[:, 2]
        valid = (za > near) | (zb > near)
        # clip to near plane
        t = np.clip((near - za) / np.where(np.abs(zb - za) < 1e-9, 1e-9, zb - za), 0, 1)
        a2 = np.where((za < near)[:, None], a + (b - a) * t[:, None], a)
        t2 = np.clip((near - zb) / np.where(np.abs(za - zb) < 1e-9, 1e-9, za - zb), 0, 1)
        b2 = np.where((zb < near)[:, None], b + (a - b) * t2[:, None], b)

        def to_px(c):
            z = -c[:, 2]
            return np.stack([v.cx + v.fx * c[:, 0] / z, v.cy - v.fy * c[:, 1] / z], -1), z

        pa, da = to_px(a2)
        pb, db = to_px(b2)
        return np.stack([pa, pb], 1), np.stack([da, db], 1), valid

    def lines3d(self, segs: np.ndarray, color, width=1.0, alpha=1.0, progress=None, occlude: bool = False,
                glow: float = 0.0, glow_alpha: float = 0.35, depth_tol: float = 0.012, fade_depth=None,
                step_px: float = 7.0, heads: float = 0.0):
        """Draw 3D segments. progress (N,) in 0..1 draws each from its first
        endpoint; alpha may be per-segment. Occlusion samples the visibility
        depth buffer along each segment."""
        if len(segs) == 0:
            return
        segs = np.asarray(segs, np.float64)
        n = len(segs)
        al = np.broadcast_to(np.asarray(alpha, np.float64), (n,)).copy()
        if progress is not None:
            pr = np.clip(np.broadcast_to(np.asarray(progress, np.float64), (n,)), 0, 1)
            keep = (pr > 1e-4) & (al > 0.002)
            segs, pr, al = segs[keep], pr[keep], al[keep]
            segs = np.stack([segs[:, 0], segs[:, 0] + (segs[:, 1] - segs[:, 0]) * pr[:, None]], 1)
        else:
            keep = al > 0.002
            segs, al = segs[keep], al[keep]
            pr = np.ones(len(segs))
        if len(segs) == 0:
            return
        P, D, valid = self.project_segments(segs)
        segs, P, D, al, pr = segs[valid], P[valid], D[valid], al[valid], pr[valid]
        if fade_depth is not None:
            d0, d1 = fade_depth
            dm = D.mean(1)
            al = al * np.clip(1 - (dm - d0) / max(d1 - d0, 1e-6), 0.15, 1)
        if occlude and self.depth is not None:
            P, al = self._occlude(P, D, al, depth_tol, step_px)
        if len(P) == 0:
            return
        # bucket by alpha to keep draw calls low
        q = np.clip(np.round(al * 24), 0, 24).astype(int)
        for level in np.unique(q):
            if level == 0:
                continue
            sel = q == level
            path = skia.Path()
            for (x0, y0), (x1, y1) in P[sel]:
                if not (np.isfinite(x0) and np.isfinite(y1)):
                    continue
                if max(abs(x0), abs(y0), abs(x1), abs(y1)) > 1e6:
                    continue
                path.moveTo(float(x0), float(y0))
                path.lineTo(float(x1), float(y1))
            self.stroke_path(path, color, level / 24.0, width, glow, glow_alpha)
        if heads > 0 and progress is not None:
            live = (pr > 0.02) & (pr < 0.98)
            if live.any():
                path = skia.Path()
                for (_, _), (x1, y1) in P[live]:
                    path.addCircle(float(x1), float(y1), 1.6 * self.u)
                self.dirty = True
                self.c.drawPath(path, self.paint(color, heads * 0.8, fill=True, glow=3.0))
                self.c.drawPath(path, self.paint(color, heads, fill=True))

    def _occlude(self, P, D, al, tol, step_px):
        H, W = self.depth.shape
        L = np.hypot(*(P[:, 1] - P[:, 0]).T)
        k = np.clip(np.ceil(L / step_px), 1, 400).astype(int)
        rep = np.repeat(np.arange(len(P)), k)
        j = np.concatenate([np.arange(c) for c in k])
        kk = k[rep]
        t0 = j / kk
        t1 = (j + 1) / kk
        tm = (t0 + t1) / 2
        a, b = P[rep, 0], P[rep, 1]
        da, db = D[rep, 0], D[rep, 1]
        # perspective-correct depth interpolation along the screen segment
        inv = (1 - tm) / da + tm / db
        dm = 1 / inv
        pm = a + (b - a) * tm[:, None]
        xi = np.clip(pm[:, 0].astype(int), 0, W - 1)
        yi = np.clip(pm[:, 1].astype(int), 0, H - 1)
        inside = (pm[:, 0] >= 0) & (pm[:, 0] < W) & (pm[:, 1] >= 0) & (pm[:, 1] < H)
        zb = self.depth[yi, xi]
        vis = ~inside | (dm <= zb * (1 + tol) + 0.02)
        pa = a + (b - a) * t0[:, None]
        pb = a + (b - a) * t1[:, None]
        return np.stack([pa, pb], 1)[vis], al[rep][vis]

    # --- typography ------------------------------------------------------------
    def font(self, role: str, size_px: float, weight: float | None = None) -> skia.Font:
        ty = self.cfg.typography[role]
        tf = typeface(str(self.cfg.font_path(role)), float(weight if weight is not None else ty["weight"]))
        f = skia.Font(tf, size_px * self.u)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setHinting(skia.FontHinting.kNone)
        return f

    def measure(self, text: str, font: skia.Font, tracking: float) -> float:
        g = font.textToGlyphs(text)
        w = font.getWidths(g)
        return float(sum(w) + tracking * font.getSize() * max(len(text) - 1, 0))

    def text(self, text: str, x: float, y: float, role: str = "display", size: float = 64.0, color=None,
             alpha: float = 1.0, tracking: float | None = None, align: str = "center", weight=None,
             per_glyph=None, clip=None):
        """Draw tracked text. (x, y) = anchor on the baseline. per_glyph(i, n)
        -> (alpha, dy_px) lets callers stagger glyph reveals. clip = (x0,y0,x1,y1)."""
        if alpha <= 0.002:
            return 0.0
        color = color or self.pal["warm_white"]
        tr = self.cfg.typography[role]["tracking"] if tracking is None else tracking
        f = self.font(role, size, weight)
        wtot = self.measure(text, f, tr)
        x0 = x - wtot / 2 if align == "center" else (x - wtot if align == "right" else x)
        glyphs = f.textToGlyphs(text)
        widths = f.getWidths(glyphs)
        self.dirty = True
        if clip is not None:
            self.c.save()
            self.c.clipRect(skia.Rect.MakeLTRB(*clip))
        cx = x0
        n = len(text)
        for i, (ch, w) in enumerate(zip(text, widths)):
            a, dy = (1.0, 0.0) if per_glyph is None else per_glyph(i, n)
            if a > 0.002 and ch != " ":
                p = skia.Paint(AntiAlias=True)
                p.setColor4f(rgb255(color, alpha * a))
                self.c.drawString(ch, cx, y + dy * self.u, f, p)
            cx += w + tr * f.getSize()
        if clip is not None:
            self.c.restore()
        return wtot
