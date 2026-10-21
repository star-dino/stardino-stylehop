# -*- coding: utf-8 -*-
"""
Style 06 · 哥特彩窗大教堂 (Gothic Stained-Glass Cathedral × Prismatic Caustics)
Style Module & Keyframe Renderer for Gemini 4 StyleHop Showcase.

Visual & Narrative Fusion (v3 Visual Grandeur + STORY.md World-08 Narrative):
  1. Grand Leaded Gothic Rose Window & Cathedral Architecture (-10° Dutch Tilt):
     - Monumental Gothic rose window (24 outer lancet petals + 16 middle trefoil
       medallions + 12 inner rosette lobes + solar sunburst core) with deep jewel
       stained glass (sapphire, ruby, amber gold, emerald, amethyst) and backlit bloom.
     - Parallax-anchored so the Rose Window remains grandly suspended in the upper-left
       cathedral zenith throughout vertical camera ascent in `render_world`.
     - Flanking pointed Gothic lancet windows with diamond lead tracery & clustered piers.
  2. Volumetric Tyndall God-Rays & Prismatic Glass Dust:
     - Diagonal volumetric sunbeams streaming at 33° from upper-left to lower-right,
       illuminating 260+ glowing colored glass dust motes.
  3. Giant Stained-Glass Cathedral Bell, Staggered Upper-Right Chime Bells & Shockwaves:
     - Giant leaded stained-glass bell on the left (cx=520, cy=380) just struck by the Slime,
       radiating concentric stained-glass acoustic shockwave rings with 4-point star jewel
       beads and an undulating amber-gold leaded glass bell rope.
     - Two staggered stained-glass wind chime bells in the upper-right (cx=1345, cy=285
       and cx=1535, cy=175) echoing the harmonic ascent toward the dome.
  4. Lit Suspended Gothic Diamond Stained-Glass Steps & Sweeping Prismatic Light Ribbons:
     - A zig-zagging trail of lit suspended Gothic diamond stained-glass steps in the
       lower-left to mid-ground (glowing in Sapphire, Emerald, Amber Gold, Ruby, and Cyan),
       leading up to the Giant Bell and launching into sweeping multi-layered translucent
       rainbow prismatic light ribbons (Sweeping Prismatic Light Ribbons).
  5. Voronoi 28-Pane Leaded Stained-Glass Slime & 4-Facet Stained-Glass Star (✦):
     - Plump spherical slime (diameter ~136px, R=68) built from 28 Voronoi stained-glass
       panes with 3.2px dark charcoal lead cames & 1px warm metallic specular highlights.
     - Brand jewel gradient: Cobalt/Sky Blue (top-left) -> Amethyst Violet (mid) ->
       Ruby Coral & Amber (bottom-right).
     - Mouthless, with two pure-white opalescent milk-glass capsule eyes (-30° cant,
       far eye 81% width, framed by lead cames).
     - Leading 4-facet diamond-cut stained-glass Star (✦) hovering ahead on the light bridge.
"""

import os
import math
import time
import random
import numpy as np
import cairo
from PIL import Image
from scipy.spatial import Voronoi

W, H = 1920, 1080
WORLD_W, WORLD_H = 1920, 3240
OUT_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style_06_stainedglass.png")


# ---------------------------------------------------------------------------
# Precomputed 28-Cell Voronoi Tessellation in Normalized Slime Coordinates (R=1.0)
# ---------------------------------------------------------------------------
def _build_voronoi_slime_cells():
    """
    Constructs the exact 28 internal Voronoi cells from v3:
      - Layer 0 (center nucleus): 1 seed
      - Layer 1 (inner petals):   6 seeds at r = 0.33
      - Layer 2 (middle petals):  9 seeds at r = 0.64
      - Layer 3 (outer petals):  12 seeds at r = 0.92
      - Guard ring:              16 seeds at r = 1.65 (ensures finite polygons)
    """
    seeds = [(0.0, 0.0)]
    for i in range(6):
        th = i * (math.tau / 6.0) + 0.22
        seeds.append((0.33 * math.cos(th), 0.33 * math.sin(th)))
    for i in range(9):
        th = i * (math.tau / 9.0) + 0.14
        seeds.append((0.64 * math.cos(th), 0.64 * math.sin(th)))
    for i in range(12):
        th = i * (math.tau / 12.0) + 0.28
        seeds.append((0.92 * math.cos(th), 0.92 * math.sin(th)))
    for i in range(16):
        th = i * (math.tau / 16.0)
        seeds.append((1.65 * math.cos(th), 1.65 * math.sin(th)))

    vor = Voronoi(np.array(seeds))
    cells = []
    for idx in range(28):
        reg = vor.regions[vor.point_region[idx]]
        if -1 in reg or len(reg) < 3:
            continue
        verts = [(float(vor.vertices[vi][0]), float(vor.vertices[vi][1])) for vi in reg]
        sx_seed, sy_seed = seeds[idx]
        cells.append({
            "seed": (float(sx_seed), float(sy_seed)),
            "verts": verts,
        })
    return cells


_VORONOI_SLIME_CELLS = _build_voronoi_slime_cells()


# ---------------------------------------------------------------------------
# Core Geometry Helpers (100% faithful to v3 slime_engine)
# ---------------------------------------------------------------------------
def _compute_slime_contour(cx: float, cy: float, radius: float, squash_y: float = 1.0,
                           tilt: float = 0.0, phase: float = 0.0, n_pts: int = 120,
                           look_x: float = 0.0, look_y: float = 0.0, grounded: bool = False):
    sy = max(0.45, min(2.2, squash_y))
    sx = 1.0 / math.sqrt(sy)
    R = radius
    pts = []
    gx = max(-1.1, min(1.1, float(look_x)))
    gy = max(-1.1, min(1.1, float(look_y)))
    coupled_tilt = tilt + gx * 0.065 - gy * 0.028 * (1.0 if gx >= 0.0 else -1.0)
    cos_t = math.cos(coupled_tilt)
    sin_t = math.sin(coupled_tilt)

    # Soft-body bottom flattening when squashed or grounded (like Clay & Blueprint worlds)
    squash_amount = max(0.0, 1.0 - sy)
    flat_factor = min(1.0, squash_amount * 2.2 + (0.18 if grounded and sy <= 1.02 else 0.0))

    for i in range(n_pts):
        th = (i / n_pts) * math.tau
        s = math.sin(th)
        c = math.cos(th)
        upper_weight = ((1.0 - s) * 0.5) ** 1.40
        lower_belly = max(0.0, s) * (1.0 - max(0.0, s) * 0.35)

        cheek_bias = 1.0 + 0.055 * gx * c * (1.0 - 0.40 * abs(s))
        # Plump organic teardrop width: wider at lower cheeks when squashed, sleeker at crown when stretched
        stretch_taper = 1.0 - max(0.0, sy - 1.0) * 0.22 * upper_weight
        width_mod = (1.02 + 0.065 * lower_belly + 0.14 * squash_amount * (s ** 2) - 0.015 * (s ** 2)) * cheek_bias * stretch_taper

        # Flatten the bottom contact arc smoothly so it sits flush on crystal platforms
        raw_y = s
        if s > 0.0 and flat_factor > 0.0:
            limit_y = 0.96 - 0.10 * squash_amount
            if raw_y > limit_y * (1.0 - 0.25 * flat_factor):
                raw_y = raw_y * (1.0 - 0.45 * flat_factor) + limit_y * (0.45 * flat_factor)
        height_mod = 0.992 - 0.032 * (max(0.0, s) ** 2.2)

        ripple = R * 0.004 * math.sin(3 * th + phase) + R * 0.003 * math.cos(4 * th - phase * 1.2)

        crown_lean_x = R * gx * 0.155 * upper_weight * sx
        crown_lift_y = R * gy * 0.115 * upper_weight * sy

        lx = (R * width_mod + ripple) * c * sx + crown_lean_x
        ly = (R * height_mod * raw_y + ripple * s) * sy + crown_lift_y

        rx = lx * cos_t - ly * sin_t
        ry = lx * sin_t + ly * cos_t
        pts.append((cx + rx, cy + ry))
    return pts


def _draw_slime_path(ctx: cairo.Context, pts: list):
    ctx.new_path()
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        if i == 0:
            ctx.move_to(mx, my)
        else:
            ctx.curve_to(x0, y0, x0, y0, mx, my)
    ctx.close_path()


def _draw_four_point_star_path(ctx: cairo.Context, cx: float, cy: float,
                               outer_r: float, inner_r: float = None, rot: float = 0.0):
    if inner_r is None:
        inner_r = outer_r * 0.26
    ctx.new_path()
    tips = []
    waists = []
    for i in range(4):
        ang_tip = rot + i * (math.pi / 2.0) - math.pi / 2.0
        ang_waist = ang_tip + math.pi / 4.0
        tips.append((cx + outer_r * math.cos(ang_tip), cy + outer_r * math.sin(ang_tip)))
        waists.append((cx + inner_r * math.cos(ang_waist), cy + inner_r * math.sin(ang_waist)))

    ctx.move_to(tips[0][0], tips[0][1])
    for i in range(4):
        wx, wy = waists[i]
        nx, ny = tips[(i + 1) % 4]
        ctx.curve_to(wx, wy, wx, wy, nx, ny)
    ctx.close_path()


def _draw_capsule_pill(ctx: cairo.Context, cx: float, cy: float, half_w: float, half_h: float):
    w = max(1.2, half_w)
    h = max(1.2, half_h)
    ctx.new_path()
    if h >= w:
        dy = h - w
        ctx.arc(cx, cy - dy, w, math.pi, 0.0)
        ctx.arc(cx, cy + dy, w, 0.0, math.pi)
    else:
        dx = w - h
        ctx.arc(cx + dx, cy, h, -math.pi * 0.5, math.pi * 0.5)
        ctx.arc(cx - dx, cy, h, math.pi * 0.5, math.pi * 1.5)
    ctx.close_path()


