# -*- coding: utf-8 -*-
"""
StyleHop · World 01 · 矩阵终端序章 (style_01_crt.py)
Fuses v3's authentic curved CRT monitor bezel, top perspective scan-grid, dense green
Matrix code rain, bottom-left `stardino@crt:~$ ./wake --curious` terminal log, and
radiant ASCII Slime aura with v4's STORY.md code staircase, `[████████░░] 78%`
progress bar springboard, shattering inverse `ERR_404` blocks, and distant `[ ENTER ↵ ]` key.
"""

import os
import sys
import math
import random
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import cairo
from PIL import Image, ImageFilter

# Repository root derived from __file__ (no absolute paths)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from corelib.math_ops import clamp, lerp, smoothstep, smootherstep, ease_out_cubic, ease_out_back, ease_in_out_cubic
from corelib.camera import get_font

# -----------------------------------------------------------------------------
# 1. CONSTANTS & WORLD DIMENSIONS
# -----------------------------------------------------------------------------
W, H = 1920, 1080
WORLD_W, WORLD_H = 5760, 1080  # 3 screens wide (5760 x 1080)

FONT_MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_MONO_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Phosphor Green Palette (Strictly Monochrome Terminal World)
PHOSPHOR_PEAK   = (0.58, 1.00, 0.72)      # #94FFB8 Peak highlight / blooming text
PHOSPHOR_BRIGHT = (0.28, 0.98, 0.52)      # #47FA85 Core vibrant text green
PHOSPHOR_CORE   = (0.04, 0.86, 0.38)      # #0AD961 Standard code green
PHOSPHOR_MID    = (0.00, 0.62, 0.26)      # #009E42 Secondary structure & grid
PHOSPHOR_DIM    = (0.00, 0.40, 0.16)      # #006629 Matrix code rain & guides
PHOSPHOR_DARK   = (0.00, 0.20, 0.08)      # #003314 Deep background grid

# Star-Spark Slime Palette (Strictly for Slime & Star ONLY: Blue -> Iris -> Coral)
SLIME_BLUE   = (0.259, 0.522, 0.957)     # #4285F4 Sky Blue
SLIME_CYAN   = (0.350, 0.740, 1.000)     # #59BDFF Luminous Cyan
SLIME_IRIS   = (0.460, 0.350, 0.910)     # #7559E8 Iris Violet
SLIME_PURPLE = (0.608, 0.447, 0.796)     # #9B72CB Orchid Purple
SLIME_CORAL  = (0.851, 0.396, 0.439)     # #D96570 Dawn Rose-Coral

ASCII_SLIME_CHARS = ["@", "#", "%", "*", "0", "1", "&", "$", "8", "B", "W", "X", "Z", "+", "=", ":", "-"]
ASCII_SHARDS = ["E", "R", "R", "_", "4", "0", "4", "!", "#", "*", "%", "&", "+", "=", "0", "1"]
MATRIX_CHARS = ["0", "1", "0", "1", "0", "1", "0", "1", ":", ".", "+", "*", "0", "1", "7", "F", "E", "A"]

# -----------------------------------------------------------------------------
# 2. CRT DISTORTION & MONITOR BEZEL CACHE
# -----------------------------------------------------------------------------
_CRT_CACHE: Dict[str, Any] = {}

def _init_crt_distortion(w: int = W, h: int = H, k: float = 0.042):
    """Precompute curved CRT barrel coordinates, 3D monitor bezel, and scanline mask."""
    key = (w, h, k)
    if key in _CRT_CACHE:
        return _CRT_CACHE[key]

    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * 0.5, h * 0.5
    nx = (x - cx) / (cx * 0.935)
    ny = (y - cy) / (cy * 0.915)
    r2 = nx * nx + ny * ny

    # Authentic curved CRT barrel distortion for the inner phosphor tube
    raw_nx = (x - cx) / cx
    raw_ny = (y - cy) / cy
    raw_r2 = raw_nx * raw_nx + raw_ny * raw_ny
    distort_x = cx + raw_nx * (1.0 + k * raw_r2) * cx
    distort_y = cy + raw_ny * (1.0 + k * raw_r2) * cy

    # Squircle CRT screen boundary distance: d_tube = 1.0 at screen edge
    # Curved barrel edges like classic 4:3/16:9 Sony/DEC CRT tube
    curve_x = np.abs(nx) * (1.0 + 0.065 * (ny ** 2))
    curve_y = np.abs(ny) * (1.0 + 0.085 * (nx ** 2))
    corner_r = 0.14
    dx_c = np.maximum(curve_x - (1.0 - corner_r), 0.0) / corner_r
    dy_c = np.maximum(curve_y - (1.0 - corner_r), 0.0) / corner_r
    d_tube = np.maximum(np.maximum(curve_x, curve_y), (1.0 - corner_r) + corner_r * np.sqrt(dx_c * dx_c + dy_c * dy_c))

    # Screen interior mask (1.0 inside CRT glass, 0.0 on outer plastic/metal bezel)
    screen_mask = np.clip((1.0 - d_tube) * 45.0, 0.0, 1.0).astype(np.float32)

    # Inner glass edge vignette (darkens smoothly near the curved glass edge)
    glass_vignette = np.clip(1.0 - 0.28 * (raw_r2 ** 1.3), 0.0, 1.0).astype(np.float32)
    edge_darken = np.clip((1.005 - d_tube) * 14.0, 0.0, 1.0).astype(np.float32)
    glass_vignette = glass_vignette * (0.35 + 0.65 * edge_darken)

    # 3D Molded Bezel Rim highlight & housing color outside the glass
    # Between d_tube = 0.992 and 1.035 is the recessed inner bezel lip
    bezel_lip = np.exp(-((d_tube - 1.006) / 0.012) ** 2).astype(np.float32)
    bezel_outer = (1.0 - screen_mask).astype(np.float32)

    # Outer monitor housing base RGB (v3 dark charcoal-olive monitor frame)
    housing_rgb = np.zeros((h, w, 3), dtype=np.float32)
    housing_rgb[:, :, 0] = 15.0 + 6.0 * (1.0 - raw_r2 * 0.4)
    housing_rgb[:, :, 1] = 19.0 + 8.0 * (1.0 - raw_r2 * 0.4)
    housing_rgb[:, :, 2] = 17.0 + 6.0 * (1.0 - raw_r2 * 0.4)

    # Dark recessed groove right around the tube + subtle green phosphor reflection on the bezel lip
    groove = np.exp(-((d_tube - 1.018) / 0.018) ** 2).astype(np.float32)
    housing_rgb *= (1.0 - 0.65 * groove[:, :, None])
    housing_rgb[:, :, 0] += bezel_lip * 12.0
    housing_rgb[:, :, 1] += bezel_lip * 62.0
    housing_rgb[:, :, 2] += bezel_lip * 28.0

    # Fine horizontal CRT scanline wave
    scanline = (0.87 + 0.13 * np.sin(y * math.pi)).astype(np.float32)

    _CRT_CACHE[key] = {
        "coords": np.array([distort_y, distort_x]),
        "screen_mask": screen_mask,
        "vignette": glass_vignette,
        "housing_rgb": housing_rgb,
        "bezel_outer": bezel_outer,
        "scanline": scanline,
    }
    return _CRT_CACHE[key]


# -----------------------------------------------------------------------------
# 3. CORE GEOMETRY & CHARACTER RIG
# -----------------------------------------------------------------------------
def compute_slime_contour(cx: float, cy: float, radius: float, squash_y: float = 1.0,
                         tilt: float = 0.0, n_pts: int = 96,
                         look_x: float = 0.0, look_y: float = 0.0) -> List[Tuple[float, float]]:
    """Volume-preserving jelly mochi contour (sx = 1/sqrt(sy)) with 3D body-gaze coupling."""
    sy = max(0.45, min(2.2, squash_y))
    sx = 1.0 / math.sqrt(sy)
    r = radius
    pts = []
    gx = max(-1.1, min(1.1, float(look_x)))
    gy = max(-1.1, min(1.1, float(look_y)))
    coupled_tilt = tilt + gx * 0.055 - gy * 0.025 * (1.0 if gx >= 0.0 else -1.0)
    cos_t, sin_t = math.cos(coupled_tilt), math.sin(coupled_tilt)

    for i in range(n_pts):
        th = (i / n_pts) * math.tau
        s = math.sin(th)  # -1 at top, +1 at base
        c = math.cos(th)

        upper_weight = ((1.0 - s) * 0.5) ** 1.45
        cheek_bias = 1.0 + 0.048 * gx * c * (1.0 - 0.45 * abs(s))

        # Plump dome with gentle bottom contact cushion
        width_mod = (1.015 + 0.030 * s - 0.012 * (s ** 2)) * cheek_bias
        height_mod = 0.992 - 0.035 * (max(0.0, s) ** 2.2)

        crown_lean_x = r * gx * 0.135 * upper_weight * sx
        crown_lift_y = r * gy * 0.095 * upper_weight * sy

        lx = r * width_mod * c * sx + crown_lean_x
        ly = r * height_mod * s * sy + crown_lift_y

        rx = lx * cos_t - ly * sin_t
        ry = lx * sin_t + ly * cos_t
        pts.append((cx + rx, cy + ry))
    return pts


