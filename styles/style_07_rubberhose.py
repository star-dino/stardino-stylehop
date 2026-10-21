# -*- coding: utf-8 -*-
"""
StyleHop · World 07: 1930s 复古胶片橡皮管爵士舞台 (1930s Rubber-Hose Cartoon × Celluloid Jazz Stage)
====================================================================================================
融合 v3 复古暖米黄赛璐珞胶片质感、黄铜大喇叭留声机角色、3D 波浪钢琴键大道、绚丽 Technicolor 彩虹扩散光环
与 v4 故事瞬间（史莱姆踩扁捣蛋黑音符小怪化作彩星、留声机旁蹦跳音符小怪 ♪、留声机上方四角星芒 ✦）。

模块接口合同：
  - W, H = 1920, 1080
  - WORLD_W, WORLD_H = 7680, 1080
  - draw_star(ctx, cx, cy, r, *, rot=0.0, t=0.0, **style_kw)
  - draw_slime(ctx, cx, cy, radius, *, squash_y=1.0, tilt=0.0, look=(0.0, 0.0), eye_mode="pill", blink=0.0, t=0.0, **style_kw)
  - render_world(cam_x, cam_y, t, state=None) -> PIL.Image.Image
  - render_keyframe() -> PIL.Image.Image
"""

import os
import sys
import math
import random
import numpy as np
import cairo
from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from slime_engine import (
    SlimePose,
    compute_slime_contour,
    compute_3d_eye_projection,
    draw_slime_path,
    draw_four_point_star,
    draw_capsule_pill,
    cairo_to_pil,
)

# ---------------------------------------------------------------------------
# 规格合同常量 (Contract Constants)
# ---------------------------------------------------------------------------
W, H = 1920, 1080
WORLD_W, WORLD_H = 7680, 1080
OUT_PATH = os.path.join(REPO_ROOT, "styles", "style_07_rubberhose.png")

# 1930s Vintage Palette Constants
INK_BLACK = (0.118, 0.102, 0.090)          # #1E1A17 Deep India Ink
SEPIA_DARK = (0.24, 0.20, 0.16)            # Rich sepia shadow
SEPIA_MID = (0.55, 0.48, 0.40)             # Sepia tone
SEPIA_LIGHT = (0.82, 0.76, 0.66)           # Sepia tint
AGED_PAPER = (0.937, 0.902, 0.824)         # #EFE6D2 Warm Aged Paper
PAPER_CREAM = (0.97, 0.94, 0.88)           # Vintage paper highlight
BRASS_GOLD = (0.88, 0.72, 0.32)            # Vintage Gramophone Brass
BRASS_DARK = (0.48, 0.36, 0.16)            # Aged Brass Shadow
MAHOGANY = (0.36, 0.18, 0.12)              # Gramophone Wood Cabinet

# Technicolor 3-Strip Palette Constants (Inside the Jazz Wavefront)
TC_BLUE = (0.259, 0.522, 0.957)            # #4285F4 Gemini Sky Blue
TC_VIOLET = (0.545, 0.361, 0.965)          # #8B5CF6 Gemini Iris Violet
TC_CORAL = (0.878, 0.353, 0.392)           # #E05A64 Gemini Vintage Coral
TC_GOLD = (0.984, 0.749, 0.141)            # #FBBF24 Technicolor Warm Gold
TC_CYAN = (0.30, 0.82, 0.98)               # Technicolor Bright Cyan


def draw_rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float):
    """Draws a path for a rounded rectangle."""
    ctx.move_to(x + r, y)
    ctx.line_to(x + w - r, y)
    ctx.arc(x + w - r, y + r, r, -math.pi * 0.5, 0)
    ctx.line_to(x + w, y + h - r)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi * 0.5)
    ctx.line_to(x + r, y + h)
    ctx.arc(x + r, y + h - r, r, math.pi * 0.5, math.pi)
    ctx.line_to(x, y + r)
    ctx.arc(x + r, y + r, r, math.pi, math.pi * 1.5)
    ctx.close_path()


# ---------------------------------------------------------------------------
# API Contract 1: draw_star (1930s Rubber-Hose Technicolor 4-Point Star ✦)
# ---------------------------------------------------------------------------
def draw_star(ctx: cairo.Context, cx: float, cy: float, r: float, *, rot: float = 0.0, t: float = 0.0, **style_kw):
    """
    Renders a 1930s Rubber-Hose Technicolor 4-Point Concave Star (✦):
      - Luminous starlight halo aura
      - Double-ink vintage cartoon outline
      - Google Gemini Technicolor gradient (Sky Blue -> Iris Violet -> Coral -> Gold)
      - Vintage cartoon motion vibration ticks (( ✦ )) and sparkle rays
    """
    ctx.save()

    # 1. Starlight luminous halo aura
    star_aura = cairo.RadialGradient(cx, cy, max(1.0, r * 0.05), cx, cy, r * 2.1)
    star_aura.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.92)
    star_aura.add_color_stop_rgba(0.4, TC_GOLD[0], TC_GOLD[1], TC_GOLD[2], 0.62)
    star_aura.add_color_stop_rgba(1.0, TC_BLUE[0], TC_BLUE[1], TC_BLUE[2], 0.0)
    ctx.set_source(star_aura)
    ctx.arc(cx, cy, r * 2.1, 0, math.tau)
    ctx.fill()

    # 2. Double-ink drop outline for star
    draw_four_point_star(ctx, cx, cy, r, r * 0.26, rot=rot)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(max(4.5, r * 0.21))
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()

    # 3. Star fill: Google Gemini Technicolor gradient
    draw_four_point_star(ctx, cx, cy, r, r * 0.26, rot=rot)
    sg = cairo.LinearGradient(cx - r, cy - r, cx + r, cy + r)
    sg.add_color_stop_rgb(0.0, *TC_BLUE)
    sg.add_color_stop_rgb(0.48, *TC_VIOLET)
    sg.add_color_stop_rgb(0.85, *TC_CORAL)
    sg.add_color_stop_rgb(1.0, *TC_GOLD)
    ctx.set_source(sg)
    ctx.fill_preserve()
    ctx.set_source_rgb(*PAPER_CREAM)
    ctx.set_line_width(max(1.6, r * 0.06))
    ctx.stroke()

    # 4. Vintage cartoon motion vibration ticks: ( ✦ )
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(max(2.2, r * 0.08))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.arc(cx - r * 1.32, cy, r * 0.58, math.pi * 0.72, math.pi * 1.28)
    ctx.stroke()
    ctx.new_path()
    ctx.arc(cx + r * 1.32, cy, r * 0.58, -math.pi * 0.28, math.pi * 0.28)
    ctx.stroke()

    # 5. Vintage cartoon sparkle rays radiating from star
    for ray_ang, r_len_ratio in [(0.4, 0.42), (1.1, 0.52), (2.0, 0.46), (3.6, 0.56), (4.4, 0.44), (5.2, 0.48)]:
        ang = ray_ang + rot * 0.5
        r_start = r * 1.22
        r_len = r * r_len_ratio
        x1 = cx + r_start * math.cos(ang)
        y1 = cy + r_start * math.sin(ang)
        x2 = cx + (r_start + r_len) * math.cos(ang)
        y2 = cy + (r_start + r_len) * math.sin(ang)
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.set_source_rgb(*TC_GOLD)
        ctx.set_line_width(max(2.0, r * 0.07))
        ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# API Contract 2: draw_slime (1930s Rubber-Hose Ben-Day Halftone Slime)
