# -*- coding: utf-8 -*-
"""
StyleHop · World 02 · 16-Bit 像素横版大闯关 (style_02_pixel.py)
Native 1280x180 Retro Pixel Scroll -> 6x Nearest Upscale (7680x1080) -> Smooth Camera Viewport (1920x1080)
Upgrades:
1. Completely fixes the `★ LEVEL UP! / 好奇心 +999` dialogue box overlap bug (taller 86x38 box,
   hand-crafted pixel bitmap font for `LEVEL UP!` in bright gold on row 1, `好奇心 +999` in
   cyan-blue on row 2 with a guaranteed 6px native / 36px screen vertical gap).
2. Fuses v3's rich pixel level layers into the keyframe viewport:
   - Upper-left floating pixel grass island with round pixel tree & cascading pixel waterfall.
   - Chasm updraft sparkles & floating cloud bridge platform.
   - Central stepped brick staircase, leaping Bayer-dithered Pixel Slime hitting Gold `[?]` block,
     bursting pixel coins, and colorful 4-point pixel star `✦`.
   - Right elevated cloud platform with v3's cute big-eyed pixel red ladybug monster +
     far-right flagpole & red brick castle silhouette peeking in on the horizon.
   - Top-right `♥♥♥` pixel hearts HUD (no external UI title badge).
"""

import os
import sys
import math
import numpy as np
import cairo
from PIL import Image, ImageDraw

# Repo root derived from this file (styles/style_02_pixel.py)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from corelib.math_ops import clamp, lerp, smoothstep, smootherstep, ease_out_cubic, ease_out_back
from slime_engine import get_pil_font

# Screen & World Dimensions
W, H = 1920, 1080
NATIVE_W, NATIVE_H = 320, 180
SCALE = 6
WORLD_W, WORLD_H = 1280 * SCALE, 180 * SCALE  # 7680 x 1080 (4 screens)
NATIVE_WORLD_W = 1280

# ---------------------------------------------------------------------------
# Strict Limited 16-Bit Color Palette (32 Indexed Colors)
# ---------------------------------------------------------------------------
PAL = {
    # Outlines & Shadows
    "VOID": (20, 18, 40, 255),           # #141228 Deepest outline / abyss / castle door
    "NIGHT": (20, 18, 58, 255),          # #14123A Upper night sky
    "DEEP_BLUE": (34, 36, 104, 255),     # #222468 Mid-upper sky
    "MID_BLUE": (50, 66, 168, 255),      # #3242A8 Mid sky
    "ROYAL_BLUE": (66, 133, 244, 255),   # #4285F4 Sky / Slime primary blue
    "CYAN_SKY": (79, 185, 255, 255),     # #4FB9FF Sky / Slime cyan highlight / Dialog line 2
    "PALE_BLUE": (152, 218, 255, 255),   # #98DAFF Lower sky / Waterfall / Cyan highlight
    "ICE_BLUE": (226, 240, 255, 255),    # #E2F0FF Horizon / Specular shine
    "WHITE": (255, 255, 255, 255),       # #FFFFFF Eyes, cloud highlights, star core

    # Slime Purples & Corals
    "VIOLET": (117, 89, 232, 255),       # #7559E8 Slime iris violet
    "LAVENDER": (160, 132, 210, 255),    # #A084D2 Slime light violet
    "DUSK_PINK": (206, 172, 226, 255),   # #CEACE2 Slime / sky dusk tint
    "CORAL": (217, 101, 112, 255),       # #D96570 Slime dawn coral pink
    "ROSE": (246, 210, 232, 255),        # #F6D2E8 Slime soft highlight pink
    "PEACH": (255, 222, 206, 255),       # #FFDECE Warm horizon

    # Clouds & Platforms
    "CLOUD_SHADOW_1": (178, 196, 240, 255),  # #B2C4F0 Cloud body shadow
    "CLOUD_SHADOW_2": (124, 140, 214, 255),  # #7C8CD6 Cloud deep shadow
    "CLOUD_OUTLINE": (84, 92, 176, 255),     # #545CB0 Cloud puff boundary

    # Gold [?] Block, Coins & Sparks
    "GOLD_LIGHT": (255, 236, 136, 255),  # #FFEC88 Question mark / Dialog line 1 highlight
    "GOLD_BASE": (255, 198, 44, 255),    # #FFC62C Question block & coin base
    "GOLD_DARK": (216, 146, 0, 255),     # #D89200 Gold shadow
    "GOLD_SHADOW": (128, 80, 0, 255),    # #805000 Gold darkest bevel / rivet

    # Empty Block State
    "BLOCK_EMPTY_LIGHT": (208, 184, 152, 255),
    "BLOCK_EMPTY_BASE": (148, 120, 92, 255),
    "BLOCK_EMPTY_DARK": (104, 80, 56, 255),

    # Terracotta Stepped Bricks, Island Dirt & Castle
    "BRICK_LIGHT": (232, 136, 104, 255),  # #E88868 Brick top highlight
    "BRICK_BASE": (184, 84, 56, 255),     # #B85438 Brick red base
    "BRICK_DARK": (136, 48, 24, 255),     # #883018 Brick shadow
    "BRICK_MORTAR": (74, 24, 12, 255),    # #4A180C Mortar seams

    # Foliage & Warp Portal Greens
    "GREEN_LIGHT": (160, 248, 144, 255),  # #A0F890 Pipe highlight / Grass top
    "GREEN_BASE": (88, 200, 80, 255),     # #58C850 Pipe / Grass primary green
    "GREEN_DARK": (40, 136, 40, 255),     # #288828 Pipe / Grass shadow
    "GREEN_DEEP": (16, 76, 16, 255),      # #104C10 Pipe rim darkest shadow

    # Ladybug & HUD Hearts
    "RED_LIGHT": (255, 112, 128, 255),    # #FF7080 Heart / Ladybug shine
    "RED_BASE": (232, 48, 64, 255),       # #E83040 Heart / Ladybug red
    "RED_DARK": (150, 24, 40, 255),       # #961828 Heart / Ladybug dark ruby
}

# 4x4 Bayer Dithering Matrix
BAYER_4X4 = np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5]
], dtype=np.float32) / 16.0 - 0.46875

# 2x2 Bayer Matrix for micro-dither
BAYER_2X2 = np.array([
    [0, 2],
    [3, 1]
], dtype=np.float32) / 4.0 - 0.375

# Crisp 5x7 Pixel Bitmap Glyphs for Zero-Overlap Dialog Text ("LEVEL UP!" & "+999")
PIXEL_GLYPHS_5X7 = {
    "L": [
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "11111",
    ],
    "E": [
        "11111",
        "10000",
        "10000",
        "11110",
        "10000",
        "10000",
        "11111",
    ],
    "V": [
        "10001",
        "10001",
        "10001",
        "10001",
        "01010",
        "01010",
        "00100",
    ],
    "U": [
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01110",
    ],
    "P": [
        "11110",
        "10001",
        "10001",
        "11110",
        "10000",
        "10000",
        "10000",
    ],
    "!": [
        "01100",
        "01100",
        "01100",
        "01100",
        "01100",
        "00000",
        "01100",
    ],
    "+": [
        "00000",
        "00100",
        "00100",
        "11111",
        "00100",
        "00100",
        "00000",
    ],
    "9": [
        "01110",
        "10001",
        "10001",
        "01111",
        "00001",
        "10001",
        "01110",
    ],
    " ": [
        "000",
        "000",
        "000",
        "000",
        "000",
        "000",
        "000",
    ],
}


