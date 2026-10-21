"""
World 04 · 水墨宣纸千里长卷 (Song-Dynasty Ink-Wash Landscape Scroll)
Physics & Act-State Simulation Engine (30fps, 28.0s = 840 frames)

 Upgraded Choreography & Physics:
  1. True Chase Distance for Guiding Star ✦ (追逐的距离感):
     - The Guiding Star ✦ always stays 320px ~ 620px ahead of the Slime, darting
       forward before the Slime jumps so it is NEVER accidentally overlapped during
       normal traversal!
  2. Act IV Complete Taiji Yin-Yang & Lotus Sequence (太极黑白两仪 · 撞击黑洞回弹 · 升莲开莲吃星):
     - 14.80s ~ 15.85s: The swirling Ink Black Hole (焦墨黑洞旋涡) at (4140, 720) sucks in
       and swallows the Guiding Star ✦! Slime on Pad 4 (3760, 710) gasps (`> <`, `!`).
     - 15.85s ~ 17.15s: Slime squats into a deep effort charge (`> <` wince) on Pad 4,
       channeling a grand rotating Black-and-White Yin-Yang Taiji Diagram (黑白两仪太极图)!
     - 17.15s ~ 17.95s: Wrapped in the spinning Yin-Yang sphere, Slime launches and
       slams directly into the Black Hole core (4140, 715)!
     - 17.95s ~ 18.85s: Heavy Taiji Impact (`> <` wince + camera shake + Yin-Yang shockwave
       + towering water splashes & concentric water ripples), and Slime REBOUNDS along a
       crisp gravity parabola back onto Pad 4 (3760, 710)!
     - 18.50s ~ 19.60s: Giant closed Ink Lotus Bud RISES out of the purified vortex water
       at (4140, 720) with cascading water splashes & ripples (莲花升起)!
     - 19.60s ~ 20.65s: The Giant Lotus OPENS its 9 petal rings (莲花打开), revealing the
       glowing Star / Cinnabar Ink-Star Token inside its golden seedpod heart!
     - 20.65s ~ 22.10s: Slime leaps from Pad 4 onto the open Giant Lotus Throne (4140, 685)
       and EATS/ABSORBS the Star Token inside the lotus (吃掉星星), bursting with sustained
       joy (`happy` `^ ^` / `sparkle` `✦ ✦`), while the freed Guiding Star ✦ dashes ahead
       up the Cloud-Mountain Sanctuary!
  3. Natural Eye Expression & Effort Logic:
     - Normal jumping & walking use `"pill"` (open capsule eyes looking at target).
     - Pre-jump deep charge (`蓄力用力`), heavy collision impact, or startled braking use
       `"wince"` (`> <`).
     - `"happy"` (`^ ^`) is a sustained emotional state triggered ONLY by joyful events
       (watching the Master Brush complete the bridge 9.15s~10.20s, and after eating the
       rescued star inside the Giant Lotus 21.35s~23.40s), never flickering on every hop!
"""

import math
from typing import Dict, List, Tuple, Any

from slime_engine import (
    SpringDamper1D,
    SpringDamper2D,
    eval_continuous_hop_chain,
    eval_targeted_jump,
)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * u


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 <= edge0:
        return 1.0 if x >= edge1 else 0.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

# ==============================================================================
# WORLD CONSTANTS & GEOMETRY HELPERS (Continuous 5600x1280 Scroll Coordinates)
# ==============================================================================
FPS = 30
DURATION = 28.0
TOTAL_FRAMES = int(FPS * DURATION)  # 840 frames

WORLD_W = 5600.0
WORLD_H = 1280.0
SLIME_R = 75.0


def bridge_deck_y(x: float) -> float:
    """
    Exact upper stone deck curve of the Song-Dynasty Stone Arch Bridge
    spanning x in [1480.0, 2520.0], with arch crown at (2000.0, 555.0).
    """
    u = clamp((x - 2000.0) / 520.0, -1.0, 1.0)
    return 555.0 + 165.0 * (u * u)


def foot_y_to_center_y(foot_y: float, radius: float, squash_y: float, grounded: bool = True) -> float:
    """
    Converts the Slime's exact bottom contact point `foot_y` into its center `cy`.
    In `style_04_inkwash.draw_slime`, when grounded, bottom vertex is at `cy + r * squash_y * 0.92`.
    """
    contact_factor = 0.91 if grounded else 0.93
    return foot_y - radius * squash_y * contact_factor