def draw_capsule_pill(ctx: cairo.Context, cx: float, cy: float, half_w: float, half_h: float):
    """Draws a rounded capsule pill centered at (cx, cy)."""
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


def draw_four_point_star(ctx: cairo.Context, cx: float, cy: float, outer_r: float,
                         inner_r: Optional[float] = None, rot: float = 0.0):
    """Signature 4-pointed sparkle star with concave Bezier arcs."""
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


# -----------------------------------------------------------------------------
# 4. REQUIRED API: draw_slime
# -----------------------------------------------------------------------------
def draw_slime(ctx: cairo.Context, cx: float, cy: float, radius: float, *,
               squash_y: float = 1.0, tilt: float = 0.0,
               look: Tuple[float, float] = (0.0, 0.0), eye_mode: str = "pill",
               blink: float = 0.0, t: float = 0.0, **style_kw):
    """
    Renders the Star-Spark Slime in World 01 CRT Terminal ASCII Style:
    - Lush outer phosphor radial aura + v3 vertical/radial ASCII energy field around contour.
    - Completely OPAQUE base: occludes background code lines.
    - Interior: dense glowing ASCII characters bound strictly to local coordinates (du, dv)
      in Star-Spark Blue -> Iris Violet -> Dawn Rose-Coral gradient with bright inner core bloom.
    - Eyes: pure white (#FFFFFF) solid capsule blocks with soft white glow, cant angle -30 deg,
      far eye = strictly 81% width of near eye, unaffected by body squash.
    - STRICTLY MOUTHLESS, NO NOSE, NO BLUSH.
    """
    sy = max(0.45, min(2.2, squash_y))
    sx = 1.0 / math.sqrt(sy)
    r = radius
    look_x, look_y = float(look[0]), float(look[1])
    pts = compute_slime_contour(cx, cy, r, squash_y=sy, tilt=tilt, look_x=look_x, look_y=look_y)
    coupled_tilt = tilt + max(-1.1, min(1.1, look_x)) * 0.055 - max(-1.1, min(1.1, look_y)) * 0.025 * (1.0 if look_x >= 0.0 else -1.0)
    cos_t, sin_t = math.cos(coupled_tilt), math.sin(coupled_tilt)

    ctx.save()

    c_blend = float(style_kw.get("color_blend", 1.0))
    is_awake = bool(style_kw.get("is_awake", True))
    if not is_awake:
        c_blend = min(c_blend, 0.0)

    # 0. Lush Outer Phosphor Bloom & v3 Shimmering ASCII Energy Field around Slime
    aura_rad = r * 2.25
    aura_grad = cairo.RadialGradient(cx, cy, r * 0.4, cx, cy, aura_rad)
    if c_blend > 0.05:
        aura_grad.add_color_stop_rgba(0.00, SLIME_CYAN[0], SLIME_CYAN[1], SLIME_CYAN[2], 0.48 * c_blend)
        aura_grad.add_color_stop_rgba(0.38, SLIME_IRIS[0], SLIME_IRIS[1], SLIME_IRIS[2], 0.28 * c_blend)
        aura_grad.add_color_stop_rgba(0.70, PHOSPHOR_CORE[0], PHOSPHOR_CORE[1], PHOSPHOR_CORE[2], 0.14)
    else:
        aura_grad.add_color_stop_rgba(0.00, PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], 0.22)
        aura_grad.add_color_stop_rgba(0.60, PHOSPHOR_DARK[0], PHOSPHOR_DARK[1], PHOSPHOR_DARK[2], 0.10)
    aura_grad.add_color_stop_rgba(1.00, 0.0, 0.0, 0.0, 0.0)
    ctx.set_source(aura_grad)
    ctx.arc(cx, cy, aura_rad, 0, math.tau)
    ctx.fill()

    # v3-style vertical ASCII energy halo columns around the Slime contour (blooms when awake)
    if c_blend > 0.08:
        ctx.save()
        ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(max(9.0, r * 0.14))
        halo_glyphs = ["|", ":", "!", "+", "*", "0", "1", "¦"]
        for col_i in range(-14, 15):
            hx_norm = col_i / 14.0
            col_x = cx + hx_norm * r * sx * 1.48
            env_h = r * sy * math.sqrt(max(0.05, 1.0 - (hx_norm * 0.66) ** 2)) * 1.42
            for row_j in range(-8, 9):
                hy_off = (row_j / 8.0) * env_h
                dist_ell = math.sqrt((hx_norm * 1.48) ** 2 + (hy_off / (r * sy)) ** 2)
                if dist_ell < 0.96 or dist_ell > 1.56:
                    continue
                alpha_h = clamp((1.56 - dist_ell) / 0.60, 0.0, 1.0) * 0.68 * c_blend
                p_col = clamp((hx_norm + 1.0) * 0.5, 0.0, 1.0)
                if p_col < 0.5:
                    f = p_col * 2.0
                    hr = lerp(SLIME_CYAN[0], SLIME_IRIS[0], f)
                    hg = lerp(SLIME_CYAN[1], SLIME_IRIS[1], f)
                    hb = lerp(SLIME_CYAN[2], SLIME_IRIS[2], f)
                else:
                    f = (p_col - 0.5) * 2.0
                    hr = lerp(SLIME_IRIS[0], SLIME_CORAL[0], f)
                    hg = lerp(SLIME_IRIS[1], SLIME_CORAL[1], f)
                    hb = lerp(SLIME_IRIS[2], SLIME_CORAL[2], f)
                ctx.set_source_rgba(hr, hg, hb, alpha_h)
                ch_h = halo_glyphs[(abs(col_i * 7 + row_j * 13)) % len(halo_glyphs)]
                ctx.move_to(col_x - 3.0, cy + hy_off + 3.0)
                ctx.show_text(ch_h)
        ctx.restore()

    # 1. Base jelly body path - SOLID OPAQUE BACKING (100% occlusion of background code)
    ctx.new_path()
    ctx.move_to(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        ctx.line_to(pt[0], pt[1])
    ctx.close_path()

    ctx.set_source_rgb(0.01, 0.02, 0.04)
    ctx.fill_preserve()

    # Rich Slime gradient body fill (Blue -> Iris -> Coral) or Dormant Dark Monochrome
    if c_blend > 0.02:
        body_grad = cairo.LinearGradient(
            cx - r * 0.85 * sx, cy - r * 0.85 * sy,
            cx + r * 0.85 * sx, cy + r * 0.85 * sy
        )
        body_grad.add_color_stop_rgba(0.00, SLIME_BLUE[0], SLIME_BLUE[1], SLIME_BLUE[2], 0.96 * c_blend)
        body_grad.add_color_stop_rgba(0.42, SLIME_IRIS[0], SLIME_IRIS[1], SLIME_IRIS[2], 0.96 * c_blend)
        body_grad.add_color_stop_rgba(0.75, SLIME_PURPLE[0], SLIME_PURPLE[1], SLIME_PURPLE[2], 0.96 * c_blend)
        body_grad.add_color_stop_rgba(1.00, SLIME_CORAL[0], SLIME_CORAL[1], SLIME_CORAL[2], 0.98 * c_blend)
        ctx.set_source(body_grad)
        ctx.fill_preserve()
    else:
        ctx.set_source_rgba(0.06, 0.10, 0.08, 0.96)
        ctx.fill_preserve()

    # Subtle upper-left specular glow (shifts with 3D gaze)
    core_glow = cairo.RadialGradient(
        cx - r * (0.38 - look_x * 0.14) * sx, cy - r * (0.38 - look_y * 0.10) * sy, r * 0.05,
        cx - r * 0.15 * sx, cy - r * 0.15 * sy, r * 0.75
    )
    core_glow.add_color_stop_rgba(0.00, SLIME_CYAN[0], SLIME_CYAN[1], SLIME_CYAN[2], 0.32 * c_blend)
    core_glow.add_color_stop_rgba(0.50, SLIME_BLUE[0], SLIME_BLUE[1], SLIME_BLUE[2], 0.12 * c_blend)
    core_glow.add_color_stop_rgba(1.00, 0.0, 0.0, 0.0, 0.0)
    ctx.set_source(core_glow)
    ctx.fill_preserve()

    # 2. Clip to body contour for local ASCII character matrix (shifted with 3D gaze)
    ctx.save()
    ctx.clip()

    cell_w, cell_h = 6.8, 9.0
    u_range = int(r * 1.35)
    v_range = int(r * 1.35)
    gaze_u_shift = look_x * r * 0.22
    gaze_v_shift = look_y * r * 0.16

    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    font_sz = max(8.5, r * 0.155)
    ctx.set_font_size(font_sz)

    for vi in range(-v_range, v_range, int(cell_h)):
        for ui in range(-u_range, u_range, int(cell_w)):
            dist_norm = math.sqrt((ui / r) ** 2 + (vi / r) ** 2)
            if dist_norm > 0.97:
                continue

            ui_s = ui + gaze_u_shift * (1.0 - 0.35 * dist_norm)
            vi_s = vi + gaze_v_shift * (1.0 - 0.35 * dist_norm)
            wx = cx + (ui_s * sx) * cos_t - (vi_s * sy) * sin_t
            wy = cy + (ui_s * sx) * sin_t + (vi_s * sy) * cos_t

            if c_blend > 0.05:
                p = clamp(((ui / r) + (vi / r)) * 0.5 + 0.5, 0.0, 1.0)
                if p < 0.48:
                    f = p / 0.48
                    cr = lerp(SLIME_CYAN[0], SLIME_IRIS[0], f)
                    cg = lerp(SLIME_CYAN[1], SLIME_IRIS[1], f)
                    cb = lerp(SLIME_CYAN[2], SLIME_IRIS[2], f)
                else:
                    f = (p - 0.48) / 0.52
                    cr = lerp(SLIME_IRIS[0], SLIME_CORAL[0], f)
                    cg = lerp(SLIME_IRIS[1], SLIME_CORAL[1], f)
                    cb = lerp(SLIME_IRIS[2], SLIME_CORAL[2], f)
                lum_boost = clamp(1.48 - 0.32 * dist_norm, 1.0, 1.52)
                char_alpha = clamp(0.92 + 0.08 * (1.0 - dist_norm), 0.85, 1.0)
                cr_f = min(1.0, cr * lum_boost)
                cg_f = min(1.0, cg * lum_boost)
                cb_f = min(1.0, cb * lum_boost)
            else:
                cr_f, cg_f, cb_f = 0.42, 0.62, 0.48
                char_alpha = 0.45

            char_idx = (int(abs(ui * 19 + vi * 37 + 11))) % len(ASCII_SLIME_CHARS)
            char_str = ASCII_SLIME_CHARS[char_idx]

            ctx.set_source_rgba(cr_f, cg_f, cb_f, char_alpha)
            ctx.move_to(wx - font_sz * 0.35, wy + font_sz * 0.35)
            ctx.show_text(char_str)

    ctx.restore()  # remove clip

    # 3. Outer Phosphor Edge / Fresnel Rim in Slime Aurora Gradient
    ctx.new_path()
    ctx.move_to(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        ctx.line_to(pt[0], pt[1])
    ctx.close_path()

    if c_blend > 0.05:
        rim_grad = cairo.LinearGradient(
            cx - r * sx, cy - r * sy,
            cx + r * sx, cy + r * sy
        )
        rim_grad.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.98)
        rim_grad.add_color_stop_rgba(0.22, SLIME_CYAN[0], SLIME_CYAN[1], SLIME_CYAN[2], 0.98)
        rim_grad.add_color_stop_rgba(0.58, SLIME_IRIS[0], SLIME_IRIS[1], SLIME_IRIS[2], 0.96)
        rim_grad.add_color_stop_rgba(1.00, SLIME_CORAL[0], SLIME_CORAL[1], SLIME_CORAL[2], 0.98)
        ctx.set_source(rim_grad)
    else:
        ctx.set_source_rgba(0.58, 0.82, 0.68, 0.85)
    ctx.set_line_width(max(3.4, r * 0.055))
    ctx.stroke()

    # 4. Pure White 3D Capsule Eyes Rig (#FFFFFF Solid Blocks + Soft Glow)
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
    pitch_arch = -math.sin(pitch) * r * 0.055 * sy

    gaze_dx = math.sin(yaw) * r * 0.50 * sx
    gaze_dy = math.sin(pitch) * r * 0.44 * sy

    cant_angle = gx_c * (-0.28 + 0.42 * gy_c)
    cos_c, sin_c = math.cos(cant_angle), math.sin(cant_angle)

    eye_sep = r * 0.235 * max(0.56, math.cos(yaw * 0.72))
    w_near = r * 0.132
    h_near = r * 0.285 * max(0.08, 1.0 - blink)

    for side in (-1, +1):
        c_eye = cos_L if side == -1 else cos_R
        persp_w = c_eye / max_cos
        persp_h = (0.82 + 0.18 * persp_w) * pitch_h
        w_eye = w_near * persp_w
        h_eye = h_near * persp_h

        local_x = side * eye_sep * (0.72 + 0.28 * persp_w)
        local_y = pitch_arch * (1.0 - persp_w)

        rot_lx = local_x * cos_c - local_y * sin_c
        rot_ly = local_x * sin_c + local_y * cos_c

        sp_x = gaze_dx + rot_lx
        sp_y = gaze_dy + rot_ly
        ex = cx + sp_x * cos_t - sp_y * sin_t
        ey = cy + sp_x * sin_t + sp_y * cos_t

        ctx.save()
        ctx.translate(ex, ey)
        ctx.rotate(coupled_tilt + cant_angle + side * gx_c * 0.03)

        if eye_mode == "sleep":
            draw_capsule_pill(ctx, 0, 0, w_eye * 1.15, max(1.8, h_eye * 0.18))
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.fill()
        elif eye_mode in ("happy", "happy_arc") or (eye_mode == "wink_right" and side == 1):
            arc_r = h_eye * 0.65
            arc_w = max(3.5, w_eye * 1.15)
            ctx.new_path()
            ctx.arc(0, arc_r * 0.3, arc_r, math.pi * 1.15, math.pi * 1.85)
            ctx.set_source_rgba(0.05, 0.08, 0.22, 0.85)
            ctx.set_line_width(arc_w + 4.0)
            ctx.stroke_preserve()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.set_line_width(arc_w)
            ctx.stroke()
        elif eye_mode == "focus":
            fw = w_eye * 1.55
            fh = max(2.5, w_eye * 0.52 * (1.0 - blink))
            draw_capsule_pill(ctx, 0, 0, fw + 3.0, fh + 3.0)
            ctx.set_source_rgba(0.02, 0.04, 0.14, 0.90)
            ctx.fill()
            draw_capsule_pill(ctx, 0, 0, fw + 1.2, fh + 1.2)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.45)
            ctx.fill()
            draw_capsule_pill(ctx, 0, 0, fw, fh)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.fill()
        elif eye_mode in ("wince", "charge"):
            dir_s = -side  # +1 for left eye (>), -1 for right eye (<)
            ww = w_eye * 1.45
            ctx.new_path()
            ctx.move_to(-dir_s * ww * 0.60, -h_eye * 0.45)
            ctx.line_to(dir_s * ww * 0.55, 0)
            ctx.line_to(-dir_s * ww * 0.60, h_eye * 0.45)
            ctx.set_source_rgba(0.05, 0.08, 0.22, 0.85)
            ctx.set_line_width(max(3.5, w_eye * 0.95) + 3.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.set_line_width(max(3.5, w_eye * 0.95))
            ctx.stroke()
        elif eye_mode == "sparkle":
            draw_four_point_star(ctx, 0, 0, h_eye * 0.85, w_eye * 0.4, rot=t * 2.0)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.fill()
        else:
            # Standard Pure White Capsule Eyes (#FFFFFF Solid + Soft White Glow)
            draw_capsule_pill(ctx, 0, 1.4, w_eye + 4.0, h_eye + 4.0)
            ctx.set_source_rgba(0.02, 0.04, 0.16, 0.95)
            ctx.fill()

            draw_capsule_pill(ctx, 0, 0, w_eye + 2.2, h_eye + 2.2)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.45)
            ctx.fill()

            draw_capsule_pill(ctx, 0, 0, w_eye, h_eye)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.fill()

        ctx.restore()

    ctx.restore()


