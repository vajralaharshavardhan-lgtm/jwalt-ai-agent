"""Blender render setups: Cycles projector stills and Workbench visibility
buffers. Both use the exact View maths from jfilm.camera."""
from __future__ import annotations

import os
from pathlib import Path

import bpy
import mathutils
import numpy as np

from ..camera import SENSOR_H, View
from ..scene import lights as L

# -----------------------------------------------------------------------------


def camera() -> bpy.types.Object:
    ob = bpy.data.objects.get("jf_camera")
    if ob is None:
        cd = bpy.data.cameras.new("jf_camera")
        ob = bpy.data.objects.new("jf_camera", cd)
        bpy.context.scene.collection.objects.link(ob)
        ob["jf_group"] = "always"
    bpy.context.scene.camera = ob
    return ob


def set_view(view: View, dof: bool = False):
    ob = camera()
    cd = ob.data
    ob.matrix_world = mathutils.Matrix(view.matrix_world().tolist())
    cd.type = "PERSP"
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = SENSOR_H
    cd.sensor_width = SENSOR_H * view.W / view.H
    cd.lens = view.lens_mm
    cd.shift_x = cd.shift_y = 0.0
    cd.clip_start = 0.01
    cd.clip_end = 20000.0
    cd.dof.use_dof = bool(dof and view.cam.focus)
    if cd.dof.use_dof:
        cd.dof.focus_distance = view.cam.focus
        cd.dof.aperture_fstop = view.cam.fstop
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = view.W, view.H
    sc.render.resolution_percentage = 100
    sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1.0


# --- Cycles stills --------------------------------------------------------------

def setup_cycles(samples: int, fast: bool = False):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02 if not fast else 0.03
    cy.adaptive_min_samples = 0
    cy.use_denoising = False          # denoised per pass in the compositor
    cy.max_bounces = 8
    cy.diffuse_bounces = 3 if not fast else 2
    cy.glossy_bounces = 3 if not fast else 2
    cy.transmission_bounces = 6
    cy.transparent_max_bounces = 16
    cy.volume_bounces = 0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 0.8
    cy.sample_clamp_direct = 0.0
    cy.sample_clamp_indirect = 6.0
    cy.use_light_tree = True
    cy.seed = 11
    cy.use_animated_seed = False
    cy.film_exposure = 1.0
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    sc.render.threads_mode = "AUTO"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    vl = sc.view_layers[0]
    vl.use_pass_combined = True
    vl.use_pass_z = True
    vl.use_pass_position = True
    vl.use_pass_normal = True
    vl.use_pass_object_index = True
    vl.cycles.denoising_store_passes = True
    return sc


def setup_still_compositor(base_path: str, groups: list[str], denoise: bool = True, extra_combined: bool = True):
    """Compositor: denoise every light-group pass (OIDN, albedo+normal guided)
    and write one multilayer EXR with lg_*, depth, position, normal, index."""
    sc = bpy.context.scene
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    out = nt.nodes.new("CompositorNodeOutputFile")
    out.base_path = base_path
    out.format.file_format = "OPEN_EXR_MULTILAYER"
    out.format.color_depth = "32"
    out.format.exr_codec = "ZIP"
    out.layer_slots.clear()
    comp = nt.nodes.new("CompositorNodeComposite")

    def sock(name):
        s = rl.outputs.get(name)
        if s is None:
            raise KeyError(f"render layer output {name!r} missing; have {[o.name for o in rl.outputs if o.enabled]}")
        return s

    def denoised(src):
        if not denoise:
            return src
        dn = nt.nodes.new("CompositorNodeDenoise")
        dn.prefilter = "ACCURATE"
        dn.use_hdr = True
        if hasattr(dn, "quality"):
            dn.quality = "HIGH"
        nt.links.new(src, dn.inputs["Image"])
        nt.links.new(sock("Denoising Normal"), dn.inputs["Normal"])
        nt.links.new(sock("Denoising Albedo"), dn.inputs["Albedo"])
        return dn.outputs["Image"]

    for g in groups:
        out.layer_slots.new(f"lg_{g}")
        nt.links.new(denoised(sock(f"Combined_{g}")), out.inputs[f"lg_{g}"])
    if extra_combined:
        out.layer_slots.new("combined")
        c = denoised(sock("Image"))
        nt.links.new(c, out.inputs["combined"])
        nt.links.new(c, comp.inputs["Image"])
    else:
        nt.links.new(sock("Image"), comp.inputs["Image"])
    for name, src in (("depth", "Depth"), ("position", "Position"), ("normal", "Normal"), ("index", "IndexOB"),
                      ("albedo", "Denoising Albedo")):
        out.layer_slots.new(name)
        nt.links.new(sock(src), out.inputs[name])
    return out


def render_still(view: View, path: Path, samples: int, groups: list[str] | None = None, dof: bool = False,
                 denoise: bool = True, fast: bool = False) -> Path:
    """Render one projector still to `path` (multilayer EXR)."""
    groups = groups or L.GROUPS
    setup_cycles(samples, fast=fast)
    set_view(view, dof=dof)
    path = Path(path)
    tmpdir = path.parent / (path.stem + "_tmp")
    tmpdir.mkdir(parents=True, exist_ok=True)
    setup_still_compositor(str(tmpdir) + "/", groups, denoise=denoise)
    sc = bpy.context.scene
    sc.frame_set(1)
    sc.render.filepath = str(tmpdir / "beauty")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=False)
    produced = sorted(tmpdir.glob("*.exr"))
    if not produced:
        raise RuntimeError("compositor produced no EXR")
    os.replace(produced[-1], path)
    for p in tmpdir.iterdir():
        p.unlink()
    tmpdir.rmdir()
    return path


# --- Workbench visibility buffer -------------------------------------------------

def setup_workbench_ids():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "OBJECT"
    sh.show_shadows = False
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    sh.show_xray = False
    sh.use_dof = False
    sh.background_type = "WORLD"
    sc.display.render_aa = "OFF"
    sc.render.film_transparent = True
    sc.render.dither_intensity = 0.0
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.use_nodes = False
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    img = sc.render.image_settings
    img.file_format = "OPEN_EXR_MULTILAYER"
    img.color_depth = "32"
    img.exr_codec = "ZIP"


def render_ids(view: View, path: Path) -> Path:
    set_view(view)
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return Path(path)
