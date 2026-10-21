# -*- coding: utf-8 -*-
"""
StarDino · Star-Spark Slime (星星恐龙 · 星芒史莱姆)
Multi-Style Procedural Character Rig, 3D Spherical Gaze Projection,
Second-Order Spring-Damper Physics & 9 Concrete World Tokens Engine
(PyCairo + NumPy + Pillow)

Created by Star Dinosaur (星星恐龙) · Generated with Gemini 4 · MIT License.
"""

import os
import math
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import cairo
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Font resolution — portable, no hard-coded user home.
#   Override with STARDINO_FONT_DIR, or per-face with
#   STARDINO_FONT_CJK_BOLD / _MED / _REG / STARDINO_FONT_MONO.
#   Missing CJK faces degrade to Pillow's built-in bitmap font rather than
#   crashing; set STARDINO_FONT_DIR if your distro ships Noto CJK elsewhere.
# ---------------------------------------------------------------------------
_FONT_DIR = os.environ.get("STARDINO_FONT_DIR", "").strip()


def _font_from_env(env_key: str, filename: str, system_paths) -> str:
    """First existing candidate: env var > STARDINO_FONT_DIR > known system paths."""
    cands = [os.environ.get(env_key, "").strip()]
    if _FONT_DIR:
        cands.append(os.path.join(_FONT_DIR, filename))
    cands.extend(system_paths)
    for p in cands:
        if p and os.path.exists(p):
            return p
    return ""


FONT_CJK_BOLD = _font_from_env(
    "STARDINO_FONT_CJK_BOLD",
    "NotoSansCJKsc-Bold.otf",
    [
        os.path.join(os.path.expanduser("~"), ".fonts", "NotoSansCJKsc-Bold.otf"),
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
    ],
)
FONT_CJK_MED = _font_from_env(
    "STARDINO_FONT_CJK_MED",
    "NotoSansCJKsc-Medium.otf",
    [
        os.path.join(os.path.expanduser("~"), ".fonts", "NotoSansCJKsc-Medium.otf"),
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Medium.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ],
)
FONT_CJK_REG = _font_from_env(
    "STARDINO_FONT_CJK_REG",
    "NotoSansCJKsc-Regular.otf",
    [
        os.path.join(os.path.expanduser("~"), ".fonts", "NotoSansCJKsc-Regular.otf"),
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ],
)
FONT_MONO = _font_from_env(
    "STARDINO_FONT_MONO",
    "DejaVuSansMono-Bold.ttf",
    [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "C:/Windows/Fonts/consolab.ttf",
    ],
)

_FONT_CACHE = {}


def get_pil_font(size: int, path: str = None) -> ImageFont.FreeTypeFont:
    """Cached font loader. `path` overrides; otherwise the CJK fallback chain is used."""
    resolved = path or FONT_CJK_MED
    key = (resolved, int(size))
    if key not in _FONT_CACHE:
        for p in (resolved, FONT_CJK_BOLD, FONT_CJK_MED, FONT_CJK_REG):
            if p and os.path.exists(p):
                _FONT_CACHE[key] = ImageFont.truetype(p, int(size))
                break
        else:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def cairo_to_pil(surface: cairo.ImageSurface) -> Image.Image:
    w, h = surface.get_width(), surface.get_height()
    buf = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgba = buf[:, :, [2, 1, 0, 3]].copy()
    return Image.fromarray(rgba, mode="RGBA")


def pil_to_cairo(img: Image.Image) -> cairo.ImageSurface:
    rgba = np.array(img.convert("RGBA"), dtype=np.uint8)
    bgra = rgba[:, :, [2, 1, 0, 3]].copy()
    h, w = bgra.shape[:2]
    return cairo.ImageSurface.create_for_data(bgra, cairo.FORMAT_ARGB32, w, h)


@dataclass
class SlimePose:
    x: float = 960.0
    y: float = 540.0
    radius: float = 110.0
    squash_y: float = 1.0          # >1 stretched vertically, <1 squashed flat (sx = 1/sqrt(sy))
    tilt: float = 0.0              # body roll/tilt in radians
    look_x: float = 0.45           # -1.0 (left) to +1.0 (right) spherical gaze
    look_y: float = -0.35          # -1.0 (up) to +1.0 (down) spherical gaze
    eye_scale: float = 1.0         # overall capsule eye scale
    eye_mode: str = "pill"         # "pill", "asymmetric", "flat", "happy_arc", "star"
    eye_cant: float = 0.0          # extra rotation (radians) of the eye-pair frame on sphere
    eye_spacing: float = 1.0       # multiplier for inter-eye distance
    left_eye_scale: tuple = (1.0, 1.0)   # (w_mult, h_mult) for left (near) capsule eye
    right_eye_scale: tuple = (1.0, 1.0)  # (w_mult, h_mult) for right (far) capsule eye
    left_eye_dy: float = 0.0       # local Y offset (in units of R) for left eye
    right_eye_dy: float = 0.0      # local Y offset (in units of R) for right eye
    wink_left: float = 0.0         # >0.5 bends left eye into happy arc
    wink_right: float = 0.0        # >0.5 bends right eye into happy arc
    mouth_type: str = "none"       # kept for legacy callers; mouthless by design
    star_offset_x: float = 0.0
    star_offset_y: float = 0.0
    star_scale: float = 1.0
    star_rot: float = 0.0
    phase: float = 0.0             # harmonic wave phase
    jelly_wave: float = 0.0        # >0 adds lateral elastic landing wave to bottom base
    show_twin_core: bool = False   # reveals internal binary-star nebula core
    twin_stars: bool = False       # splits overhead satellite into twin cyan/gold stars
    draw_shadow: bool = True       # draws soft floor contact shadow
    shape_aware_gradient: bool = False  # scale body gradient with squash/stretch (prevents coral bleeding onto stretched crown)
    coral_rgb: tuple = None        # optional override for the warm coral end of the body gradient
    twin_core_dy: float = 0.14     # vertical offset (units of R) of the internal twin-star core
    twin_core_scale: float = 1.0   # size multiplier of the internal twin-star core