# -----------------------------------------------------------------------------
# 5. REQUIRED API: draw_star
# -----------------------------------------------------------------------------
def draw_star(ctx: cairo.Context, cx: float, cy: float, r: float, *,
              rot: float = 0.0, t: float = 0.0, **style_kw):
    """
    Renders the Four-Point Sparkle Star (✦) in CRT ASCII Style:
    - 4-point concave Bezier star geometry.
    - Outer chromatic aura with Star-Spark Blue -> Iris Violet -> Coral Pink gradient.
    - Dense glowing ASCII characters (*, +, ✦, 0, 1) decorating the core and tips.
    """
    ctx.save()

    # 1. Radiant Outer Starlight Aura in Star-Spark Blue -> Iris -> Coral
    aura = cairo.RadialGradient(cx, cy, r * 0.1, cx, cy, r * 2.8)
    aura.add_color_stop_rgba(0.00, SLIME_CYAN[0], SLIME_CYAN[1], SLIME_CYAN[2], 0.90)
    aura.add_color_stop_rgba(0.38, SLIME_IRIS[0], SLIME_IRIS[1], SLIME_IRIS[2], 0.58)
    aura.add_color_stop_rgba(0.72, SLIME_CORAL[0], SLIME_CORAL[1], SLIME_CORAL[2], 0.30)
    aura.add_color_stop_rgba(1.00, SLIME_CORAL[0], SLIME_CORAL[1], SLIME_CORAL[2], 0.00)
    ctx.set_source(aura)
    ctx.arc(cx, cy, r * 2.8, 0, math.tau)
    ctx.fill()

    # 2. Signature 4-pointed Star Body with Slime 3-Color Ramp Fill
    draw_four_point_star(ctx, cx, cy, r, r * 0.26, rot=rot)
    star_grad = cairo.LinearGradient(
        cx - r * math.cos(rot), cy - r * math.sin(rot),
        cx + r * math.cos(rot), cy + r * math.sin(rot)
    )
    star_grad.add_color_stop_rgba(0.00, SLIME_CYAN[0], SLIME_CYAN[1], SLIME_CYAN[2], 1.00)
    star_grad.add_color_stop_rgba(0.45, SLIME_IRIS[0], SLIME_IRIS[1], SLIME_IRIS[2], 1.00)
    star_grad.add_color_stop_rgba(1.00, SLIME_CORAL[0], SLIME_CORAL[1], SLIME_CORAL[2], 1.00)
    ctx.set_source(star_grad)
    ctx.fill_preserve()

    # Crisp pure white highlight at the core
    draw_four_point_star(ctx, cx, cy, r * 0.42, r * 0.12, rot=rot)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.98)
    ctx.fill()

    # Crisp outer rim
    draw_four_point_star(ctx, cx, cy, r, r * 0.26, rot=rot)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.98)
    ctx.set_line_width(max(2.2, r * 0.09))
    ctx.stroke()

    # 3. Floating ASCII Sparkle Particles around ✦
    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    font_sz = max(11.0, r * 0.38)
    ctx.set_font_size(font_sz)

    sparkle_glyphs = ["✦", "*", "+", "1", "0", "°", "*"]
    for i in range(8):
        ang = rot + i * (math.tau / 8.0) + math.sin(t * 3.0 + i) * 0.2
        dist = r * (1.22 + 0.36 * math.cos(t * 2.5 + i * 1.3))
        px = cx + dist * math.cos(ang)
        py = cy + dist * math.sin(ang)
        g_idx = i % len(sparkle_glyphs)

        frac = i / 7.0
        if frac < 0.5:
            f = frac / 0.5
            cr = lerp(SLIME_CYAN[0], SLIME_IRIS[0], f)
            cg = lerp(SLIME_CYAN[1], SLIME_IRIS[1], f)
            cb = lerp(SLIME_CYAN[2], SLIME_IRIS[2], f)
        else:
            f = (frac - 0.5) / 0.5
            cr = lerp(SLIME_IRIS[0], SLIME_CORAL[0], f)
            cg = lerp(SLIME_IRIS[1], SLIME_CORAL[1], f)
            cb = lerp(SLIME_IRIS[2], SLIME_CORAL[2], f)

        ctx.set_source_rgba(cr, cg, cb, 0.95)
        ctx.move_to(px - font_sz * 0.35, py + font_sz * 0.35)
        ctx.show_text(sparkle_glyphs[g_idx])

    ctx.restore()


