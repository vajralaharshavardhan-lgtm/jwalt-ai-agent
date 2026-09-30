"""Low-level mesh helpers. Geometry is authored in world metres; every object
is tagged with metadata (group, layer, state) that the renderer, the
exploded view and the linework exporter read back."""
from __future__ import annotations

import math

import bpy
import numpy as np

# --- collections / tagging ---------------------------------------------------

_colls: dict[str, bpy.types.Collection] = {}


def reset():
    _colls.clear()


def coll(name: str) -> bpy.types.Collection:
    c = _colls.get(name)
    if c is None or c.name not in bpy.data.collections:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        _colls[name] = c
    return c


def tag(ob, group: str, layer: str, lines: str = "feature", **extra):
    """group: construction state bucket; layer: exploded-view layer;
    lines: 'feature' | 'outline' | 'none' -- how the wireframe draws it."""
    ob["jf_group"] = group
    ob["jf_layer"] = layer
    ob["jf_lines"] = lines
    for k, v in extra.items():
        ob[f"jf_{k}"] = v
    return ob


def mesh_obj(name, verts, faces, group, layer, mat=None, smooth=False, sharp_angle=None,
             origin=None, lines="feature", collection=None):
    verts = np.asarray(verts, dtype=np.float64)
    if origin is not None:
        origin = np.asarray(origin, dtype=np.float64)
        verts = verts - origin
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], [list(f) for f in faces])
    me.validate(clean_customdata=False)
    me.update()
    if smooth:
        me.shade_smooth()
        if sharp_angle is not None:
            me.set_sharp_from_angle(angle=math.radians(sharp_angle))
    ob = bpy.data.objects.new(name, me)
    if origin is not None:
        ob.location = origin.tolist()
    coll(collection or group).objects.link(ob)
    if mat is not None:
        ob.data.materials.append(mat)
    return tag(ob, group, layer, lines)


