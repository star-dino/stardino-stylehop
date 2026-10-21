#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World 06 · 哥特玫瑰彩窗圣殿 (audio_06_stainedglass.py)
Authentic 48kHz Stereo Master Audio Engine for World 06 (26.0s 4-Act 4-Zone).

Overhauled with `lemo-opuscar` & `earshot` Real-Sound Architecture:
1. Real Sampled Cathedral Instruments (`core.audio.sampler`):
   - `organ_soft`, `organ`, `organ_pedal` (Gothic cathedral pipe organ registrations)
   - `recorder`, `flute` (sacred modal cantus firmus lines)
   - `harpsichord`, `harp`, `glass`, `hand_chimes`, `glockenspiel` (crystalline stained-glass tracery)
   - `tubular_bells`, `gong2`, `timpani` (colossal Sanctuary Bell tolls)
   - `violins`, `violas`, `cellos`, `contrabass` (soaring cathedral string tutti in Act 3-4)
2. Physical Pluck Models (`core.audio.pluck`):
   - `music_box`, `harp`, `kalimba`, `upright_bass_pizz`
3. Curated Tactile Stained-Glass Foley (`earshot.forge.bank` + `styles/stained-glass/demo/mix.py`):
   - Delicate crystal-on-stone footsteps (`fit/land.light/finger_phone` + sampled `glass` + `kalimba`)
   - Prismatic dispersion shimmer (`logo_sting/whoosh_glass` + `harp` + `hand_chimes`)
   - Sanctuary Bell climax (`tubular_bells` + `gong2` + `pro_sub_drop/ref` + `fit/bell/small_bell`)
   - Warm 1930s celluloid projector handover (`23.80s - 26.00s`) with gentle low-passed sprocket rhythm & optical pips
4. Mandatory Cathedral Stop-Downs (`master.gate_zero`):
   - `5.15s - 5.88s`: Nave abyss hush before landing on the Crystal Prism Pedestal
   - `15.85s - 16.38s`: Complete cathedral silence right before the `16.40s` Sanctuary Bell toll,
     followed at `16.65s` by the glorious C-Major Full-Organ & String Choir Tutti