# ---------------------------------------------------------------------------
# API Contract Function: draw_star
# ---------------------------------------------------------------------------
def draw_star(ctx: cairo.Context, cx: float, cy: float, r: float, *,
              rot: float = 0.0, t: float = 0.0, **style_kw):
    """
    Renders the 4-Point Concave Stained-Glass Star (✦) built from 4 diamond-cut
    jewel glass facets (Cyan, Amber Gold, Ruby Coral, Amethyst Violet) with dark
    charcoal solder lead cames, golden solder nucleus, and prismatic starlight halo.
    """
    if r <= 0.5:
        return
    ctx.save()

    # 1. Radiant Prismatic Starlight Bloom Halo
    st_halo = cairo.RadialGradient(cx, cy, max(1.0, r * 0.08), cx, cy, r * 2.35)
    st_halo.add_color_stop_rgba(0.0, 1.00, 0.96, 0.78, 0.88)
    st_halo.add_color_stop_rgba(0.38, 0.35, 0.76, 1.00, 0.48)
    st_halo.add_color_stop_rgba(0.72, 0.88, 0.38, 0.68, 0.22)
    st_halo.add_color_stop_rgba(1.0, 0.85, 0.35, 0.65, 0.0)
    ctx.set_source(st_halo)
    ctx.arc(cx, cy, r * 2.35, 0, math.tau)
    ctx.fill()

    # 2. Four Diamond-Cut Glass Facets Meeting at Center
    tips = []
    waists = []
    r_inner = r * 0.26
    for i in range(4):
        ang_tip = rot + i * (math.pi * 0.5) - math.pi * 0.5
        ang_waist = ang_tip + math.pi * 0.25
        tips.append((cx + r * math.cos(ang_tip), cy + r * math.sin(ang_tip)))
        waists.append((cx + r_inner * math.cos(ang_waist), cy + r_inner * math.sin(ang_waist)))

    facet_colors = [
        ((0.24, 0.76, 0.98), (0.14, 0.50, 0.88)),  # Top Cyan (#38BDF8)
        ((0.99, 0.76, 0.16), (0.92, 0.54, 0.08)),  # Right Amber Gold (#FBBF24)
        ((0.96, 0.26, 0.38), (0.82, 0.14, 0.28)),  # Bottom Ruby Coral (#F43F5E)
        ((0.58, 0.38, 0.96), (0.40, 0.22, 0.82)),  # Left Amethyst Violet (#8B5CF6)
    ]

    for i in range(4):
        c_light, c_dark = facet_colors[i]
        p_tip = tips[i]
        p_w_next = waists[i]
        p_w_prev = waists[(i - 1) % 4]

        # Left half of diamond facet
        ctx.new_path()
        ctx.move_to(cx, cy)
        ctx.line_to(p_w_prev[0], p_w_prev[1])
        ctx.curve_to(p_w_prev[0], p_w_prev[1], p_w_prev[0], p_w_prev[1], p_tip[0], p_tip[1])
        ctx.close_path()
        ctx.set_source_rgba(c_light[0], c_light[1], c_light[2], 0.96)
        ctx.fill()

        # Right half of diamond facet
        ctx.new_path()
        ctx.move_to(cx, cy)
        ctx.line_to(p_tip[0], p_tip[1])
        ctx.curve_to(p_w_next[0], p_w_next[1], p_w_next[0], p_w_next[1], p_w_next[0], p_w_next[1])
        ctx.close_path()
        ctx.set_source_rgba(c_dark[0], c_dark[1], c_dark[2], 0.96)
        ctx.fill()

    # 3. Outer Leaded Border around Concave Star
    lw_outer = max(2.2, min(3.6, r * 0.095))
    _draw_four_point_star_path(ctx, cx, cy, r, r_inner, rot=rot)
    ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
    ctx.set_line_width(lw_outer)
    ctx.stroke()

    # 4. Dividing Lead Seam Lines Meeting at Center
    lw_inner = max(1.5, min(2.4, r * 0.062))
    for i in range(4):
        ctx.move_to(cx, cy)
        ctx.line_to(tips[i][0], tips[i][1])
        ctx.set_source_rgba(0.08, 0.09, 0.12, 0.96)
        ctx.set_line_width(lw_inner)
        ctx.stroke()

    # 5. Golden Solder Nucleus at Star Center
    nuc_r = max(2.4, r * 0.095)
    ctx.arc(cx, cy, nuc_r, 0, math.tau)
    ctx.set_source_rgba(1.0, 0.94, 0.68, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
    ctx.set_line_width(max(1.0, r * 0.035))
    ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# API Contract Function: draw_slime
# ---------------------------------------------------------------------------
def draw_slime(ctx: cairo.Context, cx: float, cy: float, radius: float, *,
               squash_y: float = 1.0, tilt: float = 0.0, look=(0.0, 0.0),
               eye_mode: str = "pill", blink: float = 0.0, t: float = 0.0, **style_kw):
    """
    Renders the Star-Spark Slime natively as ~28 hard-faceted interlocking Voronoi
    stained-glass crystal panes separated by bold dark lead cames with prism specular glints.
      - Volume-preserving squash & stretch: sx = 1 / sqrt(squash_y), with organic bottom flattening.
      - True 3D spherical/dome projection of the 28 Voronoi facets driven by head yaw/pitch & roll.
      - MOUTHLESS: Two pure-white opalescent milk-glass rounded capsule eyes
        (dynamic 3D spherical foreshortening, symmetrical when look_x == 0).
    """
    R = float(radius)
    sy = max(0.45, min(2.2, float(squash_y)))
    sx = 1.0 / math.sqrt(sy)
    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)

    if isinstance(look, (tuple, list)) and len(look) >= 2:
        look_x, look_y = float(look[0]), float(look[1])
    else:
        look_x, look_y = -0.44, -0.16

    eye_scale = float(style_kw.get("eye_scale", 1.08))
    eye_spacing = float(style_kw.get("eye_spacing", 1.02))
    star_scale = float(style_kw.get("star_scale", 1.08))
    draw_crown_star = bool(style_kw.get("draw_crown_star", False))
    roll_angle = float(style_kw.get("roll_angle", 0.0))
    grounded = bool(style_kw.get("grounded", sy <= 1.02))

    pts = _compute_slime_contour(
        cx, cy, R, squash_y=sy, tilt=tilt, phase=t * 2.0, n_pts=120,
        look_x=look_x, look_y=look_y, grounded=grounded,
    )

    # 1. Soft Floor / Bridge Contact Glow & Jewel Caustic Pool
    if style_kw.get("draw_shadow", True):
        sh_x = cx
        sh_y = cy + R * sy * 0.96
        ctx.save()
        ctx.translate(sh_x, sh_y)
        ctx.scale(R * sx * 1.25, R * 0.28)
        c_pool = cairo.RadialGradient(0, 0, 0.05, 0, 0, 1.0)
        c_pool.add_color_stop_rgba(0.0, 0.62, 0.38, 0.92, 0.56)  # Jewel purple-cyan pool
        c_pool.add_color_stop_rgba(0.55, 0.25, 0.52, 0.98, 0.30)
        c_pool.add_color_stop_rgba(1.0, 0.10, 0.15, 0.35, 0.0)
        ctx.set_source(c_pool)
        ctx.arc(0, 0, 1.0, 0, math.tau)
        ctx.fill()
        ctx.restore()

    gx_clamped = max(-1.1, min(1.1, look_x))
    gy_clamped = max(-1.1, min(1.1, look_y))
    coupled_tilt = tilt + gx_clamped * 0.065 - gy_clamped * 0.028 * (1.0 if gx_clamped >= 0.0 else -1.0)
    cos_ct = math.cos(coupled_tilt)
    sin_ct = math.sin(coupled_tilt)

    # 3D Spherical / Crystal Dome Rotation of Voronoi Facets
    cos_r = math.cos(roll_angle * 0.28)
    sin_r = math.sin(roll_angle * 0.28)
    squash_amt = max(0.0, 1.0 - sy)

    def to_global(ux: float, uy: float):
        # 1) Subtle 2D roll of Voronoi lattice
        rx0 = ux * cos_r - uy * sin_r
        ry0 = ux * sin_r + uy * cos_r
        # 2) 3D spherical dome shift: stronger at center (r=0), anchored at outer rim so panes cover 100% of contour
        r_norm = min(1.0, math.hypot(rx0, ry0) / 1.15)
        dome_weight = 1.0 - r_norm * r_norm * 0.65
        ux_s = rx0 + gx_clamped * 0.28 * dome_weight
        uy_s = ry0 + gy_clamped * 0.22 * dome_weight
        # 3) Organic lower-cheek bulge when squashed
        belly_w = 1.0 + 0.14 * squash_amt * max(0.0, uy_s)
        lx = ux_s * R * sx * belly_w
        ly = uy_s * R * sy
        gx = cx + lx * cos_ct - ly * sin_ct
        gy = cy + lx * sin_ct + ly * cos_ct
        return gx, gy

    # 2. Clip All 28 Internal Voronoi Glass Panes Strictly Inside Slime Contour
    ctx.save()
    _draw_slime_path(ctx, pts)
    ctx.clip()

    def get_pane_color(u: float):
        u = max(0.0, min(1.0, u))
        if u < 0.32:
            # Cobalt / Sky Blue (#4FADFF -> #2563EB)
            f = u / 0.32
            c0 = np.array([0.31, 0.68, 1.00])  # #4FADFF
            c1 = np.array([0.15, 0.39, 0.92])  # #2563EB
            return c0 * (1.0 - f) + c1 * f
        elif u < 0.68:
            # Amethyst Violet (#7C3AED -> #9B72CB)
            f = (u - 0.32) / 0.36
            c0 = np.array([0.15, 0.39, 0.92])  # #2563EB
            c1 = np.array([0.49, 0.23, 0.93])  # #7C3AED
            c2 = np.array([0.61, 0.45, 0.80])  # #9B72CB
            if f < 0.5:
                return c0 * (1.0 - f * 2.0) + c1 * (f * 2.0)
            else:
                return c1 * (1.0 - (f - 0.5) * 2.0) + c2 * ((f - 0.5) * 2.0)
        else:
            # Ruby Coral & Amber (#D96570 -> #F59E0B)
            f = (u - 0.68) / 0.32
            c0 = np.array([0.85, 0.40, 0.44])  # #D96570
            c1 = np.array([0.96, 0.62, 0.08])  # #F59E0B
            return c0 * (1.0 - f) + c1 * f

    came_lw = max(2.5, min(3.8, R * 0.044))
    spec_lw = max(0.9, min(1.3, R * 0.015))

    for cell_idx, cell in enumerate(_VORONOI_SLIME_CELLS):
        su, sv = cell["seed"]
        seed_gx, seed_gy = to_global(su, sv)
        u_diag = ((su + sv) / 2.0) * 0.5 + 0.5

        poly_pts = [to_global(vx, vy) for vx, vy in cell["verts"]]
        ctx.new_path()
        ctx.move_to(poly_pts[0][0], poly_pts[0][1])
        for p in poly_pts[1:]:
            ctx.line_to(p[0], p[1])
        ctx.close_path()

        base_rgb = get_pane_color(u_diag)
        # Dynamic prism facet shimmer as Slime turns/squashes
        facet_shimmer = 0.08 * math.sin(t * 3.8 + cell_idx * 0.7 + gx_clamped * 3.0 + roll_angle)
        pane_g = cairo.RadialGradient(
            seed_gx - R * 0.04, seed_gy - R * 0.05, max(1.5, R * 0.02),
            seed_gx, seed_gy, R * 0.45
        )
        pane_g.add_color_stop_rgba(
            0.0,
            min(1.0, float(base_rgb[0]) + 0.38 + facet_shimmer),
            min(1.0, float(base_rgb[1]) + 0.38 + facet_shimmer),
            min(1.0, float(base_rgb[2]) + 0.38 + facet_shimmer),
            0.98,
        )
        pane_g.add_color_stop_rgba(0.65, float(base_rgb[0]), float(base_rgb[1]), float(base_rgb[2]), 0.95)
        pane_g.add_color_stop_rgba(
            1.0,
            float(base_rgb[0]) * 0.52,
            float(base_rgb[1]) * 0.52,
            float(base_rgb[2]) * 0.52,
            0.98,
        )
        ctx.set_source(pane_g)
        ctx.fill_preserve()

        # Hard-Facet Internal Prism Slash Glint on upper-left facets
        if su + sv < 0.25 and (cell_idx % 2 == 0):
            ctx.save()
            ctx.clip_preserve()
            ctx.new_path()
            ctx.move_to(seed_gx - R * 0.22, seed_gy + R * 0.08)
            ctx.line_to(seed_gx + R * 0.14, seed_gy - R * 0.22)
            ctx.line_to(seed_gx + R * 0.22, seed_gy - R * 0.14)
            ctx.line_to(seed_gx - R * 0.14, seed_gy + R * 0.16)
            ctx.close_path()
            ctx.set_source_rgba(1.0, 0.98, 0.92, 0.24 + max(0.0, facet_shimmer))
            ctx.fill()
            ctx.restore()

        # Bold dark charcoal lead came between panes
        ctx.set_source_rgba(0.09, 0.10, 0.13, 0.98)
        ctx.set_line_width(came_lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()

        # Warm metallic specular highlight on top/left edges of each pane
        ctx.new_path()
        n_p = len(poly_pts)
        for pi in range(n_p):
            p_a = poly_pts[pi]
            p_b = poly_pts[(pi + 1) % n_p]
            nx = -(p_b[1] - p_a[1])
            ny = (p_b[0] - p_a[0])
            if (nx * (-0.7) + ny * (-0.7)) > 0:
                ctx.move_to(p_a[0], p_a[1])
                ctx.line_to(p_b[0], p_b[1])
        ctx.set_source_rgba(0.98, 0.92, 0.80, 0.62)
        ctx.set_line_width(spec_lw)
        ctx.stroke()

    # Subtle internal lead solder beads at Voronoi vertices
    bead_r = max(1.4, min(2.2, R * 0.025))
    for cell in _VORONOI_SLIME_CELLS:
        for vx, vy in cell["verts"]:
            gx, gy = to_global(vx, vy)
            ctx.arc(gx, gy, bead_r, 0, math.tau)
            ctx.set_source_rgba(0.18, 0.19, 0.23, 0.90)
            ctx.fill()

    ctx.restore()  # End slime clip

    # 3. Outer Contour: Heavy Lead Border & Sunlit Rim Highlight
    outer_lw = max(3.8, min(5.0, R * 0.056))
    _draw_slime_path(ctx, pts)
    ctx.set_source_rgba(0.07, 0.08, 0.11, 1.0)
    ctx.set_line_width(outer_lw)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()

    _draw_slime_path(ctx, pts)
    rim_g = cairo.LinearGradient(cx - R * sx, cy - R * sy, cx + R * sx, cy + R * sy)
    rim_g.add_color_stop_rgba(0.0, 0.98, 0.92, 0.82, 0.80)
    rim_g.add_color_stop_rgba(0.4, 0.45, 0.72, 1.00, 0.38)
    rim_g.add_color_stop_rgba(1.0, 0.20, 0.10, 0.30, 0.0)
    ctx.set_source(rim_g)
    ctx.set_line_width(max(1.5, R * 0.022))
    ctx.stroke()

    # 4. MOUTHLESS: Two Pure-White Opalescent Milk-Glass Rounded Capsule Eyes
    # C-infinity 3D spherical eye foreshortening:
    # - look_x < 0: 左小右大; look_x == 0 (or pure up/down): 居中完全一样大 & cant=0; look_x > 0: 左大右小!
    gx_c = max(-1.15, min(1.15, look_x))
    gy_c = max(-1.15, min(1.15, look_y))
    yaw = gx_c * 0.85
    pitch = gy_c * 0.68
    lon_L = yaw - 0.32
    lon_R = yaw + 0.32
    cos_L = max(0.45, math.cos(lon_L * 1.08))
    cos_R = max(0.45, math.cos(lon_R * 1.08))
    max_cos = max(cos_L, cos_R, 1e-6)
    pitch_h = max(0.76, math.cos(pitch * 0.60))
    pitch_arch = -math.sin(pitch) * R * 0.055 * sy

    gaze_cx = math.sin(yaw) * R * 0.52 * sx
    gaze_cy = math.sin(pitch) * R * 0.46 * sy
    cant_angle = gx_c * (-0.28 + 0.42 * gy_c)
    cos_c, sin_c = math.cos(cant_angle), math.sin(cant_angle)

    base_sep = R * 0.22 * eye_spacing * max(0.56, math.cos(yaw * 0.72))
    w_base = R * 0.118 * eye_scale
    h_base = R * 0.258 * eye_scale * max(0.10, 1.0 - float(blink) * 0.90)

    for side in (-1, +1):
        c_eye = cos_L if side == -1 else cos_R
        persp_w = c_eye / max_cos
        persp_h = (0.82 + 0.18 * persp_w) * pitch_h
        local_dx = side * base_sep * (0.72 + 0.28 * persp_w)
        local_dy = pitch_arch * (1.0 - persp_w)

        ex_sphere = gaze_cx + local_dx * cos_c - local_dy * sin_c
        ey_sphere = gaze_cy + local_dx * sin_c + local_dy * cos_c
        ex = cx + ex_sphere * cos_ct - ey_sphere * sin_ct
        ey = cy + ex_sphere * sin_ct + ey_sphere * cos_ct

        w_eye = w_base * persp_w
        h_eye = h_base * persp_h
        if eye_mode == "surprised":
            w_eye *= 1.16
            h_eye *= 1.18
        elif eye_mode in ("charge", "sharp"):
            h_eye *= 0.72

        ctx.save()
        ctx.translate(ex, ey)
        ctx.rotate(coupled_tilt + cant_angle + side * gx_c * 0.03)

        if eye_mode in ("happy", "happy_arc") or (eye_mode == "wink_right" and side == 1):
            arc_r = h_eye * 0.82
            arc_lw = max(2.8, w_eye * 1.45)
            ctx.new_path()
            ctx.arc(0, arc_r * 0.35, arc_r, math.pi * 1.15, math.pi * 1.85)
            ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
            ctx.set_line_width(arc_lw + 3.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgba(0.98, 0.99, 1.0, 1.0)
            ctx.set_line_width(arc_lw)
            ctx.stroke()
        elif eye_mode in ("wince", "charge"):
            # > < Stained-glass effort/impact chevron eyes (left eye >, right eye <)
            dir_s = -side
            cw = w_eye * 1.35
            ch = h_eye * 0.68
            lw = max(2.8, w_eye * 1.25)
            ctx.new_path()
            ctx.move_to(-dir_s * cw * 0.65, -ch * 0.65)
            ctx.line_to(dir_s * cw * 0.55, 0.0)
            ctx.line_to(-dir_s * cw * 0.65, ch * 0.65)
            ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
            ctx.set_line_width(lw + 3.4)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgba(0.98, 0.99, 1.0, 1.0)
            ctx.set_line_width(lw)
            ctx.stroke()
        elif eye_mode == "star":
            lead_pad = max(2.2, R * 0.028)
            _draw_four_point_star_path(ctx, 0, 0, h_eye * 1.15 + lead_pad, (h_eye * 1.15 + lead_pad) * 0.32)
            ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
            ctx.fill()
            _draw_four_point_star_path(ctx, 0, 0, h_eye * 1.12, h_eye * 0.32)
            ctx.set_source_rgba(1.0, 0.97, 0.80, 1.0)
            ctx.fill()
        else:
            # A. Lead Came Framing around Capsule Eye
            lead_pad = max(2.2, R * 0.028)
            _draw_capsule_pill(ctx, 0, 0, w_eye + lead_pad, h_eye + lead_pad)
            ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
            ctx.fill()

            # B. Pure-White Opalescent Milk-Glass Fill
            _draw_capsule_pill(ctx, 0, 0, w_eye, h_eye)
            milk_g = cairo.RadialGradient(-w_eye * 0.25, -h_eye * 0.35, 1.0, 0, 0, h_eye)
            milk_g.add_color_stop_rgba(0.0, 1.00, 1.00, 1.00, 1.00)
            milk_g.add_color_stop_rgba(0.55, 0.97, 0.98, 1.00, 1.00)
            milk_g.add_color_stop_rgba(0.85, 0.94, 0.92, 0.96, 1.00)
            milk_g.add_color_stop_rgba(1.0, 0.86, 0.84, 0.90, 1.00)
            ctx.set_source(milk_g)
            ctx.fill_preserve()

            # C. Inner opalescent specular glint
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.88)
            ctx.set_line_width(1.0)
            ctx.stroke()

            # Metallic lead came specular highlight on eye frame
            ctx.arc(-w_eye * 0.8, -h_eye * 0.6, max(1.4, R * 0.018), 0, math.tau)
            ctx.set_source_rgba(1.0, 0.94, 0.82, 0.92)
            ctx.fill()

        ctx.restore()

    # 5. Optional Overhead Crown Star (✦)
    if draw_crown_star:
        crown_local_y = -R * sy * 1.34
        star_cx = cx - crown_local_y * sin_t
        star_cy = cy + crown_local_y * cos_t
        star_r = R * 0.28 * star_scale
        draw_star(ctx, star_cx, star_cy, star_r, rot=0.0, t=t)

        crown_pt_x = cx - (-R * sy * 0.95) * sin_t
        crown_pt_y = cy + (-R * sy * 0.95) * cos_t
        for t_step, r_dot in [(0.35, max(1.6, R * 0.022)), (0.70, max(2.0, R * 0.026))]:
            mx = crown_pt_x + (star_cx - crown_pt_x) * t_step
            my = crown_pt_y + (star_cy - crown_pt_y) * t_step
            ctx.arc(mx, my, r_dot, 0, math.tau)
            ctx.set_source_rgba(1.0, 0.92, 0.65, 0.88)
            ctx.fill()


# ---------------------------------------------------------------------------
# Cathedral Background & Grand Leaded Gothic Rose Window (-10° Dutch Tilt)
# ---------------------------------------------------------------------------
def create_cathedral_background(ctx: cairo.Context, parallax_rose_y: float = 0.0, parallax_bg_y: float = 0.0):
    """
    Renders Gothic cathedral interior under a dramatic -10 deg Dutch tilt:
    Vaulted ceiling, stone columns, pointed lancet windows, grand rose window,
    and stone flagstone floor with prismatic caustics.
    """
    # 1. Base cathedral ambiance: deep obsidian stone with atmospheric midnight indigo
    bg_grad = cairo.LinearGradient(0, 0, W * 0.35, H)
    bg_grad.add_color_stop_rgb(0.0, 0.024, 0.028, 0.046)
    bg_grad.add_color_stop_rgb(0.6, 0.018, 0.022, 0.038)
    bg_grad.add_color_stop_rgb(1.0, 0.012, 0.014, 0.025)
    ctx.set_source(bg_grad)
    ctx.paint()

    # Apply Dutch-tilt camera rotation (-10 degrees) for the architectural framework
    ctx.save()
    tilt_rad = -10.0 * math.pi / 180.0
    ctx.translate(W * 0.5, H * 0.5)
    ctx.rotate(tilt_rad)
    ctx.translate(-W * 0.5, -H * 0.5)

    # 2. Cathedral Stone Floor (Flagstones in perspective at the bottom)
    floor_y = 780 + parallax_bg_y * 0.45
    floor_g = cairo.LinearGradient(0, floor_y, 0, H + 300)
    floor_g.add_color_stop_rgba(0.0, 0.030, 0.035, 0.055, 0.95)
    floor_g.add_color_stop_rgba(1.0, 0.015, 0.018, 0.028, 0.98)
    ctx.set_source(floor_g)
    ctx.rectangle(-250, floor_y, W + 500, H - floor_y + 400)
    ctx.fill()

    # Perspective flagstone mortar lines
    ctx.set_source_rgba(0.08, 0.09, 0.14, 0.72)
    ctx.set_line_width(2.0)
    for fx in range(-200, W + 400, 160):
        ctx.move_to(fx, floor_y)
        ctx.line_to(fx * 1.35 - 300, H + 300)
    for fy in range(int(floor_y) + 40, H + 300, 60):
        ctx.move_to(-250, fy)
        ctx.line_to(W + 250, fy)
    ctx.stroke()

    # 3. Cathedral Pillars & Clustered Shafts
    pillar_specs = [
        (-140, 110),   # Far left exterior pillar
        (130, 95),     # Mid left belfry pillar
        (1580, 110),   # Mid right nave pillar
        (1880, 120),   # Far right exterior pillar
    ]
    for px, pw in pillar_specs:
        p_grad = cairo.LinearGradient(px, 0, px + pw, 0)
        p_grad.add_color_stop_rgba(0.0, 0.06, 0.07, 0.11, 0.98)
        p_grad.add_color_stop_rgba(0.28, 0.15, 0.17, 0.24, 0.98)
        p_grad.add_color_stop_rgba(0.72, 0.08, 0.09, 0.13, 0.98)
        p_grad.add_color_stop_rgba(1.0, 0.03, 0.04, 0.06, 0.98)
        ctx.set_source(p_grad)
        ctx.rectangle(px, -300, pw, H + 600)
        ctx.fill()

        # Vertical stone shaft moldings
        for mx in [px + pw * 0.18, px + pw * 0.45, px + pw * 0.75]:
            ctx.set_source_rgba(0.22, 0.25, 0.35, 0.45)
            ctx.set_line_width(2.2)
            ctx.move_to(mx, -300)
            ctx.line_to(mx, H + 600)
            ctx.stroke()

        # Pillar capital and base stone rings
        for cap_y in [180 + parallax_bg_y * 0.35, 780 + parallax_bg_y * 0.45]:
            ctx.rectangle(px - 10, cap_y, pw + 20, 22)
            ctx.set_source_rgba(0.12, 0.14, 0.19, 0.98)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.25, 0.28, 0.38, 0.6)
            ctx.set_line_width(2.0)
            ctx.stroke()

    # 4. Pointed Gothic Lancet Windows (Background Side Aisles)
    for lcx, lcy_base, lw, lh in [(30, 260, 150, 480), (1740, 240, 150, 480)]:
        lcy = lcy_base + parallax_bg_y * 0.30
        ctx.save()
        ctx.new_path()
        ctx.move_to(lcx - lw * 0.5, lcy + lh * 0.5)
        ctx.line_to(lcx - lw * 0.5, lcy - lh * 0.1)
        ctx.curve_to(lcx - lw * 0.5, lcy - lh * 0.48, lcx - lw * 0.1, lcy - lh * 0.56, lcx, lcy - lh * 0.56)
        ctx.curve_to(lcx + lw * 0.1, lcy - lh * 0.56, lcx + lw * 0.5, lcy - lh * 0.48, lcx + lw * 0.5, lcy - lh * 0.1)
        ctx.line_to(lcx + lw * 0.5, lcy + lh * 0.5)
        ctx.close_path()
        ctx.clip()

        # Stained glass color wash
        lg = cairo.LinearGradient(lcx, lcy - lh * 0.5, lcx, lcy + lh * 0.5)
        lg.add_color_stop_rgba(0.0, 0.12, 0.45, 0.88, 0.78)  # Sapphire blue
        lg.add_color_stop_rgba(0.5, 0.48, 0.18, 0.72, 0.78)  # Amethyst
        lg.add_color_stop_rgba(1.0, 0.82, 0.22, 0.38, 0.78)  # Ruby coral
        ctx.set_source(lg)
        ctx.paint()

        # Leaded diamond tracery grid
        ctx.set_source_rgba(0.07, 0.08, 0.11, 0.88)
        ctx.set_line_width(2.5)
        spacing = 30
        for diag in range(-350, 650, spacing):
            ctx.move_to(lcx - lw, lcy + diag)
            ctx.line_to(lcx + lw, lcy + diag + lw * 1.35)
            ctx.move_to(lcx + lw, lcy + diag)
            ctx.line_to(lcx - lw, lcy + diag + lw * 1.35)
        ctx.stroke()
        ctx.restore()

        # Stone arch frame around lancet
        ctx.new_path()
        ctx.move_to(lcx - lw * 0.5, lcy + lh * 0.5)
        ctx.line_to(lcx - lw * 0.5, lcy - lh * 0.1)
        ctx.curve_to(lcx - lw * 0.5, lcy - lh * 0.48, lcx - lw * 0.1, lcy - lh * 0.56, lcx, lcy - lh * 0.56)
        ctx.curve_to(lcx + lw * 0.1, lcy - lh * 0.56, lcx + lw * 0.5, lcy - lh * 0.48, lcx + lw * 0.5, lcy - lh * 0.1)
        ctx.line_to(lcx + lw * 0.5, lcy + lh * 0.5)
        ctx.set_source_rgba(0.09, 0.10, 0.15, 0.98)
        ctx.set_line_width(14.0)
        ctx.stroke()

    # 5. Grand Leaded Gothic Rose Window (巨型哥特铅条玫瑰花窗)
    # Positioned high in cathedral zenith: center (780, 60 + parallax_rose_y), radius 420
    rose_cx = 780.0
    rose_cy = 60.0 + parallax_rose_y
    rose_r = 420.0

    # Backlit stained-glass radiant illumination bloom
    bloom = cairo.RadialGradient(rose_cx, rose_cy, rose_r * 0.08, rose_cx, rose_cy, rose_r * 1.48)
    bloom.add_color_stop_rgba(0.0, 1.00, 0.94, 0.80, 0.92)   # Radiant solar amber core
    bloom.add_color_stop_rgba(0.32, 0.35, 0.68, 1.00, 0.68)  # Luminous sapphire glow
    bloom.add_color_stop_rgba(0.68, 0.65, 0.28, 0.88, 0.40)  # Amethyst violet halo
    bloom.add_color_stop_rgba(1.0, 0.10, 0.12, 0.25, 0.0)
    ctx.set_source(bloom)
    ctx.arc(rose_cx, rose_cy, rose_r * 1.48, 0, math.tau)
    ctx.fill()

    gem_palette = [
        (0.08, 0.32, 0.78),  # Deep Sapphire (#1452C7)
        (0.85, 0.14, 0.20),  # Grand Cathedral Ruby (#D92433)
        (0.98, 0.68, 0.09),  # Imperial Amber Gold (#FAA817)
        (0.03, 0.56, 0.34),  # Chartres Emerald (#088F57)
        (0.52, 0.20, 0.82),  # Royal Amethyst (#8533D1)
        (0.20, 0.72, 0.92),  # Sky Turquoise (#33B8EB)
        (0.94, 0.36, 0.42),  # Rose Coral (#F05C6B)
    ]

    # --- Outer Ring (24 Gothic Stained-Glass Lancet Petals) ---
    n_outer = 24
    r_out_1, r_out_2 = rose_r * 0.68, rose_r * 0.96
    for i in range(n_outer):
        a1 = (i / n_outer) * math.tau
        a2 = ((i + 0.93) / n_outer) * math.tau
        amid = (a1 + a2) * 0.5

        p1 = (rose_cx + r_out_1 * math.cos(a1), rose_cy + r_out_1 * math.sin(a1))
        p2 = (rose_cx + r_out_2 * math.cos(a1 + 0.01), rose_cy + r_out_2 * math.sin(a1 + 0.01))
        ptip = (rose_cx + (r_out_2 + 15) * math.cos(amid), rose_cy + (r_out_2 + 15) * math.sin(amid))
        p3 = (rose_cx + r_out_2 * math.cos(a2 - 0.01), rose_cy + r_out_2 * math.sin(a2 - 0.01))
        p4 = (rose_cx + r_out_1 * math.cos(a2), rose_cy + r_out_1 * math.sin(a2))

        ctx.new_path()
        ctx.move_to(*p1)
        ctx.line_to(*p2)
        ctx.line_to(*ptip)
        ctx.line_to(*p3)
        ctx.line_to(*p4)
        ctx.close_path()

        col = gem_palette[i % len(gem_palette)]
        petal_g = cairo.RadialGradient(
            ptip[0], ptip[1], 4,
            (p1[0] + p4[0]) * 0.5, (p1[1] + p4[1]) * 0.5, r_out_2 - r_out_1
        )
        petal_g.add_color_stop_rgba(0.0, min(1.0, col[0] + 0.38), min(1.0, col[1] + 0.38), min(1.0, col[2] + 0.38), 0.96)
        petal_g.add_color_stop_rgba(0.68, col[0], col[1], col[2], 0.92)
        petal_g.add_color_stop_rgba(1.0, col[0] * 0.5, col[1] * 0.5, col[2] * 0.5, 0.96)
        ctx.set_source(petal_g)
        ctx.fill_preserve()

        ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
        ctx.set_line_width(3.2)
        ctx.stroke()

    # --- Middle Ring (16 Trefoil / Quatrefoil Medallions) ---
    n_mid = 16
    r_mid_1, r_mid_2 = rose_r * 0.36, rose_r * 0.66
    for i in range(n_mid):
        a1 = (i / n_mid) * math.tau + 0.05
        a2 = ((i + 0.92) / n_mid) * math.tau + 0.05
        amid = (a1 + a2) * 0.5

        ctx.new_path()
        ctx.arc(rose_cx, rose_cy, r_mid_2, a1, a2)
        ctx.arc_negative(rose_cx, rose_cy, r_mid_1, a2, a1)
        ctx.close_path()

        col = gem_palette[(i * 3 + 2) % len(gem_palette)]
        petal_g = cairo.RadialGradient(
            rose_cx + r_mid_2 * 0.85 * math.cos(amid),
            rose_cy + r_mid_2 * 0.85 * math.sin(amid), 2,
            rose_cx, rose_cy, rose_r * 0.8
        )
        petal_g.add_color_stop_rgba(0.0, min(1.0, col[0] + 0.42), min(1.0, col[1] + 0.42), min(1.0, col[2] + 0.42), 0.96)
        petal_g.add_color_stop_rgba(0.72, col[0], col[1], col[2], 0.92)
        petal_g.add_color_stop_rgba(1.0, col[0] * 0.45, col[1] * 0.45, col[2] * 0.45, 0.98)
        ctx.set_source(petal_g)
        ctx.fill_preserve()

        ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
        ctx.set_line_width(3.2)
        ctx.stroke()

        # Inner trefoil cusp motif inside petal
        cusp_r = (r_mid_2 - r_mid_1) * 0.22
        cusp_cx = rose_cx + ((r_mid_1 + r_mid_2) * 0.5) * math.cos(amid)
        cusp_cy = rose_cy + ((r_mid_1 + r_mid_2) * 0.5) * math.sin(amid)
        ctx.arc(cusp_cx, cusp_cy, cusp_r, 0, math.tau)
        ctx.set_source_rgba(1.0, 0.94, 0.70, 0.82)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.07, 0.08, 0.11, 0.98)
        ctx.set_line_width(2.2)
        ctx.stroke()

    # --- Inner Ring (12-lobed Rosette) ---
    n_in = 12
    r_in_1, r_in_2 = rose_r * 0.13, rose_r * 0.34
    for i in range(n_in):
        a1 = (i / n_in) * math.tau - 0.04
        a2 = ((i + 0.92) / n_in) * math.tau - 0.04

        ctx.new_path()
        ctx.arc(rose_cx, rose_cy, r_in_2, a1, a2)
        ctx.arc_negative(rose_cx, rose_cy, r_in_1, a2, a1)
        ctx.close_path()

        col = gem_palette[(i * 2 + 3) % len(gem_palette)]
        ctx.set_source_rgba(col[0], col[1], col[2], 0.94)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.07, 0.08, 0.11, 0.98)
        ctx.set_line_width(2.8)
        ctx.stroke()

    # Central Core Medallion (Golden Starlight Sunburst)
    ctx.arc(rose_cx, rose_cy, r_in_1, 0, math.tau)
    core_g = cairo.RadialGradient(rose_cx, rose_cy, 2, rose_cx, rose_cy, r_in_1)
    core_g.add_color_stop_rgba(0.0, 1.0, 1.0, 0.94, 1.0)
    core_g.add_color_stop_rgba(0.45, 0.98, 0.82, 0.24, 0.98)
    core_g.add_color_stop_rgba(1.0, 0.90, 0.44, 0.14, 0.95)
    ctx.set_source(core_g)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.07, 0.08, 0.11, 0.98)
    ctx.set_line_width(3.5)
    ctx.stroke()

    # Heavy Stone Tracery Rings around Rose Window
    for tr_r, tr_w in [(rose_r * 0.35, 7.5), (rose_r * 0.67, 9.5), (rose_r * 0.98, 15.0), (rose_r * 1.04, 20.0)]:
        ctx.arc(rose_cx, rose_cy, tr_r, 0, math.tau)
        ctx.set_source_rgba(0.10, 0.11, 0.15, 0.98)
        ctx.set_line_width(tr_w)
        ctx.stroke()

    # Pointed Gothic stone arch framing above the rose window
    arch_top_y = rose_cy - rose_r * 1.45
    ctx.new_path()
    ctx.move_to(rose_cx - rose_r * 1.25, rose_cy + rose_r * 0.8)
    ctx.line_to(rose_cx - rose_r * 1.25, rose_cy)
    ctx.curve_to(rose_cx - rose_r * 1.25, rose_cy - rose_r * 0.8, rose_cx - rose_r * 0.3, arch_top_y, rose_cx, arch_top_y)
    ctx.curve_to(rose_cx + rose_r * 0.3, arch_top_y, rose_cx + rose_r * 1.25, rose_cy - rose_r * 0.8, rose_cx + rose_r * 1.25, rose_cy)
    ctx.line_to(rose_cx + rose_r * 1.25, rose_cy + rose_r * 0.8)
    ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
    ctx.set_line_width(28.0)
    ctx.stroke()

    # 6. Belfry Arch Niche framing the bell on the left (cx=520, cy=380)
    belfry_w, belfry_h = 320, 560
    belfry_x, belfry_y = 520, 370 + parallax_bg_y * 0.35
    ctx.new_path()
    ctx.move_to(belfry_x - belfry_w * 0.5, belfry_y + belfry_h * 0.5)
    ctx.line_to(belfry_x - belfry_w * 0.5, belfry_y - belfry_h * 0.15)
    ctx.curve_to(
        belfry_x - belfry_w * 0.5, belfry_y - belfry_h * 0.45,
        belfry_x - belfry_w * 0.1, belfry_y - belfry_h * 0.52,
        belfry_x, belfry_y - belfry_h * 0.52
    )
    ctx.curve_to(
        belfry_x + belfry_w * 0.1, belfry_y - belfry_h * 0.52,
        belfry_x + belfry_w * 0.5, belfry_y - belfry_h * 0.45,
        belfry_x + belfry_w * 0.5, belfry_y - belfry_h * 0.15
    )
    ctx.line_to(belfry_x + belfry_w * 0.5, belfry_y + belfry_h * 0.5)
    ctx.set_source_rgba(0.07, 0.08, 0.11, 0.95)
    ctx.set_line_width(22.0)
    ctx.stroke()

    ctx.restore()  # End Dutch tilt architecture


