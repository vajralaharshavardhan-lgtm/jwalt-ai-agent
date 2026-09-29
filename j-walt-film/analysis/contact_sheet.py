"""Contact sheet + objective quality metrics for extracted portfolio crops.

Sharpness is the variance of a 3x3 Laplacian measured at a common 800px
height, so images of different native sizes are comparable. `upscale_1080`
is how much the crop must be enlarged to fill a 1080-line frame height.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def sharpness(img):
    g = np.asarray(img.convert("L").resize((round(img.width * 800 / img.height), 800),
                                           Image.LANCZOS), dtype=np.float32)
    lap = (-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])
    return float(lap.var())


def main():
    recs = json.loads((ROOT / "analysis" / "assets.json").read_text())
    metrics = {}
    thumbs = []
    for aid, r in recs.items():
        img = Image.open(ROOT / r["file"]).convert("RGB")
        m = {"sharpness": round(sharpness(img), 1),
             "upscale_1080": round(1080 / img.height, 2),
             "upscale_1920w": round(1920 / img.width, 2),
             "aspect": round(img.width / img.height, 3)}
        metrics[aid] = m
        t = img.copy()
        t.thumbnail((360, 300), Image.LANCZOS)
        thumbs.append((aid, r, m, t))

    cols, cw, ch = 5, 380, 350
    rows = -(-len(thumbs) // cols)
    sheet = Image.new("RGB", (cols * cw + 20, rows * ch + 20), (246, 245, 242))
    d = ImageDraw.Draw(sheet)
    f1, f2 = ImageFont.truetype(FONT, 15), ImageFont.truetype(FONT, 12)
    for i, (aid, r, m, t) in enumerate(thumbs):
        x, y = 20 + (i % cols) * cw, 20 + (i // cols) * ch
        sheet.paste(t, (x, y))
        d.text((x, y + t.height + 6), f"{aid}", fill=(20, 20, 20), font=f1)
        d.text((x, y + t.height + 26),
               f"p{r['page']:02d}  {r['width']}x{r['height']}  sharp {m['sharpness']:.0f}  x{m['upscale_1080']} to 1080",
               fill=(110, 110, 110), font=f2)
    out = ROOT / "analysis" / "contact" / "contact_sheet.jpg"
    sheet.save(out, quality=90)
    (ROOT / "analysis" / "metrics.json").write_text(json.dumps(metrics, indent=2))
    for aid, m in sorted(metrics.items(), key=lambda kv: -kv[1]["sharpness"]):
        print(f"{aid:24s} sharp {m['sharpness']:7.1f}  up1080 x{m['upscale_1080']}  aspect {m['aspect']}")


if __name__ == "__main__":
    main()