# -----------------------------------------------------------------------------
# 6. WORLD & V3/V4 FUSION CRT ENVIRONMENT RENDERING
# -----------------------------------------------------------------------------
def _draw_terminal_background_and_matrix_rain(ctx: cairo.Context, cam_x: float, cam_y: float, t: float):
    """
    Draws the deep phosphor-green CRT tube background, v3's dense Matrix binary/code rain
    (`0 1` vertical streams), central phosphor tube glow, and lower perspective floor grid.
    """
    # 1. Deep CRT phosphor-black base with subtle emerald ambient tint
    ctx.set_source_rgb(0.004, 0.018, 0.009)
    ctx.paint()

    # Large soft emerald phosphor ambient radial glow in the center of the CRT tube
    bg_glow = cairo.RadialGradient(W * 0.52, H * 0.48, 40.0, W * 0.52, H * 0.48, 760.0)
    bg_glow.add_color_stop_rgba(0.00, 0.00, 0.22, 0.10, 0.55)
    bg_glow.add_color_stop_rgba(0.55, 0.00, 0.12, 0.05, 0.35)
    bg_glow.add_color_stop_rgba(1.00, 0.00, 0.02, 0.01, 0.00)
    ctx.set_source(bg_glow)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # 2. v3 Dense Green Phosphor Matrix Code Rain (`0 1` & vertical character streams)
    ctx.save()
    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(14.0)

    col_w = 26
    row_h = 24
    num_rows = 36
    base_col_start = int((cam_x - W * 0.55) * 0.4) // col_w * col_w

    for idx_c in range(72):
        sx = 48 + idx_c * col_w
        if sx < 55 or sx > W - 55:
            continue

        seed_col = idx_c + int(base_col_start // col_w)
        rnd = random.Random(seed_col * 4999 + 17)
        speed = rnd.uniform(2.5, 6.0)
        head_row_1 = (rnd.uniform(0, num_rows) + t * speed) % num_rows
        head_row_2 = (head_row_1 + num_rows * 0.5) % num_rows
        col_active = rnd.random() < 0.88

        for r_idx in range(num_rows):
            sy = 115 + r_idx * row_h
            if sy > 985:
                break

            ch = MATRIX_CHARS[(seed_col * 31 + r_idx * 17) % len(MATRIX_CHARS)]

            # Distance behind raindrop head
            d1 = (head_row_1 - r_idx) % num_rows
            d2 = (head_row_2 - r_idx) % num_rows
            d_min = min(d1, d2)

            if col_active and d_min < 1.2:
                # Bright leading raindrop character
                ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.52)
            elif col_active and d_min < 11.0:
                # Glowing green matrix trail
                fade = 1.0 - (d_min / 11.0)
                alpha = 0.12 + 0.28 * (fade ** 1.3)
                ctx.set_source_rgba(PHOSPHOR_CORE[0], PHOSPHOR_CORE[1], PHOSPHOR_CORE[2], alpha)
            else:
                # Subtle background matrix lattice
                ctx.set_source_rgba(PHOSPHOR_DIM[0], PHOSPHOR_DIM[1], PHOSPHOR_DIM[2], 0.13)

            ctx.move_to(sx, sy)
            ctx.show_text(ch)
    ctx.restore()

    # 3. Lower CRT Perspective Grid (cyberspace floor horizon)
    ctx.save()
    ctx.set_line_width(1.1)
    for gy in range(700, 1020, 36):
        alpha = clamp(0.10 + 0.16 * ((gy - 700) / 320.0), 0.08, 0.26)
        ctx.set_source_rgba(PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], alpha)
        ctx.move_to(60, gy)
        ctx.line_to(W - 60, gy)
        ctx.stroke()

    horizon_x = W * 0.50 - (cam_x - 2850) * 0.12
    horizon_y = 540
    for ang_deg in range(-72, 75, 12):
        rad = math.radians(ang_deg)
        x_bottom = horizon_x + math.tan(rad) * 540
        ctx.set_source_rgba(PHOSPHOR_DIM[0], PHOSPHOR_DIM[1], PHOSPHOR_DIM[2], 0.16)
        ctx.move_to(horizon_x, horizon_y)
        ctx.line_to(x_bottom, 1020)
        ctx.stroke()
    ctx.restore()


