# -*- coding: utf-8 -*-
"""
World 06 · 哥特玫瑰彩窗圣殿 (level_06_stainedglass.py)
High-Fidelity PyCairo Hard-Facet Stained-Glass & Crystal Prism Renderer (26.0s, 4200x2160 4-Zone Stage).

Strictly preserves 100% of styles/style_06_stainedglass.py's signature aesthetic:
  - 28-Pane Hard-Facet Voronoi Stained-Glass Slime with bold dark lead cames, prism slash glints,
    organic bottom-flattened soft-body squash/stretch, and 3D spherical facet rotation.
  - Hard-Facet Crystal Triangular Prism optical dispersion puzzle (white zenith beam -> Ruby, Emerald,
    Sapphire laser beams + rainbow spectral fan).
  - 4 Beveled Gothic Diamond Stained-Glass Steps (st06.draw_gothic_stained_glass_step).
  - Giant Hard-Facet Stained-Glass Cathedral Bell & Twin Chime Bells (st06.draw_stained_glass_bell).
  - 7 Concentric Leaded-Glass Acoustic Shockwaves with 4-point diamond jewel beads & prism shards.
  - Sweeping 7-Color Prismatic Light Ribbon Bridge leading directly into the Grand 3-Ring Gothic
    Rose Window at (3480, 420), which spins and morphs into the 1930s 35mm Film Reel (3-2-1).
"""

import math
import random
import numpy as np
import cairo
from PIL import Image
import os
import sys

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
sys.path.insert(0, ROOT_DIR)

from styles import style_06_stainedglass as st06
from styles import style_07_rubberhose as st07
from slime_engine import draw_world_token, draw_four_point_star
from worlds.world_06_stainedglass.sim_06_stainedglass import (
    GALLERY_FLOOR_Y,
    ROSETTES_X,
    CLIFF_EDGE_X,
    RIBBON_P0,
    RIBBON_C1,
    RIBBON_C2,
    RIBBON_P3,
    ROSE_WINDOW_POS,
)

W, H = 1920, 1080


# ---------------------------------------------------------------------------
# 1. Expansive 4-Zone Gothic Cathedral Background (-10° Dutch Tilt)
# ---------------------------------------------------------------------------
def draw_pointed_lancet_window(ctx: cairo.Context, lcx: float, lcy: float, lw: float, lh: float,
                               c_top: tuple, c_mid: tuple, c_bot: tuple, lit: float = 0.85):
    """
    Renders a Gothic pointed lancet stained-glass window with hard-facet diamond lead tracery
    and an optional 33° volumetric Tyndall God-Ray shaft when lit.
    """
    ctx.save()

    # Backlit window bloom when ignited
    if lit > 0.25:
        bloom = cairo.RadialGradient(lcx, lcy, lw * 0.1, lcx, lcy, lh * 0.65)
        bloom.add_color_stop_rgba(0.0, min(1.0, c_top[0] + 0.35), min(1.0, c_top[1] + 0.35), min(1.0, c_top[2] + 0.35), 0.38 * lit)
        bloom.add_color_stop_rgba(0.5, c_mid[0], c_mid[1], c_mid[2], 0.18 * lit)
        bloom.add_color_stop_rgba(1.0, c_bot[0], c_bot[1], c_bot[2], 0.0)
        ctx.set_source(bloom)
        ctx.arc(lcx, lcy, lh * 0.65, 0, math.tau)
        ctx.fill()

    def _window_arch_path():
        ctx.new_path()
        ctx.move_to(lcx - lw * 0.5, lcy + lh * 0.5)
        ctx.line_to(lcx - lw * 0.5, lcy - lh * 0.12)
        ctx.curve_to(lcx - lw * 0.5, lcy - lh * 0.46, lcx - lw * 0.12, lcy - lh * 0.56, lcx, lcy - lh * 0.56)
        ctx.curve_to(lcx + lw * 0.12, lcy - lh * 0.56, lcx + lw * 0.5, lcy - lh * 0.46, lcx + lw * 0.5, lcy - lh * 0.12)
        ctx.line_to(lcx + lw * 0.5, lcy + lh * 0.5)
        ctx.close_path()

    ctx.save()
    _window_arch_path()
    ctx.clip()

    # Stained-glass color gradient
    bright = 0.22 + 0.78 * lit
    lg = cairo.LinearGradient(lcx, lcy - lh * 0.55, lcx, lcy + lh * 0.5)
    lg.add_color_stop_rgba(0.0, min(1.0, c_top[0] * bright + 0.12 * lit), min(1.0, c_top[1] * bright + 0.12 * lit), min(1.0, c_top[2] * bright + 0.12 * lit), 0.92)
    lg.add_color_stop_rgba(0.5, c_mid[0] * bright, c_mid[1] * bright, c_mid[2] * bright, 0.90)
    lg.add_color_stop_rgba(1.0, c_bot[0] * bright, c_bot[1] * bright, c_bot[2] * bright, 0.92)
    ctx.set_source(lg)
    ctx.paint()

    # Central vertical mullion & rose-medallion tracery at top of lancet
    med_y = lcy - lh * 0.26
    med_r = lw * 0.28
    ctx.arc(lcx, med_y, med_r, 0, math.tau)
    ctx.set_source_rgba(min(1.0, c_top[0] + 0.35) * bright, min(1.0, c_top[1] + 0.35) * bright, min(1.0, c_top[2] + 0.35) * bright, 0.95)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.07, 0.08, 0.11, 0.96)
    ctx.set_line_width(3.2)
    ctx.stroke()

    # Hard-facet leaded diamond quarry grid
    ctx.set_source_rgba(0.07, 0.08, 0.11, 0.90)
    ctx.set_line_width(2.6)
    spacing = 32
    for diag in range(-int(lh * 0.8), int(lh * 0.9), spacing):
        ctx.move_to(lcx - lw, lcy + diag)
        ctx.line_to(lcx + lw, lcy + diag + lw * 1.35)
        ctx.move_to(lcx + lw, lcy + diag)
        ctx.line_to(lcx - lw, lcy + diag + lw * 1.35)
    # Mullion bars
    ctx.move_to(lcx, med_y + med_r)
    ctx.line_to(lcx, lcy + lh * 0.5)
    ctx.stroke()

    # Hard-edge diagonal crystal specular slash across window panes
    if lit > 0.3:
        ctx.new_path()
        ctx.move_to(lcx - lw * 0.5, lcy - lh * 0.05)
        ctx.line_to(lcx + lw * 0.5, lcy - lh * 0.32)
        ctx.line_to(lcx + lw * 0.5, lcy - lh * 0.18)
        ctx.line_to(lcx - lw * 0.5, lcy + lh * 0.09)
        ctx.close_path()
        ctx.set_source_rgba(1.0, 0.98, 0.88, 0.22 * lit)
        ctx.fill()

    ctx.restore()

    # Heavy Gothic stone arch surround
    _window_arch_path()
    ctx.set_source_rgba(0.09, 0.10, 0.15, 0.98)
    ctx.set_line_width(14.0)
    ctx.stroke_preserve()
    ctx.set_source_rgba(0.24, 0.27, 0.36, 0.55)
    ctx.set_line_width(2.0)
    ctx.stroke()

    # Diagonal Volumetric God-Ray streaming from lit window
    if lit > 0.15:
        ray_len = 1350.0
        ray_dx = ray_len * math.cos(33.0 * math.pi / 180.0)
        ray_dy = ray_len * math.sin(33.0 * math.pi / 180.0)
        ctx.new_path()
        ctx.move_to(lcx - lw * 0.42, lcy - lh * 0.2)
        ctx.line_to(lcx + lw * 0.42, lcy - lh * 0.2)
        ctx.line_to(lcx + lw * 0.65 + ray_dx, lcy + lh * 0.3 + ray_dy)
        ctx.line_to(lcx - lw * 0.65 + ray_dx, lcy + lh * 0.3 + ray_dy)
        ctx.close_path()
        rg = cairo.LinearGradient(lcx, lcy, lcx + ray_dx, lcy + ray_dy)
        rg.add_color_stop_rgba(0.0, min(1.0, c_top[0] + 0.25), min(1.0, c_top[1] + 0.25), min(1.0, c_top[2] + 0.25), 0.22 * lit)
        rg.add_color_stop_rgba(0.45, c_mid[0], c_mid[1], c_mid[2], 0.12 * lit)
        rg.add_color_stop_rgba(1.0, c_bot[0], c_bot[1], c_bot[2], 0.0)
        ctx.set_source(rg)
        ctx.fill()

    ctx.restore()