def draw_pixel_bitmap_string(img: Image.Image, x0: int, y0: int, text: str,
                             col_top, col_bot, col_shadow):
    """Draws a crisp 5x7 pixel-art string with 1px drop shadow and top/bottom color gradient."""
    cx = x0
    for ch in text:
        grid = PIXEL_GLYPHS_5X7.get(ch)
        if grid is None:
            cx += 4
            continue
        gw = len(grid[0])
        gh = len(grid)
        # Shadow pass
        for ry in range(gh):
            for rx in range(gw):
                if grid[ry][rx] == "1":
                    img.putpixel((cx + rx + 1, y0 + ry + 1), col_shadow)
        # Foreground pass
        for ry in range(gh):
            col = col_top if ry < 3 else col_bot
            for rx in range(gw):
                if grid[ry][rx] == "1":
                    img.putpixel((cx + rx, y0 + ry), col)
        cx += gw + 1
    return cx


# ---------------------------------------------------------------------------
# Reusable Pixel Sprites & Procedural Generators
# ---------------------------------------------------------------------------

def create_pixel_slime(radius=10, squash_y=1.0, tilt=0.0, look=(0.3, -0.3),
                       eye_mode="pill", blink=0.0):
    """
    Generate native 20px diameter Slime sprite as RGBA PIL Image.
    Volume conservation: sx = 1 / sqrt(sy).
    Strictly MOUTHLESS, no nose, no blush.
    Pure white capsule eyes at -30 deg cant (near 2x5, far 1x4, narrower far eye).
    Plump rounded jelly dome with rich 3-color brand Bayer dithered gradient.
    """
    sy = max(0.45, min(2.2, squash_y))
    sx = 1.0 / math.sqrt(sy)
    size = int(max(32, radius * 3.4))
    if size % 2 != 0:
        size += 1
    xc, yc = (size - 1) / 2.0, (size - 1) / 2.0

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    cos_t, sin_t = math.cos(-tilt), math.sin(-tilt)
    body_mask = np.zeros((size, size), dtype=bool)

    rx = radius * sx
    ry = radius * sy

    for y in range(size):
        for x in range(size):
            dx = x - xc
            dy = y - yc
            dxr = dx * cos_t - dy * sin_t
            dyr = dx * sin_t + dy * cos_t

            u = dxr / rx
            # Plump bottom jelly dome modifier
            v = dyr / ry
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
                    t_grad = (u + v) * 0.40 + 0.50
                    t_dith = t_grad + 0.14 * BAYER_2X2[y % 2, x % 2]
                    if t_dith < 0.28:
                        c = PAL["CYAN_SKY"]
                    elif t_dith < 0.52:
                        c = PAL["ROYAL_BLUE"]
                    elif t_dith < 0.75:
                        c = PAL["VIOLET"]
                    else:
                        c = PAL["CORAL"]

                    pixels[x, y] = c

    # Specular highlight on upper-left shoulder
    hl_x, hl_y = int(round(xc - rx * 0.55)), int(round(yc - ry * 0.42))
    for ox, oy, col in [(0, 0, PAL["WHITE"]), (1, 0, PAL["WHITE"]), (0, 1, PAL["ICE_BLUE"])]:
        if 0 <= hl_x + ox < size and 0 <= hl_y + oy < size and body_mask[hl_y + oy, hl_x + ox]:
            pixels[hl_x + ox, hl_y + oy] = col

    # Pure White Capsule Eyes (-30 deg tilt, near 2x5, far 1x4, perspective narrower)
    ang = -30.0 * math.pi / 180.0
    ax, ay = math.cos(ang), math.sin(ang)

    base_ox = rx * (0.14 + 0.22 * look[0])
    base_oy = ry * (-0.16 + 0.22 * look[1])

    le_x = int(round(xc + base_ox - 2.6 * ax))
    le_y = int(round(yc + base_oy - 2.6 * ay))
    re_x = int(round(xc + base_ox + 2.6 * ax))
    re_y = int(round(yc + base_oy + 2.6 * ay))

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
        for dx in range(-2, 3):
            set_px(le_x + dx, le_y, PAL["WHITE"])
        for dy in range(-2, 3):
            set_px(re_x, re_y + dy, PAL["WHITE"])
        for dx in range(-1, 2):
            set_px(re_x + dx, re_y, PAL["WHITE"])
    elif eye_mode == "happy":
        for dx, dy in [(-1, 0), (0, -1), (1, 0)]:
            set_px(le_x + dx, le_y + dy, PAL["WHITE"])
        for dx, dy in [(0, -1), (1, 0)]:
            set_px(re_x + dx, re_y + dy, PAL["WHITE"])
    elif eye_mode == "focus":
        for dx in range(-1, 2):
            set_px(le_x + dx, le_y, PAL["WHITE"])
        for dx in range(0, 2):
            set_px(re_x + dx, re_y, PAL["WHITE"])
    elif eye_mode == "wince":
        for dx, dy in [(-1, -1), (0, 0), (-1, 1)]:
            set_px(le_x + dx, le_y + dy, PAL["WHITE"])
        for dx, dy in [(1, -1), (0, 0), (1, 1)]:
            set_px(re_x + dx, re_y + dy, PAL["WHITE"])
    else:
        # Default "pill":
        # Left (near) eye: 2x4 white capsule with dark under-shadow
        for dy in range(-2, 2):
            set_px(le_x, le_y + dy, PAL["WHITE"])
            set_px(le_x + 1, le_y + dy, PAL["WHITE"])
        set_px(le_x, le_y + 2, PAL["VOID"])
        set_px(le_x + 1, le_y + 2, PAL["VOID"])

        # Right (far) eye: 1x3 white capsule (narrower perspective) with dark under-shadow
        for dy in range(-1, 2):
            set_px(re_x, re_y + dy, PAL["WHITE"])
        set_px(re_x, re_y + 2, PAL["VOID"])

    return img, (xc, yc)