def _draw_v3_crt_top_perspective_grid_and_status(ctx: cairo.Context, t: float):
    """
    Draws v3's signature curved CRT top perspective scan-grid lines, inner phosphor tube border,
    and the native top status bar (`STARDINO TTY0  PHOSPHOR P1/P31  80x25  9600 BAUD`).
    NO external bottom UI label!
    """
    ctx.save()

    # 1. Curved Top Perspective Scan-Grid Lines (v3 signature upper CRT ceiling grid)
    scan_ys = [92, 108, 126, 146, 168, 192, 218, 246]
    for idx, base_y in enumerate(scan_ys):
        frac = idx / float(len(scan_ys) - 1)
        alpha = lerp(0.68, 0.16, frac)
        lw = lerp(2.0, 1.0, frac)

        ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], alpha)
        ctx.set_line_width(lw)
        ctx.new_path()
        for step_i in range(41):
            u = step_i / 40.0
            px = lerp(76.0, W - 76.0, u)
            arch = -12.0 * (1.0 - ((u - 0.5) * 2.0) ** 2) * (1.0 - frac * 0.45)
            py = base_y + arch
            if step_i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.stroke()

    # Perspective ceiling ribs connecting the top scan-grid lines
    ctx.set_line_width(1.0)
    for rib_u in [0.14, 0.28, 0.40, 0.50, 0.60, 0.72, 0.86]:
        ctx.set_source_rgba(PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], 0.25)
        x_top = lerp(110.0, W - 110.0, rib_u)
        x_bot = lerp(W * 0.5, x_top, 1.16)
        ctx.move_to(x_top, 86.0)
        ctx.line_to(x_bot, 246.0)
        ctx.stroke()

    # 2. Top Status Bar Header Band (positioned safely inside the curved top CRT bezel)
    ctx.set_source_rgba(0.00, 0.14, 0.05, 0.82)
    ctx.rectangle(135, 50, W - 270, 32)
    ctx.fill()

    ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.85)
    ctx.set_line_width(1.8)
    ctx.move_to(135, 50)
    ctx.line_to(W - 135, 50)
    ctx.move_to(135, 82)
    ctx.line_to(W - 135, 82)
    ctx.stroke()

    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(15.5)
    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.98)
    ctx.move_to(165, 71)
    ctx.show_text("STARDINO TTY0   PHOSPHOR P1/P31   80x25   9600 BAUD   ATTN.HEADS=128")

    # Right side status pill: [ WAKE_SIGNAL ● ]
    ctx.move_to(W - 365, 71)
    ctx.show_text("[ WAKE_SIGNAL ● ]")

    # 3. Inner Glowing CRT Phosphor Tube Border
    ctx.set_source_rgba(PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], 0.65)
    ctx.set_line_width(2.4)
    ctx.rectangle(68, 44, W - 136, H - 88)
    ctx.stroke()

    ctx.restore()


def _draw_wake_prompt_and_logs(ctx: cairo.Context, cam_x: float, cam_y: float, t: float):
    """
    Draws v3's iconic bottom-left terminal prompt:
    `stardino@crt:~$ ./wake --curious` and the `[ OK ]` system wake logs.
    """
    base_x = 135.0 - (cam_x - 2850.0) * 0.35
    base_y = 790.0 - (cam_y - 540.0) * 0.35

    ctx.save()

    # Translucent dark terminal backing so the wake prompt pops with 100% clarity
    ctx.set_source_rgba(0.002, 0.028, 0.012, 0.84)
    ctx.rectangle(base_x - 16, base_y - 34, 665, 172)
    ctx.fill()

    ctx.set_source_rgba(PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], 0.55)
    ctx.set_line_width(1.4)
    ctx.rectangle(base_x - 16, base_y - 34, 665, 172)
    ctx.stroke()

    # Soft green phosphor bloom behind the main prompt line
    p_glow = cairo.RadialGradient(base_x + 210, base_y - 6, 10, base_x + 210, base_y - 6, 260)
    p_glow.add_color_stop_rgba(0.0, PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.28)
    p_glow.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
    ctx.set_source(p_glow)
    ctx.rectangle(base_x - 16, base_y - 34, 520, 56)
    ctx.fill()

    # Main Prompt: stardino@crt:~$ ./wake --curious
    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(22.0)
    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 1.0)
    prompt_str = "stardino@crt:~$ ./wake --curious"
    ctx.move_to(base_x, base_y)
    ctx.show_text(prompt_str)

    # Solid glowing block cursor █
    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.95)
    ctx.rectangle(base_x + 412, base_y - 18, 13, 21)
    ctx.fill()

    # System Wake Logs below prompt (v3 style)
    logs = [
        ("[ OK ]", "tensor_grid.mount     /dev/phosphor0    0x7FFE84A0"),
        ("[ OK ]", "sparkle.core          4-point satellite locked"),
        ("[ OK ]", "curiosity.daemon      spawning...       pid 0401"),
        ("01010011", "01010100 01000001 01010010 01000100 01001001 01001110 01001111  [STARDINO]"),
    ]
    ctx.set_font_size(14.5)
    for i, (tag, desc) in enumerate(logs):
        ly = base_y + 32 + i * 24
        ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.95)
        ctx.move_to(base_x, ly)
        ctx.show_text(tag)

        ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.84)
        ctx.move_to(base_x + (72 if tag == "[ OK ]" else 88), ly)
        ctx.show_text(desc)

    ctx.restore()