def draw_grand_gothic_rose_window(ctx: cairo.Context, rose_cx: float, rose_cy: float, rose_r: float = 420.0,
                                  rot: float = 0.0, desaturate: float = 0.0, film_reel: float = 0.0):
    """
    Renders the monumental 3-Ring Gothic Rose Window (24 outer lancet petals + 16 middle trefoil
    medallions + 12 inner rosette lobes + solar sunburst core) at (rose_cx, rose_cy).
    When film_reel > 0, smoothly desaturates and morphs into the 1930s 35mm movie film reel!
    """
    ctx.save()
    ctx.translate(rose_cx, rose_cy)

    # 1. Pointed Gothic Stone Arch framing the Rose Window (stationary relative to wall)
    if film_reel < 0.85:
        arch_alpha = 1.0 - film_reel
        arch_top_y = -rose_r * 1.38
        ctx.new_path()
        ctx.move_to(-rose_r * 1.22, rose_r * 0.85)
        ctx.line_to(-rose_r * 1.22, 0)
        ctx.curve_to(-rose_r * 1.22, -rose_r * 0.78, -rose_r * 0.3, arch_top_y, 0, arch_top_y)
        ctx.curve_to(rose_r * 0.3, arch_top_y, rose_r * 1.22, -rose_r * 0.78, rose_r * 1.22, 0)
        ctx.line_to(rose_r * 1.22, rose_r * 0.85)
        ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98 * arch_alpha)
        ctx.set_line_width(26.0)
        ctx.stroke()

    # 2. Backlit stained-glass radiant illumination bloom
    if desaturate < 0.95:
        b_alpha = 1.0 - desaturate
        bloom = cairo.RadialGradient(0, 0, rose_r * 0.08, 0, 0, rose_r * 1.48)
        bloom.add_color_stop_rgba(0.0, 1.00, 0.94, 0.80, 0.92 * b_alpha)
        bloom.add_color_stop_rgba(0.32, 0.35, 0.68, 1.00, 0.68 * b_alpha)
        bloom.add_color_stop_rgba(0.68, 0.65, 0.28, 0.88, 0.40 * b_alpha)
        bloom.add_color_stop_rgba(1.0, 0.10, 0.12, 0.25, 0.0)
        ctx.set_source(bloom)
        ctx.arc(0, 0, rose_r * 1.48, 0, math.tau)
        ctx.fill()

    ctx.rotate(rot)

    base_palette = [
        (0.08, 0.32, 0.78),  # Deep Sapphire (#1452C7)
        (0.85, 0.14, 0.20),  # Grand Cathedral Ruby (#D92433)
        (0.98, 0.68, 0.09),  # Imperial Amber Gold (#FAA817)
        (0.03, 0.56, 0.34),  # Chartres Emerald (#088F57)
        (0.52, 0.20, 0.82),  # Royal Amethyst (#8533D1)
        (0.20, 0.72, 0.92),  # Sky Turquoise (#33B8EB)
        (0.94, 0.36, 0.42),  # Rose Coral (#F05C6B)
    ]
    gem_palette = []
    for (r, g, b) in base_palette:
        gray = 0.299 * r + 0.587 * g + 0.114 * b
        gem_palette.append((
            r * (1.0 - desaturate) + gray * desaturate,
            g * (1.0 - desaturate) + gray * desaturate,
            b * (1.0 - desaturate) + gray * desaturate,
        ))

    # --- Outer Ring (24 Gothic Stained-Glass Lancet Petals) ---
    n_outer = 24
    r_out_1, r_out_2 = rose_r * 0.68, rose_r * 0.96
    for i in range(n_outer):
        a1 = (i / n_outer) * math.tau
        a2 = ((i + 0.93) / n_outer) * math.tau
        amid = (a1 + a2) * 0.5

        p1 = (r_out_1 * math.cos(a1), r_out_1 * math.sin(a1))
        p2 = (r_out_2 * math.cos(a1 + 0.01), r_out_2 * math.sin(a1 + 0.01))
        ptip = ((r_out_2 + 15) * math.cos(amid), (r_out_2 + 15) * math.sin(amid))
        p3 = (r_out_2 * math.cos(a2 - 0.01), r_out_2 * math.sin(a2 - 0.01))
        p4 = (r_out_1 * math.cos(a2), r_out_1 * math.sin(a2))

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
        ctx.arc(0, 0, r_mid_2, a1, a2)
        ctx.arc_negative(0, 0, r_mid_1, a2, a1)
        ctx.close_path()

        col = gem_palette[(i * 3 + 2) % len(gem_palette)]
        petal_g = cairo.RadialGradient(
            r_mid_2 * 0.85 * math.cos(amid),
            r_mid_2 * 0.85 * math.sin(amid), 2,
            0, 0, rose_r * 0.8
        )
        petal_g.add_color_stop_rgba(0.0, min(1.0, col[0] + 0.42), min(1.0, col[1] + 0.42), min(1.0, col[2] + 0.42), 0.96)
        petal_g.add_color_stop_rgba(0.72, col[0], col[1], col[2], 0.92)
        petal_g.add_color_stop_rgba(1.0, col[0] * 0.45, col[1] * 0.45, col[2] * 0.45, 0.98)
        ctx.set_source(petal_g)
        ctx.fill_preserve()

        ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
        ctx.set_line_width(3.2)
        ctx.stroke()

        cusp_r = (r_mid_2 - r_mid_1) * 0.22
        cusp_cx = ((r_mid_1 + r_mid_2) * 0.5) * math.cos(amid)
        cusp_cy = ((r_mid_1 + r_mid_2) * 0.5) * math.sin(amid)
        ctx.arc(cusp_cx, cusp_cy, cusp_r, 0, math.tau)
        c_gold = (1.0 * (1.0 - desaturate) + 0.85 * desaturate, 0.94 * (1.0 - desaturate) + 0.85 * desaturate, 0.70 * (1.0 - desaturate) + 0.85 * desaturate)
        ctx.set_source_rgba(c_gold[0], c_gold[1], c_gold[2], 0.85)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.07, 0.08, 0.11, 0.98)
        ctx.set_line_width(2.2)
        ctx.stroke()

    # --- Inner Ring (12-lobed Rosette) ---
    n_in = 12
    r_in_1, r_in_2 = rose_r * 0.14, rose_r * 0.34
    for i in range(n_in):
        a1 = (i / n_in) * math.tau - 0.04
        a2 = ((i + 0.92) / n_in) * math.tau - 0.04

        ctx.new_path()
        ctx.arc(0, 0, r_in_2, a1, a2)
        ctx.arc_negative(0, 0, r_in_1, a2, a1)
        ctx.close_path()

        col = gem_palette[(i * 2 + 3) % len(gem_palette)]
        ctx.set_source_rgba(col[0], col[1], col[2], 0.95)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.07, 0.08, 0.11, 0.98)
        ctx.set_line_width(2.8)
        ctx.stroke()

    # Central Core Medallion (Golden Starlight Sunburst or Film Reel Spindle)
    ctx.arc(0, 0, r_in_1, 0, math.tau)
    if film_reel > 0.15:
        ctx.set_source_rgba(0.22, 0.22, 0.22, 1.0)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.05, 0.05, 0.05, 1.0)
        ctx.set_line_width(6.0)
        ctx.stroke()
    else:
        core_g = cairo.RadialGradient(0, 0, 2, 0, 0, r_in_1)
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
        ctx.arc(0, 0, tr_r, 0, math.tau)
        ctx.set_source_rgba(0.10, 0.11, 0.15, 0.98)
        ctx.set_line_width(tr_w)
        ctx.stroke()

    # 1930s Vintage Film Reel Morph Overlay (when film_reel > 0.05)
    if film_reel > 0.05:
        n_cutouts = 6
        cutout_r = rose_r * 0.20
        cutout_dist = rose_r * 0.52
        for ci in range(n_cutouts):
            c_ang = (ci / n_cutouts) * math.tau
            cx_h = cutout_dist * math.cos(c_ang)
            cy_h = cutout_dist * math.sin(c_ang)
            ctx.arc(cx_h, cy_h, cutout_r, 0, math.tau)
            ctx.set_source_rgba(0.06, 0.06, 0.06, 0.94 * film_reel)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.32, 0.30, 0.28, 0.98 * film_reel)
            ctx.set_line_width(5.5)
            ctx.stroke()

        ctx.arc(0, 0, rose_r * 0.94, 0, math.tau)
        ctx.set_source_rgba(0.08, 0.08, 0.08, 0.92 * film_reel)
        ctx.set_line_width(28.0)
        ctx.stroke()

        n_sprockets = 48
        for si in range(n_sprockets):
            s_ang = (si / n_sprockets) * math.tau
            sx_p = (rose_r * 0.94) * math.cos(s_ang)
            sy_p = (rose_r * 0.94) * math.sin(s_ang)
            ctx.save()
            ctx.translate(sx_p, sy_p)
            ctx.rotate(s_ang + math.pi * 0.5)
            ctx.rectangle(-4.5, -2.8, 9.0, 5.6)
            ctx.set_source_rgba(0.88, 0.85, 0.78, 0.90 * film_reel)
            ctx.fill()
            ctx.restore()

    ctx.restore()


