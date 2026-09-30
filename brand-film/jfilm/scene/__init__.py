"""Scene assembly + construction states.

`build_scene()` creates the whole environment once per process. Stills and
per-frame visibility buffers then only toggle which groups are present."""
from __future__ import annotations

import json

import bpy

from . import geo, lights, materials, room

# Construction states -> groups present. 'always' = sun.
STATES: dict[str, set[str]] = {
    "raw":            {"always", "shell", "mep", "framing", "site", "exterior"},
    "boarded":        {"always", "shell", "mep", "framing", "boards", "site", "exterior"},
    "finished":       {"always", "shell", "finish", "furniture", "exterior"},
    "finished_empty": {"always", "shell", "finish", "exterior"},
    "exploded":       {"always", "shell", "mep", "framing", "finish", "furniture"},
    "env":            {"always", "exterior"},
}

_built = False


def build_scene(force: bool = False):
    global _built
    if _built and not force:
        return registry()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geo.reset()
    materials.reset()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    room.build()
    lights.build(scene)
    _assign_ids()
    bpy.context.view_layer.update()     # world matrices are lazy: make them valid now
    _built = True
    return registry()


def _assign_ids():
    i = 1
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH":
            continue
        ob["jf_id"] = i
        ob.pass_index = i
        # 16-bit id split into two channels, exact in float EXR
        ob.color = ((i % 256) / 255.0, (i // 256) / 255.0, 1.0, 1.0)
        if ob.get("jf_glass"):
            ob.pass_index = 0      # see-through in stills' id pass (never matched as a surface)
        i += 1


def objects(group=None, layer=None, flag=None):
    out = []
    for ob in bpy.data.objects:
        if group is not None and ob.get("jf_group") != group:
            continue
        if layer is not None and ob.get("jf_layer") != layer:
            continue
        if flag is not None and not ob.get(f"jf_{flag}"):
            continue
        out.append(ob)
    return out


def apply_state(state: str | set[str], hide: set[str] | None = None, show: set[str] | None = None,
                glass_camera: bool = False):
    groups = STATES[state] if isinstance(state, str) else set(state)
    hide = hide or set()
    show = show or set()
    for ob in bpy.data.objects:
        g = ob.get("jf_group", "always")
        visible = (g in groups or ob.name in show) and ob.name not in hide
        ob.hide_render = not visible
        if ob.get("jf_glass"):
            ob.visible_camera = glass_camera


def registry() -> list[dict]:
    reg = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or "jf_id" not in ob:
            continue
        reg.append({
            "id": int(ob["jf_id"]), "name": ob.name, "group": ob.get("jf_group", ""),
            "layer": ob.get("jf_layer", ""), "lines": ob.get("jf_lines", "feature"),
            "lightgroup": ob.get("jf_lightgroup", ""), "glass": bool(ob.get("jf_glass", 0)),
        })
    return sorted(reg, key=lambda r: r["id"])


def save_registry(path):
    with open(path, "w") as f:
        json.dump(registry(), f)
