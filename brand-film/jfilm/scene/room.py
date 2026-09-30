"""The film's single architectural environment: an illustrative hotel-lounge
fit-out (NOT a real J-WALT project). One model carries every construction
stage, so the drawing, the structure, the exploded engineering view, the
site and the finished space are always the same geometry.

Groups (construction state buckets):
  shell     concrete frame, blockwork, facade, screed
  mep       ducts, sprinkler pipes, cable trays, hangers
  framing   wall studs, ceiling suspension grid
  boards    plasterboard (BOARDED stage only)
  finish    reeded oak, stone floor, painted ceiling, coffer, niche, partition...
  furniture loose furniture and decor
  site      work lights, material stacks (construction stage only)
  exterior  distant city (always)

Coordinates: metres, Z up. Lounge interior x in [-6.0, 5.4], y in [0, 9],
finished floor z=0, ceiling z=3.8, coffer z=4.35, soffit z=4.6.
"""
from __future__ import annotations

import math

import numpy as np

from . import geo
from . import materials as M

from .dims import *  # noqa: F401,F403  (key dimensions)
from .dims import (AXIS_X, CHAIRS, COFFER_OPEN, COFFER_WALL, MEET, MULLIONS_Y, NICHE, PARTITION_Y, SOFA, TABLE_C,
                   XP, XW, Y0, Y_PANEL, YB, Z_CEIL, Z_COFFER, Z_SOFFIT)


