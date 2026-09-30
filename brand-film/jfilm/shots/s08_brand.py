"""S08 BRAND (32.0-35.0 s): evening falls on the hero space -- the sun goes
and the architectural light remains -- then one precise line returns (the
same gesture that opened the film) and resolves into the J-WALT mark,
services and website. Holds to the end to be read.

The mark: assets/brand/logo.svg or logo.png is used when present, never
redrawn. Without it, a typeset placeholder is shown (see README)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import skia

from .. import config, easing as E
from . import s07_hero as H
from .base import Cue, Plate, Shot as _Shot

DUSK = (32.0, 32.9)
PLATE_OUT = (32.55, 33.25)
LINE = (32.85, 33.35)
MARK = (33.05, 33.75)
SUB = (33.55, 34.15)


class Shot(_Shot):
    id = "s08_brand"

    def cam(self, t):
        return H.PATH(t)

    def plate(self, t):
        if t > PLATE_OUT[1] + 0.05:
            return None
        day = 1 - float(E.smoothstep(E.lin(*DUSK, t)))
        return Plate("finished", H.hero_layers(t, daylight=0.04 + 0.96 * day), exposure=0.05 + 0.25 * (1 - day),
                     env=0.1 + 0.9 * day)

    def post(self, t):
        return {"plate_opacity": 1 - float(E.in_out_cubic(E.lin(*PLATE_OUT, t))), "grain": 0.018}

    def draw(self, t, g):
        pal = g.pal
        u = g.u
        cx = g.W / 2
        cy = g.H * (0.47 if g.fmt.key != "9x16" else 0.46)
        # the line
        a_line = float(E.out_expo(E.lin(*LINE, t)))
        half = 210 * u * a_line
        if half > 0.5:
            ry = cy + 30 * u
            g.line2d((cx - half, ry), (cx + half, ry), pal["accent"], alpha=0.95, width=1.0, glow=2.0)
        # the mark (logo file if supplied; typeset placeholder otherwise)
        m = float(E.TYPE(E.lin(*MARK, t)))
        if m > 0.002:
            clip = (0, 0, g.W, cy + 30 * u - 3 * u)
            drawn = _draw_logo(g, cx, cy, m, clip)
            if not drawn:
                def pg(i, n):
                    k = float(E.TYPE(E.lin(MARK[0] + 0.035 * i, MARK[0] + 0.035 * i + 0.62, t)))
                    return k, (1 - k) * 60.0
                g.text(g.cfg.brand["name"], cx, cy, role="wordmark", size=96, color=pal["warm_white"], per_glyph=pg,
                       clip=clip)
        s = float(E.smoothstep(E.lin(*SUB, t)))
        if s > 0.002:
            services = "   ·   ".join(g.cfg.brand["services"])
            g.text(services, cx, cy + 80 * u, role="label", size=16, color=pal["line_dim"], alpha=s, tracking=0.34)
            g.text(g.cfg.brand["website"], cx, cy + 138 * u + (1 - s) * 6 * u, role="label", size=24,
                   color=pal["warm_white"], alpha=s, tracking=0.30)

    def cues(self):
        return [Cue(DUSK[0], "resolve_start", 1.0), Cue(LINE[0], "first_line", 0.8), Cue(MARK[0], "logo_hit", 1.0),
                Cue(SUB[0], "shimmer", 0.6)]


def _draw_logo(g, cx, cy, m, clip) -> bool:
    cfg = config.load()
    svg = config.ROOT / cfg.brand.get("logo_svg", "")
    png = config.ROOT / cfg.brand.get("logo_png", "")
    target_h = 96 * g.u
    img = None
    if svg.is_file():
        try:
            stream = skia.Stream.MakeFromFile(str(svg))
            dom = skia.SVGDOM.MakeFromStream(stream)
            size = dom.containerSize()
            s = target_h / max(size.height(), 1)
            w = size.width() * s
            g.c.save()
            g.c.clipRect(skia.Rect.MakeLTRB(*clip))
            g.c.translate(cx - w / 2, cy - target_h + (1 - m) * 40 * g.u)
            g.c.scale(s, s)
            g.c.saveLayerAlpha(None, int(255 * min(1, m * 1.4)))
            dom.render(g.c)
            g.c.restore()
            g.c.restore()
            g.dirty = True
            return True
        except Exception:
            img = None
    if png.is_file():
        img = skia.Image.open(str(png))
        s = target_h / img.height()
        w = img.width() * s
        g.c.save()
        g.c.clipRect(skia.Rect.MakeLTRB(*clip))
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(min(1.0, m * 1.4))
        g.c.drawImageRect(img, skia.Rect.MakeXYWH(cx - w / 2, cy - target_h + (1 - m) * 40 * g.u, w, target_h),
                          skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)
        g.c.restore()
        g.dirty = True
        return True
    return False