# ---------------------------------------------------------------------------
# Gothic Stained-Glass Cathedral Bell & Chime Bells
# ---------------------------------------------------------------------------
def draw_stained_glass_bell(ctx: cairo.Context, bx: float, by: float,
                            scale: float = 1.0, swing_deg: float = 12.0,
                            palette_shift: int = 0, resonant_glow: bool = False):
    """
    Renders a Gothic Stained-Glass Cathedral Bell constructed of leaded jewel
    glass panes with wrought-iron yoke, bronze crown mount, and swinging clapper.
    """
    ctx.save()
    ctx.translate(bx, by)

    if resonant_glow:
        rg = cairo.RadialGradient(0, 0, 15 * scale, 0, 0, 165 * scale)
        rg.add_color_stop_rgba(0.0, 0.95, 0.88, 1.00, 0.45)
        rg.add_color_stop_rgba(0.45, 0.38, 0.72, 1.00, 0.24)
        rg.add_color_stop_rgba(1.0, 0.15, 0.25, 0.65, 0.0)
        ctx.set_source(rg)
        ctx.arc(0, 0, 165 * scale, 0, math.tau)
        ctx.fill()

        # Subtle concentric harmonic ring around upper-right chime bells
        for r_ring, a_ring in [(92 * scale, 0.38), (132 * scale, 0.22)]:
            ctx.arc(0, 12 * scale, r_ring, 0, math.tau)
            ctx.set_source_rgba(0.75, 0.90, 1.00, a_ring)
            ctx.set_line_width(1.6)
            ctx.stroke()

        # Hanging wrought-iron suspension rod up toward the cathedral vault
        ctx.new_path()
        ctx.move_to(0, -145 * scale)
        ctx.line_to(0, -450 * scale)
        ctx.set_source_rgba(0.14, 0.16, 0.22, 0.90)
        ctx.set_line_width(max(2.5, 4.5 * scale))
        ctx.stroke()

    ctx.rotate(swing_deg * math.pi / 180.0)
    ctx.scale(scale, scale)

    # 1. Wooden Belfry Timber & Wrought Iron Yoke (Mounting at the top)
    ctx.rectangle(-50, -155, 100, 36)
    yoke_g = cairo.LinearGradient(-50, 0, 50, 0)
    yoke_g.add_color_stop_rgb(0.0, 0.14, 0.15, 0.18)
    yoke_g.add_color_stop_rgb(0.5, 0.30, 0.32, 0.38)
    yoke_g.add_color_stop_rgb(1.0, 0.12, 0.13, 0.16)
    ctx.set_source(yoke_g)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.06, 0.07, 0.09, 1.0)
    ctx.set_line_width(3.2)
    ctx.stroke()

    # Iron bolts/rivets
    for rx in [-36, -14, 14, 36]:
        ctx.arc(rx, -137, 4.2, 0, math.tau)
        ctx.set_source_rgb(0.48, 0.50, 0.56)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.05, 0.05, 0.07)
        ctx.set_line_width(1.5)
        ctx.stroke()

    # Bell suspension canon loops
    for lx in [-24, 0, 24]:
        ctx.arc(lx, -118, 15.0, math.pi, 0.0)
        ctx.set_source_rgba(0.40, 0.34, 0.22, 1.0)
        ctx.set_line_width(6.5)
        ctx.stroke()

    # 2. Bell Body Contour & Stained-Glass Facet Tessellation
    top_w = 44.0
    waist_w = 66.0
    rim_w = 128.0
    h_top = -105.0
    h_waist = -20.0
    h_rim = 88.0
    h_lip = 102.0

    n_vertical_slices = 7
    n_horizontal_bands = 4
    band_y = [h_top, h_waist - 35, h_waist + 30, h_rim - 15, h_lip]

    ctx.save()
    ctx.new_path()
    ctx.move_to(-top_w, h_top)
    ctx.curve_to(-top_w * 0.9, h_waist * 0.8, -waist_w * 0.9, h_waist, -waist_w, h_waist + 20)
    ctx.curve_to(-waist_w * 1.1, h_rim * 0.8, -rim_w * 0.9, h_rim * 0.95, -rim_w, h_rim)
    ctx.line_to(-rim_w * 0.96, h_lip)
    ctx.curve_to(-rim_w * 0.5, h_lip + 15, rim_w * 0.5, h_lip + 15, rim_w * 0.96, h_lip)
    ctx.line_to(rim_w, h_rim)
    ctx.curve_to(rim_w * 0.9, h_rim * 0.95, waist_w * 1.1, h_rim * 0.8, waist_w, h_waist + 20)
    ctx.curve_to(waist_w * 0.9, h_waist, top_w * 0.9, h_waist * 0.8, top_w, h_top)
    ctx.close_path()
    ctx.clip()

    base_band_palettes = [
        [(0.12, 0.38, 0.82), (0.05, 0.55, 0.42), (0.22, 0.48, 0.92)],  # Sapphire / Emerald
        [(0.92, 0.62, 0.12), (0.98, 0.74, 0.18), (0.85, 0.48, 0.08)],  # Amber Gold
        [(0.88, 0.22, 0.28), (0.68, 0.18, 0.72), (0.95, 0.42, 0.18)],  # Ruby / Amethyst
        [(0.95, 0.78, 0.24), (0.82, 0.55, 0.15), (1.00, 0.88, 0.35)],  # Golden Rim Lip
    ]

    for b in range(n_horizontal_bands):
        y0, y1 = band_y[b], band_y[b + 1]
        pal = base_band_palettes[(b + palette_shift) % len(base_band_palettes)]
        for s in range(n_vertical_slices):
            t0 = s / n_vertical_slices
            t1 = (s + 1) / n_vertical_slices

            def get_w(y_val):
                if y_val <= h_waist:
                    f = (y_val - h_top) / (h_waist - h_top + 1e-4)
                    return top_w + (waist_w - top_w) * f
                else:
                    f = (y_val - h_waist) / (h_rim - h_waist + 1e-4)
                    return waist_w + (rim_w - waist_w) * (f ** 1.35)

            w0, w1 = get_w(y0), get_w(y1)
            x0_l = -w0 + 2.0 * w0 * t0
            x0_r = -w0 + 2.0 * w0 * t1
            x1_l = -w1 + 2.0 * w1 * t0
            x1_r = -w1 + 2.0 * w1 * t1

            ctx.new_path()
            ctx.move_to(x0_l, y0)
            ctx.line_to(x0_r, y0)
            ctx.line_to(x1_r, y1)
            ctx.line_to(x1_l, y1)
            ctx.close_path()

            col = pal[s % len(pal)]
            norm_x = (x0_l + x1_r) * 0.5 / (rim_w + 1e-4)
            shade = 0.55 + 0.45 * math.cos(norm_x * math.pi * 0.9)
            ctx.set_source_rgba(
                min(1.0, col[0] * shade + 0.14),
                min(1.0, col[1] * shade + 0.14),
                min(1.0, col[2] * shade + 0.09),
                0.94,
            )
            ctx.fill_preserve()

            # Dark solder lead came
            ctx.set_source_rgba(0.09, 0.10, 0.13, 0.98)
            ctx.set_line_width(3.2)
            ctx.stroke()

            # Specular metallic lead highlight on left-facing edges
            ctx.move_to(x0_l + 1.0, y0 + 1.0)
            ctx.line_to(x1_l + 1.0, y1 - 1.0)
            ctx.set_source_rgba(1.0, 0.94, 0.78, 0.50)
            ctx.set_line_width(1.0)
            ctx.stroke()

    ctx.restore()  # End bell clip

    # Heavy outer lead contour around the bell
    ctx.new_path()
    ctx.move_to(-top_w, h_top)
    ctx.curve_to(-top_w * 0.9, h_waist * 0.8, -waist_w * 0.9, h_waist, -waist_w, h_waist + 20)
    ctx.curve_to(-waist_w * 1.1, h_rim * 0.8, -rim_w * 0.9, h_rim * 0.95, -rim_w, h_rim)
    ctx.line_to(-rim_w * 0.96, h_lip)
    ctx.curve_to(-rim_w * 0.5, h_lip + 15, rim_w * 0.5, h_lip + 15, rim_w * 0.96, h_lip)
    ctx.line_to(rim_w, h_rim)
    ctx.curve_to(rim_w * 0.9, h_rim * 0.95, waist_w * 1.1, h_rim * 0.8, waist_w, h_waist + 20)
    ctx.curve_to(waist_w * 0.9, h_waist, top_w * 0.9, h_waist * 0.8, top_w, h_top)
    ctx.close_path()
    ctx.set_source_rgba(0.07, 0.08, 0.11, 1.0)
    ctx.set_line_width(5.2)
    ctx.stroke()

    # 3. Bronze Bell Clapper striking the lip
    clapper_base_x, clapper_base_y = 0.0, -42.0
    clapper_ball_x = rim_w * (0.73 if swing_deg >= 0 else -0.62)
    clapper_ball_y = h_lip + 4.0

    ctx.new_path()
    ctx.move_to(clapper_base_x, clapper_base_y)
    ctx.line_to(clapper_ball_x, clapper_ball_y)
    ctx.set_source_rgba(0.16, 0.14, 0.11, 1.0)
    ctx.set_line_width(7.5)
    ctx.stroke()

    cball_r = 19.0
    cball_g = cairo.RadialGradient(
        clapper_ball_x - 4, clapper_ball_y - 4, 2,
        clapper_ball_x, clapper_ball_y, cball_r
    )
    cball_g.add_color_stop_rgb(0.0, 0.98, 0.86, 0.48)
    cball_g.add_color_stop_rgb(0.5, 0.65, 0.44, 0.19)
    cball_g.add_color_stop_rgb(1.0, 0.22, 0.14, 0.08)
    ctx.set_source(cball_g)
    ctx.arc(clapper_ball_x, clapper_ball_y, cball_r, 0, math.tau)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.07, 0.07, 0.09, 1.0)
    ctx.set_line_width(2.6)
    ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# Suspended Gothic Diamond Stained-Glass Steps (悬浮哥特菱形彩窗台阶)
