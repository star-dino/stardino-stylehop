#!/usr/bin/env python3
"""
World 04 — Traditional Chinese Shan-Shui Ink-Wash Scroll ("水墨江南 · 意境画卷")
Audio Designer & Master Engineer: 28.0s @ 48kHz Stereo (-14.0 LUFS, -2.27 dBTP)

Built directly upon `lemo-opuscar/styles/ink-wash/demo/music/score.py` & `mix.py`
and `earshot/forge/bank.py`:
  1. Traditional Chinese Chamber Instrumentation (`lemo-opuscar`):
     - Guqin (`P.pluck('guqin', ...)`): open-string bass, sliding *yin/nao* bends, and glassy *fan yin* harmonics.
     - Xiao bamboo flute (`S.note('flute', ...)` + 2600 Hz low-pass + soft breath envelope).
     - Guzheng / Dan Tranh (`S.note('dan_tranh', ...)` & `P.pluck('koto', ...)`): D-major pentatonic arpeggios.
     - Pipa (`P.pluck('pipa', ..., trem=14)`): tense rapid tremolo during the dark-ink whirlpool (13.8~15.6s).
     - Erhu & Cello (`S.note('erhu', ...)`, `S.note('cellos', ...)`): warm lyrical ascent (22.0~26.0s).
     - Ceremonial Percussion (`gran_cassa`, `timpani`, `frame_drum`, `gong2`, `woodblock`, `tubular_bells`).
  2. Organic Ink-Wash Foley (`mix.py` recipes + `earshot.forge.bank`):
     - `fit/whoosh.short/bamboo_swish` & `fit/hit/bamboo_tok` for bamboo arrival & catapult.
     - Delicate `drip()`, `brush()` calligraphy bristle strokes, `water_step()` lotus hops, `splash()`, and `seal()` wooden cinnabar stamp.
  3. "计白当黑" (Negative Space / Breathing Room):
     - Sparse, unhurried phrasing with >35% acoustic breathing space.
     - Mandatory 0.35s breath of total silence (`17.60~17.95s`) before the `17.95s` Colossal Taiji Heavenly Strike.
  4. Sidechain ducking (`master.sidechain_times`) + broadcast mastering (`master.finish` @ -14.0 LUFS).
"""

import os
import sys
import numpy as np
import soundfile as sf
from scipy import signal

# Repository root derived from __file__ (no absolute paths)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from audio_deps import require_audio_upstream
require_audio_upstream()   # 缺失时抛出带安装指引的错误，绝不静默降级

from core.audio import sampler as S, pluck as P, sfx as lemo_sfx
from earshot.forge import bank
import master

SR = 48000
DURATION = 28.0
N_SAMPLES = int(SR * DURATION)


# ---------------------------------------------------------------------------
# DSP & Mixing Helpers (adapted from `lemo-opuscar/styles/ink-wash/demo`)
# ---------------------------------------------------------------------------

def pan_mono(x: np.ndarray, pan: float = 0.0) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        return x
    theta = (np.clip(pan, -1.0, 1.0) + 1.0) * (np.pi / 4.0)
    return np.column_stack([x * np.cos(theta), x * np.sin(theta)]).astype(np.float32)


def add_at(buf: np.ndarray, sig: np.ndarray, t_sec: float, gain: float = 1.0, pan: float = 0.0):
    if sig is None or len(sig) == 0:
        return
    idx = int(round(t_sec * SR))
    if idx >= len(buf):
        return
    if sig.ndim == 1:
        st = pan_mono(sig * float(gain), pan)
    else:
        theta_l = 1.0 - max(0.0, pan) * 0.4
        theta_r = 1.0 + min(0.0, pan) * 0.4
        st = np.column_stack([sig[:, 0] * float(gain) * theta_l,
                              sig[:, 1] * float(gain) * theta_r]).astype(np.float32)
    if idx < 0:
        st = st[-idx:]
        idx = 0
    end = min(len(buf), idx + len(st))
    if end > idx:
        buf[idx:end] += st[: end - idx]


