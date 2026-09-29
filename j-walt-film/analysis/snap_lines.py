"""Register hand-authored construction lines to a photograph.

The opening of the film draws a line drawing of the Heidelberg reception and
then reveals the photograph *under* it, so the lines must sit exactly on the
real edges. Lines are authored by eye (±3px) in <asset>.lines.src.json, then
each one is snapped here:

  * "edge" lines   -> maximise mean gradient magnitude along the line
  * "joint" lines  -> maximise dark-ridge response (thin dark panel joints)
  * polylines      -> every vertex snapped along its local normal, then
                      re-smoothed
  * ellipses       -> kept as authored (fitted separately, see fit_rings)

Writes <asset>.lines.json (consumed by the engine) and an overlay proof
analysis/contact/<asset>-lines-proof.jpg.

Usage: python analysis/snap_lines.py heid-reception
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent


def load_gray(path):
    g = Image.open(path).convert("L").filter(ImageFilter.GaussianBlur(1.0))
    return np.asarray(g, dtype=np.float32)


def bilinear(img, x, y):
    h, w = img.shape
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def responses(gray):
    gy, gx = np.gradient(gray)
    grad = np.hypot(gx, gy)
    return grad


def line_score(gray, grad, p0, p1, kind, n=120):
    t = np.linspace(0.04, 0.96, n)
    pts = p0[None] * (1 - t[:, None]) + p1[None] * t[:, None]
    d = (p1 - p0) / (np.linalg.norm(p1 - p0) + 1e-9)
    nrm = np.array([-d[1], d[0]])
    if kind == "joint":
        c = bilinear(gray, pts[:, 0], pts[:, 1])
        side = 0.5 * (bilinear(gray, *(pts + 2.5 * nrm).T) + bilinear(gray, *(pts - 2.5 * nrm).T))
        return float(np.mean(side - c))           # dark thin line -> positive
    return float(np.mean(bilinear(grad, pts[:, 0], pts[:, 1])))


def snap_segment(gray, grad, p0, p1, kind, rng=5.0):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    nrm = np.array([-d[1], d[0]])
    best = (line_score(gray, grad, p0, p1, kind), 0.0, 0.0)
    offs = np.arange(-rng, rng + 0.01, 0.5)
    for a in offs:
        for b in offs:
            s = line_score(gray, grad, p0 + a * nrm, p1 + b * nrm, kind)
            if s > best[0]:
                best = (s, a, b)
    _, a, b = best
    return (p0 + a * nrm).round(2).tolist(), (p1 + b * nrm).round(2).tolist(), round(best[0], 2), (a, b)


def snap_polyline(grad, pts, rng=5.0):
    pts = np.array(pts, float)
    out = pts.copy()
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        d = (b - a) / (np.linalg.norm(b - a) + 1e-9)
        nrm = np.array([-d[1], d[0]])
        offs = np.arange(-rng, rng + 0.01, 0.5)
        vals = [bilinear(grad, *(pts[i] + o * nrm)[None].T)[0] for o in offs]
        out[i] = pts[i] + offs[int(np.argmax(vals))] * nrm
    # light smoothing keeps the curve fair after independent vertex snaps
    sm = out.copy()
    for i in range(1, len(out) - 1):
        sm[i] = 0.25 * out[i - 1] + 0.5 * out[i] + 0.25 * out[i + 1]
    return sm.round(2).tolist()


def main(asset):
    src = json.loads((ROOT / "assets" / "portfolio" / f"{asset}.lines.src.json").read_text())
    img_path = ROOT / "assets" / "portfolio" / f"{asset}.jpg"
    gray = load_gray(img_path)
    grad = responses(gray)
    out = {"asset": asset, "size": list(gray.shape[::-1]), "elements": []}
    for el in src["elements"]:
        e = dict(el)
        if el["type"] == "line":
            p0, p1, score, (a, b) = snap_segment(gray, grad, el["p0"], el["p1"], el.get("kind", "edge"))
            e.update(p0=p0, p1=p1, score=score)
            print(f"{el['id']:18s} {el.get('kind','edge'):5s} moved {a:+.1f}/{b:+.1f}px  score {score}")
        elif el["type"] == "polyline" and el.get("snap", True):
            e["points"] = snap_polyline(grad, el["points"])
            print(f"{el['id']:18s} polyline snapped ({len(el['points'])} pts)")
        out["elements"].append(e)
    (ROOT / "assets" / "portfolio" / f"{asset}.lines.json").write_text(json.dumps(out, indent=1))

    # proof: lines over a slightly faded photo, plus 2x crops of registration
    im = Image.open(img_path).convert("RGB")
    im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.35)
    scale = 2
    big = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    for e in out["elements"]:
        col = (220, 20, 60)
        if e["type"] == "line":
            d.line([tuple(np.array(e["p0"]) * scale), tuple(np.array(e["p1"]) * scale)], fill=col, width=2)
        elif e["type"] == "polyline":
            d.line([tuple(np.array(p) * scale) for p in e["points"]], fill=col, width=2)
        elif e["type"] == "ellipse":
            cx, cy, rx, ry, rot = e["cx"], e["cy"], e["rx"], e["ry"], np.radians(e.get("rot", 0))
            t = np.linspace(0, 2 * np.pi, 240)
            x = cx + rx * np.cos(t) * np.cos(rot) - ry * np.sin(t) * np.sin(rot)
            y = cy + rx * np.cos(t) * np.sin(rot) + ry * np.sin(t) * np.cos(rot)
            d.line(list(zip(x * scale, y * scale)), fill=(20, 90, 220), width=2)
    proof = ROOT / "analysis" / "contact" / f"{asset}-lines-proof.jpg"
    big.save(proof, quality=88)
    print("proof ->", proof.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1])
