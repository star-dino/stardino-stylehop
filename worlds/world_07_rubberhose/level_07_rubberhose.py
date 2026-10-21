# -*- coding: utf-8 -*-
"""
World 07 · 1930s 复古橡皮管爵士乐园 (level_07_rubberhose.py)
High-performance PyCairo + Pillow frame renderer.
100% directly calls and leverages styles/style_07_rubberhose.py (st07) native scene
and full anthropomorphic Gramophone Boss functions!

Visual & Story Integrations:
- st07.draw_35mm_sprocket_borders(ctx)
- st07.draw_vintage_theater_curtains(ctx, bounce_dy=...)
- st07.draw_stage_floorboards_and_spotlights(ctx, pan_dx=...)
- st07.draw_rubber_hose_piano_keyboard(ctx, slime_cx, slime_cy, ring_r, pan_dx=...)
- st07.draw_rubber_hose_gramophone(ctx, gx, gy, scale=..., bounce_phase=..., pan_dx=..., stunned=..., recoil_angle=..., vortex_strength=..., arm_action=..., t=...)
- st07.draw_jazz_musical_notes_stream(ctx, slime_cx, slime_cy, ring_r)
- st07.draw_technicolor_jazz_soundwave_ring(ctx, cx, cy, ring_r)
- st07.draw_star(ctx, cx, cy, r, rot, t)
- slime_engine.draw_world_token(ctx, 7, tok_x, tok_y, tok_r, rot, t, alpha)
- st07.draw_slime(ctx, cx, cy, radius, squash_y=..., tilt=..., look=..., eye_mode=..., blink=..., t=..., draw_crown_star=False)
- st07.apply_celluloid_film_grain_and_scratches(arr, seed=...)
- 35mm Countdown (3-2-1) & 1930s circular Iris-Out centered on boss horn opening
"""

import os
import sys
import math
from typing import Dict, Any
import numpy as np
import cairo
from PIL import Image

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from styles import style_07_rubberhose as st07
from slime_engine import draw_world_token, draw_four_point_star

W, H = 1920, 1080

INK_BLACK   = st07.INK_BLACK
PAPER_CREAM = st07.PAPER_CREAM
TC_BLUE     = st07.TC_BLUE
TC_VIOLET   = st07.TC_VIOLET
TC_CORAL    = st07.TC_CORAL
TC_GOLD     = st07.TC_GOLD
TC_CYAN     = st07.TC_CYAN

