"""Export the model's edges for the vector wireframe layer.

'feature' objects contribute their crease/boundary edges (base mesh, before
bevels); 'outline' objects (upholstery, reeded panels, tiles) contribute a
clean oriented bounding box so the wireframe reads as precise massing, not
as a tessellated mesh."""
from __future__ import annotations

import math

import bpy
import numpy as np

_BOX_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]


def _feature_edges(me, angle_deg=30.0):
    me.calc_loop_triangles()
    fn = np.array([p.normal[:] for p in me.polygons]) if len(me.polygons) else np.zeros((0, 3))
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(len(vs)):
            a, b = vs[i], vs[(i + 1) % len(vs)]
            edge_faces.setdefault((min(a, b), max(a, b)), []).append(p.index)
    cos_t = math.cos(math.radians(angle_deg))
    out = []
    for (a, b), fs in edge_faces.items():
        if len(fs) == 1 or (len(fs) >= 2 and float(np.dot(fn[fs[0]], fn[fs[1]])) < cos_t):
            out.append((a, b))
    return out


def export(path: str) -> dict:
    segs, owner = [], []
    names, groups, layers = [], [], []
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH":
            continue
        mode = ob.get("jf_lines", "feature")
        if mode == "none":
            continue
        me = ob.data
        V = np.array([v.co[:] for v in me.vertices], dtype=np.float64)
        if len(V) == 0:
            continue
        M = np.array(ob.matrix_world)
        if mode == "outline":
            lo, hi = V.min(0), V.max(0)
            corners = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]], [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                                [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]])
            W = corners @ M[:3, :3].T + M[:3, 3]
            e = [(W[a], W[b]) for a, b in _BOX_EDGES]
        else:
            W = V @ M[:3, :3].T + M[:3, 3]
            e = [(W[a], W[b]) for a, b in _feature_edges(me)]
        if not e:
            continue
        k = len(names)
        names.append(ob.name)
        groups.append(ob.get("jf_group", ""))
        layers.append(ob.get("jf_layer", ""))
        segs.extend(e)
        owner.extend([k] * len(e))
    segs = np.array(segs, dtype=np.float32)
    owner = np.array(owner, dtype=np.int32)
    np.savez_compressed(path, segs=segs, owner=owner, names=np.array(names), groups=np.array(groups),
                        layers=np.array(layers))
    return {"segments": len(segs), "objects": len(names)}