# ---------------------------------------------------------------------------
def draw_gothic_stained_glass_step(ctx: cairo.Context, sx: float, sy: float,
                                   width: float, height: float,
                                   color_rgb: tuple, accent_rgb: tuple,
                                   lit: float = 1.0):
    """
    Renders a suspended Gothic diamond stained-glass step with:
      - Radiant backlit jewel aura when stepped on by the Slime
      - 3D beveled leaded-glass side thickness facets
      - Top Gothic diamond / pointed-lancet mosaic platform divided into 9 jewel panes
        by dark charcoal solder lead cames & 1px metallic specular highlights.
    """
    hw = width * 0.5
    hh = height * 0.5
    depth = 15.0
    cr, cg, cb = color_rgb
    ar, ag, ab = accent_rgb

    ctx.save()

    # 1. Backlit Jewel Bloom Aura Beneath & Around Step
    if lit > 0.05:
        aura = cairo.RadialGradient(sx, sy + depth * 0.5, hh * 0.15, sx, sy + depth * 0.5, hw * 1.35)
        aura.add_color_stop_rgba(0.0, min(1.0, cr + 0.30), min(1.0, cg + 0.30), min(1.0, cb + 0.30), 0.52 * lit)
        aura.add_color_stop_rgba(0.45, cr, cg, cb, 0.26 * lit)
        aura.add_color_stop_rgba(1.0, ar * 0.5, ag * 0.5, ab * 0.5, 0.0)
        ctx.save()
        ctx.translate(sx, sy + depth * 0.6)
        ctx.scale(1.0, 0.48)
        ctx.set_source(aura)
        ctx.arc(0, 0, hw * 1.35, 0, math.tau)
        ctx.fill()
        ctx.restore()

    # Define Gothic Diamond / Lancet Top Polygon vertices
    p_left = (sx - hw, sy)
    p_fl = (sx - hw * 0.38, sy + hh * 0.82)
    p_front = (sx, sy + hh)
    p_fr = (sx + hw * 0.38, sy + hh * 0.82)
    p_right = (sx + hw, sy)
    p_br = (sx + hw * 0.38, sy - hh * 0.82)
    p_back = (sx, sy - hh)
    p_bl = (sx - hw * 0.38, sy - hh * 0.82)

    top_poly = [p_left, p_fl, p_front, p_fr, p_right, p_br, p_back, p_bl]

    # 2. 3D Beveled Glass Slab Side Thickness (4 visible front-facing facets)
    front_edges = [
        (p_left, p_fl, 0.62),
        (p_fl, p_front, 0.78),
        (p_front, p_fr, 0.52),
        (p_fr, p_right, 0.38),
    ]
    for (ea, eb, shade_f) in front_edges:
        ctx.new_path()
        ctx.move_to(ea[0], ea[1])
        ctx.line_to(eb[0], eb[1])
        ctx.line_to(eb[0], eb[1] + depth)
        ctx.line_to(ea[0], ea[1] + depth)
        ctx.close_path()

        if lit > 0.05:
            eg = cairo.LinearGradient(ea[0], ea[1], eb[0], eb[1] + depth)
            eg.add_color_stop_rgba(0.0, cr * shade_f, cg * shade_f, cb * shade_f, 0.95)
            eg.add_color_stop_rgba(1.0, ar * shade_f * 0.55, ag * shade_f * 0.55, ab * shade_f * 0.55, 0.98)
            ctx.set_source(eg)
        else:
            ctx.set_source_rgba(0.10, 0.11, 0.16, 0.88)
        ctx.fill_preserve()

        ctx.set_source_rgba(0.07, 0.08, 0.11, 0.98)
        ctx.set_line_width(2.4)
        ctx.stroke()

    # 3. Top Gothic Diamond Stained-Glass Mosaic Face
    ctx.save()
    ctx.new_path()
    ctx.move_to(*top_poly[0])
    for pt in top_poly[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    ctx.clip()

    if lit > 0.05:
        tg = cairo.RadialGradient(sx, sy, hh * 0.1, sx, sy, hw * 0.95)
        tg.add_color_stop_rgba(0.0, min(1.0, cr + 0.45), min(1.0, cg + 0.45), min(1.0, cb + 0.45), 0.98)
        tg.add_color_stop_rgba(0.55, cr, cg, cb, 0.95)
        tg.add_color_stop_rgba(1.0, ar * 0.75, ag * 0.75, ab * 0.75, 0.96)
        ctx.set_source(tg)
    else:
        ctx.set_source_rgba(0.16, 0.17, 0.24, 0.78)
    ctx.paint()

    inner_diamond = [
        (sx - hw * 0.42, sy),
        (sx, sy + hh * 0.56),
        (sx + hw * 0.42, sy),
        (sx, sy - hh * 0.56),
    ]
    ctx.new_path()
    ctx.move_to(*inner_diamond[0])
    for pt in inner_diamond[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    if lit > 0.05:
        ig = cairo.RadialGradient(sx, sy, 2.0, sx, sy, hw * 0.45)
        ig.add_color_stop_rgba(0.0, 1.0, 0.98, 0.88, 0.96)
        ig.add_color_stop_rgba(0.45, min(1.0, ar + 0.25), min(1.0, ag + 0.25), min(1.0, ab + 0.25), 0.92)
        ig.add_color_stop_rgba(1.0, cr, cg, cb, 0.94)
        ctx.set_source(ig)
    else:
        ctx.set_source_rgba(0.20, 0.21, 0.29, 0.80)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
    ctx.set_line_width(2.6)
    ctx.stroke()

    came_ribs = [
        (inner_diamond[0], p_left),
        (inner_diamond[0], p_fl),
        (inner_diamond[0], p_bl),
        (inner_diamond[1], p_front),
        (inner_diamond[2], p_right),
        (inner_diamond[2], p_fr),
        (inner_diamond[2], p_br),
        (inner_diamond[3], p_back),
    ]
    ctx.set_source_rgba(0.08, 0.09, 0.13, 0.96)
    ctx.set_line_width(2.4)
    for pa, pb in came_ribs:
        ctx.move_to(*pa)
        ctx.line_to(*pb)
    ctx.stroke()

    if lit > 0.05:
        ctx.set_source_rgba(1.0, 0.95, 0.80, 0.58)
        ctx.set_line_width(1.0)
        for pa, pb in came_ribs[:4]:
            ctx.move_to(pa[0], pa[1] - 1.0)
            ctx.line_to(pb[0], pb[1] - 1.0)
        ctx.stroke()

    ctx.restore()  # End top face clip

    # 4. Crisp Outer Lead Came Border & Specular Rim
    ctx.new_path()
    ctx.move_to(*top_poly[0])
    for pt in top_poly[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    ctx.set_source_rgba(0.07, 0.08, 0.11, 1.0)
    ctx.set_line_width(3.4)
    ctx.stroke_preserve()
    ctx.set_source_rgba(0.98, 0.92, 0.76, 0.62 if lit > 0.05 else 0.25)
    ctx.set_line_width(1.1)
    ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# Sweeping Prismatic Light Ribbons (宏大优雅的多层半透明彩虹棱镜光带桥)
# ---------------------------------------------------------------------------
def draw_sweeping_prismatic_ribbons(ctx: cairo.Context, shift_x: float = 0.0, shift_y: float = 0.0):
    """
    Renders sweeping, translucent, multi-layered rainbow prismatic light ribbons
    arching from the upper lit Gothic diamond step (435, 638), sweeping gracefully
    beneath the Giant Bell's acoustic burst and cradling the Slime (1140, 520),
    then soaring upward through the staggered upper-right chime bells toward the dome.
    """
    ctx.save()
    ctx.translate(shift_x, shift_y)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    # Smooth two-span cathedral S-arch trajectory:
    # Span A: From Step 4 (435, 638) -> graceful dip & rise under the Slime (1140, 520)
    # Span B: From Slime cradle (1140, 520) -> soaring through Chime Bells (1350, 290) -> (1555, 170)
    seg_a = ((435.0, 638.0), (680.0, 545.0), (910.0, 585.0), (1140.0, 520.0))
    seg_b = ((1140.0, 520.0), (1315.0, 468.0), (1415.0, 270.0), (1555.0, 170.0))

    spectral_bands = [
        (-24.0, (0.96, 0.26, 0.40), 0.34, 8.5),   # Ruby Coral
        (-16.0, (0.98, 0.56, 0.16), 0.36, 8.5),   # Imperial Amber
        ( -8.0, (1.00, 0.86, 0.24), 0.40, 9.0),   # Solar Gold
        (  0.0, (0.12, 0.86, 0.56), 0.38, 9.5),   # Chartres Emerald
        (  8.0, (0.20, 0.78, 1.00), 0.40, 9.0),   # Sky Cyan
        ( 16.0, (0.22, 0.46, 0.98), 0.36, 8.5),   # Cobalt Sapphire
        ( 24.0, (0.68, 0.32, 0.96), 0.34, 8.5),   # Royal Amethyst
    ]

    # 1. Soft Outer Prismatic Caustic Aura
    for (p0, c1, c2, p3) in (seg_a, seg_b):
        ctx.new_path()
        ctx.move_to(p0[0], p0[1])
        ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p3[0], p3[1])
        ctx.set_source_rgba(0.55, 0.75, 1.00, 0.14)
        ctx.set_line_width(72.0)
        ctx.stroke()

    # 2. Seven Translucent Jewel-Toned Spectral Light Ribbons
    for dy_off, (r, g, b), alpha_val, lw in spectral_bands:
        for (p0, c1, c2, p3) in (seg_a, seg_b):
            ctx.new_path()
            ctx.move_to(p0[0], p0[1] + dy_off)
            ctx.curve_to(c1[0], c1[1] + dy_off, c2[0], c2[1] + dy_off, p3[0], p3[1] + dy_off)
            ctx.set_source_rgba(r, g, b, alpha_val)
            ctx.set_line_width(lw)
            ctx.stroke()

    # 3. Delicate Leaded Gold-and-Charcoal Filigree Borders Framing the Ribbon Bridge
    for border_off in (-29.0, 29.0):
        for (p0, c1, c2, p3) in (seg_a, seg_b):
            ctx.new_path()
            ctx.move_to(p0[0], p0[1] + border_off)
            ctx.curve_to(c1[0], c1[1] + border_off, c2[0], c2[1] + border_off, p3[0], p3[1] + border_off)
            ctx.set_source_rgba(0.08, 0.09, 0.13, 0.72)
            ctx.set_line_width(2.4)
            ctx.stroke_preserve()
            ctx.set_source_rgba(1.0, 0.92, 0.68, 0.55)
            ctx.set_line_width(1.0)
            ctx.stroke()

    # 4. Luminous Starlight Core Spine & Prismatic Diamond Caustic Nodes
    for (p0, c1, c2, p3) in (seg_a, seg_b):
        ctx.new_path()
        ctx.move_to(p0[0], p0[1])
        ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p3[0], p3[1])
        ctx.set_source_rgba(1.0, 0.98, 0.88, 0.68)
        ctx.set_line_width(3.2)
        ctx.stroke()

        for t_node in np.linspace(0.14, 0.86, 5):
            omt = 1.0 - t_node
            nx = (omt**3)*p0[0] + 3*(omt**2)*t_node*c1[0] + 3*omt*(t_node**2)*c2[0] + (t_node**3)*p3[0]
            ny = (omt**3)*p0[1] + 3*(omt**2)*t_node*c1[1] + 3*omt*(t_node**2)*c2[1] + (t_node**3)*p3[1]
            _draw_four_point_star_path(ctx, nx, ny, 6.5, 2.0, rot=t_node * math.pi)
            ctx.set_source_rgba(1.0, 0.96, 0.78, 0.82)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.08, 0.09, 0.13, 0.85)
            ctx.set_line_width(1.2)
            ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# Concentric Stained-Glass Acoustic Shockwaves & Bell Rope (v3 Signature)
