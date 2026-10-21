#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StyleHop · World 04 · 水墨宣纸千里长卷 (style_04_inkwash.py)
Standalone 1920x1080 keyframe & 7680x1080 4-screen scroll module.

Design & Narrative Fusion (v3 Masterpiece Ink-Wash + STORY.md Keyframe Beat):
  1. Tactile Raw Xuan Paper Backdrop (生宣纸 #F6F2E8 -> #E6DCCA):
     Warm ivory-ochre handmade rice paper texture with plant bark fibers,
     multi-scale mottling, and subtle tea-wash flecks (without blurring brush edges).
  2. 100% v3 Calligraphic Ink Mastery:
     - Left vigorous ink bamboo grove (浓淡青竹、雀头节、个字/介字竹叶) + flexing hero bamboo stalk.
     - Upper-left vertical running-script calligraphy inscription:
       「星芒入画 · 一点灵犀 / 双子乘风跃青竹 · 毫端泼墨化莲华」 + mini cinnabar gourd seal 「星芒」.
     - Three layers of distant pine-soot ink mountains (远山淡墨晕染) fading into negative-space
       mist ribbons (留白烟波) and a distant Song-dynasty broken stone arch bridge (淡墨断桥).
     - Expressive splashed-ink lotus pads (大写意泼墨荷叶) with luminous mud-gold veins (泥金叶脉)
       and delicate pink-white blooming ink lotus & buds (粉白墨荷与荷苞).
     - Upper-right giant suspended square cinnabar seal arch (朱砂方印拱门「双子奇观」)
       with concentric cinnabar shockwave rings and radial calligraphic sparks.
  3. STORY.md Keyframe Narrative Action:
     - Ink-Wash Slime (花青 #2B5B84 -> 青莲 #5E3A73 -> 胭脂 #C84B31 wet diffusion, dry-brush
       feibai outline, unpainted Xuan-paper negative-space capsule eyes at -30° cant & 81% far-eye
       width, strictly mouthless) lightly stepping between bamboo and splashed-ink lotus pads,
       sending concentric ink ripples across the water.
     - Beside the lotus pad, a lively expressive Cinnabar Fish (朱砂写意游鱼) leaps out of the water,
       with the 4-point Star-Spark ✦ (泥金勾边 + 朱砂点心) riding above its back/leading the way,
       surrounded by splashing mineral indigo (花青), sumi-ink, and cinnabar droplets!
     - Strictly NO bottom-left UI tag.
"""

import os
import sys
import math
import random
import numpy as np
import cairo
from scipy.ndimage import gaussian_filter
from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from slime_engine import (
    SlimePose,
    compute_slime_contour,
    draw_slime_path,
    draw_four_point_star,
    draw_capsule_pill,
    cairo_to_pil,
    pil_to_cairo,
    get_pil_font,
    FONT_CJK_BOLD,
    FONT_CJK_MED,
)

# ==============================================================================
# 0. MODULE CONTRACT CONSTANTS
# ==============================================================================
W, H = 1920, 1080
WORLD_W, WORLD_H = 7680, 1080  # 4-screen horizontal Song-dynasty handscroll

# Keyframe camera centers on x=4800.0 (viewport [3840.0, 5760.0])
KEY_CAM_X = 4800.0
KEY_CAM_Y = 540.0
KEY_OX = KEY_CAM_X - W * 0.5  # 3840.0

_PAPER_CACHE = {}


# ==============================================================================
# 1. TACTILE XUAN PAPER GRAIN SYNTHESIZER (生宣纸微观纤维质感 - v3 Base)
# ==============================================================================
def make_xuan_paper(width: int = W, height: int = H, seed: int = 108) -> tuple[np.ndarray, np.ndarray]:
    """
    Synthesizes authentic handmade raw Xuan paper (生宣纸):
      - Base warm ivory-ochre color gradient (#F6F2E8 -> #E6DCCA)
      - Plant bark fibers (青檀皮/沙田稻草长纤维) with directional horizontal/vertical weave
      - Multi-scale ink-absorbent paper tooth mottling
    Returns: (paper_rgb [0..1], grain_field)
    """
    key = (width, height, seed)
    if key in _PAPER_CACHE:
        return _PAPER_CACHE[key]

    rng = np.random.default_rng(seed)

    y_coords = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x_coords = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    diag = 0.55 * y_coords + 0.45 * x_coords

    c_top = np.array([247.0, 242.0, 232.0], dtype=np.float32) / 255.0
    c_bot = np.array([230.0, 220.0, 202.0], dtype=np.float32) / 255.0
    base_rgb = c_top[None, None, :] * (1.0 - diag[..., None]) + c_bot[None, None, :] * diag[..., None]

    # Subtle gentle vignette
    rad = np.sqrt((x_coords - 0.5) ** 2 + (y_coords - 0.52) ** 2)
    vignette = 1.0 - 0.042 * np.clip(rad * 1.4, 0.0, 1.0)
    base_rgb *= vignette[..., None]

    # Fibrous mottling fields
    n_fine = rng.standard_normal((height, width), dtype=np.float32)
    n_med = gaussian_filter(rng.standard_normal((height, width), dtype=np.float32), sigma=2.0)
    n_clouds = gaussian_filter(rng.standard_normal((height, width), dtype=np.float32), sigma=12.0)

    # Elongated cellulose fiber streaks (Xuan paper characteristic)
    n_fiber_h = gaussian_filter(rng.standard_normal((height, width), dtype=np.float32), sigma=(0.6, 7.5))
    n_fiber_v = gaussian_filter(rng.standard_normal((height, width), dtype=np.float32), sigma=(6.0, 0.7))

    grain = (
        0.26 * (n_fine / (np.std(n_fine) + 1e-6))
        + 0.32 * (n_med / (np.std(n_med) + 1e-6))
        + 0.22 * (n_clouds / (np.std(n_clouds) + 1e-6))
        + 0.12 * (n_fiber_h / (np.std(n_fiber_h) + 1e-6))
        + 0.08 * (n_fiber_v / (np.std(n_fiber_v) + 1e-6))
    )
    grain = np.clip(grain, -3.0, 3.0)

    # Rare tiny bark flecks / tea-wash specks (宣纸草木微粒)
    fleck_mask = rng.random((height, width)) < 0.00035
    fleck_vals = rng.uniform(0.12, 0.28, size=(height, width)).astype(np.float32)
    fleck_layer = gaussian_filter((fleck_mask * fleck_vals).astype(np.float32), sigma=0.8)

    paper_rgb = np.clip(base_rgb + grain[..., None] * 0.016 - fleck_layer[..., None], 0.0, 1.0)
    _PAPER_CACHE[key] = (paper_rgb, grain)
    return paper_rgb, grain


def draw_paper_fibers(ctx: cairo.Context, width: int = W, height: int = H, seed: int = 108):
    """Draws subtle handmade Xuan paper mulberry bark threads (青檀皮丝) on the background."""
    rng = random.Random(seed)
    ctx.save()
    for _ in range(420):
        x0 = rng.uniform(0, width)
        y0 = rng.uniform(0, height)
        length = rng.uniform(14, 52)
        angle = rng.uniform(0, math.tau)
        curve = rng.uniform(-0.38, 0.38) * length
        x1 = x0 + length * math.cos(angle)
        y1 = y0 + length * math.sin(angle)
        cx = (x0 + x1) * 0.5 + curve * math.sin(angle)
        cy = (y0 + y1) * 0.5 - curve * math.cos(angle)

        if rng.random() < 0.62:
            ctx.set_source_rgba(0.68, 0.60, 0.48, rng.uniform(0.10, 0.22))
        else:
            ctx.set_source_rgba(0.99, 0.97, 0.92, rng.uniform(0.18, 0.35))

        ctx.set_line_width(rng.uniform(0.45, 0.95))
        ctx.move_to(x0, y0)
        ctx.curve_to(cx, cy, cx, cy, x1, y1)
        ctx.stroke()
    ctx.restore()


_XUAN_PAPER_SURF_CACHE = {}


def create_xuan_paper_background(width: int = W, height: int = H, seed: int = 108) -> cairo.ImageSurface:
    """
    Creates and returns a cached cairo.ImageSurface of authentic handmade raw Xuan paper (生宣纸)
    with plant bark fibers and warm ivory-ochre tones (#F6F2E8 -> #E6DCCA).
    """
    key = (width, height, seed)
    if key in _XUAN_PAPER_SURF_CACHE:
        return _XUAN_PAPER_SURF_CACHE[key]

    paper_rgb, _ = make_xuan_paper(width, height, seed=seed)
    paper_u8 = (np.clip(paper_rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    bgra = np.zeros((height, width, 4), dtype=np.uint8)
    bgra[:, :, 0] = paper_u8[:, :, 2]  # B
    bgra[:, :, 1] = paper_u8[:, :, 1]  # G
    bgra[:, :, 2] = paper_u8[:, :, 0]  # R
    bgra[:, :, 3] = 255

    surf = cairo.ImageSurface.create_for_data(bgra, cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surf)
    draw_paper_fibers(ctx, width, height, seed=seed)
    _XUAN_PAPER_SURF_CACHE[key] = surf
    _XUAN_PAPER_SURF_CACHE[(key, "buf")] = bgra
    return surf


# ==============================================================================
# 2. CALLIGRAPHIC INK UTILITIES (墨分五色 & 飞白笔触)
# ==============================================================================
def draw_brush_leaf(
    ctx: cairo.Context,
    x0: float,
    y0: float,
    length: float,
    angle: float,
    width_mid: float,
    ink_rgba: tuple,
    bend: float = 0.0,
):
    """
    Renders an authentic calligraphic bamboo leaf (个字/介字撇捺竹叶):
      - Sharp entry (藏锋露锋起笔)
      - Swollen belly (中锋行笔按压)
      - Sweeping tapered sharp tip (收锋出挑)
    """
    ctx.save()
    ctx.translate(x0, y0)
    ctx.rotate(angle)

    tip_x = length
    tip_y = bend * length
    ctrl1_x = length * 0.32
    ctrl1_y = -width_mid * 0.85 + bend * length * 0.15
    ctrl2_x = length * 0.65
    ctrl2_y = -width_mid * 0.35 + bend * length * 0.55

    ctrl3_x = length * 0.68
    ctrl3_y = width_mid * 0.35 + bend * length * 0.55
    ctrl4_x = length * 0.28
    ctrl4_y = width_mid * 0.85 + bend * length * 0.15

    ctx.new_path()
    ctx.move_to(0, 0)
    ctx.curve_to(ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, tip_x, tip_y)
    ctx.curve_to(ctrl3_x, ctrl3_y, ctrl4_x, ctrl4_y, 0, 0)
    ctx.close_path()

    ctx.set_source_rgba(*ink_rgba)
    ctx.fill()
    ctx.restore()


def draw_bamboo_culm_segment(
    ctx: cairo.Context,
    p0: tuple[float, float],
    p1: tuple[float, float],
    w0: float,
    w1: float,
    ink_rgba: tuple,
    is_joint: bool = True,
):
    """
    Draws a calligraphic bamboo stalk segment with subtle bone-stroke taper
    and distinct joint ring (竹节雀头结).
    """
    x0, y0 = p0
    x1, y1 = p1
    dx = x1 - x0
    dy = y1 - y0
    seg_len = max(1e-4, math.hypot(dx, dy))
    ang = math.atan2(dy, dx)
    norm_ang = ang + math.pi / 2.0
    nx = math.cos(norm_ang)
    ny = math.sin(norm_ang)

    w_mid = (w0 + w1) * 0.5 * 0.94

    ctx.save()
    ctx.new_path()
    ctx.move_to(x0 - nx * w0 * 0.5, y0 - ny * w0 * 0.5)
    ctx.curve_to(
        x0 + dx * 0.25 - nx * w_mid * 0.52,
        y0 + dy * 0.25 - ny * w_mid * 0.52,
        x1 - dx * 0.25 - nx * w_mid * 0.52,
        y1 - dy * 0.25 - ny * w_mid * 0.52,
        x1 - nx * w1 * 0.5,
        y1 - ny * w1 * 0.5,
    )
    ctx.line_to(x1 + nx * w1 * 0.5, y1 + ny * w1 * 0.5)
    ctx.curve_to(
        x1 - dx * 0.25 + nx * w_mid * 0.52,
        y1 - dy * 0.25 + ny * w_mid * 0.52,
        x0 + dx * 0.25 + nx * w_mid * 0.52,
        y0 + dy * 0.25 + ny * w_mid * 0.52,
        x0 + nx * w0 * 0.5,
        y0 + ny * w0 * 0.5,
    )
    ctx.close_path()
    ctx.set_source_rgba(*ink_rgba)
    ctx.fill()

    if is_joint:
        joint_w = max(w1 * 1.32, w1 + 5.0)
        ctx.new_path()
        jx0 = x1 - nx * joint_w * 0.5
        jy0 = y1 - ny * joint_w * 0.5
        jx1 = x1 + nx * joint_w * 0.5
        jy1 = y1 + ny * joint_w * 0.5
        j_ctrl_x = x1 + dx / seg_len * 2.8
        j_ctrl_y = y1 + dy / seg_len * 2.8
        ctx.move_to(jx0, jy0)
        ctx.curve_to(j_ctrl_x, j_ctrl_y, j_ctrl_x, j_ctrl_y, jx1, jy1)
        ctx.set_source_rgba(
            ink_rgba[0] * 0.7,
            ink_rgba[1] * 0.7,
            ink_rgba[2] * 0.7,
            min(1.0, ink_rgba[3] * 1.25),
        )
        ctx.set_line_width(max(2.4, w1 * 0.18))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    ctx.restore()


# ==============================================================================
# 3. DISTANT MISTY MOUNTAINS & SONG BROKEN BRIDGE (远山淡墨水晕与烟波断桥)
# ==============================================================================
def draw_distant_mountains(ctx: cairo.Context, ox: float = KEY_OX):
    """
    Renders 3 layers of soft, poetic mountain ridges in diluted pine-soot ink wash (松烟淡墨),
    fading smoothly into white negative mist (留白空灵), plus calligraphic moss dots and mist ribbons.
    """
    rng = np.random.default_rng(2026)

    layers = [
        (225.0, 75.0, 360.0, (0.40, 0.39, 0.44, 0.17), 185.0),   # Far distant ethereal peak
        (305.0, 95.0, 280.0, (0.30, 0.29, 0.35, 0.27), 205.0),   # Mid mountain ridge
        (405.0, 110.0, 220.0, (0.21, 0.20, 0.24, 0.36), 225.0),  # Near crags with moss dots
    ]

    for base_y, amp, period, ink, mist_h in layers:
        ctx.save()
        ctx.new_path()
        ctx.move_to(ox - 400, H * 0.68)
        ctx.line_to(ox - 400, base_y)

        x_pts = np.linspace(-400, W + 400, 160)
        for lx in x_pts:
            s1 = math.sin(lx / period + 0.5)
            s2 = 0.45 * math.sin(lx / (period * 0.48) + 1.2)
            s3 = 0.22 * math.cos(lx / (period * 0.22) - 0.8)
            y = base_y + amp * (s1 + s2 + s3)
            ctx.line_to(ox + lx, y)

        ctx.line_to(ox + W + 400, H * 0.68)
        ctx.close_path()

        grad = cairo.LinearGradient(0, base_y - amp, 0, base_y + mist_h)
        grad.add_color_stop_rgba(0.0, ink[0], ink[1], ink[2], ink[3])
        grad.add_color_stop_rgba(0.45, ink[0], ink[1], ink[2], ink[3] * 0.72)
        grad.add_color_stop_rgba(1.0, ink[0], ink[1], ink[2], 0.0)
        ctx.set_source(grad)
        ctx.fill()
        ctx.restore()

    # Small calligraphic moss dots (淡墨苔点) on the nearer mountain ridge
    ctx.save()
    for _ in range(58):
        lx = rng.uniform(180.0, 1750.0)
        my = 345.0 + 70.0 * math.sin(lx / 220.0) + rng.uniform(-14.0, 14.0)
        ctx.arc(ox + lx, my, rng.uniform(1.8, 3.6), 0, math.tau)
        ctx.set_source_rgba(0.18, 0.17, 0.20, rng.uniform(0.18, 0.38))
        ctx.fill()
    ctx.restore()

    # Distant misty broken stone arch bridge (烟波断桥) emerging from mid-ground mist
    draw_misty_broken_bridge(ctx, ox + 690.0, 430.0, scale=0.64, alpha_mul=0.52)

    # Flowing mist ribbons (横向游云飞白)
    for cloud_y, cloud_h, cloud_a in [
        (275.0, 48.0, 0.18),
        (365.0, 56.0, 0.22),
        (465.0, 72.0, 0.30),
    ]:
        ctx.save()
        c_grad = cairo.LinearGradient(0, cloud_y - cloud_h * 0.5, 0, cloud_y + cloud_h * 0.5)
        c_grad.add_color_stop_rgba(0.0, 0.96, 0.94, 0.88, 0.0)
        c_grad.add_color_stop_rgba(0.5, 0.97, 0.95, 0.90, cloud_a)
        c_grad.add_color_stop_rgba(1.0, 0.96, 0.94, 0.88, 0.0)
        ctx.set_source(c_grad)
        ctx.rectangle(ox - 200, cloud_y - cloud_h * 0.5, W + 400, cloud_h)
        ctx.fill()
        ctx.restore()


def draw_misty_broken_bridge(
    ctx: cairo.Context, start_x: float, start_y: float, scale: float = 1.0, alpha_mul: float = 0.8
):
    """Draws a poetic Song-dynasty broken stone arch bridge (淡墨断桥) veiled in river mist."""
    ctx.save()
    ctx.translate(start_x, start_y)
    ctx.scale(scale, scale)

    # Soft arch shadow wash
    pat_arch = cairo.RadialGradient(145, 78, 4, 145, 78, 62)
    pat_arch.add_color_stop_rgba(0.0, 0.20, 0.19, 0.22, 0.38 * alpha_mul)
    pat_arch.add_color_stop_rgba(1.0, 0.28, 0.27, 0.30, 0.0)
    ctx.set_source(pat_arch)
    ctx.arc(145, 78, 56, math.pi, 0)
    ctx.fill()

    # Left rising stone bridge deck & arch
    ctx.set_source_rgba(0.20, 0.19, 0.22, 0.65 * alpha_mul)
    ctx.set_line_width(2.2)
    ctx.move_to(0, 88)
    ctx.curve_to(55, 58, 115, 30, 178, 18)
    ctx.stroke()

    ctx.set_line_width(1.7)
    ctx.move_to(28, 96)
    ctx.curve_to(75, 65, 120, 42, 174, 34)
    ctx.stroke()

    # Balustrade posts on left span
    ctx.set_line_width(1.3)
    for bx in (38, 82, 126, 168):
        by = 88 - (bx / 178.0) * 70
        ctx.move_to(bx, by)
        ctx.line_to(bx, by - 13)
        ctx.stroke()
        ctx.arc(bx, by - 14.5, 2.0, 0, math.tau)
        ctx.fill()
    ctx.move_to(26, 76)
    ctx.curve_to(72, 48, 120, 22, 174, 6)
    ctx.stroke()

    # Right broken span across the gap
    gap_x = 224
    ctx.set_line_width(2.0)
    ctx.move_to(gap_x, 26)
    ctx.curve_to(285, 52, 348, 74, 410, 98)
    ctx.stroke()

    ctx.set_line_width(1.5)
    ctx.move_to(gap_x, 40)
    ctx.curve_to(280, 62, 340, 82, 392, 104)
    ctx.stroke()

    ctx.restore()


# ==============================================================================
# 4. BAMBOO GROVE & HERO FLEXING STALK (竹林与借力弹跃竹梢 - v3 Base)
# ==============================================================================
def draw_bamboo_grove(ctx: cairo.Context, ox: float = KEY_OX, bend: float = 0.0, vib: float = 0.0):
    """
    Renders the authentic calligraphic bamboo scene:
      - Top-left hanging bamboo sprays framing the upper canvas
      - Background slender pale bamboo culms
      - HERO Flexing Bamboo Stalk in lower-left:
        Bends with weight (`bend`) and vibrates with underdamped oscillation (`vib`)!
    """
    # 1. Top-left hanging bamboo branches (文人画垂竹折枝)
    hanging_joints = [
        ((ox + 25, 12), (ox + 105, 62)),
        ((ox + 105, 62), (ox + 188, 108)),
        ((ox + 188, 108), (ox + 268, 146)),
        ((ox + 268, 146), (ox + 338, 172)),
    ]
    for i, (p0, p1) in enumerate(hanging_joints):
        w = max(3.5, 8.5 - i * 1.4)
        draw_bamboo_culm_segment(ctx, p0, p1, w, w * 0.9, (0.15, 0.15, 0.18, 0.84))

    leaf_clusters = [
        (ox + 105, 62, [0.42, 0.78, 1.18, 1.45], [44, 58, 50, 36], 7.0, (0.12, 0.12, 0.15, 0.88)),
        (ox + 188, 108, [0.48, 0.85, 1.28], [48, 64, 54], 7.5, (0.10, 0.10, 0.12, 0.92)),
        (ox + 268, 146, [0.58, 0.95, 1.35], [50, 66, 55], 7.8, (0.08, 0.08, 0.10, 0.95)),
        (ox + 338, 172, [0.72, 1.08, 1.42], [40, 54, 44], 7.0, (0.14, 0.14, 0.16, 0.85)),
        # Lighter background leaf sprays
        (ox + 148, 84, [-0.22, 0.18, 0.58], [38, 44, 36], 5.5, (0.35, 0.35, 0.38, 0.50)),
        (ox + 230, 125, [0.12, 0.50, 0.90], [40, 48, 42], 5.8, (0.32, 0.32, 0.35, 0.55)),
    ]
    for cx, cy, angles, lengths, w_mid, col in leaf_clusters:
        for ang, lg in zip(angles, lengths):
            draw_brush_leaf(ctx, cx, cy, lg, ang, w_mid, col, bend=0.14)

    # 2. Distant background bamboo stalks (淡墨虚竹)
    bg_joints = [
        ((ox + 158, 1080), (ox + 153, 880)),
        ((ox + 153, 880), (ox + 148, 680)),
        ((ox + 148, 680), (ox + 143, 480)),
        ((ox + 143, 480), (ox + 136, 280)),
    ]
    for p0, p1 in bg_joints:
        draw_bamboo_culm_segment(ctx, p0, p1, 10.0, 9.2, (0.40, 0.38, 0.44, 0.42))
    for py in [880, 680, 480]:
        for ang in [-0.85, -0.45, 0.35, 0.75]:
            draw_brush_leaf(ctx, ox + 148, py, 52, ang, 6.5, (0.38, 0.36, 0.42, 0.40), bend=0.1)

    # Secondary pale bamboo stalk on far left
    bg_joints_2 = [
        ((ox + 82, 1080), (ox + 86, 840)),
        ((ox + 86, 840), (ox + 92, 610)),
        ((ox + 92, 610), (ox + 98, 390)),
    ]
    for p0, p1 in bg_joints_2:
        draw_bamboo_culm_segment(ctx, p0, p1, 7.2, 6.5, (0.48, 0.46, 0.52, 0.30))
    for py in [840, 610]:
        for ang in [-0.65, 0.25, 0.68]:
            draw_brush_leaf(ctx, ox + 88, py, 44, ang, 5.2, (0.45, 0.44, 0.50, 0.32), bend=0.12)

    # 3. HERO FLEXING BAMBOO STALK (借力弹跃竹梢)
    b_dy1 = bend * 18.0
    b_dy2 = bend * 48.0
    b_dy3 = bend * 88.0 - vib * 15.0
    b_dx4 = bend * 28.0 + vib * 22.0
    b_dy4 = bend * 130.0 - vib * 25.0

    hero_joints = [
        ((ox + 265, 1080), (ox + 350, 920), 22.0, 19.5),
        ((ox + 350, 920), (ox + 440, 785 + b_dy1), 19.5, 17.0),
        ((ox + 440, 785 + b_dy1), (ox + 525, 715 + b_dy2), 17.0, 14.5),
        ((ox + 525, 715 + b_dy2), (ox + 590, 688 + b_dy3), 14.5, 12.0),
        ((ox + 590, 688 + b_dy3), (ox + 700 + b_dx4 * 0.7, 672 + b_dy4 * 0.8), 12.0, 9.5),
        ((ox + 700 + b_dx4 * 0.7, 672 + b_dy4 * 0.8), (ox + 805 + b_dx4, 675 + b_dy4), 9.5, 7.0),
    ]
    for p0, p1, w0, w1 in hero_joints:
        draw_bamboo_culm_segment(ctx, p0, p1, w0, w1, (0.10, 0.10, 0.12, 0.95))

    hero_leaf_groups = [
        (ox + 350, 920, [-1.25, -0.80, -0.40], [68, 85, 72], 9.5, (0.10, 0.10, 0.12, 0.95)),
        (ox + 440, 785 + b_dy1, [-1.38, -0.95, -0.50, -0.18], [75, 95, 88, 70], 10.5, (0.08, 0.08, 0.10, 0.98)),
        (ox + 525, 715 + b_dy2, [-1.48, -1.08, -0.68], [70, 90, 80], 9.5, (0.12, 0.12, 0.14, 0.95)),
        (ox + 700 + b_dx4 * 0.7, 672 + b_dy4 * 0.8, [0.15 + bend * 0.25, 0.48 + bend * 0.25, 0.88 + bend * 0.25], [65, 82, 70], 8.5, (0.10, 0.10, 0.12, 0.95)),
        (ox + 805 + b_dx4, 675 + b_dy4, [0.05 + bend * 0.35, 0.40 + bend * 0.35, 0.82 + bend * 0.35, 1.22 + bend * 0.35], [58, 75, 68, 52], 8.0, (0.12, 0.12, 0.14, 0.92)),
    ]
    for lx, ly, angs, lens, wm, col in hero_leaf_groups:
        for a, l in zip(angs, lens):
            draw_brush_leaf(ctx, lx, ly, l, a, wm, col, bend=0.18 + bend * 0.15)

    # Elastic rebound shockwave leaves fluttering off the flexing joint
    flutter_leaves = [
        (ox + 650 + b_dx4 * 0.5, 745 + b_dy4 * 0.5, 1.85, 52, 7.0, (0.18, 0.18, 0.20, 0.88), 0.25),
        (ox + 690 + b_dx4 * 0.6, 775 + b_dy4 * 0.6, 2.15, 46, 6.5, (0.22, 0.22, 0.25, 0.82), 0.28),
        (ox + 555 + b_dx4 * 0.3, 755 + b_dy4 * 0.3, -2.10, 48, 6.8, (0.20, 0.20, 0.22, 0.85), -0.22),
    ]
    for fx, fy, fa, fl, fwm, fcol, fb in flutter_leaves:
        draw_brush_leaf(ctx, fx, fy, fl, fa, fwm, fcol, bend=fb)


def draw_bamboo_elements(ctx: cairo.Context, ox: float = KEY_OX):
    """Renders bamboo grove at default unbent state."""
    draw_bamboo_grove(ctx, ox=ox, bend=0.0, vib=0.0)


# ==============================================================================
# 5. LOTUS POND WITH MUD-GOLD VEINS, RIPPLES, BLOOMING LOTUS & LEAPING FISH
# ==============================================================================
def draw_ink_ripples(ctx: cairo.Context, cx: float, cy: float, max_r: float = 195.0, alpha_gain: float = 1.0):
    """
    Renders concentric sumi-ink & mineral-indigo water ripples (水墨同心涟漪)
    expanding across the pond surface beneath the stepping slime and lotus pads.
    """
    ctx.save()

    # Central wet ink touch pool
    pat_pool = cairo.RadialGradient(cx, cy, 2.0, cx, cy, max_r * 0.24)
    pat_pool.add_color_stop_rgba(0.0, 0.14, 0.22, 0.30, 0.36 * alpha_gain)
    pat_pool.add_color_stop_rgba(1.0, 0.20, 0.26, 0.34, 0.0)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(1.0, 0.30)
    ctx.set_source(pat_pool)
    ctx.arc(0, 0, max_r * 0.24, 0, math.tau)
    ctx.fill()
    ctx.restore()

    rings = [
        (0.28, 0.36 * alpha_gain, 3.0, [28.0, 6.0, 42.0, 8.0]),
        (0.50, 0.28 * alpha_gain, 2.4, [38.0, 9.0, 26.0, 10.0]),
        (0.74, 0.20 * alpha_gain, 1.9, [48.0, 12.0, 32.0, 14.0]),
        (1.00, 0.13 * alpha_gain, 1.5, [60.0, 16.0, 40.0, 18.0]),
        (1.28, 0.07 * alpha_gain, 1.2, []),
    ]
    for r_scale, alpha_r, lw, dash in rings:
        rx = max_r * r_scale
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(1.0, 0.28)
        if dash:
            ctx.set_dash(dash, r_scale * 15.0)
        ctx.arc(0, 0, rx, 0, math.tau)
        ctx.restore()
        ctx.set_source_rgba(0.18, 0.24, 0.32, alpha_r)
        ctx.set_line_width(lw)
        ctx.stroke()

    ctx.restore()


def draw_splashed_lotus_pad(
    ctx: cairo.Context,
    pad_cx: float,
    pad_cy: float,
    scale_x: float = 1.28,
    scale_y: float = 0.62,
    base_rad: float = 155.0,
    seed: int = 1,
    alpha_gain: float = 1.0,
    gold_veins: bool = True,
):
    """
    Renders v3's signature organic Splashed-Ink Lotus Pad (大写意泼墨荷叶)
    enhanced with luminous mud-gold leaf veins (泥金叶脉) & mineral indigo wash!
    """
    ctx.save()
    ctx.new_path()
    n_pts_pad = 48
    pts_pad = []
    for i in range(n_pts_pad):
        ang = (i / n_pts_pad) * math.tau
        notch = 0.46 if (0.25 * math.pi < ang < 0.55 * math.pi) else 1.0
        rad = (
            base_rad
            + 28.0 * (base_rad / 155.0) * math.sin(3 * ang + 0.4 + seed)
            + 16.0 * (base_rad / 155.0) * math.cos(5 * ang - 0.6)
        ) * notch
        px = pad_cx + rad * math.cos(ang) * scale_x
        py = pad_cy + rad * math.sin(ang) * scale_y
        pts_pad.append((px, py))

    ctx.move_to(pts_pad[0][0], pts_pad[0][1])
    for i in range(n_pts_pad):
        p0 = pts_pad[i]
        p1 = pts_pad[(i + 1) % n_pts_pad]
        mx = (p0[0] + p1[0]) * 0.5
        my = (p0[1] + p1[1]) * 0.5
        ctx.curve_to(p0[0], p0[1], p0[0], p0[1], mx, my)
    ctx.close_path()

    # Wet diffusion ink gradient (Center deep pitch ink -> mineral indigo -> rim diluted wash)
    pad_grad = cairo.RadialGradient(
        pad_cx - 22 * (base_rad / 155.0),
        pad_cy - 10 * (base_rad / 155.0),
        16 * (base_rad / 155.0),
        pad_cx,
        pad_cy,
        base_rad * 1.24,
    )
    pad_grad.add_color_stop_rgba(0.00, 0.07, 0.08, 0.10, 0.96 * alpha_gain)  # Deep sumi center
    pad_grad.add_color_stop_rgba(0.42, 0.13, 0.22, 0.32, 0.88 * alpha_gain)  # 花青 Mineral indigo infusion
    pad_grad.add_color_stop_rgba(0.76, 0.22, 0.28, 0.36, 0.72 * alpha_gain)  # Pale wash
    pad_grad.add_color_stop_rgba(1.00, 0.42, 0.46, 0.50, 0.22 * alpha_gain)  # Feathered edge
    ctx.set_source(pad_grad)
    ctx.fill_preserve()

    # Expressive calligraphic leaf edge contour (焦墨破边)
    ctx.set_source_rgba(0.08, 0.08, 0.10, 0.82 * alpha_gain)
    ctx.set_line_width(2.6)
    ctx.stroke()

    # Radiating leaf veins: Dark Sumi base + Mud-Gold (泥金叶脉) highlight!
    ctx.save()
    for vein_ang in np.linspace(0.15, math.tau - 0.25, 13):
        if 0.28 * math.pi < vein_ang < 0.52 * math.pi:
            continue
        vx1 = pad_cx + (base_rad * 0.94) * math.cos(vein_ang) * scale_x * 0.92
        vy1 = pad_cy + (base_rad * 0.94) * math.sin(vein_ang) * scale_y * 0.90
        c1x = pad_cx + (vx1 - pad_cx) * 0.45 + 9 * math.sin(vein_ang * 2)
        c1y = pad_cy + (vy1 - pad_cy) * 0.45
        c2x = pad_cx + (vx1 - pad_cx) * 0.78
        c2y = pad_cy + (vy1 - pad_cy) * 0.78

        # Dark ink under-vein
        ctx.new_path()
        ctx.move_to(pad_cx, pad_cy)
        ctx.curve_to(c1x, c1y, c2x, c2y, vx1, vy1)
        ctx.set_source_rgba(0.05, 0.06, 0.08, 0.55 * alpha_gain)
        ctx.set_line_width(2.2)
        ctx.stroke()

        # Luminous Mud-Gold vein (泥金勾脉)
        if gold_veins:
            ctx.new_path()
            ctx.move_to(pad_cx + 1.0, pad_cy - 0.5)
            ctx.curve_to(c1x + 1.0, c1y - 0.5, c2x, c2y, vx1, vy1)
            vg = cairo.LinearGradient(pad_cx, pad_cy, vx1, vy1)
            vg.add_color_stop_rgba(0.0, 0.92, 0.76, 0.28, 0.78 * alpha_gain)
            vg.add_color_stop_rgba(0.65, 0.85, 0.64, 0.22, 0.58 * alpha_gain)
            vg.add_color_stop_rgba(1.0, 0.78, 0.54, 0.18, 0.12 * alpha_gain)
            ctx.set_source(vg)
            ctx.set_line_width(1.35)
            ctx.stroke()

    # Lotus navel ring in mud-gold & cinnabar
    ctx.arc(pad_cx, pad_cy, 5.2 * (base_rad / 155.0), 0, math.tau)
    ctx.set_source_rgba(0.88, 0.70, 0.24, 0.85 * alpha_gain)
    ctx.fill()
    ctx.restore()
    ctx.restore()


def draw_blooming_ink_lotus(ctx: cairo.Context, flower_cx: float, flower_cy: float, scale: float = 1.0):
    """
    Renders v3's Blooming Lotus Flower (墨荷绽放 · 胭脂花瓣与金蕊) with iron-wire calligraphic outlines.
    """
    ctx.save()

    # Flower stem (荷梗带刺点)
    ctx.new_path()
    ctx.move_to(flower_cx - 15 * scale, flower_cy + 55 * scale)
    ctx.curve_to(
        flower_cx - 24 * scale,
        flower_cy + 100 * scale,
        flower_cx - 12 * scale,
        flower_cy + 180 * scale,
        flower_cx + 12 * scale,
        flower_cy + 290 * scale,
    )
    ctx.set_source_rgba(0.14, 0.14, 0.16, 0.88)
    ctx.set_line_width(6.0 * scale)
    ctx.stroke()

    for ty_off in [30, 80, 130, 190, 240]:
        ctx.arc(flower_cx - 18 * scale, flower_cy + ty_off * scale, 2.0 * scale, 0, math.tau)
        ctx.set_source_rgba(0.08, 0.08, 0.10, 0.95)
        ctx.fill()

    petals = [
        (-0.72, 1.15, (0.98, 0.96, 0.92, 0.95), (0.78, 0.24, 0.22, 0.88)),
        (-0.38, 1.30, (0.99, 0.97, 0.94, 0.98), (0.84, 0.26, 0.20, 0.92)),
        (-0.05, 1.42, (1.00, 0.98, 0.95, 0.98), (0.88, 0.28, 0.20, 0.94)),
        (0.28, 1.32, (0.99, 0.97, 0.94, 0.98), (0.84, 0.26, 0.20, 0.92)),
        (0.62, 1.18, (0.98, 0.96, 0.92, 0.95), (0.78, 0.24, 0.22, 0.88)),
        (-0.92, 0.95, (0.96, 0.94, 0.90, 0.92), (0.72, 0.22, 0.22, 0.82)),
        (0.82, 0.98, (0.96, 0.94, 0.90, 0.92), (0.72, 0.22, 0.22, 0.82)),
    ]

    for p_ang, p_s, c_base, c_tip in petals:
        ctx.save()
        ctx.translate(flower_cx, flower_cy)
        ctx.rotate(p_ang)

        p_len = 95.0 * p_s * scale
        p_w = 34.0 * p_s * scale

        ctx.new_path()
        ctx.move_to(0, 18 * scale)
        ctx.curve_to(-p_w * 0.85, -p_len * 0.35, -p_w * 0.70, -p_len * 0.78, 0, -p_len)
        ctx.curve_to(p_w * 0.70, -p_len * 0.78, p_w * 0.85, -p_len * 0.35, 0, 18 * scale)
        ctx.close_path()

        pg = cairo.LinearGradient(0, 18 * scale, 0, -p_len)
        pg.add_color_stop_rgba(0.00, *c_base)
        pg.add_color_stop_rgba(0.50, 0.96, 0.86, 0.84, 0.95)
        pg.add_color_stop_rgba(1.00, *c_tip)
        ctx.set_source(pg)
        ctx.fill_preserve()

        ctx.set_source_rgba(0.12, 0.10, 0.12, 0.85)
        ctx.set_line_width(2.2 * scale)
        ctx.stroke()
        ctx.restore()

    # Golden stamens & seedpod (金柘花蕊与莲蓬)
    ctx.arc(flower_cx, flower_cy + 5 * scale, 14.0 * scale, 0, math.tau)
    ctx.set_source_rgba(0.85, 0.65, 0.22, 0.95)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.16, 0.14, 0.12, 0.85)
    ctx.set_line_width(2.0 * scale)
    ctx.stroke()

    for s_i in range(16):
        sa = (s_i / 16.0) * math.tau
        sx_tip = flower_cx + 26.0 * scale * math.cos(sa)
        sy_tip = flower_cy + 5 * scale + 18.0 * scale * math.sin(sa)
        ctx.new_path()
        ctx.move_to(flower_cx, flower_cy + 5 * scale)
        ctx.line_to(sx_tip, sy_tip)
        ctx.set_source_rgba(0.92, 0.72, 0.18, 0.95)
        ctx.set_line_width(1.5 * scale)
        ctx.stroke()
        ctx.arc(sx_tip, sy_tip, 2.2 * scale, 0, math.tau)
        ctx.set_source_rgba(0.98, 0.84, 0.25, 1.0)
        ctx.fill()

    ctx.restore()


def draw_pink_lotus_bud(ctx: cairo.Context, bud_cx: float, bud_cy: float, stem_bot_y: float, scale: float = 1.0, tilt: float = -0.08):
    """Renders a delicate pink-white lotus bud (娇嫩粉白荷苞) on a slender thorny stem."""
    ctx.save()
    # Stem
    ctx.new_path()
    ctx.move_to(bud_cx, bud_cy + 20 * scale)
    ctx.curve_to(
        bud_cx - 10 * scale,
        (bud_cy + stem_bot_y) * 0.5,
        bud_cx + 6 * scale,
        stem_bot_y - 30 * scale,
        bud_cx + 10 * scale,
        stem_bot_y,
    )
    ctx.set_source_rgba(0.15, 0.16, 0.18, 0.84)
    ctx.set_line_width(4.2 * scale)
    ctx.stroke()

    for u in [0.25, 0.50, 0.75]:
        ty = bud_cy + 20 * scale + u * (stem_bot_y - bud_cy - 20 * scale)
        ctx.arc(bud_cx - 3 * scale, ty, 1.6 * scale, 0, math.tau)
        ctx.set_source_rgba(0.08, 0.08, 0.10, 0.92)
        ctx.fill()

    # Bud petals
    ctx.translate(bud_cx, bud_cy)
    ctx.rotate(tilt)
    ctx.scale(scale, scale)

    for side, p_w, p_h in [(-1, 22.0, 56.0), (1, 22.0, 56.0), (0, 18.0, 64.0)]:
        ctx.new_path()
        if side == 0:
            ctx.move_to(0, 22)
            ctx.curve_to(-p_w, 6, -p_w * 0.75, -p_h * 0.65, 0, -p_h)
            ctx.curve_to(p_w * 0.75, -p_h * 0.65, p_w, 6, 0, 22)
        else:
            ctx.move_to(0, 22)
            ctx.curve_to(side * p_w * 1.15, 8, side * p_w * 0.95, -p_h * 0.6, side * 4, -p_h * 0.92)
            ctx.curve_to(side * 4, -p_h * 0.4, side * 2, 8, 0, 22)
        ctx.close_path()

        pg = cairo.LinearGradient(0, 22, 0, -p_h)
        pg.add_color_stop_rgba(0.00, 0.99, 0.97, 0.93, 0.96)
        pg.add_color_stop_rgba(0.55, 0.97, 0.85, 0.83, 0.95)
        pg.add_color_stop_rgba(1.00, 0.85, 0.24, 0.22, 0.95)
        ctx.set_source(pg)
        ctx.fill_preserve()

        ctx.set_source_rgba(0.12, 0.10, 0.12, 0.82)
        ctx.set_line_width(1.8)
        ctx.stroke()

    # Sepal base
    ctx.arc(0, 22, 6.5, 0, math.pi)
    ctx.set_source_rgba(0.16, 0.22, 0.18, 0.88)
    ctx.fill()
    ctx.restore()


def draw_cinnabar_fish(ctx: cairo.Context, cx: float, cy: float, length: float = 158.0, angle: float = -0.42):
    """
    Renders a lively expressive Cinnabar Fish (朱砂写意游鱼) leaping out of the water:
      - One-stroke calligraphic mineral cinnabar body (#D63824 -> #EA6232) with mud-gold dorsal sheen
      - Flowing swallow-tail fins (燕尾双剪大尾鳍) with feibai dry-brush tips
      - Pitch-black ink eye with mud-gold ring (焦墨点睛 · 泥金眼圈)
      - Water & ink-wash splash arc beneath its tail!
    """
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(angle)

    L = length
    W_body = L * 0.24

    # 1. Flowing swallow-tail fins (燕尾双剪大尾鳍)
    tail_x, tail_y = -L * 0.42, 0.0
    ctx.save()
    ctx.translate(tail_x, tail_y)

    # Upper tail lobe
    ctx.new_path()
    ctx.move_to(0, 0)
    ctx.curve_to(-L * 0.26, -L * 0.28, -L * 0.45, -L * 0.22, -L * 0.56, -L * 0.35)
    ctx.curve_to(-L * 0.36, -L * 0.08, -L * 0.20, -L * 0.03, 0, 0)
    ctx.close_path()
    tg1 = cairo.LinearGradient(0, 0, -L * 0.56, -L * 0.35)
    tg1.add_color_stop_rgba(0.0, 0.82, 0.22, 0.15, 0.94)
    tg1.add_color_stop_rgba(0.7, 0.90, 0.36, 0.22, 0.78)
    tg1.add_color_stop_rgba(1.0, 0.94, 0.54, 0.28, 0.25)
    ctx.set_source(tg1)
    ctx.fill()

    # Lower tail lobe
    ctx.new_path()
    ctx.move_to(0, 0)
    ctx.curve_to(-L * 0.22, L * 0.16, -L * 0.38, L * 0.22, -L * 0.48, L * 0.30)
    ctx.curve_to(-L * 0.30, L * 0.06, -L * 0.16, L * 0.02, 0, 0)
    ctx.close_path()
    tg2 = cairo.LinearGradient(0, 0, -L * 0.48, L * 0.30)
    tg2.add_color_stop_rgba(0.0, 0.84, 0.24, 0.16, 0.92)
    tg2.add_color_stop_rgba(0.7, 0.92, 0.42, 0.24, 0.72)
    tg2.add_color_stop_rgba(1.0, 0.94, 0.56, 0.30, 0.22)
    ctx.set_source(tg2)
    ctx.fill()
    ctx.restore()

    # 2. Pectoral & pelvic fins (写意胸鳍与腹鳍)
    for sign in (-1, 1):
        ctx.save()
        ctx.translate(L * 0.16, sign * W_body * 0.40)
        ctx.rotate(sign * 0.58)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-L * 0.18, sign * L * 0.22, -L * 0.34, sign * L * 0.15, -L * 0.28, sign * L * 0.02)
        ctx.close_path()
        ctx.set_source_rgba(0.86, 0.28, 0.18, 0.86)
        ctx.fill()
        ctx.restore()

    # 3. Expressive S-curved fish body (一笔朱砂鱼身)
    ctx.new_path()
    ctx.move_to(L * 0.48, 0)
    ctx.curve_to(L * 0.26, -W_body * 1.15, -L * 0.14, -W_body * 0.92, -L * 0.44, -W_body * 0.12)
    ctx.curve_to(-L * 0.20, W_body * 0.65, L * 0.16, W_body * 0.85, L * 0.48, 0)
    ctx.close_path()

    pat_fish = cairo.LinearGradient(L * 0.2, -W_body * 1.1, -L * 0.2, W_body * 0.85)
    pat_fish.add_color_stop_rgba(0.00, 0.72, 0.15, 0.10, 0.98)  # Deep vermilion spine
    pat_fish.add_color_stop_rgba(0.45, 0.88, 0.26, 0.16, 0.98)  # Bright cinnabar
    pat_fish.add_color_stop_rgba(0.82, 0.94, 0.44, 0.24, 0.96)  # Rouge-orange belly
    pat_fish.add_color_stop_rgba(1.00, 0.96, 0.68, 0.32, 0.94)  # Mud-gold belly rim
    ctx.set_source(pat_fish)
    ctx.fill_preserve()

    # Calligraphic dorsal brush accent & mud-gold spine line
    ctx.set_source_rgba(0.42, 0.08, 0.06, 0.82)
    ctx.set_line_width(2.0)
    ctx.stroke()

    ctx.new_path()
    ctx.move_to(L * 0.36, -W_body * 0.28)
    ctx.curve_to(L * 0.10, -W_body * 0.55, -L * 0.15, -W_body * 0.42, -L * 0.35, -W_body * 0.10)
    ctx.set_source_rgba(0.95, 0.78, 0.30, 0.72)
    ctx.set_line_width(1.8)
    ctx.stroke()

    # 4. Pitch-black ink eye with mud-gold ring (焦墨点睛)
    eye_x, eye_y = L * 0.35, -W_body * 0.22
    ctx.arc(eye_x, eye_y, 5.2, 0, math.tau)
    ctx.set_source_rgba(0.95, 0.80, 0.32, 0.95)
    ctx.fill()
    ctx.arc(eye_x, eye_y, 3.4, 0, math.tau)
    ctx.set_source_rgba(0.06, 0.06, 0.08, 0.98)
    ctx.fill()

    ctx.restore()


def draw_leap_and_lotus(ctx: cairo.Context, ox: float = KEY_OX, state: dict = None):
    """
    Renders the complete center-right narrative composition:
      1. Sweeping S-curve calligraphic motion trail from slime leap to upper-right seal
      2. Stepping lotus pads with mud-gold veins & concentric water ripples
      3. Blooming pink-white ink lotus flower & delicate lotus bud
      4. Expressive Cinnabar Fish leaping out of the water + Companion 4-point Star ✦
      5. Splashing mineral indigo (花青), sumi-ink, and cinnabar droplets across the scroll!
    """
    if state is None:
        state = {}

    # 1. Sweeping S-Curve Ink Motion Trail (大写意行笔飞白弧线)
    ctx.save()
    ctx.new_path()
    ctx.move_to(ox + 570, 700)
    ctx.curve_to(ox + 700, 520, ox + 890, 430, ox + 1090, 425)
    ctx.curve_to(ox + 1255, 420, ox + 1370, 355, ox + 1450, 280)
    ctx.set_source_rgba(0.22, 0.24, 0.30, 0.16)
    ctx.set_line_width(32.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()

    trail_layers = [
        (-8.0, 6.8, 0.38, (0.16, 0.24, 0.34)),  # Mineral indigo outer ribbon
        (0.0, 11.5, 0.62, (0.10, 0.10, 0.12)),   # Core sumi-ink dry brush
        (7.0, 5.8, 0.35, (0.20, 0.18, 0.22)),
    ]
    for off_y, lw, alpha, col in trail_layers:
        ctx.new_path()
        ctx.move_to(ox + 570, 700 + off_y)
        ctx.curve_to(ox + 700, 520 + off_y, ox + 890, 430 + off_y, ox + 1090, 425 + off_y)
        ctx.curve_to(ox + 1255, 420 + off_y, ox + 1370, 355 + off_y, ox + 1445, 280 + off_y)
        ctx.set_source_rgba(col[0], col[1], col[2], alpha)
        ctx.set_line_width(lw)
        ctx.stroke()

    # Cinnabar & mud-gold spark energy vein within the ink arc (朱砂泥金气韵线)
    ctx.new_path()
    ctx.move_to(ox + 610, 650)
    ctx.curve_to(ox + 735, 505, ox + 915, 428, ox + 1110, 422)
    ctx.curve_to(ox + 1260, 415, ox + 1380, 348, ox + 1440, 285)
    ctx.set_source_rgba(0.80, 0.24, 0.16, 0.58)
    ctx.set_line_width(4.5)
    ctx.stroke()
    ctx.restore()

    # 2. Concentric ink water ripples across the lotus pond (层层水墨涟漪)
    draw_ink_ripples(ctx, ox + 635, 725, max_r=180.0, alpha_gain=1.05)   # Under slime's bamboo/water touch
    draw_ink_ripples(ctx, ox + 945, 720, max_r=175.0, alpha_gain=0.98)   # Under leaping cinnabar fish
    draw_ink_ripples(ctx, ox + 1165, 835, max_r=220.0, alpha_gain=1.0)   # Under hero lotus pad

    # 3. Splashed-Ink Lotus Pads with Mud-Gold Veins (带泥金叶脉的泼墨大荷叶)
    # Distant smaller lotus pad on left-mid pond
    draw_splashed_lotus_pad(
        ctx, ox + 815.0, 765.0, scale_x=1.18, scale_y=0.52, base_rad=88.0, seed=3, alpha_gain=0.76, gold_veins=True
    )
    # Hero large splashed-ink lotus pad in center-right
    draw_splashed_lotus_pad(
        ctx, ox + 1155.0, 795.0, scale_x=1.28, scale_y=0.62, base_rad=158.0, seed=1, alpha_gain=1.0, gold_veins=True
    )
    # Foreground right lotus pad framing bottom-right
    draw_splashed_lotus_pad(
        ctx, ox + 1530.0, 885.0, scale_x=1.32, scale_y=0.58, base_rad=132.0, seed=7, alpha_gain=0.88, gold_veins=True
    )

    # 4. Blooming Pink-White Ink Lotus & Delicate Lotus Buds (粉白盛放墨荷与娇嫩荷苞)
    draw_blooming_ink_lotus(ctx, ox + 1320.0, 615.0, scale=1.0)
    draw_pink_lotus_bud(ctx, ox + 1455.0, 660.0, stem_bot_y=875.0, scale=0.92, tilt=0.14)

    # 5. Lively Cinnabar Fish Leaping Out of Water + Mud-Gold & Cinnabar 4-Point Star ✦
    fish_x = state.get("fish_x", ox + 985.0)
    fish_y = state.get("fish_y", 615.0)
    fish_ang = state.get("fish_ang", -0.46)
    draw_cinnabar_fish(ctx, fish_x, fish_y, length=168.0, angle=fish_ang)

    # Water-break droplets & fine ink arc where the fish leaps from the pond
    ctx.save()
    ctx.new_path()
    ctx.move_to(fish_x - 88, fish_y + 78)
    ctx.curve_to(fish_x - 58, fish_y + 38, fish_x - 32, fish_y + 20, fish_x - 10, fish_y + 8)
    ctx.set_source_rgba(0.18, 0.34, 0.48, 0.48)
    ctx.set_line_width(3.4)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()

    # 4-Point Star-Spark ✦ (泥金勾边 + 朱砂点心) riding above the fish's back / leading the way
    star_x = state.get("star_x", fish_x + 18.0)
    star_y = state.get("star_y", fish_y - 96.0)
    star_r = state.get("star_r", 34.0)
    star_rot = state.get("star_rot", 0.14)
    draw_star(ctx, star_x, star_y, star_r, rot=star_rot)

    # 6. Wet Sumi-Ink, Mineral Indigo (花青) & Cinnabar (朱砂) Splash Droplets (飞溅花青与朱砂墨点)
    rng_splash = np.random.default_rng(777)
    splash_points = [
        # (cx, cy, r_range, color_rgba, count)
        (ox + 660, 635, (2.2, 7.5), (0.10, 0.10, 0.12, 0.94), 16),   # Sumi ink near bamboo rebound
        (ox + 760, 575, (2.4, 8.2), (0.15, 0.36, 0.54, 0.90), 18),   # 花青 Mineral Indigo splash
        (ox + 890, 530, (2.5, 8.8), (0.80, 0.22, 0.16, 0.92), 20),   # 朱砂 Cinnabar splash around fish
        (ox + 1020, 505, (2.2, 7.8), (0.16, 0.38, 0.56, 0.88), 16),  # 花青 Indigo droplets around fish & star
        (ox + 1120, 485, (2.2, 7.5), (0.82, 0.24, 0.16, 0.92), 16),  # 朱砂 Cinnabar droplets
        (ox + 1240, 450, (2.0, 6.8), (0.14, 0.14, 0.18, 0.86), 14),  # Sumi ink trail droplets
        (ox + 1365, 355, (2.0, 6.2), (0.76, 0.20, 0.16, 0.86), 14),  # Upper trail cinnabar droplets
    ]

    for sx, sy, (r_min, r_max), col, n_dots in splash_points:
        for _ in range(n_dots):
            dx = rng_splash.normal(0, 52.0)
            dy = rng_splash.normal(0, 36.0)
            r = rng_splash.uniform(r_min, r_max)

            # Raw Xuan paper wet bleed halo around larger droplets (水晕圈)
            if r > 4.2:
                ctx.arc(sx + dx, sy + dy, r * 1.75, 0, math.tau)
                ctx.set_source_rgba(col[0], col[1], col[2], col[3] * 0.22)
                ctx.fill()

            ctx.arc(sx + dx, sy + dy, r, 0, math.tau)
            ctx.set_source_rgba(*col)
            ctx.fill()


# ==============================================================================
# 6. UPPER-RIGHT CINNABAR SEAL ARCH & SHOCKWAVE (朱文印章「双子奇观」与同心波纹)
# ==============================================================================
def draw_cinnabar_seal_stamp(
    ctx: cairo.Context, cx: float = KEY_OX + 1490.0, cy: float = 255.0, size: float = 142.0
):
    """
    Renders v3's iconic suspended square cinnabar seal arch (朱砂方印拱门「双子奇观」):
      - Cinnabar paste color (#B82618) with stone texture & chiseled border imperfections
      - Seal text 「双子奇观」 in classical 2x2 seal grid with inner dividing border
      - Concentric cinnabar impact shockwave rings radiating outward!
    """
    half_s = size * 0.5
    rng_seal = np.random.default_rng(999)

    # 1. Stamping Impact Shockwave Rings (同心朱砂声波纹)
    shock_radii = [size * 0.85, size * 1.35, size * 1.95, size * 2.65]
    shock_alphas = [0.42, 0.28, 0.18, 0.08]

    for r_ring, a_ring in zip(shock_radii, shock_alphas):
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(1.05, 0.95)
        ctx.arc(0, 0, r_ring, 0, math.tau)

        ring_g = cairo.RadialGradient(0, 0, r_ring * 0.85, 0, 0, r_ring * 1.15)
        ring_g.add_color_stop_rgba(0.00, 0.78, 0.22, 0.16, 0.0)
        ring_g.add_color_stop_rgba(0.50, 0.78, 0.22, 0.16, a_ring)
        ring_g.add_color_stop_rgba(1.00, 0.78, 0.22, 0.16, 0.0)
        ctx.set_source(ring_g)
        ctx.set_line_width(12.0)
        ctx.stroke()
        ctx.restore()

    # Radial calligraphic impact sparks
    for spark_i in range(16):
        s_ang = (spark_i / 16.0) * math.tau + rng_seal.uniform(-0.1, 0.1)
        r0 = half_s * 1.15
        r1 = r0 + rng_seal.uniform(22.0, 65.0)
        ctx.new_path()
        ctx.move_to(cx + r0 * math.cos(s_ang), cy + r0 * math.sin(s_ang))
        ctx.line_to(cx + r1 * math.cos(s_ang), cy + r1 * math.sin(s_ang))
        ctx.set_source_rgba(0.76, 0.20, 0.15, rng_seal.uniform(0.35, 0.75))
        ctx.set_line_width(rng_seal.uniform(1.8, 3.2))
        ctx.stroke()

    # 2. Antique Seal Stone Impression (金石斑驳边缘与渗油朱泥)
    ctx.save()
    x0, y0 = cx - half_s, cy - half_s
    x1, y1 = cx + half_s, cy + half_s

    n_edge = 36
    pts = []
    for i in range(n_edge):
        t = (i / n_edge) * 4.0
        side = int(t)
        u = t - side
        jit_x = rng_seal.uniform(-1.8, 1.8)
        jit_y = rng_seal.uniform(-1.8, 1.8)
        if side == 0:
            px, py = x0 + u * size, y0
        elif side == 1:
            px, py = x1, y0 + u * size
        elif side == 2:
            px, py = x1 - u * size, y1
        else:
            px, py = x0, y1 - u * size
        pts.append((px + jit_x, py + jit_y))

    ctx.new_path()
    ctx.move_to(pts[0][0], pts[0][1])
    for px, py in pts[1:]:
        ctx.line_to(px, py)
    ctx.close_path()

    seal_grad = cairo.RadialGradient(cx - 15, cy - 15, 10, cx, cy, size * 0.7)
    seal_grad.add_color_stop_rgba(0.00, 0.84, 0.22, 0.16, 0.98)
    seal_grad.add_color_stop_rgba(0.70, 0.72, 0.16, 0.12, 0.96)
    seal_grad.add_color_stop_rgba(1.00, 0.62, 0.12, 0.10, 0.98)
    ctx.set_source(seal_grad)
    ctx.fill_preserve()

    ctx.set_source_rgba(0.52, 0.10, 0.08, 0.92)
    ctx.set_line_width(2.5)
    ctx.stroke()

    # Inner seal grid divider line (界格田字框)
    ctx.new_path()
    ctx.move_to(cx, y0 + 6)
    ctx.line_to(cx, y1 - 6)
    ctx.move_to(x0 + 6, cy)
    ctx.line_to(x1 - 6, cy)
    ctx.set_source_rgba(0.55, 0.12, 0.10, 0.75)
    ctx.set_line_width(2.0)
    ctx.stroke()
    ctx.restore()

    # 3. Seal Carved Characters 「双子奇观」 (白文留白篆刻质感)
    char_cells = [
        ("双", cx + half_s * 0.48, cy - half_s * 0.48),
        ("子", cx + half_s * 0.48, cy + half_s * 0.52),
        ("奇", cx - half_s * 0.48, cy - half_s * 0.48),
        ("观", cx - half_s * 0.48, cy + half_s * 0.52),
    ]

    f_seal = get_pil_font(int(size * 0.36), FONT_CJK_MED)
    stamp_img = Image.new("RGBA", (int(size + 20), int(size + 20)), (0, 0, 0, 0))
    d_stamp = ImageDraw.Draw(stamp_img)
    ox_s, oy_s = 10, 10

    for ch, gx, gy in char_cells:
        lx = (gx - (cx - half_s)) + ox_s
        ly = (gy - (cy - half_s)) + oy_s
        bbox = d_stamp.textbbox((0, 0), ch, font=f_seal)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        d_stamp.text(
            (lx - bw * 0.5, ly - bh * 0.55),
            ch,
            font=f_seal,
            fill=(248, 242, 230, 245),
        )

    stamp_arr = np.array(stamp_img, dtype=np.float32)
    pore_noise = rng_seal.random((stamp_arr.shape[0], stamp_arr.shape[1]))
    char_mask = stamp_arr[..., 3] > 100
    erode = char_mask & (pore_noise < 0.12)
    stamp_arr[erode, 3] *= 0.25
    stamp_img_weathered = Image.fromarray(stamp_arr.astype(np.uint8), mode="RGBA")

    stamp_surf = pil_to_cairo(stamp_img_weathered)
    ctx.save()
    ctx.set_source_surface(stamp_surf, x0 - 10, y0 - 10)
    ctx.paint()
    ctx.restore()


# ==============================================================================
# 7. STANDARD API: draw_star & draw_slime
# ==============================================================================
def draw_star(ctx: cairo.Context, cx: float, cy: float, r: float, *, rot: float = 0.0, t: float = 0.0, **style_kw):
    """
    Renders the 4-point concave Star-Spark (✦) in World 07 Ink-Wash & Cinnabar style:
      - Mud-gold outline (泥金勾边 #E5B84B) + Cinnabar core wash (朱砂点心 #C83824)
      - Warm starlight aura + scattered fine gold-leaf flecks (细碎金粉)
    """
    ctx.save()

    # 1. Soft radiant gold-cinnabar aura
    aura_g = cairo.RadialGradient(cx, cy, r * 0.10, cx, cy, r * 2.1)
    aura_g.add_color_stop_rgba(0.00, 0.98, 0.84, 0.30, 0.68)
    aura_g.add_color_stop_rgba(0.50, 0.88, 0.36, 0.20, 0.32)
    aura_g.add_color_stop_rgba(1.00, 0.85, 0.30, 0.18, 0.00)
    ctx.set_source(aura_g)
    ctx.arc(cx, cy, r * 2.1, 0, math.tau)
    ctx.fill()

    # 2. Concave 4-point star body: Cinnabar core -> Mud-gold tips
    draw_four_point_star(ctx, cx, cy, r, r * 0.27, rot=rot)
    sg = cairo.RadialGradient(cx, cy, r * 0.04, cx, cy, r * 0.95)
    sg.add_color_stop_rgba(0.00, 0.92, 0.28, 0.18, 0.98)  # 鲜朱砂点心
    sg.add_color_stop_rgba(0.48, 0.84, 0.24, 0.16, 0.98)  # 沉朱砂
    sg.add_color_stop_rgba(0.82, 0.92, 0.72, 0.24, 0.98)  # 泥金过渡
    sg.add_color_stop_rgba(1.00, 0.98, 0.86, 0.35, 1.00)  # 泥金亮尖
    ctx.set_source(sg)
    ctx.fill_preserve()

    # 3. Luminous Mud-Gold outline (泥金勾边) + subtle outer sumi-ink rim
    ctx.set_source_rgba(0.96, 0.82, 0.32, 0.98)
    ctx.set_line_width(max(2.2, r * 0.10))
    ctx.stroke_preserve()

    ctx.set_source_rgba(0.16, 0.12, 0.10, 0.78)
    ctx.set_line_width(1.2)
    ctx.stroke()

    # 4. Scattered fine gold-leaf & cinnabar flecks (飘散细碎金粉)
    rng = random.Random(int(cx * 17 + cy * 31 + 42))
    for _ in range(22):
        dist = rng.uniform(r * 0.55, r * 2.4)
        ang = rng.uniform(0, math.tau)
        px = cx + dist * math.cos(ang)
        py = cy + dist * math.sin(ang)
        pr = rng.uniform(1.1, 2.8)
        if rng.random() < 0.72:
            ctx.set_source_rgba(0.96, 0.82, 0.30, rng.uniform(0.55, 0.95))
        else:
            ctx.set_source_rgba(0.86, 0.26, 0.18, rng.uniform(0.48, 0.88))
        ctx.arc(px, py, pr, 0, math.tau)
        ctx.fill()

    ctx.restore()


def _compute_ink_slime_contour(
    cx: float,
    cy: float,
    R: float,
    sy: float,
    tilt: float,
    t: float,
    look_x: float = 0.0,
    look_y: float = 0.0,
    grounded: bool = False,
    n_pts: int = 128,
) -> list[tuple[float, float]]:
    """
    Computes an organic soft-body Ink-Wash Slime contour with:
      1. Volume conservation (sx = 1 / sqrt(sy))
      2. Flat-bottom ground contact & lower-cheek bulge when squashed / grounded
      3. 3D spherical upper-dome lean toward (look_x, look_y)
      4. Subtle calligraphic brush-ripple breathing
    """
    sx = 1.0 / math.sqrt(max(0.28, sy))
    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)

    squash_amount = max(0.0, 1.0 - sy)
    stretch_amount = max(0.0, sy - 1.0)
    flat_factor = min(1.0, squash_amount * 2.4 + (0.28 if (grounded and sy <= 1.03) else 0.0))

    gx_c = max(-1.1, min(1.1, look_x))
    gy_c = max(-1.1, min(1.1, look_y))

    pts = []
    for i in range(n_pts):
        theta = (i / float(n_pts)) * math.tau
        raw_x = math.cos(theta)
        raw_y = math.sin(theta)  # >0 is bottom, <0 is top crown

        # Lower-cheek pear fullness + squash cheek bulge
        if raw_y > 0.0:
            cheek_bulge = 1.0 + (0.10 + 0.34 * squash_amount) * (raw_y ** 1.35)
            height_mod = 0.96
            if flat_factor > 0.01 and raw_y > 0.25:
                flatten_u = min(1.0, (raw_y - 0.25) / 0.75)
                flat_y = 0.25 + (raw_y - 0.25) * (1.0 - 0.36 * flat_factor * (flatten_u ** 0.85))
                cheek_bulge += 0.16 * flat_factor * math.sin(flatten_u * math.pi)
                raw_y = flat_y
        else:
            cheek_bulge = 1.0 - 0.06 * ((-raw_y) ** 1.45) - 0.08 * stretch_amount * ((-raw_y) ** 1.6)
            height_mod = 1.04

        dome_weight = max(0.0, -raw_y) ** 1.25 if raw_y < 0.0 else 0.0
        crown_lean_x = gx_c * R * 0.14 * dome_weight
        crown_lift_y = gy_c * R * 0.10 * dome_weight

        ripple = (
            R * 0.008 * math.sin(3.0 * theta + t * 2.8)
            + R * 0.005 * math.cos(5.0 * theta - t * 2.1)
        )

        lx = (R * cheek_bulge * raw_x + ripple * raw_x) * sx + crown_lean_x
        ly = (R * height_mod * raw_y + ripple * raw_y) * sy + crown_lift_y

        wx = cx + lx * cos_t - ly * sin_t
        wy = cy + lx * sin_t + ly * cos_t
        pts.append((wx, wy))
    return pts


def draw_slime(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    radius: float = 110.0,
    *,
    squash_y: float = 1.12,
    tilt: float = 0.22,
    look: tuple[float, float] = (0.55, -0.42),
    eye_mode: str = "pill",
    blink: float = 0.0,
    t: float = 0.0,
    **style_kw,
):
    """
    Renders the Gemini 4 Star-Spark Slime natively translated to raw Xuan paper & sumi-ink:
      1. Organic soft-body contour with flat-bottom ground contact & lower-cheek bulge
      2. Multi-layered 3D swirling wet ink diffusion (宿墨三色水晕流转):
         Mineral Indigo (花青 #2B5B84) -> Lotus Violet (青莲/紫毫 #5E3A73) -> Cinnabar Rouge (胭脂 #C84B31)
      3. Expressive variable-width dry-brush calligraphic outline (中锋浓墨 + 侧锋飞白墨线)
      4. Strictly MOUTHLESS: Two unpainted Xuan-paper negative-space capsule eyes
         with full 3D spherical perspective (pill, charge, happy, wince, sparkle, closed).
    """
    R = float(radius)
    sy = max(0.28, float(squash_y))
    sx = 1.0 / math.sqrt(sy)
    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)

    look_x = float(style_kw.get("look_x", look[0] if isinstance(look, (tuple, list)) else 0.55))
    look_y = float(style_kw.get("look_y", look[1] if isinstance(look, (tuple, list)) else -0.42))
    grounded = bool(style_kw.get("grounded", sy <= 1.02))
    roll_angle = float(style_kw.get("roll_angle", 0.0))

    pts = _compute_ink_slime_contour(
        cx, cy, R, sy, tilt, t, look_x=look_x, look_y=look_y, grounded=grounded, n_pts=128
    )

    # --- 0. Calligraphic Wet-Ink Absorption Contact Shadow (生宣纸触地水晕墨影) ---
    ctx.save()
    foot_y = cy + R * sy * (0.90 if grounded else 0.94)
    ctx.translate(cx - 6.0 * cos_t, foot_y)
    ctx.rotate(tilt * 0.45)
    sh_rx = R * sx * (1.06 if grounded else 0.85)
    sh_ry = max(8.0, R * 0.14)
    ctx.scale(sh_rx, sh_ry)
    sh_g = cairo.RadialGradient(0, 0, 0.08, 0, 0, 1.0)
    sh_g.add_color_stop_rgba(0.00, 0.07, 0.07, 0.09, 0.78 if grounded else 0.52)
    sh_g.add_color_stop_rgba(0.55, 0.15, 0.22, 0.30, 0.38 if grounded else 0.22)
    sh_g.add_color_stop_rgba(1.00, 0.18, 0.22, 0.28, 0.0)
    ctx.set_source(sh_g)
    ctx.arc(0, 0, 1.0, 0, math.tau)
    ctx.fill()
    ctx.restore()

    # --- 1. Soft Wet Diffusion Outer Xuan-Paper Bleed Halo (生宣纸外缘水晕渗化) ---
    for expand, alpha_w in [(1.085, 0.16), (1.042, 0.28)]:
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(expand, expand)
        ctx.translate(-cx, -cy)
        draw_slime_path(ctx, pts)
        w_grad = cairo.LinearGradient(
            cx - R * sx * cos_t,
            cy - R * sy * cos_t,
            cx + R * sx * cos_t,
            cy + R * sy * cos_t,
        )
        w_grad.add_color_stop_rgba(0.00, 0.17, 0.36, 0.52, alpha_w)  # 花青 Mineral indigo
        w_grad.add_color_stop_rgba(0.55, 0.37, 0.23, 0.45, alpha_w)  # 青莲 Lotus violet
        w_grad.add_color_stop_rgba(1.00, 0.78, 0.29, 0.19, alpha_w)  # 胭脂 Cinnabar rouge
        ctx.set_source(w_grad)
        ctx.fill()
        ctx.restore()

    # --- 2. Main Wet Ink Body Diffusion (宿墨三色晕染：花青 -> 青莲 -> 胭脂) ---
    swirl_ang = tilt + roll_angle
    cos_sw = math.cos(swirl_ang)
    sin_sw = math.sin(swirl_ang)

    draw_slime_path(ctx, pts)
    body_g = cairo.LinearGradient(
        cx - R * 0.78 * sx * cos_sw + R * 0.42 * sin_sw,
        cy - R * 0.78 * sy * cos_sw - R * 0.42 * cos_sw,
        cx + R * 0.78 * sx * cos_sw - R * 0.42 * sin_sw,
        cy + R * 0.78 * sy * cos_sw + R * 0.42 * cos_sw,
    )
    body_g.add_color_stop_rgba(0.00, 0.155, 0.345, 0.525, 0.99)  # 花青 #285886
    body_g.add_color_stop_rgba(0.28, 0.235, 0.275, 0.495, 0.99)  # 花青-青莲过渡
    body_g.add_color_stop_rgba(0.56, 0.375, 0.225, 0.460, 0.99)  # 青莲/紫毫 #603975
    body_g.add_color_stop_rgba(0.84, 0.665, 0.255, 0.275, 0.99)  # 青莲-胭脂过渡
    body_g.add_color_stop_rgba(1.00, 0.805, 0.290, 0.190, 0.99)  # 胭脂/朱磦 #CD4A30
    ctx.set_source(body_g)
    ctx.fill_preserve()

    # --- 3. Body Clip: 3D Swirling Mineral Ink Clouds, Sumi Depth & Xuan Paper Highlight ---
    ctx.save()
    ctx.clip()

    # 3a. Swirling Cinnabar-Rouge warm core cloud (胭脂朱砂气韵团)
    rouge_cx = cx + R * (0.20 * math.cos(roll_angle) + 0.14 * look_x) * sx
    rouge_cy = cy + R * (0.28 * math.sin(roll_angle + 0.8) + 0.12 * look_y) * sy
    puddle_g = cairo.RadialGradient(rouge_cx, rouge_cy, R * 0.04, rouge_cx, rouge_cy, R * 0.92)
    puddle_g.add_color_stop_rgba(0.00, 0.90, 0.36, 0.22, 0.62)
    puddle_g.add_color_stop_rgba(0.55, 0.56, 0.20, 0.38, 0.28)
    puddle_g.add_color_stop_rgba(1.00, 0.12, 0.10, 0.18, 0.00)
    ctx.set_source(puddle_g)
    ctx.arc(rouge_cx, rouge_cy, R * 0.92, 0, math.tau)
    ctx.fill()

    # 3b. Swirling Mineral Indigo cloud on opposite lobe (花青墨韵团)
    ind_cx = cx - R * (0.26 * math.cos(roll_angle) - 0.12 * look_x) * sx
    ind_cy = cy - R * (0.24 * math.sin(roll_angle + 0.8) - 0.10 * look_y) * sy
    ind_g = cairo.RadialGradient(ind_cx, ind_cy, R * 0.04, ind_cx, ind_cy, R * 0.85)
    ind_g.add_color_stop_rgba(0.00, 0.14, 0.42, 0.62, 0.52)
    ind_g.add_color_stop_rgba(0.60, 0.18, 0.30, 0.48, 0.22)
    ind_g.add_color_stop_rgba(1.00, 0.18, 0.25, 0.40, 0.00)
    ctx.set_source(ind_g)
    ctx.arc(ind_cx, ind_cy, R * 0.85, 0, math.tau)
    ctx.fill()

    # 3c. Internal calligraphic water-stain rings & mud-gold flecks (水渍墨痕与泥金星点)
    for wc_ang_off, wc_r, wc_col in [
        (0.0, 0.52, (0.08, 0.14, 0.22, 0.18)),
        (2.1, 0.44, (0.52, 0.18, 0.24, 0.16)),
    ]:
        w_ang = roll_angle * 1.4 + wc_ang_off
        w_x = cx + R * 0.22 * math.cos(w_ang) * sx
        w_y = cy + R * 0.20 * math.sin(w_ang) * sy
        ctx.new_path()
        ctx.arc(w_x, w_y, R * wc_r, 0, math.tau)
        ctx.set_source_rgba(*wc_col)
        ctx.set_line_width(2.2)
        ctx.stroke()

    # 3d. Calligraphic gloss highlight on upper-left dome (宣纸留白水光点, shifts with 3D gaze)
    ctx.save()
    ctx.translate(cx - R * (0.36 - look_x * 0.15) * sx, cy - R * (0.42 - look_y * 0.12) * sy)
    ctx.rotate(tilt * 0.6 - 0.45)
    ctx.scale(1.0, 0.46)
    hi_g = cairo.RadialGradient(0, 0, 1.0, 0, 0, R * 0.34)
    hi_g.add_color_stop_rgba(0.00, 0.99, 0.97, 0.93, 0.72)
    hi_g.add_color_stop_rgba(0.55, 0.78, 0.89, 0.98, 0.28)
    hi_g.add_color_stop_rgba(1.00, 0.17, 0.36, 0.52, 0.00)
    ctx.set_source(hi_g)
    ctx.arc(0, 0, R * 0.34, 0, math.tau)
    ctx.fill()
    ctx.restore()

    ctx.restore()  # End body clip

    # --- 4. Expressive Dry-Brush Calligraphic Outline (中锋浓墨 + 侧锋飞白墨线) ---
    draw_slime_path(ctx, pts)
    ctx.set_source_rgba(0.07, 0.07, 0.09, 0.96)
    ctx.set_line_width(max(4.2, R * 0.040))
    ctx.stroke()

    # Weighted lower-right / base brush belly stroke (重墨顿笔边线)
    ctx.save()
    ctx.translate(2.2, 3.2)
    ctx.new_path()
    n_pts = len(pts)
    for i in range(int(n_pts * 0.12), int(n_pts * 0.88)):
        p = pts[i]
        if i == int(n_pts * 0.12):
            ctx.move_to(p[0], p[1])
        else:
            ctx.line_to(p[0], p[1])
    ctx.set_source_rgba(0.04, 0.04, 0.06, 0.78)
    ctx.set_line_width(max(3.2, R * 0.032))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()

    # Dry-brush feibai highlight thread along upper-left rim (飞白丝线)
    ctx.save()
    ctx.new_path()
    for i in range(int(n_pts * 0.56), int(n_pts * 0.84)):
        p = pts[i]
        if i == int(n_pts * 0.56):
            ctx.move_to(p[0] + 1.5, p[1] + 1.5)
        else:
            ctx.line_to(p[0] + 1.5, p[1] + 1.5)
    ctx.set_source_rgba(0.97, 0.95, 0.90, 0.42)
    ctx.set_line_width(1.4)
    ctx.set_dash([12.0, 5.0, 6.0, 4.0], t * 8.0)
    ctx.stroke()
    ctx.restore()

    # --- 5. MOUTHLESS NEGATIVE-SPACE CAPSULE EYES (宣纸留白胶囊眼, C-infinity 3D projection) ---
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

    coupled_tilt = tilt + gx_c * 0.055 - gy_c * 0.025 * (1.0 if gx_c >= 0.0 else -1.0)
    cos_ct, sin_ct = math.cos(coupled_tilt), math.sin(coupled_tilt)

    gaze_cx = math.sin(yaw) * R * 0.52 * sx
    gaze_cy = math.sin(pitch) * R * 0.46 * sy

    cant_angle = gx_c * (-0.28 + 0.42 * gy_c)
    cos_c, sin_c = math.cos(cant_angle), math.sin(cant_angle)

    base_sep = R * 0.225 * max(0.56, math.cos(yaw * 0.72))
    w_base = R * 0.114
    h_base = R * 0.252 * max(0.08, 1.0 - blink * 0.92)

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

        ctx.save()
        ctx.translate(ex, ey)
        ctx.rotate(coupled_tilt + cant_angle + side * gx_c * 0.03)

        if eye_mode in ("happy", "happy_arc") or (eye_mode == "wink_right" and side == 1):
            arc_r = h_eye * 0.72
            arc_w = max(3.0, w_eye * 1.15)
            ctx.new_path()
            ctx.arc(0, arc_r * 0.3, arc_r, math.pi * 1.15, math.pi * 1.85)
            ctx.set_source_rgba(0.07, 0.07, 0.09, 0.94)
            ctx.set_line_width(arc_w + 3.4)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgba(0.992, 0.980, 0.945, 1.0)
            ctx.set_line_width(arc_w)
            ctx.stroke()
        elif eye_mode == "closed":
            arc_r = h_eye * 0.68
            arc_w = max(2.8, w_eye * 1.05)
            ctx.new_path()
            ctx.arc(0, -arc_r * 0.25, arc_r, math.pi * 0.18, math.pi * 0.82)
            ctx.set_source_rgba(0.07, 0.07, 0.09, 0.94)
            ctx.set_line_width(arc_w + 3.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgba(0.992, 0.980, 0.945, 1.0)
            ctx.set_line_width(arc_w)
            ctx.stroke()
        elif eye_mode == "wince":
            # Calligraphic > < wince eyes
            s_dir = 1.0 if side == -1 else -1.0
            hw = w_eye * 0.95
            hh = h_eye * 0.42
            ctx.new_path()
            ctx.move_to(-s_dir * hw, -hh)
            ctx.line_to(s_dir * hw * 0.65, 0.0)
            ctx.line_to(-s_dir * hw, hh)
            ctx.set_source_rgba(0.07, 0.07, 0.09, 0.95)
            ctx.set_line_width(max(3.6, w_eye * 0.95) + 3.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgba(0.992, 0.980, 0.945, 1.0)
            ctx.set_line_width(max(3.6, w_eye * 0.95))
            ctx.stroke()
        elif eye_mode in ("sparkle", "star"):
            # Four-point mud-gold & Xuan-white star eyes (✦ ✦)
            star_r = max(w_eye, h_eye) * 0.86
            draw_four_point_star(ctx, 0, 0, star_r, star_r * 0.32, rot=0.0)
            ctx.set_source_rgba(0.995, 0.985, 0.950, 1.0)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.88, 0.68, 0.22, 0.96)
            ctx.set_line_width(2.4)
            ctx.stroke()
        elif eye_mode in ("charge", "sharp"):
            # Determined angled brow capsule eye (蓄力坚毅剑眉眼)
            h_ch = h_eye * 0.80
            draw_capsule_pill(ctx, 0, 1.2, w_eye + 3.2, h_ch + 3.2)
            ctx.set_source_rgba(0.04, 0.04, 0.06, 0.58)
            ctx.fill()
            draw_capsule_pill(ctx, 0, 0, w_eye, h_ch)
            ctx.set_source_rgba(0.992, 0.980, 0.945, 1.0)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.08, 0.08, 0.10, 0.96)
            ctx.set_line_width(2.0)
            ctx.stroke()
            # Slanted calligraphic brow stroke above eye
            ctx.new_path()
            ctx.move_to(-w_eye * 0.85, -h_ch * 0.52 + side * 3.5)
            ctx.line_to(w_eye * 0.85, -h_ch * 0.52 - side * 3.5)
            ctx.set_source_rgba(0.07, 0.07, 0.09, 0.96)
            ctx.set_line_width(3.4)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
        else:
            # Subtle dark ink socket rim accent (墨色在眼周自然收边)
            draw_capsule_pill(ctx, 0, 1.2, w_eye + 3.2, h_eye + 3.2)
            ctx.set_source_rgba(0.04, 0.04, 0.06, 0.55)
            ctx.fill()

            # Pure unpainted raw Xuan paper negative space capsule eye (宣纸留白)
            draw_capsule_pill(ctx, 0, 0, w_eye, h_eye)
            ctx.set_source_rgba(0.992, 0.980, 0.945, 1.0)
            ctx.fill_preserve()

            # Fine calligraphic brush contour around the eye
            ctx.set_source_rgba(0.08, 0.08, 0.10, 0.95)
            ctx.set_line_width(1.9)
            ctx.stroke()
        ctx.restore()

    # Optional resonant gold-ochre & mineral-indigo ink drops above slime crown
    if style_kw.get("with_crown_sparks", True):
        crown_x = cx - (-R * sy * 1.04) * sin_t
        crown_y = cy + (-R * sy * 1.04) * cos_t
        for dx_s, dy_s, r_s, col_s in [
            (-9, -14, 3.4, (0.88, 0.66, 0.22, 0.88)),
            (10, -24, 4.2, (0.82, 0.26, 0.18, 0.85)),
            (25, -32, 2.8, (0.17, 0.38, 0.54, 0.82)),
        ]:
            ctx.arc(crown_x + dx_s, crown_y + dy_s, r_s, 0, math.tau)
            ctx.set_source_rgba(*col_s)
            ctx.fill()



# ==============================================================================
# 8. TRADITIONAL CALLIGRAPHY INSCRIPTION (卷首竖排小楷题诗 + 朱砂小名章, NO UI TAG!)
# ==============================================================================
def draw_calligraphy_inscription(pil_img: Image.Image, ox_screen: float = 0.0):
    """
    Renders the vertical poetic calligraphy inscription on upper-left:
      Right column: 「星芒入画 · 一点灵犀」
      Left column:  「双子乘风跃青竹　毫端泼墨化神韵」
      Plus a mini cinnabar gourd seal (葫芦引首小印「星芒」).
    Strictly omits the bottom-left UI bookplate tag!
    """
    draw = ImageDraw.Draw(pil_img)
    f_cn_med = get_pil_font(19, FONT_CJK_MED)
    f_cn_sm = get_pil_font(17, FONT_CJK_MED)
    f_mini = get_pil_font(11, FONT_CJK_MED)

    # Column 1 (Right): STORY.md scroll title inscription
    col1_text = "星芒入画·一点灵犀"
    ix1 = int(ox_screen + 412)
    iy1 = 165
    if -100 <= ix1 <= W + 100:
        cur_y = iy1
        for ch in col1_text:
            if ch == "·":
                draw.ellipse([ix1 + 7, cur_y + 6, ix1 + 12, cur_y + 11], fill=(185, 45, 32, 220))
                cur_y += 20
                continue
            draw.text((ix1, cur_y), ch, font=f_cn_med, fill=(32, 30, 36, 232))
            cur_y += 28

        # Column 2 (Left): v3 poetic couplet
        col2_text = "双子乘风跃青竹　毫端泼墨化神韵"
        ix2 = ix1 - 32
        cur_y2 = iy1 + 14
        for ch in col2_text:
            if ch == "　":
                cur_y2 += 16
                continue
            draw.text((ix2, cur_y2), ch, font=f_cn_sm, fill=(48, 44, 52, 215))
            cur_y2 += 26

        # Mini cinnabar seal below left column (朱砂小名章「星芒」)
        gourd_x, gourd_y = ix2 + 2, cur_y2 + 10
        draw.rounded_rectangle(
            [gourd_x, gourd_y, gourd_x + 22, gourd_y + 36],
            radius=6,
            fill=(190, 42, 30, 232),
            outline=(130, 25, 20, 240),
            width=1,
        )
        draw.text((gourd_x + 5, gourd_y + 4), "星", font=f_mini, fill=(248, 242, 230, 245))
        draw.text((gourd_x + 5, gourd_y + 18), "芒", font=f_mini, fill=(248, 242, 230, 245))


# ==============================================================================
# 9. WORLD & KEYFRAME RENDER PIPELINE (render_world & render_keyframe)
# ==============================================================================
def render_world(cam_x: float = KEY_CAM_X, cam_y: float = KEY_CAM_Y, t: float = 6.0, state: dict = None) -> Image.Image:
    """
    Renders the 1920x1080 viewport at camera center (cam_x, cam_y) within the 7680x1080 scroll.
    Uses v3's authentic Xuan paper synthesis and crisp PyCairo brushwork.
    """
    if state is None:
        state = {}

    # 1. Synthesize Raw Xuan Paper backdrop
    paper_rgb, grain = make_xuan_paper(W, H, seed=108)
    paper_img = Image.fromarray((paper_rgb * 255.0).astype(np.uint8), mode="RGB").convert("RGBA")

    # 2. PyCairo Painting Surface
    surface = pil_to_cairo(paper_img)
    ctx = cairo.Context(surface)

    # Subtle mulberry bark threads on paper
    draw_paper_fibers(ctx, W, H, seed=108)

    # Apply camera transform (world -> screen)
    ctx.save()
    ctx.translate(W * 0.5 - cam_x, H * 0.5 - cam_y)

    # Additional scroll landmarks for Screens 1 & 2 if camera pans left
    if cam_x < 3840.0:
        draw_distant_mountains(ctx, ox=0.0)
        draw_bamboo_elements(ctx, ox=0.0)
        draw_misty_broken_bridge(ctx, 2150.0, 480.0, scale=1.0, alpha_mul=0.85)

    # 3. Core Masterpiece Composition anchored at KEY_OX (3840.0)
    draw_distant_mountains(ctx, ox=KEY_OX)
    draw_bamboo_elements(ctx, ox=KEY_OX)
    draw_leap_and_lotus(ctx, ox=KEY_OX, state=state)

    seal_cx = state.get("seal_x", KEY_OX + 1490.0)
    seal_cy = state.get("seal_y", 255.0)
    draw_cinnabar_seal_stamp(ctx, cx=seal_cx, cy=seal_cy, size=142.0)

    # 4. Draw Ink-Wash Slime Character
    slime_cx = state.get("slime_cx", KEY_OX + 625.0)
    slime_cy = state.get("slime_cy", 605.0)
    slime_r = state.get("slime_r", 112.0)
    squash_y = state.get("squash_y", 1.12)
    tilt = state.get("tilt", 0.22)
    look = state.get("look", (0.55, -0.42))
    eye_mode = state.get("eye_mode", "pill")
    blink = state.get("blink", 0.0)

    draw_slime(
        ctx,
        slime_cx,
        slime_cy,
        slime_r,
        squash_y=squash_y,
        tilt=tilt,
        look=look,
        eye_mode=eye_mode,
        blink=blink,
        t=t,
    )

    ctx.restore()

    # Flush Cairo surface
    surface.flush()
    composite_pil = cairo_to_pil(surface)

    # 5. Global Xuan Paper Fiber Integration (v3 technique: crisp brush edges + paper tooth)
    arr = np.asarray(composite_pil, dtype=np.float32) / 255.0
    arr[..., :3] = np.clip(arr[..., :3] + grain[..., None] * 0.012, 0.0, 1.0)
    final_pil = Image.fromarray((arr * 255.0).astype(np.uint8), mode="RGBA")

    # 6. Traditional Vertical Calligraphy Inscription + Mini Cinnabar Seal (NO bottom-left UI tag)
    ox_screen = (W * 0.5 - cam_x) + KEY_OX
    draw_calligraphy_inscription(final_pil, ox_screen=ox_screen)

    return final_pil.convert("RGB")


def render_keyframe() -> Image.Image:
    """
    Renders the representative keyframe (1920x1080) for World 04 · 水墨宣纸千里长卷.
    """
    state = {
        "slime_cx": KEY_OX + 625.0,
        "slime_cy": 605.0,
        "slime_r": 112.0,
        "squash_y": 1.12,
        "tilt": 0.22,
        "look": (0.55, -0.42),
        "eye_mode": "pill",
        "blink": 0.0,
        "fish_x": KEY_OX + 985.0,
        "fish_y": 615.0,
        "fish_ang": -0.46,
        "star_x": KEY_OX + 1003.0,
        "star_y": 519.0,
        "star_r": 34.0,
        "star_rot": 0.14,
        "seal_x": KEY_OX + 1490.0,
        "seal_y": 255.0,
    }
    return render_world(KEY_CAM_X, KEY_CAM_Y, t=6.0, state=state)


if __name__ == "__main__":
    import time

    t0 = time.time()
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_png = os.path.join(out_dir, "style_04_inkwash.png")
    preview_jpg = "/tmp/preview_04_inkwash.jpg"

    img = render_keyframe()
    os.makedirs(out_dir, exist_ok=True)
    img.save(out_png, format="PNG", optimize=False)

    # Save lightweight 1280x720 preview JPG (<150KB) for visual inspection
    preview = img.resize((1280, 720), Image.Resampling.LANCZOS)
    preview.save(preview_jpg, format="JPEG", quality=80, optimize=True)

    dt = time.time() - t0
    print(f"[OK] Rendered World 04 keyframe in {dt:.2f}s -> {out_png} & {preview_jpg}")