def _draw_code_stairway_and_springboard(ctx: cairo.Context, cam_x: float, cam_y: float, t: float):
    """
    Draws the ascending glowing green code staircase, the `[████████░░] 78%` progress bar
    springboard, the jump trajectory arc, and `Loading...` near the Star `✦`.
    Laid out with strict non-overlapping horizontal & vertical zones!
    """
    steps = [
        # Step 1: Lower-left intro step (screen x: 120..440, y: 695)
        {
            "x0": 2010, "x1": 2320, "y": 700,
            "lines": [
                "0101: // SEC_02: CODE_STAIRWAY",
                "0102: *spark = alloc_tensor(V5);",
                "0103: [========================]",
            ],
        },
        # Step 2: Progress Bar Springboard Step (screen x: 465..885, y: 600)
        {
            "x0": 2355, "x1": 2765, "y": 595,
            "lines": [
                "0104: tty_pulse_scanline(VBLANK_P1);",
                "0105: curiosity_vec += SPRING_BOOST;",
            ],
            "is_springboard": True,
        },
        # Step 3: Central Impact Step (where ERR_404 is smashed by Slime!)
        {
            "x0": 2670, "x1": 3050, "y": 575,
            "lines": [
                "0107: trap_irq(COLLISION, 0xFF84A0);",
                "0108: [==== << ERR_404_SMASH >> ====]",
            ],
            "is_impact": True,
        },
        # Step 4: Upper-right step (where ✦ hovers and Loading... floats cleanly above)
        {
            "x0": 3040, "x1": 3420, "y": 468,
            "lines": [
                "0110: route_to_gate(&star_satellite);",
                "0111: if (resonance > THRESHOLD) break;",
                "0112: [===============================]",
            ],
        },
        # Step 5: Threshold platform right below the Giant [ ENTER ↵ ] Key
        {
            "x0": 3430, "x1": 3760, "y": 500,
            "lines": [
                "0113: } // ENTER_KEY_PORTAL_READY >>",
                "0114: [===============================]",
            ],
        },
    ]

    ctx.save()
    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    font_sz = 14.5
    ctx.set_font_size(font_sz)
    line_h = 20.0

    for st in steps:
        sx0 = st["x0"] - cam_x + W * 0.5
        sx1 = st["x1"] - cam_x + W * 0.5
        sy = st["y"] - cam_y + H * 0.5

        # Vertical step riser guideline
        ctx.set_source_rgba(PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], 0.45)
        ctx.set_line_width(1.4)
        ctx.move_to(sx0 + 12, sy - 36)
        ctx.line_to(sx0 + 12, sy + 36)
        ctx.stroke()

        for i, text in enumerate(st["lines"]):
            line_y = sy - (len(st["lines"]) - 1 - i) * line_h

            if "=" in text:
                ctx.set_source_rgba(0.00, 0.28, 0.11, 0.80)
                ctx.rectangle(sx0 - 5, line_y - font_sz * 0.9, (sx1 - sx0) + 10, font_sz * 1.25)
                ctx.fill()
                ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.98)
            elif "//" in text:
                ctx.set_source_rgba(PHOSPHOR_CORE[0], PHOSPHOR_CORE[1], PHOSPHOR_CORE[2], 0.88)
            else:
                ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.95)

            ctx.move_to(sx0, line_y)
            ctx.show_text(text)

        # Draw prominent `[████████░░] 78%` Progress Bar Springboard on Step 2
        if st.get("is_springboard"):
            bar_y = sy + 24
            bar_w = 415
            bar_h = 28

            ctx.set_source_rgba(0.00, 0.22, 0.09, 0.92)
            ctx.rectangle(sx0 - 4, bar_y - 20, bar_w, bar_h)
            ctx.fill()
            ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.96)
            ctx.set_line_width(1.8)
            ctx.rectangle(sx0 - 4, bar_y - 20, bar_w, bar_h)
            ctx.stroke()

            ctx.set_font_size(15.0)
            ctx.move_to(sx0 + 4, bar_y - 1)
            ctx.show_text("SPRING: [")

            seg_x0 = sx0 + 90
            for seg_i in range(10):
                bx = seg_x0 + seg_i * 15
                if seg_i < 8:
                    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.98)
                    ctx.rectangle(bx, bar_y - 15, 12, 16)
                    ctx.fill()
                else:
                    ctx.set_source_rgba(PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], 0.65)
                    ctx.set_line_width(1.2)
                    ctx.rectangle(bx, bar_y - 15, 12, 16)
                    ctx.stroke()

            ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.98)
            ctx.move_to(seg_x0 + 154, bar_y - 1)
            ctx.show_text("] 78% [BOOST]")

            # ASCII Spring Coils underneath
            ctx.set_font_size(12.5)
            ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.88)
            ctx.move_to(sx0 + 6, bar_y + 22)
            ctx.show_text("/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\")
            ctx.move_to(sx0 + 6, bar_y + 35)
            ctx.show_text("\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/")

            # Parabolic jump arc from [████████░░] 78% springboard up to the Slime impact point
            p0_x, p0_y = sx0 + 210, bar_y - 24
            p1_x, p1_y = sx0 + 365, bar_y - 205
            p2_x, p2_y = (2850.0 - cam_x + W * 0.5) - 35, (505.0 - cam_y + H * 0.5) - 35
            for dot_i in range(1, 15):
                u_arc = dot_i / 15.0
                ax = (1 - u_arc) ** 2 * p0_x + 2 * (1 - u_arc) * u_arc * p1_x + (u_arc ** 2) * p2_x
                ay = (1 - u_arc) ** 2 * p0_y + 2 * (1 - u_arc) * u_arc * p1_y + (u_arc ** 2) * p2_y
                ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.35 + 0.45 * u_arc)
                ctx.arc(ax, ay, 2.2 if dot_i % 2 == 0 else 3.2, 0, math.tau)
                ctx.fill()

    # Floating Loading... text placed cleanly above Step 4 (zero overlap with 0110!)
    lx = 3040.0 - cam_x + W * 0.5
    ly = 382.0 - cam_y + H * 0.5
    ctx.set_font_size(14.5)
    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.96)
    ctx.move_to(lx, ly)
    ctx.show_text("Loading... [ 84.6% ]")
    ctx.set_font_size(12.0)
    ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.80)
    ctx.move_to(lx, ly + 17)
    ctx.show_text(">> SATELLITE_LOCKED >>")

    ctx.restore()


def _draw_giant_enter_key_portal(ctx: cairo.Context, cam_x: float, cam_y: float, t: float):
    """
    Draws the Giant 3D Isometric/ASCII `[ ENTER ↵ ]` Mechanical Key silhouette in the
    right distance (sitting cleanly above Step 5 with zero text collision).
    """
    kx = 3495.0 - cam_x + W * 0.5
    ky = 195.0 - cam_y + H * 0.5
    kw = 235.0
    kh = 195.0

    ctx.save()

    eglow = cairo.RadialGradient(kx + kw * 0.45, ky + kh * 0.5, 20.0, kx + kw * 0.45, ky + kh * 0.5, 200.0)
    eglow.add_color_stop_rgba(0.0, PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.25)
    eglow.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
    ctx.set_source(eglow)
    ctx.rectangle(kx - 45, ky - 45, kw + 90, kh + 130)
    ctx.fill()

    # 3D Keycap outer skirt
    ctx.set_source_rgba(0.00, 0.14, 0.06, 0.78)
    ctx.move_to(kx + 32, ky)
    ctx.line_to(kx + kw, ky)
    ctx.line_to(kx + kw + 20, ky + kh + 24)
    ctx.line_to(kx - 16, ky + kh + 24)
    ctx.line_to(kx - 16, ky + 72)
    ctx.line_to(kx + 32, ky + 72)
    ctx.close_path()
    ctx.fill_preserve()

    ctx.set_source_rgba(PHOSPHOR_MID[0], PHOSPHOR_MID[1], PHOSPHOR_MID[2], 0.78)
    ctx.set_line_width(2.0)
    ctx.stroke()

    # Top face of L-shaped Giant [ ENTER ↵ ] Keycap
    ctx.set_source_rgba(0.00, 0.22, 0.09, 0.88)
    ctx.move_to(kx + 42, ky + 12)
    ctx.line_to(kx + kw - 12, ky + 12)
    ctx.line_to(kx + kw - 12, ky + kh - 6)
    ctx.line_to(kx - 2, ky + kh - 6)
    ctx.line_to(kx - 2, ky + 82)
    ctx.line_to(kx + 42, ky + 82)
    ctx.close_path()
    ctx.fill_preserve()

    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.95)
    ctx.set_line_width(2.4)
    ctx.stroke()

    # Corner bevel struts
    ctx.set_line_width(1.4)
    ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.65)
    for (x1, y1, x2, y2) in [
        (kx + 42, ky + 12, kx + 32, ky),
        (kx + kw - 12, ky + 12, kx + kw, ky),
        (kx + kw - 12, ky + kh - 6, kx + kw + 20, ky + kh + 24),
        (kx - 2, ky + kh - 6, kx - 16, ky + kh + 24),
        (kx - 2, ky + 82, kx - 16, ky + 72),
    ]:
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()

    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12.0)
    ctx.set_source_rgba(PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.85)
    ctx.move_to(kx + 38, ky - 10)
    ctx.show_text("GATEWAY_03 // PIXEL_HOP")

    ctx.set_font_size(22.5)
    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.98)
    ctx.move_to(kx + 18, ky + 120)
    ctx.show_text("[ ENTER ↵ ]")

    # Giant vector return arrow ↵ inside the keycap (below the [ ENTER ↵ ] text!)
    ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.95)
    ctx.set_line_width(3.0)
    ax0, ay0 = kx + 195, ky + 42
    ctx.move_to(ax0, ay0)
    ctx.line_to(ax0, ay0 + 118)
    ctx.line_to(kx + 58, ay0 + 118)
    ctx.stroke()
    ctx.move_to(kx + 74, ay0 + 108)
    ctx.line_to(kx + 56, ay0 + 118)
    ctx.line_to(kx + 74, ay0 + 128)
    ctx.stroke()

    # Mechanical key switch springs underneath the keycap
    ctx.set_font_size(12.5)
    ctx.set_source_rgba(PHOSPHOR_CORE[0], PHOSPHOR_CORE[1], PHOSPHOR_CORE[2], 0.80)
    for sp_row in range(2):
        ctx.move_to(kx + 14, ky + kh + 40 + sp_row * 15)
        ctx.show_text("  [|||||]      [|||||]  ")

    ctx.restore()