def draw_expansive_cathedral_background(ctx: cairo.Context, cam_x: float, cam_y: float,
                                        lancet_lit: list, rose_state: dict, t: float):
    """
    Renders the entire 4200x2160 Gothic Stained-Glass Cathedral architecture with -10° Dutch tilt
    on the distant masonry/pillars and full world-space coverage.
    """
    # 1. Deep Obsidian & Midnight Indigo Base Paint across entire canvas
    ctx.save()
    ctx.identity_matrix()
    bg_grad = cairo.LinearGradient(0, 0, W * 0.4, H)
    bg_grad.add_color_stop_rgb(0.0, 0.024, 0.028, 0.048)
    bg_grad.add_color_stop_rgb(0.55, 0.018, 0.022, 0.038)
    bg_grad.add_color_stop_rgb(1.0, 0.010, 0.012, 0.022)
    ctx.set_source(bg_grad)
    ctx.paint()
    ctx.restore()

    # 2. Distant Tilted (-10°) Gothic Stone Columns & Clerestory Lancet Windows
    ctx.save()
    tilt_rad = -10.0 * math.pi / 180.0
    ctx.translate(cam_x, cam_y)
    ctx.rotate(tilt_rad)
    ctx.translate(-cam_x, -cam_y)

    # Background stone masonry grid lines
    ctx.set_source_rgba(0.07, 0.08, 0.13, 0.55)
    ctx.set_line_width(1.8)
    for hy in range(-400, 2400, 120):
        ctx.move_to(-400, hy)
        ctx.line_to(4600, hy)
    ctx.stroke()

    # Background Gothic Clerestory Windows across Zone 2, 3, 4 (behind Prism, Steps, Bell, Bridge)
    bg_windows = [
        (1450.0,  920.0, 165.0, 520.0, (0.12, 0.48, 0.95), (0.35, 0.22, 0.82), (0.18, 0.65, 0.90), 0.72),
        (1820.0,  810.0, 165.0, 520.0, (0.06, 0.72, 0.48), (0.15, 0.48, 0.85), (0.32, 0.88, 0.68), 0.72),
        (2180.0,  700.0, 165.0, 520.0, (0.95, 0.65, 0.12), (0.85, 0.25, 0.38), (0.98, 0.82, 0.28), 0.75),
        (2880.0,  500.0, 170.0, 540.0, (0.62, 0.24, 0.88), (0.92, 0.22, 0.42), (0.35, 0.68, 0.98), 0.78),
    ]
    for wx, wy, ww, wh, ct, cm, cb, wlit in bg_windows:
        draw_pointed_lancet_window(ctx, wx, wy, ww, wh, ct, cm, cb, lit=wlit)

    # Towering Clustered Gothic Stone Pillars spanning the entire 4200px cathedral
    pillar_xs = [120, 390, 640, 880, 1140, 1640, 2000, 2340, 2700, 3120, 3880]
    for px in pillar_xs:
        pw = 88.0
        p_grad = cairo.LinearGradient(px, 0, px + pw, 0)
        p_grad.add_color_stop_rgba(0.0, 0.05, 0.06, 0.10, 0.98)
        p_grad.add_color_stop_rgba(0.30, 0.14, 0.16, 0.23, 0.98)
        p_grad.add_color_stop_rgba(0.72, 0.08, 0.09, 0.13, 0.98)
        p_grad.add_color_stop_rgba(1.0, 0.03, 0.04, 0.06, 0.98)
        ctx.set_source(p_grad)
        ctx.rectangle(px, -600, pw, 3000)
        ctx.fill()

        # Vertical stone shaft moldings
        for mx in [px + pw * 0.20, px + pw * 0.48, px + pw * 0.76]:
            ctx.set_source_rgba(0.22, 0.25, 0.35, 0.42)
            ctx.set_line_width(2.0)
            ctx.move_to(mx, -600)
            ctx.line_to(mx, 2400)
            ctx.stroke()

    ctx.restore()  # End -10° Dutch tilt layer

    # 3. Zone 1: Three Hero Gothic Lancet Windows (ignited by stomping the 3 Floor Rosettes!)
    hero_lancets = [
        (ROSETTES_X[0], 1190.0, 165.0, 510.0, (0.15, 0.55, 1.00), (0.08, 0.32, 0.85), (0.28, 0.78, 1.00), lancet_lit[0]),
        (ROSETTES_X[1], 1170.0, 165.0, 510.0, (0.10, 0.88, 0.58), (0.04, 0.58, 0.38), (0.38, 0.96, 0.72), lancet_lit[1]),
        (ROSETTES_X[2], 1150.0, 165.0, 510.0, (0.98, 0.28, 0.42), (0.78, 0.14, 0.32), (1.00, 0.68, 0.22), lancet_lit[2]),
    ]
    for wx, wy, ww, wh, ct, cm, cb, wlit in hero_lancets:
        draw_pointed_lancet_window(ctx, wx, wy, ww, wh, ct, cm, cb, lit=0.18 + 0.82 * wlit)

    # 4. Zone 1: Obsidian Flagstone Gallery Floor & 3 Inlaid Stained-Glass Floor Rosettes
    ctx.save()
    floor_g = cairo.LinearGradient(0, GALLERY_FLOOR_Y, 0, GALLERY_FLOOR_Y + 450)
    floor_g.add_color_stop_rgba(0.0, 0.055, 0.062, 0.095, 0.98)
    floor_g.add_color_stop_rgba(1.0, 0.015, 0.018, 0.030, 1.00)
    ctx.set_source(floor_g)
    ctx.move_to(-200, GALLERY_FLOOR_Y)
    ctx.line_to(CLIFF_EDGE_X + 55.0, GALLERY_FLOOR_Y)
    ctx.line_to(CLIFF_EDGE_X + 20.0, GALLERY_FLOOR_Y + 480.0)
    ctx.line_to(-200, GALLERY_FLOOR_Y + 480.0)
    ctx.close_path()
    ctx.fill_preserve()
    ctx.set_source_rgba(0.22, 0.26, 0.38, 0.85)
    ctx.set_line_width(3.5)
    ctx.stroke()

    # Perspective flagstone mortar lines on Gallery Floor
    ctx.set_source_rgba(0.12, 0.14, 0.22, 0.75)
    ctx.set_line_width(2.0)
    for fx in range(100, int(CLIFF_EDGE_X), 110):
        ctx.move_to(fx, GALLERY_FLOOR_Y)
        ctx.line_to(fx - 70, GALLERY_FLOOR_Y + 360)
    for fy in range(int(GALLERY_FLOOR_Y) + 45, int(GALLERY_FLOOR_Y) + 320, 55):
        ctx.move_to(-100, fy)
        ctx.line_to(CLIFF_EDGE_X + 35, fy)
    ctx.stroke()

    # 3 Inlaid Hard-Facet Stained-Glass Floor Rosettes at x = 520, 760, 1000
    rosette_colors = [
        ((0.15, 0.55, 1.00), (0.35, 0.85, 1.00)),
        ((0.08, 0.85, 0.55), (0.42, 0.98, 0.75)),
        ((0.96, 0.26, 0.40), (1.00, 0.75, 0.24)),
    ]
    for idx, rx in enumerate(ROSETTES_X):
        rlit = lancet_lit[idx]
        c_main, c_acc = rosette_colors[idx]
        st06.draw_gothic_stained_glass_step(
            ctx,
            rx,
            GALLERY_FLOOR_Y + 4.0,
            136.0,
            32.0,
            color_rgb=c_main,
            accent_rgb=c_acc,
            lit=0.15 + 0.85 * rlit,
        )
    ctx.restore()

    # 5. Zone 3: Pointed Gothic Stone Belfry Arch framing the Giant Stained-Glass Bell (2480, 620)
    ctx.save()
    bx, by = 2480.0, 610.0
    bw, bh = 350.0, 620.0
    ctx.new_path()
    ctx.move_to(bx - bw * 0.5, by + bh * 0.55)
    ctx.line_to(bx - bw * 0.5, by - bh * 0.15)
    ctx.curve_to(bx - bw * 0.5, by - bh * 0.45, bx - bw * 0.1, by - bh * 0.54, bx, by - bh * 0.54)
    ctx.curve_to(bx + bw * 0.1, by - bh * 0.54, bx + bw * 0.5, by - bh * 0.45, bx + bw * 0.5, by - bh * 0.15)
    ctx.line_to(bx + bw * 0.5, by + bh * 0.55)
    ctx.set_source_rgba(0.08, 0.09, 0.14, 0.96)
    ctx.set_line_width(24.0)
    ctx.stroke_preserve()
    ctx.set_source_rgba(0.26, 0.29, 0.40, 0.55)
    ctx.set_line_width(2.4)
    ctx.stroke()
    ctx.restore()

    # 6. Zone 4: Grand 3-Ring Gothic Rose Window permanently anchored at (3480, 420)
    draw_grand_gothic_rose_window(
        ctx,
        rose_state["cx"],
        rose_state["cy"],
        rose_r=420.0,
        rot=rose_state["rot"],
        desaturate=rose_state["desaturate"],
        film_reel=rose_state["film_reel"],
    )


