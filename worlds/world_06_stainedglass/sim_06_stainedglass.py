# -*- coding: utf-8 -*-
"""
World 06 · 哥特玫瑰彩窗圣殿 (sim_06_stainedglass.py)
Fixed-timestep (30fps, 26.0s = 780 frames) multi-zone simulation engine.

Combines:
  1. 100% authentic hard-facet Voronoi stained-glass & crystal prism aesthetic (style_06_stainedglass.py).
  2. Expansive 4200x2160 4-Zone Cathedral scrolling stage (zero single-screen cramping):
     - Act 1 (0.0-5.2s)  Zone 1: Obsidian Gallery entry, stomping 3 Floor Rosettes to ignite 3 Lancet Windows,
                                 braking at the Nave Abyss [?] & spotting the Crystal Triangular Prism [!].
     - Act 2 (5.2-12.0s) Zone 2: Headbutting the Giant Hard-Facet Crystal Triangular Prism to refract the white
                                 zenith sunbeam into Ruby/Emerald/Sapphire dispersion laser beams, raising & lighting
                                 4 Beveled Gothic Diamond Stained-Glass Steps, and hopping up to the Belfry Terrace.
     - Act 3 (12.0-19.4s) Zone 3: First leap pulls the Golden Bell Rope (+15 deg chime); second deep-squash leap
                                 headbutts the Giant Stained-Glass Bell's lower-left lip (-28 deg swing), blasting
                                 7 concentric hard-facet stained-glass shockwaves, unfurling the 7-Color Prismatic
                                 Ribbon Bridge, and absorbing the Stained-Glass Mini Bell Token (✦ ✦).
     - Act 4 (19.4-26.0s) Zone 4: 4 rhythmic high-elasticity hops along the 7-Color Prismatic Ribbon Bridge Bezier
                                 spine right into the solar core of the Grand 3-Ring Gothic Rose Window (3480, 420),
                                 which spins, desaturates, and morphs into the 1930s film reel (3-2-1) for World 07.
"""

import math
from typing import Dict, List, Tuple, Any
import os
import sys

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
sys.path.insert(0, ROOT_DIR)