# ---------------------------------------------------------------------------
def draw_acoustic_shockwaves(ctx: cairo.Context, strike_x: float, strike_y: float,
                             slime_x: float = 1140.0, slime_y: float = 470.0):
    """
    Renders visible concentric stained-glass acoustic shockwaves (彩色玻璃声波环)
    rippling across the mosaic from the bell impact point towards the Slime,
    plus the undulating leaded stained-glass bell rope.
    """
    # 1. Brilliant Multi-Spectral Impact Flash at the contact point
    burst_g = cairo.RadialGradient(strike_x, strike_y, 4, strike_x, strike_y, 85)
    burst_g.add_color_stop_rgba(0.0, 1.0, 1.0, 0.96, 0.98)
    burst_g.add_color_stop_rgba(0.28, 1.0, 0.86, 0.35, 0.88)
    burst_g.add_color_stop_rgba(0.62, 0.45, 0.88, 1.00, 0.50)
    burst_g.add_color_stop_rgba(1.0, 0.88, 0.35, 0.68, 0.0)
    ctx.set_source(burst_g)
    ctx.arc(strike_x, strike_y, 85, 0, math.tau)
    ctx.fill()

    # Impact spark rays radiating from contact
    ctx.save()
    for ang in np.linspace(0, math.tau, 14, endpoint=False):
        sp_len = 38.0 + (ang % 0.6) * 45.0
        ex = strike_x + sp_len * math.cos(ang)
        ey = strike_y + sp_len * math.sin(ang)
        ctx.move_to(strike_x, strike_y)
        ctx.line_to(ex, ey)
        ctx.set_source_rgba(1.0, 0.96, 0.75, 0.85)
        ctx.set_line_width(2.2)
        ctx.stroke()
    ctx.restore()

    # 2. Concentric Stained-Glass Acoustic Shockwave Rings
    radii = [140, 270, 430, 610, 810, 1040]
    spectral_colors = [
        (0.31, 0.68, 1.00),  # Sky Cyan (#4FADFF)
        (0.98, 0.78, 0.24),  # Starlight Amber Gold (#FBBF24)
        (0.85, 0.35, 0.95),  # Violet Amethyst (#D946EF)
        (0.95, 0.42, 0.48),  # Ruby Coral (#F43F5E)
        (0.25, 0.88, 0.65),  # Emerald Mint (#10B981)
        (0.45, 0.62, 1.00),  # Cobalt Blue (#3B82F6)
    ]

    for idx, r_wave in enumerate(radii):
        col = spectral_colors[idx % len(spectral_colors)]
        alpha_base = max(0.20, 0.75 - idx * 0.08)

        a_start = -math.pi * 0.40
        a_end = math.pi * 0.40

        ctx.save()
        # A. Soft prismatic caustic wave ribbon
        ctx.arc(strike_x, strike_y, r_wave, a_start, a_end)
        ctx.set_source_rgba(col[0], col[1], col[2], alpha_base * 0.65)
        ctx.set_line_width(14.0)
        ctx.stroke()

        # B. Crisp dark lead came wave line
        ctx.arc(strike_x, strike_y, r_wave, a_start, a_end)
        ctx.set_source_rgba(0.10, 0.12, 0.16, alpha_base * 0.92)
        ctx.set_line_width(3.2)
        ctx.stroke()

        # C. Warm metallic specular highlight edge
        ctx.arc(strike_x, strike_y, r_wave - 2.8, a_start, a_end)
        ctx.set_source_rgba(1.0, 0.96, 0.84, alpha_base * 0.88)
        ctx.set_line_width(1.4)
        ctx.stroke()

        # D. Floating stained-glass acoustic jewel beads along each shockwave
        n_beads = 4 + idx * 2
        for b_i in range(n_beads):
            b_ang = a_start + ((b_i + 0.5) / n_beads) * (a_end - a_start)
            bx = strike_x + r_wave * math.cos(b_ang)
            by = strike_y + r_wave * math.sin(b_ang)

            bead_r = 5.2 + (idx % 3) * 1.8
            _draw_four_point_star_path(ctx, bx, by, bead_r, bead_r * 0.32, rot=b_ang)
            ctx.set_source_rgba(
                min(1.0, col[0] + 0.32),
                min(1.0, col[1] + 0.32),
                min(1.0, col[2] + 0.32),
                alpha_base * 0.92,
            )
            ctx.fill_preserve()
            ctx.set_source_rgba(0.08, 0.09, 0.12, alpha_base)
            ctx.set_line_width(1.6)
            ctx.stroke()
        ctx.restore()

    # 3. Micro-Story Toll Connection: Leaded Stained-Glass Bell Rope
    ctx.save()
    ctx.new_path()
    rope_start_x, rope_start_y = strike_x - 12.0, strike_y + 18.0
    rope_end_x, rope_end_y = slime_x - 62.0, slime_y + 42.0
    ctrl1_x, ctrl1_y = strike_x + 80.0, strike_y + 210.0
    ctrl2_x, ctrl2_y = (strike_x + slime_x) * 0.52, max(strike_y, slime_y) + 195.0
    ctx.move_to(rope_start_x, rope_start_y)
    ctx.curve_to(ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, rope_end_x, rope_end_y)

    ctx.set_source_rgba(0.08, 0.09, 0.12, 0.85)
    ctx.set_line_width(5.0)
    ctx.stroke_preserve()
    ctx.set_source_rgba(1.0, 0.82, 0.32, 0.90)
    ctx.set_line_width(2.6)
    ctx.stroke()

    for t_step in np.linspace(0.15, 0.90, 8):
        omt = 1.0 - t_step
        px = (omt**3)*rope_start_x + 3*(omt**2)*t_step*ctrl1_x + 3*omt*(t_step**2)*ctrl2_x + (t_step**3)*rope_end_x
        py = (omt**3)*rope_start_y + 3*(omt**2)*t_step*ctrl1_y + 3*omt*(t_step**2)*ctrl2_y + (t_step**3)*rope_end_y
        ctx.arc(px, py, 4.2, 0, math.tau)
        ctx.set_source_rgba(1.0, 0.94, 0.70, 0.95)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.09, 0.10, 0.13, 1.0)
        ctx.set_line_width(1.5)
        ctx.stroke()
    ctx.restore()