# ---------------------------------------------------------------------------
# 2. Hard-Facet Crystal Triangular Prism & Optical Dispersion Laser Beams
# ---------------------------------------------------------------------------
def draw_crystal_prism_and_refraction(ctx: cairo.Context, prism: dict, steps: list, t: float):
    """
    Renders:
      1. The Beveled Leaded-Glass Prism Pedestal at (1150, 1360).
      2. The Vertical Collimated White Sunbeam streaming from the cathedral zenith onto the prism.
      3. The Giant Hard-Facet Crystal Triangular Prism at (1235, 1265) with internal beveled crystal facets.
      4. When aligned (refract_intensity > 0), refracts the white beam into a 7-color spectral fan
         plus 3 blazing hard-edged dispersion laser beams (Ruby, Emerald, Sapphire) striking the 4 steps!
    """
    px, py = prism["cx"], prism["cy"]
    ped_x, ped_y = prism["pedestal_x"], prism["pedestal_y"]
    ang_rad = prism["angle_deg"] * math.pi / 180.0
    ref_int = float(prism["refract_intensity"])
    hit_flash = float(prism["hit_flash"])

    ctx.save()

    # 1. Beveled Leaded-Glass Prism Pedestal Platform
    st06.draw_gothic_stained_glass_step(
        ctx,
        ped_x + 40.0,
        ped_y + 10.0,
        240.0,
        52.0,
        color_rgb=(0.24, 0.52, 0.92),
        accent_rgb=(0.55, 0.85, 1.00),
        lit=0.65 + 0.35 * ref_int,
    )

    # 2. Vertical Collimated White Zenith Light Beam striking the Crystal Prism
    beam_top_y = py - 950.0
    ctx.new_path()
    ctx.move_to(px - 28.0, beam_top_y)
    ctx.line_to(px + 28.0, beam_top_y)
    ctx.line_to(px + 18.0, py + 10.0)
    ctx.line_to(px - 18.0, py + 10.0)
    ctx.close_path()
    wg = cairo.LinearGradient(px, beam_top_y, px, py)
    wg.add_color_stop_rgba(0.0, 0.95, 0.98, 1.00, 0.12)
    wg.add_color_stop_rgba(0.6, 0.96, 0.98, 1.00, 0.38)
    wg.add_color_stop_rgba(1.0, 1.00, 1.00, 0.96, 0.78)
    ctx.set_source(wg)
    ctx.fill()

    # Crisp bright core of incident white beam
    ctx.move_to(px, beam_top_y)
    ctx.line_to(px, py - 8.0)
    ctx.set_source_rgba(1.0, 1.0, 0.98, 0.85)
    ctx.set_line_width(5.5)
    ctx.stroke()

    # 3. Refracted Rainbow Spectral Fan & 3 Dispersion Laser Beams (Ruby, Emerald, Sapphire)
    if ref_int > 0.01:
        # A. Wide Rainbow Dispersion Caustic Fan
        fan_len = 1150.0 * ref_int
        fan_colors = [
            (-0.24, -0.14, (0.98, 0.22, 0.36)),  # Ruby Red
            (-0.14, -0.05, (0.98, 0.62, 0.14)),  # Amber Orange
            (-0.05,  0.04, (1.00, 0.90, 0.24)),  # Solar Yellow
            ( 0.04,  0.13, (0.10, 0.88, 0.56)),  # Chartres Emerald
            ( 0.13,  0.22, (0.20, 0.76, 1.00)),  # Sky Cyan
            ( 0.22,  0.31, (0.22, 0.42, 0.98)),  # Cobalt Sapphire
            ( 0.31,  0.40, (0.68, 0.28, 0.96)),  # Royal Amethyst
        ]
        for a0, a1, (r, g, b) in fan_colors:
            ctx.new_path()
            ctx.move_to(px + 20.0, py)
            ctx.line_to(px + 20.0 + fan_len * math.cos(a0), py + fan_len * math.sin(a0))
            ctx.line_to(px + 20.0 + fan_len * math.cos(a1), py + fan_len * math.sin(a1))
            ctx.close_path()
            fg = cairo.LinearGradient(px, py, px + fan_len, py)
            fg.add_color_stop_rgba(0.0, r, g, b, 0.48 * ref_int)
            fg.add_color_stop_rgba(0.6, r, g, b, 0.22 * ref_int)
            fg.add_color_stop_rgba(1.0, r, g, b, 0.0)
            ctx.set_source(fg)
            ctx.fill()

        # B. 4 Focused Hard-Edge Prismatic Laser Beams hitting the 4 Diamond Steps
        laser_specs = [
            (steps[0], (0.18, 0.62, 1.00)),  # Sapphire laser -> Step 1
            (steps[1], (0.12, 0.92, 0.58)),  # Emerald laser  -> Step 2
            (steps[2], (1.00, 0.78, 0.20)),  # Amber laser    -> Step 3
            (steps[3], (0.98, 0.28, 0.46)),  # Ruby laser     -> Step 4
        ]
        for st_target, lcol in laser_specs:
            tx, ty = st_target["x"], st_target["y"]
            # Outer laser glow
            ctx.new_path()
            ctx.move_to(px + 18.0, py)
            ctx.line_to(tx, ty)
            ctx.set_source_rgba(lcol[0], lcol[1], lcol[2], 0.36 * ref_int * (1.0 - 0.55 * st_target["rise_prog"]))
            ctx.set_line_width(14.0)
            ctx.stroke()

            # Inner laser core
            ctx.new_path()
            ctx.move_to(px + 18.0, py)
            ctx.line_to(tx, ty)
            ctx.set_source_rgba(1.0, 0.98, 0.92, 0.75 * ref_int * (1.0 - 0.65 * st_target["rise_prog"]))
            ctx.set_line_width(3.2)
            ctx.stroke()

    # 4. Giant Hard-Facet Crystal Triangular Prism Mesh (2D Beveled Polyhedron)
    ctx.save()
    ctx.translate(px, py)
    ctx.rotate(ang_rad)

    pr_r = 92.0
    # Outer triangle vertices (pointing up)
    v_top = (0.0, -pr_r)
    v_bl = (-pr_r * 0.88, pr_r * 0.68)
    v_br = (pr_r * 0.88, pr_r * 0.68)

    # Inner beveled triangle vertices (creates 4 hard crystal facets: 1 center + 3 side bevels)
    in_scale = 0.46
    i_top = (v_top[0] * in_scale, v_top[1] * in_scale + 8.0)
    i_bl = (v_bl[0] * in_scale, v_bl[1] * in_scale + 4.0)
    i_br = (v_br[0] * in_scale, v_br[1] * in_scale + 4.0)

    # Left bevel facet (Cyan-Sapphire crystal)
    ctx.new_path()
    for pt in (v_top, v_bl, i_bl, i_top):
        ctx.line_to(*pt)
    ctx.close_path()
    g_left = cairo.LinearGradient(v_top[0], v_top[1], v_bl[0], v_bl[1])
    g_left.add_color_stop_rgba(0.0, 0.75, 0.94, 1.00, 0.92)
    g_left.add_color_stop_rgba(1.0, 0.22, 0.58, 0.96, 0.88)
    ctx.set_source(g_left)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
    ctx.set_line_width(3.6)
    ctx.stroke()

    # Right bevel facet (Amethyst-Ruby-Gold dispersion crystal)
    ctx.new_path()
    for pt in (v_top, i_top, i_br, v_br):
        ctx.line_to(*pt)
    ctx.close_path()
    g_right = cairo.LinearGradient(v_top[0], v_top[1], v_br[0], v_br[1])
    g_right.add_color_stop_rgba(0.0, 1.00, 0.92, 0.68, 0.92)
    g_right.add_color_stop_rgba(0.5, 0.95, 0.42, 0.68, 0.88)
    g_right.add_color_stop_rgba(1.0, 0.58, 0.28, 0.92, 0.90)
    ctx.set_source(g_right)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
    ctx.set_line_width(3.6)
    ctx.stroke()

    # Bottom bevel facet (Deep Cobalt-Emerald crystal)
    ctx.new_path()
    for pt in (i_bl, v_bl, v_br, i_br):
        ctx.line_to(*pt)
    ctx.close_path()
    g_bot = cairo.LinearGradient(v_bl[0], v_bl[1], v_br[0], v_br[1])
    g_bot.add_color_stop_rgba(0.0, 0.14, 0.42, 0.85, 0.92)
    g_bot.add_color_stop_rgba(0.5, 0.12, 0.78, 0.62, 0.90)
    g_bot.add_color_stop_rgba(1.0, 0.42, 0.22, 0.78, 0.92)
    ctx.set_source(g_bot)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
    ctx.set_line_width(3.6)
    ctx.stroke()

    # Center core triangle facet (Brilliant diamond white-cyan-gold heart)
    ctx.new_path()
    for pt in (i_top, i_bl, i_br):
        ctx.line_to(*pt)
    ctx.close_path()
    g_core = cairo.RadialGradient(0, 6, 2, 0, 6, pr_r * 0.45)
    g_core.add_color_stop_rgba(0.0, 1.00, 1.00, 1.00, 0.98)
    g_core.add_color_stop_rgba(0.55, 0.68, 0.92, 1.00, 0.92)
    g_core.add_color_stop_rgba(1.0, 0.88, 0.52, 0.96, 0.90)
    ctx.set_source(g_core)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.09, 0.13, 0.98)
    ctx.set_line_width(3.0)
    ctx.stroke()

    # Specular metallic highlights on crystal ridges
    ctx.set_source_rgba(1.0, 0.98, 0.90, 0.85)
    ctx.set_line_width(1.6)
    for pa, pb in [(v_top, i_top), (v_bl, i_bl), (v_br, i_br), (i_top, i_bl)]:
        ctx.move_to(*pa)
        ctx.line_to(*pb)
    ctx.stroke()

    ctx.restore()  # End prism rotation

    # 5. Impact Starburst when Slime headbutts the Crystal Prism
    if hit_flash > 0.02:
        imp_x, imp_y = px - 55.0, py + 15.0
        draw_four_point_star(ctx, imp_x, imp_y, 58.0 * hit_flash, 16.0 * hit_flash, rot=t * 3.0)
        ctx.set_source_rgba(1.0, 0.98, 0.85, hit_flash)
        ctx.fill()

    ctx.restore()


