"""Vectorize the J-WALT wordmark from page 1 of the source pack.

The only logo in the pack is an ~845px-wide raster inside a JPEG slide, too
soft to scale for a 1080p end frame. A plain trace reproduces the JPEG block
noise as visible wobble on the straight stems, so this runs in two stages:

Stage 1 -- trace
  crop the wordmark (rows 346-488 of the 2000x1125 page raster; the
  INTERIORS|MEP|CONTRACTING descriptor starts at row 492 and is excluded --
  the film sets that line in type), build a 'redness' channel r-(g+b)/2 so
  JPEG noise on white drops out, upsample 4x (Lanczos), threshold at half the
  ink level, trace with potrace (potracer, a pure-Python port).

Stage 2 -- geometric reconstruction
  resample each outline by arc length, split it at Douglas-Peucker corners,
  fit every long run with a total-least-squares line, snap near-horizontal
  and near-vertical edges exactly, share cap-height/baseline levels, snap
  slanted edges to common italic angles, then rebuild each outline from line
  intersections. Runs that are genuinely curved (the J hook, W foot, A
  shoulder) become tangent-continuous cubic fillets; roundings smaller than
  ~5 native px are JPEG softening, not design, and become sharp corners.

Both stages are rasterized and scored (IoU) against the source mask.
Writes assets/logo/jwalt-wordmark.svg + .json (clean geometry, used by the
film) and assets/logo/jwalt-wordmark-trace.svg (raw stage-1 trace, reference).
"""
import json
import math
from pathlib import Path

import numpy as np
import potrace
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
CROP = (515, 346, 1387, 489)   # x0, y0, x1, y1 in native page pixels
UP = 4
STEP = 2.0                      # arc-length resampling step (4x units)
MIN_STRAIGHT = 40.0             # shortest run treated as a straight edge
MAX_SAGITTA = 1.2               # bow (units) always accepted as straight
MIN_RADIUS = 600.0              # larger implied radius -> straight edge
SHARP_FILLET = 22.0             # fillets with tangent length below this -> sharp corner
H_SNAP_DEG, V_SNAP_DEG, SLANT_SNAP_DEG = 4.0, 2.0, 1.6
LEVEL_SNAP = 7.0                # horizontal edges within this many units share a level