# ---------------------------------------------------------------------------
# Diagonal Volumetric Tyndall God-Rays & Colored Glass Dust Motes (v3 Signature)
# ---------------------------------------------------------------------------
def draw_volumetric_god_rays(ctx: cairo.Context, rng: random.Random):
    """
    Renders diagonal volumetric sunbeams (Tyndall rays) streaming from upper-left
    to lower-right across the cathedral interior, carrying glowing colored glass dust motes.
    """
    ctx.save()

    beams = [
        (80, 280, (1.00, 0.92, 0.70, 0.16)),    # Main warm golden beam from rose window
        (340, 200, (0.35, 0.72, 1.00, 0.14)),   # Sapphire blue beam
        (580, 250, (0.85, 0.45, 0.98, 0.13)),   # Amethyst beam
        (820, 310, (1.00, 0.84, 0.42, 0.18)),   # Brilliant gold beam focusing on Slime
        (-80, 220, (0.28, 0.88, 0.65, 0.12)),   # Emerald beam illuminating the bell
        (1100, 240, (0.95, 0.45, 0.55, 0.12)),  # Rose coral beam
    ]

    ray_length = 2400.0
    ray_dx = ray_length * math.cos(33.0 * math.pi / 180.0)
    ray_dy = ray_length * math.sin(33.0 * math.pi / 180.0)

    for ox, bw, col in beams:
        p1 = (ox - bw * 0.5, -150)
        p2 = (ox + bw * 0.5, -150)
        p3 = (p2[0] + ray_dx, p2[1] + ray_dy)
        p4 = (p1[0] + ray_dx, p1[1] + ray_dy)

        ctx.new_path()
        ctx.move_to(*p1)
        ctx.line_to(*p2)
        ctx.line_to(*p3)
        ctx.line_to(*p4)
        ctx.close_path()

        rg = cairo.LinearGradient(p1[0], p1[1], p4[0], p4[1])
        rg.add_color_stop_rgba(0.0, col[0], col[1], col[2], col[3] * 1.5)
        rg.add_color_stop_rgba(0.4, col[0], col[1], col[2], col[3])
        rg.add_color_stop_rgba(0.85, col[0], col[1], col[2], col[3] * 0.4)
        rg.add_color_stop_rgba(1.0, col[0], col[1], col[2], 0.0)
        ctx.set_source(rg)
        ctx.fill()

    mote_palette = [
        (1.00, 0.95, 0.70),  # Amber diamond
        (0.40, 0.85, 1.00),  # Sapphire blue
        (0.95, 0.45, 0.85),  # Violet amethyst
        (0.98, 0.52, 0.55),  # Ruby coral
        (0.45, 0.95, 0.75),  # Emerald mint
    ]

    for _ in range(260):
        t_diag = rng.uniform(0.05, 0.95)
        lane_x = rng.uniform(-100, 1400)
        mx = lane_x + t_diag * ray_dx + rng.gauss(0, 50)
        my = -150 + t_diag * ray_dy + rng.gauss(0, 50)

        if 0 <= mx <= W and 0 <= my <= H:
            m_r = rng.uniform(1.2, 4.4)
            m_col = rng.choice(mote_palette)
            m_alpha = rng.uniform(0.35, 0.85)

            m_grad = cairo.RadialGradient(mx, my, 0.5, mx, my, m_r * 2.5)
            m_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, m_alpha)
            m_grad.add_color_stop_rgba(0.4, m_col[0], m_col[1], m_col[2], m_alpha * 0.7)
            m_grad.add_color_stop_rgba(1.0, m_col[0], m_col[1], m_col[2], 0.0)
            ctx.set_source(m_grad)
            ctx.arc(mx, my, m_r * 2.5, 0, math.tau)
            ctx.fill()

    ctx.restore()