# ==============================================================================
# MAIN 840-FRAME SIMULATION ENGINE
# ==============================================================================
def run_simulation() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    dt = 1.0 / FPS
    frames_state: List[Dict[str, Any]] = []
    audio_events: List[Dict[str, Any]] = []

    # 2nd-Order Spring-Damper Filters for C^2 Physical Continuity
    squash_damper = SpringDamper1D(x0=1.0, freq=4.5, zeta=0.68)
    tilt_damper = SpringDamper1D(x0=0.0, freq=3.8, zeta=0.74)
    look_damper = SpringDamper2D(x0=-0.52, y0=-0.15, freq=4.2, zeta=0.82)
    cam_damper = SpringDamper2D(x0=960.0, y0=540.0, freq=2.2, zeta=0.88)

    # 4 Hero Splashed-Ink Lotus Pads across Zone 3 (x = 2740 .. 3760)
    lotus_pad_defs = [
        {"x": 2740.0, "y": 715.0, "scale": 1.12, "seed": 1, "note": 293.66},  # Re (D4)
        {"x": 3080.0, "y": 730.0, "scale": 1.18, "seed": 2, "note": 329.63},  # Mi (E4)
        {"x": 3420.0, "y": 705.0, "scale": 1.14, "seed": 5, "note": 392.00},  # Sol (G4)
        {"x": 3760.0, "y": 715.0, "scale": 1.24, "seed": 7, "note": 440.00},  # La (A4)
    ]

    # 3 Cloud-Crag Terraces in Zone 4 (x = 4450 .. 5010)
    cliff_ledges = [
        {"x": 4450.0, "y": 590.0, "w": 210.0, "h": 220.0},
        {"x": 4730.0, "y": 495.0, "w": 225.0, "h": 275.0},
        {"x": 5010.0, "y": 410.0, "w": 255.0, "h": 335.0},  # Summit Pine Altar
    ]

    # Pre-scheduled Foley & Musical Audio Events
    scheduled_sfx = [
        (0.08, "feibai_sweep", {"dur": 0.85, "gain": 0.88}),
        (0.95, "ink_drop_condense", {"freq": 523.25, "gain": 0.78}),
        (1.65, "bamboo_land", {"gain": 0.72}),
        (3.20, "bamboo_creak_bend", {"dur": 0.95, "gain": 0.85}),
        (4.20, "bamboo_catapult_twang", {"freq": 196.0, "gain": 0.95}),
        (5.45, "stone_bridge_step", {"freq": 261.63, "gain": 0.75}),
        (6.05, "stone_bridge_step", {"freq": 293.66, "gain": 0.75}),
        (6.75, "skid_brake_chasm", {"gain": 0.80}),
        (7.00, "guqin_question_harmonic", {"freq": 392.00, "gain": 0.75}),
        (7.70, "chime_idea_spark", {"freq": 1046.50, "gain": 0.88}),
        (8.58, "jump_whoosh", {"gain": 0.75}),
        (8.82, "brush_ferrule_ding", {"freq": 1318.51, "gain": 0.96}),
        (8.98, "master_brush_sweep_bridge", {"dur": 0.75, "gain": 0.92}),
        (9.75, "stone_bridge_step", {"freq": 329.63, "gain": 0.72}),
        # Act III: 4 Pentatonic Lotus Pad Hops + Leaping Cinnabar Koi
        (11.20, "lotus_water_plop", {"freq": 293.66, "gain": 0.86}),
        (11.35, "koi_breach_splash", {"gain": 0.78}),
        (12.45, "lotus_water_plop", {"freq": 329.63, "gain": 0.86}),
        (13.10, "koi_breach_splash", {"gain": 0.82}),
        (13.70, "lotus_water_plop", {"freq": 392.00, "gain": 0.88}),
        (14.95, "lotus_water_plop", {"freq": 440.00, "gain": 0.90}),
        # Act IV: Black Hole Swallows Star -> Taiji Yin-Yang Strike -> Rebound -> Lotus Rises & Opens -> Eat Star
        (15.10, "vortex_dark_rumble", {"dur": 2.6, "gain": 0.90}),
        (15.55, "guqin_question_harmonic", {"freq": 220.00, "gain": 0.85}),
        (16.10, "taiji_hum_chord", {"freq": 261.63, "gain": 0.92}),
        (17.15, "taiji_spin_whoosh", {"dur": 0.85, "gain": 0.95}),
        (17.95, "lotus_water_plop", {"freq": 146.83, "gain": 1.00}),  # Heavy Taiji Impact!
        (18.02, "koi_breach_splash", {"gain": 1.00}),
        (18.60, "lotus_bloom_glissando", {"dur": 1.85, "gain": 0.96}),
        (18.85, "lotus_water_plop", {"freq": 392.00, "gain": 0.82}),  # Rebound land on Pad 4
        (21.35, "token_collect_chime", {"freq": 1174.66, "gain": 0.98}),  # Eat rescued Star in Giant Lotus!
        # Act V & VI: Cloud-Mountain Cliff Hops & Final Cinnabar Seal Stamp
        (22.65, "rock_ledge_step", {"freq": 440.00, "gain": 0.80}),
        (23.55, "rock_ledge_step", {"freq": 523.25, "gain": 0.84}),
        (24.45, "rock_ledge_step", {"freq": 587.33, "gain": 0.88}),
        (25.35, "final_soar_whoosh", {"dur": 0.85, "gain": 0.90}),
        (26.15, "seal_enter_sparkle", {"freq": 1567.98, "gain": 0.92}),
        (26.75, "cinnabar_seal_heavy_slam", {"gain": 1.00}),
    ]
    audio_events = list(scheduled_sfx)

    trail_history: List[Tuple[float, float]] = []

    for f in range(TOTAL_FRAMES):
        t = f * dt

        # -------------------------------------------------------------
        # 1. Direct Vertical Fall Entry from World 03 (No Horizontal Feibai Line!)
        # -------------------------------------------------------------
        scroll_reveal = 1.0

        # -------------------------------------------------------------
        # 2. Hero Bamboo Stalk Flexion & Vibration (Zone 1: x = 755, y = 673)
        #    Slime falls straight down from top of frame (0.00 ~ 0.90s) and lands at t = 0.90s!
        # -------------------------------------------------------------
        bamboo_bend = 0.0
        bamboo_vib = 0.0
        if 0.90 <= t < 3.25:
            dt_land = t - 0.90
            bamboo_bend = 0.28 * (1.0 - math.exp(-dt_land * 6.5))
            bamboo_vib = math.exp(-dt_land * 3.8) * math.sin(dt_land * 18.0) * 0.22
        elif 3.25 <= t < 4.20:
            p_ch = smoothstep(3.25, 4.18, t)
            bamboo_bend = 0.28 + p_ch * 0.74
        elif 4.20 <= t < 6.80:
            dt_vib = t - 4.20
            bamboo_bend = 0.0
            bamboo_vib = math.exp(-dt_vib * 4.2) * math.cos(dt_vib * 26.0) * 0.48

        b_dx4 = bamboo_bend * 28.0 + bamboo_vib * 22.0
        b_dy4 = bamboo_bend * 130.0 - bamboo_vib * 25.0
        tip_x = 755.0 + b_dx4 * 0.85
        tip_y = 673.0 + b_dy4 * 0.90

        # -------------------------------------------------------------
        # 3. Suspended Master Calligraphic Brush & Bridge Painting (Zone 2)
        # -------------------------------------------------------------
        brush_state = "idle"
        brush_x = 2020.0
        brush_y = -280.0
        brush_ang = -0.22
        bridge_drawn_prog = 0.0

        if t < 6.80:
            brush_state = "idle"
            brush_y = -280.0
        elif 6.80 <= t < 7.80:
            p_desc = smoothstep(6.80, 7.75, t)
            brush_state = "idle"
            brush_y = lerp(-260.0, 185.0, p_desc)
            brush_ang = lerp(-0.42, -0.22, p_desc)
        elif 7.80 <= t < 8.80:
            brush_state = "idle"
            brush_y = 185.0 + math.sin(t * 2.4) * 6.0
            brush_ang = -0.22 + math.sin(t * 1.8) * 0.04
        elif 8.80 <= t < 8.98:
            brush_state = "hit"
            u_hit = (t - 8.80) / 0.18
            brush_y = 185.0 - math.sin(u_hit * math.pi) * 32.0
            brush_ang = -0.22 + math.sin(u_hit * math.pi) * 0.34
        elif 8.98 <= t < 9.68:
            brush_state = "painting"
            p_br = clamp((t - 8.98) / 0.68, 0.0, 1.0)
            bridge_drawn_prog = smoothstep(0.0, 0.96, p_br)
            cur_bx = lerp(2000.0, 2520.0, bridge_drawn_prog)
            target_tip_y = bridge_deck_y(cur_bx)
            brush_x = cur_bx
            brush_y = target_tip_y - 180.0 + math.sin(p_br * math.pi * 3.0) * 18.0
            brush_ang = 0.16 + math.cos(p_br * math.pi * 3.0) * 0.28
        else:
            brush_state = "retracted"
            p_ret = smoothstep(9.68, 10.55, t)
            brush_x = lerp(2520.0, 2600.0, p_ret)
            brush_y = lerp(bridge_deck_y(2520.0) - 180.0, -320.0, p_ret)
            brush_ang = lerp(0.16, -0.35, p_ret)
            bridge_drawn_prog = 1.0

        # -------------------------------------------------------------
        # 4. Lotus Pads Dynamics & Water Splashes (Zone 3: Dipping & Ripples)
        # -------------------------------------------------------------
        lotus_pads_state = []
        pad_land_times = [11.20, 12.45, 13.70, 14.95]
        for idx, pdef in enumerate(lotus_pad_defs):
            lt = pad_land_times[idx]
            pad_dip = 0.0
            ripple_r = 0.0
            ripple_alpha = 0.0
            splash_age = -1.0
            if t >= lt:
                dt_hop = t - lt
                if dt_hop < 2.2:
                    pad_dip = math.exp(-dt_hop * 4.5) * math.sin(dt_hop * 20.0) * 20.0
                    ripple_r = 40.0 + dt_hop * 165.0
                    ripple_alpha = max(0.0, 1.0 - dt_hop / 2.0)
                if dt_hop < 0.75:
                    splash_age = dt_hop

            # Secondary rebound landing on Pad 4 at t = 18.85s after Taiji strike!
            if idx == 3 and t >= 18.85:
                dt_reb = t - 18.85
                if dt_reb < 1.8:
                    pad_dip += math.exp(-dt_reb * 4.8) * math.sin(dt_reb * 20.0) * 22.0
                    ripple_r = max(ripple_r, 40.0 + dt_reb * 175.0)
                    ripple_alpha = max(ripple_alpha, max(0.0, 1.0 - dt_reb / 1.8))
                if dt_reb < 0.75:
                    splash_age = dt_reb

            if idx == 3 and ((14.95 <= t < 17.15) or (18.85 <= t < 20.65)):
                pad_dip += 5.0 * math.sin(t * 4.2)
                if ripple_alpha < 0.35:
                    ripple_r = 95.0 + (t * 65.0) % 120.0
                    ripple_alpha = 0.42

            lotus_pads_state.append({
                "x": pdef["x"],
                "y": pdef["y"] + pad_dip,
                "base_y": pdef["y"],
                "dip": pad_dip,
                "ripple_r": ripple_r,
                "ripple_alpha": ripple_alpha,
                "splash_age": splash_age,
                "scale": pdef["scale"],
                "seed": pdef["seed"],
                "note": pdef["note"],
            })

        # -------------------------------------------------------------
        # 5. Cinnabar Koi Leaping Arc (Zone 3: 10.90s ~ 14.90s)
        # -------------------------------------------------------------
        koi_state = []
        if 10.90 <= t <= 14.90:
            kp = (t - 10.90) / 4.00
            # Lead Cinnabar Koi leaps well ahead of Slime (x: 2880 -> 3960)
            k1_x = lerp(2880.0, 3960.0, kp)
            wave_u = (kp * 2.0) % 1.0
            k1_y = 685.0 - math.sin(wave_u * math.pi) * 155.0
            k1_ang = clamp(math.atan2(-math.cos(wave_u * math.pi) * 155.0 * math.pi, 520.0), -0.62, 0.62)
            koi_state.append({
                "x": k1_x,
                "y": k1_y,
                "ang": k1_ang,
                "length": 168.0,
                "is_lead": True,
                "wave_u": wave_u,
                "alpha": smoothstep(0.0, 0.08, kp) * (1.0 - smoothstep(0.90, 1.0, kp)),
            })

        # -------------------------------------------------------------
        # 6. Act IV: Black Hole Whirlpool -> Taiji Impact -> Rising & Opening Giant Lotus
        # -------------------------------------------------------------
        vortex_center_x = 4140.0
        vortex_center_y = 720.0
        vortex_rot = (t * 4.8) % math.tau
        vortex_corruption = 0.0
        vortex_eyes = 0.0
        vortex_suck_prog = 0.0  # 0 -> 1 as black hole sucks in the Guiding Star (14.85 ~ 15.75s)
        taiji_impact_age = -1.0  # > 0 after t = 17.95s heavy Taiji slam!
        lotus_rise = 0.0  # 0 -> 1 during 18.50 ~ 19.60s (莲花升起)
        lotus_open = 0.0  # 0 -> 1 during 19.55 ~ 20.65s (莲花打开)
        vortex_active = False

        if 14.50 <= t < 17.95:
            vortex_active = True
            vortex_corruption = smoothstep(14.50, 15.30, t)
            vortex_eyes = smoothstep(15.00, 15.70, t)
            if 14.85 <= t <= 15.85:
                vortex_suck_prog = clamp((t - 14.85) / 0.90, 0.0, 1.0)
        elif 17.95 <= t < 20.70:
            vortex_active = True
            taiji_impact_age = t - 17.95
            # Black hole shatters and dissolves rapidly after the t=17.95s Taiji strike!
            vortex_corruption = max(0.0, 1.0 - smoothstep(17.95, 18.85, t))
            vortex_eyes = max(0.0, 1.0 - (t - 17.95) * 3.5)
            # Giant closed Lotus Bud rises out of the water (18.45s ~ 19.55s)
            lotus_rise = smoothstep(18.45, 19.55, t)
            # Giant Lotus unfurls its petals (19.50s ~ 20.65s)
            lotus_open = smoothstep(19.50, 20.65, t)
        elif t >= 20.70:
            vortex_active = True
            if t < 21.80:
                taiji_impact_age = t - 17.95
            vortex_corruption = 0.0
            vortex_eyes = 0.0
            lotus_rise = 1.0
            lotus_open = 1.0

        # -------------------------------------------------------------
        # 7. Rescued Star-Token inside the Opening Giant Lotus (19.65s ~ 21.65s)
        #    ("莲花升起，莲花打开，吃掉星星，然后进入下一幕")
        # -------------------------------------------------------------
        token_x = 4140.0
        token_y = 615.0
        token_r = 48.0
        token_rot = math.sin(t * 2.8) * 0.16
        token_alpha = 0.0
        token_active = False
        eat_burst_age = -1.0

        if 19.65 <= t < 21.35:
            # Rises and gleams inside the opening Giant Lotus heart!
            token_active = True
            p_emerge = smoothstep(19.65, 20.55, t)
            token_alpha = p_emerge
            token_y = lerp(685.0, 605.0, p_emerge) + math.sin(t * 4.5) * 6.0
            token_r = lerp(22.0, 50.0, p_emerge)
        elif 21.35 <= t < 21.85:
            # Slime lands on the open Giant Lotus and eats/absorbs the Star Token!
            token_active = True
            p_eat = (t - 21.35) / 0.50
            token_alpha = max(0.0, 1.0 - p_eat * 1.4)
            token_y = lerp(605.0, 625.0, p_eat)
            token_r = lerp(50.0, 12.0, p_eat)

        if 21.35 <= t < 22.45:
            eat_burst_age = t - 21.35

        # -------------------------------------------------------------
        # 8. Cinnabar & Mud-Gold Star Mandala Portal -> World 05 Hardcover Transition (x = 5380, y = 285)
        # -------------------------------------------------------------
        seal_x = 5380.0
        seal_y = 285.0
        seal_size = 176.0
        seal_flip_rx = 0.0
        seal_slam_prog = 0.0
        seal_shockwave_r = 0.0

        if 25.95 <= t < 26.55:
            p_flip = (t - 25.95) / 0.60
            seal_size = lerp(176.0, 420.0, smoothstep(0.0, 1.0, p_flip))
        if t >= 26.15:
            # Smoothly expand Cinnabar Book Cover right up to t = 27.95s so there is ZERO static freeze before World 05!
            seal_slam_prog = smoothstep(26.15, 27.95, t)
            seal_shockwave_r = (t - 26.15) * 1650.0

        # -------------------------------------------------------------
        # 9. Slime Hero State Machine & Natural Eye / Taiji Logic
        # -------------------------------------------------------------
        s_radius = SLIME_R
        s_x = 755.0
        foot_y = tip_y
        s_grounded = True
        target_squash = 1.0
        target_tilt = 0.0
        target_look_x = 0.55
        target_look_y = -0.20
        s_eye_mode = "pill"
        s_bubble = None
        s_bubble_alpha = 0.0
        s_roll_angle = 0.0
        s_alpha = 1.0
        s_color_splash = False
        s_ink_trail = False
        s_taiji_aura = 0.0  # 0..1 intensity of rotating Black-and-White Yin-Yang Taiji Diagram around Slime!

        # --- Act I (0.0 ~ 4.20s): Direct Vertical Fall from World 03 onto Bamboo & Catapult ---
        if t < 0.90:
            # 0.00s ~ 0.90s: Full-size Slime falls directly from top edge of frame (-85 -> tip_y) continuing World 03's vertical fall!
            p_drop = t / 0.90
            s_alpha = 1.0
            s_radius = SLIME_R
            s_x = 755.0
            foot_y = lerp(-85.0, 673.0, p_drop * (0.35 + 0.65 * p_drop))
            s_grounded = False
            s_ink_trail = True
            target_squash = lerp(1.42, 0.62, smoothstep(0.76, 1.0, p_drop))
            target_tilt = 0.0
            s_eye_mode = "wince" if p_drop > 0.80 else "pill"
            target_look_x = 0.0
            target_look_y = 0.48
        elif 0.90 <= t < 3.25:
            # Lands on flexing bamboo stalk at t=0.90s: deep elastic bounce + 3D spherical head turn Left -> Center -> Right!
            dt_land = t - 0.90
            s_x = tip_x
            foot_y = tip_y
            s_grounded = True
            target_squash = 1.0 - 0.36 * math.exp(-dt_land * 4.2) * math.cos(dt_land * 16.0)
            target_tilt = 0.05 * math.sin(dt_land * 6.0)
            p_sweep = dt_land / 2.35
            if p_sweep < 0.32:
                target_look_x = -0.56
                target_look_y = -0.14
            elif p_sweep < 0.65:
                u_c = (p_sweep - 0.32) / 0.33
                target_look_x = lerp(-0.56, 0.0, smoothstep(0.0, 1.0, u_c))
                target_look_y = lerp(-0.14, -0.05, smoothstep(0.0, 1.0, u_c))
            else:
                u_r = (p_sweep - 0.65) / 0.35
                target_look_x = lerp(0.0, 0.56, smoothstep(0.0, 1.0, u_r))
                target_look_y = lerp(-0.05, -0.22, smoothstep(0.0, 1.0, u_r))
            s_eye_mode = "wince" if dt_land < 0.18 else "pill"
        elif 3.25 <= t < 4.20:
            # Deep squash charge bending the bamboo stalk: effort uses `> <` (wince)!
            p_charge = (t - 3.25) / 0.95
            s_x = tip_x
            foot_y = tip_y
            s_grounded = True
            target_squash = lerp(0.96, 0.54, smoothstep(0.0, 1.0, p_charge))
            target_tilt = lerp(0.05, 0.32, p_charge)
            target_look_x = +0.58
            target_look_y = -0.26
            s_eye_mode = "wince" if p_charge > 0.25 else "pill"

        # --- Act II (4.20 ~ 10.20s): Ballistic Leap, Stone Bridge & Master Brush ---
        elif 4.20 <= t < 5.45:
            # High ballistic catapult flight from bamboo (780, 790) to left bridge ramp (1580, 656)
            # Normal open eyes ("pill") looking forward at destination during flight!
            p_fl = (t - 4.20) / 1.25
            s_x = lerp(780.0, 1580.0, p_fl)
            y_start = 790.0
            y_end = bridge_deck_y(1580.0)
            foot_y = lerp(y_start, y_end, p_fl) - math.sin(p_fl * math.pi) * 340.0
            s_grounded = False
            target_squash = 1.28 if p_fl < 0.88 else lerp(1.28, 0.72, (p_fl - 0.88) / 0.12)
            target_tilt = lerp(0.42, -0.18, p_fl)
            target_look_x = +0.56
            target_look_y = lerp(-0.28, +0.25, p_fl)
            s_eye_mode = "pill"
            s_ink_trail = True
        elif 5.45 <= t < 6.75:
            # 3 brisk hops up the left stone bridge arch [1580 -> 1985]: steady "pill" eyes!
            p_run = (t - 5.45) / 1.30
            hop = eval_continuous_hop_chain(p_run, num_hops=3, jump_height=42.0)
            s_x = lerp(1580.0, 1985.0, hop["progress_x"])
            deck_y = bridge_deck_y(s_x)
            foot_y = deck_y + hop["y_off"]
            s_grounded = abs(hop["y_off"]) < 2.5
            target_squash = hop["squash_y"]
            target_tilt = hop["tilt"] - 0.08
            target_look_x = +0.52
            target_look_y = -0.18
            s_eye_mode = "pill"
        elif 6.75 <= t < 7.55:
            # Skid stop at broken bridge edge (x=1985): startled `> <` ("wince") + `?`
            p_skid = (t - 6.75) / 0.80
            s_x = 1985.0 + math.sin(p_skid * math.pi * 0.5) * 10.0
            foot_y = bridge_deck_y(s_x)
            s_grounded = True
            target_squash = 0.76 + 0.08 * math.sin(p_skid * math.pi)
            target_tilt = 0.18
            target_look_x = 0.0
            target_look_y = +0.55
            s_eye_mode = "wince"
            s_bubble = "?"
            s_bubble_alpha = smoothstep(0.05, 0.30, p_skid) * (1.0 - smoothstep(0.75, 1.0, p_skid))
        elif 7.55 <= t < 8.35:
            # Pure look UP at descending Master Brush (look_x=0.0, look_y=-0.60, equal open eyes!) + `!`
            p_up = (t - 7.55) / 0.80
            s_x = 1995.0
            foot_y = bridge_deck_y(s_x)
            s_grounded = True
            target_squash = 1.04
            target_tilt = -0.18
            target_look_x = 0.0
            target_look_y = -0.60
            s_eye_mode = "pill"
            s_bubble = "!"
            s_bubble_alpha = smoothstep(0.05, 0.30, p_up) * (1.0 - smoothstep(0.75, 1.0, p_up))
        elif 8.35 <= t < 8.58:
            # Deep crouch before vertical headbutt jump: effort `> <` ("wince")!
            p_cr = (t - 8.35) / 0.23
            s_x = 1995.0
            foot_y = bridge_deck_y(s_x)
            s_grounded = True
            target_squash = lerp(1.04, 0.54, p_cr)
            target_tilt = -0.10
            target_look_x = 0.0
            target_look_y = -0.68
            s_eye_mode = "wince"
        elif 8.58 <= t < 9.12:
            # Vertical jump to headbutt Master Brush tip at (2015, 370) at t=8.82s
            u_hb = (t - 8.58) / 0.54
            s_x = lerp(1995.0, 2015.0, math.sin(u_hb * math.pi))
            base_deck_y = bridge_deck_y(s_x)
            arc_lift = math.sin(u_hb * math.pi) * 118.0
            foot_y = base_deck_y - arc_lift
            s_grounded = False
            target_squash = 1.26 if abs(u_hb - 0.45) > 0.12 else 0.76
            target_tilt = 0.05
            target_look_x = +0.25 if u_hb > 0.5 else 0.0
            target_look_y = -0.45
            # Open eyes during jump, `> <` wince right at headbutt impact!
            s_eye_mode = "wince" if 0.36 <= u_hb <= 0.58 else "pill"
        elif 9.12 <= t < 9.65:
            # GENUINE HAPPY EVENT: Watching the Master Brush magically paint the right bridge arch!
            p_watch = (t - 9.12) / 0.53
            s_x = 1995.0
            foot_y = bridge_deck_y(s_x)
            s_grounded = True
            target_squash = 1.0 - 0.24 * math.exp(-p_watch * 5.0) * math.cos(p_watch * 16.0)
            target_tilt = 0.06
            target_look_x = +0.48
            target_look_y = -0.15
            s_eye_mode = "happy"
        elif 9.65 <= t < 10.20:
            # Sustained happy emotion (`^ ^`) as it hops across the newly painted bridge!
            p_down = (t - 9.65) / 0.55
            hop = eval_continuous_hop_chain(p_down, num_hops=2, jump_height=36.0)
            s_x = lerp(1995.0, 2440.0, hop["progress_x"])
            foot_y = bridge_deck_y(s_x) + hop["y_off"]
            s_grounded = abs(hop["y_off"]) < 2.5
            target_squash = hop["squash_y"]
            target_tilt = hop["tilt"] + 0.10
            target_look_x = +0.55
            target_look_y = +0.18
            s_eye_mode = "happy"

        # --- Act III (10.20 ~ 14.95s): 4 Pentatonic Lotus Pad Hops & Leaping Cinnabar Koi ---
        elif 10.20 <= t < 14.95:
            # Continuous alert open eyes ("pill") watching the pads & koi — NO flickering happy->normal->happy!
            p_pond = (t - 10.20) / 4.75
            hop_idx = int(clamp(p_pond * 4.0, 0, 3))
            u_hop = (p_pond * 4.0) - hop_idx

            nodes_x = [2440.0, 2740.0, 3080.0, 3420.0, 3760.0]
            nodes_y = [
                bridge_deck_y(2440.0),
                lotus_pads_state[0]["y"],
                lotus_pads_state[1]["y"],
                lotus_pads_state[2]["y"],
                lotus_pads_state[3]["y"],
            ]
            x0, x1 = nodes_x[hop_idx], nodes_x[hop_idx + 1]
            y0, y1 = nodes_y[hop_idx], nodes_y[hop_idx + 1]

            jump = eval_targeted_jump(u_hop, x0, y0, x1, y1, arc_height=115.0)
            s_x = jump["x"]
            target_squash = jump["squash_y"]
            target_tilt = jump["tilt"]
            if u_hop < 0.20:
                foot_y = y0
                s_grounded = True
            elif u_hop >= 0.86:
                foot_y = y1
                s_grounded = True
            else:
                foot_y = jump["y"]
                s_grounded = False
                s_ink_trail = True

            target_look_x = +0.50
            target_look_y = +0.34 if 0.25 < u_hop < 0.75 else -0.18
            s_eye_mode = "pill"

        # --- Act IV (14.95 ~ 22.20s): Black Hole Eats Star -> Taiji Yin-Yang Strike & Rebound -> Lotus Rises & Opens -> Eat Star ---
        elif 14.95 <= t < 15.90:
            # Standing on Pad 4 (3760): watches Black Hole swallow the Guiding Star ✦ (`> <` wince + `!`)
            p_rec = (t - 14.95) / 0.95
            s_x = 3760.0 - math.sin(p_rec * math.pi * 0.5) * 20.0
            foot_y = lotus_pads_state[3]["y"]
            s_grounded = True
            target_squash = 0.82
            target_tilt = -0.22
            target_look_x = +0.58
            target_look_y = +0.16
            s_eye_mode = "wince"
            s_bubble = "!"
            s_bubble_alpha = smoothstep(0.10, 0.35, p_rec) * (1.0 - smoothstep(0.78, 1.0, p_rec))
        elif 15.90 <= t < 17.15:
            # Deep Taiji Charge on Pad 4: channels rotating Black-and-White Yin-Yang Taiji Diagram!
            # Uses `> <` ("wince") during deep physical/spiritual charge exertion!
            p_taiji = (t - 15.90) / 1.25
            s_x = lerp(3740.0, 3765.0, p_taiji)
            foot_y = lotus_pads_state[3]["y"]
            s_grounded = True
            target_squash = lerp(0.88, 0.52, smoothstep(0.15, 1.0, p_taiji))
            target_tilt = lerp(-0.15, 0.22, p_taiji)
            if p_taiji < 0.40:
                target_look_x = 0.0
                target_look_y = -0.12
            else:
                target_look_x = +0.58
                target_look_y = +0.10
            s_eye_mode = "wince" if p_taiji > 0.25 else "charge"
            s_bubble = "taiji"
            s_bubble_alpha = smoothstep(0.06, 0.30, p_taiji) * (1.0 - smoothstep(0.85, 1.0, p_taiji))
            s_taiji_aura = smoothstep(0.05, 0.65, p_taiji)
            s_roll_angle = (t - 15.90) * 3.2
        elif 17.15 <= t < 17.95:
            # Taiji Yin-Yang Dive-Strike from Pad 4 (3765, 715) straight into Black Hole core (4140, 715)!
            p_strike = (t - 17.15) / 0.80
            s_x = lerp(3765.0, 4140.0, p_strike)
            y0_st = lotus_pads_state[3]["base_y"]
            y1_st = 715.0
            foot_y = lerp(y0_st, y1_st, p_strike) - math.sin(p_strike * math.pi) * 260.0
            s_grounded = False
            target_squash = 1.24 if p_strike < 0.85 else lerp(1.24, 0.48, (p_strike - 0.85) / 0.15)
            target_tilt = lerp(0.38, -0.35, p_strike)
            target_look_x = +0.56
            target_look_y = +0.42
            # Focused charge during flight, `> <` wince right on impact!
            s_eye_mode = "wince" if p_strike >= 0.82 else "charge"
            s_taiji_aura = 1.0
            s_roll_angle = 4.0 + p_strike * math.tau
            s_color_splash = True
            s_ink_trail = True
        elif 17.95 <= t < 18.85:
            # Heavy Taiji Impact & Elastic Gravity Rebound from Black Hole (4140, 715) back to Pad 4 (3760, 715)!
            p_reb = (t - 17.95) / 0.90
            s_x = lerp(4140.0, 3760.0, smoothstep(0.05, 1.0, p_reb))
            foot_y = lerp(715.0, lotus_pads_state[3]["y"], p_reb) - math.sin(p_reb * math.pi) * 215.0
            s_grounded = p_reb > 0.92
            target_squash = 0.48 if p_reb < 0.12 else (1.18 if p_reb < 0.85 else 0.72)
            target_tilt = lerp(-0.35, 0.18, p_reb)
            target_look_x = +0.55
            target_look_y = +0.18
            s_eye_mode = "wince" if p_reb < 0.30 else "pill"
            s_taiji_aura = max(0.0, 1.0 - p_reb * 1.2)
            s_ink_trail = True
        elif 18.85 <= t < 20.65:
            # Standing on Pad 4 (3760), watching the Giant Lotus RISE (18.5~19.6s) and OPEN (19.5~20.65s) to reveal the Star!
            p_wait = (t - 18.85) / 1.80
            s_x = 3760.0
            foot_y = lotus_pads_state[3]["y"]
            s_grounded = True
            target_squash = 1.0 - 0.25 * math.exp(-p_wait * 5.0) * math.cos(p_wait * 16.0)
            target_tilt = 0.06
            target_look_x = +0.56
            target_look_y = -0.10
            s_eye_mode = "pill"
        elif 20.65 <= t < 21.40:
            # Leaps from Pad 4 (3760, 715) onto the open Giant Lotus Throne (4140, 685) to eat the Star!
            u_eat = (t - 20.65) / 0.75
            jump = eval_targeted_jump(u_eat, 3760.0, lotus_pads_state[3]["y"], 4140.0, 685.0, arc_height=145.0)
            s_x = jump["x"]
            target_squash = jump["squash_y"]
            target_tilt = jump["tilt"]
            if u_eat < 0.20:
                foot_y = lotus_pads_state[3]["y"]
                s_grounded = True
                s_eye_mode = "wince"  # Effort during pre-jump crouch
            elif u_eat >= 0.86:
                foot_y = 685.0
                s_grounded = True
                s_eye_mode = "sparkle"
            else:
                foot_y = jump["y"]
                s_grounded = False
                s_ink_trail = True
                s_eye_mode = "pill"
            target_look_x = +0.52
            target_look_y = -0.15
        elif 21.40 <= t < 22.30:
            # GENUINE HAPPY EVENT: Eats/absorbs the rescued Star on the Giant Lotus Throne (4140, 685)!
            # Turns gaze through center (0.0, equal eyes) with sustained joy (`sparkle` -> `happy`)!
            p_joy = (t - 21.40) / 0.90
            s_x = 4140.0
            foot_y = 685.0 - math.sin(p_joy * math.pi) * 28.0
            s_grounded = p_joy > 0.75 or p_joy < 0.15
            target_squash = 1.0 + 0.18 * math.sin(p_joy * math.pi * 2.0)
            target_tilt = 0.04
            if p_joy < 0.55:
                target_look_x = 0.0
                target_look_y = -0.12
                s_eye_mode = "sparkle"
            else:
                target_look_x = +0.55
                target_look_y = -0.32
                s_eye_mode = "happy"

        # --- Act V (22.30 ~ 24.80s): Climb Cloud-Mountain Cliff Ledges Chasing the Freed Star ---
        elif 22.30 <= t < 23.15:
            # Leap 1: Giant Lotus Throne (4140, 685) -> Cliff Ledge 1 (4450, 590) with sustained happy mood!
            u_j1 = (t - 22.30) / 0.85
            jump = eval_targeted_jump(u_j1, 4140.0, 685.0, 4450.0, 590.0, arc_height=125.0)
            s_x = jump["x"]
            target_squash = jump["squash_y"]
            target_tilt = jump["tilt"]
            if u_j1 < 0.20:
                foot_y = 685.0
                s_grounded = True
            elif u_j1 >= 0.86:
                foot_y = 590.0
                s_grounded = True
            else:
                foot_y = jump["y"]
                s_grounded = False
                s_ink_trail = True
            target_look_x = +0.55
            target_look_y = -0.32
            s_eye_mode = "happy"
        elif 23.15 <= t < 23.95:
            # Leap 2: Cliff Ledge 1 (4450, 590) -> Cliff Ledge 2 (4730, 495): focused "pill" eyes!
            u_j2 = (t - 23.15) / 0.80
            jump = eval_targeted_jump(u_j2, 4450.0, 590.0, 4730.0, 495.0, arc_height=120.0)
            s_x = jump["x"]
            target_squash = jump["squash_y"]
            target_tilt = jump["tilt"]
            if u_j2 < 0.20:
                foot_y = 590.0
                s_grounded = True
            elif u_j2 >= 0.86:
                foot_y = 495.0
                s_grounded = True
            else:
                foot_y = jump["y"]
                s_grounded = False
                s_ink_trail = True
            target_look_x = +0.55
            target_look_y = -0.32
            s_eye_mode = "pill"
        elif 23.95 <= t < 24.80:
            # Leap 3: Cliff Ledge 2 (4730, 495) -> Summit Altar (5010, 410): focused "pill" eyes!
            u_j3 = (t - 23.95) / 0.85
            jump = eval_targeted_jump(u_j3, 4730.0, 495.0, 5010.0, 410.0, arc_height=125.0)
            s_x = jump["x"]
            target_squash = jump["squash_y"]
            target_tilt = jump["tilt"]
            if u_j3 < 0.20:
                foot_y = 495.0
                s_grounded = True
            elif u_j3 >= 0.86:
                foot_y = 410.0
                s_grounded = True
            else:
                foot_y = jump["y"]
                s_grounded = False
                s_ink_trail = True
            target_look_x = +0.56
            target_look_y = -0.35
            s_eye_mode = "pill"

        # --- Act VI (24.80 ~ 28.00s): Soaring Leap into Suspended Cinnabar Seal & Full-Screen Stamp ---
        elif 24.80 <= t < 25.35:
            # On Summit Altar (5010, 410): deep pre-jump effort crouch (`> <` wince) aiming at Seal (5380, 285)!
            p_aim = (t - 24.80) / 0.55
            s_x = 5010.0
            foot_y = 410.0
            s_grounded = True
            target_squash = lerp(1.0, 0.54, smoothstep(0.15, 1.0, p_aim))
            target_tilt = lerp(0.05, 0.28, p_aim)
            target_look_x = +0.58
            target_look_y = -0.42
            s_eye_mode = "wince" if p_aim > 0.25 else "pill"
        elif 25.35 <= t < 26.15:
            # Soaring leap along calligraphic qi-yun arc into Cinnabar Seal center (5380, 285): open "pill" eyes!
            p_dive = (t - 25.35) / 0.80
            s_radius = lerp(SLIME_R, 28.0, smoothstep(0.45, 1.0, p_dive))
            s_x = lerp(5010.0, 5380.0, p_dive)
            foot_y = lerp(410.0, 295.0, p_dive) - math.sin(p_dive * math.pi) * 145.0
            s_grounded = False
            target_squash = lerp(1.28, 1.65, p_dive)
            target_tilt = 0.35
            target_look_x = +0.58
            target_look_y = -0.42
            s_eye_mode = "pill"
            s_alpha = lerp(1.0, 0.0, smoothstep(0.68, 1.0, p_dive))
            s_ink_trail = True
        else:
            s_alpha = 0.0
            s_x = 5380.0
            foot_y = 285.0
            s_grounded = False

        # Step 2nd-order Spring-Dampers
        s_squash = squash_damper.step(target_squash, dt)
        s_tilt = tilt_damper.step(target_tilt, dt)
        s_look_x, s_look_y = look_damper.step(target_look_x, target_look_y, dt)

        # Compute exact Slime center Y from foot_y AFTER squash damper step (zero clipping, zero floating!)
        if s_grounded:
            s_y = foot_y_to_center_y(foot_y, s_radius, s_squash, grounded=True)
        else:
            s_y = foot_y - s_radius * s_squash * 0.92

        # Update rolling calligraphic motion trail history
        if f == 0:
            trail_history = []
        if s_ink_trail or not s_grounded:
            trail_history.append((s_x, s_y))
            if len(trail_history) > 15:
                trail_history.pop(0)
        else:
            if len(trail_history) > 0:
                trail_history.pop(0)
            if len(trail_history) > 0:
                trail_history.pop(0)

        # Natural blink cycle for pill eyes
        if s_eye_mode == "pill":
            blink_phase = (t * 1.7) % 3.8
            s_blink = math.sin(blink_phase / 0.16 * math.pi) if blink_phase < 0.16 else 0.0
        else:
            s_blink = 0.0

        # -------------------------------------------------------------
        # 10. Guiding Star ✦ Trajectory with True Chase Distance & Black Hole Swallow
        # -------------------------------------------------------------
        star_x = s_x + 420.0
        star_y = 420.0
        star_r = 33.0
        star_rot = (t * 2.4) % math.tau
        star_alpha = 1.0

        if t < 1.20:
            star_alpha = smoothstep(0.40, 1.20, t)
            star_x = 1040.0
            star_y = 430.0
        elif 1.20 <= t < 3.00:
            # Hovers 300px ahead of bamboo stalk, teasing the Slime
            star_x = 1060.0 + math.sin(t * 2.4) * 22.0
            star_y = 435.0 + math.cos(t * 2.0) * 16.0
        elif 3.00 <= t < 4.20:
            # Darts ahead across the river BEFORE the Slime catapults!
            p_dart = smoothstep(3.00, 4.15, t)
            star_x = lerp(1060.0, 2260.0, p_dart)
            star_y = 425.0 - math.sin(p_dart * math.pi) * 85.0
        elif 4.20 <= t < 9.30:
            # Waits across the broken bridge chasm at (2280, 415) — 300px ahead of the broken edge (1985)!
            star_x = 2280.0 + math.sin(t * 2.8) * 18.0
            star_y = 415.0 + math.cos(t * 2.3) * 14.0
        elif 9.30 <= t < 10.90:
            # As soon as the bridge is painted, darts ahead into the Lotus Pond (2280 -> 3120)!
            p_dart2 = smoothstep(9.30, 10.85, t)
            star_x = lerp(2280.0, 3120.0, p_dart2)
            star_y = lerp(415.0, 485.0, p_dart2) - math.sin(p_dart2 * math.pi) * 55.0
        elif 10.90 <= t < 14.85:
            # Stays 360px ~ 440px ahead of the Slime across the Lotus Pond, leading toward (4140, 520)!
            p_lead = (t - 10.90) / 3.95
            star_x = lerp(3120.0, 4140.0, p_lead)
            star_y = 485.0 - math.sin(p_lead * math.pi * 2.0) * 42.0
        elif 14.85 <= t < 15.85:
            # SUCKED DOWN & SWALLOWED BY THE INK BLACK HOLE at (4140, 720)! ("黑洞吃掉了星星")
            p_suck = clamp((t - 14.85) / 0.90, 0.0, 1.0)
            spiral_a = p_suck * math.tau * 2.5
            spiral_r = (1.0 - p_suck) * 75.0
            star_x = 4140.0 + math.cos(spiral_a) * spiral_r
            star_y = lerp(485.0, 720.0, p_suck * p_suck)
            star_r = lerp(33.0, 4.0, p_suck)
            star_alpha = max(0.0, 1.0 - smoothstep(0.70, 1.0, p_suck))
        elif 15.85 <= t < 21.35:
            # Inside the Black Hole / Rising Lotus (the Star-Token inside the Lotus is drawn via `token`!)
            star_alpha = 0.0
            star_x = 4140.0
            star_y = 605.0
        elif 21.35 <= t < 25.10:
            # Springs forth from the open Lotus burst and dashes 450px ahead up to the Cinnabar Seal (5380, 285)!
            p_free = clamp((t - 21.35) / 3.20, 0.0, 1.0)
            star_alpha = smoothstep(21.35, 21.60, t) * (1.0 - smoothstep(24.65, 25.10, t))
            star_x = lerp(4220.0, 5380.0, smoothstep(0.0, 1.0, p_free))
            star_y = lerp(550.0, 285.0, smoothstep(0.0, 1.0, p_free)) - math.sin(p_free * math.pi * 2.0) * 48.0
        else:
            star_alpha = 0.0

        # -------------------------------------------------------------
        # 11. Smooth 2D Camera Framing across 5600x1280 Scroll
        # -------------------------------------------------------------
        if t < 4.20:
            target_cam_x = 960.0
            target_cam_y = 540.0
        elif 4.20 <= t < 10.20:
            target_cam_x = clamp(s_x + 150.0, 960.0, 2120.0)
            target_cam_y = 525.0
        elif 10.20 <= t < 14.95:
            target_cam_x = clamp(s_x + 220.0, 2120.0, 3920.0)
            target_cam_y = 545.0
        elif 14.95 <= t < 22.30:
            # Frame both Pad 4 (3760) and the Black Hole / Giant Lotus (4140) clearly!
            target_cam_x = lerp(3950.0, 4140.0, smoothstep(19.5, 21.5, t))
            target_cam_y = 535.0
        elif 22.30 <= t < 25.35:
            target_cam_x = clamp(s_x + 190.0, 4140.0, 4880.0)
            target_cam_y = lerp(535.0, 465.0, smoothstep(22.3, 24.8, t))
        else:
            target_cam_x = lerp(4880.0, 5120.0, smoothstep(25.35, 26.5, t))
            target_cam_y = lerp(465.0, 420.0, smoothstep(25.35, 26.5, t))

        cam_shake_y = 0.0
        if 8.80 <= t < 9.15:
            dt_s = t - 8.80
            cam_shake_y = math.exp(-dt_s * 8.0) * math.sin(dt_s * 55.0) * 12.0
        elif 15.20 <= t < 15.85:
            dt_s = t - 15.20
            cam_shake_y = math.exp(-dt_s * 4.5) * math.sin(dt_s * 34.0) * 8.0
        elif 17.95 <= t < 18.75:
            # Heavy Taiji Impact camera shake!
            dt_s = t - 17.95
            cam_shake_y = math.exp(-dt_s * 5.0) * math.sin(dt_s * 52.0) * 20.0
        elif 26.75 <= t < 28.0:
            dt_s = t - 26.75
            cam_shake_y = math.exp(-dt_s * 4.0) * math.sin(dt_s * 48.0) * 22.0

        filt_cam_x, filt_cam_y = cam_damper.step(target_cam_x, target_cam_y, dt)

        # -------------------------------------------------------------
        # 12. Snapshot State Dict
        # -------------------------------------------------------------
        state = {
            "frame_idx": f,
            "t": t,
            "scroll_reveal": scroll_reveal,
            "slime": {
                "x": s_x,
                "y": s_y,
                "foot_y": foot_y,
                "grounded": s_grounded,
                "radius": s_radius,
                "squash_y": s_squash,
                "tilt": s_tilt,
                "look_x": s_look_x,
                "look_y": s_look_y,
                "eye_mode": s_eye_mode,
                "blink": s_blink,
                "bubble": s_bubble,
                "bubble_alpha": s_bubble_alpha,
                "roll_angle": s_roll_angle,
                "alpha": s_alpha,
                "color_splash": s_color_splash,
                "ink_trail": s_ink_trail,
                "taiji_aura": s_taiji_aura,
                "trail_pts": list(trail_history),
            },
            "token": {
                "active": token_active,
                "x": token_x,
                "y": token_y,
                "radius": token_r,
                "rot": token_rot,
                "alpha": token_alpha,
                "eat_burst_age": eat_burst_age,
            },
            "star": {
                "x": star_x,
                "y": star_y,
                "radius": star_r,
                "rot": star_rot,
                "alpha": star_alpha,
            },
            "bamboo": {
                "bend": bamboo_bend,
                "vib": bamboo_vib,
                "tip_x": tip_x,
                "tip_y": tip_y,
            },
            "brush": {
                "state": brush_state,
                "x": brush_x,
                "y": brush_y,
                "ang": brush_ang,
            },
            "bridge": {
                "drawn_progress": bridge_drawn_prog,
            },
            "lotus_pads": lotus_pads_state,
            "koi": koi_state,
            "vortex": {
                "active": vortex_active,
                "x": vortex_center_x,
                "y": vortex_center_y,
                "rot": vortex_rot,
                "corruption": vortex_corruption,
                "eyes": vortex_eyes,
                "suck_prog": vortex_suck_prog,
                "taiji_impact_age": taiji_impact_age,
                "lotus_rise": lotus_rise,
                "lotus_open": lotus_open,
            },
            "cliff_ledges": cliff_ledges,
            "seal": {
                "x": seal_x,
                "y": seal_y,
                "size": seal_size,
                "flip_rx": seal_flip_rx,
                "slam_prog": seal_slam_prog,
                "shockwave_r": seal_shockwave_r,
            },
            "camera": {
                "x": filt_cam_x,
                "y": filt_cam_y + cam_shake_y,
                "shake": cam_shake_y,
            },
        }
        frames_state.append(state)

    return frames_state, audio_events