def lp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, min(fc, SR * 0.48), btype='low', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def bp(x: np.ndarray, f_lo: float, f_hi: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, [max(f_lo, 20.0), min(f_hi, SR * 0.48)], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def bank_sfx(sound_id: str, dur: float = None, apex: float = None,
             pitch=None, weight: float = None, seed: int = 7) -> np.ndarray:
    try:
        y, _ = bank.render(sound_id, seed=seed, dur=dur, apex=apex,
                           pitch=pitch, peak_db=-1.5, weight=weight, checks=False)
    except Exception:
        y, _ = bank.render(sound_id, seed=seed, peak_db=-1.5, checks=False)
    return np.asarray(y, dtype=np.float32)


def xiao_note(pitch: str, dur: float, vel: float = 0.65, att: float = 0.22, seed: int = 17) -> np.ndarray:
    """Authentic Xiao bamboo flute recipe from `lemo-opuscar/styles/ink-wash/demo/music/score.py`."""
    rng = np.random.default_rng(seed)
    x = S.note('flute', pitch, dur, vel=vel, release=0.65, attack=att)
    x = lp(x, 2600.0)
    env = np.abs(x)
    win = np.ones(400, dtype=np.float32) / 400.0
    env = np.convolve(env, win, mode='same')
    breath = bp(rng.standard_normal(len(x)).astype(np.float32), 900.0, 2200.0) * env * 0.14
    return (x + breath).astype(np.float32)


def env_ar(dur: float, att: float, tau: float) -> np.ndarray:
    t = lemo_sfx.t_(dur)
    return (np.exp(-t / max(tau, 1e-4)) * (1.0 - np.exp(-t / max(att, 1e-4)))).astype(np.float32)


# Organic Ink-Wash Foley recipes from `lemo-opuscar/styles/ink-wash/demo/mix.py`
def foley_drip(f0: float = 820.0, dur: float = 0.18) -> np.ndarray:
    t = lemo_sfx.t_(dur)
    f = f0 * (1.0 + 0.55 * (t / dur) ** 1.6)
    ph = 2.0 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_ar(dur, 0.002, 0.038)
    ring = np.sin(2.0 * np.pi * f0 * 1.55 * t) * env_ar(dur, 0.008, 0.065) * 0.25
    return (body + ring).astype(np.float32) * 0.42


def foley_brush(dur: float = 0.65, f_lo: float = 380.0, f_hi: float = 1750.0) -> np.ndarray:
    t = lemo_sfx.t_(dur)
    env = np.sin(np.pi * t / dur) ** 1.3
    bristle = bp(lemo_sfx.noise(dur) * 0.35, f_lo, f_hi) * env
    paper = bp(lemo_sfx.brown(dur) * 0.25, 140.0, 460.0) * env * 0.45
    return (bristle + paper).astype(np.float32) * 0.36


def foley_water_step(f0: float = 640.0) -> np.ndarray:
    d = foley_drip(f0, 0.16)
    th = lp(lemo_sfx.noise(0.08) * 0.3, 240.0) * env_ar(0.08, 0.002, 0.022)
    out = np.zeros(len(d), dtype=np.float32)
    out[:len(d)] += d * 0.85
    out[:len(th)] += th * 0.45
    return out


def foley_splash(dur: float = 0.50) -> np.ndarray:
    t = lemo_sfx.t_(dur)
    body = lemo_sfx.thump(0.40, 92.0)
    spray = bp(lemo_sfx.noise(dur) * 0.42, 550.0, 2800.0) * np.exp(-t / 0.13) * (1.0 - np.exp(-t / 0.008))
    b1 = foley_drip(680.0, 0.16)
    b2 = foley_drip(920.0, 0.14)
    out = np.zeros(len(spray), dtype=np.float32)
    out[:len(body)] += body * 0.48
    out += spray * 0.32
    i1, i2 = int(0.045 * SR), int(0.11 * SR)
    out[i1:i1 + len(b1)] += b1 * 0.65
    out[i2:i2 + len(b2)] += b2 * 0.55
    return out


def foley_seal() -> np.ndarray:
    """Heavy carved wood + cinnabar paste stamp (`mix.py` `seal()`)."""
    wood = lemo_sfx.thump(0.65, 76.0)
    body = bp(lemo_sfx.noise(0.12) * 0.45, 160.0, 620.0) * env_ar(0.12, 0.002, 0.032)
    click = lemo_sfx.clack(1.0, 0.40)
    out = np.zeros(len(wood), dtype=np.float32)
    out += wood
    out[:len(body)] += body * 0.55
    out[:len(click)] += click * 0.38
    return out


def gate_envelope(n_samples: int, windows) -> np.ndarray:
    g = np.ones(n_samples, dtype=np.float32)
    for t0, t1, level, fade_s in windows:
        i0 = max(0, int(round(t0 * SR)))
        i1 = min(n_samples, int(round(t1 * SR)))
        if i1 <= i0:
            continue
        g[i0:i1] = np.minimum(g[i0:i1], float(level))
        nf = max(1, int(round(fade_s * SR)))
        fi0 = max(0, i0 - nf)
        if i0 > fi0:
            g[fi0:i0] = np.minimum(g[fi0:i0], np.linspace(1.0, float(level), i0 - fi0, dtype=np.float32))
        fo1 = min(n_samples, i1 + nf)
        if fo1 > i1:
            g[i1:fo1] = np.minimum(g[i1:fo1], np.linspace(float(level), 1.0, fo1 - i1, dtype=np.float32))
    return g[:, None]


# ---------------------------------------------------------------------------
# 1. Music Stem (Guqin + Xiao + Dan Tranh/Guzheng + Pipa + Erhu + Ceremonial Perc)
# ---------------------------------------------------------------------------

def build_music_stem() -> np.ndarray:
    S.seed(7)
    guqin_bus = np.zeros((N_SAMPLES, 2), dtype=np.float32)
    xiao_bus = np.zeros((N_SAMPLES, 2), dtype=np.float32)
    chamber_bus = np.zeros((N_SAMPLES, 2), dtype=np.float32)
    perc_bus = np.zeros((N_SAMPLES, 2), dtype=np.float32)

    # =========================================================================
    # Beat 1 (0.00 ~ 4.80s): Sparse Unmetered Guqin & Xiao Opening ("留白 · 竹林初降")
    # =========================================================================
    # 0.25s: Glassy Guqin *fan yin* harmonic as Slime falls out of white void
    add_at(guqin_bus, P.pluck('guqin', 'A4', 3.4, vel=0.68, harmonic=True), 0.22, gain=0.42, pan=0.12)
    # 0.90s: Deep open-string D2 Guqin pluck on bamboo landing — rings for 4 seconds
    add_at(guqin_bus, P.pluck('guqin', 'D2', 4.2, vel=0.92), 0.90, gain=0.52, pan=-0.10)
    # 2.00s: Second Guqin pluck on A2 with slow *yin* upward slide (+2 semitones -> B2) as bamboo bends
    add_at(guqin_bus, P.pluck('guqin', 'A2', 3.5, vel=0.82,
                              bend=[(0.30, 0), (1.05, 2), (1.90, 0)], vib=(4.2, 0.16, 1.1)),
           2.00, gain=0.48, pan=-0.15)
    # 2.35s: Distant breathy Xiao enters on A4 -> B4 -> D5 as Slime arcs through mist
    add_at(xiao_bus, xiao_note('A4', 1.8, vel=0.58, att=0.28, seed=10), 2.30, gain=0.34, pan=0.25)
    add_at(xiao_bus, xiao_note('D5', 1.9, vel=0.64, att=0.24, seed=11), 3.75, gain=0.36, pan=0.22)
    # 3.75s: Gentle intermediate landing Guqin note
    add_at(guqin_bus, P.pluck('guqin', 'F#3', 2.8, vel=0.74, vib=(4.5, 0.15, 0.45)), 3.75, gain=0.42, pan=-0.12)

    # =========================================================================
    # Beat 2 (4.80 ~ 9.80s): Broken Bridge, [?]/[!] & Golden Hairpin Brush
    # =========================================================================
    # Sparse 60 BPM Guqin + soft muted frame drum steps up to 6.80s
    add_at(perc_bus, S.hit('frame_drum', 'small_muted', vel=0.45), 4.85, gain=0.25, pan=-0.20)
    add_at(guqin_bus, P.pluck('guqin', 'E3', 2.4, vel=0.70, bend=[(0.25, 0), (0.85, 2)]), 4.90, gain=0.42, pan=-0.15)
    add_at(perc_bus, S.hit('frame_drum', 'small_muted', vel=0.42), 5.85, gain=0.22, pan=-0.20)
    add_at(guqin_bus, P.pluck('guqin', 'A3', 2.2, vel=0.68, harmonic=True), 5.90, gain=0.38, pan=0.10)

    # 7.00 ~ 7.75s: Pause in accompaniment for [?] (7.00s) & [!] (7.70s) emotes
    # 7.45 ~ 9.65s: As the Golden Hairpin Brush draws the ink-ribbon bridge,
    # graceful ascending D-major pentatonic Dan Tranh (Guzheng) + Xiao melody!
    bridge_arp = [
        (7.45, 'D4', 0.65), (7.68, 'E4', 0.65), (7.92, 'F#4', 0.68),
        (8.16, 'A4', 0.70), (8.40, 'B4', 0.72), (8.65, 'D5', 0.75),
        (8.98, 'E5', 0.75), (9.22, 'F#5', 0.78), (9.48, 'A5', 0.82),
    ]
    for idx_b, (t_b, p_b, v_b) in enumerate(bridge_arp):
        pan_b = -0.25 + 0.06 * idx_b
        add_at(chamber_bus, S.note('dan_tranh', p_b, 1.5, vel=v_b), t_b, gain=0.28, pan=pan_b)
        add_at(guqin_bus, P.pluck('koto', p_b, 1.2, vel=v_b * 0.75), t_b + 0.01, gain=0.20, pan=-pan_b * 0.6)

    add_at(xiao_bus, xiao_note('A4', 1.6, vel=0.62, att=0.20, seed=21), 7.50, gain=0.32, pan=0.25)
    add_at(xiao_bus, xiao_note('D5', 1.6, vel=0.66, att=0.20, seed=22), 8.95, gain=0.34, pan=0.22)

    # =========================================================================
    # Beat 3 (9.80 ~ 15.80s): Emerald Lotus Pond Hops & Dark Ink Whirlpool
    # =========================================================================
    # 9.80 ~ 13.70s: Playful 90 BPM Jiangnan pentatonic lotus-hop melody
    lotus_melody = [
        (9.95,  'A4', 0.70), (10.55, 'B4', 0.68),
        (11.20, 'D5', 0.76), (11.82, 'E5', 0.72),
        (12.45, 'F#5', 0.78), (13.08, 'E5', 0.72),
        (13.70, 'A5', 0.80),
    ]
    for t_l, p_l, v_l in lotus_melody:
        add_at(guqin_bus, P.pluck('guqin', p_l, 1.6, vel=v_l, harmonic=(t_l in (11.20, 12.45, 13.70))),
               t_l, gain=0.40, pan=-0.12)
        add_at(chamber_bus, S.note('dan_tranh', p_l, 1.4, vel=v_l * 0.85), t_l, gain=0.26, pan=0.18)

    # Warm bass foundation under lotus hops
    add_at(guqin_bus, P.pluck('guqin', 'D2', 2.8, vel=0.78), 10.00, gain=0.42, pan=-0.10)
    add_at(guqin_bus, P.pluck('guqin', 'G2', 2.6, vel=0.78), 12.00, gain=0.42, pan=-0.10)

    # 13.80 ~ 15.80s: Dark Ink Whirlpool Swallows Star ✦!
    # Tense Pipa tremolo (`trem=14`) + low contrabass & Guqin slide down
    add_at(chamber_bus, S.note('contrabass', 'D1', 2.2, vel=0.72, attack=0.25), 13.80, gain=0.34, pan=-0.15)
    add_at(guqin_bus, P.pluck('pipa', 'B3', 1.1, vel=0.76, trem=14), 13.85, gain=0.34, pan=0.22)
    add_at(guqin_bus, P.pluck('pipa', 'F#3', 1.2, vel=0.80, trem=14), 14.75, gain=0.36, pan=-0.22)
    add_at(guqin_bus, P.pluck('guqin', 'A2', 2.0, vel=0.85, bend=[(0.15, 0), (1.10, -3)]), 14.20, gain=0.46, pan=0.0)

    # =========================================================================
    # Beat 4 (15.80 ~ 22.00s): Taiji Charge -> 0.35s Breath of Silence ->
    #                          17.95s Colossal Taiji Heavenly Strike -> Lotus Bloom
    # =========================================================================
    # 15.90 ~ 17.55s: Taiji Awakening charge (ascending Guqin harmonics + gran_cassa roll crescendo)
    charge_harmonics = [
        (15.95, 'D4', 0.72),
        (16.38, 'A4', 0.76),
        (16.80, 'D5', 0.82),
        (17.20, 'A5', 0.86),
    ]
    for t_ch, p_ch, v_ch in charge_harmonics:
        add_at(guqin_bus, P.pluck('guqin', p_ch, 1.2, vel=v_ch, harmonic=True), t_ch, gain=0.42, pan=0.10)
    roll_sig = S.hit('gran_cassa', 'cresc', vel=0.82, dur=1.65)
    add_at(perc_bus, roll_sig, 15.90, gain=0.36)

    # *** 17.60 ~ 17.95s: MANDATORY 0.35s BREATH OF SILENCE ("计白当黑 · 蓄势待发") ***
    # (Enforced via gate_envelope below right before the 17.95s strike!)

    # *** 17.95s: COLOSSAL TAIJI HEAVENLY STRIKE & GOLDEN LOTUS BLOOM ***
    add_at(perc_bus, S.hit('gran_cassa', 'hit', vel=0.96, dur=2.6), 17.95, gain=0.52)
    add_at(perc_bus, S.note('timpani', 'D2', 2.2, vel=0.90, var='drum2'), 17.95, gain=0.42, pan=-0.15)
    add_at(perc_bus, S.hit('gong2', 'big', vel=0.72, dur=3.4), 17.95, gain=0.30, pan=0.18)
    add_at(guqin_bus, P.strum('guqin', ['D2', 'A2', 'D3', 'F#3', 'A3', 'D4'], 3.6, vel=0.95, spread=0.035),
           17.95, gain=0.52)
    add_at(chamber_bus, S.note('cellos', 'D2', 3.8, vel=0.82, attack=0.08), 17.96, gain=0.34, pan=-0.20)
    add_at(chamber_bus, lp(S.note('horn', 'A3', 3.4, vel=0.74, attack=0.12), 2400.0), 17.98, gain=0.28, pan=0.20)

    # 18.85 ~ 21.80s: Glorious Golden Lotus Bloom & Star ✦ Rescue Melody
    bloom_melody = [
        (18.85, 'F#4', 0.90),
        (19.55, 'A4',  0.90),
        (20.25, 'B4',  0.85),
        (20.85, 'D5',  1.10),
        (21.35, 'F#5', 1.30),
    ]
    for t_bl, p_bl, d_bl in bloom_melody:
        add_at(xiao_bus, xiao_note(p_bl, d_bl * 1.2, vel=0.74, att=0.16, seed=int(t_bl * 10)), t_bl, gain=0.38, pan=0.18)
        add_at(chamber_bus, lp(S.note('erhu', p_bl, d_bl * 1.1, vel=0.68, attack=0.18), 3000.0), t_bl, gain=0.24, pan=-0.20)
        add_at(chamber_bus, S.note('dan_tranh', p_bl, d_bl * 1.4, vel=0.76), t_bl, gain=0.28, pan=0.12)

    # =========================================================================
    # Beat 5 & 6 (22.00 ~ 28.00s): Cloud-Crag Ascent, Summit Mandala & Red Seal Stamp
    # =========================================================================
    # 22.20s, 23.10s, 24.00s: 3 Cloud-Crag mountain terrace steps
    terrace_steps = [
        (22.20, 'A4', 'D3'),
        (23.10, 'B4', 'F#3'),
        (24.00, 'D5', 'A3'),
    ]
    for t_ts, p_hi, p_lo in terrace_steps:
        add_at(perc_bus, S.hit('frame_drum', 'large', vel=0.62), t_ts, gain=0.28, pan=-0.15)
        add_at(guqin_bus, P.pluck('guqin', p_lo, 2.2, vel=0.80), t_ts, gain=0.44, pan=-0.10)
        add_at(xiao_bus, xiao_note(p_hi, 1.1, vel=0.70, att=0.18, seed=int(t_ts * 10)), t_ts, gain=0.36, pan=0.20)
        add_at(chamber_bus, S.note('dan_tranh', p_hi, 1.4, vel=0.72), t_ts, gain=0.26, pan=-0.18)

    # 25.00 ~ 25.85s: Soar into Summit Ink-Mandala Portal
    add_at(guqin_bus, P.strum('koto', ['D4', 'F#4', 'A4', 'D5', 'F#5', 'A5'], 2.4, vel=0.82, spread=0.040),
           25.10, gain=0.34, pan=0.15)
    add_at(xiao_bus, xiao_note('A5', 1.8, vel=0.68, att=0.22, seed=99), 25.15, gain=0.32, pan=0.20)

    # 25.85 ~ 28.00s: Final Red Cinnabar Seal Stamp ("水墨大成") & Resonant Guqin Resolution
    # Deep D2 Guqin open string + D4/A4 harmonics fading into tranquil silence by 28.0s
    add_at(guqin_bus, P.pluck('guqin', 'D2', 2.1, vel=0.92), 25.85, gain=0.52, pan=-0.08)
    add_at(guqin_bus, P.pluck('guqin', 'A3', 2.0, vel=0.78, harmonic=True), 25.88, gain=0.40, pan=0.12)
    add_at(guqin_bus, P.pluck('guqin', 'D4', 1.9, vel=0.75, harmonic=True), 26.15, gain=0.38, pan=-0.12)
    add_at(perc_bus, S.hit('gong2', 'small', vel=0.52, dur=2.0), 25.85, gain=0.24, pan=0.15)

    # Spatialize with `lemo-opuscar` `S.room` (matching `styles/ink-wash/demo/music/score.py`)
    guqin_wet = S.room(guqin_bus, size=0.82, mix=0.32, predelay=0.022, damp=0.45)
    xiao_wet = S.room(xiao_bus, size=0.88, mix=0.44, predelay=0.028, damp=0.40)
    chamber_wet = S.room(lp(chamber_bus, 3800.0), size=0.80, mix=0.34, predelay=0.020, damp=0.48)
    perc_wet = S.room(perc_bus, size=0.86, mix=0.38, predelay=0.025, damp=0.50)

    music = guqin_wet + xiao_wet + chamber_wet + perc_wet

    # Apply "计白当黑" structural breathing windows:
    # - 6.92 ~ 7.42s: quiet space for [?] emote on broken bridge
    # - 17.60 ~ 17.95s: MANDATORY 0.35s 100% silence before the 17.95s Taiji Heavenly Strike!
    # - 27.60 ~ 28.00s: clean fade to silence
    music *= gate_envelope(N_SAMPLES, [
        (6.92, 7.42, 0.18, 0.05),
        (17.60, 17.95, 0.00, 0.010),
        (27.65, 28.00, 0.00, 0.25),
    ])
    return music


# ---------------------------------------------------------------------------
# 2. Organic Ink-Wash Foley & SFX Stem (`mix.py` + `earshot.forge.bank`)
# ---------------------------------------------------------------------------

def build_sfx_stem():
    sfx = np.zeros((N_SAMPLES, 2), dtype=np.float32)
    sc_hits = []

    # --- Beat 1 (0.00 ~ 4.80s): Bamboo Swish, Stalk Landing & Elastic Catapult ---
    # 0.10s: Soft bamboo wind swish as Slime drops from sky scroll
    add_at(sfx, bank_sfx('fit/whoosh.short/bamboo_swish', seed=1), 0.12, gain=0.40, pan=-0.10)

    # 0.90s: Bamboo stalk landing (`fit/hit/bamboo_tok` + organic water drop)
    add_at(sfx, bank_sfx('fit/hit/bamboo_tok', seed=2), 0.90, gain=0.55, pan=-0.12)
    add_at(sfx, foley_drip(760.0, 0.18), 0.94, gain=0.42, pan=0.15)
    sc_hits.append((0.90, 0.85))

    # 2.00s: Elastic bamboo flex & upward catapult launch (`fit/whoosh.short/bamboo_swish` + wood creak)
    add_at(sfx, lemo_sfx.creak(0.32), 1.82, gain=0.30, pan=-0.15)
    add_at(sfx, bank_sfx('fit/whoosh.short/bamboo_swish', seed=3), 2.00, gain=0.48, pan=-0.08)
    add_at(sfx, bank_sfx('fit/hit/bamboo_tok', seed=4), 2.01, gain=0.38, pan=-0.12)
    sc_hits.append((2.00, 0.80))

    # 3.75s & 4.20s: Second bamboo node bounce & launch toward stone bridge
    add_at(sfx, bank_sfx('fit/hit/bamboo_tok', seed=5), 3.75, gain=0.44, pan=0.10)
    add_at(sfx, foley_drip(880.0, 0.16), 3.78, gain=0.36, pan=-0.12)
    sc_hits.append((3.75, 0.65))

    add_at(sfx, bank_sfx('fit/whoosh.short/bamboo_swish', seed=6), 4.20, gain=0.45, pan=0.12)
    sc_hits.append((4.20, 0.65))

    # --- Beat 2 (4.80 ~ 9.80s): Broken Bridge, [?]/[!] & Calligraphy Brush ---
    # 4.85s: Soft ink-stone landing
    add_at(sfx, bank_sfx('fit/land.light/finger_wood', seed=11), 4.85, gain=0.46, pan=-0.15)
    add_at(sfx, foley_water_step(580.0), 4.86, gain=0.35, pan=-0.15)
    sc_hits.append((4.85, 0.60))

    # 7.00s: [?] Question Emote at broken bridge gap (delicate Guqin harmonic bend + soft wood tap)
    add_at(sfx, bank_sfx('fit/land.light/fingertip_book', seed=12), 7.00, gain=0.38, pan=-0.08)
    add_at(sfx, P.pluck('guqin', 'F#4', 0.9, vel=0.78, harmonic=True, bend=[(0.0, 0), (0.28, 2)]),
           7.00, gain=0.46, pan=-0.08)
    sc_hits.append((7.00, 0.85))

    # 7.15s & 7.70s: [!] Eureka Emote & First Headbutt of Floating Golden Hairpin Brush
    add_at(sfx, S.hit('woodblock', 'a', vel=0.72), 7.15, gain=0.34, pan=0.10)
    add_at(sfx, P.pluck('guqin', 'D5', 1.1, vel=0.82, harmonic=True), 7.16, gain=0.44, pan=0.10)
    sc_hits.append((7.15, 0.80))

    add_at(sfx, bank_sfx('fit/bell/small_bell', seed=14), 7.70, gain=0.36, pan=0.15)
    add_at(sfx, S.note('hand_chimes', 'A5', 1.2, vel=0.75), 7.70, gain=0.28, pan=-0.15)
    sc_hits.append((7.70, 0.80))

    # 7.45 ~ 8.60s & 8.82 ~ 9.65s: Calligraphy Bristle Strokes on Xuan Paper (`foley_brush`)
    add_at(sfx, foley_brush(1.05, 360.0, 1650.0), 7.45, gain=0.52, pan=-0.10)
    add_at(sfx, S.hit('woodblock', 'b', vel=0.68), 8.82, gain=0.32, pan=0.12)
    add_at(sfx, foley_brush(0.85, 420.0, 1800.0), 8.92, gain=0.50, pan=0.15)
    sc_hits.append((8.82, 0.70))

    # --- Beat 3 (9.80 ~ 15.80s): Emerald Lotus Leaf Hops & Dark Ink Whirlpool ---
    # 4 Lotus Leaf Hops (11.20s, 12.45s, 13.70s, 14.95s): organic water_step + mouth_plop
    lotus_hops = [
        (11.20, 620.0, -0.25, 21),
        (12.45, 700.0,  0.20, 22),
        (13.70, 780.0, -0.15, 23),
        (14.95, 860.0,  0.25, 24),
    ]
    for t_h, f_drip, pan_h, seed_h in lotus_hops:
        add_at(sfx, foley_water_step(f_drip), t_h, gain=0.58, pan=pan_h)
        add_at(sfx, bank_sfx('fit/pop/mouth_plop', seed=seed_h), t_h + 0.01, gain=0.34, pan=pan_h)
        sc_hits.append((t_h, 0.75))

    # 12.80s: Gentle Koi / Water Splash in Lotus Pond
    add_at(sfx, foley_splash(0.48), 12.80, gain=0.52, pan=0.18)

    # 13.80 ~ 15.60s: Dark Ink Whirlpool Swirl (`whoosh_big/deep` low-passed + water vortex)
    vortex_sig = lp(bank_sfx('whoosh_big/deep', dur=1.60, apex=0.55, seed=31), 950.0)
    add_at(sfx, vortex_sig, 13.85, gain=0.38)
    add_at(sfx, foley_splash(0.55), 14.35, gain=0.46, pan=-0.15)
    sc_hits.append((14.35, 0.70))

    # --- Beat 4 (15.80 ~ 22.00s): Taiji Charge -> 0.35s Silence -> 17.95s Strike -> Star Rescue ---
    # 15.90s: Leap onto Taiji Stone Altar
    add_at(sfx, bank_sfx('fit/hit/bamboo_tok', seed=41), 15.90, gain=0.45)
    add_at(sfx, bank_sfx('riser/swell', dur=1.62, seed=42), 15.92, gain=0.30)

    # *** 17.60 ~ 17.95s: MANDATORY 0.35s BREATH OF SILENCE (100% Zero) ***

    # *** 17.95s: COLOSSAL TAIJI HEAVENLY STRIKE (`pro_impact/deep` + `pro_sub_drop/ref` + water eruption) ***
    add_at(sfx, bank_sfx('pro_impact/deep', dur=1.10, seed=51), 17.95, gain=0.60)
    add_at(sfx, bank_sfx('pro_sub_drop/ref', dur=1.20, seed=52), 17.95, gain=0.56)
    add_at(sfx, foley_splash(0.65), 18.02, gain=0.52)
    sc_hits.append((17.95, 1.00))

    # 18.85s: Golden Lotus Bloom Unfurl (`logo_sting/soft_bloom` + delicate chime)
    add_at(sfx, bank_sfx('logo_sting/soft_bloom', seed=55), 18.85, gain=0.42)
    add_at(sfx, S.note('hand_chimes', 'D6', 1.8, vel=0.76), 18.88, gain=0.26, pan=0.20)
    sc_hits.append((18.85, 0.75))

    # 21.35s: Star ✦ Rescue & Joyful Chime
    add_at(sfx, bank_sfx('fit/bell/small_bell', seed=58), 21.35, gain=0.42, pan=-0.15)
    add_at(sfx, S.note('tubular_bells', 'A5', 2.0, vel=0.78), 21.35, gain=0.28, pan=0.15)
    add_at(sfx, P.pluck('guqin', 'D6', 1.8, vel=0.80, harmonic=True), 21.38, gain=0.40)
    sc_hits.append((21.35, 0.85))

    # --- Beat 5 & 6 (22.00 ~ 28.00s): 3 Cloud-Crag Ascent Leaps & Final Red Cinnabar Seal ---
    for idx_c, t_c in enumerate([22.20, 23.10, 24.00]):
        add_at(sfx, bank_sfx('fit/whoosh.short/bamboo_swish', seed=60 + idx_c), t_c - 0.08, gain=0.38,
               pan=(-0.20 if idx_c % 2 == 0 else 0.20))
        add_at(sfx, bank_sfx('fit/land.light/finger_wood', seed=70 + idx_c), t_c, gain=0.42)
        sc_hits.append((t_c, 0.65))

    # 25.25s: Soar into Summit Mandala Portal
    add_at(sfx, bank_sfx('whoosh_big/swell', dur=1.20, apex=0.45, seed=81), 24.95, gain=0.34)

    # 25.85s: Final Red Cinnabar Artist Seal Stamp ("水墨大成" — carved wood thump + paper press)
    add_at(sfx, foley_seal(), 25.85, gain=0.68)
    add_at(sfx, bank_sfx('fit/hit/bamboo_tok', seed=88), 25.85, gain=0.46)
    add_at(sfx, foley_brush(0.55, 300.0, 1200.0), 25.92, gain=0.36)
    sc_hits.append((25.85, 0.95))

    # Spatialize SFX in a warm, natural scroll room
    sfx_wet = S.room(lp(sfx, 4200.0), size=0.68, mix=0.24, predelay=0.016, damp=0.52)

    # Enforce 100% silence during the 17.60 ~ 17.95s pre-strike breath!
    sfx_wet *= gate_envelope(N_SAMPLES, [
        (17.60, 17.95, 0.00, 0.008),
        (27.65, 28.00, 0.00, 0.25),
    ])
    return sfx_wet, sc_hits


# ---------------------------------------------------------------------------
# 3. Ambience Stem (Gentle Mountain Breeze & Distant Stream — Whisper Quiet)
# ---------------------------------------------------------------------------

def build_ambience_stem() -> np.ndarray:
    rng = np.random.default_rng(404)
    amb = np.zeros((N_SAMPLES, 2), dtype=np.float32)
    t = np.arange(N_SAMPLES, dtype=np.float32) / SR

    # Soft mountain breeze (band-passed 220 ~ 680 Hz, modulated by slow 0.14 Hz breath LFO)
    lfo_l = 0.55 + 0.45 * np.sin(2.0 * np.pi * 0.14 * t)
    lfo_r = 0.55 + 0.45 * np.cos(2.0 * np.pi * 0.12 * t + 0.8)
    wind_l = bp(rng.standard_normal(N_SAMPLES).astype(np.float32), 220.0, 680.0) * lfo_l * 0.0065
    wind_r = bp(rng.standard_normal(N_SAMPLES).astype(np.float32), 220.0, 680.0) * lfo_r * 0.0065

    amb[:, 0] = wind_l
    amb[:, 1] = wind_r

    # Sparse distant water droplets in quiet moments
    for t_d, f_d, pan_d in [(1.55, 740.0, -0.35), (6.35, 810.0, 0.30), (10.45, 690.0, -0.25), (26.65, 760.0, 0.25)]:
        add_at(amb, foley_drip(f_d, 0.17), t_d, gain=0.22, pan=pan_d)

    amb *= gate_envelope(N_SAMPLES, [
        (17.60, 17.95, 0.00, 0.008),
        (27.50, 28.00, 0.00, 0.30),
    ])
    return amb


# ---------------------------------------------------------------------------
# 4. Full Mix, Sidechain Ducking & Broadcast Mastering (-14.0 LUFS)
# ---------------------------------------------------------------------------

def build_world_04_soundtrack(events=None, out_wav: str = None):
    out_dir = os.path.dirname(os.path.abspath(__file__))
    if out_wav is None:
        out_wav = os.path.join(out_dir, 'world_04_inkwash.wav')

    print('[World 04 Audio] Building Chinese chamber music stem (Guqin, Xiao, Dan Tranh, Pipa, Erhu)...')
    music = build_music_stem()

    print('[World 04 Audio] Building organic Ink-Wash Foley & SFX stem...')
    sfx, sc_hits = build_sfx_stem()

    print('[World 04 Audio] Building mountain breeze & water ambience stem...')
    amb = build_ambience_stem()

    # Sidechain duck music under key Foley hits
    sc_gain = master.sidechain_times(sc_hits, N_SAMPLES, depth=0.42, tau=0.16).astype(np.float32)
    raw_mix = music * sc_gain + sfx + amb

    # Guarantee pre-master silence during the 17.60 ~ 17.95s breath before the Taiji strike
    iz0, iz1 = int(17.60 * SR), int(17.945 * SR)
    raw_mix[iz0:iz1] = 0.0

    print('[World 04 Audio] Running master.finish (target = -14.0 LUFS, ceiling = 0.77)...')
    mastered, info = master.finish(
        raw_mix,
        lufs=-14.0,
        ceiling=0.77,
        mono_hz=120.0,
        comp=True,
        drive=1.08,
        air=0.14,
        hp_hz=28.0,
        end_fade=0.12,
        tail_zero=480,
    )

    # Guarantee 100% digital zero during 17.61 ~ 17.94s ("Stillness before action")
    fz0, fz1 = int(17.61 * SR), int(17.94 * SR)
    fade_n = int(0.008 * SR)
    for ch in range(2):
        mastered[fz0 - fade_n:fz0, ch] *= np.linspace(1.0, 0.0, fade_n)
        mastered[fz0:fz1, ch] = 0.0
        mastered[fz1:fz1 + fade_n, ch] *= np.linspace(0.0, 1.0, fade_n)

    sf.write(out_wav, mastered.astype(np.float32), SR, subtype='PCM_24')
    final_metrics = master.measure(mastered)
    print(f'[World 04 Audio] Saved -> {out_wav}')
    print(f'[World 04 Audio] Master Metrics: {final_metrics}')
    return final_metrics


def main():
    build_world_04_soundtrack()


if __name__ == '__main__':
    main()