# ---------------------------------------------------------------------------
# 3. Dynamic Concentric Stained-Glass Acoustic Shockwaves & Flying Shards
# ---------------------------------------------------------------------------
def draw_dynamic_shockwaves(ctx: cairo.Context, cx: float, cy: float, phase: float, intensity: float):
    """
    Renders expanding multi-spectral leaded-glass acoustic shockwaves radiating
    from the bell impact point with floating jewel beads and hard-facet glass shards.
    """
    if intensity <= 0.01:
        return

    ctx.save()

    # Central impact flash burst
    flash_r = 90.0 * min(1.0, intensity * 1.4)
    flash_g = cairo.RadialGradient(cx, cy, 3.0, cx, cy, flash_r)
    flash_g.add_color_stop_rgba(0.0, 1.0, 1.0, 0.96, 0.98 * intensity)
    flash_g.add_color_stop_rgba(0.35, 1.0, 0.88, 0.38, 0.88 * intensity)
    flash_g.add_color_stop_rgba(0.70, 0.45, 0.85, 1.00, 0.48 * intensity)
    flash_g.add_color_stop_rgba(1.0, 0.90, 0.40, 0.70, 0.0)
    ctx.set_source(flash_g)
    ctx.arc(cx, cy, flash_r, 0, math.tau)
    ctx.fill()

    spectral_colors = [
        (0.31, 0.68, 1.00),  # Cyan
        (0.98, 0.78, 0.24),  # Gold
        (0.85, 0.35, 0.95),  # Violet
        (0.95, 0.42, 0.48),  # Ruby
        (0.25, 0.88, 0.65),  # Emerald
        (0.45, 0.62, 1.00),  # Cobalt
    ]

    base_radii = [110, 230, 370, 530, 710, 910, 1140]
    for idx, r_base in enumerate(base_radii):
        r_wave = r_base + (phase * 155.0) % 340.0
        col = spectral_colors[idx % len(spectral_colors)]
        fade = max(0.0, min(1.0, 1.0 - (r_wave / 1350.0))) * intensity

        if fade <= 0.01:
            continue

        # Soft prismatic caustic ribbon
        ctx.arc(cx, cy, r_wave, 0, math.tau)
        ctx.set_source_rgba(col[0], col[1], col[2], fade * 0.46)
        ctx.set_line_width(14.0)
        ctx.stroke()

        # Dark solder lead came wave ring
        ctx.arc(cx, cy, r_wave, 0, math.tau)
        ctx.set_source_rgba(0.08, 0.09, 0.13, fade * 0.88)
        ctx.set_line_width(3.0)
        ctx.stroke()

        # Warm specular highlight
        ctx.arc(cx, cy, r_wave - 2.4, 0, math.tau)
        ctx.set_source_rgba(1.0, 0.96, 0.84, fade * 0.85)
        ctx.set_line_width(1.3)
        ctx.stroke()

        # Floating 4-point star jewel beads & hard-facet triangular shards on shockwave perimeter
        n_beads = 6 + idx * 2
        for b_i in range(n_beads):
            ang = (b_i / n_beads) * math.tau + phase * 0.35 + idx * 0.4
            bx = cx + r_wave * math.cos(ang)
            by = cy + r_wave * math.sin(ang)

            if b_i % 2 == 0:
                bead_r = 5.5 + (idx % 3) * 1.8
                draw_four_point_star(ctx, bx, by, bead_r, bead_r * 0.32, rot=ang)
            else:
                # Hard-facet diamond/triangle stained-glass shard
                sh_r = 6.5 + (idx % 3) * 2.0
                ctx.new_path()
                for k in range(3):
                    ka = ang + k * (math.tau / 3.0)
                    ctx.line_to(bx + sh_r * math.cos(ka), by + sh_r * math.sin(ka))
                ctx.close_path()

            ctx.set_source_rgba(min(1.0, col[0] + 0.32), min(1.0, col[1] + 0.32), min(1.0, col[2] + 0.32), fade * 0.92)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.08, 0.09, 0.12, fade)
            ctx.set_line_width(1.5)
            ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# 4. Dynamic Undulating Golden Stained-Glass Bell Rope