# ---------------------------------------------------------------------------
# API Contract Function: render_world
# ---------------------------------------------------------------------------
def render_world(cam_x: float, cam_y: float, t: float, state: dict = None) -> Image.Image:
    """
    Renders the 1920x1080 viewport of World 08 (Gothic Stained-Glass Cathedral)
    at camera coordinate (cam_x, cam_y) and time `t`.
    Uses parallax anchoring so the Grand Leaded Gothic Rose Window stays
    majestically suspended in the upper-left cathedral zenith throughout the ascent.
    """
    if cam_x <= 10.0 and cam_y <= WORLD_H - H:
        center_x = W * 0.5
        center_y = cam_y + H * 0.5
    else:
        center_x = float(cam_x)
        center_y = float(cam_y)

    # Reference keyframe camera center is (960.0, 1620.0)
    dy_cam = 1620.0 - center_y
    dx_cam = 960.0 - center_x

    # Parallax offsets:
    # Rose window & high zenith stay grandly visible in upper-left throughout vertical climb
    parallax_rose_y = dy_cam * 0.10
    parallax_bg_y = dy_cam * 0.22
    mid_shift_x = dx_cam * 0.65
    mid_shift_y = dy_cam * 0.55

    rng = random.Random(42)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    # 1. Background: Cathedral Vaults, Lancet Windows & Grand Gothic Rose Window (-10 deg Dutch tilt)
    create_cathedral_background(ctx, parallax_rose_y=parallax_rose_y, parallax_bg_y=parallax_bg_y)

    # 2. Sweeping Prismatic Light Ribbons (宏大的多层半透明彩虹棱镜光带桥)
    draw_sweeping_prismatic_ribbons(ctx, shift_x=mid_shift_x, shift_y=mid_shift_y)

    # 3. Lit Suspended Gothic Diamond Stained-Glass Steps (左下至中景踩亮的悬浮哥特菱形彩窗台阶)
    # 4 crisp zig-zagging jewel steps ascending from lower-left to launch onto the Prismatic Bridge
    step_specs = [
        # (screen_x_at_kf, screen_y_at_kf, width, height, main_rgb, accent_rgb)
        (170.0, 965.0, 216.0, 56.0, (0.12, 0.48, 0.98), (0.28, 0.78, 1.00)),  # Step 1: Deep Sapphire Blue
        (355.0, 855.0, 206.0, 54.0, (0.06, 0.78, 0.48), (0.35, 0.96, 0.72)),  # Step 2: Chartres Emerald Green
        (235.0, 742.0, 198.0, 52.0, (0.98, 0.70, 0.14), (1.00, 0.90, 0.42)),  # Step 3: Imperial Amber Gold
        (435.0, 638.0, 192.0, 50.0, (0.90, 0.24, 0.42), (0.72, 0.32, 0.96)),  # Step 4: Cathedral Ruby & Amethyst
    ]

    # Golden-cyan light trail connecting the lit steps upward
    ctx.save()
    ctx.new_path()
    for idx, (sx0, sy0, _, _, _, _) in enumerate(step_specs):
        px = sx0 + mid_shift_x
        py = sy0 + mid_shift_y
        if idx == 0:
            ctx.move_to(px, py)
        else:
            ctx.line_to(px, py)
    ctx.set_source_rgba(0.45, 0.85, 1.00, 0.32)
    ctx.set_line_width(8.0)
    ctx.stroke_preserve()
    ctx.set_source_rgba(1.00, 0.94, 0.72, 0.70)
    ctx.set_line_width(2.2)
    ctx.stroke()
    ctx.restore()

    for sx0, sy0, sw, sh, c_main, c_acc in step_specs:
        draw_gothic_stained_glass_step(
            ctx,
            sx0 + mid_shift_x,
            sy0 + mid_shift_y,
            sw,
            sh,
            color_rgb=c_main,
            accent_rgb=c_acc,
            lit=1.0,
        )

    # 4. Staggered Upper-Right Stained-Glass Chime Bells (右上方高低错落的琉璃风铃)
    draw_stained_glass_bell(
        ctx,
        1350.0 + mid_shift_x,
        280.0 + mid_shift_y,
        scale=0.54,
        swing_deg=-9.0,
        palette_shift=1,
        resonant_glow=True,
    )
    draw_stained_glass_bell(
        ctx,
        1545.0 + mid_shift_x,
        168.0 + mid_shift_y,
        scale=0.44,
        swing_deg=7.5,
        palette_shift=2,
        resonant_glow=True,
    )

    # 5. Giant Stained-Glass Cathedral Bell on the Left (cx=520, cy=380)
    bell_cx = 520.0 + mid_shift_x
    bell_cy = 380.0 + mid_shift_y
    draw_stained_glass_bell(ctx, bell_cx, bell_cy, scale=1.12, swing_deg=11.5, palette_shift=0)

    # 6. Concentric Stained-Glass Acoustic Shockwaves & Bell Rope
    strike_x = 596.0 + mid_shift_x
    strike_y = 460.0 + mid_shift_y

    if state and "slime" in state:
        sl = state["slime"]
        if "sx" in sl and "sy" in sl:
            slime_sx, slime_sy = float(sl["sx"]), float(sl["sy"])
        else:
            slime_sx = float(sl.get("cx", 1140.0)) - center_x + W * 0.5
            slime_sy = float(sl.get("cy", 1550.0)) - center_y + H * 0.5
        slime_r = float(sl.get("radius", 68.0))
        slime_squash = float(sl.get("squash_y", 1.06))
        slime_tilt = float(sl.get("tilt", -0.10))
        slime_look = sl.get("look", (-0.44, -0.16))
        slime_eye_mode = sl.get("eye_mode", "pill")
        slime_blink = float(sl.get("blink", 0.0))
    else:
        slime_sx = 1140.0 + mid_shift_x
        slime_sy = 470.0 + mid_shift_y
        slime_r = 68.0  # Diameter = 136px (strictly within 130~140px spec!)
        slime_squash = 1.06
        slime_tilt = -0.10
        slime_look = (-0.44, -0.16)
        slime_eye_mode = "pill"
        slime_blink = 0.0

    draw_acoustic_shockwaves(ctx, strike_x, strike_y, slime_x=slime_sx, slime_y=slime_sy)

    # 7. Diagonal Volumetric God-Rays & Colored Glass Dust Motes
    draw_volumetric_god_rays(ctx, rng)

    # 8. Leading 4-Facet Stained-Glass Companion Star (✦) & Voronoi Stained-Glass Slime
    if state is None or state.get("draw_characters", True):
        if state and "star" in state:
            st = state["star"]
            if "sx" in st and "sy" in st:
                star_sx, star_sy = float(st["sx"]), float(st["sy"])
            else:
                star_sx = float(st.get("cx", 1255.0)) - center_x + W * 0.5
                star_sy = float(st.get("cy", 1415.0)) - center_y + H * 0.5
            star_r = float(st.get("r", 38.0))
            star_rot = float(st.get("rot", 0.12))
        else:
            star_sx = 1255.0 + mid_shift_x
            star_sy = 335.0 + mid_shift_y
            star_r = 38.0
            star_rot = 0.12

        draw_star(ctx, star_sx, star_sy, star_r, rot=star_rot, t=t)

        draw_slime(
            ctx,
            slime_sx,
            slime_sy,
            slime_r,
            squash_y=slime_squash,
            tilt=slime_tilt,
            look=slime_look,
            eye_mode=slime_eye_mode,
            blink=slime_blink,
            t=t,
            draw_crown_star=False,
        )

    # 9. Convert PyCairo surface to PIL Image with subtle v3 luminance polish (NO UI TAG!)
    w, h = surface.get_width(), surface.get_height()
    buf = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = buf[:, :, [2, 1, 0]].astype(np.float32) / 255.0
    rgb = np.clip(rgb * 1.04, 0.0, 1.0)
    return Image.fromarray((rgb * 255.0).astype(np.uint8), mode="RGB")


# ---------------------------------------------------------------------------
# Concentric Stained-Glass Acoustic Shockwaves & Bell Rope (v3 Signature)
# ---------------------------------------------------------------------------
def draw_acoustic_shockwaves(ctx: cairo.Context, strike_x: float, strike_y: float,
                             slime_x: float = 1140.0, slime_y: float = 470.0):
    """
    Renders visible concentric stained-glass acoustic shockwaves (彩色玻璃声波环)
    rippling across the mosaic from the bell impact point towards the Slime,
    plus the undulating leaded stained-glass bell rope.
    """
    # 1. Brilliant Multi-Spectral Impact Flash at the contact point
    burst_g = cairo.RadialGradient(strike_x, strike_y, 4, strike_x, strike_y, 85)
    burst_g.add_color_stop_rgba(0.0, 1.0, 1.0, 0.96, 0.98)
    burst_g.add_color_stop_rgba(0.28, 1.0, 0.86, 0.35, 0.88)
    burst_g.add_color_stop_rgba(0.62, 0.45, 0.88, 1.00, 0.50)
    burst_g.add_color_stop_rgba(1.0, 0.88, 0.35, 0.68, 0.0)
    ctx.set_source(burst_g)
    ctx.arc(strike_x, strike_y, 85, 0, math.tau)
    ctx.fill()

    # Impact spark rays radiating from contact
    ctx.save()
    for ang in np.linspace(0, math.tau, 14, endpoint=False):
        sp_len = 38.0 + (ang % 0.6) * 45.0
        ex = strike_x + sp_len * math.cos(ang)
        ey = strike_y + sp_len * math.sin(ang)
        ctx.move_to(strike_x, strike_y)
        ctx.line_to(ex, ey)
        ctx.set_source_rgba(1.0, 0.96, 0.75, 0.85)
        ctx.set_line_width(2.2)
        ctx.stroke()
    ctx.restore()

    # 2. Concentric Stained-Glass Acoustic Shockwave Rings
    radii = [140, 270, 430, 610, 810, 1040]
    spectral_colors = [
        (0.31, 0.68, 1.00),  # Sky Cyan (#4FADFF)
        (0.98, 0.78, 0.24),  # Starlight Amber Gold (#FBBF24)
        (0.85, 0.35, 0.95),  # Violet Amethyst (#D946EF)
        (0.95, 0.42, 0.48),  # Ruby Coral (#F43F5E)
        (0.25, 0.88, 0.65),  # Emerald Mint (#10B981)
        (0.45, 0.62, 1.00),  # Cobalt Blue (#3B82F6)
    ]

    for idx, r_wave in enumerate(radii):
        col = spectral_colors[idx % len(spectral_colors)]
        alpha_base = max(0.20, 0.75 - idx * 0.08)

        a_start = -math.pi * 0.40
        a_end = math.pi * 0.40

        ctx.save()
        # A. Soft prismatic caustic wave ribbon
        ctx.arc(strike_x, strike_y, r_wave, a_start, a_end)
        ctx.set_source_rgba(col[0], col[1], col[2], alpha_base * 0.65)
        ctx.set_line_width(14.0)
        ctx.stroke()

        # B. Crisp dark lead came wave line
        ctx.arc(strike_x, strike_y, r_wave, a_start, a_end)
        ctx.set_source_rgba(0.10, 0.12, 0.16, alpha_base * 0.92)
        ctx.set_line_width(3.2)
        ctx.stroke()

        # C. Warm metallic specular highlight edge
        ctx.arc(strike_x, strike_y, r_wave - 2.8, a_start, a_end)
        ctx.set_source_rgba(1.0, 0.96, 0.84, alpha_base * 0.88)
        ctx.set_line_width(1.4)
        ctx.stroke()

        # D. Floating stained-glass acoustic jewel beads along each shockwave
        n_beads = 4 + idx * 2
        for b_i in range(n_beads):
            b_ang = a_start + ((b_i + 0.5) / n_beads) * (a_end - a_start)
            bx = strike_x + r_wave * math.cos(b_ang)
            by = strike_y + r_wave * math.sin(b_ang)

            bead_r = 5.2 + (idx % 3) * 1.8
            _draw_four_point_star_path(ctx, bx, by, bead_r, bead_r * 0.32, rot=b_ang)
            ctx.set_source_rgba(
                min(1.0, col[0] + 0.32),
                min(1.0, col[1] + 0.32),
                min(1.0, col[2] + 0.32),
                alpha_base * 0.92,
            )
            ctx.fill_preserve()
            ctx.set_source_rgba(0.08, 0.09, 0.12, alpha_base)
            ctx.set_line_width(1.6)
            ctx.stroke()
        ctx.restore()

    # 3. Micro-Story Toll Connection: Leaded Stained-Glass Bell Rope
    ctx.save()
    ctx.new_path()
    rope_start_x, rope_start_y = strike_x - 12.0, strike_y + 18.0
    rope_end_x, rope_end_y = slime_x - 62.0, slime_y + 42.0
    ctrl1_x, ctrl1_y = strike_x + 80.0, strike_y + 210.0
    ctrl2_x, ctrl2_y = (strike_x + slime_x) * 0.52, max(strike_y, slime_y) + 195.0
    ctx.move_to(rope_start_x, rope_start_y)
    ctx.curve_to(ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, rope_end_x, rope_end_y)

    ctx.set_source_rgba(0.08, 0.09, 0.12, 0.85)
    ctx.set_line_width(5.0)
    ctx.stroke_preserve()
    ctx.set_source_rgba(1.0, 0.82, 0.32, 0.90)
    ctx.set_line_width(2.6)
    ctx.stroke()

    for t_step in np.linspace(0.15, 0.90, 8):
        omt = 1.0 - t_step
        px = (omt**3)*rope_start_x + 3*(omt**2)*t_step*ctrl1_x + 3*omt*(t_step**2)*ctrl2_x + (t_step**3)*rope_end_x
        py = (omt**3)*rope_start_y + 3*(omt**2)*t_step*ctrl1_y + 3*omt*(t_step**2)*ctrl2_y + (t_step**3)*rope_end_y
        ctx.arc(px, py, 4.2, 0, math.tau)
        ctx.set_source_rgba(1.0, 0.94, 0.70, 0.95)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.09, 0.10, 0.13, 1.0)
        ctx.set_line_width(1.5)
        ctx.stroke()
    ctx.restore()


