# -*- coding: utf-8 -*-
"""
World 07 · 1930s 复古橡皮管爵士乐园 (sim_07_rubberhose.py)
Fixed-step physics & 6-act cartoon simulation (30fps, 26.0s = 780 frames).

Full 6-Act Story Moments:
- Beat 1 (0.0s - 4.0s): 35mm film countdown (3-2-1) -> Stage lights on -> 132 BPM bounce -> 3D look
  Boss taps shoe, winds crank, Pie-Cut eyes glare, horn bounces to beat.
- Beat 2 (4.0s - 8.8s): 3 Deep Inhale -> Spit Blast cycles (t=4.2s, 5.4s, 6.6s)
  Boss leans back (+55px), chests puffs, horn pursed -> lunges forward (-68px) and blasts Note Critters!
  Critters arc through air, land on keys, and march towards slime with rubber-hose kicking legs!
  Slime screech brake at 6.4s with '?', then resolute sharp eyes & '!' at 7.8s with deep squash charge!
- Beat 3 (8.8s - 14.2s): 3 consecutive precision stomps on wavy piano keys (t=10.2s, 12.0s, 13.9s)
  Critters pancake flat (squash_y=0.20), X X eyes, 8 parabolic star/note particles burst!
  Technicolor rings bloom dynamically (0 -> 420 -> 880 -> 1600px)!
- Beat 4 (14.2s - 18.6s): Air leap absorbs Spinning Vinyl Token -> Lands on keys at 1040
  Boss furious shaking fists -> Slime rocket headbutt charge -> CLANG! 18.6s comic starburst on Boss forehead!
- Beat 5 (18.6s - 23.0s): Boss stunned (recoil oscillation, X X eyes, 5 orbiting stars)
  Slime gravity parabolic backflip -> lands squarely on piano keys at x=960 (foot_y=672, ZERO float!)
  Boss horn spasms into reverse vacuum vortex -> Guiding Star ✦ sucked into horn at 22.4s!
- Beat 6 (23.0s - 26.0s): Slime leaps from keys into horn vortex -> 1930s circular Iris-Out on horn center!

Zero clipping & zero floating: strictly grounded foot_y contact physics.
"""

import math
import sys
import os
import numpy as np
from typing import Dict, Any, List, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from slime_engine import eval_continuous_hop_chain, eval_targeted_jump

FPS = 30
DURATION = 26.0
TOTAL_FRAMES = int(round(DURATION * FPS))  # 780 frames
DT = 1.0 / FPS
BPM = 132.0
BEAT_DUR = 60.0 / BPM  # ~0.4545s per beat

# ---------------------------------------------------------------------------
# Analytical 3D S-Curved Piano Keyboard Surface Height
# ---------------------------------------------------------------------------
SPINE_CONTROL_PTS = [
    (84.0, 1050.0),
    (280.0, 930.0),
    (520.0, 765.0),
    (680.0, 680.0),
    (840.0, 660.0),
    (1120.0, 690.0),
    (1340.0, 730.0),
    (1480.0, 750.0),
]

