"""Chapter titles: one restrained treatment used for every word in the film.

A hairline rule draws out from centre; the word's glyphs rise from behind
it (masked), staggered; tracking relaxes slowly while it holds; on exit the
glyphs lift and dissolve in reverse order and the rule retracts."""
from __future__ import annotations

from .. import easing as E

# vertical anchor (fraction of frame height) of the title baseline per format
BASELINE = {"16x9": 0.845, "9x16": 0.80, "1x1": 0.86}


def chapter(g, word: str, t: float, t_in: float, t_out: float, size: float = 58.0, y_frac: float | None = None,
            color=None, rule_color=None, tracking: float | None = None):
    if t < t_in - 0.01 or t > t_out + 0.05:
        return
    pal = g.pal
    color = color or pal["warm_white"]
    rule_color = rule_color or pal["accent"]
    base_tr = g.cfg.typography["display"]["tracking"] if tracking is None else tracking
    hold = max(t_out - t_in, 1e-3)
    # tracking breathes from +0.10em to +0.0em across the hold
    tr = base_tr + 0.10 * (1 - E.out_sine((t - t_in) / hold))
    yb = (y_frac if y_frac is not None else BASELINE.get(g.fmt.key, 0.84)) * g.H
    cx = g.W / 2
    f = g.font("display", size)
    w = g.measure(word, f, tr)
    u = g.u

    # rule
    r_in = E.out_expo(E.lin(t_in, t_in + 0.55, t))
    r_out = E.in_cubic(E.lin(t_out - 0.35, t_out, t))
    half = (w * 0.5 + 26 * u) * r_in * (1 - r_out)
    ry = yb + 20 * u
    if half > 0.5:
        g.line2d((cx - half, ry), (cx + half, ry), rule_color, alpha=0.9, width=1.0, glow=1.5)

    n = len(word)

    def per_glyph(i, n_):
        a_in = E.TYPE(E.lin(t_in + 0.12 + 0.045 * i, t_in + 0.12 + 0.045 * i + 0.6, t))
        j = n_ - 1 - i
        a_out = E.in_cubic(E.lin(t_out - 0.42 + 0.03 * j, t_out - 0.12 + 0.03 * j, t))
        dy = (1 - a_in) * 0.62 * size - a_out * 10.0
        return a_in * (1 - a_out), dy

    g.text(word, cx, yb, role="display", size=size, color=color, tracking=tr, per_glyph=per_glyph,
           clip=(0, 0, g.W, ry - 3 * u))