# ---------------------------------------------------------------------------
# Diagonal Volumetric Tyndall God-Rays & Colored Glass Dust Motes (v3 Signature)
# ---------------------------------------------------------------------------
def draw_volumetric_god_rays(ctx: cairo.Context, rng: random.Random):
    """
    Renders diagonal volumetric sunbeams (Tyndall rays) streaming from upper-left
    to lower-right across the cathedral interior, carrying glowing colored glass dust motes.
    """
    ctx.save()

    beams = [
        (80, 280, (1.00, 0.92, 0.70, 0.16)),    # Main warm golden beam from rose window
        (340, 200, (0.35, 0.72, 1.00, 0.14)),   # Sapphire blue beam
        (580, 250, (0.85, 0.45, 0.98, 0.13)),   # Amethyst beam
        (820, 310, (1.00, 0.84, 0.42, 0.18)),   # Brilliant gold beam focusing on Slime
        (-80, 220, (0.28, 0.88, 0.65, 0.12)),   # Emerald beam illuminating the bell
        (1100, 240, (0.95, 0.45, 0.55, 0.12)),  # Rose coral beam
    ]

    ray_length = 2400.0
    ray_dx = ray_length * math.cos(33.0 * math.pi / 180.0)
    ray_dy = ray_length * math.sin(33.0 * math.pi / 180.0)

    for ox, bw, col in beams:
        p1 = (ox - bw * 0.5, -150)
        p2 = (ox + bw * 0.5, -150)
        p3 = (p2[0] + ray_dx, p2[1] + ray_dy)
        p4 = (p1[0] + ray_dx, p1[1] + ray_dy)

        ctx.new_path()
        ctx.move_to(*p1)
        ctx.line_to(*p2)
        ctx.line_to(*p3)
        ctx.line_to(*p4)
        ctx.close_path()

        rg = cairo.LinearGradient(p1[0], p1[1], p4[0], p4[1])
        rg.add_color_stop_rgba(0.0, col[0], col[1], col[2], col[3] * 1.5)
        rg.add_color_stop_rgba(0.4, col[0], col[1], col[2], col[3])
        rg.add_color_stop_rgba(0.85, col[0], col[1], col[2], col[3] * 0.4)
        rg.add_color_stop_rgba(1.0, col[0], col[1], col[2], 0.0)
        ctx.set_source(rg)
        ctx.fill()

    mote_palette = [
        (1.00, 0.95, 0.70),  # Amber diamond
        (0.40, 0.85, 1.00),  # Sapphire blue
        (0.95, 0.45, 0.85),  # Violet amethyst
        (0.98, 0.52, 0.55),  # Ruby coral
        (0.45, 0.95, 0.75),  # Emerald mint
    ]

    for _ in range(260):
        t_diag = rng.uniform(0.05, 0.95)
        lane_x = rng.uniform(-100, 1400)
        mx = lane_x + t_diag * ray_dx + rng.gauss(0, 50)
        my = -150 + t_diag * ray_dy + rng.gauss(0, 50)

        if 0 <= mx <= W and 0 <= my <= H:
            m_r = rng.uniform(1.2, 4.4)
            m_col = rng.choice(mote_palette)
            m_alpha = rng.uniform(0.35, 0.85)

            m_grad = cairo.RadialGradient(mx, my, 0.5, mx, my, m_r * 2.5)
            m_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, m_alpha)
            m_grad.add_color_stop_rgba(0.4, m_col[0], m_col[1], m_col[2], m_alpha * 0.7)
            m_grad.add_color_stop_rgba(1.0, m_col[0], m_col[1], m_col[2], 0.0)
            ctx.set_source(m_grad)
            ctx.arc(mx, my, m_r * 2.5, 0, math.tau)
            ctx.fill()

    ctx.restore()


# ---------------------------------------------------------------------------
# API Contract Function: render_world
# ---------------------------------------------------------------------------
def render_world(cam_x: float, cam_y: float, t: float, state: dict = None) -> Image.Image:
    """
    Renders the 1920x1080 viewport of World 08 (Gothic Stained-Glass Cathedral)
    at camera coordinate (cam_x, cam_y) and time `t`.
    Uses parallax anchoring so the Grand Leaded Gothic Rose Window stays
    majestically suspended in the upper-left cathedral zenith throughout the ascent.
    """
    if cam_x <= 10.0 and cam_y <= WORLD_H - H:
        center_x = W * 0.5
        center_y = cam_y + H * 0.5
    else:
        center_x = float(cam_x)
        center_y = float(cam_y)

    # Reference keyframe camera center is (960.0, 1620.0)
    dy_cam = 1620.0 - center_y
    dx_cam = 960.0 - center_x

    # Parallax offsets:
    # Rose window & high zenith stay grandly visible in upper-left throughout vertical climb
    parallax_rose_y = dy_cam * 0.10
    parallax_bg_y = dy_cam * 0.22
    mid_shift_x = dx_cam * 0.65
    mid_shift_y = dy_cam * 0.55

    rng = random.Random(42)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    # 1. Background: Cathedral Vaults, Lancet Windows & Grand Gothic Rose Window (-10 deg Dutch tilt)
    create_cathedral_background(ctx, parallax_rose_y=parallax_rose_y, parallax_bg_y=parallax_bg_y)

    # 2. Lit Suspended Gothic Diamond Stained-Glass Steps (左下至中景踩亮的悬浮哥特菱形彩窗台阶)
    # Ascending zig-zag from lower-left up to the Giant Bell & Prismatic Light Bridge
    step_specs = [
        # (screen_x_at_kf, screen_y_at_kf, width, height, main_rgb, accent_rgb)
        (175.0, 968.0, 215.0, 56.0, (0.12, 0.48, 0.98), (0.28, 0.78, 1.00)),  # Step 1: Deep Sapphire Blue
        (355.0, 862.0, 204.0, 54.0, (0.06, 0.78, 0.48), (0.35, 0.96, 0.72)),  # Step 2: Chartres Emerald Green
        (240.0, 748.0, 196.0, 52.0, (0.98, 0.70, 0.14), (1.00, 0.90, 0.42)),  # Step 3: Imperial Amber Gold
        (430.0, 646.0, 190.0, 50.0, (0.90, 0.24, 0.42), (0.72, 0.32, 0.96)),  # Step 4: Cathedral Ruby & Amethyst
        (620.0, 558.0, 182.0, 48.0, (0.22, 0.72, 0.98), (0.98, 0.76, 0.24)),  # Step 5: Celestial Turquoise & Gold
    ]

    # Golden-cyan light trail connecting the lit steps upward
    ctx.save()
    ctx.new_path()
    for idx, (sx0, sy0, _, _, _, _) in enumerate(step_specs):
        px = sx0 + mid_shift_x
        py = sy0 + mid_shift_y
        if idx == 0:
            ctx.move_to(px, py)
        else:
            ctx.line_to(px, py)
    ctx.set_source_rgba(0.45, 0.85, 1.00, 0.32)
    ctx.set_line_width(8.0)
    ctx.stroke_preserve()
    ctx.set_source_rgba(1.00, 0.94, 0.72, 0.70)
    ctx.set_line_width(2.2)
    ctx.stroke()
    ctx.restore()

    for sx0, sy0, sw, sh, c_main, c_acc in step_specs:
        draw_gothic_stained_glass_step(
            ctx,
            sx0 + mid_shift_x,
            sy0 + mid_shift_y,
            sw,
            sh,
            color_rgb=c_main,
            accent_rgb=c_acc,
            lit=1.0,
        )

    # 3. Sweeping Prismatic Light Ribbons (宏大的多层半透明彩虹棱镜光带桥)
    draw_sweeping_prismatic_ribbons(ctx, shift_x=mid_shift_x, shift_y=mid_shift_y)

    # 4. Staggered Upper-Right Stained-Glass Chime Bells (右上方高低错落的琉璃风铃)
    draw_stained_glass_bell(
        ctx,
        1345.0 + mid_shift_x,
        275.0 + mid_shift_y,
        scale=0.54,
        swing_deg=-9.0,
        palette_shift=1,
        resonant_glow=True,
    )
    draw_stained_glass_bell(
        ctx,
        1540.0 + mid_shift_x,
        165.0 + mid_shift_y,
        scale=0.44,
        swing_deg=7.5,
        palette_shift=2,
        resonant_glow=True,
    )

    # 5. Giant Stained-Glass Cathedral Bell on the Left (cx=520, cy=380)
    bell_cx = 520.0 + mid_shift_x
    bell_cy = 380.0 + mid_shift_y
    draw_stained_glass_bell(ctx, bell_cx, bell_cy, scale=1.12, swing_deg=11.5, palette_shift=0)

    # 6. Concentric Stained-Glass Acoustic Shockwaves & Bell Rope
    strike_x = 596.0 + mid_shift_x
    strike_y = 460.0 + mid_shift_y

    # Determine Slime screen coordinates
    if state and "slime" in state:
        sl = state["slime"]
        if "sx" in sl and "sy" in sl:
            slime_sx, slime_sy = float(sl["sx"]), float(sl["sy"])
        else:
            slime_sx = float(sl.get("cx", 1140.0)) - center_x + W * 0.5
            slime_sy = float(sl.get("cy", 1550.0)) - center_y + H * 0.5
        slime_r = float(sl.get("radius", 68.0))
        slime_squash = float(sl.get("squash_y", 1.06))
        slime_tilt = float(sl.get("tilt", -0.10))
        slime_look = sl.get("look", (-0.44, -0.16))
        slime_eye_mode = sl.get("eye_mode", "pill")
        slime_blink = float(sl.get("blink", 0.0))
    else:
        slime_sx = 1140.0 + mid_shift_x
        slime_sy = 470.0 + mid_shift_y
        slime_r = 68.0  # Diameter = 136px (strictly within 130~140px spec!)
        slime_squash = 1.06
        slime_tilt = -0.10
        slime_look = (-0.44, -0.16)
        slime_eye_mode = "pill"
        slime_blink = 0.0

    draw_acoustic_shockwaves(ctx, strike_x, strike_y, slime_x=slime_sx, slime_y=slime_sy)

    # 7. Diagonal Volumetric God-Rays & Colored Glass Dust Motes
    draw_volumetric_god_rays(ctx, rng)

    # 8. Leading 4-Facet Stained-Glass Companion Star (✦) Ahead on the Light Bridge
    if state and "star" in state:
        st = state["star"]
        if "sx" in st and "sy" in st:
            star_sx, star_sy = float(st["sx"]), float(st["sy"])
        else:
            star_sx = float(st.get("cx", 1270.0)) - center_x + W * 0.5
            star_sy = float(st.get("cy", 1425.0)) - center_y + H * 0.5
        star_r = float(st.get("r", 36.0))
        star_rot = float(st.get("rot", 0.12))
    else:
        star_sx = 1270.0 + mid_shift_x
        star_sy = 345.0 + mid_shift_y
        star_r = 36.0
        star_rot = 0.12

    draw_star(ctx, star_sx, star_sy, star_r, rot=star_rot, t=t)

    # 9. Voronoi 28-Pane Leaded Stained-Glass Slime
    draw_slime(
        ctx,
        slime_sx,
        slime_sy,
        slime_r,
        squash_y=slime_squash,
        tilt=slime_tilt,
        look=slime_look,
        eye_mode=slime_eye_mode,
        blink=slime_blink,
        t=t,
    )

    # 10. Convert PyCairo surface to PIL Image with subtle v3 luminance polish (NO UI TAG!)
    w, h = surface.get_width(), surface.get_height()
    buf = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = buf[:, :, [2, 1, 0]].astype(np.float32) / 255.0
    rgb = np.clip(rgb * 1.04, 0.0, 1.0)
    return Image.fromarray((rgb * 255.0).astype(np.uint8), mode="RGB")


# ---------------------------------------------------------------------------
# API Contract Function: render_keyframe
# ---------------------------------------------------------------------------
def render_keyframe() -> Image.Image:
    """
    Renders the canonical 1920x1080 keyframe for World 06 (Gothic Stained-Glass Cathedral).
    """
    return render_world(960.0, 1620.0, 9.0, state=None)


if __name__ == "__main__":
    t0 = time.time()
    img = render_keyframe()
    os.makedirs(os.path.dirname(os.path.abspath(OUT_PNG)), exist_ok=True)
    img.save(OUT_PNG)
    preview_path = "/tmp/preview_06_stainedglass.jpg"
    img.resize((1280, 720), Image.Resampling.LANCZOS).save(preview_path, "JPEG", quality=80)
    print(f"Rendered World 06 keyframe in {time.time() - t0:.3f}s -> {OUT_PNG} & {preview_path}")