def compute_slime_contour(pose: SlimePose, n_pts: int = 108, boil_amp: float = 0.0, boil_seed: int = 1):
    """
    Plump Spherical Jelly / Mochi Silhouette with 3D Head-Turn & Gaze Body Coupling:
      - Nearly spherical dome & cheeks with no pointed tip at the top
      - Subtle, plush gravity contact cushion at the very bottom (theta = +pi/2)
      - Strict volume-preserving squash & stretch: sx = 1 / sqrt(squash_y), sy = squash_y
      - 3D Body-Gaze Coupling: turning head left/right (look_x) or looking up/down (look_y)
        organically cranes/leans the upper dome while keeping the bottom contact point (s=+1) anchored!
      - Optional elastic landing wave (jelly_wave) along the lower hemisphere
    """
    sy = max(0.45, min(2.2, pose.squash_y))
    sx = 1.0 / math.sqrt(sy)
    R = pose.radius
    pts = []

    lx_clamped = max(-1.0, min(1.0, float(pose.look_x)))
    ly_clamped = max(-1.0, min(1.0, float(pose.look_y)))

    # Subtle body tilt coupling when craning head up/down sideways
    coupled_tilt = pose.tilt + lx_clamped * (-ly_clamped) * 0.065
    cos_t = math.cos(coupled_tilt)
    sin_t = math.sin(coupled_tilt)

    for i in range(n_pts):
        th = (i / n_pts) * math.tau
        s = math.sin(th)   # -1 at top crown, +1 at bottom base
        c = math.cos(th)   # -1 at left, +1 at right

        # Upper-body factor: 1.0 at crown (s=-1), smoothly 0.0 at bottom contact (s=+1)
        upper_weight = ((1.0 - s) * 0.5) ** 1.45
        mid_weight = max(0.0, 1.0 - s * s)

        # Plump, nearly circular/spherical proportion (~97% pure sphere with gentle lower fullness)
        # Plus subtle cheek puff on the direction of gaze (lx_clamped)
        cheek_bias = 1.0 + 0.048 * (c * lx_clamped) * mid_weight
        width_mod = (1.015 + 0.032 * s - 0.012 * (s ** 2)) * cheek_bias
        height_mod = 0.992 - 0.038 * (max(0.0, s) ** 2.2)

        # Subtle organic breathing harmonic
        ripple = R * 0.005 * math.sin(3 * th + pose.phase) + R * 0.003 * math.cos(4 * th - pose.phase * 1.2)

        # Elastic landing rebound wave on the lower hemisphere
        landing_wave = 0.0
        if pose.jelly_wave > 0.0:
            lower_mask = max(0.0, s + 0.25) / 1.25
            landing_wave = R * 0.042 * pose.jelly_wave * math.cos(5 * th + pose.phase * 2.0) * (lower_mask ** 1.6)

        boil = 0.0
        if boil_amp > 0:
            boil = boil_amp * math.sin(7 * th + boil_seed * 2.1) * math.cos(5 * th - boil_seed * 1.7)

        # 3D Head-Turn & Pitch Crown Shift (strictly 0 at bottom s=+1 so ground contact never slips)
        crown_lean_x = lx_clamped * R * 0.145 * upper_weight * (1.0 + 0.28 * abs(ly_clamped))
        crown_lift_y = ly_clamped * R * 0.095 * upper_weight

        lx = (R * width_mod + ripple + landing_wave + boil) * c * sx + crown_lean_x
        ly = (R * height_mod + ripple - landing_wave * 0.35 + boil) * s * sy + crown_lift_y

        rx = lx * cos_t - ly * sin_t
        ry = lx * sin_t + ly * cos_t
        pts.append((pose.x + rx, pose.y + ry))
    return pts


def eval_continuous_hop_chain(u: float, num_hops: int = 5, jump_height: float = 68.0) -> dict:
    """
    Continuous, fluid multi-hop walking/chasing rhythm ported from World 05 Paper:
    - First 12% of each hop: ground contact & anticipation crouch (y=0, squash_y compresses, forward pitch)
    - Remaining 88% of each hop: brisk parabolic arc with horizontal surge and velocity-coupled stretch/tilt.
    """
    t = max(0.0, min(1.0, float(u)))
    n = max(1, int(num_hops))
    phase = t * n
    hop_idx = min(n - 1, int(math.floor(phase)))
    local = phase - hop_idx

    base_linear = phase / n
    surge = (local - math.sin(local * math.tau) / math.tau) / n
    progress_x = max(0.0, min(1.0, base_linear + 0.35 * ((hop_idx + surge * n) / n - base_linear)))

    if local < 0.14:
        c = local / 0.14
        y_off = 0.0
        squash_y = 1.0 - 0.30 * math.sin(c * math.pi)
        tilt = 0.14 * math.sin(c * math.pi)
    else:
        air = (local - 0.14) / 0.86
        y_off = -math.sin(air * math.pi) * jump_height  # Negative Y is UP in screen coordinates
        vy = math.cos(air * math.pi)
        squash_y = 0.95 + abs(vy) * 0.27
        tilt = -vy * 0.16
    return {
        "y_off": y_off,
        "squash_y": squash_y,
        "tilt": tilt,
        "progress_x": progress_x,
        "hop_idx": hop_idx,
        "local": local,
    }


def eval_targeted_jump(u: float, x0: float, y0: float, x1: float, y1: float, arc_height: float = 140.0) -> dict:
    """
    Deliberate targeted jump ported from World 05 Paper:
    - Phase 1 (t < 0.20): Aiming crouch planted at (x0, y0)
    - Phase 2 (0.20 <= t < 0.86): Clean parabolic flight to (x1, y1)
    - Phase 3 (t >= 0.86): Landing cushion & elastic recovery planted at (x1, y1)
    """
    t = max(0.0, min(1.0, float(u)))
    direction = 1.0 if x1 >= x0 else -1.0
    if t < 0.20:
        c = t / 0.20
        x, y = x0, y0
        squash_y = 1.0 - 0.38 * math.sin(c * math.pi * 0.5)
        tilt = direction * c * 0.20
    elif t < 0.86:
        air = (t - 0.20) / 0.66
        s_air = air * air * (3.0 - 2.0 * air)
        x = x0 + (x1 - x0) * s_air
        y = y0 + (y1 - y0) * s_air - math.sin(air * math.pi) * arc_height
        vy = math.cos(air * math.pi)
        squash_y = 0.94 + abs(vy) * 0.30
        tilt = -direction * vy * 0.20
    else:
        land = (t - 0.86) / 0.14
        x, y = x1, y1
        squash_y = 1.0 - 0.30 * math.sin(land * math.pi)
        tilt = direction * (1.0 - land) * 0.10
    return {"x": x, "y": y, "squash_y": squash_y, "tilt": tilt}


