"""EXR I/O + the display transform (Blender's own AgX via OCIO), so a still
looks identical here and in Blender."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import OpenEXR


def read(path: str | Path) -> dict[str, np.ndarray]:
    """Multilayer EXR -> {layer: (H,W,C) float32}. RGBA layers keep 4 channels;
    vectors (position.X/Y/Z) are stacked; scalars are (H,W)."""
    f = OpenEXR.File(str(path))
    ch = f.channels()
    out: dict[str, np.ndarray] = {}
    vec: dict[str, dict[str, np.ndarray]] = {}
    for name, c in ch.items():
        px = np.asarray(c.pixels, dtype=np.float32)
        if px.ndim == 3:
            out[name] = px
        elif "." in name:
            layer, comp = name.rsplit(".", 1)
            vec.setdefault(layer, {})[comp] = px
        else:
            out[name] = px
    for layer, comps in vec.items():
        keys = sorted(comps.keys(), key=lambda k: "XYZWRGBAV".find(k) if k in "XYZWRGBAV" else 99)
        arr = np.stack([comps[k] for k in keys], axis=-1)
        out[layer] = arr[..., 0] if arr.shape[-1] == 1 else arr
    return out


def write_rgb(path: str | Path, rgb: np.ndarray):
    rgb = np.ascontiguousarray(rgb[..., :3].astype(np.float32))
    header = {"compression": OpenEXR.ZIP_COMPRESSION, "type": OpenEXR.scanlineimage}
    with OpenEXR.File(header, {"RGB": rgb}) as f:
        f.write(str(path))


def write_layers(path: str | Path, layers: dict[str, np.ndarray]):
    chans = {k: np.ascontiguousarray(v.astype(np.float32)) for k, v in layers.items()}
    header = {"compression": OpenEXR.ZIP_COMPRESSION, "type": OpenEXR.scanlineimage}
    with OpenEXR.File(header, chans) as f:
        f.write(str(path))


def _ocio_config_path() -> str:
    import importlib.util
    spec = importlib.util.find_spec("bpy")
    base = Path(spec.origin).parent if spec and spec.origin else None
    cands = []
    if base:
        cands += list(base.glob("*/datafiles/colormanagement/config.ocio"))
    env = os.environ.get("OCIO")
    if env:
        cands.insert(0, Path(env))
    for c in cands:
        if Path(c).exists():
            return str(c)
    raise FileNotFoundError("Blender OCIO config not found (install the `bpy` wheel)")


@lru_cache(maxsize=8)
def _processor(look: str, view: str = "AgX"):
    import PyOpenColorIO as ocio
    cfg = ocio.Config.CreateFromFile(_ocio_config_path())
    t = ocio.DisplayViewTransform()
    t.setSrc("Linear Rec.709")
    t.setDisplay("sRGB")
    t.setView(view)
    if look:
        vt = ocio.LookTransform()
        vt.setSrc("Linear Rec.709")
        vt.setDst("Linear Rec.709")
        vt.setLooks(look)
        grp = ocio.GroupTransform()
        grp.appendTransform(vt)
        grp.appendTransform(t)
        return cfg.getProcessor(grp).getDefaultCPUProcessor()
    return cfg.getProcessor(t).getDefaultCPUProcessor()


def display(rgb_linear: np.ndarray, look: str = "", view: str = "AgX", exposure: float = 0.0) -> np.ndarray:
    """Scene-linear Rec.709 -> display sRGB (0..1 float) via Blender's AgX."""
    img = np.ascontiguousarray(rgb_linear[..., :3], dtype=np.float32) * np.float32(2.0 ** exposure)
    img = np.ascontiguousarray(img)
    proc = _processor(look, view)
    proc.applyRGB(img)
    return np.clip(img, 0.0, 1.0)


def save_png(path, img01: np.ndarray, bits: int = 8):
    import cv2
    a = np.clip(img01[..., :3], 0, 1)
    if bits == 16:
        cv2.imwrite(str(path), (a[..., ::-1] * 65535 + 0.5).astype(np.uint16))
    else:
        cv2.imwrite(str(path), (a[..., ::-1] * 255 + 0.5).astype(np.uint8))