def _rot_z(points, center, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    P = np.asarray(points, float) - np.asarray(center, float)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return P @ R.T + np.asarray(center, float)


def build() -> None:
    mats = {
        "concrete": M.get("concrete"),
        "concrete_dark": M.get("concrete", tone=0.8),
        "plaster": M.get("plaster_raw"),
        "screed": M.get("screed"),
        "limestone": M.get("limestone"),
        "travertine": M.get("travertine"),
        "travertine_v": M.get("travertine", vertical=True, tone=1.05),
        "oak_z": M.get("oak", axis="Z"),
        "oak_y": M.get("oak", axis="Y"),
        "oak_x": M.get("oak", axis="X"),
        "bronze": M.get("bronze"),
        "bronze_dark": M.get("bronze", dark=0.6),
        "galv": M.get("galvanised"),
        "black": M.get("black_metal"),
        "paint": M.get("paint"),
        "paint_grey": M.get("paint", col=(0.40, 0.38, 0.35)),
        "board": M.get("gypsum_board"),
        "red": M.get("red_pipe"),
        "cable": M.get("cable"),
        "boucle": M.get("boucle"),
        "velvet": M.get("velvet"),
        "boucle_dark": M.get("boucle", col=(0.16, 0.145, 0.13)),
        "rug": M.get("rug"),
        "sheer": M.get("sheer"),
        "glass": M.get("glass"),
        "ceramic_dark": M.get("ceramic"),
        "ceramic_sand": M.get("ceramic", col=(0.42, 0.34, 0.25), rough=0.65),
        "cardboard": M.get("paint", col=(0.33, 0.22, 0.12)),
        "timber_raw": M.get("oak", axis="X", tone=2.2),
        "exterior": M.get("exterior"),
        "exterior_ground": M.get("exterior", col=(0.15, 0.12, 0.09), falloff=600.0),
    }
    _shell(mats)
    _exterior(mats)
    _mep(mats)
    _framing(mats)
    _boards(mats)
    _finish_floor(mats)
    _finish_walls(mats)
    _finish_ceiling(mats)
    _partition_and_meeting(mats)
    _furniture(mats)
    _site(mats)


# --- shell -------------------------------------------------------------------

def _shell(m):
    g, L = "shell", "shell"
    geo.box("slab_floor", -6.3, 9.7, -0.6, 9.6, -0.36, -0.06, g, "floor", m["concrete"], lines="outline")
    geo.box("screed", XW, MEET[1], Y0, 9.25, -0.06, -0.02, g, "floor", m["screed"], lines="outline")
    geo.box("slab_soffit", -6.3, 9.7, -0.6, 9.6, Z_SOFFIT, Z_SOFFIT + 0.3, g, L, m["concrete_dark"], lines="outline")
    # back wall blockwork with the niche cut out
    x0, x1, ztop, yb = NICHE
    geo.box("wall_back_l", -6.3, x0, YB, 9.3, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_back_r", x1, 9.7, YB, 9.3, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_back_top", x0, x1, YB, 9.3, ztop, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_back_niche", x0, x1, yb + 0.02, 9.3, -0.06, ztop, g, "walls", m["plaster"], lines="none")
    # front wall with entrance opening
    geo.box("wall_front_l", -6.3, -1.5, -0.25, Y0, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_front_r", 0.9, 9.7, -0.25, Y0, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_front_top", -1.5, 0.9, -0.25, Y0, 3.0, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    # meeting-room shell walls
    geo.box("wall_meet_back", MEET[1], MEET[1] + 0.25, -0.6, 9.6, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_meet_s", XP + 0.02, MEET[1], MEET[2] - 0.2, MEET[2], -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_meet_n", XP + 0.02, MEET[1], MEET[3], MEET[3] + 0.2, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_right_front", XP, XP + 0.2, -0.25, MEET[2] - 0.2, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    geo.box("wall_right_back", XP, XP + 0.2, MEET[3] + 0.2, YB, -0.06, Z_SOFFIT, g, "walls", m["plaster"], lines="outline")
    # facade: bronze mullions, spandrel above ceiling line, glass (glass handled by renderer)
    for i, y in enumerate(MULLIONS_Y):
        geo.box(f"mullion_{i}", XW - 0.14, XW - 0.02, y - 0.03, y + 0.03, -0.06, Z_SOFFIT, g, "facade", m["bronze_dark"],
                bevel_w=0.003)
    geo.box("facade_transom", XW - 0.14, XW - 0.02, -0.25, 9.3, Z_CEIL + 0.02, Z_CEIL + 0.08, g, "facade", m["bronze_dark"],
            bevel_w=0.003, lines="outline")
    geo.box("facade_spandrel", XW - 0.16, XW - 0.15, -0.25, 9.3, Z_CEIL + 0.08, Z_SOFFIT + 0.3, g, "facade", m["steel_dark"] if "steel_dark" in m else M.get("steel_dark"),
            lines="none")
    geo.box("facade_sill", XW - 0.3, XW - 0.02, -0.25, 9.3, -0.1, -0.06, g, "facade", m["bronze_dark"], lines="outline")
    for i, (ya, yb2) in enumerate(zip(MULLIONS_Y[:-1], MULLIONS_Y[1:])):
        ob = geo.box(f"glass_facade_{i}", XW - 0.09, XW - 0.08, ya + 0.03, yb2 - 0.03, -0.06, Z_CEIL + 0.02, g, "facade",
                     m["glass"], lines="none")
        ob["jf_glass"] = 1
    # exterior terrace edge (catches the low sun, gives the facade depth)
    geo.box("terrace", -9.5, XW - 0.14, -3.0, 12.0, -0.40, -0.10, g, "exterior", m["concrete"], lines="none")
    # vertical brise-soleil fins: cut the low western sun into raking stripes
    for i, y in enumerate(np.arange(-0.25, 9.3, 0.5)):
        geo.box(f"fin_{i}", XW - 0.62, XW - 0.18, y - 0.025, y + 0.025, -0.40, Z_SOFFIT + 0.3, g, "facade", m["bronze_dark"],
                bevel_w=0.004, lines="none")


def _exterior(m):
    g = "exterior"
    rng = np.random.default_rng(7)
    k = 0
    for ring, (rmin, rmax, n) in enumerate([(260, 520, 14), (560, 1100, 22), (1200, 2400, 26)]):
        for i in range(n):
            ang = rng.uniform(math.radians(95), math.radians(265))      # west side hemisphere (-x)
            r = rng.uniform(rmin, rmax)
            cx, cy = r * -abs(math.sin(ang)) + XW, r * math.cos(ang) + 4.5
            w = rng.uniform(22, 60)
            d = rng.uniform(22, 60)
            h = rng.uniform(40, 330) * (1.0 if ring < 2 else 1.3)
            ob = geo.box(f"tower_{k}", cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, -140, h - 140 + 60, g, g,
                         m["exterior"], lines="none")
            ob.visible_shadow = False
            ob.lightgroup = "daylight"
            k += 1
    gr = geo.plane_xy("ground", -9000, 3000, -6000, 6000, -140, g, g, m["exterior_ground"])
    gr.visible_shadow = False
    gr.lightgroup = "daylight"


# --- MEP -------------------------------------------------------------------------

def _mep(m):
    g, L = "mep", "mep"
    # supply duct along the window side, return duct along the partition side
    geo.box("duct_supply", -4.95, -4.25, -0.2, 9.0, 4.12, 4.47, g, L, m["galv"], bevel_w=0.004)
    geo.box("duct_return", 3.95, 4.45, -0.2, 9.0, 4.18, 4.48, g, L, m["galv"], bevel_w=0.004)
    for i, y in enumerate([1.2, 3.4, 5.6, 7.8]):
        geo.box(f"duct_branch_{i}", -5.35, -4.95, y - 0.16, y + 0.16, 4.22, 4.40, g, L, m["galv"], bevel_w=0.003)
        geo.cylinder(f"duct_drop_{i}", (-5.2, y, 3.84), 0.1, 0.38, g, L, m["galv"], segs=32)
    for i, x in enumerate([-3.0, 0.0, 2.8]):
        geo.box(f"duct_cross_{i}", x - 0.2, x + 0.2, 0.4, 2.4, 4.24, 4.46, g, L, m["galv"], bevel_w=0.003)
    # sprinkler mains + branches (red), cable tray with cables
    for i, y in enumerate([1.1, 8.3]):
        geo.cylinder(f"spk_main_{i}", (-6.0, y, 4.52), 0.035, 11.4, g, L, m["red"], segs=20, axis="X")
    for i, x in enumerate(np.arange(-5.4, 5.0, 2.1)):
        geo.cylinder(f"spk_branch_{i}", (x, 1.1, 4.50), 0.022, 7.2, g, L, m["red"], segs=16, axis="Y")
        for j, y in enumerate([2.5, 4.9, 7.3]):
            geo.cylinder(f"spk_drop_{i}_{j}", (x, y, 3.86), 0.012, 0.64, g, L, m["red"], segs=12)
    geo.box("tray", 4.62, 4.98, -0.2, 9.0, 4.36, 4.40, g, L, m["galv"], lines="outline")
    for i, dx in enumerate(np.linspace(4.66, 4.94, 6)):
        geo.cylinder(f"cable_{i}", (dx, -0.2, 4.415), 0.013, 9.2, g, L, m["cable"], segs=10, axis="Y")
    # hangers
    for i, y in enumerate(np.arange(0.6, 9.0, 1.4)):
        for j, x in enumerate([-4.98, -4.22, 3.92, 4.48, 4.6, 5.0]):
            geo.cylinder(f"hanger_{i}_{j}", (x, y, 4.1), 0.005, Z_SOFFIT - 4.1, g, L, m["galv"], segs=6, lines="none")


# --- framing -----------------------------------------------------------------------

def _framing(m):
    g, L = "framing", "walls"
    x0n, x1n, ztop, _ = NICHE
    y_s0, y_s1 = 8.9105, 8.9605
    xs = list(np.arange(XW, XP + 1e-6, 0.6))
    for i, x in enumerate(xs):
        if x0n + 0.05 < x < x1n - 0.05:
            geo.box(f"stud_cripple_{i}", x - 0.025, x + 0.025, y_s0, y_s1, ztop, Z_CEIL, g, L, m["galv"])
            continue
        geo.box(f"stud_{i}", x - 0.025, x + 0.025, y_s0, y_s1, 0.0, Z_CEIL, g, L, m["galv"])
    for x in (x0n, x1n):
        geo.box(f"stud_niche_{x:+.1f}", x - 0.025, x + 0.025, y_s0, y_s1, 0.0, Z_CEIL, g, L, m["galv"])
    geo.box("track_bottom", XW, XP, y_s0, y_s1, 0.0, 0.03, g, L, m["galv"], lines="outline")
    geo.box("track_top", XW, XP, y_s0, y_s1, Z_CEIL - 0.03, Z_CEIL, g, L, m["galv"], lines="outline")
    geo.box("niche_header", x0n, x1n, y_s0, y_s1, ztop, ztop + 0.05, g, L, m["galv"], lines="outline")
    # ceiling suspension grid (main channels along x, furring along y) + hangers
    Lc = "ceiling"
    for i, y in enumerate(np.arange(0.6, 9.0, 1.2)):
        geo.box(f"ceil_main_{i}", XW, XP, y - 0.019, y + 0.019, Z_CEIL + 0.042, Z_CEIL + 0.080, g, Lc, m["galv"], lines="outline")
        for j, x in enumerate(np.arange(-5.4, 5.4, 1.2)):
            geo.cylinder(f"ceil_hanger_{i}_{j}", (x, y, Z_CEIL + 0.08), 0.004, Z_SOFFIT - Z_CEIL - 0.08, g, Lc, m["galv"],
                         segs=6, lines="none")
    for j, x in enumerate(np.arange(XW + 0.2, XP, 0.4)):
        cx0, cx1, cy0, cy1 = COFFER_OPEN
        if cx0 < x < cx1:
            for k, (ya, yb) in enumerate([(0.0, cy0), (cy1, YB)]):
                geo.box(f"ceil_fur_{j}_{k}", x - 0.024, x + 0.024, ya, yb, Z_CEIL + 0.0125, Z_CEIL + 0.04, g, Lc, m["galv"],
                        lines="outline")
        else:
            geo.box(f"ceil_fur_{j}", x - 0.024, x + 0.024, 0.0, YB, Z_CEIL + 0.0125, Z_CEIL + 0.04, g, Lc, m["galv"], lines="outline")


# --- boards (BOARDED stage) ----------------------------------------------------------

def _boards(m):
    g = "boards"
    x0n, x1n, ztop, _ = NICHE
    yb0, yb1 = 8.898, 8.9105
    k = 0
    for x in np.arange(XW, XP - 1e-6, 1.2):
        xa, xb = x, min(x + 1.2, XP)
        for za, zb in ((0.0, 2.4), (2.4, Z_CEIL)):
            if xb <= x0n or xa >= x1n or za >= ztop:
                geo.box(f"wboard_{k}", xa + 0.001, xb - 0.001, yb0, yb1, za + 0.001, zb - 0.001, g, "walls", m["board"], lines="outline")
                k += 1
            else:  # split around the niche opening
                for (pa, pb) in ((xa, min(xb, x0n)), (max(xa, x1n), xb)):
                    if pb - pa > 0.05:
                        geo.box(f"wboard_{k}", pa + 0.001, pb - 0.001, yb0, yb1, za + 0.001, zb - 0.001, g, "walls", m["board"], lines="outline")
                        k += 1
                if zb > ztop:
                    geo.box(f"wboard_{k}", max(xa, x0n) + 0.001, min(xb, x1n) - 0.001, yb0, yb1, ztop + 0.001, zb - 0.001, g, "walls",
                            m["board"], lines="outline")
                    k += 1
    # ceiling boards 1.2 x 2.4 around the coffer opening
    cx0, cx1, cy0, cy1 = COFFER_OPEN
    k = 0
    for x in np.arange(XW, XP - 1e-6, 1.2):
        for y in np.arange(Y0, YB - 1e-6, 2.4):
            xa, xb, ya, yb = x, min(x + 1.2, XP), y, min(y + 2.4, YB)
            pieces = [(xa, xb, ya, yb)]
            out = []
            for (pa, pb, qa, qb) in pieces:
                if pb <= cx0 or pa >= cx1 or qb <= cy0 or qa >= cy1:
                    out.append((pa, pb, qa, qb))
                else:
                    if pa < cx0:
                        out.append((pa, cx0, qa, qb))
                    if pb > cx1:
                        out.append((cx1, pb, qa, qb))
                    ia, ib = max(pa, cx0), min(pb, cx1)
                    if qa < cy0:
                        out.append((ia, ib, qa, cy0))
                    if qb > cy1:
                        out.append((ia, ib, cy1, qb))
            for (pa, pb, qa, qb) in out:
                if pb - pa > 0.02 and qb - qa > 0.02:
                    geo.box(f"cboard_{k}", pa + 0.001, pb - 0.001, qa + 0.001, qb - 0.001, Z_CEIL, Z_CEIL + 0.0125, g, "ceiling",
                            m["board"], lines="outline")
                    k += 1


# --- finishes ---------------------------------------------------------------------------

def _finish_floor(m):
    g, L = "finish", "floor"
    k = 0
    gap = 0.002
    regions = [(XW, XP, Y0, 9.2), (XP, MEET[1], MEET[2], MEET[3])]
    for (ra, rb, qa, qb) in regions:
        for x in np.arange(XW, rb - 1e-6, 1.2):
            for y in np.arange(Y0, qb - 1e-6, 0.6):
                xa, xb = max(x, ra), min(x + 1.2, rb)
                ya, yb = max(y, qa), min(y + 0.6, qb)
                if xb - xa < 0.03 or yb - ya < 0.03:
                    continue
                ob = geo.box(f"tile_{k}", xa + gap / 2, xb - gap / 2, ya + gap / 2, yb - gap / 2, -0.02, 0.0, g, L,
                             m["limestone"], bevel_w=0.0015, bevel_seg=2, lines="outline")
                ob["jf_tile"] = 1
                k += 1
    geo.box("skirting_gap", XW, XP, 8.885, 8.898, 0.0, 0.02, g, "joinery", m["black"], lines="none")


def _finish_walls(m):
    g = "finish"
    x0n, x1n, ztop, yback = NICHE
    # reeded smoked-oak panels, 8 per side of the niche, 4 over it
    for side, (xa, xb) in enumerate(((XW, x0n), (x1n, XP))):
        w = (xb - xa) / 8
        for i in range(8):
            ob = geo.reeded_panel(f"reed_{side}_{i}", xa + i * w + 0.0005, xa + (i + 1) * w - 0.0005, 0.02, Z_CEIL,
                                  Y_PANEL, g, "joinery", m["oak_z"])
            ob["jf_panel"] = 1
    for i in range(4):
        w = (x1n - x0n) / 4
        ob = geo.reeded_panel(f"reed_top_{i}", x0n + i * w + 0.0005, x0n + (i + 1) * w - 0.0005, ztop + 0.012, Z_CEIL,
                              Y_PANEL, g, "joinery", m["oak_z"])
        ob["jf_panel"] = 1
    # stone niche lining, bronze frame, floating oak console + decor
    geo.box("niche_back", x0n, x1n, yback - 0.03, yback, 0.0, ztop, g, "joinery", m["travertine_v"], lines="outline")
    geo.box("niche_side_l", x0n, x0n + 0.03, Y_PANEL, yback, 0.0, ztop, g, "joinery", m["travertine_v"], lines="outline")
    geo.box("niche_side_r", x1n - 0.03, x1n, Y_PANEL, yback, 0.0, ztop, g, "joinery", m["travertine_v"], lines="outline")
    geo.box("niche_soffit", x0n, x1n, Y_PANEL, yback, ztop - 0.02, ztop, g, "joinery", m["travertine_v"], lines="outline")
    geo.box("niche_frame_l", x0n - 0.012, x0n + 0.002, Y_PANEL - 0.012, Y_PANEL + 0.02, 0.0, ztop + 0.012, g, "joinery", m["bronze"],
            bevel_w=0.001)
    geo.box("niche_frame_r", x1n - 0.002, x1n + 0.012, Y_PANEL - 0.012, Y_PANEL + 0.02, 0.0, ztop + 0.012, g, "joinery", m["bronze"],
            bevel_w=0.001)
    geo.box("niche_frame_t", x0n - 0.012, x1n + 0.012, Y_PANEL - 0.012, Y_PANEL + 0.02, ztop, ztop + 0.012, g, "joinery", m["bronze"],
            bevel_w=0.001)
    geo.box("console", x0n + 0.12, x1n - 0.12, Y_PANEL + 0.01, yback - 0.03, 0.70, 0.76, g, "joinery", m["oak_x"], bevel_w=0.003)
    geo.lathe("vase", [(0.0, 0.0), (0.075, 0.0), (0.105, 0.04), (0.13, 0.16), (0.12, 0.30), (0.075, 0.40), (0.06, 0.46),
                       (0.066, 0.49), (0.055, 0.49), (0.0, 0.10)], (x0n + 0.55, 9.03, 0.76), g, "furniture", m["ceramic_dark"])
    geo.lathe("bowl_niche", [(0.0, 0.0), (0.09, 0.0), (0.17, 0.035), (0.21, 0.10), (0.20, 0.105), (0.16, 0.04), (0.0, 0.012)],
              (x1n - 0.6, 9.03, 0.76), g, "furniture", m["ceramic_sand"])
    # painted skins: front wall, right-hand solid walls
    geo.box("paint_front_l", -6.0, -1.5, Y0, Y0 + 0.012, 0.0, Z_CEIL, g, "walls", m["paint"], lines="outline")
    geo.box("paint_front_r", 0.9, XP, Y0, Y0 + 0.012, 0.0, Z_CEIL, g, "walls", m["paint"], lines="outline")
    geo.box("paint_right_front", XP - 0.012, XP, Y0, MEET[2], 0.0, Z_CEIL, g, "walls", m["paint"], lines="outline")
    geo.box("paint_right_back", XP - 0.012, XP, MEET[3], YB, 0.0, Z_CEIL, g, "walls", m["paint"], lines="outline")
    # sheers: gathered at both ends of the facade, clear glazing between
    geo.pleated_sheet("sheer_front", XW + 0.16, 0.05, 2.9, 0.012, Z_CEIL - 0.005, g, "joinery", m["sheer"], pleat=0.10, amp=0.05, seed=1)
    geo.pleated_sheet("sheer_back", XW + 0.16, 7.35, 8.85, 0.012, Z_CEIL - 0.005, g, "joinery", m["sheer"], pleat=0.09, amp=0.055, seed=2)
    geo.box("curtain_track", XW + 0.06, XW + 0.26, Y0, YB, Z_CEIL - 0.004, Z_CEIL + 0.10, g, "ceiling", m["black"], lines="outline")


def _finish_ceiling(m):
    g = "finish"
    cx0, cx1, cy0, cy1 = COFFER_OPEN
    wx0, wx1, wy0, wy1 = COFFER_WALL
    t = 0.0125
    # painted ceiling around the coffer opening (4 pieces)
    for name, (a, b, c, d) in {"ceil_s": (XW + 0.26, XP, Y0, cy0), "ceil_n": (XW + 0.26, XP, cy1, YB),
                               "ceil_w": (XW + 0.26, cx0, cy0, cy1), "ceil_e": (cx1, XP, cy0, cy1)}.items():
        geo.box(name, a, b, c, d, Z_CEIL, Z_CEIL + t, g, "ceiling", m["paint"], lines="outline")
    # coffer: upstand lip, void walls, coffer ceiling
    lip = 0.13
    geo.box("lip_s", cx0, cx1, cy0 - 0.012, cy0, Z_CEIL, Z_CEIL + lip, g, "ceiling", m["paint"])
    geo.box("lip_n", cx0, cx1, cy1, cy1 + 0.012, Z_CEIL, Z_CEIL + lip, g, "ceiling", m["paint"])
    geo.box("lip_w", cx0 - 0.012, cx0, cy0, cy1, Z_CEIL, Z_CEIL + lip, g, "ceiling", m["paint"])
    geo.box("lip_e", cx1, cx1 + 0.012, cy0, cy1, Z_CEIL, Z_CEIL + lip, g, "ceiling", m["paint"])
    geo.box("cwall_s", wx0, wx1, wy0 - 0.012, wy0, Z_CEIL, Z_COFFER, g, "ceiling", m["paint"], lines="outline")
    geo.box("cwall_n", wx0, wx1, wy1, wy1 + 0.012, Z_CEIL, Z_COFFER, g, "ceiling", m["paint"], lines="outline")
    geo.box("cwall_w", wx0 - 0.012, wx0, wy0, wy1, Z_CEIL, Z_COFFER, g, "ceiling", m["paint"], lines="outline")
    geo.box("cwall_e", wx1, wx1 + 0.012, wy0, wy1, Z_CEIL, Z_COFFER, g, "ceiling", m["paint"], lines="outline")
    geo.box("coffer_ceiling", wx0, wx1, wy0, wy1, Z_COFFER, Z_COFFER + t, g, "ceiling", m["paint"], lines="outline")
    # oak slats inside the coffer
    n = int((cx1 - cx0 - 0.3) / 0.12)
    x_start = AXIS_X - (n - 1) * 0.12 / 2
    for i in range(n):
        x = x_start + i * 0.12
        ob = geo.box(f"slat_{i}", x - 0.02, x + 0.02, cy0 + 0.1, cy1 - 0.1, Z_COFFER - 0.105, Z_COFFER - 0.015, g, "joinery",
                     m["oak_y"], bevel_w=0.002, lines="outline")
        ob["jf_slat"] = 1
    # linear slot diffuser (HVAC) along the window, black
    geo.box("slot_diffuser", -5.26, -5.14, 0.8, 8.2, Z_CEIL - 0.002, Z_CEIL + 0.001, g, "mep", m["black"], lines="outline")


def _partition_and_meeting(m):
    g = "finish"
    y0, y1 = PARTITION_Y[0], PARTITION_Y[-1]
    geo.box("part_head", XP - 0.03, XP + 0.04, y0, y1, Z_CEIL - 0.06, Z_CEIL, g, "partition", m["bronze"], bevel_w=0.002)
    geo.box("part_sill", XP - 0.03, XP + 0.04, y0, y1, 0.0, 0.025, g, "partition", m["bronze"], bevel_w=0.002)
    for i, y in enumerate(PARTITION_Y):
        geo.box(f"part_mullion_{i}", XP - 0.03, XP + 0.04, y - 0.015, y + 0.015, 0.025, Z_CEIL - 0.06, g, "partition",
                m["bronze"], bevel_w=0.002)
    for i, (ya, yb) in enumerate(zip(PARTITION_Y[:-1], PARTITION_Y[1:])):
        ob = geo.box(f"glass_part_{i}", XP + 0.0, XP + 0.01, ya + 0.015, yb - 0.015, 0.025, Z_CEIL - 0.06, g, "partition",
                     m["glass"], lines="outline")
        ob["jf_glass"] = 1
        ob["jf_panel_glass"] = 1
    # meeting room: ceiling, wall paint, table, chairs, pendant, credenza
    mx0, mx1, my0, my1 = MEET
    geo.box("meet_ceiling", mx0, mx1, my0, my1, 3.2, 3.2 + 0.0125, g, "ceiling", m["paint"], lines="outline")
    geo.box("meet_bulkhead", mx0 + 0.04, mx0 + 0.06, my0, my1, 3.2, Z_CEIL, g, "ceiling", m["paint"], lines="none")
    geo.box("meet_wall", mx1 - 0.012, mx1, my0, my1, 0.0, 3.2, g, "walls", m["paint_grey"], lines="outline")
    tc = (7.35, 5.4)
    geo.box("meet_table_top", tc[0] - 0.55, tc[0] + 0.55, tc[1] - 1.5, tc[1] + 1.5, 0.70, 0.75, g, "furniture", m["oak_y"], bevel_w=0.004)
    for dy in (-0.9, 0.9):
        geo.box(f"meet_table_leg_{dy:+.0f}", tc[0] - 0.1, tc[0] + 0.1, tc[1] + dy - 0.35, tc[1] + dy + 0.35, 0.0, 0.70, g, "furniture",
                m["travertine"], bevel_w=0.003)
    for side in (-1, 1):
        for j, dy in enumerate((-0.95, 0.0, 0.95)):
            cx = tc[0] + side * 0.85
            geo.rounded_box(f"meet_chair_seat_{side}_{j}", (cx, tc[1] + dy, 0.44), (0.5, 0.5, 0.1), 0.035, g, "furniture",
                            m["boucle_dark"], n=8, puff=0.01)
            geo.rounded_box(f"meet_chair_back_{side}_{j}", (cx + side * 0.23, tc[1] + dy, 0.72), (0.08, 0.48, 0.46), 0.03, g,
                            "furniture", m["boucle_dark"], n=8)
            geo.box(f"meet_chair_base_{side}_{j}", cx - 0.02, cx + 0.02, tc[1] + dy - 0.02, tc[1] + dy + 0.02, 0.0, 0.39, g,
                    "furniture", m["black"], lines="none")
    geo.box("meet_pendant", tc[0] - 0.03, tc[0] + 0.03, tc[1] - 1.1, tc[1] + 1.1, 2.12, 2.17, g, "lighting", m["bronze"], bevel_w=0.002)
    for dy in (-1.0, 1.0):
        geo.cylinder(f"meet_pendant_wire_{dy:+.0f}", (tc[0], tc[1] + dy, 2.17), 0.0015, 3.2 - 2.17, g, "lighting", m["black"], segs=6,
                     lines="none")
    geo.box("meet_credenza", mx1 - 0.47, mx1 - 0.02, tc[1] - 1.2, tc[1] + 1.2, 0.08, 0.76, g, "furniture", m["oak_y"], bevel_w=0.003)


def _furniture(m):
    g = "furniture"
    tx, ty = TABLE_C
    geo.rounded_box("rug", (tx, ty, 0.007), (3.9, 2.9, 0.014), 0.006, g, g, m["rug"], n=6)
    # travertine drum coffee table + bowl
    geo.cylinder("table_base", (tx, ty, 0.0), 0.34, 0.31, g, g, m["travertine"], segs=96, bevel_w=0.004)
    geo.cylinder("table_top", (tx, ty, 0.31), 0.56, 0.05, g, g, m["travertine"], segs=128, bevel_w=0.006)
    geo.lathe("bowl_table", [(0.0, 0.0), (0.07, 0.0), (0.15, 0.03), (0.19, 0.085), (0.182, 0.09), (0.14, 0.035), (0.0, 0.01)],
              (tx - 0.12, ty + 0.08, 0.36), g, g, m["ceramic_dark"])
    # sofa
    sx, sy = SOFA
    L, D = 2.7, 0.98
    x0, x1, y0, y1 = sx - L / 2, sx + L / 2, sy - D / 2, sy + D / 2
    geo.box("sofa_plinth", x0 + 0.08, x1 - 0.08, y0 + 0.08, y1 - 0.08, 0.0, 0.11, g, g, m["black"], lines="outline")
    geo.rounded_box("sofa_base", (sx, sy, 0.205), (L, D, 0.19), 0.03, g, g, m["boucle"], n=10)
    geo.rounded_box("sofa_back", (sx, y1 - 0.06, 0.45), (L, 0.12, 0.52), 0.045, g, g, m["boucle"], n=10)
    for i, xa in enumerate((x0, x1 - 0.16)):
        geo.rounded_box(f"sofa_arm_{i}", (xa + 0.08, sy, 0.39), (0.16, D, 0.40), 0.05, g, g, m["boucle"], n=10)
    inner0, inner1 = x0 + 0.16, x1 - 0.16
    cw = (inner1 - inner0) / 2
    for i in range(2):
        cxc = inner0 + cw * (i + 0.5)
        geo.rounded_box(f"sofa_seat_{i}", (cxc, sy - 0.07, 0.365), (cw - 0.01, D - 0.2, 0.15), 0.055, g, g, m["boucle"], n=12, puff=0.018)
        back = geo.rounded_box(f"sofa_cushion_{i}", (cxc, y1 - 0.22, 0.60), (cw - 0.02, 0.2, 0.42), 0.075, g, g, m["boucle"], n=12,
                               puff=0.02, puff_axis=1)
        back.rotation_euler[0] = math.radians(-9)
    # lounge chairs (seat, back, slim bronze legs), turned toward the table
    for k, (cx, cy, rot) in enumerate(CHAIRS):
        parts = []
        parts.append(geo.rounded_box(f"chair{k}_seat", (cx, cy, 0.36), (0.74, 0.72, 0.15), 0.05, g, g, m["velvet"], n=12, puff=0.016))
        back = geo.rounded_box(f"chair{k}_back", (cx, cy - 0.33, 0.62), (0.74, 0.13, 0.46), 0.055, g, g, m["velvet"], n=12,
                               puff=0.012, puff_axis=1)
        back.rotation_euler[0] = math.radians(13)
        parts.append(back)
        for j, (dx, dy) in enumerate(((-0.3, -0.28), (0.3, -0.28), (-0.3, 0.28), (0.3, 0.28))):
            parts.append(geo.cylinder(f"chair{k}_leg{j}", (cx + dx, cy + dy, 0.0), 0.012, 0.29, g, g, m["bronze"], segs=16))
        for ob in parts:
            loc = np.array(ob.location)
            ob.location = _rot_z([loc], (cx, cy, 0), rot)[0].tolist()
            ob.rotation_euler[2] += math.radians(rot)
            ob["jf_chair"] = k
    geo.cylinder("side_table", (SOFA[0] + 1.62, SOFA[1] - 0.1, 0.0), 0.22, 0.5, g, g, m["bronze"], segs=64, bevel_w=0.003)


def _site(m):
    """Construction-stage props: two LED work lights, board stack, tile boxes."""
    g = "site"
    for k, (x, y, yaw, tilt) in enumerate([(-2.6, 3.2, 35.0, 55.0), (2.4, 7.0, 200.0, 50.0)]):
        h = 1.75
        for j in range(3):
            a = math.radians(yaw + j * 120)
            fx, fy = x + 0.42 * math.cos(a), y + 0.42 * math.sin(a)
            v = np.array([[fx, fy, 0.0], [x, y, h - 0.25]])
            d = v[1] - v[0]
            ln = float(np.linalg.norm(d))
            ob = geo.cylinder(f"work{k}_leg{j}", tuple(v[0]), 0.012, ln, g, "site", m["black"], segs=8)
            ob.rotation_mode = "QUATERNION"
            import mathutils
            ob.rotation_quaternion = mathutils.Vector((0, 0, 1)).rotation_difference(mathutils.Vector(d / ln))
        geo.cylinder(f"work{k}_pole", (x, y, h - 0.25), 0.015, 0.25, g, "site", m["black"], segs=8)
        head = geo.box(f"work{k}_head", x - 0.2, x + 0.2, y - 0.04, y + 0.04, h - 0.14, h + 0.14, g, "site", m["black"], bevel_w=0.01)
        lens = geo.box(f"work{k}_lens", x - 0.18, x + 0.18, y - 0.05, y - 0.04, h - 0.12, h + 0.12, g, "site",
                       M.get("emit", kelvin=5200.0, strength=40.0), lines="none")
        for ob in (head, lens):
            ob.rotation_mode = "XYZ"
            loc = np.array(ob.location) - np.array([x, y, h])
            ca, sa = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
            loc = np.array([loc[0], loc[1] * ca - loc[2] * sa, loc[1] * sa + loc[2] * ca])
            loc = _rot_z([loc], (0, 0, 0), yaw - 90)[0]
            ob.location = (np.array([x, y, h]) + loc).tolist()
            ob.rotation_euler = (math.radians(tilt), 0, math.radians(yaw - 90))
        lens["jf_lightgroup"] = "work"
    # pallet + plasterboard stack, tile boxes
    px, py = 3.3, 1.8
    geo.box("pallet", px - 0.6, px + 0.6, py - 1.2, py + 1.2, 0.0, 0.14, g, "site", m["timber_raw"], lines="outline")
    geo.box("board_stack", px - 0.6, px + 0.6, py - 1.2, py + 1.2, 0.14, 0.14 + 16 * 0.0125, g, "site", m["board"], lines="outline")
    for i in range(6):
        bx, by = -4.7 + (i % 3) * 0.62, 7.6 + (i // 3) * 0.42
        geo.box(f"tilebox_{i}", bx - 0.3, bx + 0.3, by - 0.2, by + 0.2, 0.0, 0.14, g, "site", m["cardboard"], bevel_w=0.004,
                lines="outline")
        geo.box(f"tilebox_top_{i}", bx - 0.3, bx + 0.3, by - 0.2, by + 0.2, 0.14, 0.28, g, "site", m["cardboard"], bevel_w=0.004,
                lines="outline") if i < 3 else None