def compute_3d_eye_projection(
    cx,
    cy: float = 0.0,
    radius: float = 100.0,
    squash_y: float = 1.0,
    tilt: float = 0.0,
    look_x: float = 0.45,
    look_y: float = -0.25,
    eye_scale: float = 1.0,
    eye_spacing: float = 1.0,
    base_cant_rad: float = 0.0,
):
    """
    Computes C^infinity smooth 3D spherical eye positions, dimensions, and rotation
    for any (look_x, look_y) head turn & pitch:
      - Look Left (look_x < 0): Left eye is far/smaller, Right eye is near/larger (左小右大).
      - Look Center / Straight Up / Straight Down (look_x == 0): Both eyes face the audience
        symmetrically with 100% EQUAL width & height (居中一样大, 上下看同样大小) and 0 deg horizontal cant!
      - Look Right (look_x > 0): Left eye is near/larger, Right eye is far/smaller (右小左大).
      - Diagonal Gaze (e.g. Upper-Right look_x > 0, look_y < 0): Naturally tilts the eye-line
        along the 3D sphere latitude/longitude (reaching ~ -26 deg at upper-right).
    """
    if isinstance(cx, SlimePose):
        p = cx
        cx = p.x
        cy = p.y
        radius = p.radius
        squash_y = p.squash_y
        tilt = p.tilt
        look_x = p.look_x
        look_y = p.look_y
        eye_scale = p.eye_scale
        eye_spacing = p.eye_spacing
    else:
        cx = float(cx)

    sy = max(0.45, min(2.2, float(squash_y)))
    sx = 1.0 / math.sqrt(sy)
    R = float(radius)

    lx = max(-1.0, min(1.0, float(look_x)))
    ly = max(-1.0, min(1.0, float(look_y)))

    yaw = lx * 0.85      # -49 deg .. +49 deg
    pitch = ly * 0.68    # -39 deg .. +39 deg

    coupled_tilt = tilt + lx * 0.065 - lx * ly * 0.055
    cos_t = math.cos(coupled_tilt)
    sin_t = math.sin(coupled_tilt)

    cant = lx * (-0.28 + 0.42 * ly)
    cos_c = math.cos(cant)
    sin_c = math.sin(cant)

    face_r = 0.54 * R
    gaze_cx = (face_r * math.sin(yaw) * math.cos(pitch * 0.42) + lx * R * 0.085) * sx
    gaze_cy = (face_r * math.sin(pitch) - 0.04 * R) * sy

    spacing_foreshorten = max(0.56, math.cos(yaw * 0.74))
    sep = R * 0.22 * eye_spacing * spacing_foreshorten

    lon_L = yaw - 0.32
    lon_R = yaw + 0.32
    foreshorten_w_L = max(0.45, min(1.06, math.cos(lon_L * 1.08)))
    foreshorten_w_R = max(0.45, min(1.06, math.cos(lon_R * 1.08)))
    max_fw = max(foreshorten_w_L, foreshorten_w_R, 1e-4)
    norm_w_L = foreshorten_w_L / max_fw
    norm_w_R = foreshorten_w_R / max_fw

    pitch_h = max(0.76, math.cos(pitch * 0.58))
    foreshorten_h_L = (0.82 + 0.18 * norm_w_L) * pitch_h
    foreshorten_h_R = (0.82 + 0.18 * norm_w_R) * pitch_h

    w_base = R * 0.115 * eye_scale
    h_base = R * 0.248 * eye_scale

    pitch_arch = -math.sin(pitch) * R * 0.055 * sy

    eyes = {}
    for side, key, nw, fh in [(-1, "left", norm_w_L, foreshorten_h_L), (+1, "right", norm_w_R, foreshorten_h_R)]:
        local_dx = side * sep * (0.72 + 0.28 * nw)
        local_dy = pitch_arch * (1.0 - nw)
        ex_local = gaze_cx + local_dx * cos_c - local_dy * sin_c
        ey_local = gaze_cy + local_dx * sin_c + local_dy * cos_c
        ex = cx + ex_local * cos_t - ey_local * sin_t
        ey = cy + ex_local * sin_t + ey_local * cos_t
        eyes[key] = {
            "x": ex,
            "y": ey,
            "w": w_base * nw,
            "h": h_base * fh,
            "angle": coupled_tilt + cant + side * lx * 0.03,
            "foreshorten": nw,
        }

    return {
        "left": eyes["left"],
        "right": eyes["right"],
        "gaze_cx": gaze_cx,
        "gaze_cy": gaze_cy,
        "shift_x": lx * R * 0.28 * sx,
        "shift_y": ly * R * 0.24 * sy,
        "coupled_tilt": coupled_tilt,
    }


def draw_four_point_star(ctx: cairo.Context, cx: float, cy: float, outer_r: float, inner_r: float = None, rot: float = 0.0):
    """Draws the signature 4-pointed curved sparkle star (✦) with smooth concave Bezier arcs."""
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


def draw_capsule_pill(ctx: cairo.Context, cx: float, cy: float, half_w: float, half_h: float):
    """Draws a perfectly rounded pill / capsule centered at (cx, cy) with half-width half_w and half-height half_h."""
    w = max(1.5, half_w)
    h = max(1.5, half_h)
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


def draw_slime_path(ctx: cairo.Context, pts: list[tuple[float, float]]):
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


def draw_pixel_slime_icon(surface: cairo.ImageSurface, cx: float, cy: float, scale: int = 4):
    """Draws a crisp 16-bit Pixel RPG Slime sprite (round dark-indigo body + white capsule eyes + star satellite)."""
    pil_img = cairo_to_pil(surface)
    pw, ph = 48, 48
    sp = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    sx0, sy0 = 24, 27
    # Shadow
    d.ellipse([sx0 - 15, sy0 + 13, sx0 + 15, sy0 + 17], fill=(30, 44, 96, 160))
    # Plump spherical dark-indigo body + cyan/violet rim
    d.ellipse([sx0 - 16, sy0 - 15, sx0 + 16, sy0 + 15], fill=(12, 16, 40, 255), outline=(76, 224, 255, 255))
    d.ellipse([sx0 - 14, sy0 - 13, sx0 + 14, sy0 + 13], fill=(22, 34, 82, 255))
    d.ellipse([sx0 - 11, sy0 - 10, sx0 + 12, sy0 + 12], fill=(14, 19, 44, 255))
    # Two pure white capsule eyes on upper-right
    d.rounded_rectangle([sx0 - 1, sy0 - 9, sx0 + 3, sy0 - 1], radius=2, fill=(255, 255, 255, 255))
    d.rounded_rectangle([sx0 + 6, sy0 - 11, sx0 + 9, sy0 - 3], radius=1, fill=(255, 255, 255, 255))
    # Floating pixel star satellite
    st_x, st_y = sx0 - 2, sy0 - 21
    d.line([st_x - 4, st_y, st_x + 4, st_y], fill=(255, 225, 95, 255))
    d.line([st_x, st_y - 4, st_x, st_y + 4], fill=(100, 232, 255, 255))
    d.rectangle([st_x - 1, st_y - 1, st_x + 1, st_y + 1], fill=(255, 255, 255, 255))

    up = sp.resize((pw * scale, ph * scale), resample=Image.Resampling.NEAREST)
    pil_img.alpha_composite(up, (int(cx - (pw * scale) // 2), int(cy - (ph * scale) // 2)))
    return pil_to_cairo(pil_img)


def _draw_satellite_star(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    r: float,
    rot: float = 0.0,
    style: str = "aurora",
    color_mode: str = "aurora",
):
    """Renders a floating 4-point Star Satellite (✦) with luminous halo and aurora gradient."""
    ctx.save()
    if style != "blueprint":
        aura = cairo.RadialGradient(cx, cy, r * 0.1, cx, cy, r * 1.95)
        if color_mode == "cyan":
            aura.add_color_stop_rgba(0.0, 0.30, 0.90, 1.0, 0.55)
            aura.add_color_stop_rgba(1.0, 0.20, 0.65, 1.0, 0.0)
        elif color_mode == "gold":
            aura.add_color_stop_rgba(0.0, 1.0, 0.82, 0.28, 0.55)
            aura.add_color_stop_rgba(1.0, 1.0, 0.60, 0.15, 0.0)
        else:
            aura.add_color_stop_rgba(0.0, 0.55, 0.86, 1.0, 0.52)
            aura.add_color_stop_rgba(0.55, 0.62, 0.45, 1.0, 0.24)
            aura.add_color_stop_rgba(1.0, 0.45, 0.35, 0.95, 0.0)
        ctx.set_source(aura)
        ctx.arc(cx, cy, r * 1.95, 0, math.tau)
        ctx.fill()

    draw_four_point_star(ctx, cx, cy, r, r * 0.26, rot=rot)
    if style == "blueprint":
        ctx.set_source_rgba(0.15, 0.38, 0.75, 0.95)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.95, 0.98, 1.0, 0.98)
        ctx.set_line_width(2.4)
        ctx.stroke()
    elif style == "anime":
        ctx.set_source_rgba(1.0, 0.88, 0.22, 1.0)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.09, 0.04, 0.16, 1.0)
        ctx.set_line_width(max(2.0, r * 0.12))
        ctx.stroke()
    elif style == "paper":
        ctx.set_source_rgba(1.0, 0.84, 0.30, 1.0)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.98, 0.96, 0.90, 1.0)
        ctx.set_line_width(max(2.8, r * 0.16))
        ctx.stroke()
    else:
        # Star-Spark Aurora Gradient: Sky Blue (#4285F4) -> Iris Violet (#9B72CB) -> Rose-Coral (#D96570) -> Gold
        sg = cairo.LinearGradient(cx - r * 0.9, cy - r * 0.6, cx + r * 0.9, cy + r * 0.6)
        if color_mode == "cyan":
            sg.add_color_stop_rgba(0.0, 0.26, 0.82, 1.0, 1.0)
            sg.add_color_stop_rgba(0.5, 0.32, 0.58, 0.98, 1.0)
            sg.add_color_stop_rgba(1.0, 0.58, 0.42, 0.96, 1.0)
        elif color_mode == "gold":
            sg.add_color_stop_rgba(0.0, 0.96, 0.42, 0.54, 1.0)
            sg.add_color_stop_rgba(0.5, 0.98, 0.64, 0.36, 1.0)
            sg.add_color_stop_rgba(1.0, 1.00, 0.84, 0.28, 1.0)
        else:
            sg.add_color_stop_rgba(0.00, 0.259, 0.522, 0.957, 1.0)  # #4285F4 Sky Blue
            sg.add_color_stop_rgba(0.45, 0.608, 0.447, 0.796, 1.0)  # #9B72CB Iris Violet
            sg.add_color_stop_rgba(0.82, 0.851, 0.396, 0.439, 1.0)  # #D96570 Rose-Coral
            sg.add_color_stop_rgba(1.00, 0.984, 0.749, 0.141, 1.0)  # #FBBF24 Warm Starlight Gold
        ctx.set_source(sg)
        ctx.fill_preserve()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        ctx.set_line_width(max(1.5, r * 0.08))
        ctx.stroke()
    ctx.restore()