def bevel(ob, width=0.003, segments=2, angle=35.0):
    m = ob.modifiers.new("bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.harden_normals = True
    m.use_clamp_overlap = True
    return m


def subsurf(ob, levels=2):
    m = ob.modifiers.new("subsurf", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    return m


# --- primitives --------------------------------------------------------------

_BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def box_verts(x0, x1, y0, y1, z0, z1):
    return [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]


def box(name, x0, x1, y0, y1, z0, z1, group, layer, mat=None, bevel_w=0.0, bevel_seg=2,
        origin="center", lines="feature", collection=None):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    if origin == "center":
        o = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    elif origin == "bottom":
        o = ((x0 + x1) / 2, (y0 + y1) / 2, z0)
    else:
        o = origin
    ob = mesh_obj(name, box_verts(x0, x1, y0, y1, z0, z1), _BOX_FACES, group, layer, mat,
                  origin=o, lines=lines, collection=collection)
    if bevel_w > 0:
        bevel(ob, bevel_w, bevel_seg)
    return ob


def _cluster(u):
    return 0.5 - 0.5 * np.cos(np.pi * u)


def rounded_box(name, center, size, radius, group, layer, mat=None, n=14, puff=0.0,
                puff_axis=2, lines="outline", collection=None):
    """Box with uniformly rounded edges (Minkowski of inner box + sphere),
    optional pillow 'puff' on the +puff_axis face. Good for upholstery."""
    half = np.asarray(size, dtype=np.float64) / 2
    r = float(min(radius, *(half * 0.999)))
    inner = half - r
    key = {}
    verts = []
    faces = []

    def vid(p):
        k = tuple(np.round(p, 7))
        if k not in key:
            key[k] = len(verts)
            verts.append(p)
        return key[k]

    us = _cluster(np.linspace(0, 1, n + 1)) * 2 - 1
    for axis in range(3):
        for sign in (-1, 1):
            a1, a2 = [i for i in range(3) if i != axis]
            grid = np.empty((n + 1, n + 1), dtype=np.int64)
            for i, u in enumerate(us):
                for j, v in enumerate(us):
                    p = np.zeros(3)
                    p[axis] = sign
                    p[a1] = u
                    p[a2] = v
                    grid[i, j] = vid(p)
            for i in range(n):
                for j in range(n):
                    q = [grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]]
                    # outward winding
                    nrm = np.zeros(3)
                    nrm[axis] = sign
                    pa, pb, pc = (np.array(verts[q[0]]), np.array(verts[q[1]]), np.array(verts[q[2]]))
                    if np.dot(np.cross(pb - pa, pc - pa), nrm) < 0:
                        q = q[::-1]
                    faces.append(q)
    P = np.array(verts) * half
    Q = np.clip(P, -inner, inner)
    D = P - Q
    L = np.linalg.norm(D, axis=1, keepdims=True)
    L[L < 1e-12] = 1
    P = Q + r * D / L
    if puff:
        ax = puff_axis
        others = [i for i in range(3) if i != ax]
        top = P[:, ax] > inner[ax] - 1e-9
        w = np.clip(1 - (P[:, others[0]] / half[others[0]]) ** 2, 0, 1) * np.clip(1 - (P[:, others[1]] / half[others[1]]) ** 2, 0, 1)
        P[top, ax] += puff * w[top] ** 0.8
    P = P + np.asarray(center)
    return mesh_obj(name, P, faces, group, layer, mat, smooth=True, origin=center, lines=lines,
                    collection=collection)


def cylinder(name, center, radius, height, group, layer, mat=None, segs=48, bevel_w=0.0,
             lines="outline", collection=None, axis="Z"):
    cx, cy, cz = center
    ang = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    ring = np.stack([np.cos(ang) * radius, np.sin(ang) * radius], 1)
    verts, faces = [], []
    for h in (0.0, height):
        for x, y in ring:
            verts.append((x, y, h))
    for i in range(segs):
        j = (i + 1) % segs
        faces.append((i, j, segs + j, segs + i))
    faces.append(tuple(reversed(range(segs))))
    faces.append(tuple(range(segs, 2 * segs)))
    V = np.array(verts, dtype=np.float64)
    if axis == "X":
        V = V[:, [2, 0, 1]]
    elif axis == "Y":
        V = V[:, [0, 2, 1]]
    V = V + np.array([cx, cy, cz])
    ob = mesh_obj(name, V, faces, group, layer, mat, smooth=True, sharp_angle=40,
                  origin=center, lines=lines, collection=collection)
    if bevel_w:
        bevel(ob, bevel_w, 3)
    return ob


def lathe(name, profile, center, group, layer, mat=None, segs=72, lines="outline", collection=None):
    """Revolve a (radius, z) profile around Z. Closed at the axis if r==0."""
    prof = np.asarray(profile, dtype=np.float64)
    ang = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    verts, faces = [], []
    m = len(prof)
    for a in ang:
        for r, z in prof:
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(segs):
        i2 = (i + 1) % segs
        for k in range(m - 1):
            faces.append((i * m + k, i2 * m + k, i2 * m + k + 1, i * m + k + 1))
    V = np.array(verts) + np.asarray(center)
    return mesh_obj(name, V, faces, group, layer, mat, smooth=True, sharp_angle=50,
                    origin=center, lines=lines, collection=collection)


def reeded_panel(name, x0, x1, z0, z1, y_face, group, layer, mat=None, pitch=0.03, depth=0.011,
                 thickness=0.018, facing=-1.0, segs=8, collection=None):
    """Vertical convex-reeded (fluted) panel on a wall facing -Y (facing=-1)
    or +Y. Solid: reeded front, flat back, closed ends."""
    n = max(1, int(round((x1 - x0) / pitch)))
    pitch = (x1 - x0) / n
    prof = []
    for k in range(n):
        xc = x0 + (k + 0.5) * pitch
        for s in range(segs + 1):
            if k > 0 and s == 0:
                continue
            th = math.pi * s / segs
            prof.append((xc - (pitch / 2) * math.cos(th), y_face + facing * depth * math.sin(th) ** 0.85))
    yb = y_face - facing * thickness
    m = len(prof)
    verts = [(x, y, z0) for x, y in prof] + [(x, y, z1) for x, y in prof]
    faces = []
    for i in range(m - 1):
        f = (i, i + 1, m + i + 1, m + i)
        faces.append(f if facing < 0 else f[::-1])
    b = len(verts)
    verts += [(x1, yb, z0), (x0, yb, z0), (x1, yb, z1), (x0, yb, z1)]
    back = (b, b + 1, b + 3, b + 2)
    faces.append(back if facing < 0 else back[::-1])
    bottom = [b + 1] + list(range(m)) + [b]
    top = [b + 3] + list(range(m, 2 * m)) + [b + 2]
    faces.append(tuple(bottom) if facing < 0 else tuple(reversed(bottom)))
    faces.append(tuple(reversed(top)) if facing < 0 else tuple(top))
    left = (0, b + 1, b + 3, m)
    right = (m - 1, 2 * m - 1, b + 2, b)
    faces.append(left if facing < 0 else left[::-1])
    faces.append(right if facing < 0 else right[::-1])
    ob = mesh_obj(name, verts, faces, group, layer, mat, smooth=True, sharp_angle=50,
                  origin=((x0 + x1) / 2, y_face, (z0 + z1) / 2), lines="outline", collection=collection)
    return ob


def pleated_sheet(name, x_plane, y0, y1, z0, z1, group, layer, mat=None, pleat=0.11, amp=0.045,
                  seed=0, collection=None):
    """Sheer curtain: vertical sinusoidal pleats with gentle irregularity."""
    rng = np.random.default_rng(seed)
    ny = max(8, int((y1 - y0) / (pleat / 10)))
    nz = 24
    ys = np.linspace(y0, y1, ny + 1)
    zs = np.linspace(z0, z1, nz + 1)
    phase = rng.uniform(0, 2 * np.pi)
    jitter = rng.normal(0, 0.12, size=8)
    verts = []
    for z in zs:
        hz = (z - z0) / max(z1 - z0, 1e-6)
        for y in ys:
            u = (y - y0) / pleat * 2 * np.pi + phase
            a = amp * (0.85 + 0.15 * hz) * (1 + 0.25 * math.sin(u * 0.13 + jitter[0]))
            x = x_plane + a * math.sin(u + 0.35 * math.sin(u * 0.5 + jitter[1]))
            x += 0.01 * math.sin(hz * 3.1 + y * 1.7 + jitter[2]) * (1 - hz)
            verts.append((x, y, z))
    faces = []
    W = ny + 1
    for j in range(nz):
        for i in range(ny):
            faces.append((j * W + i, j * W + i + 1, (j + 1) * W + i + 1, (j + 1) * W + i))
    return mesh_obj(name, verts, faces, group, layer, mat, smooth=True,
                    origin=(x_plane, (y0 + y1) / 2, (z0 + z1) / 2), lines="outline", collection=collection)


def plane_xy(name, x0, x1, y0, y1, z, group, layer, mat=None, flip=False, lines="outline", collection=None):
    v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    f = [(0, 1, 2, 3)] if not flip else [(3, 2, 1, 0)]
    return mesh_obj(name, v, f, group, layer, mat, origin=((x0 + x1) / 2, (y0 + y1) / 2, z),
                    lines=lines, collection=collection)