# ---------------------------------------------------------------------------
# Note Critter Rendering (Airborne Spit, Lively Rubber-Hose Walk, or Squashed Flat)
# ---------------------------------------------------------------------------
def draw_note_critter(ctx: cairo.Context, critter_dict: dict, t: float = 0.0):
    """Draws an authentic 1930s Rubber-Hose Note Critter (airborne spit, walking, or squashed flat)."""
    if not critter_dict.get("visible", True):
        return
    c_alpha = float(critter_dict.get("alpha", 1.0))
    if c_alpha <= 0.01:
        return

    cx = critter_dict["x"]
    cy = critter_dict["y"]
    squashed = critter_dict.get("squashed", False)
    in_air = critter_dict.get("in_air", False)

    ctx.save()
    ctx.translate(cx, cy)

    if squashed:
        ctx.save()
        if c_alpha < 0.999:
            ctx.push_group()

        # 1. Flattened black ink note pancake (squash_y=0.20, squash_x=1.95)
        ctx.save()
        ctx.scale(1.95, 0.20)
        ctx.arc(0, 0, 48.0, 0, math.tau)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.fill_preserve()
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.set_line_width(2.5)
        ctx.stroke()
        ctx.restore()

        # Bent wilted note stem & flag flattened horizontally
        ctx.new_path()
        ctx.move_to(55.0, -2.0)
        ctx.curve_to(85.0, -14.0, 105.0, 4.0, 130.0, -6.0)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(7.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

        ctx.new_path()
        ctx.move_to(130.0, -6.0)
        ctx.curve_to(145.0, 0.0, 138.0, 10.0, 118.0, 8.0)
        ctx.set_line_width(5.0)
        ctx.stroke()

        # Two white gloved hands splayed flat trembling on piano keys
        for h_s in [-1, 1]:
            tremble_h = math.sin(t * 32.0 + h_s) * 3.0
            ctx.save()
            ctx.translate(h_s * 68.0, 4.0 + tremble_h)
            ctx.scale(h_s * 1.2, 0.45)
            st07.draw_cartoon_glove(ctx, 0, 0, rot=h_s * 0.4, flip=(h_s < 0))
            ctx.restore()

        # Dizzy X X cartoon eyes on squashed note pancake
        for ex in [-22.0, 20.0]:
            ctx.save()
            ctx.translate(ex, -2.0)
            ctx.scale(1.0, 0.6)
            ctx.arc(0, 0, 10.0, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(2.5)
            ctx.stroke()

            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(3.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-5.0, -5.0)
            ctx.line_to(5.0, 5.0)
            ctx.move_to(5.0, -5.0)
            ctx.line_to(-5.0, 5.0)
            ctx.stroke()
            ctx.restore()

        if c_alpha < 0.999:
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(c_alpha)
        ctx.restore()

        # 8 True Parabolic Flying Technicolor Stars and Eighth-Note Sparks!
        stomp_time = critter_dict.get("stomp_time", 10.2)
        dt_stomp = t - stomp_time
        if 0.0 <= dt_stomp < 1.8:
            particle_colors = [TC_GOLD, TC_CYAN, TC_CORAL, TC_VIOLET, TC_BLUE, TC_GOLD, TC_CORAL, TC_CYAN]
            for p_i in range(8):
                ang = (p_i / 8.0) * math.tau + 0.35
                spd = 95.0 + (p_i % 3) * 40.0
                vx = math.cos(ang) * spd
                vy0 = math.sin(ang) * spd - 75.0  # upward blast
                g = 160.0  # gravity pull
                px = vx * dt_stomp
                py = vy0 * dt_stomp + 0.5 * g * (dt_stomp ** 2)
                alpha = max(0.0, 1.0 - dt_stomp / 1.7)
                if alpha <= 0.01:
                    continue

                ctx.save()
                ctx.translate(px, py)
                col = particle_colors[p_i]
                if p_i % 2 == 0:
                    # Flying 4-point Gemini star
                    draw_four_point_star(ctx, 0, 0, 14.0 * (1.0 - dt_stomp * 0.3), 3.5, rot=dt_stomp * 6.0 + p_i)
                    ctx.set_source_rgba(col[0], col[1], col[2], alpha)
                    ctx.fill_preserve()
                    ctx.set_source_rgba(INK_BLACK[0], INK_BLACK[1], INK_BLACK[2], alpha)
                    ctx.set_line_width(1.8)
                    ctx.stroke()
                else:
                    # Flying mini eighth note
                    ctx.rotate(dt_stomp * 5.0 + p_i)
                    ctx.arc(0, 0, 5.5, 0, math.tau)
                    ctx.set_source_rgba(col[0], col[1], col[2], alpha)
                    ctx.fill()
                    ctx.move_to(4, 0)
                    ctx.line_to(4, -14)
                    ctx.curve_to(8, -12, 12, -8, 8, -6)
                    ctx.set_source_rgba(col[0], col[1], col[2], alpha)
                    ctx.set_line_width(2.5)
                    ctx.stroke()
                ctx.restore()

    elif in_air:
        # 2. Airborne Note Critter shot out from horn mouth!
        fly_p = critter_dict.get("fly_p", 0.0)
        ctx.rotate(fly_p * math.pi * 3.5)
        ctx.scale(0.85, 1.30)  # stretched in trajectory

        # Flailing gloved arms
        for arm_s in [-1, 1]:
            arm_x = arm_s * 25.0
            arm_y = -math.sin(t * 22.0 + arm_s) * 12.0
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.curve_to(arm_s * 15, -10, arm_x, arm_y, arm_x, arm_y)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(5.0)
            ctx.stroke()
            st07.draw_cartoon_glove(ctx, arm_x, arm_y, rot=arm_s * 0.8 + math.sin(t * 20) * 0.4, flip=(arm_s < 0))

        # Note Head Body
        ctx.arc(0, 0, 22.0, 0, math.tau)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.fill_preserve()
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.set_line_width(2.5)
        ctx.stroke()

        # Shocked wide eyes
        for ex in [-8.0, 8.0]:
            ctx.arc(ex, -4.0, 6.5, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(1.8)
            ctx.stroke()
            ctx.arc(ex, -4.0, 3.2, 0, math.tau)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.fill()

    else:
        # 3. Ground walking & hopping patrol! Rubber-hose legs & white gloved fists
        walk_phase = critter_dict.get("walk_phase", t * 14.0)
        hop_dy = abs(math.sin(walk_phase)) * 16.0
        ctx.translate(0, -hop_dy)

        # Drop shadow on piano keys
        ctx.save()
        ctx.translate(0, 36.0 + hop_dy)
        ctx.scale(1.25, 0.35)
        ctx.arc(0, 0, 22.0, 0, math.tau)
        ctx.set_source_rgba(0.12, 0.08, 0.06, max(0.18, 0.46 - hop_dy * 0.018))
        ctx.fill()
        ctx.restore()

        # Dynamic rubber-hose legs and big cartoon shoes
        for leg_idx, leg_s in enumerate([-1, 1]):
            # Alternating kicking forward and back
            leg_ang = math.sin(walk_phase + leg_idx * math.pi) * 0.65
            hip_x = leg_s * 8.0
            hip_y = 12.0
            knee_x = hip_x + math.sin(leg_ang) * 14.0
            knee_y = hip_y + 12.0
            ankle_x = hip_x + math.sin(leg_ang) * 26.0
            ankle_y = 35.0

            ctx.new_path()
            ctx.move_to(hip_x, hip_y)
            ctx.curve_to(knee_x + leg_s * 4, knee_y, ankle_x - leg_s * 2, ankle_y - 6, ankle_x, ankle_y)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(5.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

            # Retro cartoon shoe with heel flip
            ctx.save()
            ctx.translate(ankle_x, ankle_y)
            ctx.rotate(-leg_ang * 0.75)
            ctx.scale(1.35, 0.78)
            ctx.arc(0, 0, 8.5, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(2.4)
            ctx.stroke()
            # Shoe sole rim
            ctx.move_to(-8, 4)
            ctx.line_to(8, 4)
            ctx.set_line_width(2.0)
            ctx.stroke()
            ctx.restore()

        # Dynamic rubber-hose arms with 4-finger white gloves swinging menacingly
        for arm_idx, arm_s in enumerate([-1, 1]):
            arm_ang = -math.sin(walk_phase + arm_idx * math.pi) * 0.75
            sh_x = arm_s * 14.0
            sh_y = 2.0
            hand_x = sh_x - 18.0 + math.sin(arm_ang) * 14.0
            hand_y = 4.0 + math.cos(arm_ang) * 12.0

            ctx.new_path()
            ctx.move_to(sh_x, sh_y)
            ctx.curve_to(sh_x - 8, sh_y + 10, hand_x + 6, hand_y, hand_x, hand_y)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(4.5)
            ctx.stroke()

            ctx.save()
            ctx.translate(hand_x, hand_y)
            ctx.scale(0.85, 0.85)
            st07.draw_cartoon_glove(ctx, 0, 0, rot=-0.4 + arm_ang * 0.6, flip=False)
            ctx.restore()

        # Note Head Body (tilted forward aggressively)
        ctx.save()
        ctx.rotate(-0.16 + math.sin(walk_phase) * 0.06)
        ctx.scale(1.20, 0.94)
        ctx.arc(0, 0, 21.0, 0, math.tau)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.fill_preserve()
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.set_line_width(2.2)
        ctx.stroke()
        ctx.restore()

        # Note stem & whipping flag
        flag_whip = math.sin(walk_phase * 2.0) * 8.0
        ctx.new_path()
        ctx.move_to(16.0, -4.0)
        ctx.curve_to(20.0, -32.0, 26.0, -50.0, 20.0 + flag_whip * 0.2, -68.0)
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(7.5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

        ctx.new_path()
        ctx.move_to(20.0 + flag_whip * 0.2, -68.0)
        ctx.curve_to(48.0 + flag_whip, -58.0, 52.0 + flag_whip, -36.0, 34.0 + flag_whip * 0.5, -26.0)
        ctx.curve_to(32.0, -40.0, 25.0, -52.0, 20.0 + flag_whip * 0.2, -68.0)
        ctx.close_path()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.fill()

        # Wicked cartoon villain grin / sharp teeth
        ctx.new_path()
        ctx.arc(0.0, 8.0, 10.0, 0.15 * math.pi, 0.85 * math.pi)
        ctx.close_path()
        ctx.set_source_rgb(*PAPER_CREAM)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_BLACK)
        ctx.set_line_width(2.0)
        ctx.stroke()
        for tooth_x in [-5.0, 0.0, 5.0]:
            ctx.move_to(tooth_x, 8.0)
            ctx.line_to(tooth_x, 14.0)
            ctx.stroke()

        # Slanted villain V-eyebrows & glaring Pie-Cut eyes looking at slime
        for ex in [-7.5, 7.5]:
            ctx.arc(ex, -2.5, 5.5, 0, math.tau)
            ctx.set_source_rgb(*PAPER_CREAM)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(1.5)
            ctx.stroke()

            # Glaring pupil looking left toward slime
            ctx.arc(ex - 2.0, -2.5, 2.8, 0, math.tau)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.fill()

            # Angry V-eyebrow
            ctx.new_path()
            if ex < 0:
                ctx.move_to(ex - 6.0, -10.0)
                ctx.line_to(ex + 6.0, -6.0)
            else:
                ctx.move_to(ex - 6.0, -6.0)
                ctx.line_to(ex + 6.0, -10.0)
            ctx.set_source_rgb(*INK_BLACK)
            ctx.set_line_width(3.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

    ctx.restore()

# ---------------------------------------------------------------------------
# Pop Icons (? and !)
# ---------------------------------------------------------------------------
def draw_pop_icon(ctx: cairo.Context, icon_dict: dict, slime_x: float, slime_y: float, slime_r: float):
    """Draws a vintage dip-pen cartoon question mark or exclamation mark above slime's head."""
    if not icon_dict:
        return
    itype = icon_dict.get("type", "?")
    alpha = icon_dict.get("alpha", 1.0)
    if alpha <= 0.01:
        return

    cx = slime_x + 12.0
    cy = slime_y - slime_r - 42.0

    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(1.1, 1.1)

    # Cream cartoon backing / glow
    ctx.select_font_face("Impact", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(68.0)

    # Outline
    ctx.move_to(-16.0, 20.0)
    ctx.text_path(itype)
    ctx.set_source_rgba(1.0, 0.98, 0.92, alpha)
    ctx.set_line_width(12.0)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()

    # Black India ink fill
    ctx.move_to(-16.0, 20.0)
    ctx.text_path(itype)
    ctx.set_source_rgba(INK_BLACK[0], INK_BLACK[1], INK_BLACK[2], alpha)
    ctx.fill_preserve()
    ctx.set_line_width(2.5)
    ctx.stroke()

    ctx.restore()

# ---------------------------------------------------------------------------
# 35mm Countdown Overlay (0.0s - 1.2s)
# ---------------------------------------------------------------------------
def draw_35mm_countdown(ctx: cairo.Context, num: int):
    """Draws the classic 1930s 35mm film reel circle and 3-2-1 countdown."""
    cx, cy = 960.0, 540.0
    ctx.save()

    # Subtle sepia projection vignette over the closed theater curtains
    ctx.set_source_rgba(0.08, 0.06, 0.05, 0.22)
    ctx.rectangle(84, 0, W - 168, H)
    ctx.fill()

    # Concentric target circles
    ctx.set_source_rgba(0.96, 0.92, 0.84, 0.88)
    ctx.set_line_width(5.0)
    ctx.arc(cx, cy, 260.0, 0, math.tau)
    ctx.stroke()

    ctx.set_line_width(3.0)
    ctx.arc(cx, cy, 200.0, 0, math.tau)
    ctx.stroke()

    # Crosshairs
    ctx.set_line_width(3.5)
    ctx.move_to(cx - 300.0, cy)
    ctx.line_to(cx + 300.0, cy)
    ctx.move_to(cx, cy - 300.0)
    ctx.line_to(cx, cy + 300.0)
    ctx.stroke()

    # Big bold countdown number
    ctx.select_font_face("Impact", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(240.0)
    text_str = str(num)
    extents = ctx.text_extents(text_str)
    tx = cx - extents.width * 0.5 - extents.x_bearing
    ty = cy - extents.height * 0.5 - extents.y_bearing

    ctx.move_to(tx, ty)
    ctx.text_path(text_str)
    ctx.set_source_rgb(0.96, 0.92, 0.84)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK_BLACK)
    ctx.set_line_width(6.0)
    ctx.stroke()

    ctx.restore()

# ---------------------------------------------------------------------------
# 1930s Circular Black Iris-Out Overlay (24.2s - 26.0s)
# ---------------------------------------------------------------------------
def draw_iris_out(ctx: cairo.Context, iris_dict: dict):
    """Draws the 1930s circular black Iris-Out contracting onto the horn opening."""
    if not iris_dict.get("active", False):
        return
    cx, cy = iris_dict["center"]
    r = iris_dict["radius"]

    ctx.save()
    # Fill whole screen with black, excluding the circular hole
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.rectangle(0, 0, W, H)
    if r > 0.5:
        ctx.arc(cx, cy, r, 0, math.tau)
    ctx.set_source_rgb(0.06, 0.05, 0.04)
    ctx.fill()

    if r > 1.0:
        # Subtle vintage feathered ring edge
        ctx.arc(cx, cy, r, 0, math.tau)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.65)
        ctx.set_line_width(6.0)
        ctx.stroke()

    ctx.restore()

# ---------------------------------------------------------------------------
# API Contract: render_frame_from_state
# ---------------------------------------------------------------------------
def render_frame_from_state(state: Dict[str, Any]) -> np.ndarray:
    """
    Renders a single 1920x1080 frame from the simulation state snapshot.
    Returns a (1080, 1920, 4) uint8 BGRA numpy array for render_video_parallel.
    """
    t = state["t"]
    pan_dx = 0.0

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    # 1. Base Stage & Spotlights (Celluloid sky & perspective floorboards)
    st07.draw_stage_floorboards_and_spotlights(ctx, pan_dx=pan_dx)

    # 2. 3D 透视 S 型波浪黑白钢琴键大道
    slime = state["slime"]
    slime_cx = slime["x"]
    slime_cy = slime["y"]
    slime_r = slime["radius"]
    slime_foot_y = slime.get("foot_y")
    ring_radius = state.get("tc_ring_radius", 0.0)

    critters = state.get("critters", {})
    critter_contacts = [
        (c["x"], c["y"] + 24.0) for c in critters.values()
        if c.get("visible", False) and not c.get("in_air", False) and not c.get("squashed", False)
    ]
    st07.draw_rubber_hose_piano_keyboard(
        ctx,
        slime_cx,
        slime_cy,
        ring_radius,
        pan_dx=pan_dx,
        slime_foot_y=slime_foot_y,
        critter_contacts=critter_contacts,
    )

    # 3. Note Critters along the wavy piano keyboard
    for c_key, c_val in critters.items():
        draw_note_critter(ctx, c_val, t=t)

    # 4. Stream of Jazz Musical Notes
    st07.draw_jazz_musical_notes_stream(ctx, slime_cx, slime_cy, ring_radius, t=t)

    # 5. Technicolor Jazz Soundwave Rings
    rings = state.get("soundwave_rings", [])
    for r_item in rings:
        r_alpha = float(r_item.get("alpha", 1.0))
        if r_alpha > 0.01:
            ctx.push_group()
            st07.draw_technicolor_jazz_soundwave_ring(ctx, r_item["cx"], r_item["cy"], r_item["r"])
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(r_alpha)

    # 6. Physical Collectible Token: Spinning Vinyl Record & Eighth Note (World 7)
    token = state.get("token", {})
    if token.get("visible", False) and token.get("alpha", 0.0) > 0.01:
        draw_world_token(
            ctx,
            world_num=7,
            cx=token["x"],
            cy=token["y"],
            r=token["r"],
            rot=token["rot"],
            t=t,
            alpha=token["alpha"],
        )

    # 7. Giant Anthropomorphic Brass Gramophone Boss
    boss = state["boss"]
    st07.draw_rubber_hose_gramophone(
        ctx,
        cx=boss["x"],
        cy=boss["y"],
        scale=boss["scale"],
        bounce_phase=boss["bounce_phase"],
        pan_dx=pan_dx,
        stunned=boss["stunned"],
        recoil_angle=boss["recoil_angle"],
        vortex_strength=boss["vortex_strength"],
        arm_action=boss.get("arm_action", 1.0),
        t=t,
        boss_state=boss,
    )

    # 8. Guiding Star ✦ hovering above boss horn (or swirling into horn during suction)
    star = state.get("guiding_star", {})
    if star.get("visible", False):
        st07.draw_star(ctx, star["x"], star["y"], r=star["r"], rot=star["rot"], t=t)

    # 9. Protagonist Star-Spark Slime (MOUTHLESS + 3D Capsule Eyes + C-infinity projection)
    if slime.get("visible", True):
        st07.draw_slime(
            ctx,
            cx=slime["x"],
            cy=slime["y"],
            radius=slime["radius"],
            squash_y=slime["squash_y"],
            tilt=slime["tilt"],
            look=slime["look"],
            eye_mode=slime["eye_mode"],
            blink=slime["blink"],
            t=t,
            draw_crown_star=False,  # Guiding star is above boss, no crown star
        )

    # 10. Pop Icon (? or !) above slime's head
    pop_icon = state.get("pop_icon")
    if pop_icon:
        draw_pop_icon(ctx, pop_icon, slime["x"], slime["y"], slime["radius"])

    # 11. Vintage Theater Pelmet & Curtains (with 132 BPM bounce_dy & opening reveal)
    st07.draw_vintage_theater_curtains(
        ctx,
        bounce_dy=state.get("curtain_bounce_dy", 0.0),
        open_prog=state.get("curtain_open_prog", 1.0),
    )

    # 12. 35mm Celluloid Film Sprocket Borders
    st07.draw_35mm_sprocket_borders(ctx)

    # 13. Countdown Overlay (t < 1.2s)
    if state.get("countdown_active", False):
        draw_35mm_countdown(ctx, state.get("countdown_num", 3))

    # 14. 1930s Circular Black Iris-Out Transition
    iris = state.get("iris_out", {})
    if iris.get("active", False):
        draw_iris_out(ctx, iris)

    # Flush Cairo surface to buffer
    surface.flush()
    buf = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape((H, W, 4))
    bgra = buf.copy()

    # 15. Authentic Celluloid Film Grain & Scratches
    st07.apply_celluloid_film_grain_and_scratches(bgra, seed=state.get("film_seed", 1934))

    return bgra

if __name__ == "__main__":
    from sim_07_rubberhose import run_simulation
    print("Testing single frame render with level_07_rubberhose...")
    states, _ = run_simulation()
    test_idx = 180  # 6.0s
    frame_bgra = render_frame_from_state(states[test_idx])
    print(f"Rendered frame {test_idx}: shape={frame_bgra.shape}, dtype={frame_bgra.dtype}")
    # Convert BGRA -> RGBA for Pillow
    img = Image.fromarray(frame_bgra[:, :, [2, 1, 0, 3]])
    test_out = "/tmp/test_world_07_frame.png"
    img.save(test_out)
    print(f"Saved test frame to {test_out}")
