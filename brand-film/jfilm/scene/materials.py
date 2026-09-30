"""Procedural PBR material library (no external textures -> no licensing).

All colours are scene-linear. Each material carries natural variation
(per-object random offsets, roughness breakup, micro bump) because perfect
uniform CG surfaces are what make renders read as 'computer generated'."""
from __future__ import annotations

import bpy


def _c(v):
    v = tuple(float(x) for x in v)
    return v + (1.0,) if len(v) == 3 else v


class NB:
    """Tiny node-graph builder."""

    def __init__(self, mat: bpy.types.Material):
        mat.use_nodes = True
        self.nt = mat.node_tree
        for n in list(self.nt.nodes):
            self.nt.nodes.remove(n)
        self.output = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.output.target = "ALL"

    def _in(self, n, key):
        if isinstance(key, int):
            return n.inputs[key]
        for s in n.inputs:
            if s.identifier == key:
                return s
        cands = [s for s in n.inputs if s.name == key and s.enabled] or [s for s in n.inputs if s.name == key]
        if not cands:
            raise KeyError(f"{n.bl_idname} has no input {key!r}")
        return cands[0]

    def out(self, n, key=0):
        if isinstance(key, int):
            outs = [s for s in n.outputs if s.enabled]
            return outs[key]
        for s in n.outputs:
            if s.identifier == key:
                return s
        cands = [s for s in n.outputs if s.name == key and s.enabled] or [s for s in n.outputs if s.name == key]
        return cands[0]

    def node(self, typ, inputs=None, **props):
        n = self.nt.nodes.new(typ)
        for k, v in props.items():
            setattr(n, k, v)
        for k, v in (inputs or {}).items():
            s = self._in(n, k)
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, s)
            else:
                if s.type == "RGBA":
                    v = _c(v)
                s.default_value = v
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    # --- common patterns ---
    def coords(self, kind="Object", randomize=True, scale=(1, 1, 1)):
        tc = self.node("ShaderNodeTexCoord")
        v = self.out(tc, kind)
        if randomize:
            oi = self.node("ShaderNodeObjectInfo")
            off = self.node("ShaderNodeVectorMath", {0: self.out(oi, "Random"), 1: (37.13, 53.71, 11.29)},
                            operation="MULTIPLY")
            v = self.out(self.node("ShaderNodeVectorMath", {0: v, 1: self.out(off, 0)}, operation="ADD"), 0)
        if tuple(scale) != (1, 1, 1):
            v = self.out(self.node("ShaderNodeMapping", {"Vector": v, "Scale": scale}), 0)
        return v

    def noise(self, vec, scale, detail=4.0, rough=0.5, distortion=0.0, out="Fac"):
        n = self.node("ShaderNodeTexNoise", {"Vector": vec, "Scale": scale, "Detail": detail,
                                             "Roughness": rough, "Distortion": distortion})
        return self.out(n, out)

    def voronoi(self, vec, scale, feature="F1", out="Distance", randomness=1.0):
        n = self.node("ShaderNodeTexVoronoi", {"Vector": vec, "Scale": scale, "Randomness": randomness},
                      feature=feature)
        return self.out(n, out)

    def wave(self, vec, scale, distortion=0.0, detail=2.0, detail_scale=1.0, direction="X", kind="BANDS",
             profile="SIN", out="Fac"):
        n = self.node("ShaderNodeTexWave", {"Vector": vec, "Scale": scale, "Distortion": distortion,
                                            "Detail": detail, "Detail Scale": detail_scale},
                      wave_type=kind, bands_direction=direction, rings_direction="Z" if direction == "Z" else "X",
                      wave_profile=profile)
        return self.out(n, out)

    def ramp(self, fac, stops, interp="LINEAR"):
        n = self.node("ShaderNodeValToRGB", {"Fac": fac})
        cr = n.color_ramp
        cr.interpolation = interp
        els = cr.elements
        while len(els) > 2:
            els.remove(els[-1])
        for i, (pos, col) in enumerate(stops):
            e = els[i] if i < len(els) else els.new(pos)
            e.position = pos
            e.color = _c(col) if not isinstance(col, (int, float)) else (col, col, col, 1.0)
        return self.out(n, "Color")

    def mixc(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        for key, val in (("Factor_Float", fac), ("A_Color", a), ("B_Color", b)):
            s = self._in(n, key)
            if isinstance(val, bpy.types.NodeSocket):
                self.link(val, s)
            else:
                s.default_value = _c(val) if s.type == "RGBA" else val
        return self.out(n, "Result_Color")

    def math(self, op, a, b=0.0, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.link(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return self.out(n, 0)

    def maprange(self, v, a, b, c, d, clamp=True):
        n = self.node("ShaderNodeMapRange", {"Value": v, "From Min": a, "From Max": b, "To Min": c, "To Max": d},
                      clamp=clamp)
        return self.out(n, "Result")

    def bump(self, height, strength=0.1, distance=0.001, normal=None):
        ins = {"Height": height, "Strength": strength, "Distance": distance}
        if normal is not None:
            ins["Normal"] = normal
        return self.out(self.node("ShaderNodeBump", ins), "Normal")

    def principled(self, **ins):
        mapping = {"base": "Base Color", "rough": "Roughness", "metal": "Metallic", "normal": "Normal",
                   "ior": "IOR", "spec": "Specular IOR Level", "trans": "Transmission Weight",
                   "sheen": "Sheen Weight", "sheen_rough": "Sheen Roughness", "sheen_tint": "Sheen Tint",
                   "coat": "Coat Weight", "coat_rough": "Coat Roughness", "alpha": "Alpha",
                   "emit": "Emission Color", "emit_strength": "Emission Strength",
                   "aniso": "Anisotropic", "sss": "Subsurface Weight", "sss_radius": "Subsurface Radius"}
        n = self.node("ShaderNodeBsdfPrincipled", {mapping.get(k, k): v for k, v in ins.items()})
        n.distribution = "GGX"   # cheaper than multiscatter on CPU, visually identical here
        return n

    def surface(self, shader_node_or_socket, simple=None):
        """Connect the material output. `simple` = dict(base, rough, metal, ...)
        gives a flat stand-in used for every non-camera ray (GI bounces,
        blurry reflections): same average albedo, a fraction of the cost."""
        s = shader_node_or_socket
        if not isinstance(s, bpy.types.NodeSocket):
            s = self.out(s, 0)
        if simple is not None:
            lp = self.node("ShaderNodeLightPath")
            flat = self.principled(**simple)
            mix = self.node("ShaderNodeMixShader", {0: self.out(lp, "Is Camera Ray"), 1: self.out(flat, 0), 2: s})
            s = self.out(mix, 0)
        self.link(s, self.output.inputs["Surface"])


# ---------------------------------------------------------------------------
_cache: dict[str, bpy.types.Material] = {}


def reset():
    _cache.clear()


def _new(name):
    m = bpy.data.materials.new(name)
    return m, NB(m)


def get(name: str, **kw) -> bpy.types.Material:
    key = name + ("" if not kw else "|" + ",".join(f"{k}={v}" for k, v in sorted(kw.items())))
    if key not in _cache or _cache[key].name not in bpy.data.materials:
        fn = globals()[f"_mat_{name}"]
        m = fn(key, **kw)
        m.diffuse_color = _c(kw.get("preview", (0.8, 0.8, 0.8)))
        _cache[key] = m
    return _cache[key]


# --- stone -------------------------------------------------------------------

def _mat_limestone(name, tone=1.0):
    """Honed warm limestone floor: soft cloudy variation, fossil flecks,
    faint veining, per-tile tone shift, broken-up honed sheen."""
    m, b = _new(name)
    v = b.coords(scale=(1, 1, 1))
    oi = b.node("ShaderNodeObjectInfo")
    cloud = b.noise(v, 0.85, 5.0, 0.55)
    base = b.ramp(cloud, [(0.30, (0.47 * tone, 0.395 * tone, 0.30 * tone)), (0.72, (0.60 * tone, 0.515 * tone, 0.405 * tone))])
    fine = b.noise(v, 11.0, 5.0, 0.62)
    base = b.mixc(b.maprange(fine, 0.3, 0.7, 0.0, 0.10), base, (0.40, 0.33, 0.25), "MULTIPLY")
    vein = b.wave(v, 0.9, distortion=9.0, detail=6.0, detail_scale=1.4, direction="DIAGONAL")
    veinmask = b.maprange(vein, 0.46, 0.5, 0.0, 1.0)
    veinmask = b.math("MULTIPLY", b.math("SUBTRACT", 1.0, veinmask), b.maprange(vein, 0.5, 0.54, 1.0, 0.0))
    base = b.mixc(b.math("MULTIPLY", veinmask, 0.22), base, (0.66, 0.58, 0.47))
    fleck = b.voronoi(v, 70.0)
    fleckmask = b.maprange(fleck, 0.02, 0.07, 0.45, 0.0)
    base = b.mixc(fleckmask, base, (0.33, 0.27, 0.20))
    tile_tone = b.maprange(b.out(oi, "Random"), 0.0, 1.0, 0.93, 1.05)
    base = b.mixc(1.0, base, b.out(b.node("ShaderNodeCombineColor", {"Red": tile_tone, "Green": tile_tone, "Blue": tile_tone}), 0), "MULTIPLY")
    rough = b.maprange(b.noise(v, 3.0, 5.0, 0.6), 0.3, 0.7, 0.26, 0.42)
    rough = b.math("ADD", rough, b.math("MULTIPLY", fleckmask, 0.3))
    nrm = b.bump(b.noise(v, 45.0, 5.0, 0.7), 0.035, 0.001)
    b.surface(b.principled(base=base, rough=rough, normal=nrm, spec=0.55),
              simple=dict(base=(0.53 * tone, 0.455 * tone, 0.355 * tone), rough=0.34, spec=0.55))
    return m


def _mat_travertine(name, tone=1.0, vertical=False):
    """Vein-cut travertine: layered bands, open pores, soft honed sheen."""
    m, b = _new(name)
    v = b.coords(scale=(1.0, 1.0, 1.0) if not vertical else (1.0, 1.0, 1.0))
    bv = b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": (0.25, 0.25, 1.0) if not vertical else (1.0, 1.0, 0.25)}), 0)
    band = b.wave(bv, 5.5, distortion=1.6, detail=4.0, detail_scale=2.5, direction="Z" if not vertical else "X")
    band2 = b.wave(bv, 17.0, distortion=1.1, detail=2.0, detail_scale=3.0, direction="Z" if not vertical else "X")
    band = b.math("ADD", b.math("MULTIPLY", band, 0.7), b.math("MULTIPLY", band2, 0.3))
    base = b.ramp(band, [(0.2, (0.50 * tone, 0.41 * tone, 0.30 * tone)), (0.55, (0.60 * tone, 0.51 * tone, 0.38 * tone)),
                         (0.85, (0.55 * tone, 0.46 * tone, 0.34 * tone))])
    mott = b.noise(v, 6.0, 5.0, 0.6)
    base = b.mixc(b.maprange(mott, 0.35, 0.65, 0.0, 0.14), base, (0.36, 0.28, 0.19), "MULTIPLY")
    pv = b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": (7.0, 7.0, 34.0) if not vertical else (34.0, 34.0, 7.0)}), 0)
    pore = b.noise(pv, 1.0, 5.0, 0.7)
    poremask = b.maprange(pore, 0.62, 0.70, 0.0, 1.0)
    base = b.mixc(b.math("MULTIPLY", poremask, 0.75), base, (0.20, 0.15, 0.10))
    rough = b.math("ADD", b.maprange(mott, 0.3, 0.7, 0.36, 0.48), b.math("MULTIPLY", poremask, 0.4))
    h = b.math("SUBTRACT", b.math("MULTIPLY", b.noise(v, 40.0, 5.0, 0.6), 0.2), b.math("MULTIPLY", poremask, 1.0))
    b.surface(b.principled(base=base, rough=rough, normal=b.bump(h, 0.12, 0.0015), spec=0.5),
              simple=dict(base=(0.55 * tone, 0.46 * tone, 0.34 * tone), rough=0.45))
    return m


# --- wood --------------------------------------------------------------------

def _mat_oak(name, axis="Z", tone=1.0):
    """Smoked oak, oiled satin. Grain runs along `axis`: broad straight-grain
    banding, fine low-contrast grain lines, sparse pores, soft sheen."""
    m, b = _new(name)
    along = {"X": 0, "Y": 1, "Z": 2}[axis]

    def stretch(across, along_s):
        sc = [across, across, across]
        sc[along] = along_s
        return tuple(sc)

    across_dir = {"X": "Y", "Y": "X", "Z": "X"}[axis]
    v = b.coords()
    band = b.wave(b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": stretch(1.0, 0.08)}), 0), 3.2, distortion=2.2,
                  detail=2.0, detail_scale=0.8, direction=across_dir)
    fine = b.noise(b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": stretch(70, 1.4)}), 0), 1.0, 3.0, 0.5)
    g = b.math("ADD", b.math("MULTIPLY", band, 0.72), b.math("MULTIPLY", fine, 0.28))
    base = b.ramp(g, [(0.25, (0.072 * tone, 0.041 * tone, 0.022 * tone)), (0.55, (0.105 * tone, 0.062 * tone, 0.034 * tone)),
                      (0.85, (0.142 * tone, 0.088 * tone, 0.050 * tone))])
    pore = b.maprange(b.noise(b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": stretch(260, 7)}), 0), 1.0, 3.0, 0.6),
                      0.66, 0.74, 0.0, 1.0)
    base = b.mixc(b.math("MULTIPLY", pore, 0.35), base, (0.035, 0.02, 0.011))
    rough = b.math("ADD", b.maprange(band, 0.3, 0.7, 0.40, 0.50), b.math("MULTIPLY", pore, 0.15))
    nrm = b.bump(b.math("SUBTRACT", b.math("MULTIPLY", fine, 0.15), b.math("MULTIPLY", pore, 0.6)), 0.05, 0.0005)
    b.surface(b.principled(base=base, rough=rough, normal=nrm, spec=0.45, coat=0.12, coat_rough=0.3),
              simple=dict(base=(0.10 * tone, 0.058 * tone, 0.032 * tone), rough=0.5))
    return m


# --- metals ------------------------------------------------------------------

def _mat_bronze(name, dark=1.0):
    m, b = _new(name)
    v = b.coords()
    sv = b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": (400, 400, 3)}), 0)
    brush = b.noise(sv, 1.0, 3.0, 0.5)
    base = b.ramp(b.noise(v, 4.0, 4.0, 0.5), [(0.3, (0.30 * dark, 0.20 * dark, 0.12 * dark)), (0.7, (0.38 * dark, 0.26 * dark, 0.16 * dark))])
    rough = b.maprange(brush, 0.3, 0.7, 0.24, 0.36)
    b.surface(b.principled(base=base, metal=1.0, rough=rough, normal=b.bump(brush, 0.02, 0.0003)),
              simple=dict(base=(0.34 * dark, 0.23 * dark, 0.14 * dark), metal=1.0, rough=0.3))
    return m


def _mat_galvanised(name):
    m, b = _new(name)
    v = b.coords()
    cells = b.voronoi(v, 16.0, feature="F1", out="Color")
    cellv = b.out(b.node("ShaderNodeSeparateColor", {"Color": cells}), 0)
    base = b.ramp(cellv, [(0.0, (0.46, 0.47, 0.48)), (1.0, (0.62, 0.63, 0.64))])
    rough = b.maprange(cellv, 0.0, 1.0, 0.22, 0.46)
    smudge = b.noise(v, 2.0, 5.0, 0.6)
    rough = b.math("ADD", rough, b.maprange(smudge, 0.5, 0.8, 0.0, 0.15))
    b.surface(b.principled(base=base, metal=1.0, rough=rough), simple=dict(base=(0.55, 0.56, 0.57), metal=1.0, rough=0.34))
    return m


def _mat_black_metal(name, rough=0.42):
    m, b = _new(name)
    v = b.coords()
    r = b.maprange(b.noise(v, 8.0, 4.0, 0.5), 0.3, 0.7, rough - 0.06, rough + 0.06)
    b.surface(b.principled(base=(0.018, 0.017, 0.016), metal=0.6, rough=r))
    return m


def _mat_steel_dark(name):
    m, b = _new(name)
    b.surface(b.principled(base=(0.05, 0.05, 0.05), metal=1.0, rough=0.35))
    return m


# --- paint, plaster, board, concrete ----------------------------------------

def _mat_paint(name, col=(0.66, 0.635, 0.59)):
    m, b = _new(name)
    v = b.coords(randomize=False)
    mott = b.noise(v, 1.2, 4.0, 0.5)
    base = b.mixc(b.maprange(mott, 0.3, 0.7, 0.0, 0.05), col, (0.5, 0.48, 0.44), "MULTIPLY")
    b.surface(b.principled(base=base, rough=0.86, normal=b.bump(b.noise(v, 260.0, 3.0, 0.5), 0.03, 0.0003), spec=0.35),
              simple=dict(base=col, rough=0.86, spec=0.35))
    return m


def _mat_plaster_raw(name):
    m, b = _new(name)
    v = b.coords(randomize=False)
    mott = b.noise(v, 1.6, 5.0, 0.62)
    base = b.ramp(mott, [(0.3, (0.24, 0.235, 0.22)), (0.7, (0.34, 0.33, 0.31))])
    trow = b.wave(v, 1.3, distortion=4.0, detail=2.0, direction="DIAGONAL")
    base = b.mixc(b.maprange(trow, 0.4, 0.6, 0.0, 0.08), base, (0.45, 0.44, 0.41))
    b.surface(b.principled(base=base, rough=0.9, normal=b.bump(b.noise(v, 30.0, 5.0, 0.6), 0.12, 0.001)),
              simple=dict(base=(0.29, 0.28, 0.265), rough=0.9))
    return m


def _mat_concrete(name, tone=1.0):
    m, b = _new(name)
    v = b.coords()
    mott = b.noise(v, 2.4, 5.0, 0.62)
    base = b.ramp(mott, [(0.25, (0.20 * tone, 0.195 * tone, 0.185 * tone)), (0.75, (0.33 * tone, 0.322 * tone, 0.305 * tone))])
    stain = b.maprange(b.noise(v, 0.45, 3.0, 0.5), 0.55, 0.75, 0.0, 0.28)
    base = b.mixc(stain, base, (0.12, 0.115, 0.105))
    pores = b.maprange(b.voronoi(v, 140.0), 0.0, 0.08, 1.0, 0.0)
    base = b.mixc(b.math("MULTIPLY", pores, 0.5), base, (0.10, 0.10, 0.095))
    rough = b.maprange(mott, 0.3, 0.7, 0.78, 0.92)
    h = b.math("SUBTRACT", b.noise(v, 18.0, 5.0, 0.65), b.math("MULTIPLY", pores, 0.8))
    b.surface(b.principled(base=base, rough=rough, normal=b.bump(h, 0.22, 0.002)),
              simple=dict(base=(0.25 * tone, 0.245 * tone, 0.232 * tone), rough=0.85))
    return m


def _mat_screed(name):
    m, b = _new(name)
    v = b.coords(randomize=False)
    mott = b.noise(v, 1.1, 5.0, 0.6)
    base = b.ramp(mott, [(0.3, (0.285, 0.27, 0.25)), (0.7, (0.37, 0.355, 0.33))])
    swirl = b.wave(v, 3.5, distortion=3.0, detail=2.0, kind="RINGS")
    rough = b.math("ADD", b.maprange(mott, 0.3, 0.7, 0.62, 0.8), b.maprange(swirl, 0.3, 0.7, -0.06, 0.06))
    b.surface(b.principled(base=base, rough=rough, normal=b.bump(b.noise(v, 60.0, 5.0, 0.6), 0.06, 0.0006)),
              simple=dict(base=(0.33, 0.315, 0.29), rough=0.7))
    return m


def _mat_gypsum_board(name):
    """Fresh plasterboard sheet with taped/filled joints near its edges."""
    m, b = _new(name)
    v = b.coords(randomize=False)
    gen = b.out(b.node("ShaderNodeTexCoord"), "Generated")
    sep = b.node("ShaderNodeSeparateXYZ", {"Vector": gen})
    edge = None
    for comp in ("X", "Y", "Z"):
        c = b.out(sep, comp)
        d = b.math("MINIMUM", c, b.math("SUBTRACT", 1.0, c))
        e = b.maprange(d, 0.0, 0.035, 1.0, 0.0)
        edge = e if edge is None else b.math("MAXIMUM", edge, e)
    paper = b.noise(v, 3.0, 5.0, 0.55)
    base = b.ramp(paper, [(0.3, (0.60, 0.595, 0.57)), (0.7, (0.66, 0.655, 0.63))])
    feather = b.maprange(b.noise(v, 22.0, 4.0, 0.6), 0.3, 0.7, 0.6, 1.0)
    base = b.mixc(b.math("MULTIPLY", edge, feather), base, (0.74, 0.735, 0.71))
    b.surface(b.principled(base=base, rough=0.88, normal=b.bump(b.noise(v, 90.0, 3.0, 0.5), 0.03, 0.0004)),
              simple=dict(base=(0.64, 0.635, 0.61), rough=0.88))
    return m


def _mat_red_pipe(name):
    m, b = _new(name)
    v = b.coords()
    b.surface(b.principled(base=(0.30, 0.018, 0.012), rough=b.maprange(b.noise(v, 6.0, 4.0, 0.5), 0.3, 0.7, 0.32, 0.5)))
    return m


def _mat_cable(name, col=(0.02, 0.02, 0.022)):
    m, b = _new(name)
    b.surface(b.principled(base=col, rough=0.55))
    return m


# --- soft goods -------------------------------------------------------------

def _mat_boucle(name, col=(0.60, 0.56, 0.49)):
    m, b = _new(name)
    v = b.coords()
    loops = b.voronoi(v, 230.0, feature="SMOOTH_F1")
    fuzz = b.noise(v, 520.0, 3.0, 0.6)
    h = b.math("ADD", b.math("MULTIPLY", loops, 0.7), b.math("MULTIPLY", fuzz, 0.3))
    base = b.mixc(b.maprange(loops, 0.0, 0.4, 0.12, 0.0), col, (0.30, 0.27, 0.22), "MULTIPLY")
    b.surface(b.principled(base=base, rough=0.95, sheen=0.9, sheen_rough=0.45, sheen_tint=(1, 0.97, 0.92),
                           normal=b.bump(h, 0.45, 0.0025), spec=0.3),
              simple=dict(base=col, rough=0.95, sheen=0.9))
    return m


def _mat_velvet(name, col=(0.19, 0.11, 0.06)):
    m, b = _new(name)
    v = b.coords()
    crush = b.noise(v, 6.0, 5.0, 0.6)
    base = b.mixc(b.maprange(crush, 0.3, 0.7, 0.0, 0.25), col, (0.5, 0.45, 0.4), "MULTIPLY")
    b.surface(b.principled(base=base, rough=0.9, sheen=1.0, sheen_rough=0.35, sheen_tint=(1.0, 0.88, 0.74),
                           normal=b.bump(b.noise(v, 300.0, 3.0, 0.6), 0.12, 0.0008), spec=0.3),
              simple=dict(base=col, rough=0.9, sheen=1.0))
    return m


def _mat_rug(name, col=(0.36, 0.325, 0.28)):
    m, b = _new(name)
    v = b.coords(randomize=False)
    stripe = b.wave(v, 5.0, distortion=0.6, detail=1.0, direction="X")
    base = b.mixc(b.maprange(stripe, 0.2, 0.8, 0.0, 0.10), col, (0.52, 0.48, 0.42))
    fib = b.noise(v, 480.0, 4.0, 0.7)
    base = b.mixc(b.maprange(fib, 0.3, 0.7, 0.0, 0.16), base, (0.2, 0.18, 0.15), "MULTIPLY")
    b.surface(b.principled(base=base, rough=1.0, sheen=0.6, sheen_rough=0.5, normal=b.bump(fib, 0.5, 0.003), spec=0.2),
              simple=dict(base=col, rough=1.0))
    return m


def _mat_sheer(name):
    """Linen sheer: diffusing, softly translucent, weave-modulated openness."""
    m, b = _new(name)
    v = b.coords(randomize=False)
    weave = b.wave(b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": (1, 1, 1)}), 0), 900.0, detail=0.0, direction="Z")
    slub = b.noise(b.out(b.node("ShaderNodeMapping", {"Vector": v, "Scale": (60, 60, 2)}), 0), 1.0, 3.0, 0.5)
    openness = b.math("ADD", 0.32, b.math("MULTIPLY", b.math("ADD", weave, slub), 0.08))
    tr = b.node("ShaderNodeBsdfTransparent", {"Color": (0.98, 0.97, 0.95)})
    tl = b.node("ShaderNodeBsdfTranslucent", {"Color": (0.86, 0.82, 0.74)})
    df = b.node("ShaderNodeBsdfDiffuse", {"Color": (0.80, 0.77, 0.70)})
    cloth = b.node("ShaderNodeMixShader", {0: 0.55, 1: b.out(df, 0), 2: b.out(tl, 0)})
    mix = b.node("ShaderNodeMixShader", {0: openness, 1: b.out(cloth, 0), 2: b.out(tr, 0)})
    b.surface(mix)
    m.blend_method = "HASHED" if hasattr(m, "blend_method") else None
    return m


# --- glass, ceramic, emission -------------------------------------------------

def _mat_glass(name, tint=(0.94, 0.975, 0.965)):
    """Architectural glass. Shadow and diffuse rays see a thin transparent
    pane (so sun and skylight enter the room); camera/glossy rays see real
    dielectric glass with reflections."""
    m, b = _new(name)
    glass = b.principled(base=tint, trans=1.0, rough=0.0, ior=1.52)
    thin = b.node("ShaderNodeBsdfTransparent", {"Color": (0.90, 0.93, 0.92)})
    lp = b.node("ShaderNodeLightPath")
    fac = b.math("MAXIMUM", b.out(lp, "Is Shadow Ray"), b.out(lp, "Is Diffuse Ray"))
    b.surface(b.node("ShaderNodeMixShader", {0: fac, 1: b.out(glass, 0), 2: b.out(thin, 0)}))
    return m


def _mat_ceramic(name, col=(0.05, 0.046, 0.042), rough=0.55):
    m, b = _new(name)
    v = b.coords()
    speck = b.maprange(b.voronoi(v, 90.0), 0.0, 0.05, 0.6, 0.0)
    base = b.mixc(speck, col, (0.02, 0.018, 0.016))
    b.surface(b.principled(base=base, rough=b.maprange(b.noise(v, 5.0, 4.0, 0.5), 0.3, 0.7, rough - 0.08, rough + 0.08),
                           normal=b.bump(b.noise(v, 25.0, 4.0, 0.5), 0.05, 0.0006)), simple=dict(base=col, rough=rough))
    return m


def _mat_emit(name, kelvin=2800.0, strength=12.0, body=(0.9, 0.9, 0.9)):
    """Light source surface (LED strip, diffuser): blackbody emission over a
    pale body colour, so it still reads as an object when dimmed."""
    m, b = _new(name)
    bb = b.node("ShaderNodeBlackbody", {"Temperature": kelvin})
    em = b.node("ShaderNodeEmission", {"Color": b.out(bb, 0), "Strength": strength})
    df = b.node("ShaderNodeBsdfDiffuse", {"Color": body})
    add = b.node("ShaderNodeAddShader", {0: b.out(df, 0), 1: b.out(em, 0)})
    b.surface(add)
    return m


def _mat_clay(name, col=(0.70, 0.69, 0.67)):
    m, b = _new(name)
    b.surface(b.principled(base=col, rough=0.8, spec=0.3))
    return m


def _mat_exterior(name, col=(0.10, 0.12, 0.14), haze=(1.0, 0.78, 0.55), haze_strength=1.6, falloff=900.0):
    """Distant towers: dark curtain-wall facades dissolving into warm haze."""
    m, b = _new(name)
    cam = b.node("ShaderNodeCameraData")
    d = b.out(cam, "View Distance")
    fac = b.math("SUBTRACT", 1.0, b.math("EXPONENT", b.math("DIVIDE", b.math("MULTIPLY", d, -1.0), falloff)))
    body = b.principled(base=col, metal=0.3, rough=0.25)
    em = b.node("ShaderNodeEmission", {"Color": haze, "Strength": haze_strength})
    b.surface(b.node("ShaderNodeMixShader", {0: fac, 1: b.out(body, 0), 2: b.out(em, 0)}))
    return m