def draw_slime_character(
    ctx: cairo.Context,
    pose: SlimePose,
    style: str = "aurora",
    tint_override: tuple = None,
):
    """
    Renders the Star-Spark Slime (饱满偏圆球体 + 无嘴3D球面透视胶囊眼 + 蓝紫粉极光渐变果冻质感 + 头顶磁悬浮四角星芒伴星):
      - Default/"aurora" : Aurora Palette (#4285F4 Blue -> #8E5CF7 Iris Violet -> #D96570 Rose-Coral) + pure white 3D capsule eyes
      - Also supports "crt", "anime", "paper", "blueprint" for multi-style scenes.
    """
    sy = max(0.45, min(2.2, pose.squash_y))
    sx = 1.0 / math.sqrt(sy)
    R = pose.radius
    boil_amp = 2.0 if style == "anime" else (1.0 if style == "paper" else 0.0)
    pts = compute_slime_contour(pose, n_pts=108, boil_amp=boil_amp, boil_seed=int(pose.phase * 10) + 3)
    cos_t, sin_t = math.cos(pose.tilt), math.sin(pose.tilt)

    # --- 0. SOFT GROUND CONTACT SHADOW (Tinted with Violet-Blue) ---
    if pose.draw_shadow and style not in ("blueprint", "crt"):
        sh_x = pose.x
        sh_y = pose.y + R * min(1.08, sy * 0.95)
        sh_rx = R * sx * (1.02 if sy <= 1.05 else max(0.52, 1.15 - 0.38 * sy))
        sh_ry = max(8.0, R * 0.20)
        ctx.save()
        ctx.translate(sh_x, sh_y)
        ctx.scale(sh_rx, sh_ry)
        sh_grad = cairo.RadialGradient(0, 0, 0.05, 0, 0, 1.0)
        sh_alpha = 0.26 if sy <= 1.05 else max(0.10, 0.32 - 0.14 * sy)
        sh_grad.add_color_stop_rgba(0.0, 0.22, 0.26, 0.58, sh_alpha)
        sh_grad.add_color_stop_rgba(0.55, 0.38, 0.28, 0.68, sh_alpha * 0.48)
        sh_grad.add_color_stop_rgba(1.0, 0.38, 0.28, 0.68, 0.0)
        ctx.set_source(sh_grad)
        ctx.arc(0, 0, 1.0, 0, math.tau)
        ctx.fill()
        ctx.restore()

    # --- 1. STYLE: PAPER POP-UP / LIGHTBOX ---
    if style == "paper":
        ctx.save()
        ctx.translate(8, 12)
        draw_slime_path(ctx, pts)
        ctx.set_source_rgba(0.03, 0.05, 0.12, 0.45)
        ctx.fill()
        ctx.restore()

        ctx.save()
        draw_slime_path(ctx, pts)
        ctx.set_source_rgba(0.98, 0.96, 0.90, 1.0)
        ctx.set_line_width(14.0)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
        ctx.restore()

        draw_slime_path(ctx, pts)
        grad = cairo.RadialGradient(pose.x - R * 0.22, pose.y - R * 0.25, R * 0.1, pose.x, pose.y, R * 1.15)
        grad.add_color_stop_rgba(0.0, 0.32, 0.62, 0.98, 1.0)
        grad.add_color_stop_rgba(0.60, 0.55, 0.42, 0.88, 1.0)
        grad.add_color_stop_rgba(1.0, 0.82, 0.40, 0.52, 1.0)
        ctx.set_source(grad)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.22, 0.14, 0.10, 0.95)
        ctx.set_line_width(4.0)
        ctx.stroke()

    # --- 2. STYLE: BLUEPRINT DRAFTING ---
    elif style == "blueprint":
        draw_slime_path(ctx, pts)
        grad = cairo.RadialGradient(pose.x, pose.y - R * 0.15, R * 0.1, pose.x, pose.y, R * 1.15)
        grad.add_color_stop_rgba(0.0, 0.18, 0.42, 0.78, 0.94)
        grad.add_color_stop_rgba(1.0, 0.08, 0.20, 0.48, 0.98)
        ctx.set_source(grad)
        ctx.fill_preserve()

        ctx.save()
        ctx.clip()
        ctx.set_source_rgba(0.88, 0.95, 1.0, 0.22)
        ctx.set_line_width(1.3)
        for d in range(-int(R * 2), int(R * 2), 11):
            if d > R * 0.15:
                ctx.move_to(pose.x + d - R, pose.y + R)
                ctx.line_to(pose.x + d + R, pose.y - R)
        ctx.stroke()
        ctx.restore()

        draw_slime_path(ctx, pts)
        ctx.set_source_rgba(0.92, 0.97, 1.0, 0.98)
        ctx.set_line_width(3.4)
        ctx.stroke()

    # --- 3. STYLE: 80s CEL ANIME / SCI-FI TOON ---
    elif style == "anime":
        draw_slime_path(ctx, pts)
        r0, g0, b0 = tint_override if tint_override else (0.26, 0.52, 0.96)
        ctx.set_source_rgba(r0, g0, b0, 1.0)
        ctx.fill_preserve()

        ctx.save()
        ctx.clip()
        ctx.translate(R * 0.08, R * 0.08)
        draw_slime_path(ctx, pts)
        ctx.set_source_rgba(0.88, 0.40, 0.68, 0.85)
        ctx.set_line_width(6.5)
        ctx.stroke()
        ctx.restore()

        draw_slime_path(ctx, pts)
        ctx.set_source_rgba(0.08, 0.04, 0.18, 1.0)
        ctx.set_line_width(6.5)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()

    # --- 4. STYLE: CRT TERMINAL ---
    elif style == "crt":
        for w_line, alpha in [(16.0, 0.10), (9.0, 0.22), (3.8, 0.92)]:
            draw_slime_path(ctx, pts)
            ctx.set_source_rgba(0.20, 0.95, 0.85, alpha)
            ctx.set_line_width(w_line)
            ctx.stroke()
        draw_slime_path(ctx, pts)
        ctx.save()
        ctx.clip()
        ctx.set_source_rgba(0.03, 0.16, 0.22, 0.82)
        ctx.paint()
        ctx.set_source_rgba(0.25, 1.0, 0.90, 0.18)
        for sy_line in range(int(pose.y - R * 1.6), int(pose.y + R * 1.6), 6):
            ctx.rectangle(pose.x - R * 1.6, sy_line, R * 3.2, 1.8)
        ctx.fill()
        ctx.restore()

    # --- 5. CORE AURORA LOOK: SKY BLUE -> IRIS VIOLET -> ROSE-CORAL ---
    else:
        # Soft outer aurora glow
        for expand, alpha in [(1.10, 0.08), (1.04, 0.15)]:
            ctx.save()
            ctx.translate(pose.x, pose.y)
            ctx.scale(expand, expand)
            ctx.translate(-pose.x, -pose.y)
            draw_slime_path(ctx, pts)
            ctx.set_source_rgba(0.35, 0.52, 0.98, alpha)
            ctx.fill()
            ctx.restore()

        draw_slime_path(ctx, pts)
        if pose.shape_aware_gradient:
            grad = cairo.RadialGradient(-R * 0.32, -R * 0.34, R * 0.08, R * 0.18, R * 0.24, R * 1.28)
            body_m = cairo.Matrix()
            body_m.translate(pose.x, pose.y)
            body_m.rotate(pose.tilt)
            body_m.scale(sx, sy)
            body_m.invert()
            grad.set_matrix(body_m)
        else:
            grad = cairo.RadialGradient(
                pose.x - R * 0.32 * sx, pose.y - R * 0.34 * sy, R * 0.08,
                pose.x + R * 0.18 * sx, pose.y + R * 0.24 * sy, R * 1.28
            )
        if tint_override:
            r0, g0, b0 = tint_override
            grad.add_color_stop_rgba(0.0, min(1.0, r0 + 0.25), min(1.0, g0 + 0.25), min(1.0, b0 + 0.25), 1.0)
            grad.add_color_stop_rgba(0.55, r0, g0, b0, 1.0)
            grad.add_color_stop_rgba(1.0, r0 * 0.65, g0 * 0.45, b0 * 0.78, 1.0)
        else:
            coral = pose.coral_rgb if pose.coral_rgb else (0.875, 0.388, 0.470)
            grad.add_color_stop_rgba(0.00, 0.310, 0.680, 1.000, 1.0)  # #4FADFF Luminous Sky Blue
            grad.add_color_stop_rgba(0.30, 0.235, 0.470, 0.960, 1.0)  # #3C78F5 Royal Sky Blue (#4285F4)
            grad.add_color_stop_rgba(0.62, 0.460, 0.350, 0.910, 1.0)  # #7559E8 Iris Indigo-Violet
            grad.add_color_stop_rgba(0.86, 0.680, 0.380, 0.820, 1.0)  # #AD61D1 Orchid Purple
            grad.add_color_stop_rgba(1.00, coral[0], coral[1], coral[2], 1.0)  # #DF6378 Dawn Rose-Coral (#D96570)
        ctx.set_source(grad)
        ctx.fill_preserve()

        ctx.save()
        ctx.clip()

        # Subtle warm Rose-Coral subsurface bounce glow on the lower-right belly
        belly_g = cairo.RadialGradient(
            pose.x + R * 0.38 * sx, pose.y + R * 0.46 * sy, R * 0.05,
            pose.x + R * 0.25 * sx, pose.y + R * 0.35 * sy, R * 0.85
        )
        if pose.coral_rgb:
            belly_g.add_color_stop_rgba(0.0, 0.95, 0.60, 0.54, 0.40)
            belly_g.add_color_stop_rgba(0.55, 0.80, 0.50, 0.72, 0.16)
        else:
            belly_g.add_color_stop_rgba(0.0, 0.96, 0.44, 0.52, 0.52)   # Warm Coral-Pink glow
            belly_g.add_color_stop_rgba(0.55, 0.76, 0.38, 0.78, 0.22)
        belly_g.add_color_stop_rgba(1.0, 0.46, 0.35, 0.91, 0.0)
        ctx.set_source(belly_g)
        ctx.arc(pose.x + R * 0.25 * sx, pose.y + R * 0.35 * sy, R * 0.85, 0, math.tau)
        ctx.fill()

        # Optional Internal Twin-Star Nebula Core
        if pose.show_twin_core:
            orb_ang = pose.phase * 0.8
            k = pose.twin_core_scale
            core_dy = R * pose.twin_core_dy * sy
            c1_x = pose.x - R * 0.28 * k * sx * math.cos(orb_ang)
            c1_y = pose.y + core_dy + R * 0.10 * k * sy * math.sin(orb_ang)
            c2_x = pose.x + R * 0.28 * k * sx * math.cos(orb_ang)
            c2_y = pose.y + core_dy - R * 0.10 * k * sy * math.sin(orb_ang)

            ctx.save()
            ctx.translate(pose.x, pose.y + core_dy)
            ctx.rotate(-0.22)
            ctx.scale(R * 0.56 * k * sx, R * 0.22 * k * sy)
            ctx.arc(0, 0, 1.0, 0, math.tau)
            ctx.set_source_rgba(0.85, 0.95, 1.0, 0.45)
            ctx.set_line_width(0.06)
            ctx.stroke()
            ctx.restore()

            for cx_c, cy_c, col_c in [
                (c1_x, c1_y, (0.35, 0.92, 1.00, 0.62)),  # Ice Cyan Core
                (c2_x, c2_y, (1.00, 0.80, 0.28, 0.62)),  # Warm Star Gold Core
            ]:
                cg = cairo.RadialGradient(cx_c, cy_c, 1.0, cx_c, cy_c, R * 0.36 * k)
                cg.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, col_c[3] * 1.1)
                cg.add_color_stop_rgba(0.35, col_c[0], col_c[1], col_c[2], col_c[3])
                cg.add_color_stop_rgba(1.0, col_c[0], col_c[1], col_c[2], 0.0)
                ctx.set_source(cg)
                ctx.arc(cx_c, cy_c, R * 0.36 * k, 0, math.tau)
                ctx.fill()
                draw_four_point_star(ctx, cx_c, cy_c, R * 0.11 * k, R * 0.03 * k, rot=pose.phase)
                ctx.set_source_rgba(1.0, 1.0, 1.0, 0.88)
                ctx.fill()

        # Translucent Jelly Fresnel Inner Rim Glow (Cyan-Blue top-left -> Rose-Pink bottom-right)
        for lw, alpha_m in [(R * 0.18, 0.12), (R * 0.09, 0.24)]:
            draw_slime_path(ctx, pts)
            fresnel_layer = cairo.LinearGradient(
                pose.x - R * sx, pose.y - R * sy,
                pose.x + R * sx, pose.y + R * sy
            )
            fresnel_layer.add_color_stop_rgba(0.00, 0.55, 0.92, 1.00, alpha_m)
            fresnel_layer.add_color_stop_rgba(0.50, 0.62, 0.48, 0.98, alpha_m * 0.6)
            fresnel_layer.add_color_stop_rgba(1.00, 0.98, 0.52, 0.62, alpha_m)
            ctx.set_source(fresnel_layer)
            ctx.set_line_width(lw)
            ctx.stroke()

        # Glossy Jelly Highlight on upper-left dome
        ctx.save()
        ctx.translate(pose.x - R * 0.40 * sx, pose.y - R * 0.42 * sy)
        ctx.rotate(-0.62 + pose.tilt * 0.5)
        ctx.scale(1.0, 0.44)
        spec_g = cairo.RadialGradient(0, 0, R * 0.02, 0, 0, R * 0.30)
        spec_g.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.58)
        spec_g.add_color_stop_rgba(0.6, 0.78, 0.94, 1.0, 0.22)
        spec_g.add_color_stop_rgba(1.0, 0.45, 0.80, 1.0, 0.0)
        ctx.set_source(spec_g)
        ctx.arc(0, 0, R * 0.30, 0, math.tau)
        ctx.fill()
        ctx.restore()

        ctx.restore()  # End body clip

        # Crisp outer contour edge
        draw_slime_path(ctx, pts)
        edge_grad = cairo.LinearGradient(pose.x - R * sx, pose.y - R * sy, pose.x + R * sx, pose.y + R * sy)
        edge_grad.add_color_stop_rgba(0.00, 0.18, 0.42, 0.88, 0.92)
        edge_grad.add_color_stop_rgba(0.55, 0.36, 0.26, 0.78, 0.92)
        edge_grad.add_color_stop_rgba(1.00, 0.68, 0.26, 0.44, 0.92)
        ctx.set_source(edge_grad)
        ctx.set_line_width(max(2.4, R * 0.025))
        ctx.stroke()

    # --- 6. MOUTHLESS 3D SPHERICAL CAPSULE EYE SYSTEM (无嘴 + 球面透视胶囊眼神系统) ---
    effective_mode = pose.eye_mode
    if pose.wink_left > 0.5 and pose.wink_right > 0.5 and effective_mode == "pill":
        effective_mode = "happy_arc"

    mode_sep_mult = 1.24 if effective_mode in ("flat", "happy_arc", "star") else 1.0
    base_cant = pose.eye_cant if abs(pose.eye_cant) > 1e-4 else -0.5235987756
    proj = compute_3d_eye_projection(
        cx=pose.x,
        cy=pose.y,
        radius=R,
        squash_y=sy,
        tilt=pose.tilt,
        look_x=pose.look_x,
        look_y=pose.look_y,
        eye_scale=pose.eye_scale,
        eye_spacing=pose.eye_spacing * mode_sep_mult,
        base_cant_rad=base_cant,
    )

    for side, key in [(-1, "left"), (+1, "right")]:
        esp = proj[key]
        if effective_mode == "asymmetric" and pose.left_eye_scale == (1.0, 1.0) and pose.right_eye_scale == (1.0, 1.0):
            ew_mult, eh_mult = (1.16, 1.28) if side == -1 else (0.86, 0.72)
            local_dy = (-0.055 * R) if side == -1 else (+0.055 * R)
        else:
            ew_mult, eh_mult = pose.left_eye_scale if side == -1 else pose.right_eye_scale
            local_dy = (pose.left_eye_dy if side == -1 else pose.right_eye_dy) * R

        ex = esp["x"] - local_dy * math.sin(esp["angle"])
        ey = esp["y"] + local_dy * math.cos(esp["angle"])
        w_eye = esp["w"] * ew_mult
        h_eye = esp["h"] * eh_mult

        ctx.save()
        ctx.translate(ex, ey)
        ctx.rotate(esp["angle"])

        side_wink = pose.wink_left if side == -1 else pose.wink_right
        if effective_mode == "happy_arc" or side_wink > 0.5:
            arc_r = h_eye * 0.56
            arc_lw = max(3.5, w_eye * 1.16)
            ctx.new_path()
            ctx.arc(0, arc_r * 0.35, arc_r, math.pi * 1.15, math.pi * 1.85)
            ctx.set_source_rgba(0.14, 0.22, 0.58, 0.42)
            ctx.set_line_width(arc_lw + 4.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke_preserve()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.set_line_width(arc_lw)
            ctx.stroke()
        elif effective_mode == "flat":
            flat_w = w_eye * 1.48
            flat_h = w_eye * 0.46
            draw_capsule_pill(ctx, 0, 0, flat_w + 2.5, flat_h + 2.5)
            ctx.set_source_rgba(0.14, 0.22, 0.58, 0.40)
            ctx.fill()
            draw_capsule_pill(ctx, 0, 0, flat_w, flat_h)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.fill()
        elif effective_mode == "star":
            sr_outer = h_eye * 0.78
            sr_inner = w_eye * 0.44
            draw_four_point_star(ctx, 0, 0, sr_outer * 1.22, sr_inner * 1.22, rot=0.0)
            ctx.set_source_rgba(0.14, 0.22, 0.58, 0.38)
            ctx.fill()
            draw_four_point_star(ctx, 0, 0, sr_outer, sr_inner, rot=0.0)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.fill()
        else:
            draw_capsule_pill(ctx, 0, 1.2, w_eye + 2.6, h_eye + 2.6)
            ctx.set_source_rgba(0.12, 0.20, 0.56, 0.36)
            ctx.fill()

            draw_capsule_pill(ctx, 0, 0, w_eye, h_eye)
            if style == "blueprint":
                ctx.set_source_rgba(0.95, 0.98, 1.0, 0.98)
            elif style == "crt":
                ctx.set_source_rgba(0.75, 1.0, 0.96, 0.98)
            else:
                ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            ctx.fill()

        ctx.restore()

    # --- 7. FLOATING 4-POINT STAR SATELLITE (✦ 头顶磁悬浮四角星芒伴星) ---
    crown_local_x = pose.star_offset_x
    crown_local_y = -R * sy * 1.22 + pose.star_offset_y - 4.0 * math.sin(pose.phase * 1.5)
    star_cx = pose.x + crown_local_x * cos_t - crown_local_y * sin_t
    star_cy = pose.y + crown_local_x * sin_t + crown_local_y * cos_t
    star_r = R * 0.23 * pose.star_scale

    crown_top_x = pose.x - (-R * sy * 0.98) * sin_t
    crown_top_y = pose.y + (-R * sy * 0.98) * cos_t
    for t_dot, r_dot in [(0.35, max(1.8, R * 0.022)), (0.65, max(2.2, R * 0.028))]:
        dx_d = crown_top_x + (star_cx - crown_top_x) * t_dot
        dy_d = crown_top_y + (star_cy - crown_top_y) * t_dot
        ctx.arc(dx_d, dy_d, r_dot, 0, math.tau)
        ctx.set_source_rgba(0.45, 0.86, 1.0, 0.55)
        ctx.fill()

    if pose.twin_stars:
        sep_s = star_r * 1.28
        _draw_satellite_star(ctx, star_cx - sep_s, star_cy + 4.0, star_r * 0.88, rot=pose.star_rot - 0.18, style=style, color_mode="cyan")
        _draw_satellite_star(ctx, star_cx + sep_s, star_cy - 4.0, star_r * 0.88, rot=pose.star_rot + 0.18, style=style, color_mode="gold")
    else:
        _draw_satellite_star(ctx, star_cx, star_cy, star_r, rot=pose.star_rot, style=style, color_mode="aurora")


# =========================================================================
# 8. SECOND-ORDER SPRING-DAMPER PHYSICS & 9 CONCRETE PHYSICAL TOKENS (信物)
# =========================================================================


class SpringDamper1D:
    """
    Analytical/semi-implicit 2nd-order spring-damper filter for C^2 smooth
    character motion, squash-and-stretch, body tilt, and gaze tracking.
    Eliminates piecewise-linear velocity discontinuities (twitching/popping).
    """
    def __init__(self, x0: float = 0.0, v0: float = 0.0, freq: float = 4.5, zeta: float = 0.72):
        self.x = float(x0)
        self.v = float(v0)
        self.freq = float(freq)
        self.zeta = float(zeta)

    def step(self, target: float, dt: float, freq: Optional[float] = None, zeta: Optional[float] = None) -> float:
        f = self.freq if freq is None else float(freq)
        z = self.zeta if zeta is None else float(zeta)
        omega = 2.0 * math.pi * f
        substeps = max(1, int(math.ceil(dt * omega * 2.0)))
        h = dt / substeps
        for _ in range(substeps):
            acc = (omega * omega) * (target - self.x) - (2.0 * z * omega) * self.v
            self.v += acc * h
            self.x += self.v * h
        return self.x

    def impulse(self, dv: float):
        self.v += float(dv)


class SpringDamper2D:
    """2D coupled spring-damper for (look_x, look_y) or (x, y) trajectories."""
    def __init__(self, x0: float = 0.0, y0: float = 0.0, freq: float = 4.2, zeta: float = 0.75):
        self.sx = SpringDamper1D(x0, 0.0, freq=freq, zeta=zeta)
        self.sy = SpringDamper1D(y0, 0.0, freq=freq, zeta=zeta)

    def step(self, tx: float, ty: float, dt: float, freq: Optional[float] = None, zeta: Optional[float] = None) -> Tuple[float, float]:
        return (
            self.sx.step(tx, dt, freq=freq, zeta=zeta),
            self.sy.step(ty, dt, freq=freq, zeta=zeta),
        )


WORLD_TOKEN_META = {
    1: {"id": "crt_keycap",        "object_cn": "磷光回车键帽 [↵]",   "rationale_cn": "指令 / 唤醒", "rationale_en": "Command"},
    2: {"id": "pixel_coin",        "object_cn": "16-Bit 像素游戏币",  "rationale_cn": "玩 / 游戏",   "rationale_en": "Play"},
    3: {"id": "cyber_shard",       "object_cn": "涂鸦破框锐片",       "rationale_cn": "破界",        "rationale_en": "Breakthrough"},
    4: {"id": "ink_seal",          "object_cn": "微缩朱砂墨印",       "rationale_cn": "留白 / 意境", "rationale_en": "Ink & Blank"},
    5: {"id": "origami_crane",     "object_cn": "折纸小千纸鹤",       "rationale_cn": "陪伴",        "rationale_en": "Companionship"},
    6: {"id": "glass_bell",        "object_cn": "彩绘琉璃小钟铃",     "rationale_cn": "回响 / 共鸣", "rationale_en": "Resonance"},
    7: {"id": "vinyl_note",        "object_cn": "黑胶唱片与八分音符", "rationale_cn": "律动 / 摇摆", "rationale_en": "Swing"},
    8: {"id": "clay_charm",        "object_cn": "指纹软陶徽章",       "rationale_cn": "手作 / 造物", "rationale_en": "Handmade"},
    9: {"id": "blueprint_compass", "object_cn": "精密工程圆规",       "rationale_cn": "构想 / 升维", "rationale_en": "Dimension"},
}


def draw_rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float):
    r = max(0.0, min(r, w * 0.5, h * 0.5))
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi * 0.5, 0.0)
    ctx.arc(x + w - r, y + h - r, r, 0.0, math.pi * 0.5)
    ctx.arc(x + r, y + h - r, r, math.pi * 0.5, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, math.pi * 1.5)
    ctx.close_path()


