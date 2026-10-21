# -*- coding: utf-8 -*-
"""
World 02 · 16-Bit 像素横版大闯关 (sim_02_pixel.py)
Deterministic Simulation Pass (30 fps, 28.0s = 840 frames).
Enforces:
  - 100% C^0 & C^1 continuous Slime trajectories across all 6 beats (zero teleports, exact surface landings).
  - Zero leftover green dots after the Warp Portal finishes assembling at t = 0.65s.
  - Continuous leading flight of the Guide Star ✦, visibly diving into the Gold [?] Block in Beat 3 and bursting out in Beat 4.
  - Pitch-black Cyber Breach transition in Beat 6 (25.1s ~ 28.0s) with a bottom purple-laser & particle portal mouth,
    Slime plunging into the bottom opening, and glowing Cyber Data Cubes overflowing upward!
"""

import math
import os
import sys
import numpy as np

# Repo root derived from this file (worlds/world_02_pixel/sim_02_pixel.py)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from slime_engine import SpringDamper1D, SpringDamper2D, eval_continuous_hop_chain, eval_targeted_jump

FPS = 30
TOTAL_FRAMES = 840
DURATION = 28.0

# Native World Dimensions
NATIVE_WORLD_W = 1600
NATIVE_H = 180
SCALE = 6


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / max(1e-6, edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def simulate_world_02():
    """
    Run full 28.0s simulation of World 02 and return (frames_state, audio_events).
    """
    frames_state = []
    audio_events = []

    # 2nd-order Spring-Damper Filters for smooth C^2 physics & gaze
    squash_spring = SpringDamper1D(x0=1.0, v0=0.0, freq=6.2, zeta=0.68)
    tilt_spring = SpringDamper1D(x0=0.0, v0=0.0, freq=4.8, zeta=0.72)
    look_spring = SpringDamper2D(x0=0.3, y0=-0.2, freq=4.8, zeta=0.75)
    cam_spring = SpringDamper1D(x0=0.0, v0=0.0, freq=3.2, zeta=0.84)

    # Slime State
    slime_x = 50.0
    slime_foot_y = 126.0
    target_squash_y = 1.0
    target_tilt = 0.0
    target_look_x = 0.3
    target_look_y = -0.2
    slime_eye_mode = "pill"
    slime_blink = 0.0
    slime_visible = False
    slime_pipe_clip = False
    slime_castle_clip = False
    slime_is_invincible = False
    slime_ghost_trail = []

    # Overheads & UI
    rpg_card_alpha = 0.0
    speech_bubble = None  # None, "?", "!"
    speech_bubble_timer = 0.0
    banner_alpha = 0.0
    hud_score = 0
    target_score = 0
    floating_texts = []  # list of [text, x, y, alpha, color_type, vy]

    # Star guide ✦
    star_x = 96.0
    star_y = 66.0
    star_visible = True
    star_rot = 0.0

    # Scene actors
    pipe_assembly = 0.0
    pipe_particles_init = []
    rng = np.random.RandomState(42)
    for i in range(56):
        px0 = rng.uniform(28.0, 72.0)
        py0 = rng.uniform(-45.0, 20.0)
        target_px = 36.0 + (i % 7) * 4.0
        target_py = 108.0 + (i // 7) * 4.5
        pipe_particles_init.append({
            "x0": px0, "y0": py0,
            "tx": target_px, "ty": target_py,
            "delay": rng.uniform(0.0, 0.18),
        })

    # Pre-generate 84 sleek 3D Cyber Neon Warp Streaks & Holo-Sparks for Beat 6 portal eruption (t >= 26.15s)
    rng_cyber = np.random.RandomState(2077)
    cyber_sparks_init = []
    for i in range(84):
        ang = rng_cyber.uniform(-math.pi * 0.84, -math.pi * 0.16)
        spd = rng_cyber.uniform(520.0, 1480.0)
        cyber_sparks_init.append({
            "x0": 960.0 + rng_cyber.uniform(-110.0, 110.0),
            "y0": 880.0 + rng_cyber.uniform(-10.0, 10.0),
            "vx": math.cos(ang) * spd,
            "vy": math.sin(ang) * spd - rng_cyber.uniform(120.0, 340.0),
            "length": rng_cyber.uniform(28.0, 86.0),
            "width": rng_cyber.uniform(2.0, 4.5),
            "delay": rng_cyber.uniform(0.0, 0.72),
            "color_type": ["cyan", "magenta", "purple", "gold", "white"][i % 5],
            "is_diamond": (i % 3 == 0),
        })
    void_slime_trail_hist = []

    # Ladybug (Screen 2: x = 365 -> 315)
    ladybug_x = 365.0
    ladybug_foot_y = 144.0
    ladybug_state = "patrol"

    # Springboard (Screen 2: x = 420)
    spring_x = 420.0
    spring_compress = 0.0

    # Blocks (Screen 3: stepped bricks at 758..806, [?] at 796..812, hidden at 720..736)
    hidden_block_discovered = False
    hidden_block_y_offset = 0.0
    hidden_twinkle_phase = 0.0
    cloud_ladder_growth = 0.0

    qblock_bumped = False
    qblock_empty = False
    qblock_y_offset = 0.0

    rainbow_star_active = False
    rainbow_star_x = 804.0
    rainbow_star_y = 26.0

    # Cloud monsters (Screen 4: spike pit 980..1100, moving cloud center (1035, 132), top surface y=124)
    cloud_monsters = [
        {"x": 1005.0, "y": 106.0, "vx": 0.0, "vy": 0.0, "rot": 0.0, "hit": False},
        {"x": 1085.0, "y": 104.0, "vx": 0.0, "vy": 0.0, "rot": 0.0, "hit": False},
    ]
    moving_cloud_x = 1035.0
    moving_cloud_y = 132.0

    # Flagpole & Castle (Screen 5: pole at 1357, castle at 1420..1504, door center at 1462)
    flag_progress = 0.0
    fireworks = []

    # 16-Bit Pixel Arcade Coin (本关实物信物 at x=1412, y=134)
    coin_token_active = False
    coin_token_x = 1412.0
    coin_token_y = 134.0
    coin_token_collected = False

    # Cyber rift & pitch-black void cutscene state
    cyber_rift_open = 0.0
    door_zoom = 0.0

    # Camera
    target_cam_x = 0.0

    dt = 1.0 / FPS

    # =========================================================================
    # MAIN SIMULATION LOOP (840 frames)
    # =========================================================================
    for frame in range(TOTAL_FRAMES):
        t = frame / float(FPS)
        state = {}

        slime_pipe_clip = False
        slime_castle_clip = False
        hidden_twinkle_phase = t * 8.0

        # Score update interpolation
        if hud_score < target_score:
            hud_score = min(target_score, hud_score + 40)

        # Update floating texts
        for ft in floating_texts:
            ft[2] += ft[5]
            ft[3] = max(0.0, ft[3] - 0.03)
        floating_texts = [ft for ft in floating_texts if ft[3] > 0.0]

        # Update speech bubbles
        if speech_bubble_timer > 0:
            speech_bubble_timer -= dt
            if speech_bubble_timer <= 0:
                speech_bubble = None

        # Decay block offsets
        if hidden_block_y_offset < 0.0:
            hidden_block_y_offset = min(0.0, hidden_block_y_offset + 0.5)
        if qblock_y_offset < 0.0:
            qblock_y_offset = min(0.0, qblock_y_offset + 0.5)

        # Compute pipe particles deterministically so 100% land by t = 0.63s (frame 19)
        cur_pipe_particles = []
        if t < 0.63:
            pipe_assembly = smoothstep(0.0, 0.60, t)
            for p in pipe_particles_init:
                u_p = smoothstep(p["delay"], p["delay"] + 0.42, t)
                if u_p < 0.999:
                    cur_pipe_particles.append({
                        "x": lerp(p["x0"], p["tx"], u_p),
                        "y": lerp(p["y0"], p["ty"], u_p),
                        "landed": False,
                    })
        else:
            pipe_assembly = 1.0

        # Void cutscene defaults
        void_scene_active = False
        void_star_visible = False
        void_star_x = 960.0
        void_star_y = 880.0
        void_slime_visible = False
        void_slime_x = 960.0
        void_slime_y = 540.0
        void_slime_squash_y = 1.0
        void_slime_tilt = 0.0
        void_slime_look = (0.0, 0.5)
        void_slime_eye = "pill"
        void_sparks_state = []

        # ---------------------------------------------------------------------
        # BEAT 1: Pipe Assembly -> Smooth Pop Out -> Settle Bounce -> Gaze (0.0 ~ 4.0s, frames 0..119)
        # ---------------------------------------------------------------------
        if frame < 20:  # 0.0 ~ 0.67s: Phosphor particles assemble warp portal completely
            if frame == 0:
                audio_events.append((0.05, "block_assembly", {}))
            slime_visible = False
            rpg_card_alpha = 0.0
            star_visible = True
            star_x = 96.0
            star_y = 66.0 + math.sin(t * 3.5) * 4.0

        elif frame < 29:  # 0.67 ~ 0.97s: Slime emerges smoothly up out of the pipe mouth (x=50, y: 126 -> 108)
            if frame == 20:
                audio_events.append((t, "pipe_pop", {}))
            slime_visible = True
            slime_pipe_clip = True
            u_em = (frame - 20) / 9.0
            slime_x = 50.0
            slime_foot_y = lerp(126.0, 108.0, smoothstep(0.0, 1.0, u_em))
            target_squash_y = 1.25
            target_tilt = 0.0
            target_look_x = 0.35
            target_look_y = -0.35
            slime_eye_mode = "wince" if u_em < 0.5 else "pill"
            star_visible = True
            star_x = 96.0 + (t - 0.67) * 14.0
            star_y = 66.0 + math.sin(t * 3.5) * 4.0

        elif frame < 48:  # 0.97 ~ 1.60s: Parabolic pop arc from pipe top (50, 108) to ground (86, 144)
            slime_visible = True
            u_pop = (frame - 29) / 19.0
            slime_x = lerp(50.0, 86.0, u_pop)
            slime_foot_y = lerp(108.0, 144.0, u_pop * u_pop) - 4.0 * 24.0 * u_pop * (1.0 - u_pop)
            vy_p = math.cos(u_pop * math.pi)
            target_squash_y = 0.95 + abs(vy_p) * 0.28
            target_tilt = -0.15 * vy_p
            target_look_x = 0.45
            target_look_y = 0.15
            slime_eye_mode = "pill"
            if frame == 47:
                squash_spring.impulse(-2.0)
                audio_events.append((t, "slime_bounce", {}))
            star_visible = True
            star_x = 100.0 + (t - 0.97) * 18.0
            star_y = 66.0 + math.sin(t * 3.5) * 4.0

        elif frame < 60:  # 1.60 ~ 2.00s: Elastic settle bounce in place at x = 86.0, foot_y = 144.0
            slime_visible = True
            u_b = (frame - 48) / 12.0
            slime_x = 86.0
            slime_foot_y = 144.0 - 4.0 * 9.0 * u_b * (1.0 - u_b)
            target_squash_y = 0.72 if u_b < 0.2 else (1.08 if u_b < 0.7 else 0.88)
            target_tilt = 0.0
            target_look_x = -0.35
            target_look_y = 0.0
            slime_eye_mode = "pill"
            star_visible = True
            star_x = 112.0 + (t - 1.60) * 18.0
            star_y = 66.0 + math.sin(t * 3.5) * 4.0

        elif frame < 120:  # 2.00 ~ 4.00s: Anchored at (86.0, 144.0), look back at pipe -> audience -> up at Star ✦
            slime_visible = True
            slime_x = 86.0
            slime_foot_y = 144.0
            target_squash_y = 1.0 + 0.03 * math.sin(t * 5.0)
            target_tilt = 0.0

            if frame < 76:
                target_look_x = -0.55
                target_look_y = 0.0
                slime_eye_mode = "pill"
                slime_blink = 1.0 if (64 <= frame <= 68) else 0.0
            elif frame < 88:
                target_look_x = 0.0
                target_look_y = -0.15
                slime_eye_mode = "pill"
                slime_blink = 0.0
            else:
                target_look_x = 0.60
                target_look_y = -0.35
                slime_eye_mode = "pill"
                slime_blink = 0.0

            if 68 <= frame < 102:
                rpg_card_alpha = min(1.0, rpg_card_alpha + 0.15)
                if frame == 68:
                    audio_events.append((t, "card_appear", {}))
            elif 102 <= frame < 118:
                rpg_card_alpha = max(0.0, rpg_card_alpha - 0.15)
            else:
                rpg_card_alpha = 0.0

            star_visible = True
            star_x = lerp(120.0, 170.0, smoothstep(2.0, 4.0, t))
            star_y = 64.0 + math.sin(t * 4.0) * 5.0

        # ---------------------------------------------------------------------
        # BEAT 2: Continuous Hop from 86 -> 235 -> Parabolic Stomp on Ladybug (315, 132) -> Springboard (420) -> High Arc (4.0 ~ 8.5s)
        # ---------------------------------------------------------------------
        elif frame < 144:  # 4.00 ~ 4.80s: 2 ground hops from x=86.0 to x=235.0 (zero teleport!)
            rpg_card_alpha = 0.0
            u_run = (frame - 120) / 24.0
            hop = eval_continuous_hop_chain(u_run, num_hops=2, jump_height=10.0)
            slime_x = lerp(86.0, 235.0, hop["progress_x"])
            slime_foot_y = 144.0 + hop["y_off"]
            target_squash_y = hop["squash_y"]
            target_tilt = hop["tilt"]
            target_look_x = 0.75
            target_look_y = -0.05
            slime_eye_mode = "pill"

            ladybug_x = lerp(365.0, 332.0, u_run)
            ladybug_foot_y = 144.0

            star_visible = True
            star_x = slime_x + 84.0
            star_y = 60.0 + math.sin(t * 4.0) * 5.0

        elif frame < 162:  # 4.80 ~ 5.40s: True parabolic leap from ground (235, 144) onto Ladybug's back (315, 132)!
            rpg_card_alpha = 0.0
            u_atk = (frame - 144) / 18.0
            slime_x = lerp(235.0, 315.0, u_atk)
            slime_foot_y = lerp(144.0, 132.0, u_atk) - 4.0 * 32.0 * u_atk * (1.0 - u_atk)
            vy_a = math.cos(u_atk * math.pi)
            target_squash_y = 0.94 + abs(vy_a) * 0.28
            target_tilt = -0.15 * vy_a
            target_look_x = 0.65 if u_atk < 0.6 else 0.15
            target_look_y = -0.15 if u_atk < 0.6 else 0.45
            slime_eye_mode = "pill"

            ladybug_x = lerp(332.0, 315.0, u_atk)
            ladybug_foot_y = 144.0
            if frame == 145:
                audio_events.append((t, "jump", {}))

            star_visible = True
            star_x = slime_x + 82.0
            star_y = 60.0 + math.sin(t * 4.0) * 5.0

        elif frame == 162:  # t = 5.40s: Exact Stomp Moment on Ladybug back (315, 132)!
            rpg_card_alpha = 0.0
            slime_x = 315.0
            ladybug_x = 315.0
            ladybug_foot_y = 144.0
            slime_foot_y = 132.0
            target_squash_y = 0.54
            squash_spring.impulse(-2.2)
            ladybug_state = "stomped"
            target_score += 100
            target_look_x = 0.0
            target_look_y = 0.52
            slime_eye_mode = "wince"
            floating_texts.append(["+100", 315.0, 118.0, 1.0, "gold", -0.8])
            audio_events.append((t, "stomp", {}))
            audio_events.append((t + 0.05, "coin_get", {}))
            star_visible = True
            star_x = slime_x + 82.0
            star_y = 60.0 + math.sin(t * 4.0) * 5.0

        elif frame < 195:  # 5.43 ~ 6.50s: Rebound parabola from Ladybug (315, 132) directly to Springboard (420, 132)
            rpg_card_alpha = 0.0
            u_reb = (frame - 162) / 33.0
            slime_x = lerp(315.0, 420.0, u_reb)
            slime_foot_y = 132.0 - 4.0 * 44.0 * u_reb * (1.0 - u_reb)
            target_squash_y = 0.92 + abs(math.cos(u_reb * math.pi)) * 0.32
            target_tilt = -0.15 * math.cos(u_reb * math.pi)
            target_look_x = 0.55
            target_look_y = 0.20
            slime_eye_mode = "pill"
            star_visible = True
            star_x = slime_x + 80.0
            star_y = 58.0 + math.sin(t * 4.0) * 5.0

        elif frame < 205:  # 6.50 ~ 6.83s: Lands on Springboard (420, 132) and compresses it to 139.0
            rpg_card_alpha = 0.0
            slime_x = 420.0
            u_c = (frame - 195) / 9.0
            spring_compress = min(1.0, u_c)
            slime_foot_y = lerp(132.0, 139.0, spring_compress)
            target_squash_y = lerp(0.85, 0.58, spring_compress)
            target_look_x = 0.55
            target_look_y = 0.20
            slime_eye_mode = "wince"
            if frame == 204:
                squash_spring.impulse(2.4)
                audio_events.append((t, "spring_launch", {}))
            star_visible = True
            star_x = 500.0 + u_c * 14.0
            star_y = 56.0 + math.sin(t * 4.0) * 5.0

        elif frame < 246:  # 6.83 ~ 8.20s: Springboard launches Slime in high arc over Spike Pit (420 -> 636, 144)
            rpg_card_alpha = 0.0
            u_l = (frame - 204) / 42.0
            spring_compress = max(0.0, 1.0 - (u_l / 0.16))
            slime_x = lerp(420.0, 636.0, u_l)
            slime_foot_y = lerp(139.0, 144.0, u_l) - 4.0 * 78.0 * u_l * (1.0 - u_l)
            target_squash_y = 0.90 + abs(math.cos(u_l * math.pi)) * 0.36
            target_tilt = -0.18 * math.cos(u_l * math.pi)
            target_look_x = 0.65
            target_look_y = 0.15
            slime_eye_mode = "pill"
            if frame == 245:
                squash_spring.impulse(-1.8)
                audio_events.append((t, "slime_bounce", {}))
            star_visible = True
            star_x = slime_x + 80.0
            star_y = 56.0 + math.sin(t * 3.5) * 4.0

        elif frame < 256:  # 8.20 ~ 8.53s: Elastic landing settle hop (636 -> 652, 144)
            rpg_card_alpha = 0.0
            spring_compress = 0.0
            u_sb = (frame - 246) / 10.0
            slime_x = lerp(636.0, 652.0, u_sb)
            slime_foot_y = 144.0 - 4.0 * 9.0 * u_sb * (1.0 - u_sb)
            target_squash_y = 0.72 if u_sb < 0.25 else 1.0
            target_tilt = 0.0
            target_look_x = 0.65
            target_look_y = -0.25
            slime_eye_mode = "pill"
            star_visible = True
            star_x = lerp(716.0, 735.0, u_sb)
            star_y = 54.0 + math.sin(t * 3.5) * 4.0

        # ---------------------------------------------------------------------
        # BEAT 3: Star Dives Into [?] Block (804, 26) -> Slime Hops & Fails Jump -> Discovers Hidden Block (8.53 ~ 13.20s)
        # ---------------------------------------------------------------------
        elif frame < 282:  # 8.53 ~ 9.40s: Slime hops to wall (652 -> 736) while Star visibly flies into [?] block (804, 26)!
            rpg_card_alpha = 0.0
            u_w = (frame - 256) / 26.0
            hop = eval_continuous_hop_chain(u_w, num_hops=2, jump_height=8.0)
            slime_x = lerp(652.0, 736.0, hop["progress_x"])
            slime_foot_y = 144.0 + hop["y_off"]
            target_squash_y = hop["squash_y"]
            target_tilt = hop["tilt"]
            target_look_x = 0.55
            target_look_y = -0.50
            slime_eye_mode = "pill"

            # Star flies in a smooth arc from (735, 54) right into the center of the Gold [?] Block (804, 26)!
            star_visible = True
            u_st_in = smoothstep(0.0, 1.0, u_w)
            star_x = lerp(735.0, 804.0, u_st_in)
            star_y = lerp(54.0, 26.0, u_st_in) - 4.0 * 14.0 * u_w * (1.0 - u_w)
            if frame == 281:
                # [?] Block jiggles as the Star dives inside it!
                qblock_y_offset = -4.0
                audio_events.append((t, "coin_get", {}))

        elif frame < 308:  # 9.40 ~ 10.27s: Star is now inside [?]; Slime jumps at x=736 trying to reach [?] and falls short!
            rpg_card_alpha = 0.0
            star_visible = False
            u_try = (frame - 282) / 26.0
            slime_x = 736.0
            if u_try < 0.76:
                u_air = u_try / 0.76
                slime_foot_y = 144.0 - 4.0 * 28.0 * u_air * (1.0 - u_air)
                target_squash_y = 1.22 if u_air < 0.5 else 0.92
            else:
                slime_foot_y = 144.0
                target_squash_y = 0.74 if u_try < 0.88 else 1.0
            target_tilt = 0.0
            target_look_x = 0.25
            target_look_y = -0.65
            slime_eye_mode = "pill"
            if frame == 283:
                audio_events.append((t, "jump", {}))
            if frame == 302:
                speech_bubble = "?"
                speech_bubble_timer = 1.1
                audio_events.append((t, "question_bubble", {}))

        elif frame < 336:  # 10.27 ~ 11.20s: Puzzled at (736, 144), looks around and spots twinkling hidden block at (728, 108)
            rpg_card_alpha = 0.0
            star_visible = False
            slime_x = 736.0
            slime_foot_y = 144.0
            target_squash_y = 1.0 + 0.03 * math.sin(frame * 0.25)
            target_tilt = 0.0
            if frame < 322:
                target_look_x = 0.20
                target_look_y = -0.55
            else:
                target_look_x = -0.35
                target_look_y = -0.25
            slime_eye_mode = "pill"

        elif frame < 358:  # 11.20 ~ 11.93s: Pops [!] and hops back to x=728.0 (directly under Hidden Block 720..736)
            rpg_card_alpha = 0.0
            star_visible = False
            if frame == 336:
                speech_bubble = "!"
                speech_bubble_timer = 1.4
                slime_eye_mode = "sparkle"
                audio_events.append((t, "idea_exclamation", {}))
            u_bk = (frame - 336) / 22.0
            slime_x = lerp(736.0, 728.0, smoothstep(0.0, 1.0, u_bk))
            slime_foot_y = 144.0 - 4.0 * 6.0 * u_bk * (1.0 - u_bk)
            target_squash_y = 1.0
            target_look_x = 0.0
            target_look_y = -0.55

        elif frame < 396:  # 11.93 ~ 13.20s: Vertical jump at x=728.0, head hits Hidden Block bottom (y=112) at apex (frame 376)!
            rpg_card_alpha = 0.0
            star_visible = False
            speech_bubble = None
            speech_bubble_timer = 0.0
            slime_x = 728.0
            u_j = (frame - 358) / 38.0
            # Apex foot_y = 132.0 -> top of Slime head (foot_y - 20) = 112.0 (exact bottom of Hidden Block!)
            slime_foot_y = 144.0 - 4.0 * 12.0 * u_j * (1.0 - u_j)
            target_look_x = 0.0
            target_look_y = -0.75
            target_squash_y = 1.12 if (u_j < 0.5) else 0.88
            slime_eye_mode = "wince" if (0.42 <= u_j <= 0.58) else "pill"

            if frame == 358:
                audio_events.append((t, "jump", {}))
            elif frame == 376:
                hidden_block_discovered = True
                hidden_block_y_offset = -4.0
                target_squash_y = 0.68
                squash_spring.impulse(-1.4)
                audio_events.append((t, "hidden_block_hit", {}))
                audio_events.append((t + 0.1, "ladder_grow", {}))

            if hidden_block_discovered:
                cloud_ladder_growth = min(3.0, cloud_ladder_growth + 0.16)

        # ---------------------------------------------------------------------
        # BEAT 4: Climb Cloud Ladder (exact cloud top surfaces!) -> Hit [?] Block -> Star Bursts Out -> Invincible Leap to Ground (13.20 ~ 18.40s)
        # ---------------------------------------------------------------------
        elif frame < 468:  # 13.20 ~ 15.60s: Climb cloud ladder: (728, 144) -> (674, 114) -> (706, 90) -> (738, 68) -> Wall Top (796, 64)
            rpg_card_alpha = 0.0
            star_visible = False
            cloud_ladder_growth = 3.0
            ladder_sub = frame - 396
            target_look_x = 0.35
            target_look_y = -0.55
            slime_eye_mode = "pill"

            if ladder_sub < 18:
                tj = eval_targeted_jump(ladder_sub / 18.0, 728.0, 144.0, 674.0, 114.0, arc_height=18.0)
                slime_x, slime_foot_y, target_squash_y, target_tilt = tj["x"], tj["y"], tj["squash_y"], tj["tilt"]
                if ladder_sub == 0:
                    audio_events.append((t, "ladder_step", {}))
            elif ladder_sub < 36:
                tj = eval_targeted_jump((ladder_sub - 18) / 18.0, 674.0, 114.0, 706.0, 90.0, arc_height=18.0)
                slime_x, slime_foot_y, target_squash_y, target_tilt = tj["x"], tj["y"], tj["squash_y"], tj["tilt"]
                if ladder_sub == 18:
                    audio_events.append((t, "ladder_step", {}))
            elif ladder_sub < 54:
                tj = eval_targeted_jump((ladder_sub - 36) / 18.0, 706.0, 90.0, 738.0, 68.0, arc_height=18.0)
                slime_x, slime_foot_y, target_squash_y, target_tilt = tj["x"], tj["y"], tj["squash_y"], tj["tilt"]
                if ladder_sub == 36:
                    audio_events.append((t, "ladder_step", {}))
            else:
                tj = eval_targeted_jump((ladder_sub - 54) / 18.0, 738.0, 68.0, 796.0, 64.0, arc_height=14.0)
                slime_x, slime_foot_y, target_squash_y, target_tilt = tj["x"], tj["y"], tj["squash_y"], tj["tilt"]
                if ladder_sub == 54:
                    audio_events.append((t, "ladder_step", {}))

        elif frame < 510:  # 15.60 ~ 17.00s: On Wall Top (796, 64), head-butts [?] block bottom (y=34), Star bursts out, absorbs Rainbow Star ON Wall Top!
            rpg_card_alpha = 0.0
            sub = frame - 468
            slime_x = 796.0
            if sub < 8:
                # Deep crouch on Brick Wall Top (796, 64)
                slime_foot_y = 64.0
                target_look_x = 0.0
                target_look_y = -0.75
                target_squash_y = 0.72
                slime_eye_mode = "wince"
                star_visible = False
            elif sub < 24:
                # Jump up so top of Slime head (foot_y - 22 = 34.0) hits exact bottom of [?] block (y=34.0) at sub=14 (frame 482, t=16.07s)!
                u_j = (sub - 8) / 16.0
                slime_foot_y = 64.0 - 4.0 * 8.0 * u_j * (1.0 - u_j)
                target_squash_y = 1.12 if u_j < 0.5 else 0.86
                target_look_x = 0.0
                target_look_y = -0.85
                slime_eye_mode = "wince" if (11 <= sub <= 17) else "pill"
                if sub == 8:
                    audio_events.append((t, "head_smash", {}))
                if sub == 14 and not qblock_bumped:
                    qblock_bumped = True
                    qblock_empty = True
                    qblock_y_offset = -5.0
                    target_score += 1000
                    floating_texts.append(["+1000", 796.0, 14.0, 1.0, "gold", -0.9])
                    audio_events.append((t, "block_hit_gold", {}))
                    audio_events.append((t + 0.08, "coins_fountain", {}))
                    star_visible = True
                    star_x = 804.0
                    star_y = 18.0
                    rainbow_star_active = True
                    rainbow_star_x = 804.0
                    rainbow_star_y = 18.0
                if qblock_bumped:
                    star_visible = True
                    star_x = lerp(804.0, 860.0, (sub - 14) / 28.0)
                    star_y = 24.0 + math.sin(t * 5.0) * 4.0
                    rainbow_star_x = lerp(804.0, 796.0, (sub - 14) / 26.0)
                    rainbow_star_y = lerp(18.0, 52.0, (sub - 14) / 26.0) - 4.0 * 10.0 * ((sub - 14) / 26.0) * (1.0 - (sub - 14) / 26.0)
            else:
                # Standing firmly on Brick Wall Top (796, 64) as Rainbow Star drops into Slime!
                slime_foot_y = 64.0
                target_squash_y = 0.88 if sub < 32 else 1.05
                target_look_x = 0.65
                target_look_y = -0.20
                u_rs = min(1.0, (sub - 14) / 26.0)
                star_visible = True
                star_x = lerp(804.0, 880.0, (sub - 14) / 28.0)
                star_y = lerp(24.0, 52.0, (sub - 14) / 28.0)
                if sub < 40:
                    rainbow_star_active = True
                    rainbow_star_x = lerp(804.0, 796.0, u_rs)
                    rainbow_star_y = lerp(18.0, 54.0, u_rs * u_rs)
                    slime_eye_mode = "pill"
                else:
                    if not slime_is_invincible:
                        slime_is_invincible = True
                        rainbow_star_active = False
                        audio_events.append((t, "star_power_up", {}))
                        audio_events.append((t + 0.1, "invincible_bgm_start", {}))
                    slime_eye_mode = "sparkle"

        elif frame < 532:  # 17.00 ~ 17.73s: True Parabolic Leap off Brick Wall Top (796, 64) to Ground (885, 144)!
            rpg_card_alpha = 0.0
            slime_is_invincible = True
            rainbow_star_active = False
            slime_eye_mode = "sparkle"
            u_drop = (frame - 510) / 22.0
            slime_x = lerp(796.0, 885.0, u_drop)
            slime_foot_y = lerp(64.0, 144.0, u_drop * u_drop) - 24.0 * u_drop * (1.0 - u_drop)
            target_squash_y = 1.18 if u_drop < 0.85 else 0.72
            target_tilt = 0.16
            target_look_x = 0.80
            target_look_y = 0.15
            if frame == 531:
                squash_spring.impulse(-1.8)
                audio_events.append((t, "slime_bounce", {}))
            star_visible = True
            star_x = slime_x + 84.0
            star_y = 56.0 + math.sin(t * 5.0) * 6.0

        elif frame < 552:  # 17.73 ~ 18.40s: Invincible ground hop from (885, 144) to Left Cliff edge (965, 144)
            rpg_card_alpha = 0.0
            slime_eye_mode = "sparkle"
            u_dash = (frame - 532) / 20.0
            hop = eval_continuous_hop_chain(u_dash, num_hops=1, jump_height=12.0)
            slime_x = lerp(885.0, 965.0, u_dash)
            slime_foot_y = 144.0 + hop["y_off"]
            target_squash_y = hop["squash_y"]
            target_tilt = hop["tilt"]
            target_look_x = 0.85
            target_look_y = -0.05
            star_visible = True
            star_x = slime_x + 84.0
            star_y = 56.0 + math.sin(t * 5.0) * 6.0

        # ---------------------------------------------------------------------
        # BEAT 5: 2-Jump Vault Across Moving Cloud (1035, 124) & Spike Pit -> Ram 2 Monsters -> Flagpole (18.40 ~ 22.80s)
        # ---------------------------------------------------------------------
        elif frame < 574:  # 18.40 ~ 19.13s: Jump 1 from Left Cliff (965, 144) -> Moving Cloud Top (1035, 124), ramming Monster 1!
            rpg_card_alpha = 0.0
            slime_eye_mode = "sparkle"
            u_j1 = (frame - 552) / 22.0
            moving_cloud_x = 1035.0
            slime_x = lerp(965.0, 1035.0, u_j1)
            slime_foot_y = lerp(144.0, 124.0, u_j1) - 4.0 * 28.0 * u_j1 * (1.0 - u_j1)
            target_squash_y = 0.95 + abs(math.cos(u_j1 * math.pi)) * 0.25
            target_tilt = -0.15 * math.cos(u_j1 * math.pi)
            target_look_x = 0.85
            target_look_y = 0.0

            cm1 = cloud_monsters[0]
            if not cm1["hit"] and abs(slime_x - cm1["x"]) < 18.0:
                cm1["hit"] = True
                cm1["vx"] = 4.2
                cm1["vy"] = -5.2
                target_score += 400
                floating_texts.append(["+400", cm1["x"], cm1["y"] - 12, 1.0, "gold", -1.0])
                audio_events.append((t, "enemy_ram", {}))

            for cm in cloud_monsters:
                if cm["hit"]:
                    cm["vy"] += 0.35
                    cm["x"] += cm["vx"]
                    cm["y"] += cm["vy"]
                    cm["rot"] += 0.25

            star_visible = True
            star_x = slime_x + 84.0
            star_y = 54.0 + math.sin(t * 5.0) * 6.0

        elif frame < 596:  # 19.13 ~ 19.87s: Jump 2 from Moving Cloud Top (1035, 124) -> Right Cliff Ground (1125, 144), ramming Monster 2!
            rpg_card_alpha = 0.0
            slime_eye_mode = "sparkle"
            u_j2 = (frame - 574) / 22.0
            moving_cloud_x = 1035.0
            slime_x = lerp(1035.0, 1125.0, u_j2)
            slime_foot_y = lerp(124.0, 144.0, u_j2) - 4.0 * 28.0 * u_j2 * (1.0 - u_j2)
            target_squash_y = 0.95 + abs(math.cos(u_j2 * math.pi)) * 0.25
            target_tilt = -0.15 * math.cos(u_j2 * math.pi)
            target_look_x = 0.85
            target_look_y = 0.0

            cm2 = cloud_monsters[1]
            if not cm2["hit"] and abs(slime_x - cm2["x"]) < 18.0:
                cm2["hit"] = True
                cm2["vx"] = 4.6
                cm2["vy"] = -5.8
                target_score += 800
                floating_texts.append(["+800", cm2["x"], cm2["y"] - 12, 1.0, "gold", -1.0])
                floating_texts.append(["EXTRA!", cm2["x"] + 14, cm2["y"] - 22, 1.0, "cyan", -1.2])
                audio_events.append((t, "enemy_ram", {}))
                audio_events.append((t + 0.08, "extra_life_sound", {}))

            for cm in cloud_monsters:
                if cm["hit"]:
                    cm["vy"] += 0.35
                    cm["x"] += cm["vx"]
                    cm["y"] += cm["vy"]
                    cm["rot"] += 0.25

            star_visible = True
            star_x = slime_x + 84.0
            star_y = 54.0 + math.sin(t * 5.0) * 6.0

        elif frame < 626:  # 19.87 ~ 20.87s: Ground dash from (1125, 144) to Flagpole takeoff (1255, 144) (zero teleport!)
            rpg_card_alpha = 0.0
            slime_eye_mode = "sparkle"
            u_g = (frame - 596) / 30.0
            hop = eval_continuous_hop_chain(u_g, num_hops=2, jump_height=11.0)
            slime_x = lerp(1125.0, 1255.0, u_g)
            slime_foot_y = 144.0 + hop["y_off"]
            target_squash_y = hop["squash_y"]
            target_tilt = hop["tilt"]
            target_look_x = 0.80
            target_look_y = -0.15

            for cm in cloud_monsters:
                if cm["hit"]:
                    cm["vy"] += 0.35
                    cm["x"] += cm["vx"]
                    cm["y"] += cm["vy"]
                    cm["rot"] += 0.25

            star_visible = True
            star_x = lerp(1209.0, 1412.0, u_g)
            star_y = lerp(54.0, 96.0, u_g)

        elif frame < 652:  # 20.87 ~ 21.73s: Super Jump from (1255, 144) to Flagpole Peak (1357, 78)!
            rpg_card_alpha = 0.0
            if frame == 626:
                audio_events.append((t, "super_jump", {}))
            frac = (frame - 626) / 26.0
            slime_x = lerp(1255.0, 1357.0, frac)
            slime_foot_y = lerp(144.0, 78.0, frac) - 4.0 * 38.0 * frac * (1.0 - frac)
            target_look_x = 0.60
            target_look_y = -0.30
            slime_eye_mode = "wince" if frac < 0.16 else "pill"
            target_squash_y = 0.68 if frac < 0.16 else 1.25
            target_tilt = -0.15 * math.cos(frac * math.pi)
            if frame == 651:
                slime_x = 1357.0
                slime_foot_y = 78.0
                target_score += 5000
                floating_texts.append(["★ +5000 ★", 1357, 46, 1.0, "gold", -0.7])
                audio_events.append((t, "flagpole_top_catch", {}))
                audio_events.append((t + 0.1, "score_jackpot", {}))
            star_visible = True
            star_x = lerp(1412.0, 1462.0, frac)
            star_y = lerp(96.0, 118.0, frac)

        elif frame < 684:  # 21.73 ~ 22.80s: Slides down flagpole (1357, 78 -> 140), star flag rises, fireworks!
            rpg_card_alpha = 0.0
            slime_x = 1357.0
            slide_frac = (frame - 652) / 31.0
            slime_foot_y = lerp(78.0, 140.0, slide_frac)
            flag_progress = min(1.0, slide_frac)
            target_look_x = 0.45
            target_look_y = 0.20
            slime_eye_mode = "happy"
            target_squash_y = 1.12
            target_tilt = 0.0
            if frame == 653:
                audio_events.append((t, "flagpole_slide", {}))
            if frame == 665:
                star_visible = False
                coin_token_active = True
            if frame == 672:
                fireworks.append([1440, 48, frame, "coral"])
                target_score += 500
                floating_texts.append(["+500", 1440, 36, 1.0, "coral", -0.8])
                audio_events.append((t, "firework_bang", {}))
            elif frame == 678:
                fireworks.append([1475, 40, frame, "gold"])
                target_score += 500
                floating_texts.append(["+500", 1475, 28, 1.0, "gold", -0.8])
                audio_events.append((t, "firework_bang", {}))
            elif frame == 683:
                fireworks.append([1510, 48, frame, "cyan"])
                target_score += 500
                floating_texts.append(["+500", 1510, 36, 1.0, "cyan", -0.8])
                audio_events.append((t, "firework_bang", {}))

        # ---------------------------------------------------------------------
        # BEAT 6: Clean Hop off Flagpole -> Collect Coin -> Hop into Castle Door -> Pitch-Black Cyber Breach & Overflowing Data Cubes!
        # ---------------------------------------------------------------------
        elif frame < 702:  # 22.80 ~ 23.40s: Hop off Flagpole Base (1357, 140) to Ground (1382, 144)
            rpg_card_alpha = 0.0
            slime_is_invincible = False
            star_visible = False
            coin_token_active = True
            flag_progress = 1.0
            tj = eval_targeted_jump((frame - 684) / 18.0, 1357.0, 140.0, 1382.0, 144.0, arc_height=14.0)
            slime_x, slime_foot_y, target_squash_y, target_tilt = tj["x"], tj["y"], tj["squash_y"], tj["tilt"]
            target_look_x = 0.65
            target_look_y = 0.0
            slime_eye_mode = "pill"
            if frame == 684:
                audio_events.append((t, "jump", {}))

        elif frame < 724:  # 23.40 ~ 24.13s: Hop from (1382, 144) to (1412, 144) and absorb 16-Bit Coin Token!
            rpg_card_alpha = 0.0
            star_visible = False
            coin_token_active = True
            flag_progress = 1.0
            u_c = (frame - 702) / 22.0
            tj = eval_targeted_jump(u_c, 1382.0, 144.0, 1412.0, 144.0, arc_height=16.0)
            slime_x, slime_foot_y, target_squash_y, target_tilt = tj["x"], tj["y"], tj["squash_y"], tj["tilt"]
            target_look_x = 0.65
            target_look_y = 0.0
            if frame == 702:
                audio_events.append((t, "jump", {}))
            if frame >= 716 and not coin_token_collected:
                coin_token_collected = True
                slime_eye_mode = "sparkle"
                target_score += 1000
                floating_texts.append(["+1000", 1412, 116, 1.0, "gold", -0.8])
                audio_events.append((t, "star_coin_absorb", {}))
                audio_events.append((t + 0.1, "stage_clear_jingle", {}))

        elif frame < 752:  # 24.13 ~ 25.07s: Hop from (1412, 144) directly into Castle Arched Black Door (1462, 144)!
            rpg_card_alpha = 0.0
            star_visible = False
            flag_progress = 1.0
            u_d = (frame - 724) / 24.0
            if u_d <= 1.0:
                tj = eval_targeted_jump(u_d, 1412.0, 144.0, 1462.0, 144.0, arc_height=18.0)
                slime_x, slime_foot_y, target_squash_y, target_tilt = tj["x"], tj["y"], tj["squash_y"], tj["tilt"]
            else:
                slime_x = 1462.0
                slime_foot_y = 144.0
                target_squash_y = 0.85
                target_tilt = 0.0
            if u_d > 0.55:
                slime_castle_clip = True
            target_look_x = 0.45
            target_look_y = -0.10
            slime_eye_mode = "happy"
            if frame == 724:
                audio_events.append((t, "jump", {}))
            if frame >= 738:
                door_zoom = smoothstep(738.0, 752.0, float(frame))

        else:  # 25.07 ~ 28.00s (frames 752..839): PITCH-BLACK CYBER SPACE + 3D PERSPECTIVE HOLO-PORTAL + SLIME RIBBON DIVE & NEON WARP ERUPTION!
            rpg_card_alpha = 0.0
            star_visible = False
            slime_visible = False
            door_zoom = 1.0
            void_scene_active = True
            cyber_rift_open = smoothstep(25.08, 25.48, t)

            if frame == 754:
                audio_events.append((t, "cyber_rift_tear", {}))
            if frame == 758:
                audio_events.append((t, "super_jump", {}))
            if frame == 785:
                audio_events.append((t, "enemy_ram", {}))

            # 1) Guiding Star ✦ dives into the 3D Cyber Portal first (25.10 ~ 25.55s, frames 753..766)
            if 753 <= frame <= 766:
                void_star_visible = True
                u_vst = (frame - 753) / 13.0
                void_star_x = lerp(740.0, 960.0, smoothstep(0.0, 1.0, u_vst))
                void_star_y = lerp(240.0, 880.0, u_vst * u_vst)

            # 2) Slime leaps across the black void with a 3D Cyberpunk Ribbon Trail and plunges into the bottom 3D Portal (960, 880) at frame 785 (t=26.17s)!
            if frame < 758:
                void_slime_visible = True
                u_prep = (frame - 752) / 6.0
                void_slime_x = 500.0
                void_slime_y = 700.0
                void_slime_squash_y = lerp(1.0, 0.58, u_prep)
                void_slime_tilt = 0.15
                void_slime_look = (0.75, 0.35)
                void_slime_eye = "wince"
                void_slime_trail_hist = [(void_slime_x, void_slime_y)]
            elif frame < 786:
                void_slime_visible = True
                u_plunge = (frame - 758) / 27.0
                void_slime_x = lerp(500.0, 960.0, smoothstep(0.0, 0.84, u_plunge))
                # High arc from y=700 up to y=300 and plunging vertically down into the 3D portal core at y=895!
                void_slime_y = lerp(700.0, 895.0, u_plunge * u_plunge) - 4.0 * 420.0 * u_plunge * (1.0 - u_plunge)
                vy_v = math.cos(u_plunge * math.pi)
                void_slime_squash_y = 0.95 + abs(vy_v) * 0.48
                void_slime_tilt = -0.22 * vy_v if u_plunge < 0.65 else 0.0
                void_slime_look = (0.45, 0.35) if u_plunge < 0.55 else (0.0, 0.85)
                void_slime_eye = "pill" if u_plunge < 0.70 else "sparkle"
                void_slime_trail_hist.append((void_slime_x, void_slime_y))
                if len(void_slime_trail_hist) > 16:
                    void_slime_trail_hist.pop(0)
            else:
                void_slime_visible = False
                if len(void_slime_trail_hist) > 0:
                    void_slime_trail_hist.pop(0)

            # 3) 26.15 ~ 28.00s (frames 784..839): 3D Neon Warp Light-Streaks & Holo-Sparks erupting upward out of the 3D Portal!
            if t >= 26.12:
                dt_cyb = t - 26.12
                for sp in cyber_sparks_init:
                    t_loc = dt_cyb - sp["delay"]
                    if t_loc <= 0.0:
                        continue
                    cur_vx = sp["vx"]
                    cur_vy = sp["vy"] + 420.0 * t_loc
                    cx_s = sp["x0"] + sp["vx"] * t_loc
                    cy_s = sp["y0"] + sp["vy"] * t_loc + 0.5 * 420.0 * (t_loc ** 2)
                    s_alpha = min(1.0, t_loc * 7.5) * max(0.0, 1.0 - max(0.0, t_loc - 0.95) * 1.35)
                    if s_alpha > 0.02 and cy_s < 930.0:
                        void_sparks_state.append({
                            "x": cx_s,
                            "y": cy_s,
                            "vx": cur_vx,
                            "vy": cur_vy,
                            "length": sp["length"],
                            "width": sp["width"],
                            "alpha": s_alpha,
                            "color_type": sp["color_type"],
                            "is_diamond": sp["is_diamond"],
                        })

        # ---------------------------------------------------------------------
        # Step 2nd-order Spring-Damper Physics
        # ---------------------------------------------------------------------
        cur_squash_y = squash_spring.step(target_squash_y, dt)
        cur_tilt = tilt_spring.step(target_tilt, dt)
        cur_look_x, cur_look_y = look_spring.step(target_look_x, target_look_y, dt)

        # ---------------------------------------------------------------------
        # Slime Ghost Trail for Invincible Mode
        # ---------------------------------------------------------------------
        if slime_is_invincible:
            slime_ghost_trail.append((slime_x, slime_foot_y, cur_squash_y, cur_tilt, frame * 0.2))
            if len(slime_ghost_trail) > 6:
                slime_ghost_trail.pop(0)
        else:
            if len(slime_ghost_trail) > 0:
                slime_ghost_trail.pop(0)

        # Smooth camera tracking
        if frame < 735:
            target_cam_x = max(0.0, slime_x - 130.0)
        else:
            target_cam_x = 1462.0 - 160.0
        max_cam_x = NATIVE_WORLD_W - 320.0
        target_cam_x = min(max_cam_x, target_cam_x)

        cur_cam_x = cam_spring.step(target_cam_x, dt)
        cur_cam_x = max(0.0, min(max_cam_x, cur_cam_x))

        # Calculate geometric center y from foot_y for zero-clipping compatibility
        ry = 10.0 * cur_squash_y
        slime_center_y = slime_foot_y - ry

        # Pack frame state
        state["frame"] = frame
        state["t"] = t
        state["cam_x"] = cur_cam_x
        state["door_zoom"] = door_zoom

        # Slime
        state["slime"] = {
            "visible": slime_visible,
            "pipe_clip": slime_pipe_clip,
            "castle_clip": slime_castle_clip,
            "x": slime_x,
            "y": slime_center_y,
            "foot_y": slime_foot_y,
            "squash_y": cur_squash_y,
            "tilt": cur_tilt,
            "look": (cur_look_x, cur_look_y),
            "eye_mode": slime_eye_mode,
            "blink": slime_blink,
            "is_invincible": slime_is_invincible,
            "ghost_trail": list(slime_ghost_trail),
        }

        # Overhead UI
        state["rpg_card_alpha"] = rpg_card_alpha
        state["speech_bubble"] = speech_bubble
        state["banner_alpha"] = banner_alpha
        state["hud_score"] = hud_score
        state["floating_texts"] = [list(ft) for ft in floating_texts]

        # Scene actors
        state["pipe_assembly"] = pipe_assembly
        state["pipe_particles"] = cur_pipe_particles

        state["ladybug"] = {
            "x": ladybug_x,
            "y": ladybug_foot_y - 10.0,
            "foot_y": ladybug_foot_y,
            "state": ladybug_state,
        }

        state["spring"] = {
            "x": spring_x,
            "compress": spring_compress,
        }

        state["blocks"] = {
            "hidden_discovered": hidden_block_discovered,
            "hidden_y_offset": hidden_block_y_offset,
            "hidden_twinkle": (math.sin(hidden_twinkle_phase) > 0.25),
            "cloud_ladder_growth": cloud_ladder_growth,
            "qblock_bumped": qblock_bumped,
            "qblock_empty": qblock_empty,
            "qblock_y_offset": qblock_y_offset,
        }

        state["rainbow_star"] = {
            "active": rainbow_star_active,
            "x": rainbow_star_x,
            "y": rainbow_star_y,
        }

        state["cloud_monsters"] = [
            {"x": cm["x"], "y": cm["y"], "rot": cm["rot"], "hit": cm["hit"]}
            for cm in cloud_monsters
        ]

        state["moving_cloud"] = {
            "x": moving_cloud_x,
            "y": moving_cloud_y,
        }

        state["star_guide"] = {
            "visible": star_visible,
            "x": star_x,
            "y": star_y,
            "rot": star_rot,
        }

        state["flagpole"] = {
            "flag_progress": flag_progress,
        }

        state["fireworks"] = [
            {"x": fw[0], "y": fw[1], "age": frame - fw[2], "color": fw[3]}
            for fw in fireworks
            if frame - fw[2] < 28
        ]

        state["end_star"] = {
            "active": coin_token_active and not coin_token_collected,
            "x": coin_token_x,
            "y": coin_token_y,
            "rot_y": math.cos(frame * 0.25),
        }

        state["cyber_rift"] = {
            "open": cyber_rift_open,
            "void_active": void_scene_active,
            "void_star_visible": void_star_visible,
            "void_star_x": void_star_x,
            "void_star_y": void_star_y,
            "void_slime_visible": void_slime_visible,
            "void_slime_x": void_slime_x,
            "void_slime_y": void_slime_y,
            "void_slime_squash_y": void_slime_squash_y,
            "void_slime_tilt": void_slime_tilt,
            "void_slime_look": void_slime_look,
            "void_slime_eye": void_slime_eye,
            "void_slime_trail": list(void_slime_trail_hist),
            "void_sparks": void_sparks_state,
        }

        frames_state.append(state)

    return frames_state, audio_events


if __name__ == "__main__":
    states, events = simulate_world_02()
    print(f"[Sim World 02] Generated {len(states)} frames, {len(events)} audio events.")
