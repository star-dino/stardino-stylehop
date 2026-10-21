# -*- coding: utf-8 -*-
"""
World 01 · 矩阵终端序章 (sim_01_crt.py)
Fixed-step physics & 6-act state machine simulator (30fps, 26.0s = 780 frames).
Outputs frames_state[] and frame-accurate audio_events[].

Key Improvements:
- Continuous C^2 spring-damper dynamics (SpringDamper1D, SpringDamper2D) for squash, tilt, gaze (look_x, look_y), and camera.
- Full-screen CRT turn-on white beam & phosphor flash that expands to 100% of the screen before smoothly fading out.
- Non-overlapping layout between [--overclock] hotkey (x=650) and ERR_403 firewall (x=920).
- Seamless C^1 continuous rebound from ERR_404's head (2160, 295) directly onto the zipline cursor (2400, 306) with zero stall.
- Seamless jump from zipline -> floor (3460, 860) -> Giant Enter Key top (3680, 740) while absorbing the [ ↵ ] token.
- Complete 952-block 16-Bit Green Warp Portal assembly (x=4020, y=632..860) followed by Slime leaping into the pipe mouth and diving inside!
"""

import math
import random
from typing import Dict, Any, List, Tuple

import os
import sys
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from slime_engine import SpringDamper1D, SpringDamper2D

FPS = 30
DURATION = 26.0
TOTAL_FRAMES = int(round(DURATION * FPS))  # 780 frames
DT = 1.0 / FPS

def smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / max(1e-6, edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def run_simulation() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Runs full 26.0s 6-act physics and state simulation."""
    frames_state: List[Dict[str, Any]] = []
    audio_events: List[Dict[str, Any]] = []

    # Map geometry landmarks
    FLOOR_Y = 860.0
    SLIME_R = 66.0  # Base radius (~132px diameter, ~10% screen height)
    CONTACT_K = 0.956  # Analytical bottom contact cushion factor

    # Non-overlapping coordinates for Beat 1-3
    SLEEP_X = 185.0
    KEY1_X = 330.0
    KEY2_X = 490.0
    KEY3_X = 650.0
    KEY_TOP_Y = 826.0
    FIREWALL_X = 920.0  # w=250 -> spans 795..1045 (77px clear of KEY3 right edge 718!)

    # Staircase & ERR_404 coordinates for Beat 4
    STEP1_X, STEP1_Y = 1185.0, 625.0
    STEP2_X, STEP2_Y = 1520.0, 535.0
    STEP3_X, STEP3_Y = 1850.0, 445.0
    STEP4_X, STEP4_Y = 2200.0, 365.0
    ERR404_X, ERR404_Y = 2160.0, 365.0
    ERR404_HEAD_Y = 295.0

    # Zipline & Final Platform coordinates for Beat 5-6
    ZIP_X0, ZIP_Y0 = 2400.0, 320.0
    ZIP_X1, ZIP_Y1 = 3400.0, 380.0
    ENTER_X = 3680.0
    ENTER_TOP_Y = 740.0
    PIPE_X = 4020.0
    PIPE_TOP_Y = 632.0
    PIPE_BOTTOM_Y = FLOOR_Y  # 860.0 (height = 228 = 38 * 6)

    def contact_y(surface_y: float, sy: float) -> float:
        return surface_y - SLIME_R * sy * CONTACT_K

    def eval_foot_jump(u: float, x0: float, surf_y0: float, x1: float, surf_y1: float, arc_height: float) -> Dict[str, float]:
        u = max(0.0, min(1.0, u))
        direction = 1.0 if x1 >= x0 else -1.0
        if u < 0.16:
            c = u / 0.16
            x = x0
            foot_y = surf_y0
            squash_y = 1.0 - 0.36 * math.sin(c * math.pi * 0.5)
            tilt = direction * c * 0.15
        elif u < 0.88:
            air = (u - 0.16) / 0.72
            s_air = air * air * (3.0 - 2.0 * air)
            x = x0 + (x1 - x0) * lerp(air, s_air, 0.5)
            foot_y = lerp(surf_y0, surf_y1, air) - 4.0 * arc_height * air * (1.0 - air)
            vy = math.cos(air * math.pi)
            squash_y = 0.94 + abs(vy) * 0.28
            tilt = -direction * vy * 0.18
        else:
            land = (u - 0.88) / 0.12
            x = x1
            foot_y = surf_y1
            squash_y = 1.0 - 0.32 * math.sin(land * math.pi)
            tilt = direction * (1.0 - land) * 0.08
        return {"x": x, "foot_y": foot_y, "squash_y": squash_y, "tilt": tilt}

    # Pre-generate ERR_404 shard initial velocities
    rnd = random.Random(404)
    shards_init = []
    shard_chars = ["E", "R", "R", "_", "4", "0", "4"]
    for i, ch in enumerate(shard_chars):
        ang = rnd.uniform(-math.pi * 0.88, -math.pi * 0.12)
        spd = rnd.uniform(340.0, 700.0)
        shards_init.append({
            "char": ch,
            "x0": ERR404_X + rnd.uniform(-18, 18),
            "y0": ERR404_HEAD_Y + 30.0 + rnd.uniform(-15, 15),
            "vx": math.cos(ang) * spd,
            "vy": math.sin(ang) * spd,
            "rot0": rnd.uniform(-0.5, 0.5),
            "vrot": rnd.uniform(-7.0, 7.0),
        })

    # Pre-generate complete 16-Bit Green Warp Portal (28x38 grid of 6x6 pixel blocks = 952 blocks)
    rnd_p = random.Random(2026)
    particles_init = []
    pipe_w_cells, pipe_h_cells = 28, 38
    rim_h_cells = 10
    cell_px = 6.0

    for gy in range(pipe_h_cells):
        is_rim = (gy < rim_h_cells)
        gx_start = 0 if is_rim else 2
        gx_end = pipe_w_cells if is_rim else (pipe_w_cells - 2)
        span_w = float(gx_end - gx_start - 1)

        for gx in range(gx_start, gx_end):
            rel_x = (gx - gx_start) / max(1.0, span_w)
            if gy == 0 or (is_rim and gy == rim_h_cells - 1) or gx == gx_start or gx == gx_end - 1:
                c_type = "border"
            elif (is_rim and gy == 1) or rel_x < 0.14:
                c_type = "peak"
            elif rel_x < 0.55:
                c_type = "bright"
            elif rel_x < 0.84:
                c_type = "mid"
            else:
                c_type = "dim"

            tx = PIPE_X - (pipe_w_cells * cell_px) * 0.5 + gx * cell_px + cell_px * 0.5
            ty = PIPE_TOP_Y + gy * cell_px + cell_px * 0.5

            # Explosive burst velocity from Giant Enter Key (3680, 780)
            ang = rnd_p.uniform(-math.pi * 0.92, math.pi * 0.25)
            spd = rnd_p.uniform(220.0, 880.0)
            # Bottom rows assemble slightly earlier than top rows
            height_frac = 1.0 - (gy / float(pipe_h_cells - 1))
            delay = height_frac * 0.22 + rnd_p.uniform(0.0, 0.08)

            particles_init.append({
                "x0": ENTER_X + rnd_p.uniform(-90.0, 90.0),
                "y0": ENTER_TOP_Y + 45.0 + rnd_p.uniform(-25.0, 25.0),
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd - 240.0,
                "tx": tx,
                "ty": ty,
                "delay": delay,
                "color_type": c_type,
            })

    # Continuous 2nd-order Spring-Damper filters
    squash_sd = SpringDamper1D(1.0, 0.0, freq=9.5, zeta=0.68)
    tilt_sd = SpringDamper1D(0.0, 0.0, freq=7.5, zeta=0.72)
    look_sd = SpringDamper2D(0.0, 0.0, freq=5.5, zeta=0.76)
    cam_x_sd = SpringDamper1D(640.0, 0.0, freq=3.2, zeta=0.82)
    cam_y_sd = SpringDamper1D(540.0, 0.0, freq=3.2, zeta=0.82)

    # Simulation loop
    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx * DT

        # -------------------------------------------------------------
        # 1. CRT Power-on beam & full-screen white flash (0.0 ~ 1.05s)
        # -------------------------------------------------------------
        if t < 0.18:
            crt_open_x = smoothstep(0.01, 0.18, t)
            crt_open_y = 0.008
            crt_flash_alpha = 1.0
        elif t < 0.65:
            crt_open_x = 1.0
            crt_open_y = 0.008 + 0.992 * smoothstep(0.18, 0.62, t)
            crt_flash_alpha = 1.0 - 0.15 * smoothstep(0.50, 0.65, t)
        elif t < 1.05:
            crt_open_x = 1.0
            crt_open_y = 1.0
            crt_flash_alpha = 0.85 * (1.0 - smoothstep(0.65, 1.05, t))
        else:
            crt_open_x = 1.0
            crt_open_y = 1.0
            crt_flash_alpha = 0.0

        if frame_idx == int(0.05 * FPS):
            audio_events.append({"name": "crt_turn_on", "frame": frame_idx, "time": t})

        # -------------------------------------------------------------
        # 2. State Machine: Targets for Physics & Acting
        # -------------------------------------------------------------
        target_squash_y = 1.0
        target_tilt = 0.0
        target_look_x = 0.0
        target_look_y = 0.0
        target_cam_x = 640.0
        target_cam_y = 540.0

        slime_x = SLEEP_X
        foot_y = FLOOR_Y
        slime_y = contact_y(FLOOR_Y, 1.0)
        slime_visible = True
        slime_pipe_clip_y = None  # World Y below which Slime is inside the green pipe
        eye_mode = "pill"
        blink = 0.0
        is_awake = False
        color_blend = 0.0
        bubble = None
        bubble_alpha = 0.0

        star_visible = False
        star_x, star_y, star_r = 1500.0, 100.0, 36.0
        star_rot = t * 1.5

        token_active = False
        token_x, token_y, token_rot = ENTER_X, 665.0, t * 2.0
        token_alpha = 1.0

        firewall_h = 0.0
        firewall_state = "dormant"
        firewall_shake = 0.0

        key1_press = 0.0
        key2_press = 0.0
        key3_press = 0.0
        typed_cmd = ""
        prog_pct = 0.0

        stair_rise = 0.0
        err404_alive = True
        err404_x, err404_y = ERR404_X, ERR404_Y
        zipline_active = True
        cursor_x, cursor_y = ZIP_X0, ZIP_Y0
        enter_press = 0.0
        pipe_progress = 0.0

        # =============================================================
        # BEAT 1: 0.0 ~ 4.0s (Dormant -> Awakening -> 3D Gaze Acting)
        # =============================================================
        if t < 2.8:
            is_awake = False
            color_blend = 0.0
            eye_mode = "sleep"
            slime_x = SLEEP_X
            target_squash_y = 1.0 + 0.035 * math.sin(t * math.pi * 1.4)
            target_look_x = 0.0
            target_look_y = 0.0
            target_cam_x = 640.0

        elif t < 3.4:
            # Star descending to hit Slime head
            star_visible = True
            is_awake = False
            color_blend = 0.0
            eye_mode = "sleep"
            u_star = (t - 2.8) / 0.6
            star_x = lerp(1250.0, SLEEP_X, smoothstep(0.0, 1.0, u_star))
            star_y = lerp(100.0, FLOOR_Y - SLIME_R * 2.0 - 15.0, smoothstep(0.0, 1.0, u_star))

            if frame_idx == int(2.8 * FPS):
                audio_events.append({"name": "star_descend", "frame": frame_idx, "time": t})

            slime_x = SLEEP_X
            target_squash_y = 1.0 + 0.035 * math.sin(t * math.pi * 1.4)
            target_look_x = 0.0
            target_look_y = 0.0
            target_cam_x = 640.0

        elif t < 4.0:
            # Star strikes at 3.4s! Aurora flows into Slime
            star_visible = True
            star_x = (SLEEP_X + 110.0) + 12.0 * math.sin(t * 3.5)
            star_y = 660.0 + 10.0 * math.cos(t * 2.5)

            if frame_idx == int(3.4 * FPS):
                audio_events.append({"name": "star_strike", "frame": frame_idx, "time": t})
            if frame_idx == int(3.6 * FPS):
                audio_events.append({"name": "wake_pop", "frame": frame_idx, "time": t})

            is_awake = True
            color_blend = smoothstep(3.4, 3.9, t)
            slime_x = SLEEP_X

            if t < 3.65:
                target_squash_y = 0.62
                eye_mode = "wince"
                target_look_x = 0.0
                target_look_y = 0.0
            elif t < 3.76:
                target_squash_y = 1.05
                eye_mode = "pill"
                target_look_x = -0.55
                target_look_y = 0.0
            elif t < 3.86:
                target_squash_y = 1.02
                eye_mode = "pill"
                target_look_x = 0.0
                target_look_y = -0.10
            else:
                target_squash_y = 1.0
                eye_mode = "pill"
                target_look_x = +0.55
                target_look_y = -0.38

            target_cam_x = 640.0

        # =============================================================
        # BEAT 2: 4.0 ~ 8.5s (Chase -> Firewall Bonk -> Look Up -> Look Down)
        # =============================================================
        elif t < 8.5:
            is_awake = True
            color_blend = 1.0
            star_visible = True

            # Star moves right ahead of slime past the firewall
            u_st = smoothstep(4.0, 6.0, t)
            star_x = lerp(SLEEP_X + 110.0, 1080.0, u_st) + 12.0 * math.sin(t * 3.5)
            star_y = lerp(660.0, 580.0, u_st) + 10.0 * math.cos(t * 2.8)

            # Firewall pops up at 5.5s at x=920 (left face at x=795)
            if t < 5.5:
                firewall_h = 0.0
                firewall_state = "dormant"
            elif t < 5.95:
                firewall_state = "alarm"
                firewall_h = smoothstep(5.5, 5.95, t) * 230.0
                if frame_idx == int(5.5 * FPS):
                    audio_events.append({"name": "firewall_alarm", "frame": frame_idx, "time": t})
            else:
                firewall_state = "alarm"
                firewall_h = 230.0

            # Hop 1 (4.2 ~ 5.25s: SLEEP_X 185 -> 490 on KEY2 top)
            if t < 4.2:
                slime_x = SLEEP_X
                foot_y = FLOOR_Y
                target_squash_y = 1.0
                target_look_x = +0.75
                target_look_y = -0.15
                eye_mode = "pill"
                target_cam_x = 640.0
            elif t < 5.25:
                u_h1 = (t - 4.2) / 1.05
                fj = eval_foot_jump(u_h1, SLEEP_X, FLOOR_Y, 520.0, FLOOR_Y, arc_height=135.0)
                slime_x = fj["x"]
                foot_y = fj["foot_y"]
                target_squash_y = fj["squash_y"]
                target_tilt = fj["tilt"]
                if frame_idx == int(4.38 * FPS):
                    audio_events.append({"name": "slime_hop", "frame": frame_idx, "time": t})
                target_look_x = +0.85
                target_look_y = -0.15
                eye_mode = "pill"
                target_cam_x = lerp(640.0, 780.0, u_h1)
            # Hop 2 towards firewall left face (5.25 ~ 6.30s: 520 -> 790)
            elif t < 6.30:
                u_h2 = (t - 5.25) / 1.05
                fj = eval_foot_jump(u_h2, 520.0, FLOOR_Y, 790.0, FLOOR_Y, arc_height=140.0)
                slime_x = fj["x"]
                foot_y = fj["foot_y"]
                target_squash_y = fj["squash_y"]
                target_tilt = fj["tilt"]
                if frame_idx == int(5.42 * FPS):
                    audio_events.append({"name": "slime_hop", "frame": frame_idx, "time": t})
                target_look_x = +0.95
                target_look_y = 0.0
                eye_mode = "pill"
                target_cam_x = lerp(780.0, 880.0, u_h2)
            elif t < 6.65:
                # BONK! Hits firewall left edge (795) and rebounds to 745 (between KEY3 and Firewall)
                if frame_idx == int(6.3 * FPS):
                    audio_events.append({"name": "wall_bonk", "frame": frame_idx, "time": t})
                u_b = (t - 6.3) / 0.35
                slime_x = lerp(790.0, 745.0, smoothstep(0.0, 1.0, u_b))
                foot_y = FLOOR_Y
                target_squash_y = lerp(0.52, 0.88, u_b)
                target_tilt = -0.22 * (1.0 - u_b)
                eye_mode = "wince"
                target_look_x = 0.0
                target_look_y = 0.0
                firewall_shake = 12.0 * math.sin(u_b * math.pi * 6.0) * (1.0 - u_b)
                target_cam_x = 880.0
            elif t < 7.5:
                # Dazed -> Look UP at wall top! Pops [?]
                slime_x = 745.0
                foot_y = FLOOR_Y
                target_squash_y = 1.0 + 0.03 * math.sin(t * 6.0)
                target_tilt = 0.0
                eye_mode = "pill"
                target_look_x = 0.0
                target_look_y = -0.52
                bubble = "[?]"
                bubble_alpha = smoothstep(6.8, 7.2, t)
                if frame_idx == int(6.8 * FPS):
                    audio_events.append({"name": "question_pop", "frame": frame_idx, "time": t})
                target_cam_x = 880.0
            else:
                # Look DOWN at the ground console hotkeys! Flips to [!]
                slime_x = 745.0
                foot_y = FLOOR_Y
                target_squash_y = 1.0
                target_tilt = 0.0
                eye_mode = "pill"
                target_look_x = -0.45
                target_look_y = +0.50
                bubble = "[!]"
                bubble_alpha = 1.0
                if frame_idx == int(7.6 * FPS):
                    audio_events.append({"name": "idea_ping", "frame": frame_idx, "time": t})
                target_cam_x = 820.0

        # =============================================================
        # BEAT 3: 8.5 ~ 13.5s (Stomp 3 Hotkeys -> Compile -> Windows Rise)
        # =============================================================
        elif t < 13.5:
            is_awake = True
            color_blend = 1.0
            star_visible = True
            star_x = 1080.0 + 10.0 * math.sin(t * 2.2)
            star_y = 560.0 + 12.0 * math.cos(t * 1.8)

            firewall_h = 230.0
            firewall_state = "alarm" if t < 12.5 else "access_granted"

            # Hop 1 (8.50 ~ 9.80s): From 745.0 -> Key 1 (330.0)
            if t < 9.80:
                bubble = None
                if t < 9.25:
                    u_h1 = (t - 8.50) / 0.75
                    fj = eval_foot_jump(u_h1, 745.0, FLOOR_Y, KEY1_X, KEY_TOP_Y, arc_height=130.0)
                    slime_x = fj["x"]
                    foot_y = fj["foot_y"]
                    target_squash_y = fj["squash_y"]
                    target_tilt = fj["tilt"]
                    target_look_x = -0.75
                    target_look_y = +0.35
                    eye_mode = "pill"
                    target_cam_x = lerp(820.0, 620.0, u_h1)
                    if frame_idx == int(8.62 * FPS):
                        audio_events.append({"name": "slime_hop", "frame": frame_idx, "time": t})
                else:
                    slime_x = KEY1_X
                    u_p1 = (t - 9.25) / 0.55
                    key1_press = math.sin(u_p1 * math.pi)
                    foot_y = KEY_TOP_Y + 16.0 * key1_press
                    target_squash_y = 1.0 - 0.45 * key1_press
                    target_tilt = 0.0
                    target_look_x = -0.65
                    target_look_y = +0.40
                    eye_mode = "wince" if key1_press > 0.45 else "pill"
                    typed_cmd = "./compile"
                    target_cam_x = 620.0
                    if frame_idx == int(9.25 * FPS):
                        audio_events.append({"name": "key_click_1", "frame": frame_idx, "time": t})

            # Hop 2 (9.80 ~ 11.10s): From Key 1 (330.0) -> Key 2 (490.0)
            elif t < 11.10:
                typed_cmd = "./compile"
                if t < 10.55:
                    u_h2 = (t - 9.80) / 0.75
                    fj = eval_foot_jump(u_h2, KEY1_X, KEY_TOP_Y, KEY2_X, KEY_TOP_Y, arc_height=110.0)
                    slime_x = fj["x"]
                    foot_y = fj["foot_y"]
                    target_squash_y = fj["squash_y"]
                    target_tilt = fj["tilt"]
                    target_look_x = lerp(-0.55, +0.65, u_h2)
                    target_look_y = +0.35
                    eye_mode = "pill"
                    target_cam_x = lerp(620.0, 700.0, u_h2)
                    if frame_idx == int(9.92 * FPS):
                        audio_events.append({"name": "slime_hop", "frame": frame_idx, "time": t})
                else:
                    slime_x = KEY2_X
                    u_p2 = (t - 10.55) / 0.55
                    key2_press = math.sin(u_p2 * math.pi)
                    foot_y = KEY_TOP_Y + 16.0 * key2_press
                    target_squash_y = 1.0 - 0.45 * key2_press
                    target_tilt = 0.0
                    target_look_x = +0.65
                    target_look_y = +0.40
                    eye_mode = "wince" if key2_press > 0.45 else "pill"
                    typed_cmd = "./compile --jump"
                    target_cam_x = 700.0
                    if frame_idx == int(10.55 * FPS):
                        audio_events.append({"name": "key_click_2", "frame": frame_idx, "time": t})

            # Hop 3 (11.10 ~ 12.50s): From Key 2 (490.0) -> Key 3 (650.0)
            elif t < 12.50:
                typed_cmd = "./compile --jump"
                if t < 11.85:
                    u_h3 = (t - 11.10) / 0.75
                    fj = eval_foot_jump(u_h3, KEY2_X, KEY_TOP_Y, KEY3_X, KEY_TOP_Y, arc_height=120.0)
                    slime_x = fj["x"]
                    foot_y = fj["foot_y"]
                    target_squash_y = fj["squash_y"]
                    target_tilt = fj["tilt"]
                    target_look_x = +0.70
                    target_look_y = +0.35
                    eye_mode = "pill"
                    target_cam_x = lerp(700.0, 780.0, u_h3)
                    if frame_idx == int(11.22 * FPS):
                        audio_events.append({"name": "slime_hop", "frame": frame_idx, "time": t})
                else:
                    slime_x = KEY3_X
                    u_p3 = (t - 11.85) / 0.65
                    key3_press = math.sin(u_p3 * math.pi)
                    foot_y = KEY_TOP_Y + 16.0 * key3_press
                    target_squash_y = 1.0 - 0.45 * key3_press
                    target_tilt = 0.0
                    target_look_x = +0.70
                    target_look_y = +0.35
                    eye_mode = "wince" if key3_press > 0.45 else "pill"
                    typed_cmd = "./compile --jump --overclock"
                    prog_pct = smoothstep(11.85, 12.50, t) * 100.0
                    target_cam_x = 780.0
                    if frame_idx == int(11.85 * FPS):
                        audio_events.append({"name": "key_click_3", "frame": frame_idx, "time": t})

            # 12.50 ~ 13.50s: Stands on Key 3 (650.0), watches firewall grant access & staircase windows rise
            else:
                typed_cmd = "./compile --jump --overclock"
                prog_pct = 100.0
                slime_x = KEY3_X
                foot_y = KEY_TOP_Y
                target_squash_y = 1.0 + 0.04 * math.sin(t * 7.0)
                u_turn = (t - 12.50) / 1.0
                target_look_x = lerp(-0.45, +0.75, smoothstep(0.0, 1.0, u_turn))
                target_look_y = lerp(+0.20, -0.45, smoothstep(0.0, 1.0, u_turn))
                target_tilt = 0.05
                eye_mode = "happy"

                if frame_idx == int(12.55 * FPS):
                    audio_events.append({"name": "compile_chord", "frame": frame_idx, "time": t})
                if frame_idx == int(12.70 * FPS):
                    audio_events.append({"name": "stair_rise", "frame": frame_idx, "time": t})

                if t >= 12.60:
                    firewall_state = "access_granted"
                    firewall_h = lerp(230.0, 40.0, smoothstep(12.60, 13.30, t))
                    stair_rise = smoothstep(12.60, 13.50, t)

                target_cam_x = lerp(780.0, 1020.0, smoothstep(12.60, 13.50, t))

        # =============================================================
        # BEAT 4: 13.5 ~ 18.0s (Climb 3D Windows & Stomp ERR_404 -> Continuous Vault onto Zipline!)
        # =============================================================
        elif t < 18.0:
            is_awake = True
            color_blend = 1.0
            stair_rise = 1.0
            firewall_state = "access_granted"
            firewall_h = 40.0
            typed_cmd = "./compile --jump --overclock"
            prog_pct = 100.0

            star_visible = True
            star_x = 2320.0 + 12.0 * math.sin(t * 2.8)
            star_y = 260.0 + 10.0 * math.cos(t * 2.0)

            # Jump 1 (13.5 ~ 14.3s): From Key 3 (650, 826) -> Step 1 [tty1] (1185, 625)
            if t < 14.3:
                u = (t - 13.5) / 0.8
                fj = eval_foot_jump(u, KEY3_X, KEY_TOP_Y, STEP1_X, STEP1_Y, arc_height=135.0)
                slime_x, foot_y, target_squash_y, target_tilt = fj["x"], fj["foot_y"], fj["squash_y"], fj["tilt"]
                target_look_x = +0.70
                target_look_y = -0.30
                eye_mode = "pill"
                target_cam_x = lerp(1020.0, 1320.0, u)
                if frame_idx == int(13.5 * FPS):
                    audio_events.append({"name": "stair_hop_1", "frame": frame_idx, "time": t})

            # Jump 2 (14.3 ~ 15.1s): Step 1 (1185, 625) -> Step 2 [tty2] (1520, 535)
            elif t < 15.1:
                u = (t - 14.3) / 0.8
                fj = eval_foot_jump(u, STEP1_X, STEP1_Y, STEP2_X, STEP2_Y, arc_height=120.0)
                slime_x, foot_y, target_squash_y, target_tilt = fj["x"], fj["foot_y"], fj["squash_y"], fj["tilt"]
                target_look_x = +0.70
                target_look_y = -0.30
                eye_mode = "pill"
                target_cam_x = lerp(1320.0, 1660.0, u)
                if frame_idx == int(14.3 * FPS):
                    audio_events.append({"name": "stair_hop_2", "frame": frame_idx, "time": t})

            # Jump 3 (15.1 ~ 15.9s): Step 2 (1520, 535) -> Step 3 [kernel.log] (1850, 445)
            elif t < 15.9:
                u = (t - 15.1) / 0.8
                fj = eval_foot_jump(u, STEP2_X, STEP2_Y, STEP3_X, STEP3_Y, arc_height=120.0)
                slime_x, foot_y, target_squash_y, target_tilt = fj["x"], fj["foot_y"], fj["squash_y"], fj["tilt"]
                target_look_x = +0.70
                target_look_y = -0.30
                eye_mode = "pill"
                target_cam_x = lerp(1660.0, 1980.0, u)
                if frame_idx == int(15.1 * FPS):
                    audio_events.append({"name": "stair_hop_3", "frame": frame_idx, "time": t})

            # 15.9 ~ 16.3s: Quick elastic charge on Step 3 (1850, 445) before leaping onto ERR_404
            elif t < 16.3:
                slime_x = STEP3_X
                foot_y = STEP3_Y
                u_prep = (t - 15.9) / 0.40
                target_squash_y = 1.0 - 0.42 * smoothstep(0.0, 1.0, u_prep)
                target_tilt = 0.14
                target_look_x = +0.75
                target_look_y = -0.25
                eye_mode = "wince"
                target_cam_x = lerp(1980.0, 2080.0, u_prep)
                if frame_idx == int(15.95 * FPS):
                    audio_events.append({"name": "monster_growl", "frame": frame_idx, "time": t})

            # 16.3 ~ 17.15s: Continuous Parabolic Leap from Step 3 (1850, 445) -> Top of ERR_404 (2160, 295)!
            elif t < 17.15:
                u = (t - 16.3) / 0.85
                # Linear X progression preserves horizontal momentum right through the stomp!
                slime_x = lerp(STEP3_X, ERR404_X, u)
                foot_y = lerp(STEP3_Y, ERR404_HEAD_Y, u) - 4.0 * 145.0 * u * (1.0 - u)
                vy = math.cos(u * math.pi)
                target_squash_y = 0.94 + abs(vy) * 0.32
                target_tilt = -0.16 * vy
                if u > 0.55:
                    target_look_x = +0.25
                    target_look_y = +0.55
                else:
                    target_look_x = +0.65
                    target_look_y = -0.15
                eye_mode = "pill"
                target_cam_x = lerp(2080.0, 2240.0, u)
                if frame_idx == int(16.33 * FPS):
                    audio_events.append({"name": "jump_high", "frame": frame_idx, "time": t})

            # 17.15 ~ 18.00s: STOMP IMPACT & SEAMLESS REBOUND VAULT DIRECTLY ONTO ZIPLINE CURSOR (2400, 306)!
            else:
                err404_alive = False
                u_reb = (t - 17.15) / 0.85
                # Continuous horizontal motion from ERR_404 head (2160) straight to Zipline Cursor (2400)!
                slime_x = lerp(ERR404_X, ZIP_X0, u_reb)
                # Parabolic rebound arc from ERR_404 head (295) to Zipline Cursor top (320 - 14 = 306)!
                foot_y = lerp(ERR404_HEAD_Y, ZIP_Y0 - 14.0, u_reb) - 4.0 * 115.0 * u_reb * (1.0 - u_reb)

                if u_reb < 0.14:
                    # Momentary impact compression as it crushes ERR_404
                    target_squash_y = 0.62
                    eye_mode = "wince"
                else:
                    vy_reb = math.cos(u_reb * math.pi)
                    target_squash_y = 0.96 + abs(vy_reb) * 0.24
                    eye_mode = "happy"

                target_tilt = 0.14 * math.cos(u_reb * math.pi)
                target_look_x = +0.75
                target_look_y = -0.10
                bubble = "+1024 EXP"
                bubble_alpha = smoothstep(0.0, 0.12, u_reb) * (1.0 - smoothstep(0.72, 1.0, u_reb))
                target_cam_x = lerp(2240.0, 2480.0, u_reb)

                if frame_idx == int(17.15 * FPS):
                    audio_events.append({"name": "smash_impact", "frame": frame_idx, "time": t})
                if frame_idx == int(17.40 * FPS):
                    audio_events.append({"name": "exp_chime", "frame": frame_idx, "time": t})

        # =============================================================
        # BEAT 5: 18.0 ~ 21.55s (Zipline Glide -> Smooth Disembark -> Hop onto Enter Key & Absorb Token)
        # =============================================================
        elif t < 21.55:
            is_awake = True
            color_blend = 1.0
            stair_rise = 1.0
            err404_alive = False
            bubble = None

            # 18.00 ~ 20.10s: High-speed Zipline Glide from (2400, 320) to (3400, 380)
            if t < 20.10:
                zipline_active = True
                u_zip = (t - 18.00) / 2.10
                # Blend linear + smoothstep so velocity is non-zero right at t=18.0s (no stall on latch!)
                u_glide = 0.38 * u_zip + 0.62 * smoothstep(0.0, 1.0, u_zip)
                cursor_x = lerp(ZIP_X0, ZIP_X1, u_glide)
                cursor_y = lerp(ZIP_Y0, ZIP_Y1, u_glide)

                slime_x = cursor_x
                foot_y = cursor_y - 14.0
                # Elastic landing cushion on the cursor during first 0.18s of glide
                if u_zip < 0.10:
                    target_squash_y = lerp(0.76, 0.94, u_zip / 0.10)
                else:
                    target_squash_y = 0.94
                target_tilt = 0.16
                target_look_x = +0.75
                target_look_y = 0.0
                eye_mode = "pill"

                star_visible = True
                star_x = ENTER_X + 8.0 * math.sin(t * 3.0)
                star_y = 420.0 + 8.0 * math.cos(t * 2.0)

                if frame_idx == int(18.00 * FPS):
                    audio_events.append({"name": "zipline_latch", "frame": frame_idx, "time": t})
                if frame_idx == int(18.25 * FPS):
                    audio_events.append({"name": "zipline_whoosh", "frame": frame_idx, "time": t})

                target_cam_x = lerp(2480.0, 3460.0, u_glide)

            # 20.10 ~ 20.80s: Continuous Forward Leap off Zipline (3400, 366) -> Floor in front of Enter Key (3460, 860)
            elif t < 20.80:
                zipline_active = True
                cursor_x, cursor_y = ZIP_X1, ZIP_Y1
                u_drop = (t - 20.10) / 0.70

                # Immediate airborne trajectory carrying forward momentum (zero mid-air pause!)
                slime_x = lerp(ZIP_X1, 3465.0, u_drop)
                foot_y = lerp(ZIP_Y1 - 14.0, FLOOR_Y, u_drop * u_drop) - 55.0 * u_drop * (1.0 - u_drop)
                target_squash_y = 1.18 if u_drop < 0.85 else 0.72
                target_tilt = 0.12 * (1.0 - u_drop)
                target_look_x = +0.80
                target_look_y = +0.25
                eye_mode = "pill"

                # Star dives into Enter Key and spawns the collectible [ ↵ ] token right above the Enter Key!
                star_visible = False
                token_active = True
                token_x, token_y = ENTER_X, 665.0
                token_alpha = smoothstep(20.10, 20.35, t)
                if frame_idx == int(20.20 * FPS):
                    audio_events.append({"name": "star_token_drop", "frame": frame_idx, "time": t})

                target_cam_x = lerp(3460.0, 3600.0, u_drop)

            # 20.80 ~ 21.55s: Seamless Bounce from Floor (3465, 860) -> Giant Enter Key Top (3680, 740) & Collect Token!
            else:
                zipline_active = True
                cursor_x, cursor_y = ZIP_X1, ZIP_Y1
                u_hop = (t - 20.80) / 0.75
                fj = eval_foot_jump(u_hop, 3465.0, FLOOR_Y, ENTER_X, ENTER_TOP_Y, arc_height=130.0)
                slime_x = fj["x"]
                foot_y = fj["foot_y"]
                target_squash_y = fj["squash_y"]
                target_tilt = fj["tilt"]
                target_look_x = +0.65 * (1.0 - u_hop)
                target_look_y = -0.35 * (1.0 - u_hop) + 0.35 * u_hop

                if frame_idx == int(20.90 * FPS):
                    audio_events.append({"name": "slime_hop", "frame": frame_idx, "time": t})

                # Token stays anchored at (ENTER_X, 665.0) and is absorbed as Slime lands on Enter Key top!
                token_x, token_y = ENTER_X, 665.0
                if t < 21.40:
                    token_active = True
                    token_alpha = 1.0 - smoothstep(21.15, 21.40, t)
                    eye_mode = "pill"
                else:
                    token_active = False
                    eye_mode = "sparkle"
                    if frame_idx == int(21.35 * FPS):
                        audio_events.append({"name": "token_absorb_ding", "frame": frame_idx, "time": t})

                target_cam_x = lerp(3600.0, 3720.0, u_hop)

        # =============================================================
        # BEAT 6: 21.55 ~ 26.0s (Giant Enter Slam -> Full Green Pipe Assembly -> Slime Jumps Into Pipe!)
        # =============================================================
        else:
            is_awake = True
            color_blend = 1.0
            stair_rise = 1.0
            err404_alive = False
            star_visible = False
            token_active = False
            zipline_active = True
            cursor_x, cursor_y = ZIP_X1, ZIP_Y1
            target_cam_y = 540.0

            # 21.55 ~ 22.10s: Deep charge crouch on Enter Key top (3680, 740)
            if t < 22.10:
                slime_x = ENTER_X
                foot_y = ENTER_TOP_Y
                u_ch = (t - 21.55) / 0.55
                target_squash_y = lerp(0.92, 0.52, smoothstep(0.0, 1.0, u_ch))
                target_look_x = 0.0
                target_look_y = +0.55
                eye_mode = "wince"
                target_cam_x = 3720.0
                if frame_idx == int(21.65 * FPS):
                    audio_events.append({"name": "charge_up", "frame": frame_idx, "time": t})

            # 22.10 ~ 22.70s: Rocket Leap to high altitude (foot_y = 240.0)
            elif t < 22.70:
                if frame_idx == int(22.10 * FPS):
                    audio_events.append({"name": "rocket_leap", "frame": frame_idx, "time": t})
                u_rk = (t - 22.10) / 0.60
                slime_x = ENTER_X
                foot_y = lerp(ENTER_TOP_Y, 240.0, smoothstep(0.0, 1.0, u_rk))
                target_squash_y = 1.35 if u_rk < 0.72 else 1.02
                target_look_x = 0.0
                target_look_y = +0.55
                eye_mode = "pill"
                target_cam_x = 3750.0

            # 22.70 ~ 23.00s: DIVINE DIVE SLAM onto Giant Enter Key!
            elif t < 23.00:
                u_dv = (t - 22.70) / 0.30
                slime_x = ENTER_X
                foot_y = lerp(240.0, ENTER_TOP_Y + 55.0, u_dv * u_dv)
                enter_press = smoothstep(0.65, 1.0, u_dv)
                target_squash_y = 1.48
                target_look_x = 0.0
                target_look_y = +0.55
                eye_mode = "pill"
                target_cam_x = 3780.0

            # 23.00 ~ 24.40s: MEGA IMPACT & COMPLETE 16-BIT GREEN PIPE ASSEMBLY (at x=4020, y=632..860)
            elif t < 24.40:
                if frame_idx == int(23.00 * FPS):
                    audio_events.append({"name": "mega_enter_slam", "frame": frame_idx, "time": t})
                if frame_idx == int(23.55 * FPS):
                    audio_events.append({"name": "pixel_crystallize", "frame": frame_idx, "time": t})

                u_post = (t - 23.00) / 1.40
                enter_press = 1.0
                slime_x = ENTER_X
                foot_y = ENTER_TOP_Y + 55.0

                if t < 24.05:
                    # Recover from slam & watch the 16-Bit Green Pipe assemble on the right!
                    target_squash_y = 0.48 + 0.52 * smoothstep(23.00, 23.60, t)
                    target_look_x = smoothstep(23.20, 23.70, t) * 0.85
                    target_look_y = -0.25 * smoothstep(23.20, 23.70, t)
                    eye_mode = "wince" if t < 23.25 else "sparkle"
                else:
                    # 24.05 ~ 24.40s: Pipe is 100% complete! Slime crouches to jump into the pipe!
                    u_prep_pipe = (t - 24.05) / 0.35
                    target_squash_y = 1.0 - 0.38 * smoothstep(0.0, 1.0, u_prep_pipe)
                    target_tilt = 0.14 * u_prep_pipe
                    target_look_x = +0.85
                    target_look_y = -0.35
                    eye_mode = "sparkle"

                pipe_progress = smoothstep(23.05, 24.05, t)
                target_cam_x = lerp(3780.0, 3880.0, smoothstep(23.00, 24.00, t))

            # 24.40 ~ 25.15s: SLIME LEAPS IN HIGH ARC FROM ENTER KEY (3680, 795) TO PIPE MOUTH (4020, 632)!
            elif t < 25.15:
                if frame_idx == int(24.40 * FPS):
                    audio_events.append({"name": "jump_high", "frame": frame_idx, "time": t})

                enter_press = 1.0
                pipe_progress = 1.0
                u_jmp = (t - 24.40) / 0.75

                slime_x = lerp(ENTER_X, PIPE_X, smoothstep(0.0, 1.0, u_jmp))
                foot_y = lerp(ENTER_TOP_Y + 55.0, PIPE_TOP_Y + 4.0, u_jmp) - 4.0 * 210.0 * u_jmp * (1.0 - u_jmp)
                vy_p = math.cos(u_jmp * math.pi)
                target_squash_y = 0.95 + abs(vy_p) * 0.30
                target_tilt = -0.18 * vy_p
                if u_jmp < 0.60:
                    target_look_x = +0.75
                    target_look_y = -0.25
                else:
                    # Look straight down into the pipe mouth as it dives in!
                    target_look_x = 0.0
                    target_look_y = +0.65
                    slime_pipe_clip_y = PIPE_TOP_Y + 6.0
                eye_mode = "happy" if u_jmp < 0.65 else "pill"
                target_cam_x = lerp(3880.0, 3960.0, u_jmp)

            # 25.15 ~ 26.00s: SLIME DIVES INSIDE THE GREEN WARP PORTAL & DISAPPEARS INTO WORLD 02!
            else:
                if frame_idx == int(25.15 * FPS):
                    audio_events.append({"name": "pipe_enter_warp", "frame": frame_idx, "time": t})

                enter_press = 1.0
                pipe_progress = 1.0
                slime_x = PIPE_X
                slime_pipe_clip_y = PIPE_TOP_Y + 6.0
                target_cam_x = 3960.0

                if t < 25.68:
                    u_dive = (t - 25.15) / 0.53
                    # Plunge down from pipe mouth (636) deep into pipe interior (840)
                    foot_y = lerp(PIPE_TOP_Y + 4.0, PIPE_BOTTOM_Y - 10.0, smoothstep(0.0, 1.0, u_dive))
                    target_squash_y = 1.22
                    target_tilt = 0.0
                    target_look_x = 0.0
                    target_look_y = +0.55
                    eye_mode = "sparkle"
                    slime_visible = True
                else:
                    # Completely inside the pipe!
                    foot_y = PIPE_BOTTOM_Y
                    slime_visible = False

        # -------------------------------------------------------------
        # 3. Apply Continuous 2nd-Order Spring-Damper Filtering
        # -------------------------------------------------------------
        filtered_squash_y = squash_sd.step(target_squash_y, dt=DT)
        filtered_tilt = tilt_sd.step(target_tilt, dt=DT)
        filtered_look_x, filtered_look_y = look_sd.step(target_look_x, target_look_y, dt=DT)
        filtered_cam_x = cam_x_sd.step(target_cam_x, dt=DT)
        filtered_cam_y = cam_y_sd.step(target_cam_y, dt=DT)

        # Strict analytical contact calculation
        slime_y = foot_y - SLIME_R * filtered_squash_y * 0.96

        # -------------------------------------------------------------
        # 4. Update ERR_404 Shard physics (t >= 17.15s, exact impact frame!)
        # -------------------------------------------------------------
        shards_state = []
        if t >= 17.15:
            dt_shard = t - 17.15
            for sh in shards_init:
                sx = sh["x0"] + sh["vx"] * dt_shard
                sy = sh["y0"] + sh["vy"] * dt_shard + 0.5 * 980.0 * (dt_shard ** 2)
                srot = sh["rot0"] + sh["vrot"] * dt_shard
                shards_state.append({
                    "char": sh["char"],
                    "x": sx,
                    "y": sy,
                    "rot": srot,
                    "alpha": max(0.0, 1.0 - dt_shard * 0.45)
                })

        # -------------------------------------------------------------
        # 5. Update Pixel Pipe Particles (t >= 23.00s -> 100% locked by 24.05s)
        # -------------------------------------------------------------
        particles_state = []
        if t >= 23.00:
            dt_p = t - 23.00
            for p in particles_init:
                u_local = smoothstep(p["delay"], p["delay"] + 0.72, dt_p)
                # Ballistic burst out from Enter key during first 0.28s, then magnetic snap to pipe pixel grid
                burst_t = min(0.28, dt_p)
                blast_x = p["x0"] + p["vx"] * burst_t
                blast_y = p["y0"] + p["vy"] * burst_t + 0.5 * 500.0 * (burst_t ** 2)
                px = lerp(blast_x, p["tx"], u_local)
                py = lerp(blast_y, p["ty"], u_local)

                particles_state.append({
                    "x": px,
                    "y": py,
                    "color_type": p["color_type"],
                    "alpha": min(1.0, dt_p * 5.0),
                    "locked": (u_local >= 0.995)
                })

        # -------------------------------------------------------------
        # 6. Assemble Frame State
        # -------------------------------------------------------------
        frame_state = {
            "frame_idx": frame_idx,
            "t": t,
            "cam_x": filtered_cam_x,
            "cam_y": filtered_cam_y,
            "crt_open_x": crt_open_x,
            "crt_open_y": crt_open_y,
            "crt_flash_alpha": crt_flash_alpha,

            "slime": {
                "visible": slime_visible,
                "pipe_clip_y": slime_pipe_clip_y,
                "x": slime_x,
                "y": slime_y,
                "radius": SLIME_R,
                "squash_y": filtered_squash_y,
                "tilt": filtered_tilt,
                "look": (filtered_look_x, filtered_look_y),
                "eye_mode": eye_mode,
                "blink": blink,
                "is_awake": is_awake,
                "color_blend": color_blend,
                "bubble": bubble,
                "bubble_alpha": bubble_alpha,
            },

            "star": {
                "visible": star_visible,
                "x": star_x,
                "y": star_y,
                "radius": star_r,
                "rot": star_rot,
            },

            "token": {
                "active": token_active,
                "x": token_x,
                "y": token_y,
                "radius": 32.0,
                "rot": token_rot,
                "alpha": token_alpha,
            },

            "firewall": {
                "state": firewall_state,
                "h": firewall_h,
                "shake": firewall_shake,
                "x": FIREWALL_X,
                "y": FLOOR_Y,
            },

            "prompt": {
                "typed": typed_cmd,
                "prog_pct": prog_pct,
                "key1_press": key1_press,
                "key2_press": key2_press,
                "key3_press": key3_press,
            },

            "staircase": {
                "rise": stair_rise,
            },

            "err404": {
                "alive": err404_alive,
                "x": err404_x,
                "y": err404_y,
                "shards": shards_state,
            },

            "zipline": {
                "active": zipline_active,
                "cursor_x": cursor_x,
                "cursor_y": cursor_y,
            },

            "enter_key": {
                "press_depth": enter_press,
                "x": ENTER_X,
                "y": 420.0,
            },

            "pipe": {
                "progress": pipe_progress,
                "x": PIPE_X,
                "top_y": PIPE_TOP_Y,
                "bottom_y": PIPE_BOTTOM_Y,
            },

            "particles": particles_state,
        }
        frames_state.append(frame_state)

    return frames_state, audio_events

if __name__ == "__main__":
    states, events = run_simulation()
    print(f"[sim_01_crt] Generated {len(states)} frames, {len(events)} audio events.")
    for ev in events[:10]:
        print(f"  Event: {ev['name']:20s} at t={ev['time']:5.2f}s (f={ev['frame']})")