def draw_world_token(
    ctx: cairo.Context,
    world_num: int,
    cx: float,
    cy: float,
    r: float,
    rot: float = 0.0,
    t: float = 0.0,
    alpha: float = 1.0,
):
    """
    Draws the concrete physical collectible token (信物) for Worlds 1..9.
    NOTE: Never draw abstract rationale subtitles on screen — the physical object
    itself communicates the world's essence.
    """
    if alpha <= 0.01 or r <= 0.5:
        return

    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(rot)

    aura = cairo.RadialGradient(0, 0, r * 0.15, 0, 0, r * 1.45)
    aura.add_color_stop_rgba(0.0, 1.0, 0.96, 0.82, 0.42 * alpha)
    aura.add_color_stop_rgba(0.6, 0.45, 0.78, 1.0, 0.18 * alpha)
    aura.add_color_stop_rgba(1.0, 0.25, 0.50, 1.0, 0.0)
    ctx.set_source(aura)
    ctx.arc(0, 0, r * 1.45, 0, 2 * math.pi)
    ctx.fill()

    w_idx = ((int(world_num) - 1) % 9) + 1

    if w_idx == 1:
        # 1. Phosphor Enter Keycap [ ↵ ] (磷光回车键帽)
        kw, kh = r * 1.45, r * 1.22
        draw_rounded_rect(ctx, -kw * 0.5, -kh * 0.5 + r * 0.08, kw, kh, r * 0.22)
        ctx.set_source_rgba(0.04, 0.18, 0.10, 0.95 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.18, 1.0, 0.55, 0.95 * alpha)
        ctx.set_line_width(max(1.5, r * 0.09))
        ctx.stroke()
        iw, ih = kw * 0.78, kh * 0.74
        draw_rounded_rect(ctx, -iw * 0.5, -ih * 0.5 - r * 0.03, iw, ih, r * 0.14)
        ctx.set_source_rgba(0.06, 0.28, 0.16, 0.95 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(1.0, 0.78, 0.22, 0.92 * alpha)
        ctx.set_line_width(max(1.2, r * 0.06))
        ctx.stroke()
        ctx.set_source_rgba(0.55, 1.0, 0.78, 0.98 * alpha)
        ctx.set_line_width(max(1.8, r * 0.11))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.move_to(r * 0.24, -r * 0.22)
        ctx.line_to(r * 0.24, r * 0.10)
        ctx.line_to(-r * 0.24, r * 0.10)
        ctx.stroke()
        ctx.move_to(-r * 0.10, -r * 0.06)
        ctx.line_to(-r * 0.26, r * 0.10)
        ctx.line_to(-r * 0.10, r * 0.26)
        ctx.stroke()

    elif w_idx == 2:
        # 2. 16-Bit Pixel Arcade Coin (16-Bit 像素游戏币)
        px = max(2.0, r * 0.16)
        for gy in range(-5, 6):
            for gx in range(-4, 5):
                if abs(gx) * 1.15 + abs(gy) * 0.95 <= 5.6:
                    is_edge = (abs(gx) * 1.15 + abs(gy) * 0.95 >= 4.4)
                    is_slot = (gx == 0 and -2 <= gy <= 2)
                    if is_edge:
                        ctx.set_source_rgba(0.85, 0.45, 0.05, 0.98 * alpha)
                    elif is_slot:
                        ctx.set_source_rgba(0.72, 0.35, 0.04, 0.98 * alpha)
                    elif gx < 0 or gy < -2:
                        ctx.set_source_rgba(1.0, 0.92, 0.32, 0.98 * alpha)
                    else:
                        ctx.set_source_rgba(1.0, 0.76, 0.12, 0.98 * alpha)
                    ctx.rectangle(gx * px - px * 0.5, gy * px - px * 0.5, px * 1.02, px * 1.02)
                    ctx.fill()

    elif w_idx == 3:
        # 3. Shattered Graffiti Frame Shard (涂鸦破框锐片)
        ctx.move_to(-r * 0.95, -r * 0.78)
        ctx.line_to(r * 0.88, -r * 0.92)
        ctx.line_to(r * 0.42, -r * 0.35)
        ctx.line_to(-r * 0.32, -r * 0.28)
        ctx.line_to(-r * 0.38, r * 0.88)
        ctx.line_to(-r * 0.88, r * 0.52)
        ctx.close_path()
        ctx.set_source_rgba(0.48, 0.17, 0.75, 0.96 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.05, 0.05, 0.08, 0.98 * alpha)
        ctx.set_line_width(max(2.0, r * 0.11))
        ctx.stroke()
        ctx.move_to(-r * 0.52, -r * 0.48)
        ctx.line_to(r * 1.05, -r * 0.18)
        ctx.line_to(r * 0.18, r * 0.95)
        ctx.line_to(-r * 0.18, r * 0.22)
        ctx.close_path()
        ctx.set_source_rgba(1.0, 0.90, 0.0, 0.98 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.0, 0.96, 0.83, 0.95 * alpha)
        ctx.set_line_width(max(1.5, r * 0.08))
        ctx.stroke()

    elif w_idx == 4:
        # 4. Cinnabar Ink Seal Stamp (微缩朱砂墨印)
        s = r * 1.18
        draw_rounded_rect(ctx, -s * 0.5, -s * 0.5, s, s, r * 0.12)
        ctx.set_source_rgba(0.72, 0.16, 0.11, 0.96 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.98, 0.95, 0.88, 0.95 * alpha)
        ctx.set_line_width(max(1.5, r * 0.08))
        ctx.stroke()
        ctx.set_source_rgba(0.98, 0.95, 0.88, 0.95 * alpha)
        ctx.set_line_width(max(1.5, r * 0.09))
        ctx.move_to(-s * 0.26, -s * 0.24)
        ctx.line_to(s * 0.26, -s * 0.24)
        ctx.move_to(0, -s * 0.32)
        ctx.line_to(0, s * 0.30)
        ctx.move_to(-s * 0.22, s * 0.06)
        ctx.line_to(s * 0.22, s * 0.06)
        ctx.move_to(-s * 0.28, s * 0.28)
        ctx.line_to(s * 0.28, s * 0.28)
        ctx.stroke()

    elif w_idx == 5:
        # 5. Origami Mini Crane (折纸小千纸鹤)
        flap = math.sin(t * 8.0) * r * 0.16
        ctx.move_to(0, 0)
        ctx.line_to(-r * 0.98, -r * 0.45 + flap)
        ctx.line_to(-r * 0.28, r * 0.18)
        ctx.close_path()
        ctx.set_source_rgba(1.0, 0.86, 0.55, 0.96 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.68, 0.42, 0.22, 0.85 * alpha)
        ctx.set_line_width(max(1.2, r * 0.06))
        ctx.stroke()
        ctx.move_to(-r * 0.35, r * 0.22)
        ctx.line_to(0, -r * 0.32)
        ctx.line_to(r * 0.42, r * 0.22)
        ctx.close_path()
        ctx.set_source_rgba(0.98, 0.62, 0.48, 0.96 * alpha)
        ctx.fill()
        ctx.move_to(r * 0.22, r * 0.12)
        ctx.line_to(r * 0.78, -r * 0.58)
        ctx.line_to(r * 0.96, -r * 0.42)
        ctx.line_to(r * 0.42, r * 0.22)
        ctx.close_path()
        ctx.set_source_rgba(1.0, 0.92, 0.75, 0.98 * alpha)
        ctx.fill()
        ctx.move_to(0, 0)
        ctx.line_to(r * 0.82, -r * 0.32 - flap)
        ctx.line_to(r * 0.25, r * 0.22)
        ctx.close_path()
        ctx.set_source_rgba(0.95, 0.48, 0.42, 0.95 * alpha)
        ctx.fill()

    elif w_idx == 6:
        # 6. Stained-Glass Chime Bell (彩绘琉璃小钟铃)
        ctx.arc(0, r * 0.58, r * 0.20, 0, 2 * math.pi)
        ctx.set_source_rgba(1.0, 0.85, 0.25, 0.98 * alpha)
        ctx.fill()
        facets = [
            ([(-r * 0.32, -r * 0.55), (0, -r * 0.62), (0, r * 0.42), (-r * 0.72, r * 0.45)], (0.15, 0.48, 0.95)),
            ([(0, -r * 0.62), (r * 0.32, -r * 0.55), (r * 0.72, r * 0.45), (0, r * 0.42)], (0.92, 0.22, 0.45)),
            ([(-r * 0.48, -r * 0.05), (r * 0.48, -r * 0.05), (r * 0.68, r * 0.45), (-r * 0.68, r * 0.45)], (1.0, 0.75, 0.18)),
        ]
        for pts, col in facets:
            ctx.move_to(*pts[0])
            for px, py in pts[1:]:
                ctx.line_to(px, py)
            ctx.close_path()
            ctx.set_source_rgba(col[0], col[1], col[2], 0.95 * alpha)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.05, 0.05, 0.08, 0.98 * alpha)
            ctx.set_line_width(max(1.6, r * 0.09))
            ctx.stroke()

    elif w_idx == 7:
        # 7. Spinning Vinyl Record & Note ♪ (黑胶唱片与八分音符)
        ctx.arc(0, 0, r * 0.88, 0, 2 * math.pi)
        ctx.set_source_rgba(0.10, 0.10, 0.12, 0.98 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.95, 0.88, 0.68, 0.92 * alpha)
        ctx.set_line_width(max(1.4, r * 0.07))
        ctx.stroke()
        ctx.arc(0, 0, r * 0.34, 0, 2 * math.pi)
        ctx.set_source_rgba(0.85, 0.24, 0.20, 0.98 * alpha)
        ctx.fill()
        ctx.set_source_rgba(1.0, 0.88, 0.28, 0.98 * alpha)
        ctx.arc(-r * 0.12, r * 0.22, r * 0.20, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_line_width(max(1.8, r * 0.11))
        ctx.move_to(r * 0.04, r * 0.22)
        ctx.line_to(r * 0.04, -r * 0.48)
        ctx.curve_to(r * 0.35, -r * 0.42, r * 0.42, -r * 0.18, r * 0.28, -r * 0.05)
        ctx.stroke()

    elif w_idx == 8:
        # 8. Thumbprint Clay Charm (印有手工指纹的软陶徽章)
        ctx.arc(0, 0, r * 0.86, 0, 2 * math.pi)
        ctx.set_source_rgba(0.95, 0.56, 0.48, 0.96 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(1.0, 0.85, 0.72, 0.92 * alpha)
        ctx.set_line_width(max(1.6, r * 0.09))
        ctx.stroke()
        ctx.set_source_rgba(0.75, 0.34, 0.28, 0.88 * alpha)
        ctx.set_line_width(max(1.2, r * 0.065))
        for rad_k in (0.25, 0.45, 0.64):
            ctx.arc(0, r * 0.05, r * rad_k, -math.pi * 0.8, math.pi * 0.55)
            ctx.stroke()

    elif w_idx == 9:
        # 9. Drafting Compass (精密工程圆规)
        ctx.set_source_rgba(0.28, 0.88, 1.0, 0.92 * alpha)
        ctx.set_line_width(max(1.4, r * 0.07))
        ctx.arc(0, -r * 0.55, r * 0.95, math.pi * 0.32, math.pi * 0.68)
        ctx.stroke()
        ctx.set_source_rgba(1.0, 0.86, 0.35, 0.98 * alpha)
        ctx.set_line_width(max(2.0, r * 0.11))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(0, -r * 0.58)
        ctx.line_to(-r * 0.52, r * 0.68)
        ctx.move_to(0, -r * 0.58)
        ctx.line_to(r * 0.52, r * 0.68)
        ctx.stroke()
        ctx.arc(0, -r * 0.58, r * 0.20, 0, 2 * math.pi)
        ctx.set_source_rgba(0.95, 0.98, 1.0, 0.98 * alpha)
        ctx.fill()

    ctx.restore()