def _draw_err_404_shattered_bg(ctx: cairo.Context, cam_x: float, cam_y: float,
                               impact_x: float = 2850.0, impact_y: float = 565.0):
    """Draws background shockwaves and radial ASCII burst behind the Slime."""
    sx = impact_x - cam_x + W * 0.5
    sy = impact_y - cam_y + H * 0.5

    ctx.save()

    # Concentric circular shockwave pulses
    for i, rad in enumerate([55.0, 105.0, 165.0, 235.0]):
        alpha = clamp(0.75 - i * 0.16, 0.12, 0.75)
        ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], alpha)
        ctx.set_line_width(max(1.4, 3.4 - i * 0.6))
        ctx.save()
        ctx.set_dash([16.0, 10.0], i * 6.0)
        ctx.arc(sx, sy - 20.0, rad, 0, math.tau)
        ctx.stroke()
        ctx.restore()

    # Impact flash core under the Slime's base
    flash = cairo.RadialGradient(sx, sy, 8.0, sx, sy, 125.0)
    flash.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.92)
    flash.add_color_stop_rgba(0.28, PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.78)
    flash.add_color_stop_rgba(0.65, PHOSPHOR_BRIGHT[0], PHOSPHOR_BRIGHT[1], PHOSPHOR_BRIGHT[2], 0.32)
    flash.add_color_stop_rgba(1.00, PHOSPHOR_CORE[0], PHOSPHOR_CORE[1], PHOSPHOR_CORE[2], 0.00)
    ctx.set_source(flash)
    ctx.arc(sx, sy, 125.0, 0, math.tau)
    ctx.fill()

    # Radial ASCII Shards Field
    rnd = random.Random(404)
    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(13.5)

    for i in range(56):
        ang = rnd.uniform(0, math.tau)
        dist = rnd.uniform(85.0, 275.0)
        px = sx + dist * math.cos(ang) * 1.25
        py = (sy - 30.0) + dist * math.sin(ang) * 0.85

        shard_ch = rnd.choice(ASCII_SHARDS)
        shard_alpha = clamp(1.0 - (dist / 295.0) ** 1.4, 0.22, 0.95)
        ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], shard_alpha)
        ctx.move_to(px, py)
        ctx.show_text(shard_ch)

    ctx.restore()


def _draw_err_404_shattered_fg(ctx: cairo.Context, cam_x: float, cam_y: float,
                               impact_x: float = 2850.0, impact_y: float = 565.0):
    """
    Draws flying shattered inverse-video chunks of `ERR_404` radiating around the Slime
    (positioned cleanly outside the 140px Slime contour so the Slime is 100% unobstructed).
    """
    sx = impact_x - cam_x + W * 0.5
    sy = impact_y - cam_y + H * 0.5

    ctx.save()
    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

    chunks = [
        {"txt": "[!] ERR_404", "dx": -168, "dy": -88,  "rot": -0.30, "w": 118, "h": 30},
        {"txt": "ERR_404",     "dx":  -52, "dy": -146, "rot":  0.16, "w":  86, "h": 30},
        {"txt": "NOT_FOUND",   "dx":  148, "dy": -82,  "rot":  0.34, "w": 106, "h": 30},
        {"txt": "[ ! ]",       "dx":  192, "dy":   8,  "rot":  0.52, "w":  54, "h": 28},
        {"txt": "CRITICAL",    "dx": -152, "dy":  36,  "rot": -0.42, "w":  96, "h": 28},
        {"txt": "0x00404",     "dx":  135, "dy":  64,  "rot":  0.28, "w":  86, "h": 26},
    ]

    ctx.set_font_size(14.5)
    for ck in chunks:
        cx = sx + ck["dx"]
        cy = sy + ck["dy"]
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(ck["rot"])

        # Inverted bright phosphor green block
        ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 0.98)
        ctx.rectangle(-ck["w"] * 0.5, -ck["h"] * 0.5, ck["w"], ck["h"])
        ctx.fill()

        # Dark cutout text inside inverted block
        ctx.set_source_rgb(0.00, 0.05, 0.02)
        ctx.move_to(-ck["w"] * 0.44, ck["h"] * 0.24)
        ctx.show_text(ck["txt"])

        # Crisp white-green highlight border
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
        ctx.set_line_width(1.8)
        ctx.rectangle(-ck["w"] * 0.5, -ck["h"] * 0.5, ck["w"], ck["h"])
        ctx.stroke()
        ctx.restore()

    # Large Flying Letters radiating outward
    large_glyphs = [
        ("E", -195, -145, -0.58, 32.0),
        ("R", -115, -182, -0.25, 34.0),
        ("R",   32, -195,  0.18, 35.0),
        ("_",  120, -165,  0.38, 30.0),
        ("4",  205, -125,  0.65, 35.0),
        ("0",  228,  -28,  0.80, 32.0),
        ("4",  188,   58,  0.98, 30.0),
    ]

    for ch, gx, gy, rot_g, sz in large_glyphs:
        ctx.save()
        ctx.translate(sx + gx, sy + gy)
        ctx.rotate(rot_g)
        ctx.set_font_size(sz)

        ctx.set_source_rgba(PHOSPHOR_CORE[0], PHOSPHOR_CORE[1], PHOSPHOR_CORE[2], 0.48)
        ctx.set_line_width(sz * 0.32)
        ctx.move_to(0, 0)
        ctx.line_to(-gx * 0.20, -gy * 0.20)
        ctx.stroke()

        ctx.set_source_rgba(PHOSPHOR_PEAK[0], PHOSPHOR_PEAK[1], PHOSPHOR_PEAK[2], 1.0)
        ctx.move_to(-sz * 0.3, sz * 0.35)
        ctx.show_text(ch)
        ctx.restore()

    ctx.restore()