def eval_spine(t_val: float) -> Tuple[float, float]:
    n = len(SPINE_CONTROL_PTS) - 1
    idx = min(n - 1, max(0, int(t_val * n)))
    local_t = t_val * n - idx
    p0 = SPINE_CONTROL_PTS[max(0, idx - 1)]
    p1 = SPINE_CONTROL_PTS[idx]
    p2 = SPINE_CONTROL_PTS[min(n, idx + 1)]
    p3 = SPINE_CONTROL_PTS[min(n, idx + 2)]
    tt = local_t * local_t
    ttt = tt * local_t
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * local_t +
               (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * tt +
               (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * ttt)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * local_t +
               (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * tt +
               (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * ttt)
    return x, y

# Precompute piano key midpoints for exact height interpolation
_KEY_XS = []
_KEY_YS = []
for _k in range(46):
    _t0 = _k / 46.0
    _t1 = (_k + 0.92) / 46.0
    _x0, _y0 = eval_spine(_t0)
    _x1, _y1 = eval_spine(_t1)
    _dx, _dy = _x1 - _x0, _y1 - _y0
    _seg_len = math.hypot(_dx, _dy)
    if _seg_len < 1e-4:
        _nx, _ny = 0.0, -1.0
    else:
        _nx, _ny = -_dy / _seg_len, _dx / _seg_len
    _depth_scale = 1.0 - 0.48 * _t0
    _key_length = 135.0 * _depth_scale
    _p_back = ((_x0 + _x1) * 0.5, (_y0 + _y1) * 0.5)
    _p_front = (_p_back[0] + _nx * _key_length, _p_back[1] + _ny * _key_length)
    _KEY_XS.append((_p_back[0] + _p_front[0]) * 0.5)
    _KEY_YS.append((_p_back[1] + _p_front[1]) * 0.5)

_KEY_XS = np.array(_KEY_XS)
_KEY_YS = np.array(_KEY_YS)

def piano_surface_y(x: float) -> float:
    """Returns continuous analytical surface height of the wavy piano keyboard at coordinate x."""
    if x <= _KEY_XS[0]:
        return float(_KEY_YS[0])
    if x >= _KEY_XS[-1]:
        return float(_KEY_YS[-1])
    return float(np.interp(x, _KEY_XS, _KEY_YS))

def smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / max(1e-6, edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def run_simulation() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Runs the 26.0s (780 frames) 6-act continuous physics and state simulation."""
    frames_state: List[Dict[str, Any]] = []
    audio_events: List[Dict[str, Any]] = []

    SLIME_BASE_R = 58.0
    BOSS_X = 1380.0
    BOSS_Y = 540.0
    HORN_CENTER_X = 1200.0
    HORN_CENTER_Y = 480.0
    BOSS_FOREHEAD_X = 1215.0
    BOSS_FOREHEAD_Y = 385.0
    HORN_MOUTH_X = 1195.0
    HORN_MOUTH_Y = 455.0

    triggered_events = set()
    def trigger(name: str, t_time: float, extra: dict = None):
        if name not in triggered_events:
            triggered_events.add(name)
            ev = {"name": name, "time": t_time}
            if extra:
                ev.update(extra)
            audio_events.append(ev)

    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx * DT
        beat = t * (BPM / 60.0)
        beat_phase = beat % 1.0

        # -------------------------------------------------------------
        # 1. 35mm Countdown, Opening Theater Curtains & Stage Lights (0.0s - 1.9s)
        # -------------------------------------------------------------
        countdown_active = (t < 1.2)
        countdown_num = 3 if t < 0.4 else (2 if t < 0.8 else 1)
        if t < 0.05:
            trigger("countdown_beep_3", 0.0)
        elif 0.4 <= t < 0.45:
            trigger("countdown_beep_2", 0.4)
        elif 0.8 <= t < 0.85:
            trigger("countdown_beep_1", 0.8)

        lights_on = smoothstep(1.15, 1.45, t)
        curtain_open_prog = smoothstep(1.15, 1.90, t)
        if 1.2 <= t < 1.25:
            trigger("stage_lights_on", 1.2)

        curtain_bounce_dy = math.sin(beat * math.pi) * 8.0 * (1.0 if 1.9 <= t < 4.0 else (0.4 if t >= 4.0 else 0.0))

        # -------------------------------------------------------------
        # 2. Boss Gramophone Detailed State Machine
        # -------------------------------------------------------------
        boss_scale = 1.0
        boss_bounce = beat_phase
        boss_stunned = False
        boss_recoil = 0.0
        boss_vortex = 0.0
        eye_state = "normal"
        cab_squash_y = 1.0 - 0.08 * math.sin(beat * math.pi)
        foot_tap_angle = math.sin(beat * math.pi) * 0.18
        record_rot = t * 8.0
        crank_rot = t * 5.0
        neck_lean_x = 0.0
        neck_stretch_y = 0.0
        horn_squash_x = 1.0
        horn_squash_y = 1.0
        tongue_wag = math.sin(beat * math.pi)
        inhale_stream = 0.0
        spit_blast = 0.0
        impact_flash = 0.0
        arm1_pose = "point"
        arm2_pose = "crank"
        arm_droop = 0.0

        # Beat 1: 132 BPM taunting swing
        if t < 3.75:
            eye_state = "normal"
            neck_lean_x = math.sin(beat * math.pi * 0.5) * 8.0
            neck_stretch_y = math.cos(beat * math.pi * 0.5) * 6.0
            horn_squash_x = 1.0 + 0.06 * math.sin(beat * math.pi)
            horn_squash_y = 1.0 - 0.06 * math.sin(beat * math.pi)
            arm1_pose = "point"
            arm2_pose = "crank"

        # Beat 2: 3 Inhale -> Spit Blast cycles
        elif 3.75 <= t < 4.20:
            # Inhale 1
            p_in = (t - 3.75) / 0.45
            eye_state = "inhale_squint"
            neck_lean_x = lerp(0.0, 55.0, p_in)
            neck_stretch_y = lerp(0.0, 22.0, p_in)
            cab_squash_y = lerp(1.0, 0.85, p_in)
            horn_squash_x = lerp(1.0, 1.25, p_in)
            horn_squash_y = lerp(1.0, 0.68, p_in)
            inhale_stream = p_in
            arm1_pose = "inhale"
            arm2_pose = "inhale"
            if 3.75 <= t < 3.80:
                trigger("boss_deep_inhale_1", 3.75)
        elif 4.20 <= t < 4.60:
            # Spit Blast 1
            p_spit = (t - 4.20) / 0.40
            eye_state = "angry"
            neck_lean_x = lerp(-68.0, 0.0, p_spit)
            neck_stretch_y = lerp(-14.0, 0.0, p_spit)
            cab_squash_y = lerp(1.18, 1.0, p_spit)
            horn_squash_x = lerp(0.78, 1.0, p_spit)
            horn_squash_y = lerp(1.38, 1.0, p_spit)
            tongue_wag = math.sin(p_spit * 18.0)
            spit_blast = 1.0 - p_spit
            arm1_pose = "blast"
            arm2_pose = "blast"
            if 4.20 <= t < 4.25:
                trigger("boss_spit_blast_1", 4.20)
        elif 4.60 <= t < 4.95:
            eye_state = "angry"
            arm1_pose = "point"
            arm2_pose = "crank"

        elif 4.95 <= t < 5.40:
            # Inhale 2
            p_in = (t - 4.95) / 0.45
            eye_state = "inhale_squint"
            neck_lean_x = lerp(0.0, 55.0, p_in)
            neck_stretch_y = lerp(0.0, 22.0, p_in)
            cab_squash_y = lerp(1.0, 0.85, p_in)
            horn_squash_x = lerp(1.0, 1.25, p_in)
            horn_squash_y = lerp(1.0, 0.68, p_in)
            inhale_stream = p_in
            arm1_pose = "inhale"
            arm2_pose = "inhale"
            if 4.95 <= t < 5.00:
                trigger("boss_deep_inhale_2", 4.95)
        elif 5.40 <= t < 5.80:
            # Spit Blast 2
            p_spit = (t - 5.40) / 0.40
            eye_state = "angry"
            neck_lean_x = lerp(-68.0, 0.0, p_spit)
            neck_stretch_y = lerp(-14.0, 0.0, p_spit)
            cab_squash_y = lerp(1.18, 1.0, p_spit)
            horn_squash_x = lerp(0.78, 1.0, p_spit)
            horn_squash_y = lerp(1.38, 1.0, p_spit)
            tongue_wag = math.sin(p_spit * 18.0)
            spit_blast = 1.0 - p_spit
            arm1_pose = "blast"
            arm2_pose = "blast"
            if 5.40 <= t < 5.45:
                trigger("boss_spit_blast_2", 5.40)
        elif 5.80 <= t < 6.15:
            eye_state = "angry"
            arm1_pose = "point"
            arm2_pose = "crank"

        elif 6.15 <= t < 6.60:
            # Inhale 3
            p_in = (t - 6.15) / 0.45
            eye_state = "inhale_squint"
            neck_lean_x = lerp(0.0, 55.0, p_in)
            neck_stretch_y = lerp(0.0, 22.0, p_in)
            cab_squash_y = lerp(1.0, 0.85, p_in)
            horn_squash_x = lerp(1.0, 1.25, p_in)
            horn_squash_y = lerp(1.0, 0.68, p_in)
            inhale_stream = p_in
            arm1_pose = "inhale"
            arm2_pose = "inhale"
            if 6.15 <= t < 6.20:
                trigger("boss_deep_inhale_3", 6.15)
        elif 6.60 <= t < 7.00:
            # Spit Blast 3
            p_spit = (t - 6.60) / 0.40
            eye_state = "angry"
            neck_lean_x = lerp(-68.0, 0.0, p_spit)
            neck_stretch_y = lerp(-14.0, 0.0, p_spit)
            cab_squash_y = lerp(1.18, 1.0, p_spit)
            horn_squash_x = lerp(0.78, 1.0, p_spit)
            horn_squash_y = lerp(1.38, 1.0, p_spit)
            tongue_wag = math.sin(p_spit * 18.0)
            spit_blast = 1.0 - p_spit
            arm1_pose = "blast"
            arm2_pose = "blast"
            if 6.60 <= t < 6.65:
                trigger("boss_spit_blast_3", 6.60)
        elif 7.00 <= t < 8.80:
            # Boss gloats and laughs as minions advance
            eye_state = "angry"
            cab_squash_y = 1.0 + 0.12 * math.sin(t * 16.0)
            arm1_pose = "point"
            arm2_pose = "crank"

        # Beat 3: Minions getting squashed
        elif 8.80 <= t < 14.20:
            eye_state = "angry"
            # Flinch after each stomp
            if 10.2 <= t < 11.2:
                dt_flinch = t - 10.2
                neck_lean_x = 35.0 * math.exp(-dt_flinch * 4.0) * math.sin(dt_flinch * 14.0)
            elif 12.0 <= t < 13.0:
                dt_flinch = t - 12.0
                neck_lean_x = 42.0 * math.exp(-dt_flinch * 4.0) * math.sin(dt_flinch * 14.0)
            elif 13.9 <= t < 14.2:
                dt_flinch = t - 13.9
                neck_lean_x = 50.0 * math.exp(-dt_flinch * 4.0) * math.sin(dt_flinch * 14.0)
            arm1_pose = "fist"
            arm2_pose = "fist"

        # Beat 4: Slime absorbs token, Boss enraged, rocket headbutt impact!
        elif 14.20 <= t < 16.20:
            eye_state = "angry"
            cab_squash_y = 1.0 + 0.10 * math.sin(t * 18.0)
            arm1_pose = "fist"
            arm2_pose = "fist"
        elif 16.20 <= t < 18.25:
            # Extreme rage: Boss leans forward shaking both fists
            eye_state = "angry"
            cab_squash_y = 1.0 + 0.14 * math.sin(t * 24.0)
            neck_lean_x = -22.0 + math.sin(t * 20.0) * 6.0
            arm1_pose = "fist"
            arm2_pose = "fist"
            if 16.20 <= t < 16.25:
                trigger("gramophone_furious_roar", 16.20)
        elif 18.25 <= t < 18.60:
            # Incoming rocket right in front of Boss! Wide-eyed startled surprise (NOT dizzy or recoiled yet!)
            p_shock = (t - 18.25) / 0.35
            eye_state = "hit_shock"
            neck_lean_x = lerp(-22.0, -18.0, p_shock)
            cab_squash_y = lerp(1.0, 0.94, p_shock)
            arm1_pose = "fist"
            arm2_pose = "fist"

        # Beat 4/5: Headbutt Impact CLANG! (18.60s) -> Boss whips backward & arms droop limply!
        elif 18.60 <= t < 23.00:
            boss_stunned = True
            eye_state = "dizzy_x"
            recoil_t = t - 18.60
            impulse = math.sin(recoil_t * 8.0) * math.exp(-recoil_t * 1.45)
            boss_recoil = 0.26 * impulse
            neck_lean_x = -18.0 * math.exp(-recoil_t * 10.0) + 92.0 * impulse
            horn_squash_x = 1.0 - 0.36 * math.exp(-recoil_t * 2.2) * math.cos(recoil_t * 10.0)
            horn_squash_y = 1.0 + 0.32 * math.exp(-recoil_t * 2.2) * math.cos(recoil_t * 10.0)
            arm1_pose = "dizzy"
            arm2_pose = "dizzy"
            arm_droop = smoothstep(18.60, 19.12, t)

            if 18.60 <= t < 19.10:
                impact_flash = 1.0 - (t - 18.60) / 0.50
                if 18.60 <= t < 18.65:
                    trigger("headbutt_impact_clang", 18.60)
                    trigger("boss_stunned_chirp", 19.0)

            # Reverse vacuum vortex begins spinning inside the horn
            if t >= 20.20:
                boss_vortex = smoothstep(20.20, 21.80, t)
                if 20.20 <= t < 20.25:
                    trigger("reverse_vortex_whine", 20.20)
        else:
            # Beat 6: Continued vortex until iris-out, arms remain limply drooped
            boss_stunned = True
            eye_state = "dizzy_x"
            boss_vortex = 1.0
            arm1_pose = "dizzy"
            arm2_pose = "dizzy"
            arm_droop = 1.0

        # -------------------------------------------------------------
        # 3. Note Critters Armada (3 critters with full birth, grounded shoe walk & stomp fade)
        # -------------------------------------------------------------
        # Critter 1: spat at 4.20s -> lands at 4.85s (x=840) -> walks to 720 -> stomped at 10.15s
        c1_stomp_t = 10.15
        c1_visible = (4.20 <= t < c1_stomp_t + 2.10)
        c1_squashed = (t >= c1_stomp_t)
        c1_in_air = False
        c1_fly_p = 0.0
        c1_walk_phase = 0.0
        c1_alpha = 1.0 - smoothstep(c1_stomp_t + 1.25, c1_stomp_t + 2.05, t) if c1_squashed else 1.0

        if not c1_visible:
            c1_x, c1_y = HORN_MOUTH_X, HORN_MOUTH_Y
        elif 4.20 <= t < 4.85:
            c1_in_air = True
            c1_fly_p = (t - 4.20) / 0.65
            c1_x = lerp(HORN_MOUTH_X, 840.0, c1_fly_p)
            c1_y = lerp(HORN_MOUTH_Y, piano_surface_y(840.0) - 24.0, c1_fly_p) - math.sin(c1_fly_p * math.pi) * 130.0
        elif 4.85 <= t < c1_stomp_t:
            p_w = (t - 4.85) / (c1_stomp_t - 4.85)
            c1_x = lerp(840.0, 720.0, p_w)
            c1_y = piano_surface_y(c1_x) - 24.0
            c1_walk_phase = (t - 4.85) * 14.0
        else:
            c1_x = 720.0
            c1_y = piano_surface_y(720.0) + 8.0

        # Critter 2: spat at 5.40s -> lands at 6.05s (x=980) -> walks to 890 -> stomped at 11.95s
        c2_stomp_t = 11.95
        c2_visible = (5.40 <= t < c2_stomp_t + 2.10)
        c2_squashed = (t >= c2_stomp_t)
        c2_in_air = False
        c2_fly_p = 0.0
        c2_walk_phase = 0.0
        c2_alpha = 1.0 - smoothstep(c2_stomp_t + 1.25, c2_stomp_t + 2.05, t) if c2_squashed else 1.0

        if not c2_visible:
            c2_x, c2_y = HORN_MOUTH_X, HORN_MOUTH_Y
        elif 5.40 <= t < 6.05:
            c2_in_air = True
            c2_fly_p = (t - 5.40) / 0.65
            c2_x = lerp(HORN_MOUTH_X, 980.0, c2_fly_p)
            c2_y = lerp(HORN_MOUTH_Y, piano_surface_y(980.0) - 24.0, c2_fly_p) - math.sin(c2_fly_p * math.pi) * 140.0
        elif 6.05 <= t < c2_stomp_t:
            p_w = (t - 6.05) / (c2_stomp_t - 6.05)
            c2_x = lerp(980.0, 890.0, p_w)
            c2_y = piano_surface_y(c2_x) - 24.0
            c2_walk_phase = (t - 6.05) * 14.0 + 1.8
        else:
            c2_x = 890.0
            c2_y = piano_surface_y(890.0) + 8.0

        # Critter 3: spat at 6.60s -> lands at 7.25s (x=1110) -> walks to 1050 -> stomped at 13.85s
        c3_stomp_t = 13.85
        c3_visible = (6.60 <= t < c3_stomp_t + 2.10)
        c3_squashed = (t >= c3_stomp_t)
        c3_in_air = False
        c3_fly_p = 0.0
        c3_walk_phase = 0.0
        c3_alpha = 1.0 - smoothstep(c3_stomp_t + 1.25, c3_stomp_t + 2.05, t) if c3_squashed else 1.0

        if not c3_visible:
            c3_x, c3_y = HORN_MOUTH_X, HORN_MOUTH_Y
        elif 6.60 <= t < 7.25:
            c3_in_air = True
            c3_fly_p = (t - 6.60) / 0.65
            c3_x = lerp(HORN_MOUTH_X, 1110.0, c3_fly_p)
            c3_y = lerp(HORN_MOUTH_Y, piano_surface_y(1110.0) - 24.0, c3_fly_p) - math.sin(c3_fly_p * math.pi) * 150.0
        elif 7.25 <= t < c3_stomp_t:
            p_w = (t - 7.25) / (c3_stomp_t - 7.25)
            c3_x = lerp(1110.0, 1050.0, p_w)
            c3_y = piano_surface_y(c3_x) - 24.0
            c3_walk_phase = (t - 7.25) * 14.0 + 3.2
        else:
            c3_x = 1050.0
            c3_y = piano_surface_y(1050.0) + 8.0

        # -------------------------------------------------------------
        # 4. Technicolor Soundwave Rings & Keyboard Coloring Radius
        # -------------------------------------------------------------
        soundwave_rings = []
        tc_ring_radius = 0.0

        if t >= c1_stomp_t:
            r1 = min(380.0, (t - c1_stomp_t) * 180.0)
            a1 = max(0.0, 1.0 - (t - c1_stomp_t) / 2.6)
            if a1 > 0.02:
                soundwave_rings.append({"cx": 720.0, "cy": piano_surface_y(720.0), "r": r1, "alpha": a1})
            tc_ring_radius = lerp(0.0, 420.0, smoothstep(c1_stomp_t, 11.40, t))

        if t >= c2_stomp_t:
            r2 = min(440.0, (t - c2_stomp_t) * 200.0)
            a2 = max(0.0, 1.0 - (t - c2_stomp_t) / 2.6)
            if a2 > 0.02:
                soundwave_rings.append({"cx": 890.0, "cy": piano_surface_y(890.0), "r": r2, "alpha": a2})
            tc_ring_radius = lerp(420.0, 880.0, smoothstep(c2_stomp_t, 13.20, t))

        if t >= c3_stomp_t:
            r3 = min(560.0, (t - c3_stomp_t) * 240.0)
            a3 = max(0.0, 1.0 - (t - c3_stomp_t) / 2.8)
            if a3 > 0.02:
                soundwave_rings.append({"cx": 1050.0, "cy": piano_surface_y(1050.0), "r": r3, "alpha": a3})
            tc_ring_radius = lerp(880.0, 1600.0, smoothstep(c3_stomp_t, 15.20, t))

        # -------------------------------------------------------------
        # 5. Token: Spinning Vinyl Record & Eighth Note (World 7 Collectible)
        # -------------------------------------------------------------
        token_visible = False
        token_x, token_y = 1045.0, 520.0
        token_r = 34.0
        token_rot = t * 3.5
        token_alpha = 0.0

        if 14.0 <= t < 15.65:
            token_visible = True
            if t < 15.15:
                token_alpha = smoothstep(14.0, 14.45, t)
                if 14.2 <= t < 14.3:
                    trigger("token_pop", 14.2)
            else:
                abs_u = smoothstep(15.15, 15.60, t)
                token_alpha = max(0.0, 1.0 - abs_u)
                token_x = lerp(1045.0, 1043.0, abs_u)
                token_y = lerp(520.0, 495.0, abs_u)
                token_r = 34.0 * (1.0 - 0.55 * abs_u)
                if 15.2 <= t < 15.3:
                    trigger("token_absorb", 15.2)

        # -------------------------------------------------------------
        # 6. Guiding Star ✦ State & Suction into Boss Horn
        # -------------------------------------------------------------
        star_visible = True
        star_x, star_y = 1205.0, 282.0
        star_r = 26.0
        star_rot = -0.12 + math.sin(t * 2.5) * 0.15

        if 21.0 <= t < 22.4:
            suck_p = smoothstep(21.0, 22.4, t)
            swirl_angle = suck_p * math.pi * 5.0
            cur_r = (1.0 - suck_p) * 210.0
            star_x = HORN_CENTER_X + cur_r * 0.5 * math.cos(swirl_angle)
            star_y = HORN_CENTER_Y - (1.0 - suck_p) * 198.0 + cur_r * 0.3 * math.sin(swirl_angle)
            star_r = 26.0 * (1.0 - suck_p * 0.75)
            star_rot = swirl_angle
            if 21.0 <= t < 21.05:
                trigger("star_sucked_in", 21.0)
        elif t >= 22.4:
            star_visible = False

        # -------------------------------------------------------------
        # 7. Protagonist Slime Choreography & Zero-Floating Contact Physics
        # -------------------------------------------------------------
        slime_visible = True
        slime_r = SLIME_BASE_R
        slime_squash_y = 1.0
        slime_tilt = 0.0
        slime_eye_mode = "pill"
        slime_look = (0.52, -0.15)
        slime_blink = 0.0
        pop_icon = None
        KEY_DIP = 14.0  # Exact vertical depression of piano key under grounded Slime

        if t < 1.2:
            slime_x = 340.0
            slime_foot_y = piano_surface_y(slime_x) + KEY_DIP
            slime_squash_y = 1.0
            slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
            slime_look = (0.0, 0.0)

        elif 1.2 <= t < 4.0:
            # Beat 1: Idle 132 BPM bounce & curious 3D look (6 exact half-cycles over 2.8s -> zero jump at t=4.0!)
            slime_x = 340.0
            surf_y = piano_surface_y(slime_x) + KEY_DIP
            b_phase = ((t - 1.2) / 2.8) * 6.0
            b_val = math.sin(b_phase * math.pi)
            if b_val >= 0.0:
                hop_h = b_val * 24.0
                slime_squash_y = 1.0 + b_val * 0.14
                slime_foot_y = surf_y - hop_h
                slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
            else:
                slime_squash_y = 1.0 + b_val * 0.22
                slime_foot_y = surf_y
                slime_y = surf_y - slime_r * slime_squash_y * 0.96

            if t < 2.0:
                p_look = smoothstep(1.2, 1.8, t)
                slime_look = (lerp(0.0, -0.55, p_look), 0.0)
            elif t < 2.7:
                p_c = (t - 2.0) / 0.7
                slime_look = (lerp(-0.55, 0.0, smoothstep(0.0, 1.0, p_c)), 0.0)
            else:
                p_r = (t - 2.7) / 1.1
                slime_look = (lerp(0.0, 0.55, smoothstep(0.0, 1.0, p_r)), lerp(0.0, -0.22, smoothstep(0.0, 1.0, p_r)))

        elif 4.0 <= t < 6.4:
            # Beat 2: 2 crisp targeted hops along the piano keys (340 -> 460 -> 580)
            if t < 5.2:
                u_hop = (t - 4.0) / 1.2
                hj = eval_targeted_jump(u_hop, 340.0, piano_surface_y(340.0) + KEY_DIP, 460.0, piano_surface_y(460.0) + KEY_DIP, arc_height=65.0)
            else:
                u_hop = (t - 5.2) / 1.2
                hj = eval_targeted_jump(u_hop, 460.0, piano_surface_y(460.0) + KEY_DIP, 580.0, piano_surface_y(580.0) + KEY_DIP, arc_height=65.0)
            slime_x = hj["x"]
            slime_foot_y = hj["y"]
            slime_squash_y = hj["squash_y"]
            slime_tilt = hj["tilt"]
            slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
            slime_look = (0.50, -0.10)
            if 4.05 <= t < 4.15:
                trigger("piano_step_1", 4.1)
            elif 5.25 <= t < 5.35:
                trigger("piano_step_2", 5.3)

        elif 6.4 <= t < 7.6:
            # Beat 2: Planted at x=580! Leans back, looks at marching critters, pop '?'
            slime_x = 580.0
            surf_y = piano_surface_y(slime_x) + KEY_DIP
            slime_squash_y = 0.92 - 0.08 * math.sin((t - 6.4) * (math.tau / 1.2))
            slime_tilt = -0.22 * math.sin(smoothstep(6.4, 7.6, t) * math.pi)
            slime_foot_y = surf_y
            slime_y = surf_y - slime_r * slime_squash_y * 0.96
            slime_look = (0.48, 0.35)
            slime_eye_mode = "wince" if t < 6.85 else "pill"
            pop_icon = {"type": "?", "alpha": smoothstep(6.6, 7.0, t) * (1.0 - smoothstep(7.4, 7.6, t))}
            if 6.45 <= t < 6.55:
                trigger("screech_brake", 6.5)
                trigger("question_pop", 6.8)

        elif 7.6 <= t < 8.8:
            # Beat 2: Pop '!', deep squash charge (> < effort!)
            slime_x = 580.0
            surf_y = piano_surface_y(slime_x) + KEY_DIP
            slime_eye_mode = "wince"
            slime_look = (0.55, -0.10)
            p_charge = smoothstep(7.6, 8.8, t)
            slime_squash_y = lerp(0.92, 0.58, p_charge)
            slime_tilt = 0.08 * p_charge
            slime_foot_y = surf_y
            slime_y = surf_y - slime_r * slime_squash_y * 0.96
            pop_icon = {"type": "!", "alpha": smoothstep(7.7, 8.0, t) * (1.0 - smoothstep(8.4, 8.7, t))}
            if 7.8 <= t < 7.9:
                trigger("idea_bell", 7.8)

        elif 8.8 <= t < 10.4:
            # Beat 3 - Stomp 1: High leap from 580 to 720, slams onto Note 1 at t=10.15s
            if t < c1_stomp_t:
                sub_p = (t - 8.8) / (c1_stomp_t - 8.8)
                slime_x = lerp(580.0, 720.0, smoothstep(0.0, 1.0, sub_p))
                surf_y = lerp(piano_surface_y(580.0), piano_surface_y(720.0), sub_p) + KEY_DIP
                arc_h = math.sin(sub_p * math.pi) * 215.0
                slime_squash_y = lerp(0.58, 0.92, sub_p) + 0.34 * math.sin(sub_p * math.pi)
                slime_tilt = 0.14 * math.cos(sub_p * math.pi)
                slime_foot_y = surf_y - arc_h
                slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
                slime_look = (0.0, 0.52) if sub_p >= 0.40 else (0.45, 0.25)
            else:
                squash_p = (t - c1_stomp_t) / (10.4 - c1_stomp_t)
                slime_x = 720.0
                surf_y = piano_surface_y(720.0) + KEY_DIP + 6.0 * math.sin(squash_p * math.pi)
                slime_squash_y = 0.50 + 0.36 * smoothstep(0.0, 1.0, squash_p)
                slime_tilt = 0.0
                slime_foot_y = surf_y
                slime_y = surf_y - slime_r * slime_squash_y * 0.96
                slime_eye_mode = "wince"
                slime_look = (0.50, 0.0)
            if 8.8 <= t < 8.9:
                trigger("jump_anticipation", 8.8)
            elif c1_stomp_t <= t < c1_stomp_t + 0.05:
                trigger("stomp_splat", 10.2)
                trigger("color_ring_1", 10.2)

        elif 10.4 <= t < 12.2:
            # Beat 3 - Stomp 2: Rebound leap from 720 to 890, slams onto Note 2 at t=11.95s
            if t < c2_stomp_t:
                sub_p = (t - 10.4) / (c2_stomp_t - 10.4)
                slime_x = lerp(720.0, 890.0, smoothstep(0.0, 1.0, sub_p))
                surf_y = lerp(piano_surface_y(720.0), piano_surface_y(890.0), sub_p) + KEY_DIP
                arc_h = math.sin(sub_p * math.pi) * 235.0
                slime_squash_y = 0.86 + 0.40 * math.sin(sub_p * math.pi)
                slime_tilt = 0.16 * math.cos(sub_p * math.pi)
                slime_foot_y = surf_y - arc_h
                slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
                slime_look = (0.0, 0.52) if sub_p >= 0.40 else (0.50, 0.20)
            else:
                squash_p = (t - c2_stomp_t) / (12.2 - c2_stomp_t)
                slime_x = 890.0
                surf_y = piano_surface_y(890.0) + KEY_DIP + 6.0 * math.sin(squash_p * math.pi)
                slime_squash_y = 0.48 + 0.38 * smoothstep(0.0, 1.0, squash_p)
                slime_tilt = 0.0
                slime_foot_y = surf_y
                slime_y = surf_y - slime_r * slime_squash_y * 0.96
                slime_eye_mode = "wince"
                slime_look = (0.52, -0.05)
            if 10.4 <= t < 10.5:
                trigger("jump_anticipation", 10.4)
            elif c2_stomp_t <= t < c2_stomp_t + 0.05:
                trigger("stomp_splat", 12.0)
                trigger("color_ring_2", 12.0)

        elif 12.2 <= t < 14.2:
            # Beat 3 - Stomp 3: Mighty leap from 890 to 1050, stomps Lead Note at t=13.85s
            if t < c3_stomp_t:
                sub_p = (t - 12.2) / (c3_stomp_t - 12.2)
                slime_x = lerp(890.0, 1050.0, smoothstep(0.0, 1.0, sub_p))
                surf_y = lerp(piano_surface_y(890.0), piano_surface_y(1050.0), sub_p) + KEY_DIP
                arc_h = math.sin(sub_p * math.pi) * 250.0
                slime_squash_y = 0.86 + 0.42 * math.sin(sub_p * math.pi)
                slime_tilt = 0.18 * math.cos(sub_p * math.pi)
                slime_foot_y = surf_y - arc_h
                slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
                slime_look = (0.0, 0.52) if sub_p >= 0.40 else (0.55, 0.15)
            else:
                squash_p = (t - c3_stomp_t) / (14.2 - c3_stomp_t)
                slime_x = 1050.0
                surf_y = piano_surface_y(1050.0) + KEY_DIP + 6.0 * math.sin(squash_p * math.pi)
                slime_squash_y = 0.46 + 0.50 * smoothstep(0.0, 1.0, squash_p)
                slime_tilt = 0.0
                slime_foot_y = surf_y
                slime_y = surf_y - slime_r * slime_squash_y * 0.96
                slime_eye_mode = "wince"
                slime_look = (0.55, -0.10)
            if 12.2 <= t < 12.3:
                trigger("jump_anticipation", 12.2)
            elif c3_stomp_t <= t < c3_stomp_t + 0.05:
                trigger("stomp_splat", 13.9)
                trigger("color_ring_3", 13.9)

        elif 14.2 <= t < 16.35:
            # Beat 4: Quick crouch (14.20..14.65s) -> Crisp parabolic hop (14.65..15.80s) absorbing Token at apex
            # -> Planted elastic landing cushion on keys at x=1040 (15.80..16.35s)!
            if t < 14.65:
                c_u = (t - 14.2) / 0.45
                slime_x = 1050.0
                surf_y = piano_surface_y(1050.0) + KEY_DIP
                slime_squash_y = lerp(0.96, 0.66, smoothstep(0.0, 1.0, c_u))
                slime_tilt = 0.0
                slime_foot_y = surf_y
                slime_y = surf_y - slime_r * slime_squash_y * 0.96
                slime_look = (0.0, -0.45)
            elif t < 15.80:
                air_u = (t - 14.65) / 1.15
                slime_x = lerp(1050.0, 1040.0, smoothstep(0.0, 1.0, air_u))
                surf_y = piano_surface_y(slime_x) + KEY_DIP
                arc_h = math.sin(air_u * math.pi) * 195.0
                slime_squash_y = 0.92 + 0.28 * math.sin(air_u * math.pi)
                slime_tilt = 0.0
                slime_foot_y = surf_y - arc_h
                slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
                slime_eye_mode = "happy" if t >= 15.18 else "pill"
                slime_look = (0.0, -0.20)
            else:
                land_u = (t - 15.80) / 0.55
                slime_x = 1040.0
                surf_y = piano_surface_y(1040.0) + KEY_DIP + 5.0 * math.sin(land_u * math.pi)
                slime_squash_y = 1.0 - 0.34 * math.sin(land_u * math.pi)
                slime_tilt = 0.0
                slime_foot_y = surf_y
                slime_y = surf_y - slime_r * slime_squash_y * 0.96
                slime_eye_mode = "happy"
                slime_look = (0.45, -0.25)

        elif 16.35 <= t < 17.8:
            # Beat 4: Anticipation deep squash charge planted on keys at x=1040, locking onto Boss forehead (> < effort!)
            slime_x = 1040.0
            surf_y = piano_surface_y(slime_x) + KEY_DIP
            p_squash = smoothstep(16.35, 17.8, t)
            slime_squash_y = lerp(1.0, 0.54, p_squash)
            slime_tilt = 0.14 * p_squash
            slime_foot_y = surf_y
            slime_y = surf_y - slime_r * slime_squash_y * 0.96
            slime_eye_mode = "wince"
            slime_look = (0.60, -0.45)
            if 16.6 <= t < 16.7:
                trigger("jump_anticipation", 16.6)

        elif 17.8 <= t < 18.6:
            # Beat 4: Rocket comet launch streaking toward Boss horn forehead (1215, 395)!
            # Smoothly stretches from 0.54 -> 1.48 so foot_y never clips below the piano key!
            rocket_p = (t - 17.8) / 0.80
            ease_r = smoothstep(0.0, 0.15, rocket_p) * 0.25 + rocket_p * 0.75
            surf_y = piano_surface_y(1040.0) + KEY_DIP
            start_y = surf_y - slime_r * 0.54 * 0.96
            slime_x = lerp(1040.0, BOSS_FOREHEAD_X, ease_r)
            slime_y = lerp(start_y, BOSS_FOREHEAD_Y, ease_r)
            slime_squash_y = lerp(0.54, 1.48, smoothstep(0.0, 0.22, rocket_p))
            slime_tilt = lerp(0.14, 0.48, smoothstep(0.0, 0.22, rocket_p))
            slime_foot_y = slime_y + slime_r * slime_squash_y * 0.96
            slime_eye_mode = "pill"
            slime_look = (0.60, -0.45)
            if 17.8 <= t < 17.85:
                trigger("rocket_launch", 17.8)

        elif 18.6 <= t < 20.05:
            # Beat 4/5: Headbutt CLANG impact at 18.60s -> Parabolic Backflip Rebound -> Planted Landing at x=960!
            target_surf_y = piano_surface_y(960.0) + KEY_DIP

            if t < 18.72:
                # 0.12s Hit-Stop Compression directly against Boss's recoiling forehead!
                hit_u = (t - 18.60) / 0.12
                slime_x = lerp(BOSS_FOREHEAD_X, BOSS_FOREHEAD_X + 12.0, hit_u)
                slime_y = BOSS_FOREHEAD_Y
                slime_squash_y = 0.50
                slime_tilt = 0.48
                slime_foot_y = slime_y + slime_r * slime_squash_y * 0.96
                slime_eye_mode = "wince"
            elif t < 19.78:
                # True parabolic 360-deg backflip arc in mid-air from forehead (1227) to piano keys (960)
                air_u = (t - 18.72) / (19.78 - 18.72)
                slime_x = lerp(BOSS_FOREHEAD_X + 12.0, 960.0, air_u)
                foot_start = BOSS_FOREHEAD_Y + slime_r * 0.50 * 0.96
                foot_end = target_surf_y
                arc_h = 115.0 * 4.0 * air_u * (1.0 - air_u)
                slime_foot_y = lerp(foot_start, foot_end, air_u) - arc_h
                slime_squash_y = 1.0 + 0.18 * math.sin(air_u * math.pi)
                slime_tilt = 0.48 * (1.0 - air_u) - air_u * math.tau
                slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
                slime_eye_mode = "pill"
            else:
                # Planted elastic landing cushion on piano keys at x=960 (ZERO horizontal sliding!)
                land_u = (t - 19.78) / (20.05 - 19.78)
                slime_x = 960.0
                slime_foot_y = target_surf_y + 6.0 * math.sin(land_u * math.pi)
                slime_squash_y = 1.0 - 0.34 * math.sin(land_u * math.pi)
                slime_tilt = 0.0
                slime_y = slime_foot_y - slime_r * slime_squash_y * 0.96
                slime_eye_mode = "happy"
                if 19.78 <= t < 19.83:
                    trigger("rebound_landing", 19.80)

            slime_look = (0.55, -0.20)

        elif 20.05 <= t < 22.8:
            # Beat 5: SOLIDLY STANDING ON PIANO KEYS AT X=960!
            # Watching Boss horn spasm and Guiding Star ✦ get sucked into vortex!
            slime_x = 960.0
            surf_y = piano_surface_y(slime_x) + KEY_DIP
            b = math.sin((t - 20.05) * (132.0 / 60.0) * math.pi)
            slime_squash_y = 1.0 - 0.07 * b
            slime_tilt = 0.0
            slime_foot_y = surf_y
            slime_y = surf_y - slime_r * slime_squash_y * 0.96
            slime_look = (0.58, -0.22)
            slime_eye_mode = "happy" if t < 21.3 else "pill"

            if 22.2 <= t < 22.8:
                # Star swallowed! Pop '!' above head
                pop_icon = {"type": "!", "alpha": 1.0}
                slime_eye_mode = "wince"

        elif 22.8 <= t < 23.0:
            # Pre-dive crouch charge on piano keys (> < effort!)
            p_cr = (t - 22.8) / 0.20
            slime_x = 960.0
            surf_y = piano_surface_y(slime_x) + KEY_DIP
            slime_squash_y = lerp(1.0, 0.60, p_cr)
            slime_tilt = 0.12
            slime_foot_y = surf_y
            slime_y = surf_y - slime_r * slime_squash_y * 0.96
            slime_eye_mode = "wince"
            slime_look = (0.60, -0.25)

        elif 23.0 <= t < 24.2:
            # Beat 6: Leaps from keys and dives into Boss horn mouth (1200, 480)!
            dive_p = smoothstep(23.0, 24.2, t)
            surf_y = piano_surface_y(960.0) + KEY_DIP
            slime_x = lerp(960.0, HORN_CENTER_X, dive_p)
            slime_y = lerp(surf_y - slime_r * 0.60, HORN_CENTER_Y, dive_p) - math.sin(dive_p * math.pi) * 80.0
            slime_squash_y = lerp(0.60, 1.48, min(1.0, dive_p * 1.5))
            slime_tilt = lerp(0.12, 0.52, dive_p)
            slime_r = SLIME_BASE_R * (1.0 - dive_p * 0.65)
            slime_foot_y = slime_y + slime_r * slime_squash_y * 0.96
            slime_look = (0.60, -0.20)
            if 23.0 <= t < 23.05:
                trigger("horn_dive_whoosh", 23.0)
        else:
            # Beat 6: Slime fully inside horn, invisible
            slime_visible = False
            slime_x = HORN_CENTER_X
            slime_y = HORN_CENTER_Y
            slime_foot_y = HORN_CENTER_Y

        # -------------------------------------------------------------
        # 8. 1930s Circular Black Iris-Out Transition (24.2s - 26.0s)
        # -------------------------------------------------------------
        iris_out_active = (t >= 24.2)
        iris_out_radius = 1600.0
        if iris_out_active:
            p_iris = smoothstep(24.2, 26.0, t)
            iris_out_radius = max(0.0, 1600.0 * (1.0 - p_iris))
            if 24.2 <= t < 24.25:
                trigger("jazz_finale_cadence", 24.2)
                trigger("iris_out_thump", 24.2)

        # Assemble Snapshot Frame State
        frame_state = {
            "frame_idx": frame_idx,
            "t": t,
            "beat": beat,
            "countdown_active": countdown_active,
            "countdown_num": countdown_num,
            "lights_on": lights_on,
            "curtain_open_prog": curtain_open_prog,
            "curtain_bounce_dy": curtain_bounce_dy,
            "film_seed": 1934 + frame_idx,
            "slime": {
                "visible": slime_visible,
                "x": slime_x,
                "y": slime_y,
                "foot_y": slime_foot_y,
                "radius": slime_r,
                "squash_y": slime_squash_y,
                "tilt": slime_tilt,
                "eye_mode": slime_eye_mode,
                "look": slime_look,
                "blink": slime_blink,
            },
            "pop_icon": pop_icon,
            "boss": {
                "x": BOSS_X,
                "y": BOSS_Y,
                "scale": boss_scale,
                "bounce_phase": boss_bounce,
                "arm_action": 1.0,
                "stunned": boss_stunned,
                "recoil_angle": boss_recoil,
                "vortex_strength": boss_vortex,
                "eye_state": eye_state,
                "cab_squash_y": cab_squash_y,
                "foot_tap_angle": foot_tap_angle,
                "record_rot": record_rot,
                "crank_rot": crank_rot,
                "neck_lean_x": neck_lean_x,
                "neck_stretch_y": neck_stretch_y,
                "horn_squash_x": horn_squash_x,
                "horn_squash_y": horn_squash_y,
                "tongue_wag": tongue_wag,
                "inhale_stream": inhale_stream,
                "spit_blast": spit_blast,
                "impact_flash": impact_flash,
                "arm1_pose": arm1_pose,
                "arm2_pose": arm2_pose,
                "arm_droop": arm_droop,
            },
            "critters": {
                "critter_1": {
                    "visible": c1_visible,
                    "x": c1_x,
                    "y": c1_y,
                    "squashed": c1_squashed,
                    "in_air": c1_in_air,
                    "fly_p": c1_fly_p,
                    "walk_phase": c1_walk_phase,
                    "stomp_time": c1_stomp_t,
                    "alpha": c1_alpha,
                },
                "critter_2": {
                    "visible": c2_visible,
                    "x": c2_x,
                    "y": c2_y,
                    "squashed": c2_squashed,
                    "in_air": c2_in_air,
                    "fly_p": c2_fly_p,
                    "walk_phase": c2_walk_phase,
                    "stomp_time": c2_stomp_t,
                    "alpha": c2_alpha,
                },
                "critter_3": {
                    "visible": c3_visible,
                    "x": c3_x,
                    "y": c3_y,
                    "squashed": c3_squashed,
                    "in_air": c3_in_air,
                    "fly_p": c3_fly_p,
                    "walk_phase": c3_walk_phase,
                    "stomp_time": c3_stomp_t,
                    "alpha": c3_alpha,
                },
            },
            "tc_ring_radius": tc_ring_radius,
            "soundwave_rings": soundwave_rings,
            "token": {
                "visible": token_visible,
                "x": token_x,
                "y": token_y,
                "r": token_r,
                "rot": token_rot,
                "alpha": token_alpha,
            },
            "guiding_star": {
                "visible": star_visible,
                "x": star_x,
                "y": star_y,
                "r": star_r,
                "rot": star_rot,
            },
            "iris_out": {
                "active": iris_out_active,
                "center": (HORN_CENTER_X, HORN_CENTER_Y),
                "radius": iris_out_radius,
            },
        }
        frames_state.append(frame_state)

    return frames_state, audio_events

if __name__ == "__main__":
    states, events = run_simulation()
    print(f"Simulation test passed! Generated {len(states)} frames and {len(events)} audio events.")