def create_star_sprite(size=13, t=0.0):
    """
    13x13 pixel 4-point concave star sprite ✦.
    Brand colors: Cyan/Sky Blue, Iris Violet, Coral Pink + Pure White center core.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()
    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    r_max = cx - 1.0

    for y in range(size):
        for x in range(size):
            dx = abs(x - cx)
            dy = abs(y - cy)
            dist = math.sqrt(dx) + math.sqrt(dy)
            if dist <= math.sqrt(r_max) + 0.15:
                if dx <= 1 and dy <= 1 and (dx + dy <= 1):
                    pixels[x, y] = PAL["WHITE"]
                elif dx + dy <= 2:
                    pixels[x, y] = PAL["ICE_BLUE"]
                elif dx == 0 or dy == 0:
                    if dx >= 3 or dy >= 3:
                        pixels[x, y] = PAL["CORAL"]
                    else:
                        pixels[x, y] = PAL["VIOLET"]
                else:
                    pixels[x, y] = PAL["CYAN_SKY"]
            elif dist <= math.sqrt(r_max) + 0.78:
                pixels[x, y] = PAL["VOID"]

    return img


def create_question_block_sprite(bumped=False, empty=False):
    """16x16 pixel Gold [?] Block sprite."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if empty:
        d.rectangle([0, 0, 15, 15], fill=PAL["VOID"])
        d.rectangle([1, 1, 14, 14], fill=PAL["BLOCK_EMPTY_BASE"])
        d.line([(1, 1), (14, 1)], fill=PAL["BLOCK_EMPTY_LIGHT"])
        d.line([(1, 1), (1, 14)], fill=PAL["BLOCK_EMPTY_LIGHT"])
        d.line([(1, 14), (14, 14)], fill=PAL["BLOCK_EMPTY_DARK"])
        d.line([(14, 1), (14, 14)], fill=PAL["BLOCK_EMPTY_DARK"])
        for rx, ry in [(2, 2), (13, 2), (2, 13), (13, 13)]:
            img.putpixel((rx, ry), PAL["VOID"])
    else:
        d.rectangle([0, 0, 15, 15], fill=PAL["VOID"])
        d.rectangle([1, 1, 14, 14], fill=PAL["GOLD_BASE"])
        d.line([(1, 1), (14, 1)], fill=PAL["GOLD_LIGHT"])
        d.line([(1, 1), (1, 14)], fill=PAL["GOLD_LIGHT"])
        d.line([(1, 14), (14, 14)], fill=PAL["GOLD_SHADOW"])
        d.line([(14, 1), (14, 14)], fill=PAL["GOLD_SHADOW"])
        d.line([(2, 13), (13, 13)], fill=PAL["GOLD_DARK"])
        d.line([(13, 2), (13, 13)], fill=PAL["GOLD_DARK"])
        for rx, ry in [(2, 2), (13, 2), (2, 13), (13, 13)]:
            img.putpixel((rx, ry), PAL["GOLD_SHADOW"])

        q_coords = [
            (6, 3), (7, 3), (8, 3), (9, 3),
            (5, 4), (6, 4), (9, 4), (10, 4),
            (9, 5), (10, 5),
            (8, 6), (9, 6),
            (7, 7), (8, 7),
            (7, 8), (8, 8),
            (7, 11), (8, 11),
            (7, 12), (8, 12),
        ]
        for qx, qy in q_coords:
            img.putpixel((qx + 1, qy + 1), PAL["GOLD_SHADOW"])
        for qx, qy in q_coords:
            img.putpixel((qx, qy), PAL["WHITE"])

    return img


def create_brick_sprite():
    """16x16 pixel 16-bit stepped terracotta stepped brick block."""
    img = Image.new("RGBA", (16, 16), PAL["BRICK_MORTAR"])
    d = ImageDraw.Draw(img)

    for (x0, y0, x1, y1) in [
        (1, 1, 7, 6), (9, 1, 14, 6),
        (1, 8, 3, 14), (5, 8, 11, 14), (13, 8, 14, 14)
    ]:
        d.rectangle([x0, y0, x1, y1], fill=PAL["BRICK_BASE"])
        d.line([(x0, y0), (x1, y0)], fill=PAL["BRICK_LIGHT"])
        d.line([(x0, y0), (x0, y1)], fill=PAL["BRICK_LIGHT"])
        d.line([(x0, y1), (x1, y1)], fill=PAL["BRICK_DARK"])
        d.line([(x1, y0), (x1, y1)], fill=PAL["BRICK_DARK"])

    return img


def create_coin_sprite(anim_frame=0):
    """10x14 pixel rotating gold coin sprite."""
    img = Image.new("RGBA", (10, 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 8, 12], fill=PAL["GOLD_BASE"], outline=PAL["VOID"])
    d.line([(2, 3), (2, 10)], fill=PAL["GOLD_LIGHT"])
    d.line([(3, 2), (6, 2)], fill=PAL["GOLD_LIGHT"])
    d.rectangle([4, 4, 5, 9], fill=PAL["GOLD_DARK"], outline=PAL["GOLD_SHADOW"])
    return img