# -----------------------------------------------------------------------------
# 7. POST-PROCESSING PIPELINE (CURVED CRT MONITOR BEZEL + BLOOM + SCANLINES)
# -----------------------------------------------------------------------------
def _apply_crt_post_processing(img: Image.Image) -> Image.Image:
    """
    Applies authentic curved CRT post-processing:
    1. Multi-scale Phosphor Bloom (bright-pass blur additive blend).
    2. Horizontal Scanlines raster.
    3. Curved CRT Barrel Distortion & Subtle Chromatic Aberration.
    4. Curved CRT Tube Vignette & 3D Molded Monitor Outer Bezel (no external UI text).
    """
    cache = _init_crt_distortion(W, H, k=0.042)
    arr = np.array(img, dtype=np.uint8)

    # --- Step 1: Phosphor Bloom ---
    lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).astype(np.float32)
    bright_mask = np.clip((lum - 48.0) / 185.0, 0.0, 1.0)
    bright_pixels = (arr.astype(np.float32) * bright_mask[:, :, None]).astype(np.uint8)

    bright_pil = Image.fromarray(bright_pixels, mode="RGB")
    bloom_narrow = bright_pil.filter(ImageFilter.BoxBlur(4))
    bloom_wide = bright_pil.filter(ImageFilter.BoxBlur(18))

    bloom_arr = (np.array(bloom_narrow, dtype=np.float32) * 0.58 +
                 np.array(bloom_wide, dtype=np.float32) * 0.48)

    arr_bloom = np.clip(arr.astype(np.float32) + bloom_arr * 1.05, 0.0, 255.0)

    # --- Step 2: Scanlines ---
    arr_scan = arr_bloom * cache["scanline"][:, :, None]

    # --- Step 3: Barrel Distortion & Chromatic Aberration via scipy.ndimage ---
    from scipy.ndimage import map_coordinates

    coords_y = cache["coords"][0]
    coords_x = cache["coords"][1]

    cx = W * 0.5
    edge_factor = np.clip((coords_x - cx) / cx, -1.0, 1.0)
    shift_r = coords_x + edge_factor * 1.4
    shift_b = coords_x - edge_factor * 1.4

    distorted = np.zeros((H, W, 3), dtype=np.float32)
    distorted[:, :, 0] = map_coordinates(arr_scan[:, :, 0], [coords_y, shift_r], order=1, mode='constant', cval=0)
    distorted[:, :, 1] = map_coordinates(arr_scan[:, :, 1], [coords_y, coords_x], order=1, mode='constant', cval=0)
    distorted[:, :, 2] = map_coordinates(arr_scan[:, :, 2], [coords_y, shift_b], order=1, mode='constant', cval=0)

    # --- Step 4: Curved CRT Glass Vignette & 3D Molded Monitor Outer Bezel ---
    distorted *= cache["vignette"][:, :, None]

    # Subtle curved glass reflection sheen inside the tube
    y_idx, x_idx = np.ogrid[:H, :W]
    sheen = 4.5 * np.exp(-((x_idx - W * 0.35) ** 2 / (2 * 450 ** 2) + (y_idx - H * 0.25) ** 2 / (2 * 260 ** 2)))
    distorted[:, :, 1] = np.clip(distorted[:, :, 1] + sheen * cache["screen_mask"], 0.0, 255.0)

    # Composite inside CRT glass with outer 3D molded monitor bezel
    sm = cache["screen_mask"][:, :, None]
    final_f = distorted * sm + cache["housing_rgb"] * (1.0 - sm)

    final_arr = np.clip(final_f, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(final_arr, mode="RGB")


apply_crt_postprocess = _apply_crt_post_processing


# -----------------------------------------------------------------------------
# 8. REQUIRED API: render_world
# -----------------------------------------------------------------------------
def render_world(cam_x: float, cam_y: float, t: float, state: Optional[Dict[str, Any]] = None) -> Image.Image:
    """
    Renders World 01 viewport into PIL.Image.Image (RGB, 1920x1080).
    Deterministic: identical (cam_x, cam_y, t, state) -> identical output.
    """
    if state is None:
        state = {}

    slime_x = state.get("slime_x", 2850.0)
    slime_y = state.get("slime_y", 505.0)
    slime_r = state.get("slime_radius", 70.0)   # ~140px base diameter (135~145px target!)
    squash_y = state.get("squash_y", 0.78)      # Impact squash on ERR_404
    tilt = state.get("tilt", -0.06)
    look = state.get("look", (0.62, -0.28))     # Look up-right towards ✦ ahead
    eye_mode = state.get("eye_mode", "pill")    # Pure white capsule eyes
    blink = state.get("blink", 0.0)

    star_x = state.get("star_x", 3185.0)        # Ahead on Step 4
    star_y = state.get("star_y", 350.0)
    star_r = state.get("star_radius", 38.0)
    star_rot = state.get("star_rot", 0.42)

    impact_active = state.get("impact_active", True)

    # 1. Create PyCairo 1920x1080 surface
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    # 2. Draw CRT Terminal Background & Dense Matrix Code Rain
    _draw_terminal_background_and_matrix_rain(ctx, cam_x, cam_y, t)

    # 3. Draw Distant Giant [ ENTER ↵ ] Key Silhouette on the right
    _draw_giant_enter_key_portal(ctx, cam_x, cam_y, t)

    # 4. Draw Code Stairway Platforms & [████████░░] 78% Springboard
    _draw_code_stairway_and_springboard(ctx, cam_x, cam_y, t)

    # 5. Draw Bottom-Left `stardino@crt:~$ ./wake --curious` Terminal Prompt & Logs
    _draw_wake_prompt_and_logs(ctx, cam_x, cam_y, t)

    # 6. Draw Shattered ERR_404 Background Shockwaves & Particles
    if impact_active:
        _draw_err_404_shattered_bg(ctx, cam_x, cam_y, impact_x=slime_x, impact_y=565.0)

    # 7. Draw Slime (Enlarged ~140px diameter, radiant ASCII aura + local ASCII matrix)
    s_screen_x = slime_x - cam_x + W * 0.5
    s_screen_y = slime_y - cam_y + H * 0.5
    draw_slime(
        ctx, s_screen_x, s_screen_y, slime_r,
        squash_y=squash_y, tilt=tilt,
        look=look, eye_mode=eye_mode,
        blink=blink, t=t
    )

    # 8. Draw Shattered ERR_404 Foreground Flying Chunks & Glyphs around Slime
    if impact_active:
        _draw_err_404_shattered_fg(ctx, cam_x, cam_y, impact_x=slime_x, impact_y=565.0)

    # 9. Draw Star ✦ ahead on higher step looking back
    st_screen_x = star_x - cam_x + W * 0.5
    st_screen_y = star_y - cam_y + H * 0.5
    draw_star(
        ctx, st_screen_x, st_screen_y, star_r,
        rot=star_rot, t=t
    )

    # Stardust trailing particles drifting back from Star to Slime
    ctx.save()
    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12.5)
    for i in range(14):
        frac = (i + 1) / 15.0
        tx = lerp(st_screen_x, s_screen_x + 78, frac)
        ty = lerp(st_screen_y, s_screen_y - 52, frac) + 16.0 * math.sin(frac * 6.5 + t * 2.2)
        if frac < 0.5:
            f = frac / 0.5
            col_r = lerp(SLIME_CYAN[0], SLIME_IRIS[0], f)
            col_g = lerp(SLIME_CYAN[1], SLIME_IRIS[1], f)
            col_b = lerp(SLIME_CYAN[2], SLIME_IRIS[2], f)
        else:
            f = (frac - 0.5) / 0.5
            col_r = lerp(SLIME_IRIS[0], SLIME_CORAL[0], f)
            col_g = lerp(SLIME_IRIS[1], SLIME_CORAL[1], f)
            col_b = lerp(SLIME_IRIS[2], SLIME_CORAL[2], f)

        ctx.set_source_rgba(col_r, col_g, col_b, 0.82 * (1.0 - frac * 0.35))
        ctx.move_to(tx, ty)
        ctx.show_text("✦" if i % 4 == 0 else ("*" if i % 2 == 0 else "+"))
    ctx.restore()

    # 10. Draw v3 Curved CRT Top Perspective Scan-Grid & Native Status Bar
    _draw_v3_crt_top_perspective_grid_and_status(ctx, t)

    # 11. Convert Cairo Surface to Pillow Image
    surface.flush()
    buf = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape((H, W, 4))
    rgb = buf[:, :, [2, 1, 0]].copy()
    base_pil = Image.fromarray(rgb, mode="RGB")

    # 12. Multi-pass Curved CRT Post-Processing
    final_img = _apply_crt_post_processing(base_pil)
    return final_img


# -----------------------------------------------------------------------------
# 9. REQUIRED API: render_keyframe
# -----------------------------------------------------------------------------
def render_keyframe() -> Image.Image:
    """
    Renders World 01 canonical keyframe:
    Fuses v3 curved CRT bezel/top scan-grid/Matrix rain/`stardino@crt:~$ ./wake --curious`
    with v4 code staircase, `[████████░░] 78%` springboard, smashing `ERR_404`,
    140px ASCII Slime, `✦` star, and distant `[ ENTER ↵ ]` portal key.
    """
    t_kf = 10.2
    cam_x = 2850.0
    cam_y = 540.0

    state = {
        "slime_x": 2850.0,
        "slime_y": 505.0,
        "slime_radius": 70.0,   # diameter = 140px (within 135~145px target!)
        "squash_y": 0.78,
        "tilt": -0.06,
        "look": (0.62, -0.28),
        "eye_mode": "pill",
        "blink": 0.0,
        "star_x": 3185.0,
        "star_y": 350.0,
        "star_radius": 38.0,
        "star_rot": 0.42,
        "impact_active": True,
    }

    return render_world(cam_x, cam_y, t_kf, state)


# -----------------------------------------------------------------------------
# 10. SCRIPT ENTRY
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "style_01_crt.png")
    print("[World 01 CRT] Rendering keyframe (1920x1080)...")
    img = render_keyframe()
    img.save(out_path, format="PNG")
    print(f"[World 01 CRT] Saved to {out_path}")