# ---------------------------------------------------------------------------
def draw_golden_bell_rope(ctx: cairo.Context, start_pt: tuple, end_pt: tuple, active: bool = False, t: float = 0.0):
    x0, y0 = start_pt
    x1, y1 = end_pt

    ctx.save()
    ctx.new_path()

    wave1 = 28.0 * math.sin(t * 4.2) if not active else 12.0
    wave2 = -22.0 * math.cos(t * 3.6) if not active else -8.0

    c1x = x0 - 20.0 + wave1
    c1y = y0 + (y1 - y0) * 0.38
    c2x = x1 + 25.0 + wave2
    c2y = y0 + (y1 - y0) * 0.72

    ctx.move_to(x0, y0)
    ctx.curve_to(c1x, c1y, c2x, c2y, x1, y1)

    ctx.set_source_rgba(0.08, 0.09, 0.12, 0.96)
    ctx.set_line_width(5.6)
    ctx.stroke_preserve()

    ctx.set_source_rgba(1.0, 0.84, 0.32, 0.96)
    ctx.set_line_width(2.8)
    ctx.stroke()

    for u in np.linspace(0.14, 0.96, 7):
        omt = 1.0 - u
        px = (omt**3)*x0 + 3*(omt**2)*u*c1x + 3*omt*(u**2)*c2x + (u**3)*x1
        py = (omt**3)*y0 + 3*(omt**2)*u*c1y + 3*omt*(u**2)*c2y + (u**3)*y1
        ctx.arc(px, py, 4.8, 0, math.tau)
        ctx.set_source_rgba(1.0, 0.95, 0.72, 0.98)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
        ctx.set_line_width(1.6)
        ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# 5. Dynamic 7-Color Sweeping Prismatic Ribbon Bridge (with Elastic Dent)
