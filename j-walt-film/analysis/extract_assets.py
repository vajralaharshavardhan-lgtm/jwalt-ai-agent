"""Extract photographs from J-WALT-Brand-Film-Source-Pack.pdf.

Each PDF page is a single flattened 2000x1125 JPEG of a slide. Photos are
cropped out of those slide rasters: an approximate box (measured by eye on a
1200x675 preview) is tightened automatically by walking each edge inward
while the row/column is flat page background.

Usage:
    python analysis/extract_assets.py /path/to/J-WALT-Brand-Film-Source-Pack.pdf

Writes:
    assets/portfolio/<id>.jpg     lossless-quality re-save of each crop
    analysis/pages/pNN.jpg        the native page rasters
    analysis/assets.json          machine-readable crop boxes + sizes
"""
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PREVIEW_W = 1200  # boxes below are in 1200x675 preview coordinates

# id: (page, (x0, y0, x1, y1) in preview coords)
BOXES = {
    "about-office":          (2,  (27, 67, 707, 522)),
    "heid-reception":        (5,  (40, 67, 636, 660)),
    "heid-boardroom":        (6,  (36, 91, 590, 643)),
    "heid-teamwork-joinery": (6,  (611, 91, 1163, 643)),
    "heid-corridor-glass":   (7,  (22, 87, 475, 651)),
    "heid-private-office":   (7,  (498, 87, 1168, 651)),
    "heid-curved-glass":     (8,  (25, 85, 483, 659)),
    "heid-stained-corridor": (8,  (503, 85, 1177, 663)),
    "corys-openplan-a":      (9,  (0, 103, 428, 639)),
    "corys-glass-a":         (9,  (436, 150, 765, 639)),
    "corys-glass-b":         (10, (50, 85, 613, 654)),
    "corys-openplan-b":      (10, (636, 85, 1167, 661)),
    "snoc-boardroom-render": (11, (0, 117, 835, 607)),
    "snoc-reception-render": (12, (113, 51, 796, 655)),
    "snoc-boardroom-built":  (13, (10, 115, 611, 675)),
    "snoc-shelving-built":   (13, (617, 115, 1200, 675)),
    "omoda-reception":       (14, (0, 97, 767, 633)),
    "omoda-workspace-a":     (15, (38, 100, 622, 655)),
    "omoda-workspace-b":     (15, (648, 97, 1188, 655)),
    "omoda-boardroom":       (16, (30, 64, 600, 662)),
    "omoda-workspace-c":     (16, (620, 64, 1143, 662)),
    "wilh-reception-render": (17, (10, 124, 757, 626)),
    "wilh-openplan-a":       (18, (0, 118, 722, 607)),
    "wilh-openplan-b":       (18, (740, 118, 1200, 607)),
    "heid2-hall":            (21, (12, 108, 435, 607)),
    "heid2-window":          (21, (453, 108, 824, 607)),
    "heid2-blinds":          (21, (842, 108, 1184, 607)),
}


def is_bg_line(line, bg, tol=10.0, flat=6.0):
    """A row/column is page background if it is flat and near the bg colour."""
    return (np.abs(line.mean(axis=0) - bg).max() < tol) and (line.std(axis=0).max() < flat)


def tighten(arr, box, bg, pad=14):
    h, w, _ = arr.shape
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    moved = True
    while moved and x1 - x0 > 40 and y1 - y0 > 40:
        moved = False
        if is_bg_line(arr[y0, x0:x1], bg): y0 += 1; moved = True
        if is_bg_line(arr[y1 - 1, x0:x1], bg): y1 -= 1; moved = True
        if is_bg_line(arr[y0:y1, x0], bg): x0 += 1; moved = True
        if is_bg_line(arr[y0:y1, x1 - 1], bg): x1 -= 1; moved = True
    # shave 3px to drop JPEG ringing / rounded-corner antialiasing
    return (x0 + 3, y0 + 3, x1 - 3, y1 - 3)


def main(pdf_path):
    doc = pymupdf.open(pdf_path)
    pages_dir = ROOT / "analysis" / "pages"
    out_dir = ROOT / "assets" / "portfolio"
    pages_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    rasters = {}
    for page in doc:
        xref = page.get_images()[0][0]
        data = doc.extract_image(xref)["image"]
        p = pages_dir / f"p{page.number + 1:02d}.jpg"
        p.write_bytes(data)  # byte-identical to what is embedded in the PDF
        rasters[page.number + 1] = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)

    records = {}
    for asset_id, (pg, pbox) in BOXES.items():
        arr = rasters[pg]
        scale = arr.shape[1] / PREVIEW_W
        box = tuple(int(round(v * scale)) for v in pbox)
        bg = np.median(arr[4:40, 4:40].reshape(-1, 3), axis=0)  # page corner
        tb = tighten(arr, box, bg)
        img = Image.fromarray(arr[tb[1]:tb[3], tb[0]:tb[2]].astype(np.uint8))
        dest = out_dir / f"{asset_id}.jpg"
        img.save(dest, quality=97, subsampling=0)
        records[asset_id] = {"page": pg, "box_native": tb, "width": img.width, "height": img.height,
                             "file": str(dest.relative_to(ROOT))}
        print(f"{asset_id:24s} p{pg:02d} {img.width}x{img.height}")

    (ROOT / "analysis" / "assets.json").write_text(json.dumps(records, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