# ---------------------------------------------------------------- stage 1
def trace_mask():
    src = Image.open(ROOT / "analysis" / "pages" / "p01.jpg").convert("RGB").crop(CROP)
    a = np.asarray(src).astype(np.float32)
    redness = np.clip(a[:, :, 0] - (a[:, :, 1] + a[:, :, 2]) / 2, 0, 255)
    ink = float(np.percentile(redness[redness > 60], 50))
    up = Image.fromarray(redness.astype(np.uint8)).resize(
        (src.width * UP, src.height * UP), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
    mask = np.asarray(up) > ink * 0.5
    # potracer's Bitmap inverts its input (True = paper), hence ~mask.
    paths = potrace.Bitmap(~mask).trace(turdsize=40, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                        alphamax=0.75, opticurve=True, opttolerance=0.15)
    return mask, paths


def cubic(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def flatten_potrace(curve):
    pts = [np.array([curve.start_point.x, curve.start_point.y])]
    for seg in curve.segments:
        e = np.array([seg.end_point.x, seg.end_point.y])
        if seg.is_corner:
            pts += [np.array([seg.c.x, seg.c.y]), e]
        else:
            c1, c2 = np.array([seg.c1.x, seg.c1.y]), np.array([seg.c2.x, seg.c2.y])
            pts += list(cubic(pts[-1], c1, c2, e, 16)[1:])
    return np.array(pts[:-1])  # ring, last point == first


def potrace_d(curve):
    s = curve.start_point
    d = [f"M{s.x:.2f} {s.y:.2f}"]
    for seg in curve.segments:
        if seg.is_corner:
            d.append(f"L{seg.c.x:.2f} {seg.c.y:.2f}L{seg.end_point.x:.2f} {seg.end_point.y:.2f}")
        else:
            d.append(f"C{seg.c1.x:.2f} {seg.c1.y:.2f} {seg.c2.x:.2f} {seg.c2.y:.2f} "
                     f"{seg.end_point.x:.2f} {seg.end_point.y:.2f}")
    return "".join(d) + "Z"


# ---------------------------------------------------------------- stage 2
def resample(ring, step=STEP):
    closed = np.vstack([ring, ring[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(0, s[-1], step)
    return np.stack([np.interp(t, s, closed[:, 0]), np.interp(t, s, closed[:, 1])], axis=1)


def dp_indices(pts, eps, lo, hi):
    a, b = pts[lo], pts[hi]
    ab = b - a
    n = np.hypot(*ab) + 1e-9
    seg = pts[lo:hi + 1] - a
    dist = np.abs(ab[0] * seg[:, 1] - ab[1] * seg[:, 0]) / n
    k = int(np.argmax(dist))
    if dist[k] > eps and 0 < k < hi - lo:
        return dp_indices(pts, eps, lo, lo + k)[:-1] + dp_indices(pts, eps, lo + k, hi)
    return [lo, hi]


def fit_line(pts):
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c)
    u = vt[0]
    resid = (pts - c) @ vt[1]
    return c, u, float(np.sqrt((resid ** 2).mean()))


def intersect(c1, u1, c2, u2):
    m = np.array([u1, -u2]).T
    if abs(np.linalg.det(m)) < 1e-9:
        return None
    t = np.linalg.solve(m, c2 - c1)
    return c1 + t[0] * u1


def angle_deg(u):
    return math.degrees(math.atan2(u[1], u[0])) % 180.0


def tangent_angles(P, half=5):
    """Unwrapped tangent direction (degrees) at each ring point, from a +-half window."""
    n = len(P)
    fwd = P[(np.arange(n) + half) % n] - P[(np.arange(n) - half) % n]
    th = np.degrees(np.unwrap(np.arctan2(fwd[:, 1], fwd[:, 0])))
    return th


def reconstruct(rings):
    # --- split every ring into runs; classify each as straight edge or curve
    models = []
    for ring in rings:
        P = resample(ring)
        n = len(P)
        th = tangent_angles(P, half=8)
        # start the ring at the sharpest turn so no edge wraps around the seam
        k0 = int(np.argmax(np.abs(np.roll(th, -4) - np.roll(th, 4))))
        P = np.roll(P, -k0, axis=0)
        th = tangent_angles(P, half=8)
        closed = np.vstack([P, P[:1]])
        # a closed ring has identical end points, so split at the far point first
        kf = int(np.argmax(((P - P[0]) ** 2).sum(1)))
        idx = dp_indices(closed, 6.0, 0, kf)[:-1] + dp_indices(closed, 6.0, kf, n)
        # tiny outlines (the hyphen, ~14 native px edges) carry proportionally more
        # JPEG noise, so their edges get a looser straightness tolerance
        small = np.ptp(P[:, 0]) < 200 and np.ptp(P[:, 1]) < 200
        max_sag = 3.0 if small else MAX_SAGITTA
        runs = []
        for i0, i1 in zip(idx[:-1], idx[1:]):
            chain = closed[i0:i1 + 1]
            length = np.hypot(*(chain[-1] - chain[0]))
            m = len(chain)
            core = closed[i0 + m // 6:i1 - m // 6 + 1] if m > 8 else chain
            # straightness = sagitta of a least-squares parabola in the chord's frame;
            # JPEG jaggies average out, only systematic curvature remains
            c, u, _ = fit_line(chain)
            x = (chain - c) @ u
            y = (chain - c) @ np.array([-u[1], u[0]])
            quad = np.linalg.lstsq(np.vstack([x ** 2, x, np.ones_like(x)]).T, y, rcond=None)[0][0]
            sagitta = abs(quad) * (np.ptp(x) / 2) ** 2
            # the wordmark's designed curves have radii < ~250 units; a bow implying a
            # radius beyond MIN_RADIUS is JPEG softening on a straight edge
            radius = length ** 2 / (8 * sagitta) if sagitta > 1e-6 else 1e9
            straight = length >= MIN_STRAIGHT and (sagitta < max_sag or radius > MIN_RADIUS)
            if straight:
                c, u, _ = fit_line(core)
            runs.append({"chain": chain, "straight": straight, "c": c, "u": u})
        # noise can split one edge in two: merge consecutive near-parallel straight runs
        merged = []
        for r in runs:
            if merged and r["straight"] and merged[-1]["straight"]:
                a = abs(angle_deg(r["u"]) - angle_deg(merged[-1]["u"]))
                if min(a, 180 - a) < 3.0:
                    chain = np.vstack([merged[-1]["chain"], r["chain"][1:]])
                    c, u, _ = fit_line(chain)
                    merged[-1] = {"chain": chain, "straight": True, "c": c, "u": u}
                    continue
            merged.append(r)
        # ...including across the ring's seam
        if len(merged) > 2 and merged[0]["straight"] and merged[-1]["straight"]:
            a = abs(angle_deg(merged[0]["u"]) - angle_deg(merged[-1]["u"]))
            if min(a, 180 - a) < 3.0:
                chain = np.vstack([merged[-1]["chain"], merged[0]["chain"][1:]])
                c, u, _ = fit_line(chain)
                merged = [{"chain": chain, "straight": True, "c": c, "u": u}] + merged[1:-1]
        models.append(merged)

    # --- snap directions: horizontal, vertical, and shared italic slants
    lines = [r for runs in models for r in runs if r["straight"]]
    for r in lines:
        a = angle_deg(r["u"])
        if min(a, 180 - a) < H_SNAP_DEG:
            r["kind"], r["u"] = "h", np.array([1.0, 0.0])
        elif abs(a - 90) < V_SNAP_DEG:
            r["kind"], r["u"] = "v", np.array([0.0, 1.0])
        else:
            r["kind"] = "s"
            r["a"] = a
    slants = sorted([r for r in lines if r["kind"] == "s"], key=lambda r: r["a"])
    clusters, cur = [], []
    for r in slants:
        if cur and r["a"] - cur[-1]["a"] > SLANT_SNAP_DEG:
            clusters.append(cur); cur = []
        cur.append(r)
    if cur:
        clusters.append(cur)
    for cl in clusters:
        if len(cl) < 2:
            continue
        # length-weighted mean angle of the cluster
        w = np.array([np.hypot(*(r["chain"][-1] - r["chain"][0])) for r in cl])
        a = float((np.array([r["a"] for r in cl]) * w).sum() / w.sum())
        for r in cl:
            r["u"] = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
    # re-centre every snapped line on its own points (least squares offset)
    for r in lines:
        nrm = np.array([-r["u"][1], r["u"][0]])
        pts = r["chain"]
        off = float(np.median(pts @ nrm))
        r["c"] = nrm * off + r["u"] * float(np.median(pts @ r["u"]))
    # shared horizontal levels (cap height, baseline, bar lines)
    hs = sorted([r for r in lines if r["kind"] == "h"], key=lambda r: r["c"][1])
    groups, cur = [], []
    for r in hs:
        if cur and r["c"][1] - cur[-1]["c"][1] > LEVEL_SNAP:
            groups.append(cur); cur = []
        cur.append(r)
    if cur:
        groups.append(cur)
    for g in groups:
        y = float(np.median([r["c"][1] for r in g]))
        for r in g:
            r["c"] = np.array([r["c"][0], y])

    # --- rebuild outlines
    d_parts, polys = [], []
    for runs in models:
        # rotate so the list starts with a straight run
        s0 = next(i for i, r in enumerate(runs) if r["straight"])
        runs = runs[s0:] + runs[:s0]
        straight_idx = [i for i, r in enumerate(runs) if r["straight"]]
        cmds, poly = [], []
        for j, i in enumerate(straight_idx):
            a = runs[i]
            nxt = straight_idx[(j + 1) % len(straight_idx)]
            b = runs[nxt]
            between = runs[i + 1:nxt] if nxt > i else runs[i + 1:]
            V = intersect(a["c"], a["u"], b["c"], b["u"])
            if not between:
                if V is not None:          # parallel neighbours: the edge simply continues
                    cmds.append(("L", V))
                continue
            curve_pts = np.vstack([r["chain"] for r in between])
            # tangent points: where the curved run leaves line a / joins line b
            A = a["c"] + a["u"] * float((curve_pts[0] - a["c"]) @ a["u"])
            B = b["c"] + b["u"] * float((curve_pts[-1] - b["c"]) @ b["u"])
            if V is None:                  # U-turn between parallel edges: keep the traced points
                cmds.append(("L", A))
                cmds += [("L", p) for p in curve_pts[::4]]
                cmds.append(("L", B))
                continue
            if np.hypot(*(A - V)) < SHARP_FILLET and np.hypot(*(B - V)) < SHARP_FILLET:
                cmds.append(("L", V))
                continue
            # fit the two handle lengths so the fillet hugs the traced curve
            best = (1e18, 0.55, 0.55)
            for k1 in np.linspace(0.15, 1.0, 35):
                for k2 in np.linspace(0.15, 1.0, 35):
                    q = cubic(A, A + k1 * (V - A), B + k2 * (V - B), B, 40)
                    dist = np.sqrt(((curve_pts[:, None, :] - q[None, :, :]) ** 2).sum(-1)).min(1)
                    err = float((dist ** 2).mean())
                    if err < best[0]:
                        best = (err, k1, k2)
            _, k1, k2 = best
            cmds.append(("L", A))
            cmds.append(("C", A + k1 * (V - A), B + k2 * (V - B), B))
        # the outline is closed: first command's point is the start
        start = cmds[-1][-1]
        d = [f"M{start[0]:.2f} {start[1]:.2f}"]
        cur_pt = start
        poly.append(start)
        for cmd in cmds:
            if cmd[0] == "L":
                d.append(f"L{cmd[1][0]:.2f} {cmd[1][1]:.2f}")
                poly.append(cmd[1]); cur_pt = cmd[1]
            else:
                _, c1, c2, e = cmd
                d.append(f"C{c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} {e[0]:.2f} {e[1]:.2f}")
                poly += list(cubic(cur_pt, c1, c2, e, 24)[1:]); cur_pt = e
        d_parts.append("".join(d) + "Z")
        polys.append(np.array(poly))
    return d_parts, polys


# ---------------------------------------------------------------- scoring
def rasterize(polys, shape):
    H, W = shape
    acc = np.zeros((H, W), dtype=np.uint8)
    for poly in polys:
        layer = Image.new("1", (W, H), 0)
        ImageDraw.Draw(layer).polygon([tuple(p) for p in poly], fill=1)
        acc ^= np.asarray(layer, dtype=np.uint8)
    return acc.astype(bool)


def iou(a, b):
    return (a & b).sum() / (a | b).sum()


def main():
    mask, paths = trace_mask()
    rings = [flatten_potrace(c) for c in paths]
    raw = rasterize(rings, mask.shape)
    d_parts, polys = reconstruct(rings)
    clean = rasterize(polys, mask.shape)
    ys, xs = np.where(clean)
    b = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    out = ROOT / "assets" / "logo"
    d_all = " ".join(d_parts)
    (out / "jwalt-wordmark.json").write_text(json.dumps(
        {"d": d_all, "bounds": b, "units": f"{UP}x native page pixels",
         "source": f"source pack p01, crop {CROP}", "fillRule": "evenodd",
         "iou_vs_source": round(float(iou(clean, mask)), 4)}, indent=1))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]} {b[1]} {b[2]-b[0]} {b[3]-b[1]}">'
           f'<path fill="#BE1B20" fill-rule="evenodd" d="{{}}"/></svg>\n')
    (out / "jwalt-wordmark.svg").write_text(svg.format(d_all))
    (out / "jwalt-wordmark-trace.svg").write_text(svg.format(" ".join(potrace_d(c) for c in paths)))
    print(f"outlines {len(polys)}  bounds {b}")
    print(f"IoU raw trace vs source      {iou(raw, mask):.4f}")
    print(f"IoU reconstruction vs source {iou(clean, mask):.4f}")
    print(f"IoU reconstruction vs trace  {iou(clean, raw):.4f}")


if __name__ == "__main__":
    main()