# ---------------------------------------------------------------------------
def draw_dynamic_ribbon_bridge(ctx: cairo.Context, ribbon_state: dict):
    """
    Renders the 7-color sweeping prismatic ribbon bridge spanning from Step 4 (2220, 980)
    directly into the Grand Gothic Rose Window (3480, 420), with elastic wave depression
    under the Slime's landing points!
    """
    progress = float(ribbon_state.get("progress", 0.0))
    shimmer_phase = float(ribbon_state.get("shimmer_phase", 0.0))
    slime_x = float(ribbon_state.get("slime_x", -9999.0))
    slime_grounded = bool(ribbon_state.get("slime_grounded", False))

    if progress <= 0.01:
        return

    p0 = np.array(RIBBON_P0, dtype=np.float64)
    c1 = np.array(RIBBON_C1, dtype=np.float64)
    c2 = np.array(RIBBON_C2, dtype=np.float64)
    p3 = np.array(RIBBON_P3, dtype=np.float64)

    n_samples = max(6, int(progress * 75))
    u_vals = np.linspace(0.0, progress, n_samples)
    pts = []
    for u in u_vals:
        omt = 1.0 - u
        pt = (omt**3)*p0 + 3*(omt**2)*u*c1 + 3*omt*(u**2)*c2 + (u**3)*p3
        # Elastic wave dent when Slime lands on the bridge
        dent = math.sin(shimmer_phase * 1.5 - u * 10.0) * 3.5
        if slime_grounded and abs(pt[0] - slime_x) < 130.0:
            dent += math.cos((pt[0] - slime_x) / 130.0 * math.pi * 0.5) * 16.0
        pts.append((float(pt[0]), float(pt[1] + dent)))

    if len(pts) < 2:
        return

    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    # 1. Soft Outer Prismatic Caustic Aura
    ctx.new_path()
    ctx.move_to(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        ctx.line_to(pt[0], pt[1])
    ctx.set_source_rgba(0.55, 0.78, 1.00, 0.18 * min(1.0, progress * 2.0))
    ctx.set_line_width(78.0)
    ctx.stroke()

    # 2. Seven Translucent Jewel-Toned Spectral Light Ribbons
    spectral_bands = [
        (-25.0, (0.96, 0.26, 0.40), 0.46, 9.0),   # Ruby Coral
        (-16.5, (0.98, 0.56, 0.16), 0.48, 9.0),   # Imperial Amber
        ( -8.2, (1.00, 0.86, 0.24), 0.52, 9.5),   # Solar Gold
        (  0.0, (0.12, 0.86, 0.56), 0.50, 10.0),  # Chartres Emerald
        (  8.2, (0.20, 0.78, 1.00), 0.52, 9.5),   # Sky Cyan
        ( 16.5, (0.22, 0.46, 0.98), 0.48, 9.0),   # Cobalt Sapphire
        ( 25.0, (0.68, 0.32, 0.96), 0.46, 9.0),   # Royal Amethyst
    ]

    for dy_off, (r, g, b), alpha_val, lw in spectral_bands:
        ctx.new_path()
        ctx.move_to(pts[0][0], pts[0][1] + dy_off)
        for pt in pts[1:]:
            ctx.line_to(pt[0], pt[1] + dy_off)
        ctx.set_source_rgba(r, g, b, alpha_val * min(1.0, progress * 2.0))
        ctx.set_line_width(lw)
        ctx.stroke()

    # 3. Delicate Leaded Gold-and-Charcoal Filigree Borders Framing the Ribbon Bridge
    for border_off in (-30.0, 30.0):
        ctx.new_path()
        ctx.move_to(pts[0][0], pts[0][1] + border_off)
        for pt in pts[1:]:
            ctx.line_to(pt[0], pt[1] + border_off)
        ctx.set_source_rgba(0.08, 0.09, 0.13, 0.88)
        ctx.set_line_width(2.8)
        ctx.stroke_preserve()
        ctx.set_source_rgba(1.0, 0.92, 0.68, 0.65)
        ctx.set_line_width(1.2)
        ctx.stroke()

    # 4. Luminous Starlight Spine & Four-Point Star Diamond Nodes
    ctx.new_path()
    ctx.move_to(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        ctx.line_to(pt[0], pt[1])
    ctx.set_source_rgba(1.0, 0.98, 0.88, 0.78)
    ctx.set_line_width(3.4)
    ctx.stroke()

    node_step = max(4, len(pts) // 8)
    for i in range(node_step, len(pts), node_step):
        nx, ny = pts[i]
        draw_four_point_star(ctx, nx, ny, 8.0, 2.4, rot=shimmer_phase * 0.4 + i * 0.5)
        ctx.set_source_rgba(1.0, 0.96, 0.78, 0.90)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.08, 0.09, 0.13, 0.92)
        ctx.set_line_width(1.3)
        ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# 6. Stained-Glass Landing Caustic Ripples & Speech Bubbles
# ---------------------------------------------------------------------------
def draw_landing_caustic_ripples(ctx: cairo.Context, t: float):
    """
    Renders expanding diamond leaded-glass caustic ripples at every exact Slime landing spot!
    """
    landing_events = [
        (0.80,  320.0, GALLERY_FLOOR_Y, (0.35, 0.75, 1.00)),
        (1.88,  520.0, GALLERY_FLOOR_Y, (0.15, 0.55, 1.00)),
        (2.78,  760.0, GALLERY_FLOOR_Y, (0.10, 0.88, 0.58)),
        (3.68, 1000.0, GALLERY_FLOOR_Y, (0.98, 0.28, 0.42)),
        (5.95, 1135.0, 1360.0,          (0.35, 0.82, 1.00)),
        (9.05, 1470.0, 1340.0,          (0.12, 0.48, 0.98)),
        (9.95, 1720.0, 1220.0,          (0.06, 0.78, 0.48)),
        (10.85, 1970.0, 1100.0,         (0.98, 0.70, 0.14)),
        (11.75, 2220.0,  980.0,         (0.90, 0.24, 0.42)),
        (14.30, 2220.0,  980.0,         (1.00, 0.85, 0.35)),
        (16.95, 2220.0,  980.0,         (0.95, 0.35, 0.65)),
        (20.25, 2528.0,  908.0,         (0.20, 0.78, 1.00)),
        (21.25, 2838.0,  805.0,         (0.12, 0.86, 0.56)),
        (22.25, 3155.0,  652.0,         (0.98, 0.70, 0.24)),
    ]

    ctx.save()
    for t_land, lx, ly, col in landing_events:
        dt = t - t_land
        if 0.0 <= dt <= 0.65:
            fade = max(0.0, 1.0 - dt / 0.65)
            r_rip = dt * 125.0 + 14.0

            g_c = cairo.RadialGradient(lx, ly, 2, lx, ly, r_rip * 1.3)
            g_c.add_color_stop_rgba(0.0, col[0], col[1], col[2], fade * 0.48)
            g_c.add_color_stop_rgba(0.6, col[0], col[1], col[2], fade * 0.20)
            g_c.add_color_stop_rgba(1.0, col[0], col[1], col[2], 0.0)
            ctx.set_source(g_c)
            ctx.arc(lx, ly, r_rip * 1.3, 0, math.tau)
            ctx.fill()

            ctx.save()
            ctx.translate(lx, ly)
            ctx.scale(1.4, 0.65)
            ctx.new_path()
            ctx.move_to(0, -r_rip)
            ctx.line_to(r_rip, 0)
            ctx.line_to(0, r_rip)
            ctx.line_to(-r_rip, 0)
            ctx.close_path()

            ctx.set_source_rgba(col[0], col[1], col[2], fade * 0.80)
            ctx.set_line_width(3.0)
            ctx.stroke_preserve()
            ctx.set_source_rgba(1.0, 0.96, 0.82, fade * 0.88)
            ctx.set_line_width(1.2)
            ctx.stroke()

            for dx, dy in [(0, -r_rip), (r_rip, 0), (0, r_rip), (-r_rip, 0)]:
                draw_four_point_star(ctx, dx, dy, 5.5, 1.8, rot=dt * 4.0)
                ctx.set_source_rgba(1.0, 0.98, 0.88, fade * 0.92)
                ctx.fill()
            ctx.restore()

    ctx.restore()


def draw_leaded_bubble(ctx: cairo.Context, cx: float, cy: float, bubble_type: str):
    """Renders a hard-facet diamond/octagon leaded stained-glass speech bubble ([?] or [!])."""
    ctx.save()
    ctx.translate(cx, cy)

    # Octagonal hard-facet crystal bubble frame
    ctx.new_path()
    for i in range(8):
        ang = (i / 8.0) * math.tau + math.pi / 8.0
        rx = 26.0 * math.cos(ang)
        ry = 30.0 * math.sin(ang)
        if i == 0:
            ctx.move_to(rx, ry)
        else:
            ctx.line_to(rx, ry)
    ctx.close_path()

    if bubble_type == "question":
        bg = cairo.RadialGradient(0, 0, 2, 0, 0, 28)
        bg.add_color_stop_rgba(0.0, 0.62, 0.90, 1.00, 0.96)
        bg.add_color_stop_rgba(1.0, 0.16, 0.38, 0.88, 0.94)
    else:
        bg = cairo.RadialGradient(0, 0, 2, 0, 0, 28)
        bg.add_color_stop_rgba(0.0, 1.00, 0.96, 0.62, 0.96)
        bg.add_color_stop_rgba(1.0, 0.98, 0.56, 0.12, 0.94)

    ctx.set_source(bg)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
    ctx.set_line_width(3.4)
    ctx.stroke()

    ctx.set_source_rgba(0.08, 0.09, 0.12, 1.0)
    ctx.set_line_width(4.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    if bubble_type == "question":
        ctx.new_path()
        ctx.arc(0, -8.0, 7.5, -math.pi * 0.9, 0.2)
        ctx.curve_to(6.0, -2.0, 0, 2.0, 0, 6.0)
        ctx.stroke()
        ctx.arc(0, 13.0, 2.6, 0, math.tau)
        ctx.fill()
    else:
        ctx.new_path()
        ctx.move_to(0, -12.0)
        ctx.line_to(0, 4.0)
        ctx.stroke()
        ctx.arc(0, 12.0, 2.6, 0, math.tau)
        ctx.fill()

    ctx.restore()


# ---------------------------------------------------------------------------
# 7. Screen-Space Entry/Exit Transition Overlays (World 05 -> 06 -> 07)
# ---------------------------------------------------------------------------
def draw_screen_transitions(ctx: cairo.Context, zoetrope_intro: float, film_reel: float, t: float):
    ctx.save()
    ctx.identity_matrix()

    # A. 0.0 - 0.85s: Octagonal Paper Zoetrope Lattice Hardening into Stained-Glass Lead Cames
    if zoetrope_intro > 0.01:
        r_open = (1.0 - zoetrope_intro) * 1150.0 + 180.0
        ctx.new_path()
        ctx.rectangle(0, 0, W, H)
        for i in range(8):
            ang = (i / 8.0) * math.tau + (1.0 - zoetrope_intro) * 0.35
            px = W * 0.5 + r_open * math.cos(ang)
            py = H * 0.5 + r_open * math.sin(ang)
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.close_path()
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        ctx.set_source_rgba(0.04, 0.04, 0.07, zoetrope_intro * 0.92)
        ctx.fill()
        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)

        # Gold-to-Lead octagonal border
        ctx.new_path()
        for i in range(8):
            ang = (i / 8.0) * math.tau + (1.0 - zoetrope_intro) * 0.35
            px = W * 0.5 + r_open * math.cos(ang)
            py = H * 0.5 + r_open * math.sin(ang)
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.close_path()
        ctx.set_source_rgba(0.95, 0.78, 0.28, zoetrope_intro)
        ctx.set_line_width(6.0)
        ctx.stroke()

    # B. 23.90 - 26.00s: 1930s 35mm Sepia Film Sprocket Borders & Closing Vintage Theater Curtains
    #    (NO duplicate 3-2-1 countdown here — the 3-2-1 countdown plays on the closed curtain in World 07!)
    if film_reel > 0.20:
        f_alpha = min(1.0, (film_reel - 0.20) / 0.75)
        # Sepia vintage film wash
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0.16, 0.13, 0.10, f_alpha * 0.42)
        ctx.fill()

        # Slide in the 1930s Theater Curtains & Pelmet (closing from open_prog=1.0 -> 0.0 over 24.35s..25.75s)
        if t >= 24.05:
            pelmet_in = min(1.0, (t - 24.05) / 0.50)
            pelmet_ease = pelmet_in * pelmet_in * (3.0 - 2.0 * pelmet_in)
            close_raw = max(0.0, min(1.0, (t - 24.35) / 1.40))
            close_ease = close_raw * close_raw * (3.0 - 2.0 * close_raw)
            open_prog = 1.0 - close_ease

            ctx.save()
            if pelmet_ease < 0.999:
                ctx.translate(0.0, -(1.0 - pelmet_ease) * 160.0)
            st09.draw_vintage_theater_curtains(ctx, bounce_dy=0.0, open_prog=open_prog)
            ctx.restore()

        # Left & Right 35mm film sprocket borders sliding in (exact match with World 07!)
        sprocket_in = min(1.0, max(0.0, (t - 23.95) / 0.55))
        sprocket_ease = sprocket_in * sprocket_in * (3.0 - 2.0 * sprocket_in)
        if sprocket_ease > 0.01:
            ctx.save()
            if sprocket_ease < 0.999:
                ctx.push_group()
                st09.draw_35mm_sprocket_borders(ctx)
                ctx.pop_group_to_source()
                ctx.paint_with_alpha(sprocket_ease)
            else:
                st09.draw_35mm_sprocket_borders(ctx)
            ctx.restore()

    ctx.restore()


# ---------------------------------------------------------------------------
# Master Frame Renderer: render_frame_from_state
# ---------------------------------------------------------------------------
def render_frame_from_state(state: dict) -> Image.Image:
    t = float(state.get("t", 0.0))
    cam = state.get("camera", {"cx": 960.0, "cy": 540.0, "zoom": 1.0})
    cam_x = float(cam.get("cx", 960.0))
    cam_y = float(cam.get("cy", 540.0))
    zoom = float(cam.get("zoom", 1.0))

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    # Apply Smooth Camera Transform over the 4200x2160 Cathedral World
    ctx.save()
    ctx.translate(W * 0.5, H * 0.5)
    ctx.scale(zoom, zoom)
    ctx.translate(-cam_x, -cam_y)

    # 1. Expansive 4-Zone Gothic Cathedral Background, Lancet Windows & Grand Rose Window (3480, 420)
    draw_expansive_cathedral_background(
        ctx,
        cam_x,
        cam_y,
        state.get("lancet_lit", [1.0, 1.0, 1.0]),
        state.get("rose_window", {"cx": ROSE_WINDOW_POS[0], "cy": ROSE_WINDOW_POS[1], "rot": 0.0, "desaturate": 0.0, "film_reel": 0.0}),
        t,
    )

    # 2. Hard-Facet Crystal Triangular Prism & Refracted Dispersion Laser Beams
    steps = state.get("steps", [])
    draw_crystal_prism_and_refraction(ctx, state.get("prism", {}), steps, t)

    # 3. 4 Beveled Gothic Diamond Stained-Glass Steps (Step 1 -> Step 4)
    for s in steps:
        st06.draw_gothic_stained_glass_step(
            ctx,
            s["x"],
            s["y"],
            s["w"],
            s["h"],
            color_rgb=s["color"],
            accent_rgb=s["accent"],
            lit=s["lit"],
        )

    # 4. Sweeping 7-Color Prismatic Light Ribbon Bridge (Step 4 -> Rose Window)
    draw_dynamic_ribbon_bridge(ctx, state.get("ribbon_bridge", {}))

    # 5. Upper-Right Twin Stained-Glass Chime Bells
    for c in state.get("chimes", []):
        st06.draw_stained_glass_bell(
            ctx,
            c["cx"],
            c["cy"],
            scale=c["scale"],
            swing_deg=c["swing_deg"],
            resonant_glow=c["resonant_glow"],
        )

    # 6. Giant Hard-Facet Stained-Glass Cathedral Bell (2480, 620)
    bell = state.get("bell", {})
    st06.draw_stained_glass_bell(
        ctx,
        bell["cx"],
        bell["cy"],
        scale=bell["scale"],
        swing_deg=bell["swing_deg"],
        resonant_glow=bell.get("resonant_glow", False),
    )

    # 7. Undulating Golden Stained-Glass Bell Rope
    rope = state.get("rope", {})
    if "start" in rope and "end" in rope:
        draw_golden_bell_rope(ctx, rope["start"], rope["end"], active=rope.get("active", False), t=t)

    # 8. Concentric Hard-Facet Stained-Glass Acoustic Shockwaves
    shock = state.get("shockwave", {})
    if shock.get("active", False):
        draw_dynamic_shockwaves(
            ctx,
            shock["cx"],
            shock["cy"],
            phase=float(shock.get("phase", 0.0)),
            intensity=float(shock.get("intensity", 1.0)),
        )

    # 9. Physical World Token: Stained-Glass Chime Bell (world_num=6)
    token = state.get("token", {})
    if token and not token.get("absorbed", False) and token.get("alpha", 0.0) > 0.01:
        draw_world_token(
            ctx,
            6,
            token["cx"],
            token["cy"],
            token["r"],
            rot=token.get("rot", 0.0),
            t=t,
            alpha=token.get("alpha", 1.0),
        )

    # 10. Stained-Glass Landing Caustic Ripples
    draw_landing_caustic_ripples(ctx, t)

    # 11. Guiding 4-Facet Stained-Glass Star ✦
    star = state.get("star", {})
    if star and star.get("visible", True):
        st06.draw_star(
            ctx,
            star["cx"],
            star["cy"],
            star["r"],
            rot=star.get("rot", 0.0),
            t=t,
        )

    # 12. 28-Pane Hard-Facet Voronoi Stained-Glass Slime
    sl = state.get("slime", {})
    if sl and sl.get("visible", True) and sl.get("alpha", 1.0) > 0.01:
        ctx.save()
        if sl.get("alpha", 1.0) < 0.99:
            ctx.push_group()

        st06.draw_slime(
            ctx,
            sl["cx"],
            sl["cy"],
            sl["radius"],
            squash_y=sl.get("squash_y", 1.0),
            tilt=sl.get("tilt", 0.0),
            look=sl.get("look", (0.0, 0.0)),
            eye_mode=sl.get("eye_mode", "pill"),
            blink=sl.get("blink", 0.0),
            t=t,
            roll_angle=sl.get("roll_angle", 0.0),
            grounded=sl.get("grounded", True),
        )

        if sl.get("alpha", 1.0) < 0.99:
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(sl["alpha"])
        ctx.restore()

        bubble = sl.get("bubble")
        if bubble:
            draw_leaded_bubble(ctx, sl["cx"] + 42.0, sl["cy"] - sl["radius"] * 1.38, bubble)

    ctx.restore()  # End camera transform

    # 13. Screen-Space Entry/Exit Transition Overlays
    draw_screen_transitions(
        ctx,
        float(state.get("zoetrope_intro", 0.0)),
        float(state.get("rose_window", {}).get("film_reel", 0.0)),
        t,
    )

    # Convert PyCairo surface to PIL Image
    w_px, h_px = surface.get_width(), surface.get_height()
    buf = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape((h_px, w_px, 4))
    rgb = buf[:, :, [2, 1, 0]].astype(np.float32) / 255.0
    rgb = np.clip(rgb * 1.04, 0.0, 1.0)
    return Image.fromarray((rgb * 255.0).astype(np.uint8), mode="RGB")