# ---------------------------------------------------------------------------
def draw_slime(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    radius: float,
    *,
    squash_y: float = 1.0,
    tilt: float = 0.0,
    look: tuple = (0.52, -0.15),
    eye_mode: str = "pill",
    blink: float = 0.0,
    t: float = 0.0,
    **style_kw,
):
    """
    Renders the Star-Spark Slime translated into the 1930s Rubber-Hose Universe:
      - Organic 1930s hand-drawn boil & double-ink dip-pen contour
      - Google Gemini Technicolor gradient (Sky Blue #4285F4 -> Iris Violet #8B5CF6 -> Vintage Coral #E05A64)
      - Ben-Day halftone shading dots along the lower belly
      - MOUTHLESS: Two pure-white rounded 3D capsule eyes (-30 deg cant, far eye 81% width)
      - Optional overhead floating 4-point concave star (✦) with vibration ticks
    """
    ctx.save()

    look_x = look[0] if isinstance(look, (tuple, list)) else 0.52
    look_y = look[1] if isinstance(look, (tuple, list)) else -0.15

    pose = SlimePose(
        x=cx,
        y=cy,
        radius=radius,
        squash_y=max(0.25, squash_y),
        tilt=tilt,
        look_x=look_x,
        look_y=look_y,
        eye_scale=1.08,
        eye_mode=eye_mode,
        eye_cant=-0.5236,  # -30 degrees cant
        eye_spacing=1.02,
        left_eye_scale=(1.0, 1.0),
        right_eye_scale=(0.81, 0.92),  # 81% far eye width foreshortening!
        draw_shadow=True,
    )

    sy = pose.squash_y
    sx = 1.0 / math.sqrt(sy)
    R = pose.radius
    scale_ratio = R / 118.0

    # Compute contour points with organic 1930s hand-drawn boil
    pts = compute_slime_contour(pose, n_pts=108, boil_amp=1.6 * scale_ratio, boil_seed=1934)

    # 1. Soft Dynamic Contact Drop Shadow under surfing slime
    sh_x = cx - 10.0 * scale_ratio
    sh_y = cy + R * sy * 0.96
    ctx.save()
    ctx.translate(sh_x, sh_y)
    ctx.scale(R * sx * 1.08, R * 0.26)
    sh_grad = cairo.RadialGradient(0, 0, 0.05, 0, 0, 1.0)
    sh_grad.add_color_stop_rgba(0.0, 0.12, 0.08, 0.16, 0.65)
    sh_grad.add_color_stop_rgba(0.6, TC_VIOLET[0], TC_VIOLET[1], TC_VIOLET[2], 0.28)
    sh_grad.add_color_stop_rgba(1.0, 0.10, 0.08, 0.06, 0.0)
    ctx.set_source(sh_grad)
    ctx.arc(0, 0, 1.0, 0, math.tau)
    ctx.fill()
    ctx.restore()

    # 2. Outer vintage dip-pen double-ink contour underlay
    draw_slime_path(ctx, pts)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(max(6.0, 12.0 * scale_ratio))
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()

    # 3. Slime Body Fill: Lush 3-Strip Technicolor Google Gemini Gradient
    draw_slime_path(ctx, pts)
    grad = cairo.RadialGradient(
        cx - R * 0.38 * sx, cy - R * 0.40 * sy, R * 0.08,
        cx + R * 0.24 * sx, cy + R * 0.28 * sy, R * 1.28
    )
    grad.add_color_stop_rgb(0.00, 0.32, 0.68, 1.00)     # Luminous Sky Blue
    grad.add_color_stop_rgb(0.28, *TC_BLUE)              # Iconic Google Gemini Blue
    grad.add_color_stop_rgb(0.58, *TC_VIOLET)            # Gemini Iris Violet
    grad.add_color_stop_rgb(0.82, 0.76, 0.36, 0.78)     # Orchid Purple
    grad.add_color_stop_rgb(1.00, *TC_CORAL)             # Vintage Coral-Rose (#E05A64)
    ctx.set_source(grad)
    ctx.fill_preserve()

    # 4. Body Clip for Jelly Shading, Halftone Ben-Day Dots & Specular Gloss
    ctx.save()
    ctx.clip()

    # Warm Coral Subsurface Bounce Glow on lower right
    belly_g = cairo.RadialGradient(
        cx + R * 0.38 * sx, cy + R * 0.44 * sy, R * 0.05,
        cx + R * 0.22 * sx, cy + R * 0.32 * sy, R * 0.88
    )
    belly_g.add_color_stop_rgba(0.0, 0.98, 0.48, 0.54, 0.65)
    belly_g.add_color_stop_rgba(0.6, 0.86, 0.40, 0.78, 0.30)
    belly_g.add_color_stop_rgba(1.0, 0.55, 0.36, 0.92, 0.0)
    ctx.set_source(belly_g)
    ctx.arc(cx + R * 0.22 * sx, cy + R * 0.32 * sy, R * 0.88, 0, math.tau)
    ctx.fill()

    # 1930s Ben-Day Halftone Dot Screen on lower shaded crescent
    dot_spacing = max(6.0, 9.0 * scale_ratio)
    y_start = int(cy - R * sy * 0.1)
    y_end = int(cy + R * sy * 1.1)
    x_start = int(cx - R * sx * 0.9)
    x_end = int(cx + R * sx * 1.1)
    step = max(4, int(round(dot_spacing)))
    for dy_grid in range(y_start, y_end, step):
        for dx_grid in range(x_start, x_end, step):
            dist_c = math.hypot(dx_grid - (cx + R * 0.3 * sx), dy_grid - (cy + R * 0.4 * sy))
            if dist_c < R * 0.75:
                dot_r = max(0.8, min(3.8 * scale_ratio, (1.0 - dist_c / (R * 0.75)) * 4.2 * scale_ratio))
                ctx.arc(dx_grid, dy_grid, dot_r, 0, math.tau)
                ctx.set_source_rgba(0.18, 0.12, 0.28, 0.42)
                ctx.fill()

    # Translucent Jelly Fresnel Inner Rim Glow
    for lw_fr, alpha_fr in [(R * 0.16, 0.22), (R * 0.08, 0.42)]:
        draw_slime_path(ctx, pts)
        fr_g = cairo.LinearGradient(cx - R * sx, cy - R * sy, cx + R * sx, cy + R * sy)
        fr_g.add_color_stop_rgba(0.00, 0.55, 0.92, 1.00, alpha_fr)
        fr_g.add_color_stop_rgba(0.50, 0.65, 0.48, 0.98, alpha_fr * 0.6)
        fr_g.add_color_stop_rgba(1.00, 0.98, 0.55, 0.62, alpha_fr)
        ctx.set_source(fr_g)
        ctx.set_line_width(lw_fr)
        ctx.stroke()

    # 1930s Glossy Jelly Cartoon Highlight on upper-left dome (shifted with 3D gaze)
    ctx.save()
    ctx.translate(cx - R * (0.40 - look_x * 0.14) * sx, cy - R * (0.42 - look_y * 0.10) * sy)
    ctx.rotate(-0.55)
    ctx.scale(1.0, 0.42)
    spec_g = cairo.RadialGradient(0, 0, R * 0.02, 0, 0, R * 0.34)
    spec_g.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.85)
    spec_g.add_color_stop_rgba(0.5, 0.82, 0.95, 1.0, 0.45)
    spec_g.add_color_stop_rgba(1.0, 0.55, 0.82, 1.0, 0.0)
    ctx.set_source(spec_g)
    ctx.arc(0, 0, R * 0.34, 0, math.tau)
    ctx.fill()
    ctx.restore()

    ctx.restore()  # End body clip

    # 5. Crisp Vintage Double-Ink Contour Outline
    draw_slime_path(ctx, pts)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(max(3.8, 6.2 * scale_ratio))
    ctx.stroke()

    # 6. MOUTHLESS 3D SPHERICAL CAPSULE EYE SYSTEM (无嘴 + 纯白高光胶囊眼, C-infinity 3D projection)
    eye_proj = compute_3d_eye_projection(pose)
    blink_factor = max(0.08, 1.0 - float(blink))

    for side, espec in [(-1, eye_proj["left"]), (+1, eye_proj["right"])]:
        ex, ey = espec["x"], espec["y"]
        w_eye = espec["w"]
        h_eye = espec["h"] * blink_factor
        eye_rot = espec["angle"]

        ctx.save()
        ctx.translate(ex, ey)
        ctx.rotate(eye_rot)

        if eye_mode in ("happy", "happy_arc") or (eye_mode == "wink_right" and side == 1):
            # ^ ^ Happy cartoon arc eyes
            ctx.new_path()
            ctx.arc(0, h_eye * 0.2, w_eye * 0.95, math.pi * 1.12, math.pi * 1.88)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(max(5.0, w_eye * 0.85))
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.set_line_width(max(3.0, w_eye * 0.55))
            ctx.stroke()
        elif eye_mode in ("wince", "charge"):
            # > < 1930s cartoon effort / impact chevron eyes (left eye >, right eye <)
            dir_s = -side
            cw = w_eye * 1.35
            ch = h_eye * 0.52
            ctx.new_path()
            ctx.move_to(-dir_s * cw * 0.65, -ch * 0.70)
            ctx.line_to(dir_s * cw * 0.55, 0.0)
            ctx.line_to(-dir_s * cw * 0.65, ch * 0.70)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(max(5.4, w_eye * 0.90))
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.set_line_width(max(3.2, w_eye * 0.58))
            ctx.stroke()
        else:
            # Subtle dark drop shadow under white capsule eye
            draw_capsule_pill(ctx, 0, 2.0 * scale_ratio, w_eye + 2.5 * scale_ratio, h_eye + 2.5 * scale_ratio)
            ctx.set_source_rgba(0.12, 0.08, 0.18, 0.50)
            ctx.fill()

            # Pure-white rounded 3D capsule eye
            draw_capsule_pill(ctx, 0, 0, w_eye, h_eye)
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.fill_preserve()

            # Crisp vintage India ink eye contour
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(max(1.8, 2.6 * scale_ratio))
            ctx.stroke()

            # Pure white specular twinkle dot
            ctx.arc(-w_eye * 0.28, -h_eye * 0.38, max(2.0, w_eye * 0.32), 0, math.tau)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.fill()

        ctx.restore()

    # 7. Overhead Floating 4-Point Concave Satellite Star (✦) if requested (default True)
    if style_kw.get("draw_crown_star", True):
        star_cx = cx + 8.0 * scale_ratio
        star_cy = cy - R * sy - 50.0 * scale_ratio
        star_r = 36.0 * scale_ratio
        draw_star(ctx, star_cx, star_cy, star_r, rot=0.10, t=t)

    # Surfing speed swoosh arcs under the slime (only when explicitly requested)
    if style_kw.get("draw_swoosh", False):
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(max(2.2, 3.5 * scale_ratio))
        for sw_dy in [18 * scale_ratio, 32 * scale_ratio]:
            ctx.new_path()
            ctx.arc(cx - 28 * scale_ratio, cy + R * sy + sw_dy, 45.0 * scale_ratio, math.pi * 0.25, math.pi * 0.85)
            ctx.stroke()

    ctx.restore()


