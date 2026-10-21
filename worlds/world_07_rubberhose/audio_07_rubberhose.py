#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World 07 · 1930s 复古橡皮管爵士乐园 (audio_07_rubberhose.py)
Authentic 1930s Fleischer / Silly Symphony / Cuphead Rubber-Hose Soundtrack & Slapstick Foley.
Built with real recorded acoustic instruments from `lemo-opuscar` (sampler, pluck, sfx)
and `earshot` (forge.bank, master.finish @ -14.0 LUFS, sidechain ducking, stop-downs).
"""

import os
import sys
import math
import wave
import numpy as np
from scipy import signal

# Repository root derived from __file__ (no absolute paths)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from audio_deps import require_audio_upstream
require_audio_upstream()   # 缺失时抛出带安装指引的错误，绝不静默降级

from core.audio import sampler as S, pluck as PL, sfx as X
from earshot.forge import bank
import master

SR = S.SR  # 48000
BPM = 132.0
BEAT = 60.0 / BPM          # 0.454545... s
BAR = 4.0 * BEAT           # 1.818181... s

# Sample attack lead-time compensation (seconds) so brass/reeds lock to the beat grid
LEAD = {
    "tuba": 0.024,
    "tuba_stac": 0.020,
    "trombone": 0.018,
    "trombone_stac": 0.014,
    "trumpet": 0.016,
    "trumpet_stac": 0.012,
    "trumpet_mute": 0.014,
    "clarinet": 0.014,
    "clarinet_stac": 0.010,
    "contrabass_pizz": 0.012,
    "jazz_bass": 0.010,
}


# =============================================================================
# Helper Utilities
# =============================================================================

def add_stereo(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0, pan: float = 0.0):
    """Mix mono or stereo `sig` into stereo `(N, 2)` `buf` at time `at` (seconds)."""
    if sig is None or len(sig) == 0:
        return
    if sig.ndim == 1:
        X.add(buf, sig.astype(np.float32), max(0.0, float(at)), gain=float(gain), pan=float(pan))
    else:
        i0 = max(0, int(round(float(at) * SR)))
        if i0 >= len(buf):
            return
        n = min(len(sig), len(buf) - i0)
        if n <= 0:
            return
        theta = (np.clip(float(pan), -1.0, 1.0) + 1.0) * (np.pi / 4.0)
        gL = float(gain) * np.cos(theta) * math.sqrt(2.0)
        gR = float(gain) * np.sin(theta) * math.sqrt(2.0)
        buf[i0:i0 + n, 0] += sig[:n, 0].astype(np.float32) * gL
        buf[i0:i0 + n, 1] += sig[:n, 1].astype(np.float32) * gR


def place_inst(
    buf: np.ndarray,
    inst: str,
    pitch,
    at: float,
    dur: float,
    vel: float = 0.8,
    gain: float = 1.0,
    pan: float = 0.0,
    var=None,
):
    """Render a real sampled instrument note with lead-time compensation and place into stereo buffer."""
    lead = LEAD.get(inst, 0.0)
    x = S.note(inst, pitch, dur=float(dur), vel=float(vel), var=var)
    X.add(buf, x, max(0.0, float(at) - lead), gain=float(gain), pan=float(pan))


def place_chord(
    buf: np.ndarray,
    inst: str,
    pitches: list,
    at: float,
    dur: float,
    vel: float = 0.78,
    gain: float = 1.0,
    pan: float = 0.0,
    strum: float = 0.008,
):
    """Render a real sampled chord and place into stereo buffer."""
    lead = LEAD.get(inst, 0.0)
    x = S.chord(inst, pitches, dur=float(dur), vel=float(vel), strum=float(strum))
    X.add(buf, x, max(0.0, float(at) - lead), gain=float(gain), pan=float(pan))


def plunger_wah(x: np.ndarray, f_closed: float = 360.0, f_open: float = 2450.0, f_end: float = 420.0) -> np.ndarray:
    """1930s Cab Calloway / Fleischer plunger-mute wah filter sweep on real brass sample."""
    n = len(x)
    if n < 64:
        return x
    y = np.zeros_like(x, dtype=np.float32)
    step = 256
    for i in range(0, n, step):
        u = i / max(1, n)
        if u < 0.42:
            fc = f_closed + (f_open - f_closed) * (u / 0.42)
        else:
            fc = f_open + (f_end - f_open) * ((u - 0.42) / 0.58)
        fc = float(np.clip(fc, 180.0, SR * 0.42))
        b, a = signal.butter(2, fc / (SR * 0.5), btype="low")
        j = min(n, i + step * 2)
        seg = signal.lfilter(b, a, x[i:j]).astype(np.float32)
        win = np.hanning(len(seg)).astype(np.float32)
        y[i:j] += seg * win
    peak = float(np.max(np.abs(y)))
    if peak > 1e-6:
        y = y * (float(np.max(np.abs(x))) / peak)
    return y


def gate_zero(buf: np.ndarray, t0: float, t1: float, fade: float = 0.025, floor: float = 0.0):
    """Carve a clean cartoon stop-down silence window in the music bus."""
    i0 = max(0, int(round(t0 * SR)))
    i1 = min(len(buf), int(round(t1 * SR)))
    if i1 <= i0:
        return
    nf = max(1, int(round(fade * SR)))
    g = np.full(i1 - i0, float(floor), dtype=np.float32)
    if 2 * nf < len(g):
        g[:nf] = np.linspace(1.0, float(floor), nf, dtype=np.float32)
        g[-nf:] = np.linspace(float(floor), 1.0, nf, dtype=np.float32)
    buf[i0:i1] *= g[:, None]


def apply_1930s_optical_warmth(stereo_bus: np.ndarray) -> np.ndarray:
    """
    Gentle 1930s optical soundtrack warmth on the BGM bus:
    rolls off sub-65Hz rumble and harsh >8.5kHz fizz so foreground Foley & mallets pop cleanly.
    """
    sos_hp = signal.butter(2, 65.0 / (SR * 0.5), btype="high", output="sos")
    sos_lp = signal.butter(2, 8600.0 / (SR * 0.5), btype="low", output="sos")
    y = signal.sosfilt(sos_hp, stereo_bus, axis=0)
    y = signal.sosfilt(sos_lp, y, axis=0)
    # Subtle warm ribbon-mic saturation
    y = np.tanh(y * 1.12) / np.tanh(1.12)
    return y.astype(np.float32)


def whistle_slide(f0: float, f1: float, dur: float) -> np.ndarray:
    """Authentic 1930s wooden slide-whistle with gentle breath air and smooth cosine pitch trajectory."""
    n = max(1, int(round(float(dur) * SR)))
    u = 0.5 - 0.5 * np.cos(np.pi * np.linspace(0.0, 1.0, n, dtype=np.float32))
    f = float(f0) * ((float(f1) / max(20.0, float(f0))) ** u)
    phase = 2.0 * np.pi * np.cumsum(f) / SR
    env = np.clip(np.sin(np.pi * np.linspace(0.0, 1.0, n, dtype=np.float32)), 0.0, 1.0) ** 0.75
    tone = (np.sin(phase) + 0.18 * np.sin(2.0 * phase)).astype(np.float32)
    air = X.bp(X.noise(dur) * 0.08, 1100.0, 3200.0)
    return ((tone * 0.42 + air[:n]) * env).astype(np.float32)


def export_wav_int16(samples: np.ndarray, path: str, sr: int = SR) -> dict:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    m = master.measure(clipped)
    m["path"] = path
    return m


# =============================================================================
# 1. 1930s Ragtime & Big Band Score Builder (Real Acoustic Samples)
# =============================================================================

def build_music_score(duration_s: float = 26.0) -> np.ndarray:
    """
    Builds the 26.0s 1930s Fleischer / Cuphead Ragtime & Big Band score using real samples.
    Designed with clear phrasing, call-and-response space, and dramatic stop-downs
    so it never feels cluttered or fatiguing.
    """
    n_samples = int(round(duration_s * SR))
    music = np.zeros((n_samples, 2), dtype=np.float32)

    # -------------------------------------------------------------------------
    # ACT I (0.0s – 1.2s): Sparse Cold Open — No BGM yet!
    # Gives 5–9 LU natural Loudness Range (LRA) and lets the 35mm projector
    # countdown & theater switch snap set the 1930s stage atmosphere.
    # -------------------------------------------------------------------------
    # Little solo clarinet + banjo pickup at 1.02s leading into Bar 1 at 1.20s
    place_inst(music, "clarinet_stac", "G4", 1.02, 0.09, vel=0.65, gain=0.42, pan=-0.22)
    place_inst(music, "clarinet_stac", "A4", 1.11, 0.09, vel=0.72, gain=0.46, pan=-0.22)

    # -------------------------------------------------------------------------
    # ACT II (1.20s – 3.92s): Beat 1 — Lazy Playful Ragtime Intro (1.5 bars)
    # Stride honky-tonk piano + tuba oom-pah + banjo backbeat + jaunty clarinet
    # -------------------------------------------------------------------------
    t_intro = 1.20
    intro_chords = [
        # (beat_offset, bass_note, chord_notes, banjo_notes)
        (0, "C2", ["E4", "G4", "A4", "C5"], ["C4", "E4", "G4", "C5"]),
        (1, "G1", ["E4", "G4", "B4", "D5"], ["G3", "B3", "D4", "G4"]),
        (2, "A1", ["E4", "G4", "C#5", "E5"], ["A3", "C#4", "E4", "A4"]),
        (3, "E1", ["F4", "A4", "C5", "D5"], ["D4", "F4", "A4", "D5"]),
        (4, "F1", ["F4", "Ab4", "C5", "D5"], ["F3", "Ab3", "C4", "F4"]),
        (5, "G1", ["F4", "G4", "B4", "D5"], ["G3", "B3", "D4", "G4"]),
    ]
    for b_idx, bass_p, p_chord, bj_chord in intro_chords:
        t_b = t_intro + b_idx * BEAT
        # Downbeat: Tuba staccato + Honky-tonk low octave
        place_inst(music, "tuba_stac", bass_p, t_b, BEAT * 0.65, vel=0.76, gain=0.52, pan=-0.15)
        place_inst(music, "honky_tonk", bass_p.replace("1", "2").replace("2", "3"), t_b, BEAT * 0.45, vel=0.72, gain=0.38, pan=-0.25)
        # Offbeat ("pah"): Stride piano chord + crisp Banjo up-strum + light brush tap
        t_off = t_b + BEAT * 0.52
        place_chord(music, "honky_tonk", p_chord, t_off, BEAT * 0.38, vel=0.74, gain=0.36, pan=-0.22, strum=0.008)
        bj = PL.strum("banjo", bj_chord, dur=0.22, vel=0.68, spread=0.012, up=True)
        X.add(music, bj, t_off, gain=0.26, pan=0.28)
        X.add(music, S.hit("snare2", "taps", vel=0.38), t_off, gain=0.22, pan=0.18)

    # Jaunty Clarinet + Xylophone Ragtime Melody over Beat 1 (1.20s – 3.70s)
    mel_beat1 = [
        (0.00, "C5", 0.35), (0.52, "E5", 0.35), (1.00, "G5", 0.42), (1.52, "E5", 0.35),
        (2.00, "A5", 0.42), (2.52, "G5", 0.35), (3.00, "E5", 0.35), (3.52, "D5", 0.35),
        (4.00, "C5", 0.45), (4.66, "D5", 0.28), (5.00, "E5", 0.55),
    ]
    for b_off, note_p, d_beats in mel_beat1:
        tm = t_intro + b_off * BEAT
        place_inst(music, "clarinet", note_p, tm, d_beats * BEAT, vel=0.78, gain=0.46, pan=-0.18)
        if b_off in (0.0, 2.0, 4.0):
            place_inst(music, "xylophone", note_p, tm, 0.22, vel=0.68, gain=0.28, pan=0.22)

    # -------------------------------------------------------------------------
    # ACT III (3.92s – 8.80s): Beat 2 — Call-and-Response Mickey-Mousing
    # Sparse walking pizzicato bass + light piano comping leaves wide open
    # acoustic space for Boss's 3 plunger-wah spits & Slime's piano-key jumps!
    # -------------------------------------------------------------------------
    walk_notes = [
        (3.95, "C2"), (4.55, "E2"), (5.15, "F2"), (5.75, "F#2"),
        (6.35, "G2"), (7.25, "A2"), (8.10, "G2"), (8.50, "G1"),
    ]
    for tw, bp in walk_notes:
        xb = PL.pluck("upright_bass_pizz", bp, dur=0.42, vel=0.74)
        X.add(music, xb, tw, gain=0.48, pan=-0.12)
        X.add(music, S.hit("snare2", "taps", vel=0.30), tw + 0.22, gain=0.16, pan=0.18)

    # Playful clarinet answer phrases in the gaps after Slime's dodges (4.45s, 5.65s, 8.15s)
    place_inst(music, "clarinet_stac", "G5", 4.48, 0.14, vel=0.68, gain=0.36, pan=-0.20)
    place_inst(music, "clarinet_stac", "E5", 4.64, 0.16, vel=0.65, gain=0.34, pan=-0.20)
    place_inst(music, "clarinet_stac", "A5", 5.68, 0.14, vel=0.70, gain=0.36, pan=-0.20)
    place_inst(music, "clarinet_stac", "F5", 5.84, 0.16, vel=0.65, gain=0.34, pan=-0.20)
    # Little upbeat piano & clarinet turnaround after the 7.8s Idea Bulb leading into Beat 3 (8.25s–8.80s)
    place_chord(music, "honky_tonk", ["G4", "B4", "D5", "F5"], 8.28, 0.25, vel=0.74, gain=0.36, pan=-0.22)
    place_inst(music, "clarinet", "G5", 8.30, 0.22, vel=0.75, gain=0.40, pan=-0.18)
    place_inst(music, "clarinet", "B5", 8.54, 0.22, vel=0.80, gain=0.42, pan=-0.18)

    # -------------------------------------------------------------------------
    # ACT IV (8.80s – 14.20s): Beat 3 — Slime's 3 Heavy Stomps & Technicolor Revival
    # As color washes across the stage, the ensemble warms up from sepia ragtime
    # into lush Silly Symphony orchestral swing!
    # -------------------------------------------------------------------------
    t_b3 = 8.80
    b3_bars = [
        # (bar_start, bass_root, bass_fifth, chord_pitches, brass_stab)
        (8.80,  "C2", "G1", ["E4", "G4", "A4", "C5"], ["E4", "G4", "C5"]),
        (10.62, "F2", "C2", ["F4", "A4", "C5", "D5"], ["F4", "A4", "D5"]),
        (12.44, "G2", "D2", ["F4", "A4", "B4", "D5"], ["G4", "B4", "D5"]),
    ]
    for bar_t, r1, r2, ch_notes, br_notes in b3_bars:
        for beat_i in range(4):
            tb = bar_t + beat_i * BEAT
            if tb >= 13.60:
                break
            b_note = r1 if (beat_i % 2 == 0) else r2
            place_inst(music, "tuba_stac", b_note, tb, BEAT * 0.62, vel=0.78, gain=0.50, pan=-0.15)
            xb = PL.pluck("upright_bass_pizz", b_note, dur=0.35, vel=0.75)
            X.add(music, xb, tb, gain=0.38, pan=-0.10)

            t_off = tb + BEAT * 0.52
            if t_off < 13.60:
                place_chord(music, "upright", ch_notes, t_off, BEAT * 0.38, vel=0.75, gain=0.38, pan=-0.22)
                bj = PL.strum("banjo", ch_notes, dur=0.20, vel=0.68, spread=0.012, up=True)
                X.add(music, bj, t_off, gain=0.25, pan=0.26)
                X.add(music, S.hit("snare2", "taps", vel=0.40), t_off, gain=0.22, pan=0.18)

        # Warm brass & reed syncopated figure between the stomps
        t_sync = bar_t + 1.5 * BEAT
        if t_sync < 13.55:
            place_chord(music, "trombone_stac", br_notes[:2], t_sync, 0.22, vel=0.72, gain=0.34, pan=0.22)
            place_inst(music, "clarinet", br_notes[2], t_sync, 0.30, vel=0.76, gain=0.40, pan=-0.20)

    # Stop-Down before the 3rd Stomp & Full Technicolor Explosion (13.62s – 13.84s)
    gate_zero(music, 13.62, 13.84, fade=0.02)

    # -------------------------------------------------------------------------
    # ACT V (14.20s – 18.60s): Beat 4 — Golden Vinyl Absorb, Boss Fury & Stop-Down
    # 14.20s–16.75s: Radiant swing groove celebrating the Golden Vinyl Token
    # 16.80s–18.58s: MANDATORY CARTOON STOP-DOWN (total band silence during rocket charge!)
    # -------------------------------------------------------------------------
    b4_beats = [
        (14.25, "C2", ["E4", "G4", "B4", "D5"], "G5"),
        (14.70, "A1", ["E4", "G4", "C5", "E5"], "A5"),
        (15.15, "D2", ["F#4", "A4", "C5", "E5"], "B5"),
        (15.60, "G1", ["F4", "A4", "B4", "D5"], "D6"),
        (16.05, "E2", ["G#4", "B4", "D5", "F5"], "E5"),
    ]
    for tb, b_note, ch_n, mel_n in b4_beats:
        place_inst(music, "tuba_stac", b_note, tb, 0.28, vel=0.76, gain=0.48, pan=-0.15)
        place_chord(music, "honky_tonk", ch_n, tb + 0.22, 0.20, vel=0.72, gain=0.34, pan=-0.22)
        place_inst(music, "clarinet", mel_n, tb, 0.32, vel=0.74, gain=0.38, pan=-0.18)
        place_inst(music, "vibraphone", mel_n, tb, 0.42, vel=0.68, gain=0.26, pan=0.22)

    # Hard Stop-Down silence from 16.80s to 18.58s so Slime's wind-up & slide-whistle rocket launch
    # play against pure theater air before the colossal 18.60s headbutt impact!
    gate_zero(music, 16.80, 18.58, fade=0.025)

    # -------------------------------------------------------------------------
    # ACT VI (18.60s – 23.00s): Beat 5 — Dizzy Stars & Reverse Suction Riff
    # Light comedic accompaniment under the dizzy stars & reverse horn vortex
    # -------------------------------------------------------------------------
    # 18.90s–20.15s: Tipsy oom-pah while Boss sees stars
    for i, (tb, bn, cn) in enumerate([
        (18.95, "C2", ["E4", "G4", "Bb4", "C#5"]),
        (19.42, "F#1", ["E4", "Ab4", "C5", "D5"]),
        (19.88, "G1", ["F4", "A4", "B4", "D5"]),
    ]):
        place_inst(music, "tuba_stac", bn, tb, 0.26, vel=0.70, gain=0.42, pan=-0.15)
        place_chord(music, "honky_tonk", cn, tb + 0.22, 0.18, vel=0.68, gain=0.30, pan=-0.22)

    # 20.30s–22.65s: Sneaky descending chromatic walking bass + muted trumpet during reverse suction
    suction_steps = [
        (20.35, "C3", "G4"), (20.75, "B2", "F#4"), (21.15, "Bb2", "F4"),
        (21.55, "A2", "E4"), (21.95, "Ab2", "Eb4"), (22.35, "G2", "D4"),
    ]
    for ts, b_p, tr_p in suction_steps:
        xb = PL.pluck("upright_bass_pizz", b_p, dur=0.32, vel=0.74)
        X.add(music, xb, ts, gain=0.45, pan=-0.12)
        place_inst(music, "clarinet_stac", tr_p, ts + 0.16, 0.14, vel=0.68, gain=0.34, pan=-0.20)
        X.add(music, S.hit("woodblock", "b", vel=0.45), ts + 0.16, gain=0.18, pan=0.22)

    # Stop-down breath from 22.85s to 24.18s so Slime's leap into the horn (23.0s)
    # and the big cartoon gulp (23.75s) are crystal clear!
    gate_zero(music, 22.85, 24.18, fade=0.025)

    # -------------------------------------------------------------------------
    # ACT VII (24.20s – 25.60s): Beat 6 — Classic 1930s Big Band Showstopper Finale
    # "BUM (24.20) - BUM (24.42) - BADA (24.64, 24.78) - BUMMM! (24.92)"
    # -------------------------------------------------------------------------
    cadence_hits = [
        (24.20, "C2", ["C4", "E4", "G4", "C5"], ["E4", "G4", "C5"], 0.20, 0.82),
        (24.42, "D2", ["D4", "F#4", "A4", "C5"], ["F#4", "A4", "D5"], 0.20, 0.84),
        (24.64, "Eb2", ["Eb4", "G4", "A4", "C5"], ["G4", "A4", "Eb5"], 0.13, 0.78),
        (24.78, "E2", ["E4", "G#4", "B4", "D5"], ["G#4", "B4", "E5"], 0.13, 0.82),
    ]
    for tc, bass_n, p_ch, br_ch, dur_c, vel_c in cadence_hits:
        place_inst(music, "tuba_stac", bass_n, tc, dur_c, vel=vel_c, gain=0.58, pan=-0.12)
        place_chord(music, "honky_tonk", p_ch, tc, dur_c, vel=vel_c, gain=0.44, pan=-0.22, strum=0.005)
        place_chord(music, "trumpet_stac", br_ch, tc, dur_c, vel=vel_c, gain=0.46, pan=0.22, strum=0.004)
        place_inst(music, "trombone_stac", bass_n.replace("2", "3"), tc, dur_c, vel=vel_c, gain=0.42, pan=0.18)
        X.add(music, S.hit("snare2", "on", vel=vel_c * 0.8), tc, gain=0.32, pan=0.15)

    # Final Glorious C6/9 Chord at 24.92s
    t_fin = 24.92
    place_inst(music, "tuba", "C2", t_fin, 0.62, vel=0.90, gain=0.62, pan=-0.10)
    place_chord(music, "honky_tonk", ["C4", "E4", "G4", "A4", "D5", "G5"], t_fin, 0.65, vel=0.88, gain=0.46, pan=-0.20, strum=0.008)
    place_chord(music, "trumpet", ["E4", "G4", "A4", "D5"], t_fin, 0.58, vel=0.86, gain=0.48, pan=0.22, strum=0.006)
    place_inst(music, "trombone", "C3", t_fin, 0.58, vel=0.85, gain=0.45, pan=0.16)
    place_inst(music, "clarinet", "G5", t_fin, 0.58, vel=0.85, gain=0.42, pan=-0.18)
    place_chord(music, "vibraphone", ["E5", "G5", "A5", "D6"], t_fin, 0.68, vel=0.80, gain=0.36, pan=0.12, strum=0.010)
    X.add(music, S.hit("clash", "short", vel=0.68), t_fin, gain=0.34, pan=0.20)
    X.add(music, S.hit("bass_drum", vel=0.82), t_fin, gain=0.48, pan=0.0)

    # Apply 1930s optical warmth + compact stage room reverb
    music = apply_1930s_optical_warmth(music)
    music = S.room(music, size=0.22, mix=0.15, damp=0.62)[:n_samples]
    return music


# =============================================================================
# 2. Frame-Accurate 1930s Cartoon Slapstick & Musical Foley Bus
# =============================================================================

def build_sfx_and_foley(audio_events: list, duration_s: float = 26.0) -> tuple[np.ndarray, list[float]]:
    """
    Renders frame-accurate 1930s Fleischer / Silly Symphony Foley using real orchestral
    percussion & instruments (`S.note`, `S.hit`, `PL`) and `earshot.forge.bank`.
    Returns `(sfx_stereo, duck_hit_times)`.
    """
    n_samples = int(round(duration_s * SR))
    sfx = np.zeros((n_samples, 2), dtype=np.float32)
    duck_times = []

    # 1. Cold Open (0.0s – 1.2s): 35mm Projector Countdown & Stage Switch
    for t_cnt, pitch_wb, var_wb in [(0.04, "a", 0.65), (0.42, "b", 0.72), (0.80, "c", 0.80)]:
        X.add(sfx, S.hit("woodblock", var_wb, vel=var_wb), t_cnt, gain=0.48, pan=0.0)
        y_tick, _ = bank.render("fit/tick/domino", seed=int(t_cnt * 100), peak_db=-6.0)
        add_stereo(sfx, y_tick, t_cnt, gain=0.35, pan=-0.10)

    # 1.18s: Theater Spotlight & Stage Switch Clack
    y_sw, _ = bank.render("fit/snap/switch_flip", seed=701, peak_db=-3.0)
    add_stereo(sfx, y_sw, 1.18, gain=0.55, pan=0.0)
    duck_times.append(1.18)

    # Default event schedule if none passed
    if not audio_events:
        audio_events = [
            (1.20, "ragtime_intro_start"),
            (3.75, "boss_inhale_1"), (4.10, "piano_step_1"), (4.20, "boss_spit_note_1"),
            (4.95, "boss_inhale_2"), (5.30, "piano_step_2"), (5.40, "boss_spit_note_2"),
            (6.15, "boss_inhale_3"), (6.50, "screech_brake"), (6.60, "boss_spit_note_3"),
            (6.80, "question_mark_pop"), (7.80, "idea_bulb_ding"),
            (10.15, "stomp_1"), (10.20, "technicolor_bloom_1"),
            (11.95, "stomp_2"), (12.00, "technicolor_bloom_2"),
            (13.85, "stomp_3"), (13.90, "boss_horn_blast"),
            (15.20, "vinyl_token_absorb"), (16.20, "boss_furious_roar"),
            (16.85, "charge_windup"), (17.80, "rocket_launch_whoosh"),
            (18.60, "headbutt_impact_clang"), (18.85, "boss_stars_twinkle"),
            (19.80, "slime_rebound_land"), (20.20, "reverse_vortex_suction"),
            (21.00, "star_sucked_in"), (21.30, "slime_dragged_slide"),
            (23.00, "slime_leap_into_horn"), (23.75, "slime_swallowed_gulp"),
            (25.10, "iris_out_thump"),
        ]

    for ev in audio_events:
        if isinstance(ev, dict):
            t = float(ev.get("time", ev.get("t", 0.0)))
            name = str(ev.get("name", ""))
        else:
            t = float(ev[0])
            name = str(ev[1])
        if t < 0.0 or t >= duration_s - 0.05:
            continue

        # ---------------------------------------------------------------------
        # BEAT 2: Boss Inhale/Spit Cycles & Slime Piano-Key Dodges
        # ---------------------------------------------------------------------
        if name.startswith("boss_inhale"):
            # Brass bellows breath + low trombone slide-in
            y_in, _ = bank.render("whoosh_fast/reverse", seed=710, dur=0.36, peak_db=-6.0)
            add_stereo(sfx, y_in, t, gain=0.38, pan=0.35)
            tb_in = S.note("trombone", "G2", dur=0.34, vel=0.68, attack=0.12)
            X.add(sfx, plunger_wah(tb_in, 280.0, 950.0, 1400.0), t, gain=0.42, pan=0.35)

        elif name.startswith("boss_spit_note"):
            idx = int(name[-1])
            pitches = {1: ("Eb3", "Bb3"), 2: ("D3", "Ab3"), 3: ("C#3", "G3")}[idx]
            # Authentic 1930s plunger-mute trombone + muted trumpet "BWAA-WAH!" spit
            tb = S.note("trombone", pitches[0], dur=0.38, vel=0.88)
            tr = S.note("trumpet_mute", pitches[1], dur=0.34, vel=0.85)
            wah_mix = plunger_wah(tb * 0.65 + np.pad(tr, (0, max(0, len(tb) - len(tr))))[:len(tb)] * 0.55)
            X.add(sfx, wah_mix, t, gain=0.68, pan=0.32)
            place_inst(sfx, "tuba_stac", pitches[0].replace("3", "2"), t, 0.22, vel=0.82, gain=0.52, pan=0.32)
            y_pop, _ = bank.render("fit/pop/mouth_plop", seed=720 + idx, peak_db=-4.0)
            add_stereo(sfx, y_pop, t, gain=0.45, pan=0.32)
            duck_times.append(t)

        elif name in ("piano_step_1", "piano_step_2"):
            is_first = name.endswith("1")
            chord_p = ["C5", "E5", "G5", "C6"] if is_first else ["F5", "A5", "C6", "F6"]
            pan_v = -0.32 if is_first else -0.18
            # Crisp floor-piano key strike + bright xylophone & glockenspiel bounce
            place_chord(sfx, "honky_tonk", chord_p[:3], t, 0.34, vel=0.85, gain=0.55, pan=pan_v, strum=0.006)
            place_inst(sfx, "xylophone", chord_p[2], t, 0.26, vel=0.88, gain=0.58, pan=pan_v)
            place_inst(sfx, "glockenspiel", chord_p[3], t + 0.04, 0.32, vel=0.78, gain=0.42, pan=pan_v)
            # Subtle cartoon hop whistle
            w_hop = whistle_slide(380.0 if is_first else 460.0, 820.0 if is_first else 980.0, 0.14)
            X.add(sfx, w_hop, t, gain=0.22, pan=pan_v)
            duck_times.append(t)

        elif name == "screech_brake":
            # Cartoon heel-skid: fast clarinet downward grace + dry woodblock + paper/rubber swipe
            y_skid, _ = bank.render("swipe/Trigger" if "swipe/Trigger" in bank.ids() else "swipe/flick", seed=730, peak_db=-4.0)
            add_stereo(sfx, y_skid, t, gain=0.48, pan=-0.10)
            w_skid = whistle_slide(1250.0, 420.0, 0.18)
            X.add(sfx, w_skid, t, gain=0.26, pan=-0.10)
            X.add(sfx, S.hit("woodblock", "a", vel=0.78), t + 0.12, gain=0.45, pan=-0.10)
            duck_times.append(t)

        elif name == "question_mark_pop":
            # "?" Pop at 6.80s: dry woodblock 'tok' + quizzical upward clarinet & banjo pluck ("Huh?")
            X.add(sfx, S.hit("woodblock", "b", vel=0.82), t, gain=0.52, pan=-0.10)
            place_inst(sfx, "clarinet_stac", "C5", t + 0.02, 0.10, vel=0.78, gain=0.48, pan=-0.10)
            place_inst(sfx, "clarinet_stac", "F#5", t + 0.11, 0.16, vel=0.84, gain=0.52, pan=-0.10)
            bj_q = PL.pluck("banjo", "C6", dur=0.22, vel=0.78)
            X.add(sfx, bj_q, t + 0.11, gain=0.38, pan=-0.05)
            y_plop, _ = bank.render("fit/pop/lip_pop", seed=740, peak_db=-4.0)
            add_stereo(sfx, y_plop, t, gain=0.48, pan=-0.10)
            duck_times.append(t)

        elif name == "idea_bulb_ding":
            # "!" Idea Bulb at 7.80s: radiant glockenspiel + vibraphone + small_bell ping!
            y_bell, _ = bank.render("fit/bell/small_bell", seed=750, peak_db=-3.0)
            add_stereo(sfx, y_bell, t, gain=0.55, pan=-0.08)
            place_inst(sfx, "glockenspiel", "C6", t, 0.55, vel=0.90, gain=0.58, pan=-0.08)
            place_inst(sfx, "glockenspiel", "G6", t + 0.06, 0.65, vel=0.92, gain=0.62, pan=-0.05)
            place_chord(sfx, "vibraphone", ["C5", "E5", "G5", "C6"], t + 0.03, 0.70, vel=0.82, gain=0.42, pan=-0.08)
            duck_times.append(t)

        # ---------------------------------------------------------------------
        # BEAT 3: Slime's 3 Heavy Stomps & Technicolor Revival (10.15s, 11.95s, 13.85s)
        # ---------------------------------------------------------------------
        elif name in ("stomp_1", "stomp_2", "stomp_3"):
            idx = int(name[-1])
            pan_s = {-1: -0.25, 1: -0.22, 2: -0.05, 3: 0.12}[idx]
            timp_pitch = {1: "C2", 2: "F2", 3: "G2"}[idx]
            piano_ch = {
                1: ["C3", "G3", "C4", "E4", "G4"],
                2: ["F3", "C4", "F4", "A4", "C5"],
                3: ["G3", "D4", "G4", "B4", "D5", "G5"],
            }[idx]
            # Orchestral Timpani + Bass Drum + Piano Low Chord
            place_inst(sfx, "timpani", timp_pitch, t, 0.58, vel=0.88 + 0.04 * idx, gain=0.65, pan=pan_s)
            X.add(sfx, S.hit("bass_drum", vel=0.80 + 0.05 * idx), t, gain=0.52, pan=pan_s)
            place_chord(sfx, "piano", piano_ch, t, 0.50, vel=0.85, gain=0.48, pan=pan_s, strum=0.006)
            if idx == 3:
                # 3rd stomp lands right out of the 13.62-13.84s stop-down!
                X.add(sfx, S.hit("clash", "short", vel=0.72), t, gain=0.40, pan=pan_s)
                arp3 = ["G4", "B4", "D5", "G5", "B5", "D6", "G6"]
                for i_a, p_a in enumerate(arp3):
                    place_inst(sfx, "glockenspiel", p_a, t + 0.04 + i_a * 0.045, 0.45, vel=0.82, gain=0.44, pan=pan_s + 0.03 * i_a)
                    place_inst(sfx, "harp", p_a, t + 0.04 + i_a * 0.045, 0.55, vel=0.80, gain=0.42, pan=pan_s - 0.02 * i_a)
            duck_times.append(t)

        elif name in ("technicolor_bloom_1", "technicolor_bloom_2"):
            is_b1 = name.endswith("1")
            arp_notes = ["C5", "E5", "G5", "A5", "C6", "E6"] if is_b1 else ["F5", "A5", "C6", "D6", "F6", "A6"]
            pan_b = -0.20 if is_b1 else -0.04
            for i_a, p_a in enumerate(arp_notes):
                ta = t + i_a * 0.055
                place_inst(sfx, "vibraphone", p_a, ta, 0.48, vel=0.76, gain=0.38, pan=pan_b + 0.04 * i_a)
                place_inst(sfx, "glockenspiel" if not is_b1 else "xylophone", p_a, ta, 0.36, vel=0.78, gain=0.42, pan=pan_b - 0.03 * i_a)
                hp = PL.pluck("harp", p_a, dur=0.52, vel=0.75)
                X.add(sfx, hp, ta, gain=0.34, pan=pan_b)

        elif name == "boss_horn_blast":
            # 13.90s: Boss shocked brass horn blast as color hits him
            place_chord(sfx, "trumpet", ["G4", "B4", "D5", "F5"], t, 0.45, vel=0.86, gain=0.50, pan=0.30, strum=0.008)
            tb_b = S.note("trombone", "G3", dur=0.45, vel=0.88)
            X.add(sfx, plunger_wah(tb_b, 420.0, 2600.0, 680.0), t, gain=0.54, pan=0.30)

        # ---------------------------------------------------------------------
        # BEAT 4: Golden Vinyl Token Absorb (15.20s), Boss Fury (16.20s) & Rocket Charge
        # ---------------------------------------------------------------------
        elif name == "vinyl_token_absorb":
            # Shimmering golden harp + glockenspiel + vibraphone chord bloom
            v_notes = ["C5", "E5", "G5", "B5", "D6", "G6"]
            for i_v, pv in enumerate(v_notes):
                tv = t + i_v * 0.045
                place_inst(sfx, "glockenspiel", pv, tv, 0.65, vel=0.84, gain=0.46, pan=-0.15 + i_v * 0.06)
                place_inst(sfx, "vibraphone", pv, tv, 0.75, vel=0.80, gain=0.38, pan=0.15 - i_v * 0.05)
                hp = PL.pluck("harp", pv, dur=0.70, vel=0.82)
                X.add(sfx, hp, tv, gain=0.36, pan=0.0)
            y_sp, _ = bank.render("logo_sting/spark", seed=760, peak_db=-4.0)
            add_stereo(sfx, y_sp, t, gain=0.40, pan=0.0)
            duck_times.append(t)

        elif name == "boss_furious_roar":
            # 16.20s: Boss furious plunger-trombone growl ("GRR-WAH-WAH!")
            for i_g, (dt_g, p_tb, p_tr) in enumerate([
                (0.00, "F#2", "C3"),
                (0.20, "G2", "C#3"),
                (0.40, "Ab2", "D3"),
            ]):
                tb_g = S.note("trombone", p_tb, dur=0.22, vel=0.88)
                tr_g = S.note("trumpet_mute", p_tr, dur=0.20, vel=0.84)
                X.add(sfx, plunger_wah(tb_g, 300.0, 2200.0, 380.0), t + dt_g, gain=0.58, pan=0.32)
                X.add(sfx, plunger_wah(tr_g, 450.0, 2500.0, 520.0), t + dt_g, gain=0.44, pan=0.32)
            duck_times.append(t)

        elif name == "charge_windup":
            # 16.85s–17.75s: Inside the Grand Stop-Down!
            # Crisp mechanical wind-up clicks (woodblock + snare stick + domino ticks) & rising timpani roll
            n_clicks = 11
            for i_c in range(n_clicks):
                u = i_c / max(1, n_clicks - 1)
                tc = t + u * 0.82
                wb_var = ["a", "b", "c"][i_c % 3]
                X.add(sfx, S.hit("woodblock", wb_var, vel=0.55 + 0.35 * u), tc, gain=0.40, pan=-0.28)
                # Rising pizzicato string tension
                pizz_p = ["C3", "C#3", "D3", "Eb3", "E3", "F3", "F#3", "G3", "Ab3", "A3", "B3"][i_c]
                xp = PL.pluck("banjo", pizz_p, dur=0.12, vel=0.60 + 0.30 * u)
                X.add(sfx, xp, tc, gain=0.32, pan=-0.28)
            # Crisp snare roll crescendo into launch
            X.add(sfx, S.hit("snare2", "roll", vel=0.78, dur=0.75), t + 0.15, gain=0.38, pan=-0.20)
            duck_times.append(t)

        elif name == "rocket_launch_whoosh":
            # 17.80s: Iconic 1930s Slide-Whistle Rocket Launch + Clarinet Glissando!
            w_up = whistle_slide(420.0, 1960.0, 0.74)
            X.add(sfx, w_up, t, gain=0.52, pan=-0.10)
            y_wh, _ = bank.render("whoosh_fast/whistle", seed=770, dur=0.68, peak_db=-3.0)
            add_stereo(sfx, y_wh, t + 0.04, gain=0.48, pan=0.0)
            # Fast ascending xylophone run leading straight to the 18.60s impact
            run_p = ["C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6"]
            for i_r, pr in enumerate(run_p):
                place_inst(sfx, "xylophone", pr, t + i_r * 0.085, 0.14, vel=0.72 + 0.03 * i_r, gain=0.42, pan=-0.22 + i_r * 0.06)
            duck_times.append(t)

        # ---------------------------------------------------------------------
        # BEAT 5: Colossal Headbutt Impact (18.60s), Dizzy Stars (18.85s) & Vortex (20.20s)
        # ---------------------------------------------------------------------
        elif name == "headbutt_impact_clang":
            # 18.60s: THE CLIMAX HIT! Maximum contrast right out of the 1.8s stop-down silence!
            place_inst(sfx, "timpani", "C2", t, 0.90, vel=1.0, gain=0.78, pan=0.18)
            X.add(sfx, S.hit("bass_drum", vel=0.98), t, gain=0.68, pan=0.15)
            X.add(sfx, S.hit("gong2", "big", vel=0.82, dur=1.35), t, gain=0.48, pan=0.25)
            X.add(sfx, S.hit("clash", "crash", vel=0.80, dur=0.95), t, gain=0.44, pan=0.20)
            # Big Brass & Piano "KERR-SPLANG!" impact chord
            place_chord(sfx, "honky_tonk", ["C3", "G3", "Bb3", "E4", "F#4", "C5"], t, 0.55, vel=0.95, gain=0.56, pan=0.15, strum=0.004)
            place_chord(sfx, "trumpet_stac", ["E4", "Bb4", "D#5", "G5"], t, 0.35, vel=0.92, gain=0.54, pan=0.25, strum=0.004)
            place_inst(sfx, "trombone", "C2", t, 0.48, vel=0.92, gain=0.56, pan=0.22)
            duck_times.append(t)

        elif name == "boss_stars_twinkle":
            # 18.85s: Comedic Dizzy Orbiting Stars ("Cuckoo / Tweety" xylophone + glockenspiel + tipsy clarinet loop)
            dizzy_notes = [
                ("C6", "E5"), ("Eb6", "G5"), ("F#6", "A5"), ("A6", "C6"),
                ("G6", "B5"), ("Eb6", "G5"), ("C6", "E5"), ("A5", "C5"),
                ("C6", "E5"), ("Eb6", "G5"), ("G6", "B5"), ("C7", "E6"),
            ]
            for i_d, (g_p, c_p) in enumerate(dizzy_notes):
                td = t + i_d * 0.095
                pan_d = 0.28 + 0.16 * math.sin(i_d * 1.1)
                place_inst(sfx, "glockenspiel", g_p, td, 0.24, vel=0.78, gain=0.46, pan=pan_d)
                place_inst(sfx, "xylophone", c_p, td, 0.18, vel=0.74, gain=0.42, pan=pan_d)
                if i_d % 2 == 0:
                    place_inst(sfx, "clarinet_stac", c_p, td, 0.15, vel=0.70, gain=0.35, pan=pan_d)
            duck_times.append(t)

        elif name == "slime_rebound_land":
            # 19.80s: Slime lands back on stage with a bouncy pizzicato & mouth plop
            y_plop, _ = bank.render("fit/pop/mouth_plop", seed=780, peak_db=-3.0)
            add_stereo(sfx, y_plop, t, gain=0.55, pan=-0.18)
            xb = PL.pluck("upright_bass_pizz", "G2", dur=0.35, vel=0.85)
            X.add(sfx, xb, t, gain=0.52, pan=-0.18)
            X.add(sfx, S.hit("woodblock", "b", vel=0.75), t, gain=0.42, pan=-0.18)
            duck_times.append(t)

        elif name == "reverse_vortex_suction":
            # 20.20s: Boss's horn goes into reverse suction — warm reverse air swell + downward trombone slide
            y_rev, _ = bank.render("whoosh_big/reverse", seed=790, dur=1.65, peak_db=-5.0)
            add_stereo(sfx, y_rev, t, gain=0.42, pan=0.28)
            w_down = whistle_slide(1180.0, 340.0, 1.15)
            X.add(sfx, w_down, t + 0.15, gain=0.25, pan=0.28)

        elif name == "star_sucked_in":
            # 21.00s: Orbiting star gets gulped into the horn with a bright chime & lip pop
            place_inst(sfx, "glockenspiel", "G6", t, 0.35, vel=0.86, gain=0.52, pan=0.32)
            place_inst(sfx, "xylophone", "C6", t + 0.08, 0.25, vel=0.82, gain=0.48, pan=0.32)
            y_pop, _ = bank.render("fit/pop/lip_pop", seed=800, peak_db=-3.0)
            add_stereo(sfx, y_pop, t + 0.12, gain=0.52, pan=0.32)
            duck_times.append(t)

        elif name == "slime_dragged_slide":
            # 21.30s–22.50s: Slime skids toward the horn with rapid tiptoe xylophone taps
            skid_notes = ["G5", "F#5", "F5", "E5", "Eb5", "D5", "C#5", "C5"]
            for i_s, ps in enumerate(skid_notes):
                ts = t + i_s * 0.12
                place_inst(sfx, "xylophone", ps, ts, 0.12, vel=0.72, gain=0.38, pan=-0.15 + i_s * 0.05)
                X.add(sfx, S.hit("woodblock", ["a", "b", "c"][i_s % 3], vel=0.60), ts, gain=0.28, pan=-0.15 + i_s * 0.05)

        # ---------------------------------------------------------------------
        # BEAT 6: Slime Dives Into Horn (23.00s), Gulp (23.75s) & Iris-Out (25.10s)
        # ---------------------------------------------------------------------
        elif name == "slime_leap_into_horn":
            # 23.00s: Parabolic slide-whistle leap up and down into the giant horn!
            w_arc_up = whistle_slide(480.0, 1520.0, 0.32)
            w_arc_dn = whistle_slide(1520.0, 320.0, 0.36)
            X.add(sfx, w_arc_up, t, gain=0.48, pan=0.10)
            X.add(sfx, w_arc_dn, t + 0.32, gain=0.48, pan=0.28)
            place_inst(sfx, "clarinet", "C6", t + 0.28, 0.18, vel=0.78, gain=0.40, pan=0.20)
            duck_times.append(t)

        elif name == "slime_swallowed_gulp":
            # 23.75s: Big comedic horn "GULP!" (mouth_plop + deep tuba & timpani thump)
            y_gulp, _ = bank.render("fit/pop/mouth_plop", seed=810, peak_db=-2.0)
            add_stereo(sfx, y_gulp, t, gain=0.65, pan=0.32)
            place_inst(sfx, "tuba_stac", "C2", t + 0.03, 0.28, vel=0.88, gain=0.58, pan=0.32)
            place_inst(sfx, "timpani", "G2", t + 0.03, 0.35, vel=0.84, gain=0.52, pan=0.32)
            X.add(sfx, S.hit("woodblock", "c", vel=0.85), t + 0.05, gain=0.46, pan=0.32)
            duck_times.append(t)

        elif name == "iris_out_thump":
            # Iris-out whistle at 25.25s + soft final curtain thump at 25.55s
            t_wh = min(t + 0.15, duration_s - 0.72)
            t_th = min(t + 0.45, duration_s - 0.42)
            w_iris = whistle_slide(960.0, 260.0, 0.28)
            X.add(sfx, w_iris, t_wh, gain=0.42, pan=0.0)
            place_inst(sfx, "timpani", "C2", t_th, 0.32, vel=0.82, gain=0.54, pan=0.0)
            y_end, _ = bank.render("fit/pop/mouth_plop", seed=820, peak_db=-3.0)
            add_stereo(sfx, y_end, t_th, gain=0.52, pan=0.0)
            duck_times.append(t_wh)

    # Put Foley through a tight, dry-forward theater stage reflection
    sfx = S.room(sfx, size=0.16, mix=0.10, damp=0.68)[:n_samples]
    return sfx, sorted(set(duck_times))


# =============================================================================
# 3. Main Render & Master Entrypoint (-14.0 LUFS, LRA >= 5.0 LU)
# =============================================================================

def render_audio(audio_events=None, out_wav_path=None, duration_s: float = 26.0) -> dict:
    """
    Renders and masters the 26.0s World 07 1930s Rubber-Hose Jazz & Slapstick Foley soundtrack.
    Uses `master.sidechain_times` to duck BGM under Foley gags and `master.finish`
    for broadcast-grade -14.0 LUFS loudness with natural dynamic breathing room.
    """
    if out_wav_path is None:
        out_wav_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_07_rubberhose.wav")

    n_samples = int(round(duration_s * SR))
    music = build_music_score(duration_s=duration_s)
    sfx, duck_times = build_sfx_and_foley(audio_events, duration_s=duration_s)

    # Sidechain duck the music bus around all foreground Foley/gag hits
    duck_env = master.sidechain_times([(float(t_d), 1.0) for t_d in duck_times], n_samples, depth=0.46, tau=0.14).astype(np.float32)
    music_ducked = music * duck_env

    # Ultra-subtle 1930s 35mm optical film crackle bed (strictly < -58 dBFS so it never sounds noisy)
    rng = np.random.default_rng(193407)
    bed = np.zeros((n_samples, 2), dtype=np.float32)
    for _ in range(int(duration_s * 4)):
        t_pop = float(rng.uniform(0.05, duration_s - 0.35))
        X.add(bed, X.click(pitch=float(rng.uniform(0.6, 1.4)), v=0.015), t_pop, gain=0.08, pan=float(rng.uniform(-0.3, 0.3)))

    mix_stereo = music_ducked * 0.92 + sfx * 1.08 + bed

    # Macro-dynamic contour: keep Cold Open (0~1.2s), Beat 2 call-and-response (3.9~8.8s),
    # and the pre-headbutt stop-down (16.80~18.58s) gentler so the 3 Technicolor stomps,
    # 18.60s Climax Headbutt, and 24.2s Big Band Showstopper Finale have 6+ LU LRA!
    macro_env = np.ones(n_samples, dtype=np.float32)
    for t0, t1, g_val in [(0.0, 1.18, 0.42), (3.95, 8.75, 0.56), (16.82, 18.55, 0.30), (20.20, 23.90, 0.58)]:
        i0, i1 = int(t0 * SR), int(t1 * SR)
        macro_env[i0:i1] = g_val
    macro_env = signal.sosfilt(signal.butter(1, 3.5, btype="low", fs=SR, output="sos"), macro_env).astype(np.float32)
    mix_stereo *= macro_env[:, None]

    # Clean fade-out over the final 120ms so the clip ends in pure silence at 26.0s
    fade_n = int(0.12 * SR)
    if fade_n < n_samples:
        fade_curve = np.linspace(1.0, 0.0, fade_n, dtype=np.float32)[:, None]
        mix_stereo[-fade_n:] *= fade_curve

    # Master to -14.0 LUFS, true-peak ceiling 0.77 (-2.27 dBTP)
    mastered, _ = master.finish(mix_stereo, lufs=-14.0, ceiling=0.77, comp=False, drive=1.06, air=0.10)

    info = export_wav_int16(mastered, out_wav_path, sr=SR)
    return info


if __name__ == "__main__":
    from sim_07_rubberhose import run_simulation
    _, sim_events = run_simulation()
    out_wav = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_07_rubberhose.wav")
    info = render_audio(sim_events, out_wav, duration_s=26.0)
    print(f"[World 07 Audio] Exported -> {info}")