def create_v3_big_eyed_ladybug_sprite(walk_phase=0.0):
    """
    v3's signature cute, round, big-eyed Pixel Red Ladybug Monster (24x22 native pixels):
    - Plump rounded red shell with black spots and bright glossy highlight
    - Huge expressive cartoon white eyes with dark pupils gazing left at the Slime
    - Cute antennae with glowing gold bobbles and little walking feet
    """
    img = Image.new("RGBA", (24, 22), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    foot_shift = int(round(math.sin(walk_phase * math.pi * 2) * 1.0))

    # Cute antennae on top of head with gold tips
    d.line([(8, 6), (6, 2)], fill=PAL["VOID"])
    d.line([(13, 6), (14, 2)], fill=PAL["VOID"])
    d.rectangle([5, 0, 7, 2], fill=PAL["GOLD_BASE"], outline=PAL["VOID"])
    d.rectangle([13, 0, 15, 2], fill=PAL["GOLD_BASE"], outline=PAL["VOID"])
    img.putpixel((6, 1), PAL["GOLD_LIGHT"])
    img.putpixel((14, 1), PAL["GOLD_LIGHT"])

    # Little walking feet
    for fx in [6 + foot_shift, 11, 16 - foot_shift]:
        d.rectangle([fx, 18, fx + 3, 20], fill=PAL["VOID"])

    # Plump round ladybug body shell
    d.ellipse([2, 5, 21, 19], fill=PAL["RED_BASE"], outline=PAL["VOID"])
    # Lower belly shadow
    d.arc([3, 6, 20, 18], start=15, end=165, fill=PAL["RED_DARK"])
    d.line([(4, 18), (19, 18)], fill=PAL["VOID"])

    # Glossy shell highlight on upper right back
    d.line([(14, 7), (17, 8)], fill=PAL["RED_LIGHT"])
    d.line([(15, 8), (18, 9)], fill=PAL["RED_LIGHT"])

    # Classic black ladybug spots on red shell
    for sx, sy in [(14, 10), (18, 12), (13, 14), (17, 15)]:
        d.rectangle([sx, sy, sx + 1, sy + 1], fill=PAL["VOID"])

    # Two Big Expressive Cartoon Pixel Eyes (looking left toward the Slime)
    # Left eye (4x6) & Right eye (4x6)
    d.rectangle([3, 8, 7, 14], fill=PAL["WHITE"], outline=PAL["VOID"])
    d.rectangle([7, 8, 11, 14], fill=PAL["WHITE"], outline=PAL["VOID"])
    # Pupils + white specular twinkle
    d.rectangle([4, 10, 5, 13], fill=PAL["VOID"])
    d.rectangle([8, 10, 9, 13], fill=PAL["VOID"])
    img.putpixel((5, 10), PAL["WHITE"])
    img.putpixel((9, 10), PAL["WHITE"])

    return img


def create_v3_floating_island_with_tree_and_waterfall():
    """
    v3's iconic Floating Pixel Grass Island (70x58 native pixels):
    - Cute round shaded pixel tree on the left lawn
    - Lush bright-green grass top with hanging pixel tufts
    - Stepped V-shaped faceted terracotta/rock underbelly
    - Sparkling cyan/white pixel waterfall cascading off the right side
    """
    w, h = 70, 58
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    island_y = 22
    island_w = 60
    ix0 = 4
    ix1 = ix0 + island_w
    mid_x = (ix0 + ix1) // 2

    # 1. Stepped V-shaped rocky dirt underbelly (y: 26..45)
    cone_h = 20
    for dy in range(cone_h):
        y = island_y + 4 + dy
        frac = dy / float(cone_h - 1)
        half_span = int(round((island_w * 0.46) * (1.0 - frac * 0.92)))
        x_left = mid_x - half_span
        x_right = mid_x + half_span
        for x in range(x_left, x_right + 1):
            if x == x_left or x == x_right or dy == cone_h - 1:
                col = PAL["VOID"]
            elif x < mid_x - 2:
                # Lit left facet
                col = PAL["BRICK_LIGHT"] if (x + y) % 5 == 0 else PAL["BRICK_BASE"]
            elif x < mid_x + 4:
                # Mid facet
                col = PAL["BRICK_DARK"]
            else:
                # Deep shadow right facet
                col = PAL["BRICK_MORTAR"] if (x - y) % 4 == 0 else PAL["BRICK_DARK"]
            img.putpixel((x, y), col)

    # Diagonal facet seam lines on the rock cone (like v3!)
    d.line([(mid_x - 8, island_y + 5), (mid_x, island_y + 4 + cone_h - 2)], fill=PAL["VOID"])
    d.line([(mid_x + 6, island_y + 5), (mid_x, island_y + 4 + cone_h - 2)], fill=PAL["VOID"])

    # 2. Lush Green Grass Top Layer (y: 21..26)
    d.rectangle([ix0, island_y, ix1, island_y + 5], fill=PAL["GREEN_BASE"], outline=PAL["VOID"])
    d.line([(ix0 + 1, island_y + 1), (ix1 - 1, island_y + 1)], fill=PAL["GREEN_LIGHT"])
    d.line([(ix0 + 1, island_y + 2), (ix1 - 1, island_y + 2)], fill=PAL["GREEN_LIGHT"])
    d.line([(ix0 + 2, island_y + 4), (ix1 - 2, island_y + 4)], fill=PAL["GREEN_DARK"])
    # Hanging grass tooth tufts along bottom edge of lawn
    for gx in range(ix0 + 4, ix1 - 4, 5):
        img.putpixel((gx, island_y + 5), PAL["GREEN_BASE"])
        img.putpixel((gx + 1, island_y + 5), PAL["GREEN_DARK"])
        img.putpixel((gx, island_y + 6), PAL["VOID"])

    # 3. Cute Round Pixel Tree on the left of the island (x: 12..30, y: 2..22)
    tree_cx, tree_cy, tree_r = 21, 10, 8
    # Tree trunk
    d.rectangle([tree_cx - 2, tree_cy + 5, tree_cx + 2, island_y], fill=PAL["BRICK_DARK"], outline=PAL["VOID"])
    d.line([(tree_cx - 1, tree_cy + 6), (tree_cx - 1, island_y - 1)], fill=PAL["BRICK_BASE"])
    # Tree round foliage crown
    for ty in range(tree_cy - tree_r - 1, tree_cy + tree_r + 2):
        for tx in range(tree_cx - tree_r - 1, tree_cx + tree_r + 2):
            dist = math.hypot(tx - tree_cx, ty - tree_cy)
            if dist <= tree_r + 0.4:
                if dist > tree_r - 0.75:
                    col = PAL["VOID"]
                elif (tx - tree_cx) + (ty - tree_cy) < -3.0:
                    col = PAL["GREEN_LIGHT"]
                elif (tx - tree_cx) + (ty - tree_cy) > 3.5:
                    col = PAL["GREEN_DARK"]
                else:
                    col = PAL["GREEN_BASE"]
                if 0 <= tx < w and 0 <= ty < h:
                    img.putpixel((tx, ty), col)

    # 4. Sparkling Pixel Waterfall cascading from right side of island (x: 47..53, y: 22..56)
    wf_x = 48
    for wy in range(island_y + 1, h - 2):
        img.putpixel((wf_x, wy), PAL["PALE_BLUE"])
        img.putpixel((wf_x + 1, wy), PAL["WHITE"] if wy % 3 != 0 else PAL["CYAN_SKY"])
        img.putpixel((wf_x + 2, wy), PAL["CYAN_SKY"] if wy % 2 == 0 else PAL["WHITE"])
        if wy < island_y + 14:
            img.putpixel((wf_x + 3, wy), PAL["PALE_BLUE"])
    # Waterfall top lip & bottom mist droplets
    d.line([(wf_x - 1, island_y + 1), (wf_x + 3, island_y + 1)], fill=PAL["WHITE"])
    for mx, my in [(wf_x - 2, h - 6), (wf_x + 4, h - 5), (wf_x, h - 1), (wf_x + 2, h - 2)]:
        if 0 <= mx < w and 0 <= my < h:
            img.putpixel((mx, my), PAL["WHITE"])

    return img


def create_pipe_sprite(width=28, height=38):
    """Modular green warp portal with rim collar and shaded tube body."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rim_h = 10
    tube_w = width - 4
    tube_x = 2

    for y in range(rim_h, height):
        for x in range(tube_x, tube_x + tube_w):
            rel = (x - tube_x) / float(tube_w - 1)
            if x == tube_x or x == tube_x + tube_w - 1:
                c = PAL["VOID"]
            elif rel < 0.12:
                c = PAL["GREEN_LIGHT"]
            elif rel < 0.55:
                c = PAL["GREEN_BASE"]
            elif rel < 0.85:
                c = PAL["GREEN_DARK"]
            else:
                c = PAL["GREEN_DEEP"]
            img.putpixel((x, y), c)

    for y in range(rim_h):
        for x in range(width):
            rel = x / float(width - 1)
            if y == 0 or y == rim_h - 1 or x == 0 or x == width - 1:
                c = PAL["VOID"]
            elif y == 1:
                c = PAL["GREEN_LIGHT"]
            elif rel < 0.12:
                c = PAL["GREEN_LIGHT"]
            elif rel < 0.55:
                c = PAL["GREEN_BASE"]
            elif rel < 0.85:
                c = PAL["GREEN_DARK"]
            else:
                c = PAL["GREEN_DEEP"]
            img.putpixel((x, y), c)

    return img


def create_flagpole_and_castle_sprites():
    """Flagpole with star flag and red brick castle with arched black door."""
    fp = Image.new("RGBA", (24, 76), (0, 0, 0, 0))
    d_fp = ImageDraw.Draw(fp)
    d_fp.rectangle([0, 68, 15, 75], fill=PAL["GREEN_DARK"], outline=PAL["VOID"])
    d_fp.line([(7, 4), (7, 68)], fill=PAL["WHITE"])
    d_fp.line([(8, 4), (8, 68)], fill=PAL["ICE_BLUE"])
    d_fp.ellipse([5, 0, 10, 5], fill=PAL["GOLD_BASE"], outline=PAL["VOID"])
    d_fp.polygon([(9, 6), (22, 12), (9, 18)], fill=PAL["RED_BASE"], outline=PAL["VOID"])
    fp.putpixel((13, 12), PAL["WHITE"])

    c_w, c_h = 84, 72
    castle = Image.new("RGBA", (c_w, c_h), (0, 0, 0, 0))
    d_c = ImageDraw.Draw(castle)

    d_c.rectangle([6, 20, c_w - 7, c_h - 1], fill=PAL["BRICK_BASE"], outline=PAL["VOID"])
    # Brick mortar texture lines on castle wall
    for by in range(26, c_h - 2, 6):
        d_c.line([(7, by), (c_w - 8, by)], fill=PAL["BRICK_MORTAR"])
    d_c.rectangle([6, 8, 24, 20], fill=PAL["BRICK_BASE"], outline=PAL["VOID"])
    d_c.rectangle([c_w - 25, 8, c_w - 7, 20], fill=PAL["BRICK_BASE"], outline=PAL["VOID"])
    d_c.rectangle([30, 4, 54, 20], fill=PAL["BRICK_BASE"], outline=PAL["VOID"])
    for bx in [6, 14, 22, 30, 38, 46, 60, 68, 74]:
        d_c.rectangle([bx, 0, bx + 4, 4], fill=PAL["BRICK_BASE"], outline=PAL["VOID"])
        d_c.line([(bx + 1, 1), (bx + 3, 1)], fill=PAL["BRICK_LIGHT"])
    # Arched dark portal door
    d_c.rectangle([34, 44, 50, c_h - 1], fill=PAL["VOID"])
    d_c.chord([34, 34, 50, 54], start=180, end=360, fill=PAL["VOID"])

    return fp, castle


def create_heart_sprite():
    """9x8 pixel retro RPG life bar heart."""
    img = Image.new("RGBA", (9, 8), (0, 0, 0, 0))
    outline = [
        (1, 0), (2, 0), (5, 0), (6, 0),
        (0, 1), (3, 1), (4, 1), (7, 1),
        (0, 2), (7, 2),
        (0, 3), (7, 3),
        (1, 4), (6, 4),
        (2, 5), (5, 5),
        (3, 6), (4, 6),
    ]
    for x, y in outline:
        img.putpixel((x, y), PAL["VOID"])

    fill_coords = [
        (1, 1), (2, 1), (5, 1), (6, 1),
        (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
        (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
        (2, 4), (3, 4), (4, 4), (5, 4),
        (3, 5), (4, 5),
    ]
    for x, y in fill_coords:
        img.putpixel((x, y), PAL["RED_BASE"])

    img.putpixel((1, 1), PAL["WHITE"])
    img.putpixel((2, 1), PAL["RED_LIGHT"])
    img.putpixel((1, 2), PAL["RED_LIGHT"])
    return img


def create_dialog_box_sprite():
    """
    16-Bit Pixel Dialogue Popup Box (86x38 native pixels -> 516x228 screen pixels):
    - Guaranteed ZERO OVERLAP between Row 1 and Row 2!
    - Row 1 (strictly y = 6..14): Gold star ★ + Gold pixel-bitmap 'LEVEL UP!'
    - Clear 6-pixel vertical separation gap (y = 15..20, with subtle divider rule at y = 17)
    - Row 2 (strictly y = 21..32): Cyan-Blue ('好奇心 +999')
    """
    bw, bh = 86, 38
    box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)

    # Deep navy RPG dialogue background + double gold frame
    d.rectangle([2, 2, bw - 3, bh - 3], fill=(18, 20, 64, 255))
    d.rectangle([0, 0, bw - 1, bh - 1], outline=PAL["VOID"])
    d.rectangle([1, 1, bw - 2, bh - 2], outline=PAL["GOLD_DARK"])
    d.rectangle([2, 2, bw - 3, bh - 3], outline=PAL["GOLD_BASE"])
    d.line([(3, 3), (bw - 4, 3)], fill=PAL["GOLD_LIGHT"])
    d.line([(3, 3), (3, bh - 4)], fill=PAL["GOLD_LIGHT"])

    # Corner gold rivets
    for rx, ry in [(4, 4), (bw - 5, 4), (4, bh - 5), (bw - 5, bh - 5)]:
        box.putpixel((rx, ry), PAL["GOLD_LIGHT"])

    # --- ROW 1 (y = 6..13): Gold 4-point star icon ★ + 'LEVEL UP!' in bright Gold ---
    # Crisp 7x7 gold star at (6, 6)
    star_coords_core = [(9, 6), (9, 12), (6, 9), (12, 9)]
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if abs(dx) + abs(dy) <= 2:
                box.putpixel((9 + dx + 1, 9 + dy + 1), PAL["VOID"])
                box.putpixel((9 + dx, 9 + dy), PAL["WHITE"] if (dx == 0 and dy == 0) else PAL["GOLD_LIGHT"])
    for sx, sy in star_coords_core:
        box.putpixel((sx + 1, sy + 1), PAL["VOID"])
        box.putpixel((sx, sy), PAL["GOLD_BASE"])

    # Hand-crafted 5x7 pixel bitmap text 'LEVEL UP!' at x = 16, y = 6 (occupies y = 6..13)
    draw_pixel_bitmap_string(
        box, 16, 6, "LEVEL UP!",
        col_top=PAL["GOLD_LIGHT"],
        col_bot=PAL["GOLD_BASE"],
        col_shadow=PAL["VOID"]
    )

    # Subtle inner divider line at y = 17 (separating Row 1 and Row 2)
    d.line([(6, 17), (bw - 7, 17)], fill=(42, 54, 120, 255))

    # --- ROW 2 (y = 21..32): Cyan-Blue '好奇心 +999' ---
    # Render CJK '好奇心' onto an isolated mask, crop tightly to ink bbox, and blit at y = 21..31
    font_cjk = get_pil_font(11)
    cjk_im = Image.new("L", (48, 18), 0)
    d_cjk = ImageDraw.Draw(cjk_im)
    d_cjk.text((1, 0), "好奇心", fill=255, font=font_cjk)
    cjk_arr = np.array(cjk_im) > 105

    ys_nz, xs_nz = np.where(cjk_arr)
    if len(ys_nz) > 0:
        y_min, y_max = int(ys_nz.min()), int(ys_nz.max())
        x_min, x_max = int(xs_nz.min()), int(xs_nz.max())
        sub_mask = cjk_arr[y_min:y_max + 1, x_min:x_max + 1]
        # Constrain height to max 11px so it stays strictly inside y = 21..32
        sh_m, sw_m = sub_mask.shape
        sh_m = min(sh_m, 11)
        sw_m = min(sw_m, 40)
        start_x = 7
        start_y = 21
        for ry in range(sh_m):
            for rx in range(sw_m):
                if sub_mask[ry, rx]:
                    box.putpixel((start_x + rx + 1, start_y + ry + 1), PAL["VOID"])
        for ry in range(sh_m):
            col_cjk = PAL["PALE_BLUE"] if ry < 4 else PAL["CYAN_SKY"]
            for rx in range(sw_m):
                if sub_mask[ry, rx]:
                    box.putpixel((start_x + rx, start_y + ry), col_cjk)
        plus_x = start_x + sw_m + 4
    else:
        plus_x = 46

    # Hand-crafted 5x7 pixel bitmap '+999' in Cyan-Blue at y = 23..30
    draw_pixel_bitmap_string(
        box, plus_x, 23, "+999",
        col_top=PAL["PALE_BLUE"],
        col_bot=PAL["CYAN_SKY"],
        col_shadow=PAL["VOID"]
    )

    return box


def create_pixel_distant_cloud(w=44, h=14):
    """16-Bit stepped-contour distant pixel cloud sprite with 3-tier lilac/rose shading."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    p1 = (int(w * 0.28), int(h * 0.60), int(h * 0.40))
    p2 = (int(w * 0.50), int(h * 0.48), int(h * 0.50))
    p3 = (int(w * 0.72), int(h * 0.60), int(h * 0.40))

    for y in range(h):
        for x in range(w):
            d1 = math.hypot(x - p1[0], y - p1[1]) / float(max(1, p1[2]))
            d2 = math.hypot(x - p2[0], y - p2[1]) / float(max(1, p2[2]))
            d3 = math.hypot(x - p3[0], y - p3[1]) / float(max(1, p3[2]))
            d_min = min(d1, d2, d3)
            if d_min <= 1.0:
                if d_min > 0.80:
                    col = PAL["CLOUD_OUTLINE"]
                elif y > h * 0.65:
                    col = PAL["LAVENDER"]
                elif y < h * 0.32:
                    col = PAL["ROSE"]
                else:
                    col = PAL["DUSK_PINK"]
                im.putpixel((x, y), col)
    return im


# ---------------------------------------------------------------------------
# Full 1280x180 World Background & Terrain Generator
# ---------------------------------------------------------------------------

_STATIC_BG_CACHE = None

def get_static_world_background():
    """
    Render once and cache the entire 1280x180 background long-canvas:
    - Bayer-dithered 16-bit gradient sky across 1280x180
    - Twinkling stars & stepped-contour distant pixel clouds
    """
    global _STATIC_BG_CACHE
    if _STATIC_BG_CACHE is not None:
        return _STATIC_BG_CACHE.copy()

    bg = Image.new("RGBA", (NATIVE_WORLD_W, NATIVE_H), (0, 0, 0, 255))
    pixels = bg.load()

    # Sky gradient with 4x4 Bayer dithering
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

    # Twinkling stars in upper sky (y < 68)
    rng = np.random.RandomState(42)
    star_xs = rng.randint(0, NATIVE_WORLD_W, size=130)
    star_ys = rng.randint(4, 68, size=130)
    for sx, sy in zip(star_xs, star_ys):
        if rng.rand() < 0.28:
            pixels[sx, sy] = PAL["WHITE"]
            if sx > 0: pixels[sx - 1, sy] = PAL["PALE_BLUE"]
            if sx < NATIVE_WORLD_W - 1: pixels[sx + 1, sy] = PAL["PALE_BLUE"]
            if sy > 0: pixels[sx, sy - 1] = PAL["PALE_BLUE"]
            if sy < NATIVE_H - 1: pixels[sx, sy + 1] = PAL["PALE_BLUE"]
        else:
            pixels[sx, sy] = PAL["WHITE"]

    # Stepped pixel distant clouds in the mid-sky
    cloud_sprite = create_pixel_distant_cloud(w=42, h=14)
    for cx in range(30, NATIVE_WORLD_W, 85):
        cy = 96 + int(math.sin(cx * 0.05) * 6)
        bg.paste(cloud_sprite, (cx, cy), cloud_sprite)

    _STATIC_BG_CACHE = bg
    return bg.copy()


def draw_cloud_sea_mass(canvas, x_start, x_end, ground_y=148, left_cliff=False, right_cliff=False):
    """
    Render authentic 16-bit cloud sea ground with puffed shaded domes (v3 + v4 fusion).
    """
    d = ImageDraw.Draw(canvas)
    rng = np.random.RandomState(1337 + int(x_start))

    # 1. Underside shadow bulges
    x = x_start + 4
    while x <= x_end - 4:
        r = rng.randint(13, 18)
        d.ellipse([x - r, ground_y + 12 - r, x + r, ground_y + 12 + r], fill=PAL["CLOUD_SHADOW_2"])
        d.ellipse([x - r + 1, ground_y + 9 - r, x + r - 1, ground_y + 9 + r], fill=PAL["CLOUD_SHADOW_1"])
        x += rng.randint(16, 24)

    # 2. Solid ground base
    d.rectangle([x_start + 4, ground_y + 6, x_end - 4, NATIVE_H], fill=PAL["WHITE"])

    # 3. Scalloped top domes with v3 crescent inner shading
    puffs = []
    x = x_start
    while x <= x_end + 8:
        r = rng.randint(12, 17)
        dy = rng.randint(-3, 3)
        puffs.append((x, ground_y + dy, r))
        x += rng.randint(13, 19)

    for cx, cy, r in puffs:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAL["CLOUD_OUTLINE"])
    for cx, cy, r in puffs:
        d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=PAL["CLOUD_SHADOW_1"])
        d.ellipse([cx - r + 1, cy - r + 1, cx + r - 3, cy + r - 3], fill=PAL["WHITE"])

    d.rectangle([x_start + 4, ground_y + 8, x_end - 4, NATIVE_H], fill=PAL["WHITE"])

    # Bottom row of secondary cloud puffs (like v3's lush multi-layered cloud floor)
    for cx, cy, r in puffs[::2]:
        by = ground_y + 16
        br = r - 1
        d.ellipse([cx - br, by - br, cx + br, by + br], fill=PAL["CLOUD_OUTLINE"])
        d.ellipse([cx - br + 1, by - br + 1, cx + br - 1, by + br - 1], fill=PAL["CLOUD_SHADOW_1"])
        d.ellipse([cx - br + 1, by - br + 1, cx + br - 2, by + br - 3], fill=PAL["WHITE"])

    if left_cliff:
        for ex, ey, er in [(x_end - 4, ground_y + 2, 13), (x_end - 6, ground_y + 14, 11), (x_end - 9, ground_y + 24, 9)]:
            d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=PAL["CLOUD_OUTLINE"])
            d.ellipse([ex - er + 1, ey - er + 1, ex + er - 1, ey + er - 1], fill=PAL["CLOUD_SHADOW_1"])
            d.ellipse([ex - er + 1, ey - er + 1, ex + er - 2, ey + er - 2], fill=PAL["WHITE"])

    if right_cliff:
        for ex, ey, er in [(x_start + 4, ground_y + 2, 13), (x_start + 6, ground_y + 14, 11), (x_start + 9, ground_y + 24, 9)]:
            d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=PAL["CLOUD_OUTLINE"])
            d.ellipse([ex - er + 1, ey - er + 1, ex + er - 1, ey + er - 1], fill=PAL["CLOUD_SHADOW_1"])
            d.ellipse([ex - er + 1, ey - er + 1, ex + er - 2, ey + er - 2], fill=PAL["WHITE"])


