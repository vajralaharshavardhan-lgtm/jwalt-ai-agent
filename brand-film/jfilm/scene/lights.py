"""Lighting design, split into light groups so any lighting state (work
lights, dusk sun, cove on, downlights on...) can be mixed after rendering:
light is additive, so a still rendered once per group relights exactly."""
from __future__ import annotations

import math

import bpy
import mathutils
import numpy as np

from . import geo
from . import materials as M
from .dims import AXIS_X, COFFER_OPEN, MEET, NICHE, XP, XW, Y_PANEL, Z_CEIL

GROUPS = ["daylight", "cove_s", "cove_n", "cove_w", "cove_e", "down", "niche", "meeting", "work"]
COVE = ["cove_s", "cove_n", "cove_w", "cove_e"]

# Sun: late-afternoon, entering through the west facade (-x), travelling
# into the room and slightly toward the back wall so it rakes the reeds.
SUN_ELEV = 17.0          # degrees
SUN_TRAVEL_AZ = 22.0     # degrees from +x toward +y (direction light travels)


def kelvin_rgb(k: float) -> tuple[float, float, float]:
    """Approximate blackbody colour, normalised, linear."""
    t = k / 100.0
    if t <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
        b = 0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307
    else:
        r = 329.698727446 * (t - 60) ** -0.1332047592
        g = 288.1221695283 * (t - 60) ** -0.0755148492
        b = 255.0
    rgb = np.clip(np.array([r, g, b]) / 255.0, 0, 1) ** 2.2
    return tuple((rgb / rgb.max()).tolist())


def sun_direction() -> np.ndarray:
    """Unit vector the sunlight travels along."""
    e, a = math.radians(SUN_ELEV), math.radians(SUN_TRAVEL_AZ)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), -math.sin(e)])


def _lamp(name, kind, loc, power, color, group, size=0.05, size_y=None, spot=None, direction=None,
          camera_visible=False, state_group="finish"):
    ld = bpy.data.lights.new(name, kind)
    ld.color = color
    ld.energy = power
    if kind == "AREA":
        ld.shape = "RECTANGLE" if size_y else "SQUARE"
        ld.size = size
        if size_y:
            ld.size_y = size_y
    elif kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    if kind == "SPOT" and spot:
        ld.spot_size = math.radians(spot[0])
        ld.spot_blend = spot[1]
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    if direction is not None:
        d = mathutils.Vector(direction).normalized()
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = mathutils.Vector((0, 0, -1)).rotation_difference(d)
    ob.visible_camera = camera_visible
    geo.coll("lights").objects.link(ob)
    ob.lightgroup = group
    ob["jf_group"] = state_group
    ob["jf_layer"] = "lighting"
    ob["jf_lines"] = "none"
    ob["jf_lightgroup"] = group
    return ob


def build(scene: bpy.types.Scene) -> None:
    vl = scene.view_layers[0]
    for gname in GROUPS:
        if gname not in [lg.name for lg in vl.lightgroups]:
            vl.lightgroups.add(name=gname)

    _world(scene)
    d = sun_direction()
    _lamp("sun", "SUN", (0, 0, 20), 4.2, kelvin_rgb(3900), "daylight", direction=d, state_group="always")
    bpy.data.lights["sun"].angle = math.radians(0.9)

    _cove()
    _downlights()
    _niche()
    _meeting()
    _worklights()


def _world(scene):
    w = bpy.data.worlds.new("sky")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(SUN_ELEV)
    # Nishita azimuth: measured from +Y toward -X?  Solved numerically so the
    # sky's bright side matches the sun lamp (see _nishita_rotation).
    sky.sun_rotation = _nishita_rotation()
    sky.altitude = 120.0
    sky.air_density = 1.0
    sky.dust_density = 2.2
    sky.ozone_density = 1.0
    bg.inputs["Strength"].default_value = 0.22
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    w.lightgroup = "daylight"


def _nishita_rotation() -> float:
    # Direction TO the sun is -travel. Blender's Nishita rotation r places the
    # sun at azimuth (sin r, cos r) in xy (verified with a panorama probe).
    to_sun = -sun_direction()
    return math.atan2(to_sun[0], to_sun[1])