# ---------------------------------------------------------------------------
# Stage Environment & Story Elements (v3 Heritage + v4 Story Beats)
# ---------------------------------------------------------------------------
def draw_35mm_sprocket_borders(ctx: cairo.Context):
    """Draws authentic 1930s 35mm celluloid film margins with rounded sprocket holes."""
    border_w = 84.0
    sprocket_w = 34.0
    sprocket_h = 50.0
    sprocket_r = 7.0
    spacing = 76.0

    for bx in [0.0, W - border_w]:
        ctx.save()
        g = cairo.LinearGradient(bx, 0, bx + border_w, 0)
        g.add_color_stop_rgb(0.0, 0.09, 0.08, 0.07)
        g.add_color_stop_rgb(0.5, 0.13, 0.11, 0.10)
        g.add_color_stop_rgb(1.0, 0.08, 0.07, 0.06)
        ctx.set_source(g)
        ctx.rectangle(bx, 0, border_w, H)
        ctx.fill()

        ctx.set_source_rgba(0.28, 0.24, 0.20, 0.85)
        ctx.set_line_width(2.0)
        edge_x = border_w if bx == 0 else (W - border_w)
        ctx.move_to(edge_x, 0)
        ctx.line_to(edge_x, H)
        ctx.stroke()

        cx = bx + border_w * 0.5
        n_sprockets = int(H // spacing) + 2
        for i in range(n_sprockets):
            cy = 38.0 + i * spacing
            sx = cx - sprocket_w * 0.5
            sy = cy - sprocket_h * 0.5

            ctx.set_source_rgba(0.04, 0.03, 0.03, 0.95)
            ctx.new_path()
            draw_rounded_rect(ctx, sx - 1, sy - 1, sprocket_w + 2, sprocket_h + 2, sprocket_r)
            ctx.fill()

            hole_g = cairo.LinearGradient(sx, sy, sx + sprocket_w, sy + sprocket_h)
            hole_g.add_color_stop_rgb(0.0, 0.92, 0.88, 0.79)
            hole_g.add_color_stop_rgb(1.0, 0.86, 0.81, 0.71)
            ctx.set_source(hole_g)
            ctx.new_path()
            draw_rounded_rect(ctx, sx, sy, sprocket_w, sprocket_h, sprocket_r)
            ctx.fill()

            ctx.set_source_rgba(0.12, 0.10, 0.08, 0.35)
            ctx.set_line_width(1.5)
            ctx.new_path()
            draw_rounded_rect(ctx, sx, sy, sprocket_w, sprocket_h, sprocket_r)
            ctx.stroke()

        ctx.restore()


def draw_vintage_theater_curtains(ctx: cairo.Context, bounce_dy: float = 0.0, open_prog: float = 1.0):
    """
    Draws 1930s cartoon stage valance (pelmet) and left/right draped curtains.
    Supports full opening/closing choreography via `open_prog`:
      - open_prog = 0.0: Curtains 100% closed at center (x = 960), covering the entire stage with pleated velvet folds & gold fringe.
      - open_prog = 1.0: Curtains grandly drawn open and tied back at the left/right edges (x = 84 & x = 1836).
    """
    ctx.save()
    open_u = max(0.0, min(1.0, float(open_prog)))
    close_amt = 1.0 - open_u

    # 1. Left & Right Main Stage Velvet Curtains (drawn behind top scalloped pelmet)
    half_stage_w = (W - 168.0) * 0.5 + 4.0  # 880.0px so closed curtains overlap seamlessly at x=960
    for side, cx_edge, dir_sign in [(-1, 84.0, 1.0), (1, W - 84.0, -1.0)]:
        # Interpolate top, waist (sash tie-back), and bottom inner edge positions
        w_top = 180.0 * open_u + half_stage_w * close_amt
        w_waist = 56.0 * open_u + half_stage_w * (close_amt ** 1.15)
        w_bot = 4.0 * open_u + half_stage_w * (close_amt ** 0.88)
        y_bot = 590.0 * open_u + (H + 24.0) * (1.0 - open_u ** 1.6)
        sash_y = 420.0 + bounce_dy * 0.5

        x_top = cx_edge + dir_sign * w_top
        x_waist = cx_edge + dir_sign * w_waist
        x_bot = cx_edge + dir_sign * w_bot

        ctx.save()
        ctx.new_path()
        ctx.move_to(cx_edge, 0.0)
        ctx.line_to(x_top, 0.0)
        ctx.curve_to(
            cx_edge + dir_sign * (w_top * 0.96), 190.0,
            x_waist + dir_sign * (18.0 * open_u), sash_y - 40.0,
            x_waist, sash_y,
        )
        ctx.curve_to(
            x_waist - dir_sign * (14.0 * open_u), sash_y + 90.0,
            x_bot + dir_sign * (28.0 * close_amt), y_bot - 80.0,
            x_bot, y_bot,
        )
        ctx.line_to(cx_edge, y_bot)
        ctx.close_path()

        curt_g = cairo.LinearGradient(cx_edge, 0.0, cx_edge + dir_sign * max(180.0, w_top), 0.0)
        curt_g.add_color_stop_rgb(0.00, 0.13, 0.10, 0.08)
        curt_g.add_color_stop_rgb(0.45, 0.22, 0.17, 0.14)
        curt_g.add_color_stop_rgb(0.82, 0.17, 0.13, 0.11)
        curt_g.add_color_stop_rgb(1.00, 0.26, 0.20, 0.16)
        ctx.set_source(curt_g)
        ctx.fill_preserve()

        # Clip inside curtain panel to draw rich 1930s pleated velvet vertical folds
        ctx.save()
        ctx.clip()
        n_folds = 7
        for f_i in range(1, n_folds + 1):
            frac = f_i / float(n_folds + 1)
            fx_top = cx_edge + dir_sign * (w_top * frac)
            fx_waist = cx_edge + dir_sign * (w_waist * frac)
            fx_bot = cx_edge + dir_sign * (w_bot * frac)

            # Shaded velvet pleat valley
            ctx.new_path()
            ctx.move_to(fx_top, 0.0)
            ctx.curve_to(fx_top, 200.0, fx_waist, sash_y - 40.0, fx_waist, sash_y)
            ctx.curve_to(fx_waist, sash_y + 90.0, fx_bot, y_bot - 80.0, fx_bot, y_bot)
            ctx.set_source_rgba(0.06, 0.04, 0.03, 0.48)
            ctx.set_line_width(14.0 * (0.4 + 0.6 * close_amt))
            ctx.stroke()

            # Crisp dip-pen fold crease line
            ctx.new_path()
            ctx.move_to(fx_top, 0.0)
            ctx.curve_to(fx_top, 200.0, fx_waist, sash_y - 40.0, fx_waist, sash_y)
            ctx.curve_to(fx_waist, sash_y + 90.0, fx_bot, y_bot - 80.0, fx_bot, y_bot)
            ctx.set_source_rgba(INK_BLACK[0], INK_BLACK[1], INK_BLACK[2], 0.72)
            ctx.set_line_width(2.6)
            ctx.stroke()

        # Golden braided trim along the inner curtain edge
        ctx.new_path()
        ctx.move_to(x_top - dir_sign * 8.0, 0.0)
        ctx.curve_to(
            cx_edge + dir_sign * (w_top * 0.96 - 8.0), 190.0,
            x_waist + dir_sign * (18.0 * open_u - 8.0), sash_y - 40.0,
            x_waist - dir_sign * 8.0, sash_y,
        )
        ctx.curve_to(
            x_waist - dir_sign * (14.0 * open_u + 8.0), sash_y + 90.0,
            x_bot + dir_sign * (28.0 * close_amt - 8.0), y_bot - 80.0,
            x_bot - dir_sign * 8.0, y_bot,
        )
        ctx.set_source_rgba(0.85, 0.70, 0.36, 0.85)
        ctx.set_line_width(4.5)
        ctx.stroke()
        ctx.restore()  # End fold clip

        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(4.5)
        ctx.stroke()

        # Golden Sash Tie-Back Rope & Medallion
        sash_cx = cx_edge + dir_sign * (42.0 * open_u + 68.0 * close_amt)
        ctx.new_path()
        ctx.move_to(cx_edge, sash_y - 10.0)
        ctx.curve_to(cx_edge + dir_sign * 25.0, sash_y + 8.0, sash_cx - dir_sign * 15.0, sash_y + 6.0, x_waist, sash_y)
        ctx.set_source_rgb(0.82, 0.68, 0.35)
        ctx.set_line_width(8.0)
        ctx.stroke_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(2.2)
        ctx.stroke()

        ctx.arc(sash_cx, sash_y, 16.0, 0, math.tau)
        ctx.set_source_rgb(0.82, 0.68, 0.35)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(3.0)
        ctx.stroke()
        ctx.restore()

    # 2. Top Scalloped Valance (Pelmet) with Golden Tassels
    if bounce_dy != 0.0:
        ctx.translate(0.0, bounce_dy)
    pelmet_h = 135.0
    n_scallops = 16
    dx = (W - 168.0) / n_scallops

    ctx.new_path()
    ctx.move_to(84.0, -20.0)
    ctx.line_to(W - 84.0, -20.0)
    ctx.line_to(W - 84.0, 50.0)

    for i in range(n_scallops - 1, -1, -1):
        x_r = 84.0 + (i + 1) * dx
        x_l = 84.0 + i * dx
        y_bot = pelmet_h + 12.0 * math.sin(i * 0.8)
        ctx.curve_to(x_r - 10, y_bot, x_l + 10, y_bot, x_l, 45.0 + 8.0 * math.sin(i * 0.5))

    ctx.close_path()

    val_g = cairo.LinearGradient(0, 0, 0, pelmet_h + 15)
    val_g.add_color_stop_rgb(0.0, 0.16, 0.13, 0.11)
    val_g.add_color_stop_rgb(0.7, 0.22, 0.18, 0.15)
    val_g.add_color_stop_rgb(1.0, 0.12, 0.10, 0.08)
    ctx.set_source(val_g)
    ctx.fill_preserve()

    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(4.5)
    ctx.stroke()

    for i in range(n_scallops):
        xm = 84.0 + (i + 0.5) * dx
        ym = pelmet_h + 10.0 * math.sin(i * 0.8)

        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(2.0)
        ctx.move_to(xm, ym)
        ctx.line_to(xm, ym + 18.0)
        ctx.stroke()

        ctx.arc(xm, ym + 22.0, 5.0, 0, math.tau)
        ctx.set_source_rgb(0.78, 0.65, 0.38)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(2.0)
        ctx.stroke()

    for i in range(n_scallops + 1):
        xf = 84.0 + i * dx
        ctx.move_to(xf, 0)
        ctx.curve_to(xf - 8, 50, xf + 6, 90, xf, pelmet_h - 10)
        ctx.set_source_rgba(0.08, 0.06, 0.05, 0.65)
        ctx.set_line_width(3.0)
        ctx.stroke()

    ctx.restore()


def draw_stage_floorboards_and_spotlights(ctx: cairo.Context, pan_dx: float = 0.0):
    """Draws perspective cartoon wooden stage floorboards and dramatic 1930s conical spotlights."""
    ctx.save()

    # Base background: warm aged paper sky (#EFE6D2)
    sky_g = cairo.RadialGradient(960, 420, 100, 960, 420, 980)
    sky_g.add_color_stop_rgb(0.0, 0.965, 0.935, 0.865)
    sky_g.add_color_stop_rgb(0.65, 0.925, 0.885, 0.800)
    sky_g.add_color_stop_rgb(1.0, 0.840, 0.780, 0.680)
    ctx.set_source(sky_g)
    ctx.rectangle(84, 0, W - 168, H)
    ctx.fill()

    horizon_y = 620.0

    # Cartoon stage backdrop: faint musical staff waves
    ctx.set_source_rgba(0.72, 0.65, 0.54, 0.42)
    ctx.set_line_width(2.0)
    for staff_i in range(5):
        sy = horizon_y - 120.0 + staff_i * 18.0
        ctx.new_path()
        ctx.move_to(84, sy)
        ctx.curve_to(520, sy - 30, 1100, sy + 35, W - 84, sy - 15)
        ctx.stroke()

    # Stage floor perspective planks
    vanish_x, vanish_y = 1040.0 - pan_dx * 0.25, 480.0
    ctx.save()
    ctx.rectangle(84, horizon_y, W - 168, H - horizon_y)
    ctx.clip()

    floor_g = cairo.LinearGradient(0, horizon_y, 0, H)
    floor_g.add_color_stop_rgb(0.0, 0.85, 0.78, 0.66)
    floor_g.add_color_stop_rgb(1.0, 0.68, 0.58, 0.45)
    ctx.set_source(floor_g)
    ctx.paint()

    n_planks = 26
    for i in range(-8, n_planks + 9):
        bot_x = -200.0 + i * (W + 400.0) / n_planks - pan_dx
        ctx.move_to(vanish_x, vanish_y)
        ctx.line_to(bot_x, H + 50)
        ctx.set_source_rgba(0.22, 0.17, 0.13, 0.45)
        ctx.set_line_width(3.2)
        ctx.stroke()

        for step in [720, 840, 960]:
            t_p = (step - horizon_y) / (H - horizon_y)
            px = vanish_x + (bot_x - vanish_x) * t_p
            ctx.arc(px, step, 3.0, 0, math.tau)
            ctx.set_source_rgba(0.20, 0.15, 0.10, 0.35)
            ctx.fill()

    ctx.restore()

    # Dual 1930s Stage Spotlights
    spot1 = cairo.RadialGradient(280, 80, 40, 680, 580, 420)
    spot1.add_color_stop_rgba(0.0, 1.0, 0.98, 0.88, 0.42)
    spot1.add_color_stop_rgba(0.5, 1.0, 0.95, 0.82, 0.22)
    spot1.add_color_stop_rgba(1.0, 1.0, 0.92, 0.75, 0.0)
    ctx.set_source(spot1)
    ctx.new_path()
    ctx.move_to(220, 0)
    ctx.line_to(340, 0)
    ctx.line_to(980, 920)
    ctx.line_to(380, 920)
    ctx.close_path()
    ctx.fill()

    spot2 = cairo.RadialGradient(1620, 80, 40, 1380, 560, 440)
    spot2.add_color_stop_rgba(0.0, 1.0, 0.98, 0.88, 0.38)
    spot2.add_color_stop_rgba(0.5, 1.0, 0.95, 0.80, 0.18)
    spot2.add_color_stop_rgba(1.0, 1.0, 0.90, 0.72, 0.0)
    ctx.set_source(spot2)
    ctx.new_path()
    ctx.move_to(1560, 0)
    ctx.line_to(1680, 0)
    ctx.line_to(1750, 920)
    ctx.line_to(1080, 920)
    ctx.close_path()
    ctx.fill()

    ctx.restore()


def draw_rubber_hose_piano_keyboard(
    ctx: cairo.Context,
    slime_cx: float,
    slime_cy: float,
    ring_r: float,
    pan_dx: float = 0.0,
    slime_foot_y: float = None,
    critter_contacts: list = None,
):
    """
    Renders the sweeping S-curved undulating 3D rubber-hose piano keyboard.
    Keys under the slime or critter are elastic and squashed ONLY when physically contacted;
    inside the Technicolor ring they reflect vivid hues!
    """
    ctx.save()

    spine_control_pts = [
        (84.0 - pan_dx, 1050.0),
        (280.0 - pan_dx, 930.0),
        (520.0 - pan_dx, 765.0),
        (680.0 - pan_dx, 680.0),     # Slime trampoline rebound dip
        (840.0 - pan_dx, 660.0),     # Rising swing arc
        (1120.0 - pan_dx, 690.0),    # Descending toward gramophone
        (1340.0 - pan_dx, 730.0),    # Approaching gramophone cabinet base
        (1480.0 - pan_dx, 750.0),
    ]

    def eval_bezier(t_val):
        n = len(spine_control_pts) - 1
        idx = min(n - 1, max(0, int(t_val * n)))
        local_t = t_val * n - idx
        p0 = spine_control_pts[max(0, idx - 1)]
        p1 = spine_control_pts[idx]
        p2 = spine_control_pts[min(n, idx + 1)]
        p3 = spine_control_pts[min(n, idx + 2)]
        tt = local_t * local_t
        ttt = tt * local_t
        x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * local_t +
                   (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * tt +
                   (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * ttt)
        y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * local_t +
                   (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * tt +
                   (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * ttt)
        return x, y

    n_keys = 46
    key_geom = []
    max_rebound_dip = 0.0
    for k in range(n_keys):
        t0 = k / float(n_keys)
        t1 = (k + 0.92) / float(n_keys)
        x0, y0 = eval_bezier(t0)
        x1, y1 = eval_bezier(t1)

        dx, dy = x1 - x0, y1 - y0
        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-4:
            nx, ny = 0.0, -1.0
        else:
            nx, ny = -dy / seg_len, dx / seg_len

        depth_scale = 1.0 - 0.48 * t0
        key_length = 135.0 * depth_scale

        k_mid_x = (x0 + x1) * 0.5
        k_mid_y = (y0 + y1) * 0.5
        k_center_x = k_mid_x + nx * key_length * 0.5
        k_center_y = k_mid_y + ny * key_length * 0.5

        # Precise physical key compression: ONLY compress when foot_y is within contact range of the key center!
        rebound_dip = 0.0
        if slime_foot_y is not None:
            dx_foot = abs(k_center_x - slime_cx)
            dy_foot = abs(k_center_y - slime_foot_y)
            if dx_foot < 62.0 and dy_foot < 26.0:
                rebound_dip = (1.0 - dx_foot / 62.0) * (1.0 - dy_foot / 26.0) * 18.0
        else:
            dx_slime = abs(k_center_x - slime_cx)
            dy_slime = abs(k_center_y - (slime_cy + 55.0))
            if dx_slime < 62.0 and dy_slime < 26.0:
                rebound_dip = (1.0 - dx_slime / 62.0) * (1.0 - dy_slime / 26.0) * 18.0

        if critter_contacts:
            for cx_c, cy_c in critter_contacts:
                dx_c = abs(k_center_x - cx_c)
                dy_c = abs(k_center_y - cy_c)
                if dx_c < 40.0 and dy_c < 22.0:
                    c_dip = (1.0 - dx_c / 40.0) * 10.0
                    rebound_dip = max(rebound_dip, c_dip)

        if rebound_dip > max_rebound_dip:
            max_rebound_dip = rebound_dip

        p_back = ((x0 + x1) * 0.5, (y0 + y1) * 0.5 + rebound_dip)
        p_front = (p_back[0] + nx * key_length, p_back[1] + ny * key_length)

        w_half = seg_len * 0.55
        tx, ty = dx / max(1e-4, seg_len), dy / max(1e-4, seg_len)

        c_tl = (p_back[0] - tx * w_half, p_back[1] - ty * w_half)
        c_tr = (p_back[0] + tx * w_half, p_back[1] + ty * w_half)
        c_br = (p_front[0] + tx * w_half * 1.15, p_front[1] + ty * w_half * 1.15)
        c_bl = (p_front[0] - tx * w_half * 1.15, p_front[1] - ty * w_half * 1.15)

        key_geom.append({
            "idx": k,
            "center": ((p_back[0] + p_front[0]) * 0.5, (p_back[1] + p_front[1]) * 0.5),
            "corners": [c_bl, c_br, c_tr, c_tl],
            "is_black": (k % 7) in (1, 2, 4, 5, 6) and (k % 14 != 0),
            "depth_scale": depth_scale,
            "dist_to_slime": math.hypot(k_mid_x - slime_cx, k_mid_y - slime_cy),
            "rebound_dip": rebound_dip,
        })

    # Drop shadow under keyboard
    ctx.set_source_rgba(0.12, 0.08, 0.06, 0.38)
    for kg in key_geom:
        ctx.new_path()
        pts = kg["corners"]
        ctx.move_to(pts[0][0] + 8, pts[0][1] + 18)
        ctx.line_to(pts[1][0] + 8, pts[1][1] + 18)
        ctx.line_to(pts[2][0] + 8, pts[2][1] + 18)
        ctx.line_to(pts[3][0] + 8, pts[3][1] + 18)
        ctx.close_path()
        ctx.fill()

    # White Keys
    for kg in key_geom:
        pts = kg["corners"]
        kc_x, kc_y = kg["center"]
        d_slime = math.hypot(kc_x - slime_cx, kc_y - slime_cy)

        ctx.new_path()
        ctx.move_to(pts[0][0], pts[0][1])
        ctx.line_to(pts[1][0], pts[1][1])
        ctx.line_to(pts[2][0], pts[2][1])
        ctx.line_to(pts[3][0], pts[3][1])
        ctx.close_path()

        if ring_r > 5.0 and d_slime < ring_r:
            blend = max(0.0, 1.0 - d_slime / ring_r)
            r = 0.95 + 0.05 * math.sin(kg["idx"] * 0.6)
            g = 0.90 + 0.08 * math.cos(kg["idx"] * 0.4)
            b = 0.96 + 0.04 * math.sin(kg["idx"] * 0.8)
            col_r = r * (1.0 - blend * 0.38) + TC_BLUE[0] * (blend * 0.38)
            col_g = g * (1.0 - blend * 0.38) + TC_VIOLET[1] * (blend * 0.38)
            col_b = b * (1.0 - blend * 0.38) + TC_CORAL[2] * (blend * 0.38)
            ctx.set_source_rgb(col_r, col_g, col_b)
        else:
            ivory = 0.94 - 0.08 * (kg["idx"] % 3 == 0)
            ctx.set_source_rgb(ivory, ivory * 0.96, ivory * 0.88)

        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(3.2 * kg["depth_scale"] + 0.8)
        ctx.stroke()

        ctx.move_to(pts[0][0], pts[0][1])
        ctx.line_to(pts[1][0], pts[1][1])
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.75)
        ctx.set_line_width(2.0)
        ctx.stroke()

    # Black Keys (Accidentals)
    for kg in key_geom:
        if not kg["is_black"]:
            continue
        pts = kg["corners"]
        kc_x, kc_y = kg["center"]
        d_slime = math.hypot(kc_x - slime_cx, kc_y - slime_cy)

        bk_tl = pts[3]
        bk_tr = pts[2]
        bk_br = (pts[2][0] * 0.38 + pts[1][0] * 0.62, pts[2][1] * 0.38 + pts[1][1] * 0.62)
        bk_bl = (pts[3][0] * 0.38 + pts[0][0] * 0.62, pts[3][1] * 0.38 + pts[0][1] * 0.62)

        ctx.set_source_rgba(0.10, 0.08, 0.06, 0.55)
        ctx.new_path()
        ctx.move_to(bk_bl[0] + 4, bk_bl[1] + 5)
        ctx.line_to(bk_br[0] + 4, bk_br[1] + 5)
        ctx.line_to(bk_tr[0] + 4, bk_tr[1] + 5)
        ctx.line_to(bk_tl[0] + 4, bk_tl[1] + 5)
        ctx.close_path()
        ctx.fill()

        ctx.new_path()
        ctx.move_to(bk_bl[0], bk_bl[1])
        ctx.line_to(bk_br[0], bk_br[1])
        ctx.line_to(bk_tr[0], bk_tr[1])
        ctx.line_to(bk_tl[0], bk_tl[1])
        ctx.close_path()

        if ring_r > 5.0 and d_slime < ring_r:
            ctx.set_source_rgb(0.18, 0.12, 0.34)
        else:
            ctx.set_source_rgb(0.12, 0.10, 0.09)

        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(2.8 * kg["depth_scale"] + 0.6)
        ctx.stroke()

        ctx.move_to(bk_tl[0] + (bk_tr[0] - bk_tl[0]) * 0.3, bk_tl[1] + (bk_tr[1] - bk_tl[1]) * 0.3)
        ctx.line_to(bk_bl[0] + (bk_br[0] - bk_bl[0]) * 0.3, bk_bl[1] + (bk_br[1] - bk_bl[1]) * 0.3)
        ctx.set_source_rgba(0.75, 0.82, 0.95, 0.45 if (ring_r > 5.0 and d_slime < ring_r) else 0.25)
        ctx.set_line_width(1.8)
        ctx.stroke()

    # Trampoline bouncy vibration action ticks ONLY when actually compressing the keyboard
    if max_rebound_dip > 4.0:
        eff_foot_y = slime_foot_y if slime_foot_y is not None else (slime_cy + 55.0)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(3.0)
        for tick_off in [-48, -24, 0, 24, 48]:
            tx_b = slime_cx + tick_off * 1.3
            ty_b = eff_foot_y + abs(tick_off) * 0.18 + 14.0
            ctx.arc(tx_b, ty_b, 14.0, math.pi * 0.2, math.pi * 0.8)
            ctx.stroke()

    ctx.restore()


def draw_cartoon_glove(ctx: cairo.Context, gx: float, gy: float, rot: float = 0.0, flip: bool = False):
    """Draws an authentic 1930s 4-finger white cartoon glove with 3 black back-darts and rolled wrist cuff."""
    ctx.save()
    ctx.translate(gx, gy)
    ctx.rotate(rot)
    if flip:
        ctx.scale(-1.0, 1.0)

    ctx.save()
    ctx.scale(1.2, 0.65)
    ctx.arc(0, 0, 16.0, 0, math.tau)
    ctx.set_source_rgb(*PAPER_CREAM)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(3.2)
    ctx.stroke()
    ctx.restore()

    ctx.new_path()
    ctx.arc(0, 16.0, 18.0, 0, math.tau)
    ctx.set_source_rgb(*PAPER_CREAM)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(3.2)
    ctx.stroke()

    finger_angles = [-0.65, -0.22, 0.22, 0.65]
    finger_lengths = [22.0, 26.0, 24.0, 18.0]
    for fa, fl in zip(finger_angles, finger_lengths):
        fx = fl * math.sin(fa)
        fy = 16.0 + fl * math.cos(fa)
        ctx.new_path()
        ctx.arc(fx, fy, 8.5, 0, math.tau)
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(3.0)
        ctx.stroke()

    ctx.arc(0, 16.0, 16.0, 0, math.tau)
    ctx.set_source_rgb(*PAPER_CREAM)
    ctx.fill()

    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(2.5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for dart_dx in [-7.0, 0.0, 7.0]:
        ctx.move_to(dart_dx, 8.0)
        ctx.line_to(dart_dx * 1.15, 20.0)
        ctx.stroke()

    ctx.restore()


def draw_rubber_hose_gramophone(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    scale: float = 1.0,
    bounce_phase: float = 0.0,
    pan_dx: float = 0.0,
    stunned: bool = False,
    recoil_angle: float = 0.0,
    vortex_strength: float = 0.0,
    arm_action: float = 1.0,
    t: float = 0.0,
    boss_state: dict = None,
):
    """
    Renders the giant anthropomorphic 1930s Rubber-Hose Brass Gramophone Horn on the right:
      - Bending noodle brass neck & lively cartoon bounce
      - Expressive giant flared brass horn bell pointing leftward toward the slime
      - Singing mouth throat with vibrating cartoon tongue
      - Classic 1930s 4-finger white cartoon gloves with 3 black back-darts
      - Native eye states (Pie-cut Pac-Man, angry V-brows, inhale-squint, or rotating X X dizzy eyes)
      - Dynamic leftward propagating soundwave blast rings
      - Violent golden logarithmic reverse vacuum vortex when vortex_strength > 0!
      - 1930s Comic impact starburst (CLANG!) when impact_flash > 0!
    """
    if boss_state is None:
        boss_state = {}

    eye_state = boss_state.get("eye_state", "dizzy_x" if stunned else "normal")
    cab_squash_y = boss_state.get("cab_squash_y", 1.0 - 0.08 * math.sin(bounce_phase * math.pi))
    foot_tap_angle = boss_state.get("foot_tap_angle", math.sin(t * (132.0 / 60.0) * math.tau) * 0.18)
    record_rot = boss_state.get("record_rot", t * 8.0)
    crank_rot = boss_state.get("crank_rot", t * 5.0)
    neck_lean_x = boss_state.get("neck_lean_x", 0.0)
    neck_stretch_y = boss_state.get("neck_stretch_y", 0.0)
    horn_squash_x = boss_state.get("horn_squash_x", 1.0)
    horn_squash_y = boss_state.get("horn_squash_y", 1.0)
    tongue_wag = boss_state.get("tongue_wag", math.sin(t * 12.0))
    inhale_stream = boss_state.get("inhale_stream", 0.0)
    spit_blast = boss_state.get("spit_blast", 0.0)
    impact_flash = boss_state.get("impact_flash", 0.0)
    arm1_pose = boss_state.get("arm1_pose", "point" if not stunned else "dizzy")
    arm2_pose = boss_state.get("arm2_pose", "crank" if not stunned else "dizzy")

    ctx.save()

    if pan_dx != 0.0:
        ctx.translate(-pan_dx, 0.0)

    # Base pivot for scale and recoil
    pivot_x = cx + 20.0
    pivot_y = cy + 220.0
    if scale != 1.0 or recoil_angle != 0.0:
        ctx.translate(pivot_x, pivot_y)
        if scale != 1.0:
            ctx.scale(scale, scale)
        if recoil_angle != 0.0:
            ctx.rotate(recoil_angle)
        ctx.translate(-pivot_x, -pivot_y)

    # Dynamic cabinet dimensions based on cab_squash_y (preserving volume)
    cab_w = 240.0 / max(0.4, cab_squash_y ** 0.5)
    cab_h = 110.0 * cab_squash_y
    cab_base_y = cy + 220.0 + 55.0
    cab_cy = cab_base_y - cab_h * 0.5
    cab_cx = cx + 20.0

    # Drop shadow on floor
    ctx.set_source_rgba(0.12, 0.08, 0.06, 0.42)
    ctx.new_path()
    ctx.save()
    ctx.translate(cab_cx, cab_base_y + 8)
    ctx.scale(1.0, 0.36)
    ctx.arc(0, 0, 155.0, 0, math.tau)
    ctx.fill()
    ctx.restore()

    # Cartoon rubber-hose feet with tapping left shoe
    for foot_x, foot_sign, is_tap in [(cab_cx - 85.0, -1, True), (cab_cx + 85.0, 1, False)]:
        foot_ang = foot_tap_angle if is_tap else 0.0
        ctx.new_path()
        ctx.move_to(foot_x, cab_cy + cab_h * 0.5 - 10)
        ctx.curve_to(foot_x + foot_sign * 18, cab_cy + cab_h * 0.5 + 24,
                     foot_x - foot_sign * 10, cab_cy + cab_h * 0.5 + 45,
                     foot_x + foot_sign * 8, cab_cy + cab_h * 0.5 + 50)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(12.0)
        ctx.stroke()

        ctx.save()
        ctx.translate(foot_x + foot_sign * 8, cab_cy + cab_h * 0.5 + 50)
        if is_tap and foot_ang != 0.0:
            ctx.rotate(foot_ang)
        ctx.scale(1.35, 0.82)
        ctx.arc(0, 0, 16.0, 0, math.tau)
        ctx.set_source_rgb(0.15, 0.13, 0.11)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(3.2)
        ctx.stroke()
        # Shoe highlight
        ctx.arc(-4, -4, 4.0, 0, math.tau)
        ctx.set_source_rgba(0.9, 0.88, 0.80, 0.6)
        ctx.fill()
        ctx.restore()

        # Shoe tap dust / rhythm tick
        if is_tap and foot_ang > 0.08:
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(2.5)
            ctx.arc(foot_x + foot_sign * 28, cab_cy + cab_h * 0.5 + 46, 8.0, -0.4, 0.4)
            ctx.stroke()

    # Wooden Cabinet Body
    cab_rect = [cab_cx - cab_w * 0.5, cab_cy - cab_h * 0.5, cab_w, cab_h]
    draw_rounded_rect(ctx, cab_rect[0], cab_rect[1], cab_rect[2], cab_rect[3], 14.0)
    wood_g = cairo.LinearGradient(cab_rect[0], 0, cab_rect[0] + cab_w, 0)
    wood_g.add_color_stop_rgb(0.0, 0.48, 0.24, 0.16)
    wood_g.add_color_stop_rgb(0.5, 0.62, 0.32, 0.20)
    wood_g.add_color_stop_rgb(1.0, 0.38, 0.18, 0.12)
    ctx.set_source(wood_g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(5.0)
    ctx.stroke()

    # Brass decorative corner brackets
    ctx.set_source_rgb(*BRASS_GOLD)
    for bx, by in [
        (cab_rect[0] + 16, cab_rect[1] + 16),
        (cab_rect[0] + cab_w - 16, cab_rect[1] + 16),
        (cab_rect[0] + 16, cab_rect[1] + cab_h - 16),
        (cab_rect[0] + cab_w - 16, cab_rect[1] + cab_h - 16),
    ]:
        ctx.arc(bx, by, 6.0, 0, math.tau)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(2.0)
        ctx.stroke()
        ctx.set_source_rgb(*BRASS_GOLD)

    # Turntable disc & Vinyl record on top
    tt_cx, tt_cy = cab_cx - 15.0, cab_cy - cab_h * 0.5 - 12.0
    ctx.save()
    ctx.translate(tt_cx, tt_cy)
    ctx.scale(1.0, 0.32)
    # Turntable felt rim
    ctx.arc(0, 0, 92.0, 0, math.tau)
    ctx.set_source_rgb(0.20, 0.42, 0.30)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(6.0)
    ctx.stroke()

    # Vinyl disc
    ctx.arc(0, 0, 86.0, 0, math.tau)
    ctx.set_source_rgb(0.12, 0.11, 0.10)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(4.0)
    ctx.stroke()

    # Grooves
    for vr in [48.0, 62.0, 74.0]:
        ctx.arc(0, 0, vr, 0, math.tau)
        ctx.set_source_rgba(0.85, 0.85, 0.85, 0.22)
        ctx.set_line_width(2.2)
        ctx.stroke()

    # Rotating Golden Sheen Sectors (78 RPM spin feedback!)
    for sheen_ang in [record_rot, record_rot + math.pi]:
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.arc(0, 0, 84.0, sheen_ang - 0.24, sheen_ang + 0.24)
        ctx.close_path()
        ctx.set_source_rgba(TC_GOLD[0], TC_GOLD[1], TC_GOLD[2], 0.28)
        ctx.fill()

    # Center label
    ctx.arc(0, 0, 32.0, 0, math.tau)
    ctx.set_source_rgb(0.92, 0.76, 0.24)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(3.0)
    ctx.stroke()
    # Spindle hole
    ctx.arc(0, 0, 7.0, 0, math.tau)
    ctx.set_source_rgb(0.85, 0.85, 0.85)
    ctx.fill()
    ctx.restore()

    # Winding crank handle
    crank_x, crank_y = cab_rect[0] + cab_w, cab_cy
    crank_knob_x = crank_x + 36.0 + math.cos(crank_rot) * 12.0
    crank_knob_y = crank_y + 18.0 + math.sin(crank_rot) * 12.0
    ctx.new_path()
    ctx.move_to(crank_x, crank_y)
    ctx.line_to(crank_x + 36, crank_y - 12)
    ctx.line_to(crank_knob_x, crank_knob_y)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(5.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.arc(crank_knob_x, crank_knob_y, 9.0, 0, math.tau)
    ctx.set_source_rgb(0.92, 0.88, 0.80)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(3.0)
    ctx.stroke()

    # Bending Noodle Brass Gooseneck
    neck_start_x, neck_start_y = tt_cx + 45.0, tt_cy - 10.0
    neck_mid1_x = cx + 80.0 + neck_lean_x * 0.45
    neck_mid1_y = cy + 90.0 - neck_stretch_y * 0.35
    neck_mid2_x = cx + 60.0 + neck_lean_x * 0.80
    neck_mid2_y = cy - 20.0 - neck_stretch_y * 0.70
    horn_throat_x = cx - 20.0 + neck_lean_x
    horn_throat_y = cy - 10.0 - neck_stretch_y

    ctx.new_path()
    ctx.move_to(neck_start_x, neck_start_y)
    ctx.curve_to(neck_mid1_x + 40, neck_mid1_y, neck_mid2_x + 60, neck_mid2_y, horn_throat_x, horn_throat_y)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(32.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()

    ctx.new_path()
    ctx.move_to(neck_start_x, neck_start_y)
    ctx.curve_to(neck_mid1_x + 40, neck_mid1_y, neck_mid2_x + 60, neck_mid2_y, horn_throat_x, horn_throat_y)
    ctx.set_source_rgb(*BRASS_GOLD)
    ctx.set_line_width(22.0)
    ctx.stroke()

    ctx.new_path()
    ctx.move_to(neck_start_x - 3, neck_start_y)
    ctx.curve_to(neck_mid1_x + 34, neck_mid1_y, neck_mid2_x + 54, neck_mid2_y, horn_throat_x, horn_throat_y - 4)
    ctx.set_source_rgba(1.0, 0.98, 0.85, 0.75)
    ctx.set_line_width(6.0)
    ctx.stroke()

    # Giant Flared Anthropomorphic Brass Horn (Singing Mouth)
    bell_cx = cx - 180.0 + neck_lean_x
    bell_cy = cy - 60.0 - neck_stretch_y
    bell_rx = 85.0 * horn_squash_x
    bell_ry = 160.0 * horn_squash_y

    horn_top_lip = (bell_cx, bell_cy - bell_ry)
    horn_bot_lip = (bell_cx, bell_cy + bell_ry)

    ctx.new_path()
    ctx.move_to(horn_throat_x, horn_throat_y - 12)
    ctx.curve_to(cx - 60 + neck_lean_x * 0.5, cy - 40, cx - 110 + neck_lean_x * 0.8, bell_cy - bell_ry * 0.85, horn_top_lip[0], horn_top_lip[1])
    ctx.line_to(horn_bot_lip[0], horn_bot_lip[1])
    ctx.curve_to(cx - 100 + neck_lean_x * 0.8, bell_cy + bell_ry * 0.85, cx - 50 + neck_lean_x * 0.5, cy + 30, horn_throat_x, horn_throat_y + 16)
    ctx.close_path()

    horn_body_g = cairo.LinearGradient(horn_throat_x, horn_throat_y, bell_cx, bell_cy)
    horn_body_g.add_color_stop_rgb(0.0, 0.58, 0.44, 0.18)
    horn_body_g.add_color_stop_rgb(0.45, 0.92, 0.78, 0.34)
    horn_body_g.add_color_stop_rgb(0.75, 0.82, 0.65, 0.28)
    horn_body_g.add_color_stop_rgb(1.0, 0.48, 0.36, 0.16)
    ctx.set_source(horn_body_g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(6.0)
    ctx.stroke()

    n_petals = 12
    for p in range(n_petals):
        ang0 = (p / n_petals) * math.pi - math.pi * 0.5
        px0 = bell_cx + bell_rx * 0.15 * math.cos(ang0)
        py0 = bell_cy + bell_ry * math.sin(ang0)
        ctx.move_to(horn_throat_x, horn_throat_y)
        ctx.line_to(px0, py0)
        ctx.set_source_rgba(0.24, 0.18, 0.08, 0.35)
        ctx.set_line_width(2.0)
        ctx.stroke()

    # Bell Mouth Interior
    ctx.save()
    ctx.translate(bell_cx, bell_cy)
    ctx.scale(bell_rx * 0.45, bell_ry)
    ctx.arc(0, 0, 1.0, 0, math.tau)
    bell_inner_g = cairo.RadialGradient(0.2, 0.0, 0.05, 0.0, 0.0, 1.0)
    bell_inner_g.add_color_stop_rgb(0.0, 0.05, 0.04, 0.03)
    bell_inner_g.add_color_stop_rgb(0.7, 0.18, 0.14, 0.10)
    bell_inner_g.add_color_stop_rgb(1.0, 0.42, 0.32, 0.18)
    ctx.set_source(bell_inner_g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(0.08)
    ctx.stroke()

    # Singing cartoon tongue deep inside the trumpet bell!
    ctx.save()
    ctx.translate(0.18 + tongue_wag * 0.10, 0.35 + abs(tongue_wag) * 0.08)
    ctx.scale(0.38 * (1.2 if spit_blast > 0 else 1.0), 0.32 * (1.2 if spit_blast > 0 else 1.0))
    ctx.arc(0, 0, 1.0, 0, math.tau)
    ctx.set_source_rgb(0.78, 0.30, 0.36)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(0.15)
    ctx.stroke()
    ctx.move_to(0, -0.6)
    ctx.line_to(0, 0.4)
    ctx.stroke()
    ctx.restore()
    ctx.restore()

    # Outer brass rim ring
    ctx.save()
    ctx.translate(bell_cx, bell_cy)
    ctx.scale(bell_rx * 0.48, bell_ry * 1.03)
    ctx.arc(0, 0, 1.0, 0, math.tau)
    ctx.set_source_rgb(*BRASS_GOLD)
    ctx.set_line_width(0.12)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(0.16)
    ctx.stroke()
    ctx.restore()

    # 1930s Pac-Man Pie-Cut Eyes on the Horn Bell (or X X Spiral Dizzy Eyes)
    eye_horn_cx = bell_cx + 90.0
    eye_horn_cy = bell_cy - bell_ry * 0.48

    is_dizzy_mode = (eye_state == "dizzy_x" or stunned)
    is_shock_mode = (eye_state == "hit_shock" and not is_dizzy_mode)
    is_angry_mode = (eye_state == "angry")
    is_inhale_mode = (eye_state == "inhale_squint")

    if is_dizzy_mode:
        for e_off_x in [-22.0, 22.0]:
            ex = eye_horn_cx + e_off_x
            ey = eye_horn_cy - e_off_x * 0.2
            ctx.save()
            ctx.translate(ex, ey)
            ctx.scale(1.0, 1.35)
            ctx.arc(0, 0, 18.0, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(3.5)
            ctx.stroke()

            # Rotating Dizzy X X (strictly inside white eye socket, never overlapping pie-cut!)
            rot_dizzy = t * 4.0 if e_off_x > 0 else -t * 4.0
            ctx.rotate(rot_dizzy)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(4.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-7.0, -7.0)
            ctx.line_to(7.0, 7.0)
            ctx.move_to(7.0, -7.0)
            ctx.line_to(-7.0, 7.0)
            ctx.stroke()
            ctx.restore()

            # Wobbly squiggly dizzy eyebrow
            ctx.new_path()
            ctx.move_to(ex - 16.0, ey - 30.0)
            ctx.curve_to(ex - 8.0, ey - 38.0 + math.sin(t * 15.0) * 4.0, ex + 8.0, ey - 24.0, ex + 16.0, ey - 32.0)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(4.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

        # Overhead spinning golden stars (5 stars along a 3D tilted ellipse)
        for s_idx in range(5):
            ang_s = t * 5.5 + s_idx * (math.tau / 5.0)
            star_dx = eye_horn_cx + math.cos(ang_s) * 72.0
            star_dy = (eye_horn_cy - 78.0) + math.sin(ang_s) * 25.0
            ctx.save()
            draw_four_point_star(ctx, star_dx, star_dy, 16.0, 4.5, rot=ang_s * 1.5)
            ctx.set_source_rgb(*TC_GOLD)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(2.0)
            ctx.stroke()
            ctx.restore()

    elif is_shock_mode:
        # Wide-eyed startled surprise right before impact (NO dizzy X-eyes or stars yet!)
        for e_off_x in [-22.0, 22.0]:
            ex = eye_horn_cx + e_off_x
            ey = eye_horn_cy - e_off_x * 0.2
            ctx.save()
            ctx.translate(ex, ey)
            ctx.scale(1.15, 1.55)
            ctx.arc(0, 0, 18.0, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(3.5)
            ctx.stroke()

            # Tiny contracted startled pupil looking straight at incoming Slime
            ctx.arc(-6.0, 1.0, 6.5, 0, math.tau)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.fill()
            ctx.restore()

            # High-arched startled eyebrow
            ctx.new_path()
            ctx.arc(ex, ey - 38.0, 16.0, math.pi * 1.15, math.pi * 1.85)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(5.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

    elif is_inhale_mode:
        # Inhale squinting eyes: shut eyelids with strain wrinkles
        for e_off_x in [-22.0, 22.0]:
            ex = eye_horn_cx + e_off_x
            ey = eye_horn_cy - e_off_x * 0.2
            ctx.save()
            ctx.translate(ex, ey)
            ctx.scale(1.0, 1.35)
            ctx.arc(0, 0, 18.0, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(3.5)
            ctx.stroke()

            # Squinting closed eyelids > and <
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(4.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            if e_off_x < 0:
                ctx.move_to(8.0, -8.0)
                ctx.line_to(-6.0, 0.0)
                ctx.line_to(8.0, 8.0)
            else:
                ctx.move_to(-8.0, -8.0)
                ctx.line_to(6.0, 0.0)
                ctx.line_to(-8.0, 8.0)
            ctx.stroke()
            ctx.restore()

            # Deep arched straining eyebrow
            ctx.new_path()
            ctx.arc(ex, ey - 28.0, 14.0, math.pi * 1.15, math.pi * 1.85)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(5.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

    elif is_angry_mode:
        # Fierce angry Pie-Cut eyes with slanted brows glaring down at slime
        for e_off_x in [-22.0, 22.0]:
            ex = eye_horn_cx + e_off_x
            ey = eye_horn_cy - e_off_x * 0.2
            ctx.save()
            ctx.translate(ex, ey)
            ctx.scale(1.0, 1.35)
            ctx.arc(0, 0, 18.0, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(3.5)
            ctx.stroke()

            # Glaring black pupil
            ctx.translate(-6.0, 2.0)
            ctx.arc(0, 0, 11.0, 0, math.tau)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.fill()
            ctx.move_to(0, 0)
            ctx.arc(0, 0, 12.0, math.pi * 0.95, math.pi * 1.35)
            ctx.close_path()
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill()
            ctx.restore()

            # Slanted fierce angry eyebrow pointing down towards center
            ctx.new_path()
            if e_off_x < 0:
                ctx.move_to(ex - 16.0, ey - 22.0)
                ctx.line_to(ex + 16.0, ey - 34.0)
            else:
                ctx.move_to(ex - 16.0, ey - 34.0)
                ctx.line_to(ex + 16.0, ey - 22.0)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

    else:
        # Normal 1930s Pac-Man Pie-Cut Eyes
        for e_off_x in [-22.0, 22.0]:
            ex = eye_horn_cx + e_off_x
            ey = eye_horn_cy - e_off_x * 0.2
            ctx.save()
            ctx.translate(ex, ey)
            ctx.scale(1.0, 1.35)
            ctx.arc(0, 0, 18.0, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(3.5)
            ctx.stroke()

            ctx.translate(-4.0, -1.0)
            ctx.arc(0, 0, 11.0, 0, math.tau)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.fill()
            ctx.move_to(0, 0)
            ctx.arc(0, 0, 12.0, math.pi * 0.95, math.pi * 1.35)
            ctx.close_path()
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill()
            ctx.restore()

            ctx.new_path()
            ctx.arc(ex, ey - 32.0, 16.0, math.pi * 1.15, math.pi * 1.85)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(4.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

    # Inward Suction Air Streamlines around Horn Mouth during Inhale
    if inhale_stream > 0.05:
        ctx.save()
        ctx.translate(bell_cx, bell_cy)
        ctx.set_source_rgba(0.25, 0.22, 0.18, 0.65 * inhale_stream)
        ctx.set_line_width(3.0 * inhale_stream)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for s_i in range(8):
            ang_in = (s_i / 8.0) * math.tau + t * 4.0
            r_outer = 180.0 * (1.0 - (t * 2.0 + s_i * 0.25) % 0.4)
            r_inner = max(20.0, r_outer - 55.0)
            x_out = r_outer * 0.55 * math.cos(ang_in)
            y_out = r_outer * 1.15 * math.sin(ang_in)
            x_in = r_inner * 0.55 * math.cos(ang_in)
            y_in = r_inner * 1.15 * math.sin(ang_in)
            ctx.move_to(x_out, y_out)
            ctx.line_to(x_in, y_in)
            ctx.stroke()
        ctx.restore()

    # Dynamic Spit Blast Shockwave Rings blasting leftward
    if spit_blast > 0.05:
        ctx.save()
        ctx.translate(bell_cx, bell_cy)
        for sb_i in range(3):
            sb_p = (1.0 - spit_blast + sb_i * 0.3) % 1.0
            rad_x = 40.0 + sb_p * 260.0
            rad_y = 80.0 + sb_p * 320.0
            alpha = (1.0 - sb_p) * 0.85 * spit_blast
            ctx.save()
            ctx.scale(rad_x, rad_y)
            ctx.arc(0, 0, 1.0, math.pi * 0.65, math.pi * 1.35)
            ctx.set_source_rgba(0.24, 0.18, 0.12, alpha)
            ctx.set_line_width(0.06)
            ctx.stroke()
            ctx.restore()
        ctx.restore()

    # 1930s Comic Impact Starburst on Forehead (CLANG!)
    if impact_flash > 0.05:
        ctx.save()
        ctx.translate(bell_cx + 35.0, eye_horn_cy)
        ctx.scale(impact_flash, impact_flash)
        n_spikes = 16
        ctx.new_path()
        for spk in range(n_spikes):
            ang_spk = (spk / n_spikes) * math.tau
            r_spk = 130.0 if (spk % 2 == 0) else 55.0
            sx = r_spk * math.cos(ang_spk)
            sy = r_spk * math.sin(ang_spk)
            if spk == 0:
                ctx.move_to(sx, sy)
            else:
                ctx.line_to(sx, sy)
        ctx.close_path()
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(5.5)
        ctx.stroke()

        # Inner golden starburst core
        ctx.new_path()
        for spk in range(n_spikes):
            ang_spk = (spk / n_spikes) * math.tau + 0.1
            r_spk = 85.0 if (spk % 2 == 0) else 35.0
            sx = r_spk * math.cos(ang_spk)
            sy = r_spk * math.sin(ang_spk)
            if spk == 0:
                ctx.move_to(sx, sy)
            else:
                ctx.line_to(sx, sy)
        ctx.close_path()
        ctx.set_source_rgb(*TC_GOLD)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(3.5)
        ctx.stroke()
        ctx.restore()

    # Vintage 1930s 4-Finger White Cartoon Gloves (Expressive Rubber-Hose Arms)
    droop_p = float(boss_state.get("arm_droop", 1.0 if is_dizzy_mode else 0.0))
    sway_x = math.sin(t * 4.5) * 4.5 if is_dizzy_mode else 0.0
    sway_y = math.cos(t * 4.5) * 2.5 if is_dizzy_mode else 0.0

    # Arm 1 (front/left arm: pointing / lunging / punching / limply hanging down when dizzy!)
    arm1_start_x = (cx - 20.0) * (1.0 - droop_p) + (cab_cx - cab_w * 0.44) * droop_p
    arm1_start_y = (cy + 40.0) * (1.0 - droop_p) + (cab_cy - cab_h * 0.18) * droop_p
    if arm1_pose == "point":
        arm1_hand_x = cx - 145.0 + math.sin(t * 8.0) * 8.0
        arm1_hand_y = cy + 90.0 + math.cos(t * 8.0) * 6.0
        glove1_rot = -0.22
    elif arm1_pose == "inhale":
        arm1_hand_x = cx - 45.0
        arm1_hand_y = cy + 120.0 + math.sin(t * 20.0) * 3.0
        glove1_rot = -0.65
    elif arm1_pose == "blast":
        arm1_hand_x = cx - 180.0
        arm1_hand_y = cy + 65.0
        glove1_rot = 0.15
    elif arm1_pose == "fist":
        arm1_hand_x = cx - 95.0 + math.sin(t * 26.0) * 10.0
        arm1_hand_y = cy + 30.0 + math.cos(t * 26.0) * 8.0
        glove1_rot = 0.55
    else:  # dizzy -> smoothly drops down from fist pose to hang limply alongside cabinet near the floor!
        fist1_x, fist1_y = cx - 95.0, cy + 30.0
        limp1_x = cab_cx - cab_w * 0.5 - 28.0 + sway_x
        limp1_y = cab_base_y - 4.0 + sway_y
        arm1_hand_x = fist1_x * (1.0 - droop_p) + limp1_x * droop_p
        arm1_hand_y = fist1_y * (1.0 - droop_p) + limp1_y * droop_p
        glove1_rot = 0.55 * (1.0 - droop_p) + (0.06 + 0.04 * math.sin(t * 4.5)) * droop_p

    ctx.new_path()
    ctx.move_to(arm1_start_x, arm1_start_y)
    if arm1_pose == "dizzy":
        ctx.curve_to(
            arm1_start_x - 36.0, arm1_start_y + 32.0,
            arm1_hand_x - 10.0, arm1_hand_y - 42.0,
            arm1_hand_x, arm1_hand_y,
        )
    else:
        ctx.curve_to(arm1_start_x - 50, arm1_start_y + 30, arm1_hand_x - 20, arm1_hand_y - 30, arm1_hand_x, arm1_hand_y)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(14.0)
    ctx.stroke()
    draw_cartoon_glove(ctx, arm1_hand_x, arm1_hand_y, rot=glove1_rot, flip=False)

    # Arm 2 (back/right arm: winding crank / punching / blast / limply hanging down when dizzy!)
    arm2_start_x = (cx + 80.0) * (1.0 - droop_p) + (cab_cx + cab_w * 0.44) * droop_p
    arm2_start_y = (cy + 80.0) * (1.0 - droop_p) + (cab_cy - cab_h * 0.18) * droop_p
    if arm2_pose == "crank":
        arm2_hand_x = crank_knob_x
        arm2_hand_y = crank_knob_y
        glove2_rot = 1.15
    elif arm2_pose == "fist":
        arm2_hand_x = cx + 130.0 + math.cos(t * 24.0) * 8.0
        arm2_hand_y = cy + 25.0 + math.sin(t * 24.0) * 10.0
        glove2_rot = 1.35
    elif arm2_pose == "blast":
        arm2_hand_x = cx - 120.0
        arm2_hand_y = cy + 115.0
        glove2_rot = 0.45
    else:  # dizzy -> smoothly drops down from fist pose to hang limply alongside right of cabinet near the floor!
        fist2_x, fist2_y = cx + 130.0, cy + 25.0
        limp2_x = cab_cx + cab_w * 0.5 + 32.0 - sway_x
        limp2_y = cab_base_y - 2.0 + sway_y
        arm2_hand_x = fist2_x * (1.0 - droop_p) + limp2_x * droop_p
        arm2_hand_y = fist2_y * (1.0 - droop_p) + limp2_y * droop_p
        glove2_rot = 1.35 * (1.0 - droop_p) + (-0.06 - 0.04 * math.sin(t * 4.5)) * droop_p

    ctx.new_path()
    ctx.move_to(arm2_start_x, arm2_start_y)
    if arm2_pose == "dizzy":
        ctx.curve_to(
            arm2_start_x + 36.0, arm2_start_y + 32.0,
            arm2_hand_x + 10.0, arm2_hand_y - 42.0,
            arm2_hand_x, arm2_hand_y,
        )
    else:
        ctx.curve_to(arm2_start_x + 60, arm2_start_y + 20, arm2_hand_x + 40, arm2_hand_y - 30, arm2_hand_x, arm2_hand_y)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(14.0)
    ctx.stroke()
    draw_cartoon_glove(ctx, arm2_hand_x, arm2_hand_y, rot=glove2_rot, flip=True)

    # Reverse Vacuum Vortex or Dynamic Leftward Soundwave Pulses
    if vortex_strength > 0.05:
        # Golden Logarithmic Reverse Vacuum Vortex into horn mouth
        ctx.save()
        ctx.translate(bell_cx, bell_cy)
        n_spiral_arms = 6
        for sp in range(n_spiral_arms):
            base_theta = (sp / n_spiral_arms) * math.tau + t * 9.0 * (1.0 + vortex_strength)
            ctx.new_path()
            for step in range(50):
                frac = step / 50.0
                r_v = 240.0 * vortex_strength * (1.0 - frac)
                theta_v = base_theta + frac * 4.2 * math.pi
                vx = r_v * 0.55 * math.cos(theta_v)
                vy = r_v * 1.15 * math.sin(theta_v)
                if step == 0:
                    ctx.move_to(vx, vy)
                else:
                    ctx.line_to(vx, vy)
            ctx.set_source_rgba(TC_GOLD[0], TC_GOLD[1], TC_GOLD[2], 0.75 * vortex_strength)
            ctx.set_line_width(max(1.5, 4.0 * vortex_strength))
            ctx.stroke()

        # Central suction black hole
        ctx.scale(0.48, 1.05)
        suction_g = cairo.RadialGradient(0, 0, 5, 0, 0, 95 * vortex_strength)
        suction_g.add_color_stop_rgba(0.0, 0.02, 0.02, 0.02, 0.98 * vortex_strength)
        suction_g.add_color_stop_rgba(0.5, TC_GOLD[0], TC_GOLD[1], TC_GOLD[2], 0.50 * vortex_strength)
        suction_g.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        ctx.set_source(suction_g)
        ctx.arc(0, 0, 95 * vortex_strength, 0, math.tau)
        ctx.fill()
        ctx.restore()
    elif not is_dizzy_mode:
        # DYNAMIC Leftward Propagating Soundwave Pulses (replacing dead static arcs!)
        for w_i in range(5):
            w_phase = (t * 1.8 + w_i * 0.20) % 1.0
            wr_x = 70.0 + w_phase * 460.0
            wr_y = 140.0 + w_phase * 360.0
            alpha = (1.0 - w_phase) * (0.65 if spit_blast <= 0 else 0.25)
            if alpha > 0.02:
                ctx.save()
                ctx.translate(bell_cx - 20.0, bell_cy)
                ctx.scale(wr_x, wr_y)
                ctx.arc(0, 0, 1.0, math.pi * 0.65, math.pi * 1.35)
                ctx.set_source_rgba(0.24, 0.20, 0.16, alpha)
                ctx.set_line_width(0.04)
                ctx.stroke()
                ctx.restore()

    ctx.restore()


def draw_squashed_and_bouncing_note_critters(
    ctx: cairo.Context,
    slime_cx: float,
    slime_cy: float,
    slime_r: float,
    squash_y: float,
    gramo_cx: float,
    gramo_cy: float,
    t: float = 0.0,
):
    """
    Story Moment Integration (STORY.md):
      1. Right beneath the slime's bounce landing on the piano keys: a squashed mischievous black
         note critter (扁平墨池 + 弯曲符干 + X X 眩晕眼 + 飞溅彩星与彩色小音符)!
      2. Beside the gramophone on the piano road: lively bouncing rubber-hose black note critters (♪)
         with cartoon pie-cut eyes, white gloves/shoes, hopping to the jazz beat!
    """
    # 1. Squashed Black Note Critter right under the slime's contact zone
    sq_x = slime_cx + 6.0
    sq_y = slime_cy + slime_r * squash_y + 18.0
    ctx.save()
    ctx.translate(sq_x, sq_y)

    # Impact shockwave ellipse on the piano keys
    ctx.save()
    ctx.scale(1.0, 0.34)
    ctx.arc(0, 0, 108.0, 0, math.tau)
    ctx.set_source_rgba(TC_GOLD[0], TC_GOLD[1], TC_GOLD[2], 0.75)
    ctx.set_line_width(5.5)
    ctx.stroke()
    ctx.arc(0, 0, 84.0, 0, math.tau)
    ctx.set_source_rgba(TC_CYAN[0], TC_CYAN[1], TC_CYAN[2], 0.65)
    ctx.set_line_width(4.0)
    ctx.stroke()
    ctx.restore()

    # Flattened black ink note pancake
    ctx.save()
    ctx.scale(1.0, 0.30)
    ctx.arc(0, 0, 56.0, 0, math.tau)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.fill_preserve()
    ctx.set_source_rgb(*PAPER_CREAM)
    ctx.set_line_width(2.5)
    ctx.stroke()
    ctx.restore()

    # Bent note stem & flag flattened to the right
    ctx.new_path()
    ctx.move_to(38.0, -2.0)
    ctx.curve_to(72.0, -14.0, 88.0, 8.0, 108.0, -10.0)
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(7.5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.new_path()
    ctx.move_to(108.0, -10.0)
    ctx.curve_to(122.0, -2.0, 118.0, 12.0, 102.0, 10.0)
    ctx.set_line_width(5.5)
    ctx.stroke()

    # Dizzy X X cartoon eyes on the squashed note
    for ex in [-18.0, 16.0]:
        ctx.save()
        ctx.translate(ex, -2.0)
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.set_line_width(3.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(-5.5, -5.0)
        ctx.line_to(5.5, 5.0)
        ctx.move_to(5.5, -5.0)
        ctx.line_to(-5.5, 5.0)
        ctx.stroke()
        ctx.restore()

    # Burst of colorful Technicolor mini stars (✦) and splashed mini notes flying out from impact!
    burst_items = [
        (-88.0, -18.0, 14.0, TC_GOLD, "star"),
        (-68.0, 16.0, 11.0, TC_CYAN, "star"),
        (82.0, -26.0, 15.0, TC_CORAL, "star"),
        (74.0, 18.0, 12.0, TC_VIOLET, "star"),
        (-105.0, 4.0, 10.0, TC_BLUE, "note"),
        (115.0, 6.0, 10.0, TC_GOLD, "note"),
    ]
    for bx, by, br, bcol, btype in burst_items:
        ctx.save()
        ctx.translate(bx, by)
        if btype == "star":
            draw_four_point_star(ctx, 0, 0, br, br * 0.26, rot=0.25)
            ctx.set_source_rgb(*bcol)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(2.2)
            ctx.stroke()
        else:
            ctx.arc(0, 0, br * 0.65, 0, math.tau)
            ctx.set_source_rgb(*bcol)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(2.0)
            ctx.stroke()
            ctx.move_to(br * 0.55, 0)
            ctx.line_to(br * 0.55, -br * 1.6)
            ctx.set_line_width(2.8)
            ctx.stroke()
        ctx.restore()

    ctx.restore()

    # 2. Bouncing Mischievous Black Note Critters (♪) hopping along the piano road near the Gramophone!
    critters = [
        (gramo_cx - 265.0, gramo_cy + 145.0, 1.05, -0.12),
        (gramo_cx - 175.0, gramo_cy + 185.0, 0.88, 0.16),
    ]
    for c_idx, (ncx, ncy, nsc, nrot) in enumerate(critters):
        ctx.save()
        ctx.translate(ncx, ncy)
        ctx.rotate(nrot)
        ctx.scale(nsc, nsc)

        # Drop shadow on piano keys
        ctx.save()
        ctx.translate(0, 38.0)
        ctx.scale(1.2, 0.35)
        ctx.arc(0, 0, 22.0, 0, math.tau)
        ctx.set_source_rgba(0.12, 0.08, 0.06, 0.45)
        ctx.fill()
        ctx.restore()

        # Rubber-hose bouncing legs + cartoon shoes
        for leg_s in [-1, 1]:
            ctx.new_path()
            ctx.move_to(leg_s * 9.0, 14.0)
            ctx.curve_to(leg_s * 16.0, 22.0, leg_s * 8.0, 30.0, leg_s * 14.0, 35.0)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(5.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

            ctx.save()
            ctx.translate(leg_s * 15.0, 36.0)
            ctx.scale(1.3, 0.75)
            ctx.arc(0, 0, 7.5, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(2.4)
            ctx.stroke()
            ctx.restore()

        # Note head body
        ctx.save()
        ctx.rotate(-0.22)
        ctx.scale(1.18, 0.92)
        ctx.arc(0, 0, 22.0, 0, math.tau)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.fill_preserve()
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.set_line_width(2.0)
        ctx.stroke()
        ctx.restore()

        # Note stem & waving flag
        ctx.new_path()
        ctx.move_to(16.0, -4.0)
        ctx.curve_to(20.0, -34.0, 26.0, -54.0, 20.0, -72.0)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(7.5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

        ctx.new_path()
        ctx.move_to(20.0, -72.0)
        ctx.curve_to(48.0, -62.0, 52.0, -42.0, 34.0, -30.0)
        ctx.curve_to(32.0, -44.0, 26.0, -56.0, 20.0, -72.0)
        ctx.close_path()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.fill()

        # Expressive cartoon eyes on the note critter
        for ex in [-7.5, 7.5]:
            ctx.arc(ex, -2.0, 5.5, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill()
            ctx.arc(ex - 1.8, -2.0, 2.5, 0, math.tau)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.fill()

        # Hopping motion arc ticks underneath
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(2.2)
        ctx.arc(0, 42.0, 14.0, math.pi * 0.2, math.pi * 0.8)
        ctx.stroke()

        ctx.restore()


def draw_jazz_musical_notes_stream(ctx: cairo.Context, slime_cx: float, slime_cy: float, ring_r: float, t: float = 0.0):
    """
    Renders the dynamic stream of jazz musical notes (♪ ♫ ♬) blasting from the horn.
    As they cross into the Technicolor Soundwave Ring around the slime, they transform into
    glowing 4-point Gemini stars (✦) and chromatic notes!
    """
    ctx.save()

    base_notes = [
        (1230.0, 390.0, "quaver", 0.45, 1.30),
        (1200.0, 480.0, "double", 0.35, 1.25),
        (1140.0, 410.0, "quaver", -0.22, 1.40),
        (1090.0, 540.0, "quaver", 0.45, 1.10),
        (1040.0, 360.0, "double", 0.20, 1.35),
        (1010.0, 460.0, "semi", -0.38, 1.35),
        (960.0, 390.0, "treble", 0.18, 1.50),
        (930.0, 520.0, "double", 0.28, 1.20),
        # Entering Technicolor wave -> Transforming into stars & colorful notes!
        (880.0, 440.0, "star_note", -0.20, 1.30),
        (830.0, 350.0, "gemini_star", 0.35, 1.45),
        (790.0, 510.0, "gemini_star", -0.15, 1.25),
        (740.0, 420.0, "gemini_star", 0.52, 1.55),
        (630.0, 410.0, "gemini_star", -0.40, 1.30),
        (580.0, 490.0, "star_note", 0.25, 1.20),
        (520.0, 430.0, "double", -0.18, 1.15),
        (460.0, 540.0, "quaver", 0.32, 1.10),
    ]

    for b_nx, b_ny, ntype, nrot, nscale in base_notes:
        # Dynamic wave flowing leftward from horn opening
        shift_x = (t * 135.0) % 840.0
        nx = 1260.0 - ((1260.0 - b_nx + shift_x) % 840.0)
        ny = b_ny + math.sin(t * 4.5 + b_nx * 0.02) * 16.0
        d_slime = math.hypot(nx - slime_cx, ny - slime_cy)
        in_tc = d_slime < ring_r

        ctx.save()
        ctx.translate(nx, ny)
        ctx.rotate(nrot)
        ctx.scale(nscale, nscale)

        if ntype == "gemini_star" or (in_tc and ntype in ("quaver", "star_note")):
            star_r = 20.0
            halo = cairo.RadialGradient(0, 0, 2, 0, 0, star_r * 2.2)
            halo.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.85)
            halo.add_color_stop_rgba(0.4, TC_GOLD[0], TC_GOLD[1], TC_GOLD[2], 0.55)
            halo.add_color_stop_rgba(1.0, TC_BLUE[0], TC_BLUE[1], TC_BLUE[2], 0.0)
            ctx.set_source(halo)
            ctx.arc(0, 0, star_r * 2.2, 0, math.tau)
            ctx.fill()

            draw_four_point_star(ctx, 0, 0, star_r, star_r * 0.26)
            star_g = cairo.LinearGradient(-star_r, -star_r, star_r, star_r)
            star_g.add_color_stop_rgb(0.0, *TC_BLUE)
            star_g.add_color_stop_rgb(0.5, *TC_VIOLET)
            star_g.add_color_stop_rgb(1.0, *TC_CORAL)
            ctx.set_source(star_g)
            ctx.fill_preserve()
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.set_line_width(2.0)
            ctx.stroke()

            ctx.set_source_rgb(*TC_GOLD)
            ctx.set_line_width(2.2)
            for ray_ang in [0.3, 1.2, 2.1, 3.4, 4.8]:
                rx1, ry1 = 24.0 * math.cos(ray_ang), 24.0 * math.sin(ray_ang)
                rx2, ry2 = 32.0 * math.cos(ray_ang), 32.0 * math.sin(ray_ang)
                ctx.move_to(rx1, ry1)
                ctx.line_to(rx2, ry2)
                ctx.stroke()

        elif ntype == "double":
            col = TC_VIOLET if in_tc else INK_BLACK
            for hx, hy in [(-12.0, 12.0), (12.0, 6.0)]:
                ctx.save()
                ctx.translate(hx, hy)
                ctx.rotate(-0.35)
                ctx.scale(1.2, 0.85)
                ctx.arc(0, 0, 8.5, 0, math.tau)
                ctx.set_source_rgb(*col)
                ctx.fill()
                ctx.restore()

            ctx.set_source_rgb(*col)
            ctx.set_line_width(3.5)
            ctx.move_to(-6.0, 10.0)
            ctx.line_to(-6.0, -14.0)
            ctx.move_to(18.0, 4.0)
            ctx.line_to(18.0, -20.0)
            ctx.stroke()

            ctx.set_line_width(6.0)
            ctx.move_to(-7.0, -12.0)
            ctx.line_to(19.0, -18.0)
            ctx.stroke()

            ctx.arc(-11.0, 11.0, 2.5, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill()
            ctx.arc(13.0, 5.0, 2.5, 0, math.tau)
            ctx.fill()

        elif ntype == "treble":
            col = TC_CORAL if in_tc else INK_BLACK
            ctx.set_source_rgb(*col)
            ctx.set_line_width(4.0)
            ctx.new_path()
            ctx.move_to(0, -28.0)
            ctx.curve_to(16, -18, -14, 0, 4, 12)
            ctx.curve_to(16, 20, 0, 28, -6, 26)
            ctx.stroke()
            ctx.move_to(2, -32.0)
            ctx.line_to(2, 32.0)
            ctx.stroke()
            ctx.arc(2, 34.0, 4.5, 0, math.tau)
            ctx.fill()

        else:
            col = TC_BLUE if in_tc else INK_BLACK
            ctx.save()
            ctx.translate(-4.0, 8.0)
            ctx.rotate(-0.35)
            ctx.scale(1.2, 0.85)
            ctx.arc(0, 0, 9.0, 0, math.tau)
            ctx.set_source_rgb(*col)
            ctx.fill()
            ctx.restore()

            ctx.set_source_rgb(*col)
            ctx.set_line_width(3.5)
            ctx.move_to(2.0, 6.0)
            ctx.line_to(2.0, -18.0)
            ctx.stroke()
            ctx.new_path()
            ctx.move_to(2.0, -18.0)
            ctx.curve_to(14, -14, 16, -4, 10, 4)
            ctx.set_line_width(4.0)
            ctx.stroke()

            ctx.arc(-3.0, 7.0, 2.5, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill()

        ctx.restore()

    ctx.restore()


def draw_technicolor_jazz_soundwave_ring(ctx: cairo.Context, slime_cx: float, slime_cy: float, ring_r: float):
    """
    Renders the expanding Technicolor Jazz Soundwave Ring around the slime:
    - Glowing concentric chromatic rings (Cyan, Violet, Coral, Gold)
    - Separates the vintage 1930s sepia celluloid world from the 3-strip Technicolor universe!
    """
    ctx.save()

    tc_aura = cairo.RadialGradient(slime_cx, slime_cy, ring_r * 0.1, slime_cx, slime_cy, ring_r * 1.05)
    tc_aura.add_color_stop_rgba(0.0, 0.95, 0.98, 1.00, 0.38)
    tc_aura.add_color_stop_rgba(0.55, TC_VIOLET[0], TC_VIOLET[1], TC_VIOLET[2], 0.22)
    tc_aura.add_color_stop_rgba(0.85, TC_CORAL[0], TC_CORAL[1], TC_CORAL[2], 0.18)
    tc_aura.add_color_stop_rgba(1.0, TC_GOLD[0], TC_GOLD[1], TC_GOLD[2], 0.0)
    ctx.set_source(tc_aura)
    ctx.arc(slime_cx, slime_cy, ring_r * 1.05, 0, math.tau)
    ctx.fill()

    for r_mult, lw, col, alpha in [
        (1.00, 5.0, (1.00, 0.98, 0.92), 0.95),
        (0.97, 7.0, TC_CYAN, 0.85),
        (0.94, 6.0, TC_VIOLET, 0.75),
        (0.90, 8.0, TC_CORAL, 0.65),
        (0.86, 5.0, TC_GOLD, 0.55),
    ]:
        ctx.arc(slime_cx, slime_cy, ring_r * r_mult, 0, math.tau)
        ctx.set_source_rgba(col[0], col[1], col[2], alpha)
        ctx.set_line_width(lw)
        ctx.stroke()

    n_notches = 32
    for i in range(n_notches):
        ang = (i / n_notches) * math.tau
        r1 = ring_r * 0.98
        r2 = ring_r * (1.03 + 0.03 * math.sin(i * 3.0))
        ctx.move_to(slime_cx + r1 * math.cos(ang), slime_cy + r1 * math.sin(ang))
        ctx.line_to(slime_cx + r2 * math.cos(ang), slime_cy + r2 * math.sin(ang))
        ctx.set_source_rgba(1.0, 0.95, 0.85, 0.75)
        ctx.set_line_width(2.2)
        ctx.stroke()

    ctx.restore()


def apply_celluloid_film_grain_and_scratches(arr: np.ndarray, seed: int = 1934):
    """
    Applies authentic 1930s 35mm celluloid film texture:
    - Silver-halide emulsion grain
    - Vertical hair scratches with realistic breaks
    - Dust specks and lint flecks
    """
    rng = np.random.default_rng(seed)
    h, w = arr.shape[:2]

    grain = rng.standard_normal((h, w, 1), dtype=np.float32) * 10.5
    arr[..., :3] = np.clip(arr[..., :3].astype(np.float32) + grain, 0, 255).astype(np.uint8)

    scratch_xs = [320, 560, 940, 1420, 1680]
    for sx in scratch_xs:
        x_jitter = sx + int(rng.integers(-2, 3))
        if 84 < x_jitter < w - 84:
            n_segments = int(rng.integers(2, 6))
            for _ in range(n_segments):
                y_start = int(rng.integers(0, h - 200))
                seg_len = int(rng.integers(80, 360))
                y_end = min(h, y_start + seg_len)
                scratch_col = int(rng.choice([245, 30]))
                arr[y_start:y_end, x_jitter:x_jitter + 1, :3] = (
                    arr[y_start:y_end, x_jitter:x_jitter + 1, :3] * 0.4 + scratch_col * 0.6
                )

    n_dust = 34
    dust_ys = rng.integers(30, h - 30, size=n_dust)
    dust_xs = rng.integers(90, w - 90, size=n_dust)
    for dy, dx in zip(dust_ys, dust_xs):
        d_rad = int(rng.integers(1, 3))
        d_col = int(rng.choice([250, 20]))
        y1, y2 = max(0, int(dy) - d_rad), min(h, int(dy) + d_rad + 1)
        x1, x2 = max(0, int(dx) - d_rad), min(w, int(dx) + d_rad + 1)
        arr[y1:y2, x1:x2, :3] = (arr[y1:y2, x1:x2, :3] * 0.35 + d_col * 0.65).astype(np.uint8)


# ---------------------------------------------------------------------------
# API Contract 3: render_world
# ---------------------------------------------------------------------------
def render_world(cam_x: float, cam_y: float, t: float, state: dict = None) -> Image.Image:
    """
    Renders the 1920x1080 viewport for World 09 at camera (cam_x, cam_y) and time t.
    At keyframe (cam_x=2880.0, cam_y=540.0), pan_dx = 0.0, preserving 100% of v3's golden composition
    while integrating the squashed note critter, bouncing note critters, and gramophone star ✦.
    """
    if state is None:
        state = {}

    pan_dx = (cam_x - 2880.0) * 0.45

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    slime_cx = state.get("slime_cx", 680.0 - pan_dx)
    slime_cy = state.get("slime_cy", 560.0)
    slime_r = state.get("slime_r", 118.0)
    squash_y = state.get("slime_squash_y", 0.84)
    tilt = state.get("slime_tilt", 0.12)
    gramo_cx = state.get("gramo_cx", 1380.0 - pan_dx)
    gramo_cy = state.get("gramo_cy", 540.0)
    ring_radius = state.get("ring_radius", 375.0)

    # 1. Base Stage & Spotlights (Warm #EFE6D2 aged paper celluloid sky & wooden planks)
    draw_stage_floorboards_and_spotlights(ctx, pan_dx=pan_dx)

    # 2. Undulating S-Curved 3D Rubber Piano Keyboard
    draw_rubber_hose_piano_keyboard(ctx, slime_cx, slime_cy, ring_radius, pan_dx=pan_dx)

    # 3. Anthropomorphic 1930s Rubber-Hose Brass Gramophone Character
    draw_rubber_hose_gramophone(ctx, gramo_cx, gramo_cy)

    # 4. Concentric Technicolor Soundwave Ring around Slime
    draw_technicolor_jazz_soundwave_ring(ctx, slime_cx, slime_cy, ring_radius)

    # 5. Story Beat: Squashed Black Note Critter under Slime + Bouncing Note Critters by Gramophone
    draw_squashed_and_bouncing_note_critters(
        ctx, slime_cx, slime_cy, slime_r, squash_y, gramo_cx, gramo_cy, t=t
    )

    # 6. Stream of Jazz Musical Notes transforming into Gemini Stars inside the Technicolor Ring
    draw_jazz_musical_notes_stream(ctx, slime_cx, slime_cy, ring_radius)

    # 7. Story Beat: 4-Point Star ✦ dancing atop/in front of the Gramophone Horn Bell!
    gramo_star_cx = gramo_cx - 175.0
    gramo_star_cy = gramo_cy - 258.0
    draw_star(ctx, gramo_star_cx, gramo_star_cy, r=28.0, rot=-0.12 + math.sin(t * 2.0) * 0.1, t=t)

    # 8. Star-Spark Slime Surfing the Keyboard (with Ben-Day halftone dots & overhead crown star)
    draw_slime(
        ctx,
        slime_cx,
        slime_cy,
        slime_r,
        squash_y=squash_y,
        tilt=tilt,
        look=(0.52, -0.15),
        eye_mode="pill",
        t=t,
        draw_crown_star=True,
    )

    # 9. Vintage Theater Pelmet & Curtains
    draw_vintage_theater_curtains(ctx)

    # 10. 35mm Celluloid Sprocket Borders
    draw_35mm_sprocket_borders(ctx)

    # Convert cairo to PIL for vintage celluloid film grain & scratches (NO UI badge!)
    pil_img = cairo_to_pil(surface)
    arr = np.array(pil_img, dtype=np.uint8)
    apply_celluloid_film_grain_and_scratches(arr, seed=1934)
    pil_final = Image.fromarray(arr, mode="RGBA").convert("RGB")
    return pil_final


# ---------------------------------------------------------------------------
# API Contract 4: render_keyframe
# ---------------------------------------------------------------------------
def render_keyframe() -> Image.Image:
    """Renders the canonical World 09 keyframe (1920x1080 RGB PIL Image)."""
    return render_world(cam_x=2880.0, cam_y=540.0, t=6.6)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(os.path.abspath(OUT_PATH)), exist_ok=True)
    img = render_keyframe()
    img.save(OUT_PATH, format="PNG", optimize=False)
    print(f"Successfully rendered World 07 Rubber-Hose Keyframe -> {OUT_PATH}")