from slime_engine import (
    SpringDamper1D,
    SpringDamper2D,
    eval_continuous_hop_chain,
    eval_targeted_jump,
)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def lerp(a: float, b: float, u: float) -> float:
    return float(a) + (float(b) - float(a)) * clamp(u, 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if abs(edge1 - edge0) < 1e-9:
        return 1.0 if x >= edge1 else 0.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

FPS = 30
DURATION = 26.0
TOTAL_FRAMES = int(FPS * DURATION)  # 780 frames
SLIME_R = 68.0  # Exact diameter 136px matching style_06_stainedglass.py

# ---------------------------------------------------------------------------
# World Coordinate Landmarks (4200 x 2160 Expansive Cathedral Stage)
# ---------------------------------------------------------------------------
GALLERY_FLOOR_Y = 1620.0
ROSETTES_X = [520.0, 760.0, 1000.0]
CLIFF_EDGE_X = 1090.0

# Crystal Prism Pedestal & Giant Triangular Prism
PRISM_PEDESTAL = (1150.0, 1360.0)  # (center_x, top_y)
PRISM_CENTER = (1235.0, 1265.0)

# 4 Suspended Beveled Gothic Diamond Stained-Glass Steps across the Nave Abyss
STEP_COORDS = [
    (1470.0, 1340.0, 224.0, 56.0, (0.12, 0.48, 0.98), (0.28, 0.78, 1.00)),  # Step 1: Cobalt Sapphire
    (1720.0, 1220.0, 214.0, 54.0, (0.06, 0.78, 0.48), (0.35, 0.96, 0.72)),  # Step 2: Chartres Emerald
    (1970.0, 1100.0, 206.0, 52.0, (0.98, 0.70, 0.14), (1.00, 0.90, 0.42)),  # Step 3: Imperial Amber Gold
    (2220.0,  980.0, 232.0, 58.0, (0.90, 0.24, 0.42), (0.72, 0.32, 0.96)),  # Step 4: Ruby-Amethyst Belfry Terrace
]

# Giant Stained-Glass Bell & Twin Resonance Chime Bells
GIANT_BELL_POS = (2480.0, 620.0)
BELL_STRIKE_LIP = (2348.0, 728.0)  # Exact lower-left rim contact point
ROPE_GRAB_PT = (2375.0, 835.0)
CHIME_BELL_1 = (2840.0, 535.0)
CHIME_BELL_2 = (3060.0, 415.0)

# Grand 3-Ring Gothic Rose Window (Exact destination of the 7-Color Prismatic Bridge!)
ROSE_WINDOW_POS = (3480.0, 420.0)

# Cubic Bezier Spine of the 7-Color Sweeping Prismatic Ribbon Bridge:
# Starts at Step 4 (2220, 980) -> sweeps under Giant Bell & Chimes -> enters Rose Window (3480, 420)
RIBBON_P0 = (2220.0, 980.0)
RIBBON_C1 = (2580.0, 880.0)
RIBBON_C2 = (3040.0, 740.0)
RIBBON_P3 = (3480.0, 420.0)


def ribbon_spine_xy(s: float) -> Tuple[float, float, float]:
    """
    Evaluates (x, y, slope_angle) along the 7-Color Prismatic Ribbon Bridge Bezier spine for s in [0, 1].
    """
    u = clamp(s, 0.0, 1.0)
    omt = 1.0 - u
    x = (omt**3)*RIBBON_P0[0] + 3*(omt**2)*u*RIBBON_C1[0] + 3*omt*(u**2)*RIBBON_C2[0] + (u**3)*RIBBON_P3[0]
    y = (omt**3)*RIBBON_P0[1] + 3*(omt**2)*u*RIBBON_C1[1] + 3*omt*(u**2)*RIBBON_C2[1] + (u**3)*RIBBON_P3[1]

    dx = 3*(omt**2)*(RIBBON_C1[0]-RIBBON_P0[0]) + 6*omt*u*(RIBBON_C2[0]-RIBBON_C1[0]) + 3*(u**2)*(RIBBON_P3[0]-RIBBON_C2[0])
    dy = 3*(omt**2)*(RIBBON_C1[1]-RIBBON_P0[1]) + 6*omt*u*(RIBBON_C2[1]-RIBBON_C1[1]) + 3*(u**2)*(RIBBON_P3[1]-RIBBON_C2[1])
    slope = math.atan2(dy, max(1.0, dx))
    return x, y, slope


def foot_y_to_center_y(foot_y: float, squash_y: float, r: float = SLIME_R) -> float:
    """Exact zero-clipping contact formula: anchors bottom of Voronoi slime to foot_y."""
    return foot_y - r * squash_y * 0.96


def run_simulation() -> Tuple[List[Dict[str, Any]], List[Tuple[float, str, float]]]:
    dt = 1.0 / FPS
    frames_state: List[Dict[str, Any]] = []
    audio_events: List[Tuple[float, str, float]] = [
        (0.05, "zoetrope_harden", 0.9),
        (0.80, "land_stone", 0.85),
        (1.85, "rosette_chime_1", 0.85),
        (2.75, "rosette_chime_2", 0.90),
        (3.65, "rosette_chime_3", 0.95),
        (4.15, "question_pop", 0.75),
        (4.75, "idea_ding", 0.90),
        (5.95, "land_pedestal", 0.80),
        (6.60, "prism_strike_1", 0.90),
        (7.35, "prism_strike_2_refract", 1.00),
        (7.80, "steps_crystallize_chord", 0.95),
        (9.05, "step_1_sapphire", 0.85),
        (9.95, "step_2_emerald", 0.88),
        (10.85, "step_3_amber", 0.92),
        (11.75, "step_4_ruby", 0.95),
        (13.50, "bell_rope_chime", 0.92),
        (14.30, "land_step_4", 0.80),
        (14.60, "charge_swell", 0.85),
        (15.65, "giant_bell_toll_blast", 1.00),
        (16.95, "land_step_4", 0.85),
        (17.20, "ribbon_bridge_unfurl", 0.95),
        (18.60, "token_bell_collect", 1.00),
        (20.25, "ribbon_hop_1", 0.85),
        (21.25, "ribbon_hop_2", 0.88),
        (22.25, "ribbon_hop_3", 0.92),
        (23.25, "rose_window_enter", 1.00),
        (23.80, "film_reel_whir", 0.95),
    ]

    # Second-order spring dampers for C^2 continuous motion
    squash_sd = SpringDamper1D(x0=1.0, freq=5.2, zeta=0.62)
    tilt_sd = SpringDamper1D(x0=0.0, freq=4.5, zeta=0.72)
    look_sd = SpringDamper2D(x0=-0.45, y0=0.10, freq=4.2, zeta=0.78)
    cam_sd = SpringDamper2D(x0=680.0, y0=1280.0, freq=1.6, zeta=0.88)
    zoom_sd = SpringDamper1D(x0=1.0, freq=1.5, zeta=0.88)

    # Step depression spring dampers
    step_depress_sd = [SpringDamper1D(x0=0.0, freq=4.8, zeta=0.65) for _ in range(4)]

    prev_sx = 320.0
    roll_angle = 0.0

    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx * dt

        # Default frame parameters
        sx = 320.0
        foot_y = GALLERY_FLOOR_Y
        target_squash = 1.0
        target_tilt = 0.0
        target_look = (0.45, -0.15)
        eye_mode = "pill"
        blink = 0.0
        bubble = None
        grounded = True
        slime_alpha = 1.0

        # Periodic natural blink
        for bt in (1.25, 3.95, 8.20, 12.35, 17.40, 21.60):
            if abs(t - bt) < 0.09:
                blink = math.cos((t - bt) / 0.09 * math.pi * 0.5)

        # Camera targets
        target_cam_x = 680.0
        target_cam_y = 1280.0
        target_zoom = 1.0

        # Environment state
        lancet_lit = [
            smoothstep(1.85, 2.25, t),
            smoothstep(2.75, 3.15, t),
            smoothstep(3.65, 4.05, t),
        ]
        prism_angle_deg = -28.0
        prism_refract_intensity = 0.0
        prism_hit_flash = 0.0

        # Step states (rise & lit after prism refraction at t=7.4s)
        steps_rise_prog = [
            smoothstep(7.45 + i * 0.14, 8.15 + i * 0.14, t) for i in range(4)
        ]
        steps_lit = [
            max(0.25 * steps_rise_prog[i], smoothstep(8.95 + i * 0.90, 9.25 + i * 0.90, t))
            for i in range(4)
        ]
        step_target_depress = [0.0, 0.0, 0.0, 0.0]

        # Bell & shockwave states
        bell_swing_deg = math.sin(t * 1.6) * 1.5
        bell_glow = False
        chime_1_swing = math.sin(t * 2.4) * 2.0
        chime_2_swing = math.cos(t * 2.7) * 2.0
        chimes_glow = False
        rope_end_pt = [2375.0, 910.0]
        rope_active = False
        shockwave_active = False
        shockwave_phase = 0.0
        shockwave_intensity = 0.0

        # Ribbon bridge state
        ribbon_prog = smoothstep(16.80, 19.10, t)

        # World 06 Token (Stained-Glass Mini Chime Bell)
        token_state = {
            "cx": GIANT_BELL_POS[0] - 40.0,
            "cy": GIANT_BELL_POS[1] + 110.0,
            "r": 34.0,
            "rot": t * 2.2,
            "alpha": 0.0,
            "absorbed": t >= 18.65,
        }

        # Guiding Star ✦
        star_x, star_y = 620.0, 1260.0
        star_rot = math.sin(t * 2.5) * 0.18

        # Rose Window Film Reel transition
        rose_rot = t * 0.18
        rose_desat = 0.0
        rose_film_reel = 0.0
        zoetrope_intro = clamp(1.0 - t / 0.85, 0.0, 1.0)

        # =====================================================================
        # ACT 1 (0.0s - 5.2s): 走马灯硬化入场 · 三扇哥特柳叶窗点亮 · 深渊断桥受阻
        # =====================================================================
        if t < 5.2:
            if t < 0.80:
                # Drop onto obsidian gallery floor from Zoetrope transition
                u = t / 0.80
                sx = 320.0
                foot_y = lerp(1260.0, GALLERY_FLOOR_Y, u * u)
                target_squash = 1.24 if u < 0.88 else 0.64
                target_look = (-0.45, 0.25)
                grounded = u >= 0.88
            elif t < 1.35:
                # Landing cushion & 3D head turn sweeping through look_x = 0.0 (facing audience!)
                u = (t - 0.80) / 0.55
                sx = 320.0
                foot_y = GALLERY_FLOOR_Y
                target_squash = 0.68 if u < 0.35 else 1.0
                # Sweep from left (-0.50) -> center audience (0.0) -> right (+0.55)
                target_look = (lerp(-0.50, 0.55, smoothstep(0.0, 1.0, u)), lerp(0.05, -0.25, u))
            elif t < 3.85:
                # 3 rhythmic hops across the 3 Stained-Glass Floor Rosettes (x = 520, 760, 1000)
                hops = [
                    (1.35, 2.15, 320.0, 520.0),
                    (2.15, 3.00, 520.0, 760.0),
                    (3.00, 3.85, 760.0, 1000.0),
                ]
                for t0, t1, x0, x1 in hops:
                    if t <= t1:
                        u = clamp((t - t0) / (t1 - t0), 0.0, 1.0)
                        jres = eval_targeted_jump(u, x0, GALLERY_FLOOR_Y, x1, GALLERY_FLOOR_Y, arc_height=95.0)
                        sx = jres["x"]
                        foot_y = jres["y"]
                        target_squash = jres["squash_y"]
                        target_tilt = jres["tilt"]
                        grounded = (u < 0.20 or u >= 0.86)
                        # Look up at the newly ignited Lancet Window upon landing!
                        if u >= 0.78:
                            target_look = (0.15, -0.55)
                            eye_mode = "pill"
                        else:
                            target_look = (0.55, -0.15)
                        break
            else:
                # 3.85 - 5.20s: Hop to cliff edge (1090), brake at Nave Abyss [?], then spot Crystal Prism [!]
                u_edge = clamp((t - 3.85) / 0.40, 0.0, 1.0)
                sx = lerp(1000.0, CLIFF_EDGE_X, smoothstep(0.0, 1.0, u_edge))
                foot_y = GALLERY_FLOOR_Y
                if t < 4.55:
                    # Pure downward gaze into the dark Nave Abyss (look_x = 0.0 -> symmetrical eyes!)
                    target_look = (0.0, 0.56)
                    target_squash = 0.90
                    target_tilt = 0.10
                    if t >= 4.10:
                        bubble = "question"
                else:
                    # Pure upward gaze then turn toward the Crystal Triangular Prism on the upper ledge [!]
                    u_spot = clamp((t - 4.55) / 0.65, 0.0, 1.0)
                    target_look = (lerp(0.0, 0.42, u_spot), -0.58)
                    target_squash = 0.72 if u_spot > 0.65 else 1.04
                    eye_mode = "surprised" if u_spot < 0.65 else "charge"
                    bubble = "exclamation"

            star_x = lerp(650.0, 1235.0, smoothstep(0.5, 4.8, t))
            star_y = lerp(1320.0, 1120.0, smoothstep(0.5, 4.8, t)) + math.sin(t * 3.5) * 18.0
            target_cam_x = clamp(sx + 220.0, 680.0, 1280.0)
            target_cam_y = lerp(1340.0, 1260.0, smoothstep(1.5, 5.0, t))
            target_zoom = 1.0

        # =====================================================================
        # ACT 2 (5.2s - 12.0s): 撞击硬切面水晶三棱镜折射三色光 · 四级菱形彩窗浮台攀升
        # =====================================================================
        elif t < 12.0:
            if t < 6.10:
                # Leap from gallery cliff (1090, 1620) onto Crystal Prism Pedestal (1135, 1360)
                u = clamp((t - 5.20) / 0.90, 0.0, 1.0)
                jres = eval_targeted_jump(u, CLIFF_EDGE_X, GALLERY_FLOOR_Y, 1135.0, PRISM_PEDESTAL[1], arc_height=115.0)
                sx, foot_y, target_squash, target_tilt = jres["x"], jres["y"], jres["squash_y"], jres["tilt"]
                grounded = (u < 0.20 or u >= 0.86)
                target_look = (0.48, -0.25)
                prism_angle_deg = -28.0
            elif t < 7.80:
                # Two hard-facet body-slam headbutts against the Crystal Triangular Prism (t = 6.60s and t = 7.35s)
                foot_y = PRISM_PEDESTAL[1]
                if t < 6.85:
                    # Strike 1 (6.10 -> 6.85s, impact at 6.60s)
                    u = (t - 6.10) / 0.75
                    if u < 0.35:
                        sx = lerp(1135.0, 1110.0, u / 0.35)
                        target_squash = 0.68
                        eye_mode = "charge"
                    elif u < 0.66:
                        wu = (u - 0.35) / 0.31
                        sx = lerp(1110.0, 1168.0, wu * wu)
                        foot_y = PRISM_PEDESTAL[1] - math.sin(wu * math.pi) * 38.0
                        target_squash = 1.28
                        target_tilt = 0.24
                        eye_mode = "charge"
                    else:
                        ru = (u - 0.66) / 0.34
                        sx = lerp(1168.0, 1130.0, ru)
                        target_squash = 0.78 if ru > 0.7 else 1.0
                        target_tilt = -0.15 * (1.0 - ru)
                    prism_angle_deg = lerp(-28.0, -12.0, smoothstep(6.55, 6.80, t))
                    prism_hit_flash = max(0.0, 1.0 - abs(t - 6.60) / 0.18)
                else:
                    # Strike 2 (6.85 -> 7.80s, full impact at 7.35s -> Total Prismatic Dispersion!)
                    u = (t - 6.85) / 0.95
                    if u < 0.32:
                        sx = lerp(1130.0, 1105.0, u / 0.32)
                        target_squash = 0.58
                        eye_mode = "charge"
                    elif u < 0.53:
                        wu = (u - 0.32) / 0.21
                        sx = lerp(1105.0, 1172.0, wu * wu)
                        foot_y = PRISM_PEDESTAL[1] - math.sin(wu * math.pi) * 48.0
                        target_squash = 1.35
                        target_tilt = 0.28
                        eye_mode = "charge"
                    else:
                        ru = (u - 0.53) / 0.47
                        sx = lerp(1172.0, 1145.0, smoothstep(0.0, 1.0, ru))
                        target_squash = 0.74 if (0.3 < ru < 0.6) else 1.02
                        eye_mode = "happy"
                    prism_angle_deg = lerp(-12.0, 0.0, smoothstep(7.30, 7.55, t))
                    prism_hit_flash = max(0.0, 1.0 - abs(t - 7.35) / 0.22)

                prism_refract_intensity = smoothstep(7.32, 7.75, t)
                target_look = (0.55, 0.05)
                target_cam_x = lerp(1280.0, 1520.0, smoothstep(6.0, 7.8, t))
                target_cam_y = lerp(1260.0, 1180.0, smoothstep(6.0, 7.8, t))
                target_zoom = 1.02
            else:
                # 7.80 - 12.0s: Hop up the 4 newly crystallized Beveled Gothic Diamond Stained-Glass Steps!
                prism_angle_deg = 0.0
                prism_refract_intensity = 1.0
                if t < 8.35:
                    # Brief admiring pause on pedestal as the 4 diamond steps rise & ignite
                    sx = 1145.0
                    foot_y = PRISM_PEDESTAL[1]
                    target_squash = 0.72 if t > 8.10 else 1.04
                    # Sweep gaze across the rising steps
                    target_look = (0.58, -0.18)
                    eye_mode = "happy"
                else:
                    step_jumps = [
                        (8.35,  9.25, (1145.0, PRISM_PEDESTAL[1]), (STEP_COORDS[0][0], STEP_COORDS[0][1]), 0),
                        (9.25, 10.15, (STEP_COORDS[0][0], STEP_COORDS[0][1]), (STEP_COORDS[1][0], STEP_COORDS[1][1]), 1),
                        (10.15, 11.05, (STEP_COORDS[1][0], STEP_COORDS[1][1]), (STEP_COORDS[2][0], STEP_COORDS[2][1]), 2),
                        (11.05, 12.00, (STEP_COORDS[2][0], STEP_COORDS[2][1]), (STEP_COORDS[3][0], STEP_COORDS[3][1]), 3),
                    ]
                    for t0, t1, (x0, y0), (x1, y1), s_idx in step_jumps:
                        if t <= t1:
                            u = clamp((t - t0) / (t1 - t0), 0.0, 1.0)
                            jres = eval_targeted_jump(u, x0, y0, x1, y1, arc_height=105.0)
                            sx, foot_y, target_squash, target_tilt = jres["x"], jres["y"], jres["squash_y"], jres["tilt"]
                            grounded = (u < 0.20 or u >= 0.86)
                            if u < 0.20 and s_idx > 0:
                                step_target_depress[s_idx - 1] = 10.0
                                foot_y += 8.0
                            elif u >= 0.86:
                                step_target_depress[s_idx] = 12.0
                                foot_y += 10.0
                            target_look = (0.52, -0.32 if u < 0.75 else 0.0)
                            eye_mode = "pill"
                            break

                target_cam_x = clamp(sx + 180.0, 1520.0, 2360.0)
                target_cam_y = clamp(foot_y - 120.0, 820.0, 1180.0)
                target_zoom = 1.0

            star_x = lerp(1470.0, 2380.0, smoothstep(6.5, 11.8, t))
            star_y = lerp(1200.0, 740.0, smoothstep(6.5, 11.8, t)) + math.sin(t * 4.0) * 16.0

        # =====================================================================
        # ACT 3 (12.0s - 19.4s): 高坛拉绳初鸣 · 深度蓄力头槌撞响硬切面琉璃大钟 · 吸收信物
        # =====================================================================
        elif t < 19.4:
            prism_angle_deg = 0.0
            prism_refract_intensity = 1.0
            step4_x, step4_y = STEP_COORDS[3][0], STEP_COORDS[3][1]

            if t < 12.75:
                # Stand on Step 4 (2220, 980), turn through look_x = 0.0 (symmetrical eyes!) to look up at Giant Bell
                u = (t - 12.0) / 0.75
                sx = step4_x
                foot_y = step4_y
                step_target_depress[3] = 6.0
                target_squash = 0.94 + 0.06 * math.sin(u * math.pi)
                # Sweep through 0.0 (symmetrical facing audience) -> (+0.48, -0.52) looking up at Giant Bell
                if u < 0.45:
                    target_look = (0.0, -0.45)  # Pure upward look -> equal eye sizes!
                else:
                    target_look = (lerp(0.0, 0.50, (u - 0.45) / 0.55), -0.52)
            elif t < 14.45:
                # First Leap: Jump to grab/pull the Golden Glass Bell Rope at (2375, 835) (t = 13.50s)
                u = (t - 12.75) / 1.70
                if u < 0.16:
                    sx, foot_y = step4_x, step4_y
                    target_squash = 0.68
                    step_target_depress[3] = 11.0
                    target_look = (0.48, -0.48)
                    eye_mode = "charge"
                elif u < 0.46:
                    # Ascend to rope grab point (2375, 835)
                    fu = (u - 0.16) / 0.30
                    sx = lerp(step4_x, ROPE_GRAB_PT[0], fu)
                    foot_y = lerp(step4_y, ROPE_GRAB_PT[1], 1.0 - (1.0 - fu) ** 2)
                    target_squash = 1.24
                    target_tilt = 0.20
                    grounded = False
                    target_look = (0.35, -0.45)
                elif u < 0.60:
                    # Hang & yank the golden rope downward! (> < effort)
                    pu = (u - 0.46) / 0.14
                    sx = ROPE_GRAB_PT[0]
                    foot_y = ROPE_GRAB_PT[1] + math.sin(pu * math.pi) * 28.0
                    target_squash = 0.82
                    grounded = False
                    rope_active = True
                    rope_end_pt = [sx, foot_y - SLIME_R * 0.3]
                    eye_mode = "charge"
                    target_look = (0.25, -0.55)
                else:
                    # Parabolic rebound back to Step 4 (2220, 980)
                    du = (u - 0.60) / 0.40
                    sx = lerp(ROPE_GRAB_PT[0], step4_x, du)
                    foot_y = lerp(ROPE_GRAB_PT[1] + 15.0, step4_y, du * du)
                    target_squash = 0.68 if du > 0.85 else 1.12
                    target_tilt = -0.18 * (1.0 - du)
                    grounded = du > 0.85
                    if grounded:
                        step_target_depress[3] = 12.0
                    target_look = (0.45, -0.42)

                # Preliminary bell swing from rope pull (+16 deg)
                if t >= 13.45:
                    dt_r = t - 13.45
                    bell_swing_deg = math.exp(-dt_r * 2.2) * math.sin(dt_r * 7.5) * 16.0
                    bell_glow = True
            elif t < 17.10:
                # Second Leap: Deep-squash charge on Step 4 -> Full-power Headbutt on Giant Bell lower-left lip (t = 15.65s)!
                if t < 15.10:
                    # Deep squash charge (sy = 0.52) on Step 4 (> < effort)
                    cu = (t - 14.45) / 0.65
                    sx = step4_x
                    foot_y = step4_y + 12.0 * math.sin(cu * math.pi * 0.5)
                    step_target_depress[3] = 16.0 * math.sin(cu * math.pi * 0.5)
                    target_squash = lerp(0.95, 0.52, smoothstep(0.0, 1.0, cu))
                    eye_mode = "charge"
                    # Pure focus on bell lip
                    target_look = (0.45, -0.58)
                elif t < 15.65:
                    # Rocket launch to Giant Bell lower-left lip (2348, 728)!
                    # Slime center at impact = (2325, 760), crown tangent to (2348, 728), foot_y = 760 + 68*0.96 = 825
                    lu = (t - 15.10) / 0.55
                    sx = lerp(step4_x, 2328.0, lu)
                    foot_y = lerp(step4_y, 822.0, 1.0 - (1.0 - lu) ** 2.2)
                    target_squash = 1.38
                    target_tilt = 0.28
                    grounded = False
                    eye_mode = "charge" if lu > 0.80 else "pill"
                    target_look = (0.35, -0.55)
                else:
                    # True gravity parabolic rebound from Bell Lip back to Step 4 (15.65 -> 17.10s)
                    du = (t - 15.65) / 1.45
                    sx = lerp(2328.0, step4_x, du)
                    # Slight upward arc after impact before gravity drop onto Step 4
                    foot_y = lerp(822.0, step4_y, du * du) - 45.0 * math.sin(du * math.pi)
                    target_squash = 0.64 if du > 0.86 else (1.0 + 0.24 * math.sin(du * math.pi))
                    target_tilt = -0.24 * (1.0 - du)
                    grounded = du > 0.86
                    if grounded:
                        foot_y = step4_y + 10.0
                        step_target_depress[3] = 14.0
                    eye_mode = "charge" if du < 0.16 else ("happy" if grounded else "pill")
                    target_look = (0.0, -0.25)
            else:
                # 17.10 - 19.40s: On Step 4 watching 7-Color Prismatic Bridge unfurl & hopping to absorb Mini Bell Token (18.60s)
                sx = step4_x
                foot_y = step4_y
                step_target_depress[3] = 5.0
                target_squash = 1.0

                # Token descends along a graceful arc from Giant Bell (2440, 730) to Step 4 (2220, 855)
                tu = clamp((t - 16.60) / 1.95, 0.0, 1.0)
                token_state["alpha"] = smoothstep(16.60, 17.00, t) * (1.0 if t < 18.65 else 0.0)
                token_state["cx"] = lerp(2440.0, step4_x, smoothstep(0.0, 1.0, tu))
                token_state["cy"] = lerp(730.0, step4_y - 125.0, tu) - math.sin(tu * math.pi) * 55.0

                # Hop on Step 4 to absorb the token (18.25 -> 18.95s, peak at 18.60s)
                if 18.25 <= t <= 18.95:
                    hu = (t - 18.25) / 0.70
                    foot_y = step4_y - math.sin(hu * math.pi) * 85.0
                    target_squash = 1.20 if 0.2 < hu < 0.8 else 0.74
                    grounded = False

                if t >= 18.55:
                    eye_mode = "star"
                    # Face audience symmetrically (look_x = 0.0 -> both star/pill eyes 100% equal!)
                    target_look = (0.0, 0.0)
                else:
                    target_look = (0.35, -0.35)

            # Continuous Bell Harmonic Swing, Twin Chimes & 7 Concentric Shockwave Rings for t >= 15.65s
            if t >= 15.65:
                dt_b = t - 15.65
                bell_swing_deg = math.exp(-dt_b * 0.75) * math.cos(dt_b * 6.8) * -28.0
                bell_glow = True
                chime_1_swing = math.exp(-dt_b * 0.55) * math.sin(dt_b * 9.5) * 22.0
                chime_2_swing = -math.exp(-dt_b * 0.55) * math.sin(dt_b * 10.5) * 24.0
                chimes_glow = True
                shockwave_active = True
                shockwave_phase = dt_b * 2.2
                shockwave_intensity = clamp(math.exp(-dt_b * 0.35) * 1.15, 0.0, 1.0)
                rope_end_pt = [
                    2375.0 + math.sin(dt_b * 6.8) * 45.0 * math.exp(-dt_b * 0.8),
                    910.0 - abs(math.cos(dt_b * 6.8)) * 25.0 * math.exp(-dt_b * 0.8),
                ]

            star_x = lerp(2380.0, 2620.0, smoothstep(12.0, 19.0, t))
            star_y = lerp(740.0, 720.0, smoothstep(12.0, 19.0, t)) + math.sin(t * 3.8) * 16.0
            target_cam_x = lerp(2420.0, 2560.0, smoothstep(12.0, 19.0, t))
            target_cam_y = lerp(800.0, 730.0, smoothstep(12.0, 19.0, t))
            target_zoom = 0.96

        # =====================================================================
        # ACT 4 (19.4s - 26.0s): 七彩流光彩带天桥四连跳冲刺 · 跃入三环玫瑰花窗胶片转场
        # =====================================================================
        else:
            prism_angle_deg = 0.0
            prism_refract_intensity = 1.0
            ribbon_prog = 1.0
            dt_b = t - 15.65
            bell_swing_deg = math.exp(-dt_b * 0.75) * math.cos(dt_b * 6.8) * -28.0
            bell_glow = True
            chimes_glow = True
            shockwave_active = t < 22.5
            shockwave_phase = dt_b * 2.2
            shockwave_intensity = clamp(math.exp(-dt_b * 0.38), 0.0, 1.0)

            if t < 23.40:
                # 4 grand rhythmic hops along the 7-Color Prismatic Ribbon Bridge Bezier spine (s: 0 -> 0.25 -> 0.50 -> 0.75 -> 1.0)
                bridge_hops = [
                    (19.40, 20.40, 0.00, 0.25),
                    (20.40, 21.40, 0.25, 0.50),
                    (21.40, 22.40, 0.50, 0.75),
                    (22.40, 23.40, 0.75, 1.00),
                ]
                for t0, t1, s0, s1 in bridge_hops:
                    if t <= t1:
                        u = clamp((t - t0) / (t1 - t0), 0.0, 1.0)
                        if u < 0.16:
                            # Brief elastic crouch on the rainbow ribbon bridge
                            cu = u / 0.16
                            bx, by, bslope = ribbon_spine_xy(s0)
                            sx = bx
                            foot_y = by + 12.0 * math.sin(cu * math.pi)
                            target_squash = 0.68
                            target_tilt = bslope * 0.5
                            grounded = True
                            target_look = (0.55, -0.35)
                        elif u < 0.86:
                            # Soaring parabolic arc along the rainbow bridge
                            fu = (u - 0.16) / 0.70
                            cur_s = lerp(s0, s1, fu)
                            bx, by, bslope = ribbon_spine_xy(cur_s)
                            sx = bx
                            foot_y = by - 4.0 * 115.0 * fu * (1.0 - fu)
                            target_squash = 1.0 + 0.30 * math.sin(fu * math.pi)
                            target_tilt = bslope + 0.22 * math.cos(fu * math.pi)
                            grounded = False
                            eye_mode = "pill"
                            target_look = (0.52, lerp(-0.42, 0.15, fu))
                        else:
                            # Elastic landing cushion on the rainbow bridge node
                            lu = (u - 0.86) / 0.14
                            bx, by, bslope = ribbon_spine_xy(s1)
                            sx = bx
                            foot_y = by + 14.0 * math.sin(lu * math.pi)
                            target_squash = 0.66 + 0.34 * lu
                            target_tilt = bslope * 0.5
                            grounded = True
                            eye_mode = "pill"
                            target_look = (0.48, -0.32)
                        break

                star_s = clamp((t - 19.40) / 3.60 + 0.18, 0.0, 1.0)
                star_x, star_y, _ = ribbon_spine_xy(star_s)
                star_y -= 75.0
                target_cam_x = clamp(sx + 160.0, 2560.0, ROSE_WINDOW_POS[0])
                target_cam_y = clamp(foot_y - 90.0, ROSE_WINDOW_POS[1], 730.0)
                target_zoom = lerp(0.96, 1.06, (t - 19.40) / 4.0)
            else:
                # 23.40 - 26.00s: Dive into the solar center of the Grand 3-Ring Gothic Rose Window (3480, 420)!
                # Camera centers squarely on (3480, 420) as Rose Window spins & morphs into 1930s Film Reel (3-2-1)
                end_u = clamp((t - 23.40) / 2.60, 0.0, 1.0)
                sx = ROSE_WINDOW_POS[0]
                foot_y = ROSE_WINDOW_POS[1] + SLIME_R * 0.96
                target_squash = 1.0
                target_tilt = 0.0
                eye_mode = "star"
                target_look = (0.0, 0.0)
                slime_alpha = clamp(1.0 - end_u * 2.2, 0.0, 1.0)
                star_x, star_y = ROSE_WINDOW_POS[0], ROSE_WINDOW_POS[1]

                rose_rot = 23.40 * 0.18 + (t - 23.40) * (2.5 + end_u * 9.5)
                rose_desat = smoothstep(0.10, 0.70, end_u)
                rose_film_reel = smoothstep(0.20, 0.85, end_u)

                target_cam_x = ROSE_WINDOW_POS[0]
                target_cam_y = ROSE_WINDOW_POS[1]
                target_zoom = lerp(1.06, 1.22, smoothstep(0.0, 1.0, end_u))

        # Step the second-order spring dampers
        actual_squash = clamp(squash_sd.step(target_squash, dt), 0.50, 1.48)
        actual_tilt = clamp(tilt_sd.step(target_tilt, dt), -0.48, 0.48)
        lx, ly = look_sd.step(target_look[0], target_look[1], dt)
        cam_x, cam_y = cam_sd.step(target_cam_x, target_cam_y, dt)
        cam_zoom = zoom_sd.step(target_zoom, dt)

        # Accumulate true 3D Voronoi facet roll angle from horizontal velocity
        dx = sx - prev_sx
        prev_sx = sx
        roll_angle += dx / SLIME_R

        # Exact zero-clipping center Y from foot_y and actual_squash
        cy = foot_y_to_center_y(foot_y, actual_squash, SLIME_R)

        # Step the 4 diamond step spring dampers
        steps_state = []
        for i, (st_x, st_y, st_w, st_h, col_main, col_acc) in enumerate(STEP_COORDS):
            dep = step_depress_sd[i].step(step_target_depress[i], dt)
            rise_offset = (1.0 - steps_rise_prog[i]) * 260.0
            steps_state.append({
                "x": st_x,
                "y": st_y + rise_offset + dep,
                "w": st_w,
                "h": st_h,
                "color": col_main,
                "accent": col_acc,
                "lit": steps_lit[i],
                "rise_prog": steps_rise_prog[i],
            })

        frames_state.append({
            "frame": frame_idx,
            "t": t,
            "camera": {
                "cx": cam_x,
                "cy": cam_y,
                "zoom": cam_zoom,
            },
            "zoetrope_intro": zoetrope_intro,
            "lancet_lit": lancet_lit,
            "prism": {
                "cx": PRISM_CENTER[0],
                "cy": PRISM_CENTER[1],
                "pedestal_x": PRISM_PEDESTAL[0],
                "pedestal_y": PRISM_PEDESTAL[1],
                "angle_deg": prism_angle_deg,
                "refract_intensity": prism_refract_intensity,
                "hit_flash": prism_hit_flash,
            },
            "steps": steps_state,
            "bell": {
                "cx": GIANT_BELL_POS[0],
                "cy": GIANT_BELL_POS[1],
                "scale": 1.18,
                "swing_deg": bell_swing_deg,
                "resonant_glow": bell_glow,
            },
            "chimes": [
                {"cx": CHIME_BELL_1[0], "cy": CHIME_BELL_1[1], "scale": 0.56, "swing_deg": chime_1_swing, "resonant_glow": chimes_glow},
                {"cx": CHIME_BELL_2[0], "cy": CHIME_BELL_2[1], "scale": 0.46, "swing_deg": chime_2_swing, "resonant_glow": chimes_glow},
            ],
            "rope": {
                "start": (GIANT_BELL_POS[0] - 18.0, GIANT_BELL_POS[1] + 115.0),
                "end": tuple(rope_end_pt),
                "active": rope_active,
            },
            "shockwave": {
                "active": shockwave_active,
                "cx": BELL_STRIKE_LIP[0],
                "cy": BELL_STRIKE_LIP[1],
                "phase": shockwave_phase,
                "intensity": shockwave_intensity,
            },
            "ribbon_bridge": {
                "progress": ribbon_prog,
                "shimmer_phase": t * 3.2,
                "slime_x": sx if 19.4 <= t <= 23.4 else -9999.0,
                "slime_foot_y": foot_y if 19.4 <= t <= 23.4 else -9999.0,
                "slime_grounded": grounded and (19.4 <= t <= 23.4),
            },
            "token": token_state,
            "star": {
                "cx": star_x,
                "cy": star_y,
                "r": 38.0,
                "rot": star_rot,
                "visible": t < 23.6,
            },
            "slime": {
                "cx": sx,
                "cy": cy,
                "foot_y": foot_y,
                "radius": SLIME_R,
                "squash_y": actual_squash,
                "tilt": actual_tilt,
                "look": (lx, ly),
                "eye_mode": eye_mode,
                "blink": blink,
                "roll_angle": roll_angle,
                "grounded": grounded,
                "alpha": slime_alpha,
                "visible": slime_alpha > 0.01,
                "bubble": bubble,
            },
            "rose_window": {
                "cx": ROSE_WINDOW_POS[0],
                "cy": ROSE_WINDOW_POS[1],
                "rot": rose_rot,
                "desaturate": rose_desat,
                "film_reel": rose_film_reel,
            },
        })

    return frames_state, audio_events


if __name__ == "__main__":
    states, events = run_simulation()
    print(f"[Sim 06] Generated {len(states)} frames and {len(events)} audio events.")
