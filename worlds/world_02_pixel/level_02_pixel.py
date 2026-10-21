# -*- coding: utf-8 -*-
"""
World 02 · 16-Bit 像素横版大闯关 (level_02_pixel.py)
Full 1600x180 Native Canvas -> 6x Nearest Upscale -> Smooth 1920x1080 Screen Viewport.
Features:
  - 100% inheritance & direct reuse of styles/style_02_pixel.py aesthetics.
  - Enhanced 3D spherical dome tilt, arching/ducking, gaze-coupled Bayer shading.
  - Pure white capsule eyes (-30° tilt, far eye 1px narrower, 81% perspective).
  - 100% ground/platform contact anchoring (zero clipping, zero floating, zero leftover pipe dots).
  - 16-Bit Pixel Arcade Coin (本关实物信物) with zero abstract text.
  - High-tech pitch-black Cyber Breach cutscene in Beat 6: bottom purple-laser & particle portal mouth,
    Slime plunging into the bottom opening, and glowing 3D/pixel Cyber Data Cubes overflowing upward!
"""

import os
import sys
import tempfile
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Repo root derived from this file (worlds/world_02_pixel/level_02_pixel.py)
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(CUR_DIR))
for _p in (CUR_DIR, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from slime_engine import get_pil_font
from styles import style_02_pixel as st02

# Screen & World Dimensions
W, H = 1920, 1080
NATIVE_W, NATIVE_H = 320, 180
SCALE = 6
NATIVE_WORLD_W = 1600
WORLD_W, WORLD_H = NATIVE_WORLD_W * SCALE, NATIVE_H * SCALE

# Reuse strict 16-bit palette from style_02_pixel and add cyber colors
PAL = dict(st02.PAL)
PAL["CYBER_MAGENTA"] = (255, 20, 154, 255)
PAL["CYBER_CYAN"] = (0, 245, 255, 255)
PAL["CYBER_PURPLE"] = (176, 38, 255, 255)

BAYER_4X4 = st02.BAYER_4X4
BAYER_2X2 = st02.BAYER_2X2


# ---------------------------------------------------------------------------
# Enhanced 3D Spherical Gaze-Coupled Slime Sprite Generator
# ---------------------------------------------------------------------------

def create_pixel_slime_sprite(radius=10, squash_y=1.0, tilt=0.0, look=(0.3, -0.3),
                              eye_mode="pill", blink=0.0, is_invincible=False,
                              rainbow_phase=0.0):
    """
    Generate native Slime sprite with genuine 3D spherical perspective coupling:
    - Upper body dome leans/arches/ducks towards gaze direction (look_x, look_y) by 1~2px.
    - Bottom contact row remains strictly anchored and unaffected (zero ground penetration).
    - Internal highlights and Bayer-dithered shading shift synchronously with gaze.
    - Pure white capsule eyes (-30° tilt, far eye 1px narrower, 81% perspective).
    - Strictly MOUTHLESS, no nose, no blush.
    """
    sy = max(0.40, min(2.4, squash_y))
    sx = 1.0 / math.sqrt(sy)
    size = int(max(36, radius * 3.8))
    if size % 2 != 0:
        size += 1
    xc, yc = (size - 1) / 2.0, (size - 1) / 2.0

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    cos_t, sin_t = math.cos(-tilt), math.sin(-tilt)
    body_mask = np.zeros((size, size), dtype=bool)

    rx = radius * sx
    ry = radius * sy

    look_x, look_y = look

    if is_invincible:
        rainbow_colors = [
            PAL["GOLD_LIGHT"], PAL["CORAL"], PAL["VIOLET"],
            PAL["ROYAL_BLUE"], PAL["CYAN_SKY"], PAL["GREEN_LIGHT"], PAL["RED_LIGHT"]
        ]
        num_c = len(rainbow_colors)

    for y in range(size):
        for x in range(size):
            dx = x - xc
            dy = y - yc
            dxr = dx * cos_t - dy * sin_t
            dyr = dx * sin_t + dy * cos_t

            v_raw = dyr / ry
            t_height = max(0.0, min(1.0, (1.0 - v_raw) / 2.0))

            shift_x = look_x * 1.8 * (t_height ** 1.3)

            if look_y < 0:
                shift_y = abs(look_y) * 1.6 * (t_height ** 1.5)
            else:
                shift_y = -look_y * 1.4 * (t_height ** 1.5)

            dx_eff = dxr - shift_x
            dy_eff = dyr + (shift_y if v_raw < 0.2 else 0.0)

            u = dx_eff / rx
            v = dy_eff / ry
            if v > 0:
                u_mod = u / (1.0 + 0.06 * v)
            else:
                u_mod = u
            d = math.sqrt(u_mod * u_mod + v * v)

            if d <= 1.08:
                if d > 0.89:
                    pixels[x, y] = PAL["VOID"]
                else:
                    body_mask[y, x] = True
                    t_grad = (u + v) * 0.40 + 0.50 - 0.22 * look_x - 0.20 * look_y
                    t_dith = t_grad + 0.14 * BAYER_2X2[y % 2, x % 2]

                    if is_invincible:
                        c_idx = int((t_dith * 3.0 + rainbow_phase) % num_c)
                        c = rainbow_colors[c_idx]
                    else:
                        if t_dith < 0.28:
                            c = PAL["CYAN_SKY"]
                        elif t_dith < 0.52:
                            c = PAL["ROYAL_BLUE"]
                        elif t_dith < 0.75:
                            c = PAL["VIOLET"]
                        else:
                            c = PAL["CORAL"]

                    pixels[x, y] = c

    # Specular highlight shifts with 3D spherical gaze
    hl_x = int(round(xc - rx * 0.55 + rx * 0.28 * look_x))
    hl_y = int(round(yc - ry * 0.42 + ry * 0.25 * look_y))
    for ox, oy, col in [(0, 0, PAL["WHITE"]), (1, 0, PAL["WHITE"]), (0, 1, PAL["ICE_BLUE"])]:
        if 0 <= hl_x + ox < size and 0 <= hl_y + oy < size and body_mask[hl_y + oy, hl_x + ox]:
            pixels[hl_x + ox, hl_y + oy] = col

    # 3D Spherical Gaze & Eye Line Coordinates
    base_ox = rx * (0.32 * look_x)
    base_oy = ry * (-0.16 + 0.30 * look_y)
    eye_cy = int(round(yc + base_oy))

    if abs(look_x) <= 0.22:
        le_x = int(round(xc + base_ox - 2.5))
        re_x = int(round(xc + base_ox + 2.5))
        le_y = eye_cy
        re_y = eye_cy
    elif look_x > 0.22:
        le_x = int(round(xc + base_ox - 2.5))
        re_x = int(round(xc + base_ox + 2.5))
        le_y = eye_cy
        if look_y < -0.2:
            re_y = eye_cy - 1
        elif look_y > 0.2:
            re_y = eye_cy + 1
        else:
            re_y = eye_cy
    else:
        le_x = int(round(xc + base_ox - 2.5))
        re_x = int(round(xc + base_ox + 2.5))
        re_y = eye_cy
        if look_y < -0.2:
            le_y = eye_cy - 1
        elif look_y > 0.2:
            le_y = eye_cy + 1
        else:
            le_y = eye_cy

    def set_px(px, py, col):
        if 0 <= px < size and 0 <= py < size and body_mask[py, px]:
            pixels[px, py] = col

    if blink > 0.5:
        for dx in range(-1, 2):
            set_px(le_x + dx, le_y, PAL["WHITE"])
        for dx in range(0, 2):
            set_px(re_x + dx, re_y, PAL["WHITE"])
    elif eye_mode == "sparkle":
        for dy in range(-2, 3):
            set_px(le_x, le_y + dy, PAL["WHITE"])
            set_px(re_x, re_y + dy, PAL["WHITE"])
        for dx in range(-2, 3):
            set_px(le_x + dx, le_y, PAL["WHITE"])
        for dx in range(-1, 2):
            set_px(re_x + dx, re_y, PAL["WHITE"])
    elif eye_mode == "happy":
        for dx, dy in [(-1, 0), (0, -1), (1, 0)]:
            set_px(le_x + dx, le_y + dy, PAL["WHITE"])
            set_px(re_x + dx, re_y + dy, PAL["WHITE"])
    elif eye_mode == "focus":
        if abs(look_x) <= 0.22:
            for dx in range(0, 2):
                set_px(le_x + dx, le_y, PAL["WHITE"])
                set_px(re_x + dx, re_y, PAL["WHITE"])
        elif look_x > 0.22:
            for dx in range(-1, 2):
                set_px(le_x + dx, le_y, PAL["WHITE"])
            for dx in range(0, 2):
                set_px(re_x + dx, re_y, PAL["WHITE"])
        else:
            for dx in range(0, 2):
                set_px(le_x + dx, le_y, PAL["WHITE"])
            for dx in range(-1, 2):
                set_px(re_x + dx, re_y, PAL["WHITE"])
    elif eye_mode in ("wince", "charge"):
        for dx, dy in [(-1, -1), (0, 0), (-1, 1)]:
            set_px(le_x + dx, le_y + dy, PAL["WHITE"])
        for dx, dy in [(1, -1), (0, 0), (1, 1)]:
            set_px(re_x + dx, re_y + dy, PAL["WHITE"])
    else:
        if abs(look_x) <= 0.22:
            h_range = range(-1, 2) if abs(look_y) > 0.38 else range(-2, 2)
            for dy in h_range:
                set_px(le_x, le_y + dy, PAL["WHITE"])
                set_px(le_x + 1, le_y + dy, PAL["WHITE"])
                set_px(re_x, re_y + dy, PAL["WHITE"])
                set_px(re_x + 1, re_y + dy, PAL["WHITE"])
        elif look_x > 0.22:
            for dy in range(-2, 2):
                set_px(le_x, le_y + dy, PAL["WHITE"])
                set_px(le_x + 1, le_y + dy, PAL["WHITE"])
            for dy in range(-1, 2):
                set_px(re_x, re_y + dy, PAL["WHITE"])
        else:
            for dy in range(-1, 2):
                set_px(le_x, le_y + dy, PAL["WHITE"])
            for dy in range(-2, 2):
                set_px(re_x, re_y + dy, PAL["WHITE"])
                set_px(re_x + 1, re_y + dy, PAL["WHITE"])

    return img, (xc, yc, ry)


# ---------------------------------------------------------------------------
# 16-Bit Pixel Arcade Coin (本关实物信物)
# ---------------------------------------------------------------------------

def create_pixel_arcade_coin_sprite(rot_y=1.0):
    """14x14 pixel golden arcade coin rotating horizontally with 3D bevel and inner arcade star."""
    w_coin = max(2, int(round(14 * abs(rot_y))))
    coin = Image.new("RGBA", (w_coin, 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(coin)

    if w_coin >= 8:
        d.ellipse([0, 0, w_coin - 1, 13], fill=PAL["GOLD_BASE"], outline=PAL["VOID"])
        d.ellipse([1, 1, w_coin - 2, 12], outline=PAL["GOLD_LIGHT"])
        mid_x = (w_coin - 1) / 2.0
        mid_y = 6.5
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if abs(dx) + abs(dy) <= 2:
                    px = int(round(mid_x + dx * (w_coin / 14.0)))
                    py = int(round(mid_y + dy))
                    if 1 <= px < w_coin - 1 and 1 <= py < 13:
                        coin.putpixel((px, py), PAL["WHITE"] if (dx == 0 and dy == 0) else PAL["GOLD_LIGHT"])
        d.arc([1, 1, w_coin - 2, 12], start=0, end=90, fill=PAL["GOLD_SHADOW"])
    else:
        d.rectangle([0, 0, w_coin - 1, 13], fill=PAL["GOLD_BASE"], outline=PAL["VOID"])
        d.line([(0, 1), (w_coin - 1, 1)], fill=PAL["GOLD_LIGHT"])
        d.line([(w_coin // 2, 2), (w_coin // 2, 11)], fill=PAL["WHITE"])

    return coin


# ---------------------------------------------------------------------------
# Reusable Sprites & Level Geometry
# ---------------------------------------------------------------------------

def create_solid_hidden_block_sprite():
    """16x16 pixel solid hidden block with [!] symbol."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 15, 15], fill=PAL["VOID"])
    d.rectangle([1, 1, 14, 14], fill=PAL["CYAN_SKY"])
    d.line([(1, 1), (14, 1)], fill=PAL["ICE_BLUE"])
    d.line([(1, 1), (1, 14)], fill=PAL["ICE_BLUE"])
    d.line([(1, 14), (14, 14)], fill=PAL["ROYAL_BLUE"])
    d.line([(14, 1), (14, 14)], fill=PAL["ROYAL_BLUE"])
    d.rectangle([7, 3, 8, 9], fill=PAL["WHITE"])
    d.rectangle([7, 11, 8, 12], fill=PAL["WHITE"])
    return img


def create_springboard_sprite(compress=0.0):
    """18px wide red-and-white springboard: uncompressed h=12 (top=132), full compressed h=5 (top=139)."""
    compress = max(0.0, min(1.0, compress))
    h = int(round(12.0 - 7.0 * compress))
    img = Image.new("RGBA", (18, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, h - 2, 15, h - 1], fill=PAL["VOID"])
    if h > 6:
        d.rectangle([4, 2, 13, h - 2], fill=PAL["RED_BASE"], outline=PAL["VOID"])
        d.line([(5, h // 2), (12, h // 2)], fill=PAL["WHITE"])
    else:
        d.rectangle([4, 2, 13, h - 2], fill=PAL["RED_BASE"], outline=PAL["VOID"])
    d.rectangle([1, 0, 16, 2], fill=PAL["RED_LIGHT"], outline=PAL["VOID"])
    return img


def create_ladybug_sprite(walk_phase=0.0, stomped=False):
    """24x22 pixel Ladybug monster (normal and squashed pancake)."""
    if stomped:
        img = Image.new("RGBA", (26, 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([1, 1, 24, 6], fill=PAL["RED_BASE"], outline=PAL["VOID"])
        d.line([(6, 3), (8, 5)], fill=PAL["WHITE"])
        d.line([(8, 3), (6, 5)], fill=PAL["WHITE"])
        d.line([(17, 3), (19, 5)], fill=PAL["WHITE"])
        d.line([(19, 3), (17, 5)], fill=PAL["WHITE"])
        return img
    return st02.create_v3_big_eyed_ladybug_sprite(walk_phase=walk_phase)


def create_cloud_monster_sprite(rot=0.0):
    """22x18 pixel frowning gray pixel cloud monster."""
    img = Image.new("RGBA", (22, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.ellipse([1, 4, 20, 16], fill=PAL["CLOUD_SHADOW_2"], outline=PAL["VOID"])
    d.ellipse([3, 2, 12, 12], fill=PAL["CLOUD_SHADOW_1"], outline=PAL["VOID"])
    d.ellipse([10, 2, 19, 12], fill=PAL["CLOUD_SHADOW_1"], outline=PAL["VOID"])

    d.polygon([(5, 2), (7, 0), (7, 3)], fill=PAL["GOLD_BASE"])
    d.polygon([(16, 2), (14, 0), (14, 3)], fill=PAL["GOLD_BASE"])

    d.rectangle([5, 6, 8, 10], fill=PAL["WHITE"], outline=PAL["VOID"])
    d.rectangle([13, 6, 16, 10], fill=PAL["WHITE"], outline=PAL["VOID"])
    d.rectangle([6, 8, 7, 9], fill=PAL["VOID"])
    d.rectangle([14, 8, 15, 9], fill=PAL["VOID"])

    d.line([(8, 13), (13, 13)], fill=PAL["VOID"])
    d.line([(7, 14), (8, 13)], fill=PAL["VOID"])
    d.line([(13, 13), (14, 14)], fill=PAL["VOID"])

    if abs(rot) > 0.05:
        img = img.rotate(-math.degrees(rot), resample=Image.Resampling.NEAREST, expand=False)
    return img


def create_speech_bubble_sprite(text="?"):
    """Crisp 16x15 pixel white rounded comic speech bubble (never looks like a solid block!)."""
    b = Image.new("RGBA", (16, 15), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    # Rounded white cloud bubble with black pixel outline
    d.ellipse([1, 0, 14, 11], fill=PAL["WHITE"], outline=PAL["VOID"])
    d.polygon([(6, 11), (9, 11), (7, 14)], fill=PAL["WHITE"], outline=PAL["VOID"])
    d.line([(7, 11), (8, 11)], fill=PAL["WHITE"])

    col = PAL["RED_BASE"] if text == "!" else PAL["ROYAL_BLUE"]
    if text == "?":
        for px, py in [(6, 3), (7, 2), (8, 2), (9, 3), (9, 4), (8, 5), (7, 6), (7, 7), (7, 9)]:
            b.putpixel((px, py), col)
    else:
        for px, py in [(7, 2), (8, 2), (7, 3), (8, 3), (7, 4), (8, 4), (7, 5), (8, 5), (7, 6), (8, 6), (7, 8), (8, 8), (7, 9), (8, 9)]:
            b.putpixel((px, py), col)
    return b


# ---------------------------------------------------------------------------
# Static World Background Generator (1600x180)
# ---------------------------------------------------------------------------

_STATIC_BG_1600 = None

def get_static_world_bg_1600():
    """Generate and cache 1600x180 Bayer-dithered retro sky with distant clouds and twinkling stars."""
    global _STATIC_BG_1600
    if _STATIC_BG_1600 is not None:
        return _STATIC_BG_1600.copy()

    bg = Image.new("RGBA", (NATIVE_WORLD_W, NATIVE_H), (0, 0, 0, 255))
    pixels = bg.load()

    for y in range(NATIVE_H):
        rel_y = y / float(NATIVE_H - 1)
        for x in range(NATIVE_WORLD_W):
            dith = BAYER_4X4[y % 4, x % 4] * 0.12
            val = rel_y + dith

            if val < 0.15:
                c = PAL["NIGHT"]
            elif val < 0.30:
                c = PAL["DEEP_BLUE"]
            elif val < 0.46:
                c = PAL["MID_BLUE"]
            elif val < 0.62:
                c = PAL["ROYAL_BLUE"]
            elif val < 0.76:
                c = PAL["CYAN_SKY"]
            elif val < 0.88:
                c = PAL["DUSK_PINK"]
            else:
                c = PAL["PEACH"]
            pixels[x, y] = c

    rng = np.random.RandomState(42)
    star_xs = rng.randint(0, NATIVE_WORLD_W, size=180)
    star_ys = rng.randint(4, 70, size=180)
    for sx, sy in zip(star_xs, star_ys):
        pixels[sx, sy] = PAL["WHITE"]
        if rng.rand() < 0.28:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if 0 <= sx + dx < NATIVE_WORLD_W and 0 <= sy + dy < NATIVE_H:
                    pixels[sx + dx, sy + dy] = PAL["PALE_BLUE"]

    cloud_sprite = st02.create_pixel_distant_cloud(w=42, h=14)
    for cx in range(30, NATIVE_WORLD_W, 90):
        cy = 96 + int(math.sin(cx * 0.05) * 6)
        bg.paste(cloud_sprite, (cx, cy), cloud_sprite)

    _STATIC_BG_1600 = bg
    return bg.copy()


def draw_spike_pit(canvas, x0, x1, ground_y=148):
    """Draw dangerous spike pit chasm."""
    d = ImageDraw.Draw(canvas)
    d.rectangle([x0, ground_y, x1, NATIVE_H], fill=PAL["VOID"])
    sx = x0 + 4
    while sx < x1 - 6:
        d.polygon([(sx, ground_y + 24), (sx + 4, ground_y + 6), (sx + 8, ground_y + 24)],
                  fill=PAL["ICE_BLUE"], outline=PAL["VOID"])
        sx += 8


def _draw_3d_hex_ring(d, cx, cy, rx, ry, rot_rad, col, width=3, with_brackets=False):
    """Draws a 3D perspective hexagonal ring on the horizontal plane (rx, ry) rotated by rot_rad."""
    pts = []
    for k in range(6):
        ang = rot_rad + k * (math.pi / 3.0)
        pts.append((cx + math.cos(ang) * rx, cy + math.sin(ang) * ry))
    pts.append(pts[0])
    d.line(pts, fill=col, width=width)
    if with_brackets:
        for k in range(6):
            ang = rot_rad + k * (math.pi / 3.0)
            vx = cx + math.cos(ang) * rx
            vy = cy + math.sin(ang) * ry
            d.ellipse([vx - 4, vy - 3, vx + 4, vy + 3], fill=(255, 255, 255, col[3]))


def render_cyber_void_cutscene(viewport: Image.Image, cr: dict, t: float, frame: int) -> Image.Image:
    """
    Renders the Beat 6 3D Cyberpunk Holographic Abyss Portal & Neon Warp Transition on a pitch-black screen:
    - Faint 3D perspective cyber floor grid converging toward the bottom portal (960, 880)
    - 6 stacked 3D depth rings (rotating 3D hexagonal tech rings & segmented neon energy rings in
      Electric Cyan #00F5FF, Cyber Magenta #FF00AA, Neon Purple #9D4EDD, and Cyber Gold #FFE600)
    - Upward volumetric purple/cyan laser beams & rising holographic diamond motes
    - Guiding Star ✦ diving into the portal core first, followed by the Slime leaping with a 3D Cyberpunk
      Neon Ribbon Trail (matching World 03!) and plunging head-first into the bottom portal
    - Upon impact (t >= 26.12s): Central Overdrive Laser Pillar, rising 3D hexagonal shockwave rings,
      and 84 velocity-aligned 3D neon warp light-streaks & holo-sparks with real multi-scale Unreal Bloom!
    """
    prog = cr.get("open", 0.0)
    if prog <= 0.01:
        return viewport

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    pcx = 960
    is_erupting = (t >= 26.12)
    erupt_dt = max(0.0, t - 26.12)
    erupt_boost = min(1.0, erupt_dt * 4.5) if is_erupting else 0.0

    # Camera Dive into the 3D Cyber Portal Vortex (t = 26.55s ~ 28.00s -> Seamless Hyperspace Breach into World 03!)
    dive_u = max(0.0, min(1.0, (t - 26.55) / 1.45))
    dive_ease = dive_u * dive_u * (3.0 - 2.0 * dive_u)

    pcy = int(round(880.0 - 360.0 * (dive_ease ** 0.90)))  # 880 -> 520 (centered as camera plunges straight into the portal!)
    aspect_y = 0.24 + 0.58 * dive_ease                     # 0.24 -> 0.82 as camera pitches down into the hexagonal tunnel

    # 1. Subtle 3D Perspective Cyber Floor Grid around the bottom portal (fades out as we dive inside)
    horizon_y = int(round(660.0 - 420.0 * dive_ease))
    grid_alpha = int((42 + 38 * erupt_boost) * prog * max(0.0, 1.0 - dive_ease * 1.35))
    if grid_alpha > 4:
        for g_idx in range(-8, 9):
            if g_idx == 0:
                continue
            x_far = pcx + g_idx * 65
            x_near = pcx + g_idx * 240
            d.line([(x_far, horizon_y), (x_near, 1080)], fill=(18, 52, 96, grid_alpha), width=2)
        for z_step in range(1, 7):
            frac_z = (z_step / 6.0) ** 1.6
            gy = int(horizon_y + frac_z * (1080 - horizon_y))
            span_x = int((260 + frac_z * 820) * prog)
            d.line([(pcx - span_x, gy), (pcx + span_x, gy)], fill=(48, 16, 88, grid_alpha), width=2)

    # 2. Concentric/Receding 3D Hexagonal Abyss Tunnel Rings (rushing outward past the camera lens!)
    rx_base = (310.0 + 45.0 * erupt_boost) * prog * (1.0 + 3.8 * (dive_u ** 1.65))

    ring_colors = [
        (0, 245, 255, 245),    # Electric Cyan
        (255, 0, 170, 240),    # Cyber Magenta
        (157, 78, 221, 230),   # Neon Purple
        (255, 230, 0, 225),    # Cyber Gold
        (0, 245, 255, 240),    # Electric Cyan
        (255, 180, 255, 250),  # Core White-Magenta
        (0, 245, 255, 245),
        (255, 0, 170, 240),
        (157, 78, 221, 235),
        (255, 230, 0, 235),
    ]
    num_rings = 10 if dive_u > 0.01 else 6
    for depth_k in range(num_rings):
        if dive_u > 0.01:
            # Continuous streaming tunnel phase so hexagonal wireframe rings rush outward past the camera!
            raw_phase = ((depth_k / float(num_rings)) - (dive_u * 2.6)) % 1.0
            frac_d = raw_phase
        else:
            frac_d = depth_k / 5.0
        r_x = rx_base * (1.0 - frac_d * 0.86)
        r_y = r_x * aspect_y
        cy_depth = pcy + (depth_k * 8.0 * prog * (1.0 - dive_ease))
        rot_k = t * (2.4 if depth_k % 2 == 0 else -2.8) + depth_k * 0.5
        r_col = ring_colors[depth_k % len(ring_colors)]

        if depth_k == 0 and dive_u < 0.01:
            d.ellipse(
                [pcx - r_x, cy_depth - r_y, pcx + r_x, cy_depth + r_y],
                fill=(6, 2, 18, 245),
                outline=(157, 78, 221, 220),
                width=4,
            )
            _draw_3d_hex_ring(d, pcx, cy_depth, r_x * 1.04, r_y * 1.04, rot_k, r_col, width=4, with_brackets=True)
        elif depth_k % 3 == 1:
            for seg in range(4):
                a0 = int(math.degrees(rot_k) + seg * 90 + 10)
                a1 = a0 + 62
                d.arc(
                    [pcx - r_x, cy_depth - r_y, pcx + r_x, cy_depth + r_y],
                    start=a0, end=a1,
                    fill=r_col,
                    width=max(2, int(5 - frac_d * 3)),
                )
        else:
            _draw_3d_hex_ring(d, pcx, cy_depth, r_x, r_y, rot_k, r_col, width=max(2, int(5 - frac_d * 3)), with_brackets=(depth_k % 2 == 0))

    # Glowing Portal Singularity Core wireframe at center (smooth glow is computed in numpy below!)
    core_rx = int(max(18.0, (76.0 + 34.0 * erupt_boost) * prog * (1.0 - 0.35 * dive_ease)))
    core_ry = int(core_rx * aspect_y)
    _draw_3d_hex_ring(d, pcx, pcy, core_rx, core_ry, -t * 3.8, (255, 255, 255, 255), width=4, with_brackets=True)

    # 3. Upward Volumetric Laser Cage from the 3D Hexagonal Portal Vertices
    for k_v in range(8):
        ang_v = t * 0.8 + k_v * (math.pi / 4.0)
        bx0 = pcx + math.cos(ang_v) * rx_base * 0.86
        by0 = pcy + math.sin(ang_v) * (rx_base * aspect_y * 0.86)
        pulse_v = 0.65 + 0.35 * math.sin(t * 14.0 + k_v * 1.3)
        beam_h = (420.0 + 380.0 * erupt_boost) * pulse_v * prog * (1.0 - 0.65 * dive_ease)
        bx1 = pcx + math.cos(ang_v) * rx_base * (0.42 if not is_erupting else 1.25)
        by1 = by0 - beam_h
        b_col = (0, 245, 255, int(195 * prog)) if k_v % 2 == 0 else (255, 20, 175, int(210 * prog))
        d.line([(bx0, by0), (bx1, by1)], fill=b_col, width=3 if not is_erupting else 4)

    # Ambient rising holographic diamond motes above the portal
    rng_mote = np.random.RandomState(3077)
    for m_i in range(36):
        m_ox = rng_mote.uniform(-250.0, 250.0)
        m_spd = rng_mote.uniform(160.0, 380.0)
        m_y_off = (t * m_spd + m_i * 29.0) % 480.0
        mx = pcx + m_ox * prog + 12.0 * math.sin(t * 4.5 + m_i)
        my = pcy - m_y_off * prog
        m_alpha = int(230 * max(0.0, 1.0 - m_y_off / 480.0) * prog)
        if m_alpha > 15:
            m_col = (0, 245, 255, m_alpha) if m_i % 3 == 0 else ((255, 230, 0, m_alpha) if m_i % 5 == 0 else (210, 70, 255, m_alpha))
            r_m = 5 if m_i % 4 == 0 else 3
            d.polygon([(mx, my - r_m), (mx + r_m, my), (mx, my + r_m), (mx - r_m, my)], fill=m_col)

    # 4. Guiding Star ✦ diving into the 3D Cyber Portal first (t = 25.10 ~ 25.55s)
    if cr.get("void_star_visible", False):
        sx_v = cr["void_star_x"]
        sy_v = cr["void_star_y"]
        d.line([(sx_v - 45, sy_v - 110), (sx_v, sy_v)], fill=(255, 230, 0, 210), width=5)
        d.line([(sx_v - 22, sy_v - 55), (sx_v, sy_v)], fill=(255, 255, 255, 245), width=3)
        r_st = 22.0
        st_pts = []
        for k_s in range(8):
            a_s = t * 8.0 + k_s * (math.pi / 4.0)
            rad_s = r_st if k_s % 2 == 0 else r_st * 0.35
            st_pts.append((sx_v + math.cos(a_s) * rad_s, sy_v + math.sin(a_s) * rad_s))
        d.polygon(st_pts, fill=(255, 245, 150, 255), outline=(0, 245, 255, 255))

    # 5. Slime's 3D Cyberpunk Neon Ribbon Trail (matching World 03's Ribbon + Dual Edge Rails!)
    trail_pts = cr.get("void_slime_trail", [])
    if len(trail_pts) >= 2:
        left_rail = []
        right_rail = []
        n_tr = len(trail_pts)
        for i_t, (tx, ty) in enumerate(trail_pts):
            u_tr = (i_t + 1) / float(n_tr)
            if i_t < n_tr - 1:
                dx_t = trail_pts[i_t + 1][0] - tx
                dy_t = trail_pts[i_t + 1][1] - ty
            else:
                dx_t = tx - trail_pts[i_t - 1][0]
                dy_t = ty - trail_pts[i_t - 1][1]
            mag_t = max(1e-3, math.hypot(dx_t, dy_t))
            nx_t = -dy_t / mag_t
            ny_t = dx_t / mag_t
            half_w = 34.0 * (u_tr ** 1.25)
            pL = (tx + nx_t * half_w, ty + ny_t * half_w)
            pR = (tx - nx_t * half_w, ty - ny_t * half_w)
            left_rail.append(pL)
            right_rail.append(pR)
            if i_t > 0:
                quad = [left_rail[i_t - 1], right_rail[i_t - 1], right_rail[i_t], left_rail[i_t]]
                r_c = int(255 * (1.0 - u_tr * 0.85))
                g_c = int(245 * (u_tr ** 1.2))
                b_c = 255
                a_c = int(175 * (u_tr ** 1.3))
                d.polygon(quad, fill=(r_c, g_c, b_c, a_c))
                d.line([left_rail[i_t - 1], left_rail[i_t]], fill=(0, 245, 255, min(255, int(a_c * 1.35))), width=3)
                d.line([right_rail[i_t - 1], right_rail[i_t]], fill=(255, 40, 190, min(255, int(a_c * 1.35))), width=3)

    # 6. Draw Slime Plunging Into the 3D Portal Core (clipped at y = pcy + 8 so it dives inside!)
    if cr.get("void_slime_visible", False):
        vs_sprite, (scx, scy, s_ry) = create_pixel_slime_sprite(
            radius=10,
            squash_y=cr["void_slime_squash_y"],
            tilt=cr["void_slime_tilt"],
            look=cr["void_slime_look"],
            eye_mode=cr["void_slime_eye"],
            blink=0.0,
            is_invincible=False,
        )
        vs_big = vs_sprite.resize((vs_sprite.width * SCALE, vs_sprite.height * SCALE), Image.Resampling.NEAREST)
        paste_x = int(round(cr["void_slime_x"] - scx * SCALE))
        paste_y = int(round(cr["void_slime_y"] - (scy + s_ry) * SCALE))

        clip_bottom = pcy + 8
        if paste_y < clip_bottom:
            vis_h = min(vs_big.height, clip_bottom - paste_y)
            if vis_h > 0:
                vs_cropped = vs_big.crop((0, 0, vs_big.width, vis_h))
                overlay.paste(vs_cropped, (paste_x, paste_y), vs_cropped)

    # 7. Post-Dive 3D Holographic Shockwave Cascade & Neon Warp Eruption (t >= 26.12s)
    if is_erupting:
        # 7A. Central Overdrive Laser Pillar surging upward from the portal core (fades out cleanly as camera dives in!)
        pillar_fade = max(0.0, 1.0 - max(0.0, erupt_dt - 0.55) * 1.8)
        pillar_w = int((46.0 + 18.0 * math.sin(t * 28.0)) * min(1.0, erupt_dt * 6.0) * pillar_fade)
        if pillar_w > 2:
            d.rectangle(
                [pcx - pillar_w * 2, 0, pcx + pillar_w * 2, pcy],
                fill=(145, 25, 255, int(85 * pillar_fade)),
            )
            d.rectangle(
                [pcx - pillar_w, 0, pcx + pillar_w, pcy],
                fill=(0, 245, 255, int(165 * pillar_fade)),
            )
            d.rectangle(
                [pcx - max(2, pillar_w // 2), 0, pcx + max(2, pillar_w // 2), pcy],
                fill=(255, 255, 255, int(235 * pillar_fade)),
            )

        # 7B. 6 Waves of Rising 3D Perspective Hexagonal & Circular Shockwave Rings
        for w_idx in range(6):
            w_age = erupt_dt - w_idx * 0.18
            if 0.0 < w_age < 1.35:
                u_w = w_age / 1.35
                w_cy = pcy - (u_w ** 0.82) * 680.0 * (1.0 - 0.75 * dive_ease)
                w_rx = rx_base * (0.45 + u_w * 1.25)
                w_ry = w_rx * aspect_y
                w_alpha = int(250 * ((1.0 - u_w) ** 1.15))
                w_col_rgb = [(0, 245, 255), (255, 0, 170), (255, 230, 0), (157, 78, 221)][w_idx % 4]
                w_col = (w_col_rgb[0], w_col_rgb[1], w_col_rgb[2], w_alpha)
                if w_idx % 2 == 0:
                    _draw_3d_hex_ring(
                        d, pcx, w_cy, w_rx, w_ry,
                        rot_rad=t * 2.4 + w_idx,
                        col=w_col,
                        width=max(2, int(5 * (1.0 - u_w))),
                        with_brackets=True,
                    )
                else:
                    d.ellipse(
                        [pcx - w_rx, w_cy - w_ry, pcx + w_rx, w_cy + w_ry],
                        outline=w_col,
                        width=max(2, int(4 * (1.0 - u_w))),
                    )

        # 7C. 84 Velocity-Aligned 3D Neon Warp Light-Streaks & Diamond Holo-Sparks
        spark_pal = {
            "cyan":    (0, 245, 255),
            "magenta": (255, 20, 175),
            "purple":  (175, 75, 255),
            "gold":    (255, 230, 0),
            "white":   (235, 248, 255),
        }
        for sp in cr.get("void_sparks", []):
            sx_p, sy_p = sp["x"], sp["y"]
            vx_p, vy_p = sp["vx"], sp["vy"]
            spd_p = max(1e-3, math.hypot(vx_p, vy_p))
            ux, uy = vx_p / spd_p, vy_p / spd_p
            s_len = sp["length"]
            s_w = int(round(sp["width"]))
            a_sp = int(255 * sp["alpha"])
            rgb_s = spark_pal.get(sp["color_type"], (0, 245, 255))

            tail_x = sx_p - ux * s_len
            tail_y = sy_p - uy * s_len
            mid_x = sx_p - ux * (s_len * 0.35)
            mid_y = sy_p - uy * (s_len * 0.35)
            d.line([(tail_x, tail_y), (sx_p, sy_p)], fill=(rgb_s[0], rgb_s[1], rgb_s[2], a_sp), width=s_w + 2)
            d.line([(mid_x, mid_y), (sx_p, sy_p)], fill=(255, 255, 255, a_sp), width=max(1, s_w))

            if sp["is_diamond"]:
                r_fl = 7.0 + s_w
                d.polygon(
                    [(sx_p, sy_p - r_fl), (sx_p + r_fl * 0.5, sy_p), (sx_p, sy_p + r_fl), (sx_p - r_fl * 0.5, sy_p)],
                    fill=(255, 255, 255, a_sp),
                    outline=(rgb_s[0], rgb_s[1], rgb_s[2], a_sp),
                )

    # 7D. Dimensional Cyber Warp Tunnel Dive & Pixel-to-3D De-Pixelation (t = 26.55s ~ 28.00s)
    if dive_u > 0.01:
        rng_warp = np.random.RandomState(4099)
        for s_i in range(64):
            ang_w = (s_i / 64.0) * math.tau + rng_warp.uniform(-0.04, 0.04)
            spd_w = rng_warp.uniform(1.6, 3.2)
            phase_w = ((dive_u * spd_w) + rng_warp.uniform(0.0, 1.0)) % 1.0
            r_in = 35.0 + (phase_w ** 1.55) * 1080.0
            r_out = r_in + (110.0 + 340.0 * phase_w) * min(1.0, dive_u * 2.0)
            wx0 = pcx + math.cos(ang_w) * r_in
            wy0 = pcy + math.sin(ang_w) * (r_in * (0.68 + 0.32 * dive_ease))
            wx1 = pcx + math.cos(ang_w) * r_out
            wy1 = pcy + math.sin(ang_w) * (r_out * (0.68 + 0.32 * dive_ease))
            w_alpha = int(255 * min(1.0, dive_u * 2.4) * math.sin(phase_w * math.pi))
            if w_alpha > 12:
                c_rgb = [(0, 245, 255), (255, 0, 170), (157, 78, 221), (255, 230, 0)][s_i % 4]
                d.line([(wx0, wy0), (wx1, wy1)], fill=(c_rgb[0], c_rgb[1], c_rgb[2], w_alpha), width=3 if s_i % 2 == 0 else 2)
                if s_i % 3 == 0:
                    px_sz = int(6 + 12 * phase_w)
                    d.rectangle(
                        [wx1 - px_sz, wy1 - px_sz, wx1 + px_sz, wy1 + px_sz],
                        fill=(c_rgb[0], c_rgb[1], c_rgb[2], int(w_alpha * 0.85)),
                        outline=(255, 255, 255, w_alpha),
                        width=2,
                    )

    # 8. Front Lip of the 3D Portal Rim (drawn over Slime & streaks emerging from the core!)
    if dive_u < 0.55:
        lip_a = int(255 * max(0.0, 1.0 - dive_u / 0.55))
        r_y_front = rx_base * aspect_y
        d.arc(
            [pcx - rx_base, pcy - r_y_front, pcx + rx_base, pcy + r_y_front],
            start=0, end=180,
            fill=(0, 245, 255, lip_a),
            width=5,
        )
        d.arc(
            [pcx - rx_base * 0.82, pcy - r_y_front * 0.82, pcx + rx_base * 0.82, pcy + r_y_front * 0.82],
            start=0, end=180,
            fill=(255, 20, 175, lip_a),
            width=4,
        )

    # 9. True Multi-Scale Gaussian Unreal Bloom Pass + Smooth Per-Pixel Singularity Breach Flash!
    base_rgba = viewport.convert("RGBA")
    combined_rgb = Image.alpha_composite(base_rgba, overlay).convert("RGB")

    small_w, small_h = 480, 270
    small_img = combined_rgb.resize((small_w, small_h), Image.Resampling.BILINEAR)
    bloom_tight = small_img.filter(ImageFilter.GaussianBlur(radius=4)).resize((W, H), Image.Resampling.BILINEAR)
    bloom_wide = small_img.filter(ImageFilter.GaussianBlur(radius=14)).resize((W, H), Image.Resampling.BILINEAR)

    arr_base = np.asarray(combined_rgb, dtype=np.float32)
    arr_b1 = np.asarray(bloom_tight, dtype=np.float32)
    arr_b2 = np.asarray(bloom_wide, dtype=np.float32)
    arr_out = arr_base + arr_b1 * 0.55 + arr_b2 * 0.75

    # Smooth Per-Pixel Gaussian Radial Portal Glow & Full-Screen Cyber Hyperspace Breach (zero flat bands!)
    yy, xx = np.ogrid[0:H, 0:W]
    dx_g = (xx - float(pcx))
    dy_g = (yy - float(pcy)) / max(0.24, aspect_y)
    dist_sq = dx_g * dx_g + dy_g * dy_g

    # Ambient purple/cyan floor portal glow + singularity core glow
    sigma_floor = max(80.0, 290.0 * prog * (1.0 + 1.8 * dive_ease))
    glow_floor = np.exp(-dist_sq / (2.0 * sigma_floor * sigma_floor)) * prog * (0.45 + 0.35 * erupt_boost)
    sigma_core = max(25.0, (58.0 + 35.0 * erupt_boost) * prog * (1.0 + 2.4 * dive_ease))
    glow_core = np.exp(-dist_sq / (2.0 * sigma_core * sigma_core)) * prog * (0.75 + 0.45 * erupt_boost)

    arr_out[:, :, 0] += glow_floor * 135.0 + glow_core * 185.0
    arr_out[:, :, 1] += glow_floor * 35.0  + glow_core * 248.0
    arr_out[:, :, 2] += glow_floor * 245.0 + glow_core * 255.0

    # At t = 27.15s ~ 28.00s: Smooth Radial Cyber-Cyan & White Hyperspace Breach enveloping the screen!
    if t >= 27.15:
        breach_u = max(0.0, min(1.0, (t - 27.15) / 0.85))
        breach_ease = breach_u * breach_u * (3.0 - 2.0 * breach_u)
        sigma_breach = 140.0 + (breach_ease ** 1.45) * 2200.0
        radial_flash = np.exp(-dist_sq / (2.0 * sigma_breach * sigma_breach)) * (breach_ease ** 1.15)
        full_veil = max(0.0, min(1.0, (t - 27.45) / 0.50)) ** 1.5
        flash_w = np.clip(radial_flash + full_veil * 0.92, 0.0, 1.0)[:, :, None]
        # Target color: Radiant Cyber-Ice White (#EAFFFF) matching World 03's t=0.00s portal breach!
        target_cyber_flash = np.array([[[230.0, 253.0, 255.0]]], dtype=np.float32)
        arr_out = arr_out * (1.0 - flash_w) + target_cyber_flash * flash_w

    arr_out = np.clip(arr_out, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(arr_out, "RGB")


# ---------------------------------------------------------------------------
# Main Frame Render Function
# ---------------------------------------------------------------------------

def render_frame_from_state(state: dict) -> Image.Image:
    """
    Renders 1 frame at 1920x1080 from the simulation state dictionary.
    """
    canvas = get_static_world_bg_1600()
    d_c = ImageDraw.Draw(canvas)

    t = state["t"]
    frame = state["frame"]

    # --- 1. Level Terrain & Scenery ---
    island_sprite = st02.create_v3_floating_island_with_tree_and_waterfall()
    canvas.paste(island_sprite, (145, 38), island_sprite)
    canvas.paste(island_sprite, (656, 36), island_sprite)

    # Screen 1 (0..320): Cloud ground & Warp Portal
    st02.draw_cloud_sea_mass(canvas, 0, 320, ground_y=144)

    pipe_assembly = state["pipe_assembly"]
    pipe_sprite = st02.create_pipe_sprite(width=28, height=38)
    if pipe_assembly > 0.05:
        if pipe_assembly < 1.0:
            h_vis = max(1, int(38 * pipe_assembly))
            sub = pipe_sprite.crop((0, 38 - h_vis, 28, 38))
            canvas.paste(sub, (36, 108 + 38 - h_vis), sub)
        else:
            canvas.paste(pipe_sprite, (36, 108), pipe_sprite)

    for p in state.get("pipe_particles", []):
        if not p["landed"]:
            d_c.rectangle([p["x"], p["y"], p["x"] + 2, p["y"] + 2], fill=PAL["GREEN_LIGHT"])

    # Screen 2 (320..640): Cloud ground, Ladybug, Spike Pit (440..600), Springboard (420)
    st02.draw_cloud_sea_mass(canvas, 320, 440, ground_y=144, left_cliff=True)
    draw_spike_pit(canvas, 440, 600, ground_y=144)
    st02.draw_cloud_sea_mass(canvas, 600, 640, ground_y=144, right_cliff=True)

    spring_x = state["spring"]["x"]
    spring_comp = state["spring"]["compress"]
    spring_sprite = create_springboard_sprite(compress=spring_comp)
    canvas.paste(spring_sprite, (int(spring_x - spring_sprite.width / 2), 144 - spring_sprite.height), spring_sprite)

    lb = state["ladybug"]
    if lb["state"] != "hidden":
        is_stomped = (lb["state"] == "stomped")
        lb_sprite = create_ladybug_sprite(walk_phase=t * 2.0, stomped=is_stomped)
        canvas.paste(lb_sprite, (int(lb["x"] - lb_sprite.width / 2), int(lb["foot_y"] - lb_sprite.height)), lb_sprite)

    # Screen 3 (640..960): Stepped Bricks + Blocks + Cloud Ladder
    st02.draw_cloud_sea_mass(canvas, 640, 960, ground_y=144)

    brick = st02.create_brick_sprite()
    for bx in [758, 774, 790]:
        for by in range(64, 144, 16):
            canvas.paste(brick, (bx, by), brick)

    bl = state["blocks"]

    # Hidden block at x=720..736, y=96..112 (center=(728, 104), bottom=112)
    if bl["hidden_discovered"]:
        hb = create_solid_hidden_block_sprite()
        hy = 96 + int(bl["hidden_y_offset"])
        canvas.paste(hb, (720, hy), hb)
    elif bl["hidden_twinkle"]:
        # Bright twinkling pixel star hint right at the Hidden Block location (728, 108)!
        d_c.rectangle([727, 107, 729, 109], fill=PAL["WHITE"])
        canvas.putpixel((725, 108), PAL["GOLD_LIGHT"])
        canvas.putpixel((731, 108), PAL["GOLD_LIGHT"])
        canvas.putpixel((728, 105), PAL["GOLD_LIGHT"])
        canvas.putpixel((728, 111), PAL["GOLD_LIGHT"])

    # Cloud ladder steps: centers at (674, 122), (706, 98), (738, 76) -> top surfaces at y=114, 90, 68!
    ladder_growth = bl["cloud_ladder_growth"]
    ladder_steps = [(674, 122), (706, 98), (738, 76)]
    for i, (lx, ly) in enumerate(ladder_steps):
        if ladder_growth >= (i + 1) * 0.9:
            st02.draw_floating_cloud_platform(canvas, lx, ly, w=28, h=10)

    # Gold [?] Block at x=796..812, y=18..34 (center=(804, 26), bottom=34)
    qb = st02.create_question_block_sprite(bumped=bl["qblock_bumped"], empty=bl["qblock_empty"])
    qy = 18 + int(bl["qblock_y_offset"])
    canvas.paste(qb, (796, qy), qb)
    # Golden absorption sparkle ring when Star Guide dives into the [?] Block (9.00s <= t <= 9.45s)
    if 9.00 <= t <= 9.45:
        for ang_deg in range(0, 360, 45):
            rad_s = math.radians(ang_deg + t * 180.0)
            r_s = 10.0 * (1.0 - max(0.0, (t - 9.00) / 0.45) * 0.5)
            spx = int(round(804 + math.cos(rad_s) * r_s))
            spy = int(round(qy + 8 + math.sin(rad_s) * r_s))
            if 0 <= spx < NATIVE_WORLD_W and 0 <= spy < NATIVE_H:
                canvas.putpixel((spx, spy), PAL["WHITE"] if ang_deg % 90 == 0 else PAL["GOLD_LIGHT"])

    # Rainbow Star (ejected from [?] block)
    rs = state["rainbow_star"]
    if rs["active"]:
        rs_sprite = st02.create_star_sprite(size=13, t=t)
        canvas.paste(rs_sprite, (int(rs["x"] - 6), int(rs["y"] - 6)), rs_sprite)

    # Screen 4 (960..1280): Spike pit (980..1100), Moving Cloud & Cloud Monsters
    st02.draw_cloud_sea_mass(canvas, 960, 980, ground_y=144, left_cliff=True)
    draw_spike_pit(canvas, 980, 1100, ground_y=144)
    st02.draw_cloud_sea_mass(canvas, 1100, 1280, ground_y=144, right_cliff=True)

    mc = state["moving_cloud"]
    st02.draw_floating_cloud_platform(canvas, int(mc["x"]), int(mc["y"]), w=38, h=14)

    for cm in state["cloud_monsters"]:
        cm_sprite = create_cloud_monster_sprite(rot=cm["rot"])
        canvas.paste(cm_sprite, (int(cm["x"] - 11), int(cm["y"] - 9)), cm_sprite)

    # Screen 5 (1280..1600): Flagpole & Red Brick Castle
    st02.draw_cloud_sea_mass(canvas, 1280, 1600, ground_y=144)
    fp_sprite, castle_sprite = st02.create_flagpole_and_castle_sprites()
    # Erase the baked-in static top flag from fp_sprite so only our dynamic rising flag is drawn!
    fp_sprite = fp_sprite.copy()
    ImageDraw.Draw(fp_sprite).rectangle([9, 5, 23, 19], fill=(0, 0, 0, 0))

    canvas.paste(castle_sprite, (1420, 72), castle_sprite)
    canvas.paste(fp_sprite, (1350, 72), fp_sprite)

    flag_prog = state["flagpole"]["flag_progress"]
    flag_y = int(128 - flag_prog * 50)
    d_c.polygon([(1358, flag_y), (1372, flag_y + 6), (1358, flag_y + 12)], fill=PAL["RED_BASE"], outline=PAL["VOID"])
    canvas.putpixel((1362, flag_y + 6), PAL["WHITE"])

    # Fireworks at castle
    for fw in state.get("fireworks", []):
        fx, fy, age, col_name = fw["x"], fw["y"], fw["age"], fw["color"]
        col = PAL.get(col_name.upper(), PAL["GOLD_LIGHT"])
        r = age * 0.9
        for angle_deg in range(0, 360, 45):
            rad = math.radians(angle_deg)
            px = int(fx + math.cos(rad) * r)
            py = int(fy + math.sin(rad) * r)
            if 0 <= px < NATIVE_WORLD_W and 0 <= py < NATIVE_H:
                d_c.rectangle([px, py, px + 1, py + 1], fill=col)

    # Star Guide ✦
    sg = state["star_guide"]
    if sg["visible"]:
        star_sprite = st02.create_star_sprite(size=13, t=t)
        canvas.paste(star_sprite, (int(sg["x"] - 6), int(sg["y"] - 6)), star_sprite)

    # 16-Bit Pixel Arcade Coin (本关实物信物)
    es = state["end_star"]
    if es["active"]:
        rot_y = es["rot_y"]
        coin_sprite = create_pixel_arcade_coin_sprite(rot_y=rot_y)
        bob = math.sin(t * 5.0) * 2.0
        coin_x = int(es["x"] - coin_sprite.width / 2)
        coin_y = int(es["y"] + bob - 7)
        canvas.paste(coin_sprite, (coin_x, coin_y), coin_sprite)

        for ox, oy in [(-8, -4), (10, -2), (-6, 8), (9, 6)]:
            sp_phase = (t * 4.0 + ox * 0.3) % 1.0
            if sp_phase < 0.4:
                d_c.rectangle([coin_x + ox, coin_y + oy, coin_x + ox + 1, coin_y + oy + 1], fill=PAL["GOLD_LIGHT"])

    # --- 2. Slime & Ghost Trails (Zero-Penetration Anchoring) ---
    sl = state["slime"]
    if sl["visible"]:
        if sl["is_invincible"]:
            for i, gt in enumerate(sl["ghost_trail"][:-1]):
                gx, g_foot_y, g_sy, g_tilt, hue_off = gt
                alpha = int(90 * (i + 1) / len(sl["ghost_trail"]))
                g_sprite, (gcx, gcy, g_ry) = create_pixel_slime_sprite(
                    radius=10, squash_y=g_sy, tilt=g_tilt, look=sl["look"],
                    eye_mode="focus", is_invincible=True, rainbow_phase=hue_off
                )
                g_arr = np.array(g_sprite)
                g_arr[:, :, 3] = (g_arr[:, :, 3] * (alpha / 255.0)).astype(np.uint8)
                faded = Image.fromarray(g_arr, "RGBA")
                g_paste_x = int(round(gx - gcx))
                g_paste_y = int(round(g_foot_y - (gcy + g_ry)))
                canvas.paste(faded, (g_paste_x, g_paste_y), faded)

        slime_sprite, (scx, scy, s_ry) = create_pixel_slime_sprite(
            radius=10, squash_y=sl["squash_y"], tilt=sl["tilt"],
            look=sl["look"], eye_mode=sl["eye_mode"], blink=sl["blink"],
            is_invincible=sl["is_invincible"], rainbow_phase=frame * 0.35
        )
        slime_paste_x = int(round(sl["x"] - scx))
        slime_paste_y = int(round(sl["foot_y"] - (scy + s_ry)))
        canvas.paste(slime_sprite, (slime_paste_x, slime_paste_y), slime_sprite)

        # If Slime is emerging out of the Warp Portal in Beat 1, redraw the Warp Portal over the bottom of Slime!
        if sl.get("pipe_clip"):
            canvas.paste(pipe_sprite, (36, 108), pipe_sprite)

    # --- 3. Overheads & Floating Texts ---
    bubble = state.get("speech_bubble")
    if bubble and sl["visible"]:
        bubble_sprite = create_speech_bubble_sprite(text=bubble)
        bx = int(sl["x"] - 8)
        by = int(sl["foot_y"] - 37)
        canvas.paste(bubble_sprite, (bx, by), bubble_sprite)

    font_float = get_pil_font(9)
    for ft in state.get("floating_texts", []):
        txt, fx, fy, f_alpha, col_t = ft[0], ft[1], ft[2], ft[3], ft[4]
        col = PAL["GOLD_LIGHT"] if col_t == "gold" else (PAL["CYAN_SKY"] if col_t == "cyan" else PAL["CORAL"])
        d_c.text((int(fx), int(fy)), txt, fill=col, font=font_float)

    # --- 4. Sub-Pixel Viewport Crop & 6x Upscaling (Anti-Jitter Rule 3) ---
    cam_x = state["cam_x"]
    base_x = int(math.floor(cam_x))
    offset_x = int(round((cam_x - base_x) * SCALE))

    slice_w = NATIVE_W + 4
    max_slice_x = NATIVE_WORLD_W - slice_w
    safe_base_x = max(0, min(max_slice_x, base_x))
    native_slice = canvas.crop((safe_base_x, 0, safe_base_x + slice_w, NATIVE_H))

    scaled_slice = native_slice.resize((slice_w * SCALE, NATIVE_H * SCALE), Image.Resampling.NEAREST)

    crop_x0 = offset_x
    viewport = scaled_slice.crop((crop_x0, 0, crop_x0 + W, H)).convert("RGB")

    # --- 5. Pitch-Black Cyber Breach Cutscene (Beat 6: 24.8s ~ 28.0s) ---
    door_zoom = state.get("door_zoom", 0.0)
    cr = state.get("cyber_rift", {})
    if door_zoom > 0.0:
        black_bg = Image.new("RGB", (W, H), (3, 1, 8))
        viewport = Image.blend(viewport, black_bg, min(1.0, door_zoom))
        if cr.get("open", 0.0) > 0.01:
            viewport = render_cyber_void_cutscene(viewport, cr, t, frame)

    # --- 6. Screen HUD (World, Score, 3 Hearts) ---
    if door_zoom < 0.85:
        d_hud = ImageDraw.Draw(viewport)
        font_hud = get_pil_font(28)

        d_hud.text((48, 36), "WORLD 02-1 · PIXEL SKY", fill=PAL["WHITE"][:3], font=font_hud)

        score_str = f"SCORE {state['hud_score']:06d}"
        d_hud.text((W // 2 - 130, 36), score_str, fill=PAL["GOLD_LIGHT"][:3], font=font_hud)

        heart_shape = [
            " 11 11 ",
            "1111111",
            "1111111",
            " 11111 ",
            "  111  ",
            "   1   ",
        ]
        hud_rx = W - 220
        for h_idx in range(3):
            hx_base = hud_rx + h_idx * 56
            hy_base = 36
            for ry, row in enumerate(heart_shape):
                for rx, ch in enumerate(row):
                    if ch == "1":
                        d_hud.rectangle([
                            hx_base + rx * 6, hy_base + ry * 6,
                            hx_base + (rx + 1) * 6 - 1, hy_base + (ry + 1) * 6 - 1
                        ], fill=PAL["RED_BASE"][:3])

    return viewport


if __name__ == "__main__":
    from sim_02_pixel import simulate_world_02
    states, events = simulate_world_02()
    test_frame = states[805]
    img = render_frame_from_state(test_frame)
    out_path = os.path.join(tempfile.gettempdir(), "w02_test_frame.png")
    img.save(out_path)
    print(f"[Level 02 Pixel] Saved test frame 805: {out_path} {img.size}")