def _cove():
    g = "finish"
    cx0, cx1, cy0, cy1 = COFFER_OPEN
    mat = M.get("emit", kelvin=2750.0, strength=9.0)
    off = 0.07
    z0, z1 = Z_CEIL + 0.0125, Z_CEIL + 0.03
    strips = {"cove_s": (cx0 - 0.1, cx1 + 0.1, cy0 - off - 0.012, cy0 - off + 0.012),
              "cove_n": (cx0 - 0.1, cx1 + 0.1, cy1 + off - 0.012, cy1 + off + 0.012),
              "cove_w": (cx0 - off - 0.012, cx0 - off + 0.012, cy0 - 0.1, cy1 + 0.1),
              "cove_e": (cx1 + off - 0.012, cx1 + off + 0.012, cy0 - 0.1, cy1 + 0.1)}
    for name, (a, b, c, d) in strips.items():
        ob = geo.box(name, a, b, c, d, z0, z1, g, "lighting", mat, lines="none")
        ob.lightgroup = name          # one circuit per side: the cove can come on in sequence
        ob["jf_lightgroup"] = name


def _downlights():
    g = "finish"
    trim = M.get("black_metal", rough=0.3)
    lens = M.get("emit", kelvin=3000.0, strength=6.0, body=(0.6, 0.6, 0.6))
    xs = [x for x in np.linspace(XW + 0.6, XP - 0.5, 10)]
    for i, x in enumerate(xs):
        y = Y_PANEL - 0.55
        geo.cylinder(f"dl_trim_{i}", (x, y, Z_CEIL - 0.004), 0.045, 0.004, g, "lighting", trim, segs=32, lines="none")
        ob = geo.cylinder(f"dl_lens_{i}", (x, y, Z_CEIL - 0.0045), 0.026, 0.001, g, "lighting", lens, segs=24, lines="none")
        ob.lightgroup = "down"
        ob["jf_lightgroup"] = "down"
        _lamp(f"dl_{i}", "SPOT", (x, y, Z_CEIL - 0.03), 16.0, kelvin_rgb(3000), "down", size=0.02, spot=(58, 0.55),
              direction=(0, 0.42, -1))
    for i, y in enumerate(np.linspace(3.0, 7.8, 4)):
        x = XP - 0.7
        geo.cylinder(f"dl2_trim_{i}", (x, y, Z_CEIL - 0.004), 0.045, 0.004, g, "lighting", trim, segs=32, lines="none")
        ob = geo.cylinder(f"dl2_lens_{i}", (x, y, Z_CEIL - 0.0045), 0.026, 0.001, g, "lighting", lens, segs=24, lines="none")
        ob.lightgroup = "down"
        ob["jf_lightgroup"] = "down"
        _lamp(f"dl2_{i}", "SPOT", (x, y, Z_CEIL - 0.03), 10.0, kelvin_rgb(3000), "down", size=0.02, spot=(60, 0.6),
              direction=(0.15, 0, -1))


def _niche():
    g = "finish"
    x0, x1, ztop, yb = NICHE
    ob = geo.box("niche_led", x0 + 0.05, x1 - 0.05, Y_PANEL + 0.03, Y_PANEL + 0.05, ztop - 0.024, ztop - 0.02, g, "lighting",
                 M.get("emit", kelvin=2700.0, strength=10.0), lines="none")
    ob.lightgroup = "niche"
    ob["jf_lightgroup"] = "niche"
    _lamp("niche_wash", "AREA", ((x0 + x1) / 2, Y_PANEL + 0.06, ztop - 0.03), 55.0, kelvin_rgb(2700), "niche",
          size=x1 - x0 - 0.12, size_y=0.03, direction=(0, 0.25, -1))


def _meeting():
    tc = (7.35, 5.4)
    ob = geo.box("meet_pendant_led", tc[0] - 0.02, tc[0] + 0.02, tc[1] - 1.08, tc[1] + 1.08, 2.118, 2.12, "finish", "lighting",
                 M.get("emit", kelvin=3000.0, strength=14.0), lines="none")
    ob.lightgroup = "meeting"
    ob["jf_lightgroup"] = "meeting"
    _lamp("meet_wash", "AREA", (tc[0], tc[1], 2.11), 70.0, kelvin_rgb(3000), "meeting", size=0.04, size_y=2.1, direction=(0, 0, -1))
    mx0, mx1, my0, my1 = MEET
    _lamp("meet_fill", "AREA", ((mx0 + mx1) / 2, (my0 + my1) / 2, 3.18), 60.0, kelvin_rgb(3200), "meeting", size=2.0, size_y=4.0,
          direction=(0, 0, -1))


def _worklights():
    for k in (0, 1):
        lens = bpy.data.objects.get(f"work{k}_lens")
        if lens is None:
            continue
        lens.lightgroup = "work"
        mw = lens.matrix_world
        n = (mw.to_3x3() @ mathutils.Vector((0, -1, 0))).normalized()
        loc = mw.translation + n * 0.03
        _lamp(f"work{k}_lamp", "AREA", tuple(loc), 420.0, kelvin_rgb(5200), "work", size=0.36, size_y=0.24,
              direction=tuple(n), state_group="site")
