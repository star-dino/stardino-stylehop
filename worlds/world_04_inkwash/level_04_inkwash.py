#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World 04 · 水墨宣纸千里长卷 (level_04_inkwash.py)
Authentic Song-Dynasty Ink-Wash & Mineral-Color Handscroll Renderer (5600x1280).

100% Faithful to `styles/style_04_inkwash.png` (计白当黑 · 墨分五色 · 气韵生动):
  - Pure, unstained handmade raw Xuan paper backdrop (#F6F2E8 -> #E6DCCA) — water and clouds
    are represented by luminous negative space (留白作水，留白作云) accented with concentric
    ink ripples, NEVER dirty grey rectangles or opaque black polygon staircases!
  - Seamless, infinite-scroll 3-layer distant misty mountains (远山淡墨晕染) dissolving into Xuan paper.
  - Zone 1: Calligraphic bamboo grove & flexing hero bamboo stalk over rippling water.
  - Zone 2: Poetic Song-dynasty brush-painted broken stone arch bridge (淡墨水晕断桥) fading into
            river mist, completed live by the suspended purple-wolf-hair Master Brush (紫毫巨笔).
  - Zone 3: Splashed-ink mud-gold lotus pads (泥金泼墨荷叶), blooming pink-white ink lotuses,
            and leaping Cinnabar Fish (朱砂写意游鱼) with wet mineral indigo & cinnabar droplets.
  - Zone 4: Calligraphic sumi-ink whirlpool purified by 360° Taiji mineral ink into a Grand
            Blooming Ink & Mud-Gold Lotus Throne.
  - Zone 5: Translucent Song-dynasty cloud-crag mountain terraces (云山墨石折枝云台) fading into
            Xuan-paper mist, cliffside ink pines, Token 4 「墨印」, and Suspended Cinnabar Seal
            Arch 「双子奇观」 full-screen antique stamp transition!
"""

import os
import sys
import math
import random
import numpy as np
import cairo
from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from styles import style_04_inkwash as st04
from worlds.world_04_inkwash.sim_04_inkwash import bridge_deck_y, clamp, lerp, smoothstep
from slime_engine import (
    cairo_to_pil,
    pil_to_cairo,
    get_pil_font,
    FONT_CJK_BOLD,
    FONT_CJK_MED,
    draw_world_token,
    draw_four_point_star,
)

W, H = 1920, 1080

_GLOBAL_PAPER_SURF = None
_GLOBAL_RED_STAMP_SURF = None
_GLOBAL_RED_STAMP_BUF = None


def get_base_paper_surface() -> cairo.ImageSurface:
    global _GLOBAL_PAPER_SURF
    if _GLOBAL_PAPER_SURF is not None:
        return _GLOBAL_PAPER_SURF
    _GLOBAL_PAPER_SURF = st04.create_xuan_paper_background(W, H, seed=108)
    return _GLOBAL_PAPER_SURF


def draw_cinnabar_gold_star_mandala(ctx: cairo.Context, cx: float, cy: float, size: float, t: float = 0.0):
    """
    Draws an ornate Song-Dynasty Cinnabar & Mud-Gold Octagonal Star Mandala (朱砂泥金八角星芒乾坤卷轴阵)
    at the mountain summit (5380, 285), replacing the old text seal.
    Pure classical mineral-cinnabar & mud-gold geometry with zero modern font characters!
    """
    r = size * 0.58
    ctx.save()
    ctx.translate(cx, cy)

    # 1. Soft Cinnabar & Mud-Gold Mineral Ink-Wash Halo dissolving into Xuan paper mist
    halo_r = r * 1.85
    g_halo = cairo.RadialGradient(0, 0, r * 0.25, 0, 0, halo_r)
    g_halo.add_color_stop_rgba(0.0, 0.78, 0.18, 0.13, 0.42)
    g_halo.add_color_stop(0.48, 0.84, 0.62, 0.22, 0.22) if hasattr(g_halo, "add_color_stop") else None
    g_halo.add_color_stop_rgba(0.50, 0.84, 0.62, 0.22, 0.20)
    g_halo.add_color_stop_rgba(1.0, 0.84, 0.62, 0.22, 0.0)
    ctx.set_source(g_halo)
    ctx.arc(0, 0, halo_r, 0, math.tau)
    ctx.fill()

    # 2. Orbiting Mud-Gold & Cinnabar Mineral Ink Motes
    for m_i in range(12):
        ang_m = t * 0.9 + m_i * (math.tau / 12.0)
        dist_m = r * (1.18 + 0.12 * math.sin(t * 2.4 + m_i * 1.7))
        mx = math.cos(ang_m) * dist_m
        my = math.sin(ang_m) * dist_m
        ctx.arc(mx, my, 3.2 if m_i % 2 == 0 else 2.2, 0, math.tau)
        if m_i % 2 == 0:
            ctx.set_source_rgba(0.95, 0.82, 0.44, 0.85)
        else:
            ctx.set_source_rgba(0.76, 0.17, 0.12, 0.78)
        ctx.fill()

    # 3. 8-Pointed Palace Octagonal Frame (two interlocking squares rotated by 45 deg)
    rot_base = t * 0.32
    sq_half = r * 0.78
    for k_sq in range(2):
        ctx.save()
        ctx.rotate(rot_base + k_sq * (math.pi * 0.25))
        ctx.rectangle(-sq_half, -sq_half, sq_half * 2.0, sq_half * 2.0)
        g_cin = cairo.RadialGradient(0, 0, sq_half * 0.1, 0, 0, sq_half * 1.4)
        g_cin.add_color_stop_rgba(0.0, 0.80, 0.19, 0.14, 0.94)
        g_cin.add_color_stop_rgba(1.0, 0.62, 0.11, 0.08, 0.94)
        ctx.set_source(g_cin)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.95, 0.82, 0.46, 0.95)
        ctx.set_line_width(3.2)
        ctx.stroke()

        # Inner mud-gold hairline border
        in_h = sq_half * 0.86
        ctx.rectangle(-in_h, -in_h, in_h * 2.0, in_h * 2.0)
        ctx.set_source_rgba(0.88, 0.68, 0.28, 0.72)
        ctx.set_line_width(1.6)
        ctx.stroke()
        ctx.restore()

    # 4. Counter-Rotating Classical Mud-Gold Lotus-Cloud Ring & Meander Motifs
    ctx.save()
    ctx.rotate(-t * 0.55)
    ring_r = r * 0.62
    ctx.arc(0, 0, ring_r, 0, math.tau)
    ctx.set_source_rgba(0.96, 0.86, 0.54, 0.90)
    ctx.set_line_width(2.4)
    ctx.stroke()

    for p_i in range(8):
        ang_p = p_i * (math.tau / 8.0)
        ctx.save()
        ctx.rotate(ang_p)
        ctx.new_path()
        ctx.move_to(ring_r * 0.58, 0)
        ctx.curve_to(ring_r * 0.78, -ring_r * 0.22, ring_r * 0.96, -ring_r * 0.12, ring_r * 0.98, 0)
        ctx.curve_to(ring_r * 0.96, ring_r * 0.12, ring_r * 0.78, ring_r * 0.22, ring_r * 0.58, 0)
        ctx.close_path()
        ctx.set_source_rgba(0.98, 0.89, 0.58, 0.32)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.98, 0.89, 0.58, 0.88)
        ctx.set_line_width(1.6)
        ctx.stroke()
        ctx.restore()
    ctx.restore()

    # 5. Centerpiece: Golden 16-Point Gemini Star Crest & Concave 4-Point Star Core (✦)
    ctx.save()
    ctx.rotate(t * 0.45)
    ctx.new_path()
    for i_st in range(16):
        rad_s = (r * 0.44) if i_st % 2 == 0 else (r * 0.19)
        ang_s = i_st * (math.tau / 16.0)
        sx = math.cos(ang_s) * rad_s
        sy = math.sin(ang_s) * rad_s
        if i_st == 0:
            ctx.move_to(sx, sy)
        else:
            ctx.line_to(sx, sy)
    ctx.close_path()
    ctx.set_source_rgba(1.0, 0.92, 0.60, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgba(1.0, 0.98, 0.88, 0.95)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.restore()

    # Inner luminous 4-point concave star core
    core_r = r * 0.26 * (1.0 + 0.08 * math.sin(t * 5.0))
    ctx.new_path()
    for k_c in range(4):
        a0 = k_c * (math.pi * 0.5)
        a1 = (k_c + 1) * (math.pi * 0.5)
        amid = a0 + math.pi * 0.25
        if k_c == 0:
            ctx.move_to(math.cos(a0) * core_r, math.sin(a0) * core_r)
        ctx. quadratic_to(
            math.cos(amid) * (core_r * 0.25),
            math.sin(amid) * (core_r * 0.25),
            math.cos(a1) * core_r,
            math.sin(a1) * core_r,
        ) if hasattr(ctx, "quadratic_to") else ctx.curve_to(
            math.cos(amid) * (core_r * 0.28),
            math.sin(amid) * (core_r * 0.28),
            math.cos(amid) * (core_r * 0.28),
            math.sin(amid) * (core_r * 0.28),
            math.cos(a1) * core_r,
            math.sin(a1) * core_r,
        )
    ctx.close_path()
    ctx.set_source_rgba(1.0, 0.99, 0.94, 0.98)
    ctx.fill()

    ctx.restore()


def _draw_gold_foil_origami_crane(ctx: cairo.Context, cx: float, cy: float, scale: float, alpha: float):
    """Draws an embossed Gold-Foil Origami Paper Crane emblem on the Cinnabar Hardcover Book Cover."""
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(scale, scale)

    # Geometric origami crane facets: (pts, gold_rgb_alpha)
    facets = [
        # Left Rear Wing
        ([(-18, -8), (-88, -62), (-32, -28)], (0.86, 0.65, 0.24, 0.85 * alpha)),
        # Body Central Diamond
        ([(-28, 6), (0, -24), (28, 4), (0, 22)], (0.95, 0.78, 0.38, 0.95 * alpha)),
        # Neck & Head (Right)
        ([(18, -2), (56, -48), (44, -52), (8, -10)], (0.98, 0.86, 0.48, 0.96 * alpha)),
        # Beak
        ([(56, -48), (74, -40), (48, -42)], (1.0, 0.94, 0.68, 0.98 * alpha)),
        # Tail (Left)
        ([(-22, 2), (-72, -36), (-54, -8)], (0.90, 0.70, 0.30, 0.92 * alpha)),
        # Foreground Sweeping Wing
        ([(-14, -4), (42, -74), (16, 12)], (1.0, 0.91, 0.56, 0.98 * alpha)),
    ]
    for pts, rgba in facets:
        ctx.new_path()
        ctx.move_to(pts[0][0], pts[0][1])
        for px, py in pts[1:]:
            ctx.line_to(px, py)
        ctx.close_path()
        ctx.set_source_rgba(*rgba)
        ctx.fill_preserve()
        ctx.set_source_rgba(1.0, 0.97, 0.82, 0.92 * alpha)
        ctx.set_line_width(2.0)
        ctx.stroke()

    ctx.restore()


def draw_cinnabar_book_cover_transition(ctx: cairo.Context, ox: float, oy: float, state: dict, t: float):
    """
    Smoothly transitions from the Summit Cinnabar & Mud-Gold Star Mandala (5380, 285)
    into the exact Cinnabar & Gold-Foil Hardcover Pop-Up Book Cover of World 05!
    - Phase 1 (slam_prog 0.0 -> 0.75): Radial Cinnabar & Mud-Gold ink-wash bloom expands from the Mandala center.
    - Phase 2 (slam_prog 0.25 -> 1.00): Double Gold-Foil Border, Spine Groove, 16-Point Gemini Star Crest,
      and Embossed Gold-Foil Origami Crane & Mountain Scrollwork gleam into place, matching World 05 Frame 1!
    """
    s_st = state["seal"]
    prog = s_st["slam_prog"]
    if prog <= 0.001:
        return

    scx = s_st["x"] - ox
    scy = s_st["y"] - oy

    ctx.save()

    # 1. Expanding Cinnabar Book-Cloth Radial Wash from Mandala Center (scx, scy) -> Screen Center (960, 540)
    wash_u = clamp(prog / 0.65, 0.0, 1.0)
    ease_w = smoothstep(0.0, 1.0, wash_u)
    cur_cx = lerp(scx, 960.0, ease_w)
    cur_cy = lerp(scy, 540.0, ease_w)
    max_r = lerp(95.0, 1450.0, ease_w ** 0.85)

    if wash_u < 0.999:
        # Expanding feathered cinnabar & gold ink-wash wave
        g_wave = cairo.RadialGradient(cur_cx, cur_cy, max_r * 0.1, cur_cx, cur_cy, max_r)
        g_wave.add_color_stop_rgba(0.00, 0.788, 0.184, 0.133, 1.0)
        g_wave.add_color_stop_rgba(0.62, 0.722, 0.157, 0.110, 0.98)
        g_wave.add_color_stop_rgba(0.86, 0.459, 0.075, 0.051, 0.92)
        g_wave.add_color_stop_rgba(0.94, 0.890, 0.720, 0.320, 0.65)
        g_wave.add_color_stop_rgba(1.00, 0.722, 0.157, 0.110, 0.0)
        ctx.set_source(g_wave)
        ctx.arc(cur_cx, cur_cy, max_r, 0, math.tau)
        ctx.fill()
    else:
        # Exact World 05 Hardcover Cinnabar Book-Cloth Radial Gradient (#C92F22 -> #B8281C -> #75130D)
        bg_grad = cairo.RadialGradient(960.0, 540.0, 150.0, 960.0, 540.0, 1100.0)
        bg_grad.add_color_stop_rgba(0.00, 201 / 255.0, 47 / 255.0, 34 / 255.0, 1.0)
        bg_grad.add_color_stop_rgba(0.65, 184 / 255.0, 40 / 255.0, 28 / 255.0, 1.0)
        bg_grad.add_color_stop_rgba(1.00, 117 / 255.0, 19 / 255.0, 13 / 255.0, 1.0)
        ctx.set_source(bg_grad)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()

    # 2. Hardcover Book Cloth Weave, Left Spine Groove & Gold-Foil Cover Ornaments (World 05 Match-Cut!)
    foil_a = smoothstep(0.28, 0.88, prog)
    if foil_a > 0.01:
        # Subtle horizontal book cloth texture lines (matching World 05 render_stage.html lines 158-161)
        ctx.set_source_rgba(1.0, 0.90, 0.70, 0.035 * foil_a)
        for y_line in range(0, H, 4):
            ctx.rectangle(0, y_line, W, 1)
        ctx.fill()

        # Left book spine groove shadow (x = 0..100, matching World 05 render_stage.html lines 164-169)
        spine_grad = cairo.LinearGradient(0.0, 0.0, 100.0, 0.0)
        spine_grad.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.70 * foil_a)
        spine_grad.add_color_stop_rgba(0.6, 0.0, 0.0, 0.0, 0.20 * foil_a)
        spine_grad.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        ctx.set_source(spine_grad)
        ctx.rectangle(0, 0, 100, H)
        ctx.fill()

        # Double Gold-Foil Border ([96, 64, 1728, 952] & [108, 76, 1704, 928])
        ctx.set_source_rgba(243 / 255.0, 210 / 255.0, 121 / 255.0, foil_a)
        ctx.set_line_width(4.0)
        ctx.rectangle(96.0, 64.0, W - 192.0, H - 128.0)
        ctx.stroke()

        ctx.set_source_rgba(217 / 255.0, 169 / 255.0, 72 / 255.0, foil_a)
        ctx.set_line_width(2.0)
        ctx.rectangle(108.0, 76.0, W - 216.0, H - 152.0)
        ctx.stroke()

        # Classical Gold-Foil Cloud-Meander Corner Ornaments & Corner Medallions
        corners = [
            (96.0, 64.0, 1.0, 1.0),
            (W - 96.0, 64.0, -1.0, 1.0),
            (96.0, H - 64.0, 1.0, -1.0),
            (W - 96.0, H - 64.0, -1.0, -1.0),
        ]
        for ccx, ccy, sx_c, sy_c in corners:
            ctx.arc(ccx, ccy, 12.0, 0, math.tau)
            ctx.set_source_rgba(1.0, 0.898, 0.60, foil_a)
            ctx.fill()
            # Inner classical meander bracket
            ctx.new_path()
            ctx.move_to(ccx + sx_c * 24.0, ccy + sy_c * 58.0)
            ctx.line_to(ccx + sx_c * 24.0, ccy + sy_c * 24.0)
            ctx.line_to(ccx + sx_c * 58.0, ccy + sy_c * 24.0)
            ctx.move_to(ccx + sx_c * 34.0, ccy + sy_c * 44.0)
            ctx.line_to(ccx + sx_c * 34.0, ccy + sy_c * 34.0)
            ctx.line_to(ccx + sx_c * 44.0, ccy + sy_c * 34.0)
            ctx.set_source_rgba(243 / 255.0, 210 / 255.0, 121 / 255.0, 0.88 * foil_a)
            ctx.set_line_width(2.5)
            ctx.stroke()

        # Top Golden 16-Point Gemini Star Crest at (960, 390) (matching World 05 cover!)
        ctx.save()
        ctx.translate(960.0, 390.0)
        g_star_glow = cairo.RadialGradient(0, 0, 8.0, 0, 0, 88.0)
        g_star_glow.add_color_stop_rgba(0.0, 1.0, 0.92, 0.60, 0.55 * foil_a)
        g_star_glow.add_color_stop_rgba(1.0, 0.83, 0.63, 0.20, 0.0)
        ctx.set_source(g_star_glow)
        ctx.arc(0, 0, 88.0, 0, math.tau)
        ctx.fill()

        ctx.new_path()
        for i_s in range(16):
            r_s = 56.0 if i_s % 2 == 0 else 24.0
            ang_s = i_s * (math.pi / 8.0)
            x_s = r_s * math.sin(ang_s)
            y_s = -r_s * math.cos(ang_s)
            if i_s == 0:
                ctx.move_to(x_s, y_s)
            else:
                ctx.line_to(x_s, y_s)
        ctx.close_path()
        ctx.set_source_rgba(1.0, 0.922, 0.60, foil_a)
        ctx.fill()

        # Twin 4-point star emblems flanking the 16-point star crest
        for side_x in (-72.0, 72.0):
            draw_four_point_star(ctx, side_x, 0.0, 14.0)
            ctx.set_source_rgba(1.0, 0.97, 0.88, foil_a)
            ctx.fill()
        ctx.restore()

        # Centerpiece Gold-Foil Origami Valley Medallion (Origami Paper Cranes + Folded Sun & Mountains)
        ctx.save()
        ctx.translate(960.0, 610.0)
        # Double concentric gold-foil medallion ring
        ctx.arc(0, 0, 138.0, 0, math.tau)
        ctx.set_source_rgba(243 / 255.0, 210 / 255.0, 121 / 255.0, 0.88 * foil_a)
        ctx.set_line_width(3.0)
        ctx.stroke()
        ctx.arc(0, 0, 128.0, 0, math.tau)
        ctx.set_source_rgba(217 / 255.0, 169 / 255.0, 72 / 255.0, 0.65 * foil_a)
        ctx.set_line_width(1.5)
        ctx.stroke()

        # Gold-foil origami mountain ridges inside medallion
        for m_pts, m_a in [
            ([(-115, 42), (-52, -18), (8, 28), (64, -26), (115, 42)], 0.32),
            ([(-98, 56), (-22, 4), (44, 42), (98, 56)], 0.48),
        ]:
            ctx.new_path()
            ctx.move_to(m_pts[0][0], m_pts[0][1])
            for px, py in m_pts[1:]:
                ctx.line_to(px, py)
            ctx.close_path()
            ctx.set_source_rgba(0.95, 0.78, 0.36, m_a * foil_a)
            ctx.fill_preserve()
            ctx.set_source_rgba(1.0, 0.92, 0.62, 0.85 * foil_a)
            ctx.set_line_width(2.0)
            ctx.stroke()

        # Embossed Gold-Foil Hero Origami Crane soaring at the center of the medallion
        _draw_gold_foil_origami_crane(ctx, -6.0, -4.0, 1.08, foil_a)
        _draw_gold_foil_origami_crane(ctx, -78.0, -42.0, 0.48, 0.85 * foil_a)
        _draw_gold_foil_origami_crane(ctx, 76.0, -36.0, 0.45, 0.85 * foil_a)

        # Flanking horizontal gold-foil scroll rules with diamond terminals
        for dir_s in (-1.0, 1.0):
            x0_r = dir_s * 168.0
            x1_r = dir_s * 420.0
            ctx.new_path()
            ctx.move_to(x0_r, 0.0)
            ctx.line_to(x1_r, 0.0)
            ctx.set_source_rgba(243 / 255.0, 210 / 255.0, 121 / 255.0, 0.82 * foil_a)
            ctx.set_line_width(2.2)
            ctx.stroke()
            for dx_d, r_d in [(x0_r, 7.0), (dir_s * 290.0, 5.0), (x1_r, 7.0)]:
                ctx.new_path()
                ctx.move_to(dx_d, -r_d)
                ctx.line_to(dx_d + r_d * 1.4, 0.0)
                ctx.line_to(dx_d, r_d)
                ctx.line_to(dx_d - r_d * 1.4, 0.0)
                ctx.close_path()
                ctx.set_source_rgba(1.0, 0.92, 0.60, 0.92 * foil_a)
                ctx.fill()
        ctx.restore()

    ctx.restore()


# ==============================================================================
# 1. CONTINUOUS 3-LAYER SONG-DYNASTY DISTANT MOUNTAINS (远山淡墨水晕 · 零断茬)
# ==============================================================================
def draw_continuous_scroll_mountains(ctx: cairo.Context, ox: float, oy: float):
    """
    Renders 3 continuous parallax layers of Song-dynasty pine-soot & mineral-indigo mountains
    across the entire viewport [0, W] with soft translucent washes that dissolve into
    the Xuan paper mist (alpha -> 0.0) and ZERO vertical cutoffs!
    """
    layers = [
        # (parallax, base_y, amp, period, ink_rgba, mist_h, with_details)
        (0.18, 225.0, 75.0, 380.0, (0.38, 0.38, 0.43, 0.17), 190.0, False),  # Far ethereal peak
        (0.32, 305.0, 95.0, 290.0, (0.29, 0.28, 0.34, 0.26), 210.0, False),  # Mid mountain ridge
        (0.46, 400.0, 108.0, 225.0, (0.20, 0.19, 0.23, 0.34), 230.0, True),  # Near crags with moss dots
    ]

    x_screen_pts = np.linspace(-60.0, W + 60.0, 140)

    for p_fac, base_y, amp, period, ink, mist_h, with_details in layers:
        ctx.save()
        ctx.new_path()
        by_scr = base_y - oy * p_fac
        ctx.move_to(-60.0, H * 0.72)
        for sx in x_screen_pts:
            wx = sx + ox * p_fac
            s1 = math.sin(wx / period + 0.5)
            s2 = 0.45 * math.sin(wx / (period * 0.48) + 1.2)
            s3 = 0.22 * math.cos(wx / (period * 0.22) - 0.8)
            wy = by_scr + amp * (s1 + s2 + s3)
            ctx.line_to(sx, wy)
        ctx.line_to(W + 60.0, H * 0.72)
        ctx.close_path()

        grad = cairo.LinearGradient(0, by_scr - amp, 0, by_scr + mist_h)
        grad.add_color_stop_rgba(0.00, ink[0], ink[1], ink[2], ink[3])
        grad.add_color_stop_rgba(0.45, ink[0], ink[1], ink[2], ink[3] * 0.70)
        grad.add_color_stop_rgba(1.00, ink[0], ink[1], ink[2], 0.0)
        ctx.set_source(grad)
        ctx.fill()

        # Subtle calligraphic moss dots (淡墨苔点) on the nearer mountain ridge
        if with_details:
            cell_w = period * 0.5
            k_min = int(math.floor((ox * p_fac - 100.0) / cell_w))
            k_max = int(math.ceil((ox * p_fac + W + 100.0) / cell_w))
            for k in range(k_min, k_max + 1):
                wx_peak = k * cell_w + 40.0
                sx_peak = wx_peak - ox * p_fac
                if -80.0 <= sx_peak <= W + 80.0:
                    s1 = math.sin(wx_peak / period + 0.5)
                    s2 = 0.45 * math.sin(wx_peak / (period * 0.48) + 1.2)
                    s3 = 0.22 * math.cos(wx_peak / (period * 0.22) - 0.8)
                    py = by_scr + amp * (s1 + s2 + s3)
                    rng_m = random.Random(k * 97 + 13)
                    for _ in range(7):
                        dx_m = rng_m.uniform(-35.0, 35.0)
                        dy_m = rng_m.uniform(-6.0, 18.0)
                        r_m = rng_m.uniform(1.8, 3.5)
                        ctx.arc(sx_peak + dx_m, py + dy_m, r_m, 0, math.tau)
                        ctx.set_source_rgba(0.18, 0.17, 0.20, rng_m.uniform(0.18, 0.36))
                        ctx.fill()
        ctx.restore()

    # Distant misty broken bridge silhouette in far background (烟波远桥意象)
    bg_br_x = 1120.0 - ox * 0.38
    bg_br_y = 435.0 - oy * 0.38
    if -400.0 < bg_br_x < W + 200.0:
        st04.draw_misty_broken_bridge(ctx, bg_br_x, bg_br_y, scale=0.62, alpha_mul=0.45)

    # Flowing negative-space mist ribbons (横向游云飞白)
    for cloud_y, cloud_h, cloud_a in [
        (275.0, 48.0, 0.18),
        (365.0, 56.0, 0.22),
        (465.0, 72.0, 0.30),
    ]:
        ctx.save()
        cy_scr = cloud_y - oy * 0.35
        c_grad = cairo.LinearGradient(0, cy_scr - cloud_h * 0.5, 0, cy_scr + cloud_h * 0.5)
        c_grad.add_color_stop_rgba(0.0, 0.96, 0.94, 0.88, 0.0)
        c_grad.add_color_stop_rgba(0.5, 0.97, 0.95, 0.90, cloud_a)
        c_grad.add_color_stop_rgba(1.0, 0.96, 0.94, 0.88, 0.0)
        ctx.set_source(c_grad)
        ctx.rectangle(0, cy_scr - cloud_h * 0.5, W, cloud_h)
        ctx.fill()
        ctx.restore()


# ==============================================================================
# 2. DYNAMIC CALLIGRAPHIC QI-YUN MOTION TRAIL (动态行笔飞白与花青朱砂气韵尾迹)
# ==============================================================================
def draw_dynamic_slime_ink_trail(ctx: cairo.Context, trail_pts: list, t: float):
    """
    Renders a living, tapering calligraphic brush-and-cinnabar trail following
    the Slime's recent airborne trajectory (`trail_pts`), plus wet mineral-indigo
    and cinnabar ink droplets with Xuan-paper bleed halos!
    """
    n = len(trail_pts)
    if n < 3:
        return

    ctx.save()
    # 1. Soft mineral-indigo outer wash along trail
    for i in range(n - 1):
        u = (i + 1) / float(n)
        p0 = trail_pts[i]
        p1 = trail_pts[i + 1]
        ctx.new_path()
        ctx.move_to(p0[0], p0[1])
        ctx.line_to(p1[0], p1[1])
        ctx.set_source_rgba(0.16, 0.32, 0.46, 0.18 * (u ** 1.4))
        ctx.set_line_width(28.0 * u)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

        # Core sumi-ink dry brush stroke
        ctx.new_path()
        ctx.move_to(p0[0], p0[1])
        ctx.line_to(p1[0], p1[1])
        ctx.set_source_rgba(0.10, 0.10, 0.12, 0.52 * (u ** 1.3))
        ctx.set_line_width(10.5 * u)
        ctx.stroke()

        # Cinnabar energy thread
        ctx.new_path()
        ctx.move_to(p0[0], p0[1] - 5.0)
        ctx.line_to(p1[0], p1[1] - 5.0)
        ctx.set_source_rgba(0.82, 0.24, 0.16, 0.58 * (u ** 1.2))
        ctx.set_line_width(3.8 * u)
        ctx.stroke()

    # 2. Splashing mineral indigo (花青), cinnabar (朱砂), and sumi droplets around the trail
    for idx in range(0, n, 2):
        u = (idx + 1) / float(n)
        px, py = trail_pts[idx]
        rng_d = random.Random(int(px * 13 + py * 7))
        for _ in range(3):
            dx = rng_d.uniform(-42.0, 42.0)
            dy = rng_d.uniform(-34.0, 34.0)
            r = rng_d.uniform(2.2, 6.5) * u
            col = rng_d.choice([
                (0.15, 0.36, 0.54, 0.85 * u),  # 花青
                (0.82, 0.24, 0.16, 0.88 * u),  # 朱砂
                (0.10, 0.10, 0.12, 0.82 * u),  # 焦墨
            ])
            if r > 3.5:
                ctx.arc(px + dx, py + dy, r * 1.75, 0, math.tau)
                ctx.set_source_rgba(col[0], col[1], col[2], col[3] * 0.22)
                ctx.fill()
            ctx.arc(px + dx, py + dy, r, 0, math.tau)
            ctx.set_source_rgba(*col)
            ctx.fill()

    ctx.restore()


# ==============================================================================
# 3. ZONE 1: BAMBOO GROVE & RIPPLING WATER TOUCH (青竹折枝与水墨涟漪)
# ==============================================================================
def draw_zone1_bamboo_grove(ctx: cairo.Context, bamboo_st: dict, t: float):
    """
    Renders the Zone 1 Calligraphic Bamboo Grove & Flexing Hero Stalk
    directly on the luminous Xuan paper (matching `style_04_inkwash.png` 100%),
    with concentric water ripples and a small splashed-ink lotus pad beneath the bamboo!
    """
    ctx.save()

    # Concentric water ripples beneath the flexing bamboo tip (exactly like style_04_inkwash.png!)
    st04.draw_ink_ripples(ctx, 765.0, 755.0, max_r=180.0, alpha_gain=1.0)
    st04.draw_splashed_lotus_pad(
        ctx, 945.0, 785.0, scale_x=1.16, scale_y=0.52, base_rad=88.0, seed=3, alpha_gain=0.82, gold_veins=True
    )

    # Calligraphic Bamboo Grove & Flexing Hero Stalk (world ox = 0.0!)
    st04.draw_bamboo_grove(ctx, ox=0.0, bend=bamboo_st["bend"], vib=bamboo_st["vib"])

    ctx.restore()


# ==============================================================================
# 4. ZONE 2: POETIC SONG-DYNASTY BRUSH-PAINTED STONE ARCH BRIDGE & MASTER BRUSH
# ==============================================================================
def draw_poetic_stone_arch_bridge(ctx: cairo.Context, drawn_progress: float, t: float):
    """
    Renders the Zone 2 Song-Dynasty Broken Stone Arch Bridge (烟波断桥, x in [1480, 2520])
    in the authentic wet-ink wash & calligraphic brush-stroke style of `st04.draw_misty_broken_bridge`:
      - Soft, translucent sumi & mineral-indigo ink wash that dissolves into the
        Xuan-paper river mist at the bottom (alpha -> 0.0, ZERO hard grey CAD blocks!).
      - Concentric ink ripples on the Xuan-paper water beneath the arch.
      - Expressive tapered calligraphic brush lines for the double arch ring, stone courses,
        and lotus-finial balustrade posts!
    """
    ctx.save()
    arch_cx = 2000.0
    arch_cy = 770.0
    arch_r = 185.0

    # Concentric water ripples beneath the bridge arch on the Xuan-paper river
    st04.draw_ink_ripples(ctx, 1740.0, 765.0, max_r=170.0, alpha_gain=0.75)
    st04.draw_ink_ripples(ctx, 2240.0, 775.0, max_r=165.0, alpha_gain=0.65 * max(0.3, drawn_progress))

    # Faint dry-brush phantom sketch on right span before the Master Brush paints it
    if drawn_progress < 0.99:
        ctx.save()
        ctx.set_dash([12.0, 10.0], 0.0)
        ctx.new_path()
        for sx in np.linspace(2000.0, 2520.0, 24):
            sy = bridge_deck_y(sx)
            if sx == 2000.0:
                ctx.move_to(sx, sy)
            else:
                ctx.line_to(sx, sy)
        ctx.set_source_rgba(0.28, 0.27, 0.32, 0.28 * (1.0 - drawn_progress))
        ctx.set_line_width(2.0)
        ctx.stroke()
        ctx.restore()

    max_bridge_x = 2000.0 + drawn_progress * 520.0

    # Clip with an organic jagged stone fracture contour when broken, or full span when completed
    ctx.save()
    ctx.new_path()
    ctx.move_to(1440.0, 440.0)
    ctx.line_to(max_bridge_x + 4.0, 440.0)
    if drawn_progress < 0.98:
        # Weathered broken stone steps & diagonal mist fracture instead of a vertical knife cut!
        ctx.line_to(max_bridge_x + 2.0, 562.0)
        ctx.line_to(max_bridge_x - 14.0, 578.0)
        ctx.line_to(max_bridge_x - 6.0, 596.0)
        ctx.line_to(max_bridge_x - 28.0, 622.0)
        ctx.line_to(max_bridge_x - 52.0, 665.0)
        ctx.line_to(max_bridge_x - 95.0, 755.0)
    else:
        ctx.line_to(max_bridge_x + 20.0, 760.0)
    ctx.line_to(1440.0, 760.0)
    ctx.close_path()
    ctx.clip()

    # 1. Poetic Translucent Wet-Ink Wash Bridge Spandrel (fading into Xuan-paper mist at bottom y=745!)
    # Note: Inner arch vault is left as pure Xuan-paper negative space (留白拱洞)!
    ctx.new_path()
    xs_top = np.linspace(1480.0, 2520.0, 60)
    ctx.move_to(1480.0, 745.0)
    for x_pt in xs_top:
        ctx.line_to(x_pt, bridge_deck_y(x_pt))
    ctx.line_to(2520.0, 745.0)
    # Subtract inner arch vault opening cleanly
    ctx.line_to(arch_cx + arch_r, 745.0)
    ctx.arc_negative(arch_cx, arch_cy, arch_r, 0.0, math.pi)
    ctx.line_to(1480.0, 745.0)
    ctx.close_path()

    g_wash = cairo.LinearGradient(0, 555.0, 0, 745.0)
    g_wash.add_color_stop_rgba(0.00, 0.16, 0.22, 0.28, 0.62)  # 淡花青墨韵桥脊
    g_wash.add_color_stop_rgba(0.50, 0.20, 0.21, 0.26, 0.38)  # 松烟水晕中段
    g_wash.add_color_stop_rgba(0.85, 0.24, 0.24, 0.28, 0.12)  # 桥脚烟波消融
    g_wash.add_color_stop_rgba(1.00, 0.26, 0.25, 0.30, 0.00)  # 底部完全融于宣纸留白烟波!
    ctx.set_source(g_wash)
    ctx.fill()

    # 2. Subtle Stone Course Masonry Lines on the Bridge Spandrel (宋画石桥券石肌理)
    for row_y in [605.0, 632.0, 660.0, 688.0]:
        for seg_x in range(1520, 2460, 75):
            if abs(seg_x - arch_cx) < arch_r * 0.82 and row_y > 610.0:
                continue
            if row_y > bridge_deck_y(seg_x) + 14.0:
                ctx.new_path()
                ctx.move_to(seg_x, row_y)
                ctx.line_to(seg_x + 48.0, row_y)
                ctx.set_source_rgba(0.14, 0.15, 0.18, 0.28)
                ctx.set_line_width(1.4)
                ctx.stroke()

    # 3. Expressive Calligraphic Double-Line Deck & Arch Ring (书法中锋双勾桥面与拱券)
    ctx.new_path()
    for i, x_pt in enumerate(xs_top):
        if i == 0:
            ctx.move_to(x_pt, bridge_deck_y(x_pt))
        else:
            ctx.line_to(x_pt, bridge_deck_y(x_pt))
    ctx.set_source_rgba(0.10, 0.10, 0.13, 0.90)
    ctx.set_line_width(5.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()

    # Secondary lower deck molding stroke (matching st04.draw_misty_broken_bridge!)
    ctx.new_path()
    for i, x_pt in enumerate(xs_top):
        y_low = bridge_deck_y(x_pt) + 16.0
        if i == 0:
            ctx.move_to(x_pt + 18.0, y_low)
        else:
            ctx.line_to(x_pt, y_low)
    ctx.set_source_rgba(0.16, 0.16, 0.20, 0.68)
    ctx.set_line_width(2.8)
    ctx.stroke()

    # Mud-gold & cinnabar subtle accent thread along bridge deck
    ctx.new_path()
    for i, x_pt in enumerate(xs_top):
        if i == 0:
            ctx.move_to(x_pt, bridge_deck_y(x_pt) + 4.5)
        else:
            ctx.line_to(x_pt, bridge_deck_y(x_pt) + 4.5)
    ctx.set_source_rgba(0.86, 0.68, 0.24, 0.58)
    ctx.set_line_width(1.8)
    ctx.stroke()

    # Calligraphic Arch Ring & Voussoir Ticks (写意拱券墨线)
    ctx.new_path()
    ctx.arc(arch_cx, arch_cy, arch_r, math.pi * 1.08, math.pi * 1.92)
    ctx.set_source_rgba(0.10, 0.11, 0.14, 0.86)
    ctx.set_line_width(3.8)
    ctx.stroke()

    ctx.new_path()
    ctx.arc(arch_cx, arch_cy, arch_r + 22.0, math.pi * 1.10, math.pi * 1.90)
    ctx.set_source_rgba(0.16, 0.17, 0.21, 0.60)
    ctx.set_line_width(2.2)
    ctx.stroke()

    for vi in range(13):
        ang_v = math.pi * 1.12 + (vi / 12.0) * (math.pi * 0.76)
        ctx.new_path()
        ctx.move_to(arch_cx + arch_r * math.cos(ang_v), arch_cy + arch_r * math.sin(ang_v))
        ctx.line_to(arch_cx + (arch_r + 22.0) * math.cos(ang_v), arch_cy + (arch_r + 22.0) * math.sin(ang_v))
        ctx.set_source_rgba(0.14, 0.14, 0.18, 0.55)
        ctx.set_line_width(1.8)
        ctx.stroke()

    # 4. Poetic Song-Dynasty Balustrade Posts & Railing (写意莲柱石栏)
    post_xs = [1540.0, 1650.0, 1760.0, 1870.0, 1980.0, 2020.0, 2130.0, 2240.0, 2350.0, 2460.0]
    for pi, px in enumerate(post_xs):
        py = bridge_deck_y(px)
        ctx.new_path()
        ctx.move_to(px, py)
        ctx.line_to(px, py - 26.0)
        ctx.set_source_rgba(0.12, 0.12, 0.15, 0.85)
        ctx.set_line_width(3.2)
        ctx.stroke()

        # Lotus finial dot
        ctx.arc(px, py - 29.0, 3.8, 0, math.tau)
        ctx.set_source_rgba(0.14, 0.14, 0.18, 0.90)
        ctx.fill()

        if pi < len(post_xs) - 1 and pi != 4:
            nx = post_xs[pi + 1]
            ny = bridge_deck_y(nx)
            mx = 0.5 * (px + nx)
            my = bridge_deck_y(mx)
            ctx.new_path()
            ctx.move_to(px, py - 20.0)
            ctx.curve_to(mx, my - 20.0, mx, my - 20.0, nx, ny - 20.0)
            ctx.set_source_rgba(0.16, 0.16, 0.20, 0.72)
            ctx.set_line_width(2.2)
            ctx.stroke()

    # 5. Calligraphic Moss Dots along the Bridge Arch
    rng_br = random.Random(2026)
    for _ in range(24):
        mx = rng_br.uniform(1520.0, 2480.0)
        my = bridge_deck_y(mx) + rng_br.uniform(6.0, 42.0)
        ctx.arc(mx, my, rng_br.uniform(1.8, 3.8), 0, math.tau)
        ctx.set_source_rgba(0.10, 0.12, 0.15, rng_br.uniform(0.45, 0.78))
        ctx.fill()

    ctx.restore()  # End horizontal reveal clip

    # 6. Soft Xuan-Paper River Mist Puff Veiling the Broken Fracture Edge (断桥残烟留白晕染)
    if drawn_progress < 0.98:
        edge_x = max_bridge_x
        edge_y = bridge_deck_y(edge_x) + 32.0
        mist_g = cairo.RadialGradient(edge_x + 10.0, edge_y + 18.0, 12.0, edge_x + 10.0, edge_y + 18.0, 95.0)
        mist_g.add_color_stop_rgba(0.0, 0.95, 0.92, 0.85, 0.78 * (1.0 - drawn_progress))
        mist_g.add_color_stop_rgba(0.55, 0.95, 0.92, 0.85, 0.38 * (1.0 - drawn_progress))
        mist_g.add_color_stop_rgba(1.0, 0.95, 0.92, 0.85, 0.0)
        ctx.set_source(mist_g)
        ctx.arc(edge_x + 10.0, edge_y + 18.0, 95.0, 0, math.tau)
        ctx.fill()

        # Rugged broken stonedry-brush strokes at the fracture tip
        ctx.new_path()
        ctx.move_to(edge_x, bridge_deck_y(edge_x))
        ctx.line_to(edge_x - 14.0, bridge_deck_y(edge_x) + 18.0)
        ctx.line_to(edge_x - 6.0, bridge_deck_y(edge_x) + 36.0)
        ctx.set_source_rgba(0.12, 0.12, 0.15, 0.72 * (1.0 - drawn_progress))
        ctx.set_line_width(3.2)
        ctx.stroke()

    # 7. Wet Ink & Mineral-Indigo Splash Droplets at the Active Brush Edge (when 0 < drawn_progress < 0.99)
    if 0.01 < drawn_progress < 0.99:
        edge_x = max_bridge_x
        edge_y = bridge_deck_y(edge_x)
        rng_sp = random.Random(int(drawn_progress * 100))
        for _ in range(14):
            dx = rng_sp.uniform(-28.0, 28.0)
            dy = rng_sp.uniform(-35.0, 45.0)
            r = rng_sp.uniform(2.5, 6.8)
            col = rng_sp.choice([
                (0.10, 0.10, 0.12, 0.88),
                (0.16, 0.36, 0.54, 0.85),
                (0.90, 0.72, 0.24, 0.85),
            ])
            ctx.arc(edge_x + dx, edge_y + dy, r, 0, math.tau)
            ctx.set_source_rgba(*col)
            ctx.fill()

    ctx.restore()


def draw_master_calligraphy_brush(ctx: cairo.Context, b_st: dict, t: float):
    """
    Renders the suspended Master Wolf-Hair Calligraphic Brush (悬空紫毫巨笔):
      - Spotted bamboo shaft with gold-inlaid ox-horn ferrule
      - Plump purple-wolf hair tuft (紫毫笔锋) with glowing mud-gold & sumi ink aura
    """
    bx = b_st["x"]
    by = b_st["y"]
    ang = b_st["ang"]
    state = b_st["state"]
    if by < -240.0:
        return

    ctx.save()
    ctx.translate(bx, by)
    ctx.rotate(ang)

    # Ethereal Mud-Gold Halo around the Brush Tuft
    aura_g = cairo.RadialGradient(0, 125.0, 8.0, 0, 125.0, 90.0)
    aura_g.add_color_stop_rgba(0.0, 0.94, 0.78, 0.28, 0.38 if state != "painting" else 0.68)
    aura_g.add_color_stop_rgba(0.6, 0.22, 0.38, 0.52, 0.15)
    aura_g.add_color_stop_rgba(1.0, 0.18, 0.28, 0.40, 0.0)
    ctx.set_source(aura_g)
    ctx.arc(0, 125.0, 90.0, 0, math.tau)
    ctx.fill()

    # 1. Bamboo Shaft (湘妃竹笔杆)
    ctx.new_path()
    ctx.move_to(-10.5, -230.0)
    ctx.line_to(-12.5, 0.0)
    ctx.line_to(12.5, 0.0)
    ctx.line_to(10.5, -230.0)
    ctx.close_path()
    g_shaft = cairo.LinearGradient(-12.5, 0, 12.5, 0)
    g_shaft.add_color_stop_rgba(0.0, 0.36, 0.25, 0.16, 0.96)
    g_shaft.add_color_stop_rgba(0.42, 0.68, 0.54, 0.36, 0.96)
    g_shaft.add_color_stop_rgba(1.0, 0.24, 0.16, 0.10, 0.96)
    ctx.set_source(g_shaft)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.10, 0.08, 0.06, 0.90)
    ctx.set_line_width(2.0)
    ctx.stroke()

    for jy in [-75.0, -155.0]:
        ctx.new_path()
        ctx.move_to(-12.0, jy)
        ctx.line_to(12.0, jy)
        ctx.set_source_rgba(0.22, 0.14, 0.08, 0.82)
        ctx.set_line_width(2.8)
        ctx.stroke()

    # 2. Gold-Inlaid Ox-Horn Ferrule (泥金牛角笔斗)
    ctx.new_path()
    ctx.move_to(-14.5, 0.0)
    ctx.line_to(-18.5, 42.0)
    ctx.line_to(18.5, 42.0)
    ctx.line_to(14.5, 0.0)
    ctx.close_path()
    g_ferr = cairo.LinearGradient(-18.5, 0, 18.5, 0)
    g_ferr.add_color_stop_rgba(0.0, 0.12, 0.11, 0.14, 0.98)
    g_ferr.add_color_stop_rgba(0.5, 0.28, 0.25, 0.30, 0.98)
    g_ferr.add_color_stop_rgba(1.0, 0.08, 0.07, 0.10, 0.98)
    ctx.set_source(g_ferr)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.90, 0.74, 0.26, 0.92)
    ctx.set_line_width(2.4)
    ctx.stroke()

    # 3. Plump Purple Wolf-Hair Tuft (紫毫笔锋, tip at y = 185.0)
    tip_bend_x = -14.0 * math.sin(t * 18.0) if state == "painting" else 0.0
    ctx.new_path()
    ctx.move_to(-17.5, 42.0)
    ctx.curve_to(-25.0, 86.0, -17.0, 140.0, tip_bend_x, 185.0)
    ctx.curve_to(17.0, 140.0, 25.0, 86.0, 17.5, 42.0)
    ctx.close_path()
    g_tuft = cairo.LinearGradient(0, 42.0, 0, 185.0)
    g_tuft.add_color_stop_rgba(0.00, 0.38, 0.26, 0.34, 0.98)
    g_tuft.add_color_stop_rgba(0.45, 0.16, 0.24, 0.38, 0.98)
    g_tuft.add_color_stop_rgba(0.80, 0.06, 0.07, 0.10, 0.99)
    g_tuft.add_color_stop_rgba(1.00, 0.02, 0.02, 0.04, 1.00)
    ctx.set_source(g_tuft)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.05, 0.05, 0.07, 0.95)
    ctx.set_line_width(2.0)
    ctx.stroke()

    ctx.arc(tip_bend_x, 187.0, 4.8, 0, math.tau)
    ctx.set_source_rgba(0.94, 0.78, 0.26, 0.95)
    ctx.fill()
    ctx.arc(tip_bend_x, 187.0, 2.8, 0, math.tau)
    ctx.set_source_rgba(0.04, 0.04, 0.06, 0.98)
    ctx.fill()

    if state in ("hit", "painting"):
        rng_sp = random.Random(int(t * 60))
        for _ in range(12):
            ang_s = rng_sp.uniform(0, math.tau)
            dist_s = rng_sp.uniform(12.0, 62.0)
            sx_s = tip_bend_x + dist_s * math.cos(ang_s)
            sy_s = 182.0 + dist_s * math.sin(ang_s)
            r_s = rng_sp.uniform(2.0, 5.0)
            col_s = rng_sp.choice([
                (0.95, 0.80, 0.28, 0.92),
                (0.16, 0.36, 0.54, 0.88),
                (0.06, 0.06, 0.08, 0.90),
            ])
            ctx.arc(sx_s, sy_s, r_s, 0, math.tau)
            ctx.set_source_rgba(*col_s)
            ctx.fill()

    ctx.restore()


# ==============================================================================
# 5. ZONE 3: MUD-GOLD LOTUS POND, LEAPING CINNABAR KOI & CALLIGRAPHIC WHIRLPOOL
# ==============================================================================
def draw_ballistic_water_splash(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    age: float,
    max_age: float = 0.75,
    scale: float = 1.0,
    seed: int = 0,
):
    """
    Renders dynamic multi-ring concentric water wave ripples, curved calligraphic
    white-and-indigo splash plumes (马远《水图》飞白水花浪爪), and ballistic water/ink droplets
    following true gravity trajectories with strong contrast against Xuan paper!
    """
    if age < 0.0 or age >= max_age:
        return
    u_lin = clamp(age / max_age, 0.0, 1.0)
    # Fast explosive onset so the very first frames of impact burst dramatically
    u = u_lin ** 0.48
    fade = (1.0 - u_lin) ** 1.15

    ctx.save()

    # 1. Expanding multi-ring high-contrast water waves on the river plane (双色水墨花青套环水波纹)
    for ring_i in range(5):
        r_rx = (38.0 + ring_i * 34.0 + u * 195.0) * scale
        r_ry = r_rx * 0.30
        r_alpha = fade * (0.92 - ring_i * 0.16)
        if r_alpha <= 0.02:
            continue
        ctx.save()
        ctx.translate(cx, cy + 6.0)
        ctx.scale(1.0, r_ry / max(1.0, r_rx))
        ctx.new_path()
        ctx.arc(0, 0, r_rx, 0, math.tau)
        # Outer dark mineral-indigo & sumi-ink wave shadow for crisp visibility on Xuan paper
        ctx.set_source_rgba(0.08, 0.22, 0.36, r_alpha * 0.88)
        ctx.set_line_width((7.5 - ring_i * 1.1) * scale)
        ctx.stroke_preserve()
        # Inner bright white-foam wave crest
        if ring_i <= 2:
            ctx.set_source_rgba(0.99, 0.98, 0.94, r_alpha * 0.96)
            ctx.set_line_width((3.6 - ring_i * 0.6) * scale)
            ctx.stroke()
        else:
            ctx.new_path()
        ctx.restore()

    # 2. Curved Calligraphic Water Splash Plumes (冲天飞白浪花爪 + 焦墨花青勾勒)
    plume_lift = math.sin(min(1.0, (u_lin ** 0.36) * 1.22) * math.pi)
    if plume_lift > 0.04:
        for side in (-1, 1):
            for p_idx in range(4):
                spread_x = side * (32.0 + p_idx * 30.0 + u * 92.0) * scale
                peak_h = (76.0 + (3 - p_idx) * 34.0) * plume_lift * scale
                ctx.new_path()
                ctx.move_to(cx + side * 14.0 * scale, cy)
                ctx.curve_to(
                    cx + spread_x * 0.42,
                    cy - peak_h * 1.02,
                    cx + spread_x * 0.78,
                    cy - peak_h * 1.12,
                    cx + spread_x,
                    cy - peak_h * 0.30,
                )
                # Bold dark sumi-indigo outer calligraphic stroke
                ctx.set_source_rgba(0.07, 0.18, 0.30, 0.88 * fade)
                ctx.set_line_width((10.2 - p_idx * 1.6) * scale)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke_preserve()
                # Middle mineral-cyan water body
                ctx.set_source_rgba(0.18, 0.45, 0.66, 0.90 * fade)
                ctx.set_line_width((6.8 - p_idx * 1.1) * scale)
                ctx.stroke_preserve()
                # Inner luminous white foam crest
                ctx.set_source_rgba(1.00, 0.99, 0.95, 0.96 * fade)
                ctx.set_line_width((3.4 - p_idx * 0.5) * scale)
                ctx.stroke()

    # 3. Ballistic Water & Ink Droplets under Gravity (抛物线飞溅水珠与墨点)
    rng = random.Random(seed + 77)
    n_drops = int(26 * scale)
    eff_age = max(0.08, age)
    for _ in range(n_drops):
        vx_d = rng.uniform(-240.0, 240.0) * scale
        vy_d = rng.uniform(180.0, 420.0) * scale
        grav = 620.0 * scale
        dx = cx + vx_d * eff_age
        dy = cy - vy_d * eff_age + 0.5 * grav * (eff_age * eff_age)
        if dy > cy + 20.0:
            continue
        dr = rng.uniform(3.4, 7.6) * scale * (1.0 - 0.30 * u_lin)
        col_d = rng.choice([
            (0.99, 0.98, 0.94, 0.96 * fade),  # 亮白水珠
            (0.14, 0.38, 0.58, 0.92 * fade),  # 花青水珠
            (0.06, 0.07, 0.10, 0.90 * fade),  # 焦墨水点
            (0.86, 0.24, 0.16, 0.90 * fade),  # 朱砂灵点
        ])
        ctx.arc(dx, dy, dr, 0, math.tau)
        ctx.set_source_rgba(*col_d)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.07, 0.16, 0.26, 0.82 * fade)
        ctx.set_line_width(1.5 * scale)
        ctx.stroke()

    ctx.restore()



def draw_taiji_yinyang_array(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    radius: float,
    rot: float,
    alpha: float,
    scale_y: float = 1.0,
):
    """
    Renders a classic Chinese Calligraphic Black-and-White Yin-Yang Taiji Diagram
    (水墨黑白两仪太极双鱼阵 + 八卦水墨爻画):
      - Crisp Sumi-Black Yin Fish (浓墨阴鱼) with Pure White Eye (留白阳眼)
      - Crisp Xuan-Paper White Yang Fish (宣纸留白阳鱼) with Sumi-Black Eye (浓墨阴眼)
      - 8 Rotating Calligraphic Bagua Trigrams (乾兑离震巽坎艮坤) & Swirling Yin-Yang Qi Ribbons!
    """
    if alpha <= 0.01 or radius <= 2.0:
        return

    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(1.0, scale_y)
    ctx.rotate(rot)

    # 1. Outer Luminous Yin-Yang Qi Halo
    halo_g = cairo.RadialGradient(0, 0, radius * 0.2, 0, 0, radius * 1.45)
    halo_g.add_color_stop_rgba(0.0, 0.98, 0.96, 0.90, 0.48 * alpha)
    halo_g.add_color_stop_rgba(0.65, 0.88, 0.72, 0.28, 0.26 * alpha)
    halo_g.add_color_stop_rgba(1.0, 0.14, 0.28, 0.42, 0.0)
    ctx.set_source(halo_g)
    ctx.arc(0, 0, radius * 1.45, 0, math.tau)
    ctx.fill()

    # 2. Classic Black-and-White Yin-Yang Twin Fish Core (黑白两仪双鱼)
    r_core = radius * 0.76
    # White Yang Circle Base (留白阳仪)
    ctx.new_path()
    ctx.arc(0, 0, r_core, 0, math.tau)
    ctx.set_source_rgba(0.99, 0.97, 0.92, 0.92 * alpha)
    ctx.fill()

    # Black Yin Fish S-Curve Half (浓墨阴仪)
    ctx.new_path()
    ctx.arc(0, 0, r_core, -math.pi * 0.5, math.pi * 0.5)
    ctx.arc(0, r_core * 0.5, r_core * 0.5, math.pi * 0.5, -math.pi * 0.5)
    ctx.arc_negative(0, -r_core * 0.5, r_core * 0.5, math.pi * 0.5, -math.pi * 0.5)
    ctx.close_path()
    ctx.set_source_rgba(0.06, 0.07, 0.10, 0.92 * alpha)
    ctx.fill()

    # Yin-Yang Eyes (鱼眼: 阴中有阳，阳中有阴)
    ctx.new_path()
    ctx.arc(0, -r_core * 0.5, r_core * 0.16, 0, math.tau)
    ctx.set_source_rgba(0.06, 0.07, 0.10, 0.95 * alpha)
    ctx.fill()

    ctx.new_path()
    ctx.arc(0, r_core * 0.5, r_core * 0.16, 0, math.tau)
    ctx.set_source_rgba(0.99, 0.97, 0.92, 0.96 * alpha)
    ctx.fill()

    # Calligraphic Dry-Brush & Mud-Gold Ring around Yin-Yang Core
    ctx.new_path()
    ctx.arc(0, 0, r_core, 0, math.tau)
    ctx.set_source_rgba(0.08, 0.09, 0.12, 0.90 * alpha)
    ctx.set_line_width(4.2)
    ctx.stroke()

    ctx.new_path()
    ctx.arc(0, 0, r_core + 6.0, 0, math.tau)
    ctx.set_source_rgba(0.90, 0.74, 0.24, 0.78 * alpha)
    ctx.set_line_width(2.2)
    ctx.set_dash([28.0, 8.0], rot * 12.0)
    ctx.stroke()
    ctx.set_dash([], 0.0)

    # 3. 8 Rotating Calligraphic Bagua Trigrams (八卦水墨爻画)
    bagua_bits = [
        (1, 1, 1), (0, 1, 1), (1, 0, 1), (0, 0, 1),
        (1, 1, 0), (0, 1, 0), (1, 0, 0), (0, 0, 0),
    ]
    for g_idx, bits in enumerate(bagua_bits):
        g_ang = g_idx * (math.tau / 8.0)
        ctx.save()
        ctx.rotate(g_ang)
        ctx.translate(0, -radius * 0.98)
        for line_i, bit in enumerate(bits):
            ly = (line_i - 1) * 6.5
            ctx.set_source_rgba(0.08, 0.09, 0.12, 0.85 * alpha)
            ctx.set_line_width(3.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            if bit == 1:
                ctx.new_path()
                ctx.move_to(-14.0, ly)
                ctx.line_to(14.0, ly)
                ctx.stroke()
            else:
                ctx.new_path()
                ctx.move_to(-14.0, ly)
                ctx.line_to(-3.0, ly)
                ctx.move_to(3.0, ly)
                ctx.line_to(14.0, ly)
                ctx.stroke()
        ctx.restore()

    # 4. Twin Swirling Black & White Yin-Yang Qi Ribbons (外圈黑白两仪气旋带)
    for arm_i, arm_col in enumerate([
        (0.05, 0.06, 0.09, 0.86 * alpha),  # 浓墨阴气带
        (0.99, 0.98, 0.93, 0.92 * alpha),  # 宣白阳气带
    ]):
        base_a = arm_i * math.pi
        ctx.new_path()
        for k_i in range(20):
            u_k = k_i / 19.0
            a_k = base_a + u_k * math.pi * 1.35
            r_k = radius * (1.06 + 0.22 * math.sin(u_k * math.pi))
            px_k = r_k * math.cos(a_k)
            py_k = r_k * math.sin(a_k)
            if k_i == 0:
                ctx.move_to(px_k, py_k)
            else:
                ctx.line_to(px_k, py_k)
        ctx.set_source_rgba(*arm_col)
        ctx.set_line_width(8.5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

    ctx.restore()


def draw_lotus_pond_and_koi(ctx: cairo.Context, state: dict, t: float):
    """
    Renders the Zone 3 Splashed-Ink Lotus Pond (x = 2500..4350) directly on the
    pure Xuan-paper negative space (ZERO dirty grey rectangle at the bottom!),
    with multi-ring water ripples & ballistic water splashes on every lotus pad landing!
    """
    ctx.save()

    # 1. Background decorative lotus pads, blooming ink lotus & buds (positioned cleanly without koi overlap!)
    st04.draw_splashed_lotus_pad(
        ctx, 2505.0, 815.0, scale_x=1.06, scale_y=0.45, base_rad=92.0, seed=9, alpha_gain=0.72, gold_veins=True
    )
    st04.draw_splashed_lotus_pad(
        ctx, 3590.0, 825.0, scale_x=1.18, scale_y=0.48, base_rad=108.0, seed=12, alpha_gain=0.76, gold_veins=True
    )
    st04.draw_blooming_ink_lotus(ctx, 2505.0, 648.0, scale=0.82)
    st04.draw_pink_lotus_bud(ctx, 3190.0, 668.0, stem_bot_y=825.0, scale=0.84, tilt=-0.08)
    st04.draw_blooming_ink_lotus(ctx, 3570.0, 645.0, scale=0.88)
    st04.draw_pink_lotus_bud(ctx, 3940.0, 660.0, stem_bot_y=835.0, scale=0.86, tilt=0.12)

    # 2. 4 Hero Interactive Splashed-Ink Lotus Pads with Mud-Gold Veins, Ripples & Water Splashes!
    for pad in state["lotus_pads"]:
        px = pad["x"]
        py = pad["y"]
        sc = pad["scale"]
        if pad["ripple_r"] > 1.0:
            st04.draw_ink_ripples(ctx, px, py + 10.0, max_r=pad["ripple_r"], alpha_gain=pad["ripple_alpha"])
        else:
            st04.draw_ink_ripples(ctx, px, py + 10.0, max_r=135.0, alpha_gain=0.55)

        st04.draw_splashed_lotus_pad(
            ctx,
            px,
            py,
            scale_x=1.26 * sc,
            scale_y=0.58 * sc,
            base_rad=122.0,
            seed=pad["seed"],
            alpha_gain=1.0,
            gold_veins=True,
        )

        # Ballistic Water Plumes & Ripples whenever the Slime lands on a Lotus Pad!
        if pad.get("splash_age", -1.0) >= 0.0:
            draw_ballistic_water_splash(
                ctx,
                px,
                py + 6.0,
                age=pad["splash_age"],
                max_age=0.75,
                scale=1.05,
                seed=int(px),
            )

    # 3. Expressive Leaping Cinnabar Fish (朱砂写意游鱼跃水) with Breach Water Spray
    for koi in state["koi"]:
        if koi["alpha"] <= 0.02:
            continue
        kx, ky, kang, klen = koi["x"], koi["y"], koi["ang"], koi["length"]

        st04.draw_ink_ripples(ctx, kx - 55.0, 745.0, max_r=160.0, alpha_gain=0.82 * koi["alpha"])
        ctx.save()
        ctx.new_path()
        ctx.move_to(kx - 85.0, 742.0)
        ctx.curve_to(kx - 55.0, ky + 45.0, kx - 28.0, ky + 18.0, kx - 8.0, ky + 6.0)
        ctx.set_source_rgba(0.16, 0.36, 0.50, 0.56 * koi["alpha"])
        ctx.set_line_width(3.8)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

        # Scattered mineral indigo, white foam & cinnabar splash droplets around leaping fish
        rng_k = random.Random(int(kx * 3))
        for _ in range(14):
            dx_k = rng_k.uniform(-85.0, 75.0)
            dy_k = rng_k.uniform(-55.0, 55.0)
            rk = rng_k.uniform(2.4, 6.4)
            col_k = rng_k.choice([
                (0.99, 0.98, 0.94, 0.90 * koi["alpha"]),
                (0.16, 0.38, 0.56, 0.85 * koi["alpha"]),
                (0.82, 0.24, 0.16, 0.88 * koi["alpha"]),
            ])
            if rk > 3.8:
                ctx.arc(kx + dx_k, ky + dy_k, rk * 1.7, 0, math.tau)
                ctx.set_source_rgba(col_k[0], col_k[1], col_k[2], col_k[3] * 0.22)
                ctx.fill()
            ctx.arc(kx + dx_k, ky + dy_k, rk, 0, math.tau)
            ctx.set_source_rgba(*col_k)
            ctx.fill()
        ctx.restore()

        st04.draw_cinnabar_fish(ctx, kx, ky, length=klen, angle=kang)

    ctx.restore()


def draw_ink_dragon_whirlpool_and_giant_lotus(ctx: cairo.Context, state: dict, t: float):
    """
    Renders the complete Act IV Story at (4140.0, 720.0):
      1. Ink Black Hole Whirlpool (焦墨黑洞旋涡) swallowing the Guiding Star ✦ (14.85s ~ 15.85s)
      2. Heavy Taiji Yin-Yang Impact Shockwave + Colossal Water Splash & Ripples (17.95s ~ 19.20s)
      3. Giant Lotus RISING out of the water as a closed bud (莲花升起 18.45s ~ 19.55s)
         and OPENING its 9 petal rings (莲花打开 19.50s ~ 20.65s) to reveal the rescued Star!
      4. Star-Eating Radiant Burst at t = 21.35s (吃掉星星)!
    """
    v_st = state["vortex"]
    if not v_st["active"]:
        return

    vx = v_st["x"]
    vy = v_st["y"]
    rot = v_st["rot"]
    corr = v_st["corruption"]
    eyes = v_st["eyes"]
    suck_prog = v_st.get("suck_prog", 0.0)
    impact_age = v_st.get("taiji_impact_age", -1.0)
    lotus_rise = v_st.get("lotus_rise", 0.0)
    lotus_open = v_st.get("lotus_open", 0.0)

    ctx.save()

    # --- A. Calligraphic Sumi-Ink Black Hole Whirlpool (when corruption > 0.01) ---
    if corr > 0.01:
        ctx.save()
        # 1. Perspective water-plane calligraphic spiral ink black hole
        ctx.save()
        ctx.translate(vx, vy)
        ctx.scale(1.42, 0.46)

        g_abyss = cairo.RadialGradient(0, 0, 12.0, 0, 0, 240.0)
        g_abyss.add_color_stop_rgba(0.00, 0.02, 0.02, 0.04, 0.96 * corr)
        g_abyss.add_color_stop_rgba(0.42, 0.07, 0.10, 0.16, 0.78 * corr)
        g_abyss.add_color_stop_rgba(0.78, 0.14, 0.22, 0.30, 0.34 * corr)
        g_abyss.add_color_stop_rgba(1.00, 0.20, 0.28, 0.36, 0.0)
        ctx.set_source(g_abyss)
        ctx.arc(0, 0, 240.0, 0, math.tau)
        ctx.fill()

        # 4 Tapered Calligraphic Dry-Brush Spiral Arms
        for arm_i in range(4):
            base_a = rot * 1.5 + arm_i * (math.tau / 4.0)
            ctx.new_path()
            for s_i in range(28):
                u_s = s_i / 27.0
                ang_s = base_a + u_s * 3.8
                rad_s = 16.0 + u_s * 200.0
                px_s = rad_s * math.cos(ang_s)
                py_s = rad_s * math.sin(ang_s)
                if s_i == 0:
                    ctx.move_to(px_s, py_s)
                else:
                    ctx.line_to(px_s, py_s)
            col_arm = (0.03, 0.03, 0.05, 0.88 * corr) if arm_i % 2 == 0 else (0.12, 0.22, 0.32, 0.72 * corr)
            ctx.set_source_rgba(*col_arm)
            ctx.set_line_width(9.5 if arm_i % 2 == 0 else 5.8)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_dash([36.0, 8.0, 18.0, 6.0], rot * 15.0)
            ctx.stroke()
        ctx.restore()

        # 2. Dark Suction Vortex Funnel Pulling the Star Down (when 0 < suck_prog < 1.0)
        if 0.01 < suck_prog < 0.99:
            for f_i in range(5):
                f_ang = rot * 2.5 + f_i * (math.tau / 5.0)
                top_x = vx + math.cos(f_ang) * 78.0 * (1.0 - suck_prog)
                top_y = lerp(485.0, vy, suck_prog)
                ctx.new_path()
                ctx.move_to(top_x, top_y)
                ctx.curve_to(
                    vx + math.sin(f_ang) * 55.0,
                    lerp(top_y, vy, 0.5),
                    vx - math.cos(f_ang) * 35.0,
                    vy - 25.0,
                    vx,
                    vy,
                )
                ctx.set_source_rgba(0.04, 0.04, 0.07, 0.72 * corr)
                ctx.set_line_width(3.6)
                ctx.stroke()

        # 3. Rising Calligraphic Ink-Ribbon Tendrils & Splashing Droplets
        for tendril_i in range(3):
            t_phase = t * 5.0 + tendril_i * (math.tau / 3.0)
            tx0 = vx + math.cos(t_phase) * 95.0
            ty0 = vy + math.sin(t_phase) * 28.0
            tx1 = vx + math.cos(t_phase + 1.4) * 55.0
            ty1 = vy - 75.0 * corr
            tx2 = vx + math.cos(t_phase + 2.6) * 25.0
            ty2 = vy - 135.0 * corr
            ctx.new_path()
            ctx.move_to(tx0, ty0)
            ctx.curve_to(tx1, ty1, tx1 - 20.0, ty1 - 30.0, tx2, ty2)
            ctx.set_source_rgba(0.06, 0.07, 0.10, 0.62 * corr)
            ctx.set_line_width(4.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

        # 4. Peering Cinnabar Dragon Eyes in the Whirlpool Core
        if eyes > 0.05:
            eye_y_base = vy - 18.0 * corr
            for side in (-1, 1):
                ex = vx + side * 28.0
                ctx.save()
                ctx.translate(ex, eye_y_base)
                ctx.rotate(side * -0.22)
                ctx.new_path()
                ctx.move_to(-16.0, 0.0)
                ctx.curve_to(-5.0, -8.5, 5.0, -8.5, 16.0, 0.0)
                ctx.curve_to(5.0, 6.5, -5.0, 6.5, -16.0, 0.0)
                ctx.close_path()
                ctx.set_source_rgba(0.92, 0.26, 0.16, 0.95 * eyes * corr)
                ctx.fill_preserve()
                ctx.set_source_rgba(0.96, 0.82, 0.30, 0.90 * eyes * corr)
                ctx.set_line_width(1.6)
                ctx.stroke()

                ctx.rectangle(-2.0, -6.0, 4.0, 12.0)
                ctx.set_source_rgba(0.04, 0.04, 0.06, 0.98 * eyes * corr)
                ctx.fill()
                ctx.restore()
        ctx.restore()

    # --- B. Heavy Taiji Yin-Yang Impact Shockwave & Colossal Water Splash (t >= 17.95s) ---
    if 0.0 <= impact_age < 1.65:
        imp_u = clamp(impact_age / 1.45, 0.0, 1.0)
        imp_fade = (1.0 - imp_u) ** 1.2
        # 1. Expanding Black-and-White Yin-Yang Taiji Array on the Water Plane!
        draw_taiji_yinyang_array(
            ctx,
            vx,
            vy + 4.0,
            radius=85.0 + imp_u * 290.0,
            rot=-t * 5.2,
            alpha=0.92 * imp_fade,
            scale_y=0.38,
        )
        # 2. Colossal Water Wave Ripples & Towering Splash Plumes!
        draw_ballistic_water_splash(
            ctx,
            vx,
            vy + 4.0,
            age=impact_age,
            max_age=1.25,
            scale=1.85,
            seed=4140,
        )

    # --- C. Giant Lotus RISING (莲花升起) & OPENING (莲花打开) + Rescued Star Inside ---
    if lotus_rise > 0.01:
        ctx.save()
        # Constrained water ripples around the rising & blooming Giant Lotus
        st04.draw_ink_ripples(ctx, vx, vy + 14.0, max_r=255.0 * lotus_rise, alpha_gain=0.95 * lotus_rise)

        # Cascading water droplets & splash as the Giant Lotus rises out of the water (18.45s ~ 19.65s)
        if 0.02 < lotus_rise < 0.98:
            draw_ballistic_water_splash(
                ctx,
                vx,
                vy + 10.0,
                age=(1.0 - abs(lotus_rise - 0.5) * 2.0) * 0.45,
                max_age=0.75,
                scale=1.35,
                seed=1888,
            )

        # Broad Mud-Gold-Veined Splashed-Ink Lotus Pad Base
        st04.draw_splashed_lotus_pad(
            ctx,
            vx,
            vy + 15.0,
            scale_x=1.78 * lotus_rise,
            scale_y=0.60 * lotus_rise,
            base_rad=144.0,
            seed=42,
            alpha_gain=lotus_rise,
            gold_veins=True,
        )

        # Clip vertically above the water line (y <= 738) so the Giant Lotus visibly RISES out of the river!
        ctx.save()
        ctx.rectangle(vx - 320.0, 320.0, 640.0, 418.0)
        ctx.clip()

        # Rising vertical offset: starts 140px below water when lotus_rise=0, reaches 0 at lotus_rise=1!
        rise_dy = (1.0 - lotus_rise) * 140.0
        lotus_cy = 695.0 + rise_dy

        # Golden Seedpod Landing Platform inside the Lotus (revealed as lotus_open increases!)
        if lotus_open > 0.05:
            ctx.save()
            ctx.translate(vx, 688.0 + rise_dy)
            ctx.scale(1.0, 0.38)
            pod_r = 74.0 * lerp(0.35, 1.0, lotus_open)
            pod_g = cairo.RadialGradient(0, 0, 6.0, 0, 0, pod_r)
            pod_g.add_color_stop_rgba(0.00, 0.98, 0.86, 0.32, 0.98 * lotus_rise)
            pod_g.add_color_stop_rgba(0.70, 0.86, 0.66, 0.20, 0.96 * lotus_rise)
            pod_g.add_color_stop_rgba(1.00, 0.58, 0.42, 0.14, 0.94 * lotus_rise)
            ctx.set_source(pod_g)
            ctx.arc(0, 0, pod_r, 0, math.tau)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.14, 0.12, 0.10, 0.90 * lotus_rise)
            ctx.set_line_width(2.8)
            ctx.stroke()
            ctx.restore()

        # Multi-Ring Pink-White & Mud-Gold Lotus Petals:
        # When lotus_open == 0.0, petals are gathered tightly into a pointed Giant Lotus Bud (含苞待放)!
        # As lotus_open -> 1.0, petals unfurl wide into the Grand Lotus Throne (莲花盛开)!
        open_spread = lerp(0.12, 1.00, lotus_open)
        petal_rings = [
            (-1.25, 134.0, 46.0, (0.78, 0.22, 0.22, 0.90)),
            (1.25, 134.0, 46.0, (0.78, 0.22, 0.22, 0.90)),
            (-0.92, 148.0, 50.0, (0.84, 0.25, 0.20, 0.94)),
            (0.92, 148.0, 50.0, (0.84, 0.25, 0.20, 0.94)),
            (-0.58, 156.0, 52.0, (0.88, 0.28, 0.20, 0.96)),
            (0.58, 156.0, 52.0, (0.88, 0.28, 0.20, 0.96)),
            (-0.26, 162.0, 54.0, (0.90, 0.30, 0.22, 0.98)),
            (0.26, 162.0, 54.0, (0.90, 0.30, 0.22, 0.98)),
            (0.00, 168.0, 56.0, (0.92, 0.32, 0.22, 0.98)),
        ]
        for p_ang_full, p_len_base, p_w_base, c_tip in petal_rings:
            p_ang = p_ang_full * open_spread
            p_len = p_len_base * lerp(0.88, 1.0, lotus_open)
            p_w = p_w_base * lerp(0.76, 1.0, lotus_open)
            ctx.save()
            ctx.translate(vx, lotus_cy + 12.0)
            ctx.rotate(p_ang)

            ctx.new_path()
            ctx.move_to(0, 16.0)
            ctx.curve_to(-p_w * 0.90, -p_len * 0.32, -p_w * 0.70, -p_len * 0.78, 0, -p_len)
            ctx.curve_to(p_w * 0.70, -p_len * 0.78, p_w * 0.90, -p_len * 0.32, 0, 16.0)
            ctx.close_path()

            pg = cairo.LinearGradient(0, 16.0, 0, -p_len)
            pg.add_color_stop_rgba(0.00, 0.99, 0.97, 0.93, 0.98 * lotus_rise)
            pg.add_color_stop_rgba(0.52, 0.97, 0.85, 0.84, 0.96 * lotus_rise)
            pg.add_color_stop_rgba(1.00, c_tip[0], c_tip[1], c_tip[2], c_tip[3] * lotus_rise)
            ctx.set_source(pg)
            ctx.fill_preserve()

            ctx.set_source_rgba(0.12, 0.10, 0.12, 0.88 * lotus_rise)
            ctx.set_line_width(2.2)
            ctx.stroke()

            ctx.new_path()
            ctx.move_to(0, 8.0)
            ctx.line_to(0, -p_len * 0.84)
            ctx.set_source_rgba(0.92, 0.74, 0.24, 0.65 * lotus_rise)
            ctx.set_line_width(1.4)
            ctx.stroke()
            ctx.restore()

        ctx.restore()  # End vertical water-line clip

        # Rescued Shining Star & Cinnabar Ink-Star Token revealed inside the Open Lotus Heart!
        tok = state["token"]
        if tok["active"] and tok["alpha"] > 0.01:
            ctx.save()
            tg = cairo.RadialGradient(tok["x"], tok["y"], 6.0, tok["x"], tok["y"], tok["radius"] * 2.1)
            tg.add_color_stop_rgba(0.0, 0.99, 0.92, 0.45, 0.78 * tok["alpha"])
            tg.add_color_stop_rgba(0.55, 0.88, 0.28, 0.18, 0.32 * tok["alpha"])
            tg.add_color_stop_rgba(1.0, 0.88, 0.28, 0.18, 0.0)
            ctx.set_source(tg)
            ctx.arc(tok["x"], tok["y"], tok["radius"] * 2.1, 0, math.tau)
            ctx.fill()
            ctx.restore()
            # Draw both the radiant Star ✦ and the Cinnabar Seal Token inside the Lotus heart so the
            # audience unmistakably sees the Lotus open and release the swallowed Star for the Slime to eat!
            draw_world_token(ctx, 4, tok["x"], tok["y"], tok["radius"] * 0.88, rot=tok["rot"], t=t, alpha=tok["alpha"])
            st04.draw_star(ctx, tok["x"], tok["y"], tok["radius"] * 0.78, rot=t * 2.6, t=t)

        # Star-Eating Radiant Celebration Burst when Slime eats the Star on the Lotus (t = 21.35s)!
        eat_age = tok.get("eat_burst_age", -1.0)
        if 0.0 <= eat_age < 1.0:
            eu = clamp(eat_age / 1.0, 0.0, 1.0)
            efade = (1.0 - eu) ** 1.3
            ctx.save()
            for r_mult, col_b in [
                (1.0, (0.98, 0.84, 0.28, 0.88 * efade)),
                (0.68, (0.86, 0.26, 0.18, 0.82 * efade)),
            ]:
                ctx.new_path()
                ctx.arc(vx, 615.0, (35.0 + eu * 210.0) * r_mult, 0, math.tau)
                ctx.set_source_rgba(*col_b)
                ctx.set_line_width(4.5 * (1.0 - 0.5 * eu))
                ctx.stroke()
            ctx.restore()

        ctx.restore()

    ctx.restore()


# ==============================================================================
# 6. ZONE 4: SONG-DYNASTY CLOUD-MOUNTAIN PEAKS, CANTILEVERED CLIFF LEDGES & SEAL
# ==============================================================================
def draw_cloud_crag_terraces_and_seal(ctx: cairo.Context, state: dict, t: float):
    """
    Renders the Zone 4 Song-Dynasty Cloud-Mountain & Overhanging Cliff Sanctuary (米家云山 · 奇峰古松悬崖石台):
      - Layer A: 3 soaring, asymmetric background ink-wash mountain peaks (崇山峻岭)
        with cascading white Xuan-paper waterfalls (留白飞瀑) and drifting cloud bands (留白云带).
      - Layer B: 3 sculptural, cantilevered scholar's-rock & cliff ledges at
        (4450, 590), (4730, 495), and (5010, 410) with rugged crag shoulders,
        axe-cut brush strokes (斧劈皴), moss dots, and gnarled cliffside pines (迎客奇松)!
      - Layer C: Suspended Seal Arch 「双子奇观」!
    """
    ctx.save()

    # --- Layer A: Soaring Background Song-Dynasty Ink-Wash Peaks (奇峰耸翠与留白飞瀑) ---
    bg_peaks = [
        (4560.0, 225.0, 4240.0, 4860.0, 745.0, 0.36, None),
        (4920.0, 145.0, 4560.0, 5320.0, 735.0, 0.46, 4885.0),
        (5260.0, 185.0, 4940.0, 5580.0, 725.0, 0.38, None),
    ]
    for pk_x, pk_y, lx0, rx0, by0, a_top, wf_x in bg_peaks:
        ctx.save()
        ctx.new_path()
        ctx.move_to(lx0, by0)
        ctx.curve_to(lx0 + (pk_x - lx0) * 0.35, by0 - (by0 - pk_y) * 0.42,
                     pk_x - 85.0, pk_y + 65.0,
                     pk_x - 32.0, pk_y + 18.0)
        ctx.curve_to(pk_x - 10.0, pk_y - 4.0, pk_x + 12.0, pk_y - 2.0, pk_x + 28.0, pk_y + 22.0)
        ctx.curve_to(pk_x + 80.0, pk_y + 95.0,
                     pk_x + (rx0 - pk_x) * 0.55, by0 - (by0 - pk_y) * 0.38,
                     rx0, by0)
        ctx.close_path()

        g_pk = cairo.LinearGradient(0, pk_y, 0, by0)
        g_pk.add_color_stop_rgba(0.00, 0.14, 0.21, 0.28, a_top)
        g_pk.add_color_stop_rgba(0.48, 0.20, 0.22, 0.27, a_top * 0.62)
        g_pk.add_color_stop_rgba(0.82, 0.25, 0.25, 0.30, a_top * 0.18)
        g_pk.add_color_stop_rgba(1.00, 0.28, 0.27, 0.32, 0.00)
        ctx.set_source(g_pk)
        ctx.fill()

        ctx.new_path()
        ctx.move_to(pk_x - 135.0, pk_y + 145.0)
        ctx.curve_to(pk_x - 65.0, pk_y + 42.0, pk_x - 18.0, pk_y + 2.0, pk_x + 16.0, pk_y + 8.0)
        ctx.curve_to(pk_x + 52.0, pk_y + 46.0, pk_x + 95.0, pk_y + 105.0, pk_x + 145.0, pk_y + 175.0)
        ctx.set_source_rgba(0.12, 0.14, 0.18, a_top * 1.15)
        ctx.set_line_width(3.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

        if wf_x is not None:
            for wf_off, wf_w in [(-6.0, 5.5), (5.0, 3.2)]:
                ctx.new_path()
                ctx.move_to(wf_x + wf_off, pk_y + 78.0)
                ctx.curve_to(wf_x + wf_off - 8.0, pk_y + 185.0,
                             wf_x + wf_off + 6.0, pk_y + 295.0,
                             wf_x + wf_off - 4.0, pk_y + 415.0)
                ctx.set_source_rgba(0.97, 0.95, 0.90, 0.78)
                ctx.set_line_width(wf_w)
                ctx.stroke()
        ctx.restore()

    # --- Layer B: 3 Asymmetric Cantilevered Scholar's-Rock Cliff Terraces (奇石悬崖石台) ---
    terrace_specs = [
        {
            "cx": 4450.0, "top_y": 590.0, "lw": 210.0, "crag_h": 220.0, "seed": 11,
            "left_shoulder": (-145.0, 26.0), "right_prow": (128.0, 14.0), "has_left_pine": True,
        },
        {
            "cx": 4730.0, "top_y": 495.0, "lw": 225.0, "crag_h": 275.0, "seed": 22,
            "left_shoulder": (-138.0, 32.0), "right_prow": (142.0, 18.0), "has_left_pine": False,
        },
        {
            "cx": 5010.0, "top_y": 410.0, "lw": 255.0, "crag_h": 335.0, "seed": 33,
            "left_shoulder": (-155.0, 28.0), "right_prow": (158.0, 12.0), "has_left_pine": False,
        },
    ]

    for spec in terrace_specs:
        cx = spec["cx"]
        top_y = spec["top_y"]
        lw = spec["lw"]
        crag_h = spec["crag_h"]
        seed = spec["seed"]
        ls_dx, ls_dy = spec["left_shoulder"]
        rp_dx, rp_dy = spec["right_prow"]
        hw = lw * 0.5

        ctx.save()

        ctx.new_path()
        ctx.move_to(cx - hw - 85.0, top_y + crag_h)
        ctx.curve_to(cx - hw - 68.0, top_y + crag_h * 0.58,
                     cx + ls_dx - 18.0, top_y + ls_dy + 42.0,
                     cx + ls_dx, top_y + ls_dy)
        ctx.curve_to(cx - hw - 12.0, top_y + 6.0, cx - hw * 0.85, top_y, cx - hw * 0.72, top_y)
        ctx.line_to(cx + hw * 0.78, top_y)
        ctx.curve_to(cx + hw, top_y, cx + rp_dx, top_y + rp_dy - 4.0, cx + rp_dx, top_y + rp_dy)
        ctx.curve_to(cx + rp_dx - 14.0, top_y + rp_dy + 26.0,
                     cx + hw + 12.0, top_y + 48.0,
                     cx + hw + 28.0, top_y + 88.0)
        ctx.curve_to(cx + hw + 45.0, top_y + crag_h * 0.55,
                     cx + hw + 62.0, top_y + crag_h * 0.82,
                     cx + hw + 78.0, top_y + crag_h)
        ctx.close_path()

        g_crag = cairo.LinearGradient(0, top_y, 0, top_y + crag_h)
        g_crag.add_color_stop_rgba(0.00, 0.14, 0.21, 0.28, 0.76)
        g_crag.add_color_stop_rgba(0.38, 0.19, 0.21, 0.26, 0.52)
        g_crag.add_color_stop_rgba(0.75, 0.25, 0.25, 0.30, 0.16)
        g_crag.add_color_stop_rgba(1.00, 0.28, 0.27, 0.32, 0.00)
        ctx.set_source(g_crag)
        ctx.fill()

        sub_cx = cx - hw * 0.35 if seed != 22 else cx + hw * 0.32
        sub_y = top_y + 34.0
        ctx.new_path()
        ctx.move_to(sub_cx - 75.0, top_y + crag_h * 0.85)
        ctx.curve_to(sub_cx - 58.0, sub_y + 35.0, sub_cx - 32.0, sub_y, sub_cx, sub_y - 4.0)
        ctx.curve_to(sub_cx + 38.0, sub_y + 2.0, sub_cx + 62.0, sub_y + 42.0, sub_cx + 78.0, top_y + crag_h * 0.85)
        ctx.close_path()
        g_sub = cairo.LinearGradient(0, sub_y, 0, top_y + crag_h * 0.85)
        g_sub.add_color_stop_rgba(0.0, 0.12, 0.16, 0.22, 0.45)
        g_sub.add_color_stop_rgba(0.7, 0.20, 0.20, 0.25, 0.15)
        g_sub.add_color_stop_rgba(1.0, 0.24, 0.24, 0.28, 0.0)
        ctx.set_source(g_sub)
        ctx.fill()

        ctx.new_path()
        ctx.move_to(cx + ls_dx - 16.0, top_y + ls_dy + 38.0)
        ctx.curve_to(cx + ls_dx - 6.0, top_y + ls_dy + 8.0, cx + ls_dx, top_y + ls_dy, cx - hw * 0.72, top_y)
        ctx.line_to(cx + hw * 0.78, top_y)
        ctx.curve_to(cx + hw, top_y, cx + rp_dx, top_y + rp_dy - 4.0, cx + rp_dx, top_y + rp_dy)
        ctx.curve_to(cx + rp_dx - 14.0, top_y + rp_dy + 22.0, cx + hw + 10.0, top_y + 42.0, cx + hw + 22.0, top_y + 76.0)
        ctx.set_source_rgba(0.08, 0.09, 0.12, 0.90)
        ctx.set_line_width(4.4)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

        ctx.new_path()
        ctx.move_to(cx - hw * 0.70, top_y + 4.5)
        ctx.line_to(cx + hw * 0.82, top_y + 4.5)
        ctx.set_source_rgba(0.88, 0.70, 0.24, 0.62)
        ctx.set_line_width(2.2)
        ctx.stroke()

        rng_c = random.Random(seed + 100)
        for s_i in range(7):
            sx0 = cx - hw * 0.78 + s_i * (lw * 0.25)
            sy0 = top_y + 8.0 + (s_i % 3) * 10.0
            s_len = rng_c.uniform(48.0, 105.0)
            s_dx = rng_c.uniform(-28.0, 22.0)
            ctx.new_path()
            ctx.move_to(sx0, sy0)
            ctx.curve_to(sx0 + s_dx * 0.4, sy0 + s_len * 0.45,
                         sx0 - s_dx * 0.3, sy0 + s_len * 0.75,
                         sx0 + s_dx, sy0 + s_len)
            ctx.set_source_rgba(0.10, 0.12, 0.16, 0.42)
            ctx.set_line_width(rng_c.uniform(1.8, 3.2))
            ctx.stroke()

        for m_i in range(12):
            mx = cx + rng_c.uniform(-hw * 0.95, hw * 0.95)
            my = top_y + rng_c.uniform(-2.0, 24.0)
            ctx.arc(mx, my, rng_c.uniform(2.0, 4.2), 0, math.tau)
            if m_i % 3 == 0:
                ctx.set_source_rgba(0.14, 0.32, 0.28, 0.72)
            else:
                ctx.set_source_rgba(0.07, 0.08, 0.11, rng_c.uniform(0.60, 0.88))
            ctx.fill()

        if spec["has_left_pine"]:
            px0, py0 = cx + ls_dx + 6.0, top_y + ls_dy
            ctx.new_path()
            ctx.move_to(px0, py0)
            ctx.curve_to(px0 - 22.0, py0 - 24.0, px0 - 42.0, py0 - 32.0, px0 - 64.0, py0 - 26.0)
            ctx.set_source_rgba(0.10, 0.10, 0.12, 0.88)
            ctx.set_line_width(4.5)
            ctx.stroke()
            for p_cx, p_cy, p_r in [(px0 - 36.0, py0 - 30.0, 18.0), (px0 - 62.0, py0 - 28.0, 22.0)]:
                for n_i in range(7):
                    n_ang = math.pi + (n_i / 6.0) * math.pi
                    ctx.new_path()
                    ctx.move_to(p_cx, p_cy)
                    ctx.line_to(p_cx + p_r * math.cos(n_ang), p_cy + p_r * math.sin(n_ang))
                    ctx.set_source_rgba(0.12, 0.22, 0.19, 0.80)
                    ctx.set_line_width(1.5)
                    ctx.stroke()

        ctx.restore()

    # Drifting Xuan-Paper Cloud Ribbons weaving around the Cliff Waists (山腰留白云带)
    for cl_x, cl_y, cl_rx, cl_ry in [
        (4580.0, 655.0, 260.0, 38.0),
        (4880.0, 585.0, 290.0, 42.0),
        (5180.0, 520.0, 270.0, 38.0),
    ]:
        ctx.save()
        ctx.translate(cl_x + math.sin(t * 0.8) * 18.0, cl_y)
        ctx.scale(1.0, cl_ry / cl_rx)
        cg = cairo.RadialGradient(0, 0, 10.0, 0, 0, cl_rx)
        cg.add_color_stop_rgba(0.0, 0.96, 0.94, 0.88, 0.72)
        cg.add_color_stop_rgba(0.6, 0.96, 0.94, 0.88, 0.35)
        cg.add_color_stop_rgba(1.0, 0.96, 0.94, 0.88, 0.0)
        ctx.set_source(cg)
        ctx.arc(0, 0, cl_rx, 0, math.tau)
        ctx.fill()
        ctx.restore()

    # 3. Gnarled Cliffside Ink Pine Tree jutting from Summit Altar (迎客古松 at x = 5140, y = 412)
    ctx.save()
    ctx.new_path()
    ctx.move_to(5135.0, 414.0)
    ctx.curve_to(5175.0, 378.0, 5205.0, 362.0, 5258.0, 368.0)
    ctx.set_source_rgba(0.10, 0.10, 0.12, 0.90)
    ctx.set_line_width(6.5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()

    for p_cx, p_cy, p_r in [(5185.0, 365.0, 26.0), (5225.0, 355.0, 30.0), (5262.0, 366.0, 24.0)]:
        for n_i in range(9):
            n_ang = math.pi + (n_i / 8.0) * math.pi
            ctx.new_path()
            ctx.move_to(p_cx, p_cy)
            ctx.line_to(p_cx + p_r * math.cos(n_ang), p_cy + p_r * math.sin(n_ang))
            ctx.set_source_rgba(0.12, 0.20, 0.18, 0.82)
            ctx.set_line_width(1.6)
            ctx.stroke()
    ctx.restore()

    # 4. Suspended Song-Dynasty Cinnabar & Mud-Gold Octagonal Star Mandala (朱砂泥金八角星芒乾坤卷轴阵)
    s_st = state["seal"]
    if s_st["flip_rx"] < 0.02:
        draw_cinnabar_gold_star_mandala(ctx, cx=s_st["x"], cy=s_st["y"], size=s_st["size"], t=t)
    else:
        ctx.save()
        ctx.translate(s_st["x"], s_st["y"])
        ctx.scale(1.0, max(0.22, math.cos(s_st["flip_rx"])))
        draw_cinnabar_gold_star_mandala(ctx, cx=0.0, cy=0.0, size=s_st["size"], t=t)
        ctx.restore()

    ctx.restore()


# ==============================================================================
# 7. CALLIGRAPHIC SPEECH BUBBLE & TAIJI RING HELPERS
# ==============================================================================
def draw_calligraphy_bubble(ctx: cairo.Context, cx: float, cy: float, kind: str, alpha: float = 1.0, t: float = 0.0):
    """Draws a calligraphic brush-drawn speech bubble (?, !, or spinning Black-and-White Taiji Yin-Yang symbol)."""
    if alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(cx, cy)

    ctx.arc(0, 0, 32.0, 0, math.tau)
    ctx.set_source_rgba(0.98, 0.96, 0.92, 0.94 * alpha)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.08, 0.10, 0.90 * alpha)
    ctx.set_line_width(3.2)
    ctx.stroke()

    if kind == "?":
        ctx.new_path()
        ctx.arc(0, -8.0, 9.5, math.pi * 0.85, math.tau * 0.38)
        ctx.curve_to(2.0, 2.0, -1.5, 6.0, 0.0, 10.0)
        ctx.set_source_rgba(0.08, 0.08, 0.10, 0.95 * alpha)
        ctx.set_line_width(4.2)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
        ctx.arc(0, 17.0, 2.8, 0, math.tau)
        ctx.set_source_rgba(0.82, 0.22, 0.16, 0.95 * alpha)
        ctx.fill()
    elif kind == "!":
        ctx.new_path()
        ctx.move_to(0, -15.0)
        ctx.line_to(0, 7.0)
        ctx.set_source_rgba(0.82, 0.22, 0.16, 0.96 * alpha)
        ctx.set_line_width(4.8)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
        ctx.arc(0, 16.5, 3.0, 0, math.tau)
        ctx.fill()
    elif kind == "taiji":
        ctx.rotate(t * 4.5)
        ctx.arc(0, 0, 20.0, 0, math.tau)
        ctx.set_source_rgba(0.99, 0.98, 0.94, 0.96 * alpha)
        ctx.fill()
        ctx.new_path()
        ctx.arc(0, 0, 20.0, -math.pi * 0.5, math.pi * 0.5)
        ctx.arc(0, 10.0, 10.0, math.pi * 0.5, -math.pi * 0.5)
        ctx.arc_negative(0, -10.0, 10.0, math.pi * 0.5, -math.pi * 0.5)
        ctx.close_path()
        ctx.set_source_rgba(0.06, 0.07, 0.10, 0.96 * alpha)
        ctx.fill()
        ctx.arc(0, -10.0, 3.6, 0, math.tau)
        ctx.set_source_rgba(0.06, 0.07, 0.10, 0.98 * alpha)
        ctx.fill()
        ctx.arc(0, 10.0, 3.6, 0, math.tau)
        ctx.set_source_rgba(0.99, 0.98, 0.94, 0.98 * alpha)
        ctx.fill()
        ctx.arc(0, 0, 20.0, 0, math.tau)
        ctx.set_source_rgba(0.06, 0.07, 0.10, 0.92 * alpha)
        ctx.set_line_width(2.0)
        ctx.stroke()

    ctx.restore()


# ==============================================================================
# 8. MAIN FRAME RENDERER: render_frame_from_state
# ==============================================================================
def render_frame_from_state(state: dict) -> np.ndarray:
    """
    Renders a single frame (1920x1080) from snapshot state dict.
    Returns uint8 array of shape (1080, 1920, 4) in BGRA format for FFmpeg.
    """
    t = state["t"]
    cam = state["camera"]
    cam_x = cam["x"]
    cam_y = cam["y"]
    ox = cam_x - W * 0.5
    oy = cam_y - H * 0.5

    # 1. Base Canvas & Raw Xuan Paper Texture via st04
    bg_surf = get_base_paper_surface()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_surface(bg_surf, 0, 0)
    ctx.paint()

    # 2. Continuous 3-Layer Song-Dynasty Distant Misty Mountains (Screen-space parallax, zero cutoffs!)
    draw_continuous_scroll_mountains(ctx, ox=ox, oy=oy)

    # 3. Enter World-Space Camera Transform (ALL world elements drawn at exact world coordinates!)
    ctx.save()
    ctx.translate(-ox, -oy)

    # Zone 1: Calligraphic Bamboo Grove & Rippling Water Touch (visible when ox < 1850)
    if ox < 1850.0:
        draw_zone1_bamboo_grove(ctx, state["bamboo"], t)

    # Zone 2: Poetic Song-Dynasty Broken Stone Arch Bridge & Master Brush
    if ox + W > 1100.0 and ox < 2900.0:
        draw_poetic_stone_arch_bridge(ctx, drawn_progress=state["bridge"]["drawn_progress"], t=t)
        draw_master_calligraphy_brush(ctx, state["brush"], t=t)

    # Zone 3: Mud-Gold Lotus Pond & Leaping Cinnabar Koi
    if ox + W > 2300.0 and ox < 4500.0:
        draw_lotus_pond_and_koi(ctx, state, t=t)

    # Zone 3/4: Calligraphic Sumi-Ink Whirlpool, Taiji Impact & Rising/Opening Giant Lotus
    if ox + W > 3400.0 and ox < 4900.0:
        draw_ink_dragon_whirlpool_and_giant_lotus(ctx, state, t=t)

    # Zone 4: Translucent Cloud-Crag Terraces & Cinnabar Seal Arch
    if ox + W > 3950.0:
        draw_cloud_crag_terraces_and_seal(ctx, state, t=t)

    # Dynamic Calligraphic Qi-Yun Motion Trail behind airborne Slime
    slime_st = state["slime"]
    if slime_st.get("trail_pts"):
        draw_dynamic_slime_ink_trail(ctx, slime_st["trail_pts"], t=t)

    # Guiding Star-Spark ✦ via st04
    star_st = state["star"]
    if star_st["alpha"] > 0.01:
        st04.draw_star(ctx, star_st["x"], star_st["y"], star_st["radius"], rot=star_st["rot"], t=t)

    # Inkwash Slime Hero & Black-and-White Yin-Yang Taiji Diagram (黑白两仪太极阵)
    if slime_st["alpha"] > 0.01:
        sx_w = slime_st["x"]
        sy_w = slime_st["y"]
        taiji_a = slime_st.get("taiji_aura", 0.0)

        # When channeling or striking with Taiji Yin-Yang (15.90s ~ 18.85s), render the
        # rotating Black-and-White Yin-Yang Diagram & Bagua Trigrams around the Slime!
        if taiji_a > 0.01:
            if slime_st["grounded"]:
                # Perspective Yin-Yang Bagua formation on the Lotus Pad / Water beneath Slime's feet!
                draw_taiji_yinyang_array(
                    ctx,
                    sx_w,
                    slime_st["foot_y"] + 6.0,
                    radius=155.0 * taiji_a,
                    rot=t * 3.8,
                    alpha=0.88 * taiji_a,
                    scale_y=0.38,
                )
            # Upright spinning Black-and-White Yin-Yang Taiji Wheel behind/around the Slime's body!
            draw_taiji_yinyang_array(
                ctx,
                sx_w,
                sy_w,
                radius=128.0 * (0.75 + 0.25 * taiji_a),
                rot=-t * 5.6,
                alpha=0.82 * taiji_a,
                scale_y=1.0,
            )

        st04.draw_slime(
            ctx,
            sx_w,
            sy_w,
            radius=slime_st["radius"],
            squash_y=slime_st["squash_y"],
            tilt=slime_st["tilt"],
            look=(slime_st["look_x"], slime_st["look_y"]),
            eye_mode=slime_st["eye_mode"],
            blink=slime_st["blink"],
            t=t,
            grounded=slime_st["grounded"],
            roll_angle=slime_st["roll_angle"],
        )

        # Calligraphic speech bubble (?, !, or Taiji ☯)
        if slime_st["bubble"] and slime_st["bubble_alpha"] > 0.01:
            draw_calligraphy_bubble(
                ctx,
                sx_w + 42.0,
                sy_w - slime_st["radius"] * slime_st["squash_y"] - 42.0,
                slime_st["bubble"],
                alpha=slime_st["bubble_alpha"],
                t=t,
            )

    ctx.restore()  # Exit World-Space Camera Transform

    # 3b. Beat 6 Cinnabar & Gold-Foil Hardcover Pop-Up Book Cover Transition (Handover to World 05)
    if state["seal"]["slam_prog"] > 0.005:
        draw_cinnabar_book_cover_transition(ctx, ox=ox, oy=oy, state=state, t=t)

    # 4. Opening Vertical Plunge Sumi-Ink Speed Lines (Beat 1: 0.0 ~ 0.90s Direct Vertical Drop from World 03)
    if t < 0.90:
        drop_u = clamp(t / 0.90, 0.0, 1.0)
        fade_a = (1.0 - drop_u) ** 1.35
        sx_scr = slime_st["x"] - ox
        sy_scr = slime_st["y"] - oy
        ctx.save()
        # Subtle top-edge sumi-ink & Xuan-paper mist vignette fading out as Slime drops in
        top_g = cairo.LinearGradient(0, 0, 0, 260.0)
        top_g.add_color_stop_rgba(0.0, 0.08, 0.09, 0.12, 0.38 * fade_a)
        top_g.add_color_stop_rgba(1.0, 0.08, 0.09, 0.12, 0.0)
        ctx.set_source(top_g)
        ctx.rectangle(0, 0, W, 260.0)
        ctx.fill()

        # Vertical dry-brush speed lines trailing directly above the falling Slime
        line_offsets = [-68.0, -42.0, -18.0, 0.0, 22.0, 46.0, 72.0]
        for idx_l, dx_l in enumerate(line_offsets):
            lx = sx_scr + dx_l
            ly_bot = max(0.0, sy_scr - 45.0 - (idx_l % 3) * 18.0)
            ly_top = max(-40.0, ly_bot - lerp(280.0, 95.0, drop_u) - (idx_l % 2) * 55.0)
            if ly_bot > ly_top:
                ctx.new_path()
                ctx.move_to(lx, ly_top)
                ctx.line_to(lx, ly_bot)
                col_a = (0.55 if idx_l % 2 == 0 else 0.35) * fade_a
                if idx_l == 3:
                    ctx.set_source_rgba(0.82, 0.24, 0.16, col_a * 0.95)  # Cinnabar core thread
                else:
                    ctx.set_source_rgba(0.10, 0.11, 0.14, col_a)
                ctx.set_line_width(3.4 - abs(idx_l - 3) * 0.45)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke()
        ctx.restore()

    surf.flush()
    buf = surf.get_data()
    arr = np.ndarray(shape=(H, W, 4), dtype=np.uint8, buffer=buf)
    return arr.copy()