5. Sidechain Ducking & -14.0 LUFS Mastering (`master.sidechain_times` + `master.finish`).
"""

import math
import os
import sys
import numpy as np
import scipy.signal as sig

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(CUR_DIR))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from audio_deps import require_audio_upstream
require_audio_upstream()   # 缺失时抛出带安装指引的错误，绝不静默降级

from core.audio import sampler as S
from core.audio import pluck as P
from core.audio import sfx as lemo_sfx
from earshot.forge import bank
from earshot import api as earshot_api
import master

SR = 48000
TOTAL_DURATION = 26.0
TOTAL_SAMPLES = int(round(TOTAL_DURATION * SR))


# =============================================================================
# UTILITY & FILTER HELPERS
# =============================================================================
import soundfile as sf

def _stereo_bus(dur_s: float, sr: int = SR) -> np.ndarray:
    return np.zeros((int(round(float(dur_s) * sr)), 2), dtype=np.float32)

def _pan_stereo(mono: np.ndarray, pan: float = 0.0) -> np.ndarray:
    x = np.asarray(mono, dtype=np.float32)
    if x.ndim == 2:
        return x
    th = (float(np.clip(pan, -1.0, 1.0)) + 1.0) * (math.pi / 4.0)
    return np.column_stack((x * math.cos(th), x * math.sin(th))).astype(np.float32)

def _place(bus: np.ndarray, clip: np.ndarray, t: float, sr: int = SR, pan: float = None, gain: float = 1.0) -> None:
    if clip is None or len(clip) == 0:
        return
    st = _pan_stereo(clip, pan if pan is not None else 0.0) if (clip.ndim == 1 or pan is not None) else np.asarray(clip, dtype=np.float32)
    i0 = int(round(float(t) * sr))
    if i0 < 0:
        st = st[-i0:]
        i0 = 0
    if i0 >= len(bus) or len(st) == 0:
        return
    i1 = min(len(bus), i0 + len(st))
    bus[i0:i1] += st[:i1 - i0] * float(gain)

def _gate_zero(bus: np.ndarray, t0: float, t1: float, sr: int = SR, fade_ms: float = 20.0) -> np.ndarray:
    y = bus.copy()
    n = len(y)
    i0 = max(0, int(round(t0 * sr)))
    i1 = min(n, int(round(t1 * sr)))
    if i1 <= i0:
        return y
    fn = max(1, int(round((fade_ms / 1000.0) * sr)))
    y[i0:i1] = 0.0
    if i0 > fn:
        w = np.linspace(1.0, 0.0, fn, dtype=y.dtype)[:, None]
        y[i0 - fn:i0] *= w
    if i1 + fn <= n:
        w = np.linspace(0.0, 1.0, fn, dtype=y.dtype)[:, None]
        y[i1:i1 + fn] *= w
    return y

def _reverb(bus: np.ndarray, sr: int = SR, rt60: float = 1.8, predelay_ms: float = 15.0, wet: float = 0.25, damp: float = 0.45) -> np.ndarray:
    size = float(np.clip((rt60 - 0.4) / 3.0, 0.05, 0.98))
    return S.room(bus.astype(np.float32), size=size, mix=wet, predelay=predelay_ms / 1000.0, damp=damp)[:len(bus)]

master.stereo_bus = _stereo_bus
master.pan_stereo = _pan_stereo
master.place = _place
master.gate_zero = _gate_zero
master.reverb = _reverb

def lp(x: np.ndarray, cutoff_hz: float, order: int = 2) -> np.ndarray:
    if len(x) < 16:
        return x
    sos = sig.butter(order, min(cutoff_hz, SR * 0.47) / (SR * 0.5), btype="low", output="sos")
    return sig.sosfilt(sos, x, axis=0).astype(np.float32)


def hp(x: np.ndarray, cutoff_hz: float, order: int = 2) -> np.ndarray:
    if len(x) < 16:
        return x
    sos = sig.butter(order, max(cutoff_hz, 20.0) / (SR * 0.5), btype="high", output="sos")
    return sig.sosfilt(sos, x, axis=0).astype(np.float32)


def bp(x: np.ndarray, lo_hz: float, hi_hz: float, order: int = 2) -> np.ndarray:
    if len(x) < 16:
        return x
    nyq = SR * 0.5
    sos = sig.butter(order, [max(lo_hz, 20.0) / nyq, min(hi_hz, SR * 0.47) / nyq], btype="band", output="sos")
    return sig.sosfilt(sos, x, axis=0).astype(np.float32)


def fade_io(x: np.ndarray, fade_in_s: float = 0.005, fade_out_s: float = 0.03) -> np.ndarray:
    y = x.copy()
    n = len(y)
    fi = min(int(fade_in_s * SR), n // 2)
    fo = min(int(fade_out_s * SR), n // 2)
    if fi > 1:
        w_in = np.linspace(0.0, 1.0, fi, dtype=np.float32)
        y[:fi] = y[:fi] * (w_in[:, None] if y.ndim == 2 else w_in)
    if fo > 1:
        w_out = np.linspace(1.0, 0.0, fo, dtype=np.float32)
        y[-fo:] = y[-fo:] * (w_out[:, None] if y.ndim == 2 else w_out)
    return y


def add_note(
    bus: np.ndarray,
    inst: str,
    pitch: str,
    t: float,
    dur: float,
    vel: float = 0.65,
    pan: float = 0.0,
    vib: float = 0.0,
) -> None:
    if t >= TOTAL_DURATION - 0.02:
        return
    mono = S.note(inst, pitch, dur=dur, vel=vel)
    _place(bus, mono, t, sr=SR, pan=pan, gain=1.0)


def add_pluck(
    bus: np.ndarray,
    preset: str,
    pitch: str,
    t: float,
    dur: float = 0.9,
    vel: float = 0.65,
    pan: float = 0.0,
    gain: float = 0.45,
) -> None:
    if t >= TOTAL_DURATION - 0.02:
        return
    mono = P.pluck(preset, pitch, dur=dur, vel=vel)
    _place(bus, mono, t, sr=SR, pan=pan, gain=gain)


def add_crystal_arpeggio(
    bus: np.ndarray,
    start_t: float,
    pitches: list,
    step_s: float = 0.065,
    dur_s: float = 1.05,
    vel: float = 0.58,
    pan_center: float = 0.0,
    use_harpsichord: bool = True,
) -> None:
    for i, p_name in enumerate(pitches):
        t_n = start_t + i * step_s
        if t_n >= TOTAL_DURATION - 0.05:
            break
        pan = float(np.clip(pan_center + (i / max(len(pitches) - 1, 1) - 0.5) * 0.45, -0.75, 0.75))
        add_note(bus, "harp", p_name, t_n, dur=dur_s, vel=vel * 0.85, pan=pan)
        if use_harpsichord and (i % 2 == 0):
            add_note(bus, "harpsichord", p_name, t_n, dur=dur_s * 0.75, vel=vel * 0.48, pan=-pan * 0.6)
        if i == len(pitches) - 1 or i == 0:
            add_note(bus, "glass", p_name, t_n, dur=dur_s * 1.15, vel=vel * 0.52, pan=pan * 0.5)


# =============================================================================
# TACTILE STAINED-GLASS FOLEY PRIMITIVES (`styles/stained-glass/STYLE.md`)
# =============================================================================
def foley_glass_step(
    pitch: str = "C5",
    chime_pitch: str = "G5",
    heavy: bool = False,
    seed: int = 1,
    pan: float = 0.0,
) -> np.ndarray:
    """
    Delicate, resonant stained-glass Slime step/landing:
    1. Curated fingertip-on-glass/stone tap (`fit/land.light/finger_phone`), low-passed for warmth
    2. Real sampled `glass` harmonic resonance + `kalimba` body bounce
    3. Gentle low-passed stone floor foundation (only when heavy=True)
    """
    dur = 0.75
    out = master.stereo_bus(dur, sr=SR)

    tap_mono, _ = bank.render("fit/land.light/finger_phone", seed=seed)
    tap_clean = lp(hp(tap_mono, 110.0), 3400.0) * (0.28 if heavy else 0.20)
    master.place(out, tap_clean, 0.0, sr=SR, pan=pan, gain=1.0)

    # Real sampled glass harmonic ring
    glass_mono = S.note("glass", chime_pitch, dur=0.65, vel=0.46 if heavy else 0.36)
    master.place(out, glass_mono, 0.004, sr=SR, pan=pan, gain=0.72)

    # Elastic crystal body bounce via physical kalimba pluck
    kal_mono = P.pluck("kalimba", pitch, dur=0.32, vel=0.52 if heavy else 0.40)
    master.place(out, kal_mono, 0.002, sr=SR, pan=pan * 0.8, gain=0.34)

    if heavy:
        stone_thump = lp(lemo_sfx.thump(0.22, 88.0), 150.0)
        master.place(out, stone_thump, 0.0, sr=SR, pan=pan * 0.5, gain=0.65)

    return fade_io(out, 0.002, 0.04)


def foley_lead_snap(pitch_hz: float = 2100.0, pan: float = 0.0) -> np.ndarray:
    """Crisp metallic lead-came solder snap when a stained-glass window locks into illumination."""
    dur = 0.12
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    env = np.exp(-t * 58.0) * (1.0 - np.exp(-t * 900.0))
    tone = (
        0.55 * np.sin(2.0 * np.pi * pitch_hz * t)
        + 0.30 * np.sin(2.0 * np.pi * (pitch_hz * 1.48) * t)
    ) * env * 0.14
    return master.pan_stereo(tone.astype(np.float32), pan=pan)


def foley_sanctuary_bell(
    root_pitch: str = "C4",
    upper_pitch: str = "C5",
    climax: bool = False,
    pan: float = 0.0,
) -> np.ndarray:
    """
    Authentic Sanctuary Bell using real sampled `tubular_bells` + `gong2` + `glass`
    + `fit/bell/small_bell` + deep sub-drop (when climax=True).
    """
    dur = 4.8 if climax else 3.2
    out = master.stereo_bus(dur, sr=SR)

    # Primary tubular bell strike
    tb_main = S.note("tubular_bells", upper_pitch, dur=dur * 0.92, vel=0.88 if climax else 0.68)
    master.place(out, tb_main, 0.0, sr=SR, pan=pan, gain=0.88 if climax else 0.68)

    # Sub-octave bronze hum
    tb_low = S.note("tubular_bells", root_pitch, dur=dur * 0.95, vel=0.75 if climax else 0.52)
    master.place(out, tb_low, 0.005, sr=SR, pan=pan * 0.5, gain=0.72 if climax else 0.50)

    # Warm cathedral gong wash
    gong_st = S.hit("gong2", "big", vel=0.55 if climax else 0.35, dur=dur)
    master.place(out, lp(gong_st, 2800.0), 0.010, sr=SR, pan=0.0, gain=0.45 if climax else 0.28)

    # Crystalline stained-glass overtone shimmer
    gl_st = S.note("glass", upper_pitch, dur=dur * 0.65, vel=0.62 if climax else 0.45)
    master.place(out, gl_st, 0.015, sr=SR, pan=-pan, gain=0.55)

    bell_tap, _ = bank.render("fit/bell/small_bell", seed=16 if climax else 9)
    master.place(out, lp(bell_tap, 5500.0), 0.0, sr=SR, pan=pan, gain=0.26 if climax else 0.18)

    if climax:
        sub_drop, _ = bank.render("pro_sub_drop/ref", pitch="C1")
        sub_clean = lp(sub_drop[: min(len(sub_drop), int(2.2 * SR))], 125.0)
        master.place(out, sub_clean, 0.0, sr=SR, pan=0.0, gain=0.42)

        timp = S.note("timpani", "C2", dur=2.2, vel=0.78)
        master.place(out, timp, 0.0, sr=SR, pan=0.0, gain=0.58)

    return fade_io(out, 0.002, 0.15)


def foley_vintage_projector_handover(dur: float = 2.20) -> np.ndarray:
    """
    Warm, authentic 1930s celluloid film projector handover (23.80s - 26.00s):
    - Gentle low-passed 24fps Maltese-cross sprocket ticks (derived from tactile book/paper click, LP @ 2.8kHz)
    - Subtle warm motor hum (96Hz + 192Hz at very low level)
    - Musical optical leader 3-2-1 pips (sampled `flute` + `glockenspiel` at +0.20s, +0.85s, +1.50s)
    """
    out = master.stereo_bus(dur, sr=SR)
    n = len(out)
    t = np.arange(n, dtype=np.float32) / SR

    # Subtle warm motor purr (never harsh or buzz-heavy)
    motor = (
        0.032 * np.sin(2.0 * np.pi * 96.0 * t)
        + 0.018 * np.sin(2.0 * np.pi * 192.0 * t)
    ) * (0.82 + 0.18 * np.sin(2.0 * np.pi * 8.0 * t))
    motor_st = master.pan_stereo(motor.astype(np.float32), pan=0.0)
    out += fade_io(motor_st, 0.12, 0.18)

    # Gentle 24fps mechanical sprocket ticks (low-passed so they feel tactile, never noisy)
    raw_tick, _ = bank.render("fit/land.light/fingertip_book", seed=24)
    tick_short = lp(hp(raw_tick[: int(0.012 * SR)], 220.0), 2600.0)
    tick_short = fade_io(tick_short, 0.001, 0.005) * 0.16

    step_s = 1.0 / 24.0
    idx = 0
    t_cur = 0.04
    while t_cur < dur - 0.08:
        pan_c = -0.12 if (idx % 2 == 0) else 0.12
        master.place(out, tick_short, t_cur, sr=SR, pan=pan_c, gain=0.85)
        t_cur += step_s
        idx += 1

    # Vintage optical leader 3 - 2 - 1 countdown pips (+0.20s, +0.85s, +1.50s)
    pip_specs = [
        (0.20, "G5", 0.45),
        (0.85, "G5", 0.48),
        (1.50, "C6", 0.56),
    ]
    for p_t, p_note, p_vel in pip_specs:
        fl_pip = S.note("flute", p_note, dur=0.14, vel=p_vel)
        gl_pip = S.note("glockenspiel", p_note, dur=0.22, vel=p_vel * 0.65)
        master.place(out, fl_pip, p_t, sr=SR, pan=0.0, gain=0.55)
        master.place(out, gl_pip, p_t, sr=SR, pan=0.0, gain=0.42)

    return fade_io(out, 0.06, 0.12)


# =============================================================================
# MAIN SCORE & FOLEY ENGINE (26.0s)
# =============================================================================
def render_world_06_audio(output_wav_path: str) -> dict:
    print(f"[Audio 06] Building 26.0s Stained-Glass Cathedral Score & Foley @ {SR}Hz...")

    music_dry = master.stereo_bus(TOTAL_DURATION, sr=SR)
    music_cathedral = master.stereo_bus(TOTAL_DURATION, sr=SR)
    foley_bus = master.stereo_bus(TOTAL_DURATION, sr=SR)
    sub_bus = master.stereo_bus(TOTAL_DURATION, sr=SR)

    foley_anchors = []

    # =========================================================================
    # ACT 1 (0.0s - 5.5s): Zoetrope Harden, Sacred Modal Organ & 3 Lancet Awakenings
    # =========================================================================
    # 0.04s: Zoetrope Stained-Glass Harden shimmer
    add_note(music_cathedral, "hand_chimes", "C6", 0.04, dur=1.4, vel=0.52, pan=0.0)
    add_crystal_arpeggio(
        music_cathedral, 0.06, ["D5", "A5", "D6", "F6", "A6"],
        step_s=0.055, dur_s=1.0, vel=0.52, pan_center=-0.18, use_harpsichord=True,
    )

    # 0.28s & 0.78s: Slime drop & obsidian gallery landing bounce
    master.place(foley_bus, foley_glass_step("A4", "E5", heavy=False, seed=101, pan=-0.32), 0.28, sr=SR)
    master.place(foley_bus, foley_glass_step("D4", "A5", heavy=True, seed=102, pan=-0.30), 0.78, sr=SR)
    foley_anchors.extend([0.28, 0.78])

    # Sacred Cathedral `organ_soft` & `recorder` modal intro (0.15s - 2.05s: D Dorian)
    for p_org, pan_o in [("D3", -0.25), ("A3", 0.15), ("D4", -0.10), ("F4", 0.25)]:
        add_note(music_cathedral, "organ_soft", p_org, 0.15, dur=1.90, vel=0.52, pan=pan_o)
    add_note(music_cathedral, "organ_pedal", "D2", 0.15, dur=1.90, vel=0.48, pan=0.0)
    add_note(music_cathedral, "recorder", "A4", 0.45, dur=0.75, vel=0.46, pan=-0.15, vib=4.2)
    add_note(music_cathedral, "recorder", "D5", 1.20, dur=0.80, vel=0.48, pan=-0.12, vib=4.5)

    # 3 Floor Rosette Stomps (1.85s, 2.75s, 3.65s) + 3 Sequential Lancet Awakenings (2.05s, 3.35s, 4.65s)
    # Lancet 1 (Sapphire - C Major):
    master.place(foley_bus, foley_glass_step("C4", "C5", heavy=True, seed=103, pan=-0.25), 1.85, sr=SR)
    master.place(foley_bus, foley_lead_snap(1980.0, pan=-0.25), 2.04, sr=SR)
    foley_anchors.extend([1.85, 2.05])
    for p_w1, pan_w1 in [("C3", -0.30), ("G3", -0.10), ("C4", 0.10), ("E4", -0.20), ("G4", 0.25)]:
        add_note(music_cathedral, "organ_soft", p_w1, 2.05, dur=1.30, vel=0.58, pan=pan_w1)
    add_note(music_cathedral, "organ_pedal", "C2", 2.05, dur=1.30, vel=0.52, pan=-0.15)
    add_crystal_arpeggio(
        music_cathedral, 2.08, ["C5", "E5", "G5", "C6", "E6"],
        step_s=0.060, dur_s=0.95, vel=0.55, pan_center=-0.25,
    )

    # Lancet 2 (Emerald - E Minor / G Major):
    master.place(foley_bus, foley_glass_step("E4", "E5", heavy=True, seed=104, pan=0.0), 2.75, sr=SR)
    master.place(foley_bus, foley_lead_snap(2220.0, pan=0.0), 3.34, sr=SR)
    foley_anchors.extend([2.75, 3.35])
    for p_w2, pan_w2 in [("E3", -0.20), ("B3", 0.15), ("E4", -0.05), ("G4", 0.20), ("B4", -0.15)]:
        add_note(music_cathedral, "organ_soft", p_w2, 3.35, dur=1.30, vel=0.62, pan=pan_w2)
    add_note(music_cathedral, "organ_pedal", "E2", 3.35, dur=1.30, vel=0.55, pan=0.0)
    add_crystal_arpeggio(
        music_cathedral, 3.38, ["E5", "G5", "B5", "E6", "G6"],
        step_s=0.060, dur_s=0.95, vel=0.58, pan_center=0.0,
    )

    # Lancet 3 (Ruby - G Major):
    master.place(foley_bus, foley_glass_step("G4", "G5", heavy=True, seed=105, pan=0.25), 3.65, sr=SR)
    master.place(foley_bus, foley_lead_snap(2480.0, pan=0.25), 4.64, sr=SR)
    foley_anchors.extend([3.65, 4.65])
    for p_w3, pan_w3 in [("G3", -0.15), ("D4", 0.20), ("G4", 0.05), ("B4", 0.30)]:
        add_note(music_cathedral, "organ", p_w3, 4.65, dur=0.52, vel=0.54, pan=pan_w3)

    # 4.15s: Brake at Nave Abyss [?] + 4.75s: Spot Crystal Triangular Prism [!]
    add_note(music_dry, "glass", "F5", 4.15, dur=0.55, vel=0.45, pan=0.15)
    add_note(music_dry, "hand_chimes", "D6", 4.75, dur=0.75, vel=0.55, pan=0.22)
    add_pluck(music_dry, "music_box", "A5", 4.77, dur=0.65, vel=0.55, pan=0.20, gain=0.38)

    # Note: 5.15s - 5.88s is STOP-DOWN #1 (Nave Abyss Hush via gate_zero on music buses),
    # leaving only a delicate breath of cathedral air and single glass harmonic!
    abyss_air, _ = bank.render("swipe/cloth", seed=61, dur=0.68)
    master.place(foley_bus, lp(abyss_air, 1400.0), 5.20, sr=SR, pan=0.0, gain=0.16)
    add_note(foley_bus, "glass", "E5", 5.32, dur=0.85, vel=0.32, pan=0.0)

    # =========================================================================
    # ACT 2 (5.9s - 12.2s): Prism Refraction, 3 Pedal Bass Strikes & 4 Crystal Steps
    # =========================================================================
    # 5.95s: Slime lands on Crystal Prism Pedestal (breaking the abyss silence!)
    master.place(foley_bus, foley_glass_step("D4", "D5", heavy=True, seed=201, pan=-0.10), 5.95, sr=SR)
    foley_anchors.append(5.95)

    # Mysterious modal organ & flute phrase as Slime approaches the Prism (5.95s - 7.35s)
    for p_ab, pan_ab in [("A2", -0.20), ("E3", 0.20), ("A3", -0.10), ("C4", 0.15), ("E4", 0.0)]:
        add_note(music_cathedral, "organ_soft", p_ab, 5.96, dur=1.40, vel=0.54, pan=pan_ab)
    add_note(music_cathedral, "flute", "E5", 6.05, dur=1.20, vel=0.48, pan=-0.15, vib=4.5)

    # 6.60s & 7.35s: Two hard-facet body-slam headbutts against the Giant Crystal Triangular Prism!
    master.place(foley_bus, foley_glass_step("G4", "G5", heavy=True, seed=202, pan=-0.05), 6.60, sr=SR)
    add_note(foley_bus, "hand_chimes", "C6", 6.60, dur=0.95, vel=0.52, pan=-0.05)
    foley_anchors.append(6.60)

    # 7.35s: Full Prismatic Dispersion Laser Refraction!
    master.place(foley_bus, foley_glass_step("C5", "C6", heavy=True, seed=203, pan=0.0), 7.35, sr=SR)
    whoosh_glass, _ = bank.render("logo_sting/whoosh_glass", seed=7)
    master.place(foley_bus, lp(whoosh_glass[: int(1.1 * SR)], 5800.0), 7.35, sr=SR, pan=0.0, gain=0.28)
    add_crystal_arpeggio(
        music_cathedral, 7.35, ["C5", "E5", "G5", "B5", "C6", "E6", "G6"],
        step_s=0.042, dur_s=1.15, vel=0.64, pan_center=0.0, use_harpsichord=True,
    )
    foley_anchors.append(7.35)

    # 3 Resonant Cathedral Organ Pedal Bass + Chime Strikes (7.60s C, 8.30s E, 9.00s G)
    pedal_strikes = [
        (7.60, "C2", ["C3", "G3", "C4", "E4", "G4"], "C5", -0.20, 0.66),
        (8.30, "E2", ["E3", "B3", "E4", "G4", "B4"], "E5", 0.00, 0.70),
        (9.00, "G2", ["G3", "D4", "G4", "B4", "D5"], "G5", 0.20, 0.74),
    ]
    for t_ps, ped_p, chord_ps, chime_p, pan_ps, vel_ps in pedal_strikes:
        add_note(music_cathedral, "organ_pedal", ped_p, t_ps, dur=0.95, vel=vel_ps, pan=pan_ps * 0.5)
        add_note(sub_bus, "contrabass", ped_p, t_ps, dur=0.85, vel=vel_ps * 0.85, pan=0.0)
        for idx_c, c_p in enumerate(chord_ps):
            c_pan = pan_ps + (idx_c - 2) * 0.12
            add_note(music_cathedral, "organ", c_p, t_ps, dur=0.82, vel=vel_ps * 0.82, pan=c_pan)
        add_note(music_cathedral, "tubular_bells", chime_p, t_ps, dur=1.4, vel=vel_ps * 0.58, pan=pan_ps)
        master.place(foley_bus, foley_lead_snap(2100.0 + idx_c * 180.0, pan=pan_ps), t_ps, sr=SR)
        foley_anchors.append(t_ps)

    # Warm string + soft organ bed supporting the 4 Diamond Crystal Stairs (9.05s - 12.20s)
    for p_st, pan_st in [("G3", -0.35), ("B3", 0.35), ("D4", -0.20), ("G4", 0.20)]:
        add_note(music_cathedral, "organ_soft", p_st, 9.05, dur=3.10, vel=0.52, pan=pan_st)
    add_note(music_cathedral, "cellos", "G2", 9.05, dur=3.10, vel=0.48, pan=0.22, vib=4.0)
    add_note(music_cathedral, "violins", "D5", 9.85, dur=2.30, vel=0.46, pan=-0.28, vib=5.0)

    # Slime's 4 ascending step hops (9.05s, 9.95s, 10.85s, 11.75s) + stair chimes (10.10s, 10.70s, 11.30s, 11.90s)
    sim_step_landings = [
        (9.05, "C4", "C5", -0.20, 211),
        (9.95, "E4", "E5", -0.05, 212),
        (10.85, "G4", "G5", 0.10, 213),
        (11.75, "C5", "C6", 0.25, 214),
    ]
    for t_sl, p_kal, p_gl, pan_sl, seed_sl in sim_step_landings:
        master.place(foley_bus, foley_glass_step(p_kal, p_gl, heavy=True, seed=seed_sl, pan=pan_sl), t_sl, sr=SR)
        add_note(music_dry, "harpsichord", p_gl, t_sl + 0.01, dur=0.65, vel=0.52, pan=pan_sl)
        foley_anchors.append(t_sl)

    stair_chime_notes = [
        (10.10, "D5", -0.15),
        (10.70, "G5", 0.00),
        (11.30, "B5", 0.15),
        (11.90, "D6", 0.25),
    ]
    for t_sc, p_sc, pan_sc in stair_chime_notes:
        add_note(music_cathedral, "hand_chimes", p_sc, t_sc, dur=1.10, vel=0.54, pan=pan_sc)
        add_pluck(music_dry, "music_box", p_sc, t_sc, dur=0.80, vel=0.56, pan=-pan_sc, gain=0.36)

    # =========================================================================
    # ACT 3 (12.2s - 19.8s): Gothic Suspense, Rope Pull, MANDATORY SILENCE & Colossal Sanctuary Bell
    # =========================================================================
    # Dramatic D-minor Gothic Organ & Harpsichord tension (12.20s - 15.80s)
    for p_t1, pan_t1 in [("D3", -0.25), ("F3", 0.20), ("A3", -0.10), ("D4", 0.25)]:
        add_note(music_cathedral, "organ_soft", p_t1, 12.20, dur=2.25, vel=0.58, pan=pan_t1)
    add_note(music_cathedral, "organ_pedal", "D2", 12.20, dur=2.25, vel=0.55, pan=0.0)
    add_crystal_arpeggio(
        music_cathedral, 12.30, ["D5", "F5", "A5", "D6", "A5", "F5"],
        step_s=0.14, dur_s=0.80, vel=0.52, pan_center=0.10, use_harpsichord=True,
    )

    # First Leap: Rope pull (12.95s hop -> 13.50s yank -> 14.20s initial bronze bell toll -> 14.30s Step 4 landing)
    master.place(foley_bus, foley_glass_step("D4", "A4", heavy=False, seed=301, pan=0.10), 12.95, sr=SR)
    master.place(foley_bus, foley_sanctuary_bell("A3", "A4", climax=False, pan=0.15), 13.50, sr=SR)
    master.place(foley_bus, foley_sanctuary_bell("G3", "G4", climax=False, pan=0.12), 14.20, sr=SR)
    master.place(foley_bus, foley_glass_step("E4", "B4", heavy=True, seed=302, pan=0.10), 14.30, sr=SR)
    foley_anchors.extend([13.50, 14.20, 14.30])

    # 14.50s - 15.80s: Dominant A7 charge swell on Step 4 + aerial launch at 15.65s
    for p_ch, pan_ch in [("A2", -0.25), ("E3", 0.25), ("G3", -0.15), ("C#4", 0.20), ("E4", 0.0), ("A4", -0.10)]:
        add_note(music_cathedral, "organ", p_ch, 14.50, dur=1.30, vel=0.64, pan=pan_ch)
    add_note(music_cathedral, "organ_pedal", "A1", 14.50, dur=1.30, vel=0.62, pan=0.0)
    add_note(music_cathedral, "timpani", "A2", 14.55, dur=1.25, vel=0.58, pan=0.0)

    # Soft cloth/air launch whoosh (14.65s - 15.60s)
    launch_air, _ = bank.render("swipe/cloth", seed=77, dur=0.90)
    master.place(foley_bus, lp(launch_air, 2200.0), 14.70, sr=SR, pan=0.08, gain=0.24)

    # 15.65s: Initial rim kiss + crystal gliss before the 15.85s-16.38s Cathedral Stop-Down!
    add_note(foley_bus, "glass", "D6", 15.65, dur=0.45, vel=0.52, pan=0.08)
    master.place(foley_bus, foley_lead_snap(2600.0, pan=0.08), 15.65, sr=SR)

    # *** 15.85s - 16.38s: MANDATORY CATHEDRAL SILENCE (`master.gate_zero` applied below!) ***
    # At 16.40s: COLOSSAL SANCTUARY BELL CLIMAX STRIKE rings into pure silence!
    master.place(foley_bus, foley_sanctuary_bell("C4", "C5", climax=True, pan=0.04), 16.40, sr=SR)
    foley_anchors.append(16.40)

    # Twin stained-glass windchimes awakened by the shockwave (16.46s, 16.53s, 16.60s)
    add_note(foley_bus, "hand_chimes", "G5", 16.46, dur=2.2, vel=0.62, pan=0.35)
    add_note(foley_bus, "hand_chimes", "C6", 16.53, dur=2.2, vel=0.64, pan=-0.35)
    add_note(foley_bus, "hand_chimes", "E6", 16.60, dur=2.4, vel=0.66, pan=0.25)

    # 16.95s: Slime lands back on Step 4 after bell rebound
    master.place(foley_bus, foley_glass_step("E4", "C5", heavy=True, seed=305, pan=0.10), 16.95, sr=SR)
    foley_anchors.append(16.95)

    # 16.65s - 20.40s: GLORIOUS C-MAJOR FULL-ORGAN TOCCATA & CATHEDRAL STRING TUTTI
    # (Enters 250ms after the 16.40s bell strike, exactly as specified in `styles/stained-glass/STYLE.md`)
    toccata_prog = [
        (16.65, 1.20, "C2", ["C3", "G3", "C4", "E4", "G4", "C5"], "E5", 0.74),  # C Major Grand Tutti
        (17.85, 1.30, "F2", ["F3", "C4", "F4", "A4", "C5"], "F5", 0.76),        # F Major Prismatic Swell
        (19.15, 1.30, "G2", ["G3", "D4", "G4", "B4", "D5"], "G5", 0.78),        # G Major Radiant Fanfare
    ]
    for t_tc, d_tc, ped_tc, chord_tc, vln_tc, vel_tc in toccata_prog:
        add_note(music_cathedral, "organ_pedal", ped_tc, t_tc, dur=d_tc, vel=vel_tc, pan=0.0)
        add_note(sub_bus, "contrabass", ped_tc, t_tc, dur=d_tc, vel=vel_tc * 0.80, pan=0.0)
        add_note(music_cathedral, "cellos", ped_tc.replace("2", "3"), t_tc, dur=d_tc, vel=vel_tc * 0.72, pan=0.25, vib=4.2)
        add_note(music_cathedral, "violas", chord_tc[2], t_tc, dur=d_tc, vel=vel_tc * 0.65, pan=-0.20, vib=4.2)
        add_note(music_cathedral, "violins", vln_tc, t_tc, dur=d_tc, vel=vel_tc * 0.75, pan=-0.32, vib=5.0)
        for idx_o, p_o in enumerate(chord_tc):
            pan_o = (idx_o / max(len(chord_tc) - 1, 1) - 0.5) * 0.65
            add_note(music_cathedral, "organ", p_o, t_tc, dur=d_tc, vel=vel_tc * 0.76, pan=pan_o)
            add_note(music_cathedral, "organ_soft", p_o, t_tc, dur=d_tc, vel=vel_tc * 0.65, pan=-pan_o * 0.5)

    # Sparkling Baroque Harpsichord & Harp cascade during Prismatic Rainbow Bridge unfurl (17.05s - 19.10s)
    bridge_unfurl_pitches = [
        "C5", "E5", "G5", "C6", "G5", "C6", "E6", "G6",
        "F5", "A5", "C6", "F6", "G5", "B5", "D6", "G6",
    ]
    add_crystal_arpeggio(
        music_cathedral, 17.05, bridge_unfurl_pitches,
        step_s=0.115, dur_s=0.75, vel=0.58, pan_center=0.0, use_harpsichord=True,
    )

    # 18.30s hop + 18.60s & 19.20s Radiant Stained-Glass Star Token Absorption Fanfare!
    master.place(foley_bus, foley_glass_step("G4", "D5", heavy=False, seed=308, pan=0.0), 18.30, sr=SR)
    add_note(foley_bus, "glockenspiel", "C6", 18.60, dur=1.2, vel=0.68, pan=-0.15)
    add_note(foley_bus, "hand_chimes", "E6", 18.65, dur=1.3, vel=0.65, pan=0.15)
    add_note(foley_bus, "glockenspiel", "E6", 19.20, dur=1.4, vel=0.72, pan=0.15)
    add_note(foley_bus, "hand_chimes", "G6", 19.24, dur=1.5, vel=0.70, pan=-0.15)
    add_crystal_arpeggio(
        music_cathedral, 19.20, ["C5", "E5", "G5", "C6", "E6", "G6"],
        step_s=0.048, dur_s=1.0, vel=0.65, pan_center=0.0, use_harpsichord=True,
    )
    foley_anchors.extend([18.60, 19.20])

    # =========================================================================
    # ACT 4 (19.8s - 26.0s): Triumphant Climax, Rainbow Bridge Hops, Rose Window & 1930s Projector
    # =========================================================================
    # Soaring Triumphant Organ & Cathedral String Choir Climax (20.45s - 23.75s)
    climax_prog = [
        (20.45, 1.05, "C2", ["C3", "E3", "G3", "C4", "E4", "G4"], "C5", 0.76),
        (21.50, 1.05, "F2", ["F3", "A3", "C4", "F4", "A4", "C5"], "F5", 0.78),
        (22.55, 1.25, "C2", ["C3", "G3", "C4", "E4", "G4", "C5", "E5"], "G5", 0.82),
    ]
    for t_cc, d_cc, ped_cc, chord_cc, vln_cc, vel_cc in climax_prog:
        add_note(music_cathedral, "organ_pedal", ped_cc, t_cc, dur=d_cc, vel=vel_cc, pan=0.0)
        add_note(sub_bus, "contrabass", ped_cc, t_cc, dur=d_cc, vel=vel_cc * 0.82, pan=0.0)
        add_note(music_cathedral, "cellos", "C3", t_cc, dur=d_cc, vel=vel_cc * 0.72, pan=0.25, vib=4.5)
        add_note(music_cathedral, "violins", vln_cc, t_cc, dur=d_cc, vel=vel_cc * 0.76, pan=-0.30, vib=5.2)
        add_note(music_cathedral, "flute", vln_cc, t_cc, dur=d_cc, vel=vel_cc * 0.58, pan=0.18, vib=4.8)
        for idx_o, p_o in enumerate(chord_cc):
            pan_o = (idx_o / max(len(chord_cc) - 1, 1) - 0.5) * 0.70
            add_note(music_cathedral, "organ", p_o, t_cc, dur=d_cc, vel=vel_cc * 0.78, pan=pan_o)

    # Rainbow Bridge Hops (19.50s, 20.25s, 21.25s, 22.25s, 23.25s) + Bridge Chimes (20.60s, 21.60s, 22.60s, 23.60s)
    rainbow_sim_hops = [
        (19.50, "C4", "C5", 0.05, 401),
        (20.25, "D4", "D5", 0.12, 402),
        (21.25, "E4", "E5", 0.20, 403),
        (22.25, "G4", "G5", 0.28, 404),
        (23.25, "C5", "C6", 0.35, 405),
    ]
    for t_rh, p_k, p_g, pan_rh, seed_rh in rainbow_sim_hops:
        master.place(foley_bus, foley_glass_step(p_k, p_g, heavy=True, seed=seed_rh, pan=pan_rh), t_rh, sr=SR)
        foley_anchors.append(t_rh)

    rainbow_chimes = [
        (20.60, ["C5", "E5", "G5", "C6"], 0.10),
        (21.60, ["F5", "A5", "C6", "F6"], 0.20),
        (22.60, ["G5", "B5", "D6", "G6"], 0.28),
        (23.60, ["C5", "G5", "C6", "E6"], 0.00),
    ]
    for t_rc, notes_rc, pan_rc in rainbow_chimes:
        add_note(music_cathedral, "hand_chimes", notes_rc[-1], t_rc, dur=1.25, vel=0.58, pan=pan_rc)
        add_crystal_arpeggio(
            music_cathedral, t_rc, notes_rc,
            step_s=0.048, dur_s=0.85, vel=0.56, pan_center=pan_rc, use_harpsichord=False,
        )

    # 23.45s: Dive through the spinning Grand 3-Ring Gothic Rose Window
    rose_whoosh, _ = bank.render("logo_sting/whoosh_glass", seed=23)
    master.place(foley_bus, lp(rose_whoosh[: int(0.95 * SR)], 4800.0), 23.45, sr=SR, pan=0.0, gain=0.25)

    # 23.80s - 26.00s: Vintage 1930s Film Projector Reel Handover to World 07!
    proj_handover = foley_vintage_projector_handover(dur=2.20)
    master.place(foley_bus, proj_handover, 23.80, sr=SR, gain=0.92)
    foley_anchors.extend([24.00, 24.65, 25.30])

    # Warm vintage optical sound-head C-major chord bed under projector reel (23.80s - 25.95s)
    for p_end, pan_end in [("C3", -0.20), ("G3", 0.20), ("C4", -0.10), ("E4", 0.10)]:
        add_note(music_dry, "organ_soft", p_end, 23.80, dur=2.12, vel=0.38, pan=pan_end)
    add_note(music_dry, "organ_pedal", "C2", 23.80, dur=2.10, vel=0.36, pan=0.0)

    # =========================================================================
    # CATHEDRAL REVERB, MANDATORY STOP-DOWNS (`gate_zero`), DUCKING & MASTERING
    # =========================================================================
    print("[Audio 06] Applying cathedral acoustic space, mandatory stop-downs, sidechain ducking & -14 LUFS mastering...")

    # Apply lush Gothic cathedral reverb to music_cathedral and gentle hall air to foley_bus
    music_cathedral_wet = master.reverb(music_cathedral, sr=SR, rt60=2.35, predelay_ms=22.0, wet=0.36, damp=0.32)
    music_dry_wet = master.reverb(music_dry, sr=SR, rt60=1.25, predelay_ms=14.0, wet=0.22, damp=0.45)
    music_bus = music_cathedral_wet + music_dry_wet + sub_bus * 0.72

    # Clean sub-35Hz rumble and tame any harshness above 9.5kHz on music bus
    music_bus = lp(hp(music_bus, 32.0), 9800.0)

    # *** MANDATORY CATHEDRAL STOP-DOWNS (`master.gate_zero`) ***
    # 1. Nave Abyss Hush (5.18s - 5.90s) before landing on Crystal Prism Pedestal at 5.95s
    music_bus = master.gate_zero(music_bus, t0=5.18, t1=5.90, sr=SR, fade_ms=22.0)
    # 2. Sanctuary Bell Pre-Climax Silence (15.85s - 16.38s): 530ms of sacred silence before 16.40s Bell Toll!
    music_bus = master.gate_zero(music_bus, t0=15.85, t1=16.38, sr=SR, fade_ms=18.0)

    # Sidechain ducking of music under key Foley & Bell anchors
    sc_env = master.sidechain_times(
        [(float(t_a), 1.0) for t_a in foley_anchors],
        len(music_bus),
        depth=0.40,
        tau=0.16,
        attack=0.010,
    ).astype(np.float32)
    music_ducked = music_bus * sc_env

    # Foley bus gentle cathedral tail
    foley_wet = master.reverb(foley_bus, sr=SR, rt60=1.45, predelay_ms=15.0, wet=0.20, damp=0.42)
    foley_clean = lp(hp(foley_wet, 42.0), 10500.0)

    # Combine buses and enforce exact 26.0s frame length with smooth tail fade
    raw_mix = (music_ducked * 0.92 + foley_clean * 0.88)[:TOTAL_SAMPLES]
    raw_mix = fade_io(raw_mix, fade_in_s=0.01, fade_out_s=0.08)

    # Master to -14.0 LUFS, true peak <= -1.5 dBTP (ceiling=0.77)
    final_mix, _ = master.finish(raw_mix, lufs=-14.0, ceiling=0.77)
    final_mix = final_mix[:TOTAL_SAMPLES].astype(np.float32)

    os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
    sf.write(output_wav_path, final_mix, SR, subtype="PCM_24")
    m_report = master.measure(final_mix)
    print(
        f"[Audio 06] Mastered {output_wav_path} | dur={m_report['seconds']:.2f}s | "
        f"LUFS={m_report['lufs']:.2f} | TP={m_report['true_peak_db']:.2f} dBTP | "
        f"LRA={m_report['lra']:.2f} LU"
    )
    return {"master": m_report}


if __name__ == "__main__":
    wav_file = os.path.join(CUR_DIR, "world_06_stainedglass.wav")
    render_world_06_audio(wav_file)