def draw_floating_cloud_platform(canvas, cx, cy, w=36, h=14):
    """Draw floating pixel cloud platform (空中云台)."""
    d = ImageDraw.Draw(canvas)
    span = w // 3
    puffs = [(-span, 8), (-span // 2, 9), (0, 10), (span // 2, 9), (span, 8)]
    for ox, r in puffs:
        d.ellipse([cx + ox - r, cy - r, cx + ox + r, cy + r], fill=PAL["CLOUD_OUTLINE"])
    for ox, r in puffs:
        d.ellipse([cx + ox - r + 1, cy - r + 1, cx + ox + r - 1, cy + r - 1], fill=PAL["CLOUD_SHADOW_1"])
        d.ellipse([cx + ox - r + 1, cy - r + 1, cx + ox + r - 2, cy + r - 3], fill=PAL["WHITE"])


# ---------------------------------------------------------------------------
# Core Module Contract Functions
# ---------------------------------------------------------------------------

def draw_slime(ctx, cx, cy, radius, *, squash_y=1.0, tilt=0.0,
               look=(0.0, 0.0), eye_mode="pill", blink=0.0, t=0.0, **style_kw):
    """Draw the 16-Bit pixel slime on a Cairo context with strict NEAREST filter."""
    sprite_img, (scx, scy) = create_pixel_slime(
        radius=10, squash_y=squash_y, tilt=tilt, look=look,
        eye_mode=eye_mode, blink=blink
    )

    arr = np.array(sprite_img, dtype=np.uint8)
    bgra = arr[:, :, [2, 1, 0, 3]].copy()
    sh, sw = bgra.shape[:2]
    sprite_surf = cairo.ImageSurface.create_for_data(bgra, cairo.FORMAT_ARGB32, sw, sh)

    scale_factor = radius / 10.0

    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(scale_factor, scale_factor)
    ctx.set_source_surface(sprite_surf, -scx, -scy)
    ctx.get_source().set_filter(cairo.FILTER_NEAREST)
    ctx.paint()
    ctx.restore()


def draw_star(ctx, cx, cy, r, *, rot=0.0, t=0.0, **style_kw):
    """Draw the 16-Bit pixel four-point star ✦ on a Cairo context."""
    star_img = create_star_sprite(size=13, t=t)
    arr = np.array(star_img, dtype=np.uint8)
    bgra = arr[:, :, [2, 1, 0, 3]].copy()
    sh, sw = bgra.shape[:2]
    star_surf = cairo.ImageSurface.create_for_data(bgra, cairo.FORMAT_ARGB32, sw, sh)

    scale_factor = r / 6.0

    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(rot)
    ctx.scale(scale_factor, scale_factor)
    ctx.set_source_surface(star_surf, -6.0, -6.0)
    ctx.get_source().set_filter(cairo.FILTER_NEAREST)
    ctx.paint()
    ctx.restore()


def build_native_world(t=10.4, state=None):
    """
    Assemble the complete 1280x180 native 4-screen world.
    Screen 3 (x: 640..960) is the keyframe viewport and fuses ALL signature v3 & v4 elements:
    - Left-upper: v3 floating pixel grass island with round pixel tree & sparkling waterfall
    - Left-lower: Cloud cliff, abyss water-geyser basin & floating cloud bridge platform
    - Center: Stepped brick staircase, leaping Bayer-dithered Pixel Slime hitting Gold [?] block,
              bursting gold coins & colorful pixel star ✦
    - Upper-right: Fixed zero-overlap `★ LEVEL UP! / 好奇心 +999` dialogue box
    - Right: Elevated cloud platform with v3's cute big-eyed red ladybug monster +
             far-right flagpole & red brick castle corner peeking on the horizon!
    """
    world = get_static_world_background()
    d_w = ImageDraw.Draw(world)

    island_sprite = create_v3_floating_island_with_tree_and_waterfall()
    ladybug_sprite = create_v3_big_eyed_ladybug_sprite(walk_phase=t * 2.0)
    fp_sprite, castle_sprite = create_flagpole_and_castle_sprites()
    coin_sprite = create_coin_sprite(anim_frame=0)
    brick_sprite = create_brick_sprite()

    # ---------------------------------------------------------
    # Screen 1 (x: 0..320)
    # ---------------------------------------------------------
    draw_cloud_sea_mass(world, 0, 320, ground_y=148)
    pipe = create_pipe_sprite(width=28, height=38)
    world.paste(pipe, (36, 112), pipe)
    world.paste(island_sprite, (145, 38), island_sprite)

    # ---------------------------------------------------------
    # Screen 2 (x: 320..640)
    # ---------------------------------------------------------
    draw_cloud_sea_mass(world, 320, 640, ground_y=148)
    world.paste(ladybug_sprite, (475, 128), ladybug_sprite)

    # ---------------------------------------------------------
    # Screen 3 (x: 640..960) · KEYFRAME MASTERPIECE FOCUS
    # ---------------------------------------------------------
    # 1. Upper-Left: v3's Cute Floating Pixel Grass Island (with round tree & cascading waterfall)
    world.paste(island_sprite, (656, 36), island_sprite)

    # 2. Lower-Left Cloud Sea, Abyss Geyser Basin & Floating Cloud Platform
    draw_cloud_sea_mass(world, 640, 686, ground_y=148, left_cliff=True)

    # Abyss Chasm (x = 686..746) with Bayer-dithered deep ocean/sky void + v3 updraft geyser
    for y in range(146, NATIVE_H):
        rel_abyss = (y - 146) / float(NATIVE_H - 146)
        for x in range(686, 746):
            dith = BAYER_4X4[y % 4, x % 4] * 0.15
            val = rel_abyss + dith
            if val < 0.28:
                c = PAL["DEEP_BLUE"]
            elif val < 0.60:
                c = PAL["MID_BLUE"]
            elif val < 0.82:
                c = PAL["NIGHT"]
            else:
                c = PAL["VOID"]
            world.putpixel((x, y), c)

    # v3-style dark blue vortex basin & vertical sparkling cyan/white updraft streams at x = 690..722
    d_w.ellipse([686, 152, 728, 168], fill=PAL["MID_BLUE"], outline=PAL["CLOUD_OUTLINE"])
    d_w.ellipse([690, 155, 724, 166], fill=PAL["NIGHT"])
    for gx in [694, 700, 707, 714, 720]:
        for gy in range(114, 158, 3):
            col_g = PAL["WHITE"] if (gy + gx) % 2 == 0 else PAL["PALE_BLUE"]
            world.putpixel((gx, gy), col_g)

    # Floating Cloud Platform bridging the chasm (x = 732, y = 132) + floating coins
    draw_floating_cloud_platform(world, 732, 132, w=30, h=12)
    world.paste(coin_sprite, (722, 108), coin_sprite)
    world.paste(coin_sprite, (735, 102), coin_sprite)

    # Right Cloud Ground resumes at world x = 746..960
    draw_cloud_sea_mass(world, 746, 960, ground_y=148, right_cliff=True)

    # 3. Central Stepped Bricks (3-step staircase at x = 758..806)
    # Step 1 (x: 758..774, y: 132..148)
    world.paste(brick_sprite, (758, 132), brick_sprite)
    # Step 2 (x: 774..790, y: 116..148)
    world.paste(brick_sprite, (774, 132), brick_sprite)
    world.paste(brick_sprite, (774, 116), brick_sprite)
    # Step 3 (x: 790..806, y: 100..148)
    world.paste(brick_sprite, (790, 132), brick_sprite)
    world.paste(brick_sprite, (790, 116), brick_sprite)
    world.paste(brick_sprite, (790, 100), brick_sprite)

    # 4. Gold [?] Question Block above peak of stairs (x = 796, y = 48)
    qblock_x = 796
    qblock_y = 48
    qblock = create_question_block_sprite(bumped=True, empty=False)
    world.paste(qblock, (qblock_x, qblock_y), qblock)

    # v3-style subtle Bayer-dithered pixel glow halo around the Slime & [?] block impact zone
    halo_cx, halo_cy = qblock_x + 8, 72
    for hy in range(halo_cy - 26, halo_cy + 26):
        for hx in range(halo_cx - 28, halo_cx + 28):
            if 0 <= hx < NATIVE_WORLD_W and 0 <= hy < NATIVE_H:
                dist_h = math.hypot(hx - halo_cx, hy - halo_cy)
                if 11.0 < dist_h < 25.0 and (hx + hy) % 2 == 0 and BAYER_4X4[hy % 4, hx % 4] > 0.12:
                    world.putpixel((hx, hy), PAL["ICE_BLUE"])

    # Impact starburst sparks between slime head and block bottom
    hit_y = qblock_y + 16
    for sp_x, sp_y in [
        (qblock_x + 2, hit_y), (qblock_x + 7, hit_y + 1), (qblock_x + 13, hit_y),
        (qblock_x - 3, hit_y - 1), (qblock_x + 19, hit_y - 1),
        (qblock_x + 5, hit_y - 2), (qblock_x + 11, hit_y - 2)
    ]:
        d_w.rectangle([sp_x, sp_y, sp_x + 1, sp_y + 1], fill=PAL["WHITE"])

    # 5. Pixel Slime leaping up, head hitting bottom of [?] block
    slime_cx = qblock_x + 8  # 804
    slime_cy = 76            # Head touches block bottom at y = 64

    # Motion ghost trail
    ghost_img, (gcx, gcy) = create_pixel_slime(
        radius=10.5, squash_y=1.10, tilt=0.0, look=(0.35, -0.65), eye_mode="pill"
    )
    g_arr = np.array(ghost_img)
    g_arr[:, :, 3] = (g_arr[:, :, 3] * 0.35).astype(np.uint8)
    ghost_faded = Image.fromarray(g_arr, "RGBA")
    world.paste(ghost_faded, (int(slime_cx - gcx), int(slime_cy + 13 - gcy)), ghost_faded)

    # Main Slime sprite (plump rounded jelly dome)
    slime_img, (scx, scy) = create_pixel_slime(
        radius=10.5, squash_y=1.04, tilt=-0.05, look=(0.35, -0.70),
        eye_mode="pill", blink=0.0
    )
    world.paste(slime_img, (int(slime_cx - scx), int(slime_cy - scy)), slime_img)

    # 6. Pixel Coins & Colorful Pixel Star ✦ bursting out from top of [?] block
    world.paste(coin_sprite, (786, 28), coin_sprite)
    world.paste(coin_sprite, (798, 12), coin_sprite)
    world.paste(coin_sprite, (811, 20), coin_sprite)

    star_x = 822
    star_y = 22
    star = create_star_sprite(size=13, t=t)
    world.paste(star, (star_x, star_y), star)
    # Twinkling cross-sparkles around ✦ and coins
    for sx, sy in [(star_x - 3, star_y + 11), (star_x + 14, star_y - 1), (782, 22), (814, 10)]:
        world.putpixel((sx, sy), PAL["WHITE"])
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            world.putpixel((sx + dx, sy + dy), PAL["GOLD_LIGHT"])

    # 7. Fixed Zero-Overlap Dialogue Box: ★ LEVEL UP! / 好奇心 +999 (x = 838..924, y = 10..48)
    dialog_box = create_dialog_box_sprite()
    box_x = 838
    box_y = 10
    # Speech-bubble pointer tail drawn BEFORE pasting box so it never overlaps box interior!
    d_w.polygon([(box_x + 1, box_y + 26), (box_x + 1, box_y + 33), (box_x - 7, box_y + 35)],
                fill=PAL["GOLD_BASE"], outline=PAL["VOID"])
    world.paste(dialog_box, (box_x, box_y), dialog_box)

    # 8. Right Elevated Cloud Platform with v3's Cute Big-Eyed Pixel Red Ladybug (x = 868, y = 122)
    draw_floating_cloud_platform(world, 868, 122, w=42, h=14)
    world.paste(ladybug_sprite, (856, 97), ladybug_sprite)

    # 9. Far-Right Horizon of Screen 3: Flagpole & Red Brick Castle peeking in (x = 912..960+)
    world.paste(fp_sprite, (910, 74), fp_sprite)
    world.paste(castle_sprite, (928, 76), castle_sprite)

    # ---------------------------------------------------------
    # Screen 4 (x: 960..1280)
    # ---------------------------------------------------------
    draw_cloud_sea_mass(world, 960, 1280, ground_y=148)
    world.paste(fp_sprite, (1060, 74), fp_sprite)
    world.paste(castle_sprite, (1130, 76), castle_sprite)

    return world


def render_world(cam_x, cam_y, t, state=None) -> Image.Image:
    """
    Render world viewport at 1920x1080.
    1. Build native 1280x180 world.
    2. Upscale 6x using Image.Resampling.NEAREST to 7680x1080.
    3. Smoothly crop 1920x1080 viewport using cam_x / cam_y.
    4. Overlay HUD (3 pixel hearts ♥♥♥) in top-right screen space.
    """
    native_world = build_native_world(t=t, state=state)

    # 6x NEAREST upscaling
    world_6x = native_world.resize((WORLD_W, WORLD_H), Image.Resampling.NEAREST)

    max_cam_x = WORLD_W - W
    max_cam_y = WORLD_H - H
    cx = int(round(clamp(cam_x, 0, max_cam_x)))
    cy = int(round(clamp(cam_y, 0, max_cam_y)))

    viewport = world_6x.crop((cx, cy, cx + W, cy + H))

    # Overlay HUD: Top-right 3 pixel hearts ♥♥♥ (Screen coordinates, no top-left title badge)
    heart = create_heart_sprite()
    heart_6x = heart.resize((heart.width * SCALE, heart.height * SCALE), Image.Resampling.NEAREST)

    hud_start_x = W - 3 * (heart_6x.width + 12) - 42
    hud_y = 36
    for i in range(3):
        hx = hud_start_x + i * (heart_6x.width + 12)
        viewport.paste(heart_6x, (hx, hud_y), heart_6x)

    return viewport.convert("RGB")


def render_keyframe() -> Image.Image:
    """
    Render World 02 keyframe at t = 10.4s (Screen 3: hitting [?] block).
    Camera centered on Screen 3: cam_x = 640 * 6 = 3840, cam_y = 0.
    """
    return render_world(cam_x=640.0 * SCALE, cam_y=0.0, t=10.4, state=None)


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "style_02_pixel.png")
    kf = render_keyframe()
    kf.save(out_path, format="PNG")
    print(f"[World 02 Pixel] Saved keyframe: {out_path} ({kf.size[0]}x{kf.size[1]})")
