# -*- coding: utf-8 -*-
"""
World 02 · 16-Bit 像素横版大闯关 (audio_02_pixel.py)
Re-scored & mastered with lemo-opuscar (SNES SPC700-style sampled orchestral/harp/marimba/
xylophone/brass/woodwind/pizzicato + anti-aliased PolyBLEP pulse/NES 4-bit triangle + 3-tap
SNES echo) and earshot (forge/bank + master).

Design Principles (Addressing "好吵的音效"):
  1. Warm 16-Bit SNES Hybrid Palette (16-bit era console aesthetic):
     - Eliminates harsh square waves, high-shelf boosts, and continuous 16th-note wall-of-sound.
     - Blends band-limited PolyBLEP pulse/triangle waves (low-passed <= 2.8 kHz with SNES 3-tap
       stereo echo) with real sampled instruments (`sampler.py`: harp, marimba, xylophone,
       glockenspiel, flute, clarinet, trumpet_stac, horn, violins_pizz, contrabass_pizz, timpani)
       and physical waveguide plucks (`pluck.py`: kalimba, music_box, harp).
  2. Narrative Breathing Room & Stop-Downs (LRA >= 5.5 LU):
     - 0.00 ~ 1.55s: Sparse intro — shimmering harp/kalimba pipe assembly (0.05s) and classic
       warm warp-pipe pop (0.67s) in open air before the Overworld groove begins at 1.60s.
     - 9.65 ~ 12.50s: MUSICAL STOP-DOWN during the Cliff & Hidden Block Puzzle! Music drops to
       a whisper-quiet bass heartbeat so the failed jump (9.43s), [?] question_bubble (10.07s),
       and [!] idea_exclamation (11.20s) ring out in crystal-clear silence.
     - 15.65 ~ 16.05s: Pre-climax breath of silence right before the Gold [?] Block head-smash
       at 16.07s!
     - 21.30 ~ 22.80s: Clean pause in accompaniment as the Slime catches the flagpole top (21.70s)
       and slides down (21.77s), letting the flagpole glissando and 3 fireworks breathe before
       the Stage Clear orchestral brass/bell fanfare.
  3. Sidechain Ducking & Broadcast Mastering:
     - Music bus ducks (depth=0.45, tau=0.14s) on key story SFX hits via `master.sidechain_times`.
     - Mastered via `master.finish(mix, lufs=-14.0, ceiling=0.77)` -> -14.0 LUFS, <= -2.27 dBTP.
"""

import os
import sys
import math
import numpy as np
import soundfile as sf
from scipy import signal
from numba import njit

# Repo root derived from this file (worlds/world_02_pixel/audio_02_pixel.py)
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(CUR_DIR))
for _p in (CUR_DIR, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from audio_deps import require_audio_upstream
require_audio_upstream()   # 缺失时抛出带安装指引的错误，绝不静默降级

from core.audio import sampler as S, pluck as P, sfx as lemo_sfx
from earshot.forge import bank
import master as earshot_master

SR = 48000
TOTAL_DURATION = 28.0
TOTAL_SAMPLES = int(round(TOTAL_DURATION * SR))

# -----------------------------------------------------------------------------
# 1. Pitch Helpers & Band-Limited 16-Bit SNES Synth Primitives
# -----------------------------------------------------------------------------
NOTE_FREQ = {}
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
for _oct in range(0, 8):
    for _idx, _nm in enumerate(_NOTE_NAMES):
        _midi = (_oct + 1) * 12 + _idx
        _f = 440.0 * (2.0 ** ((_midi - 69) / 12.0))
        NOTE_FREQ[f"{_nm}{_oct}"] = _f
        if "#" in _nm:
            _flat = _NOTE_NAMES[(_idx + 1) % 12] + "b"
            NOTE_FREQ[f"{_flat}{_oct}"] = _f


def n2f(note) -> float:
    if isinstance(note, (int, float)):
        return float(note)
    return NOTE_FREQ.get(str(note), 440.0)


@njit
def _blep(t, dt):
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


@njit
def polyblep_pulse(freq_arr, duty=0.5):
    """Band-limited PolyBLEP pulse oscillator (zero aliasing harshness)."""
    n = len(freq_arr)
    y = np.zeros(n)
    ph = 0.0
    for i in range(n):
        dt = freq_arr[i] / SR
        if dt >= 0.49:
            dt = 0.49
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
        v = 1.0 if ph < duty else -1.0
        v += _blep(ph, dt)
        v -= _blep((ph - duty + 1.0) % 1.0, dt)
        y[i] = v - (2.0 * duty - 1.0)
    return y


TRI32 = np.concatenate([np.arange(15, -1, -1), np.arange(0, 16)]) / 7.5 - 1.0


def snes_pulse_note(note: str, dur_s: float, duty: float = 0.25, cutoff: float = 2500.0, vib: float = 0.008) -> np.ndarray:
    """Warm, low-passed 16-bit pulse lead (inspired by lemo-opuscar pixel-rpg)."""
    n = max(1, int(round(dur_s * SR)))
    f0 = n2f(note)
    t = np.arange(n, dtype=np.float64) / SR
    if vib > 0:
        v_env = np.clip((t - 0.08) / 0.15, 0.0, 1.0)
        f_arr = f0 * (1.0 + vib * np.sin(2.0 * math.pi * 5.5 * t) * v_env)
    else:
        f_arr = np.full(n, f0, dtype=np.float64)
    raw = 0.65 * polyblep_pulse(f_arr, duty=duty) + 0.35 * np.sin(2.0 * math.pi * np.cumsum(f_arr) / SR)
    fc = min(cutoff, max(1200.0, f0 * 3.8), 2800.0)
    sos = signal.butter(2, fc, btype="low", fs=SR, output="sos")
    filt = signal.sosfilt(sos, raw)
    # Smooth ADSR envelope
    att = min(int(0.008 * SR), n // 3)
    rel = min(int(0.045 * SR), n // 3)
    env = np.exp(-t / max(0.38, dur_s * 1.2))
    if att > 0:
        env[:att] *= np.linspace(0.0, 1.0, att)
    if rel > 0:
        env[-rel:] *= np.linspace(1.0, 0.0, rel)
    return (filt * env).astype(np.float32)


def nes_tri_bass(note: str, dur_s: float) -> np.ndarray:
    """Warm 32-step 4-bit triangle + sub-sine bass wave (low-passed at 950 Hz)."""
    n = max(1, int(round(dur_s * SR)))
    f0 = n2f(note)
    t = np.arange(n, dtype=np.float64) / SR
    f_inst = f0 * (1.0 + 0.12 * np.exp(-t / 0.012))
    ph = (np.cumsum(f_inst) / SR) % 1.0
    tri = TRI32[(ph * 32).astype(int) % 32]
    sub = np.sin(2.0 * math.pi * ph)
    raw = 0.55 * tri + 0.45 * sub
    sos = signal.butter(2, 950.0, btype="low", fs=SR, output="sos")
    filt = signal.sosfilt(sos, raw)
    att = min(int(0.004 * SR), n // 4)
    rel = min(int(0.030 * SR), n // 3)
    env = np.exp(-t / max(0.28, dur_s * 0.9))
    if att > 0:
        env[:att] *= np.linspace(0.0, 1.0, att)
    if rel > 0:
        env[-rel:] *= np.linspace(1.0, 0.0, rel)
    return (filt * env).astype(np.float32)


def lp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    if len(x) < 12:
        return x
    sos = signal.butter(order, min(fc, SR * 0.47), btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def hp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    if len(x) < 12:
        return x
    sos = signal.butter(order, max(fc, 20.0), btype="high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def pan_mono(x: np.ndarray, pan: float = 0.0) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        return x
    theta = (float(np.clip(pan, -1.0, 1.0)) + 1.0) * (math.pi / 4.0)
    return np.column_stack([x * math.cos(theta), x * math.sin(theta)]).astype(np.float32)


def add_at(buf: np.ndarray, sig: np.ndarray, t_sec: float, gain: float = 1.0, pan: float = 0.0):
    if sig is None or len(sig) == 0:
        return
    idx = int(round(float(t_sec) * SR))
    if idx >= len(buf):
        return
    if sig.ndim == 1:
        st = pan_mono(sig * float(gain), pan)
    else:
        theta_l = 1.0 - max(0.0, float(pan)) * 0.4
        theta_r = 1.0 + min(0.0, float(pan)) * 0.4
        st = np.column_stack([
            sig[:, 0] * float(gain) * theta_l,
            sig[:, 1] * float(gain) * theta_r,
        ]).astype(np.float32)
    if idx < 0:
        st = st[-idx:]
        idx = 0
    end = min(len(buf), idx + len(st))
    if end > idx:
        buf[idx:end] += st[:end - idx]


def snes_echo(stereo_bus: np.ndarray, taps=(0.18, 0.27, 0.36), gains=(0.32, 0.22, 0.15), lpf=2400.0, mix=0.22) -> np.ndarray:
    """Authentic SNES SPC700 multi-tap low-passed stereo echo."""
    mono = stereo_bus.mean(axis=1)
    n = len(mono)
    sos = signal.butter(2, lpf, btype="low", fs=SR, output="sos")
    filt = signal.sosfilt(sos, mono).astype(np.float32)
    wl = np.zeros(n, dtype=np.float32)
    wr = np.zeros(n, dtype=np.float32)
    for idx_t, (dt_s, g) in enumerate(zip(taps, gains)):
        k = int(round(dt_s * SR))
        if k < n:
            if idx_t % 2 == 0:
                wl[k:] += filt[:n - k] * g
                wr[k:] += filt[:n - k] * (g * 0.65)
            else:
                wr[k:] += filt[:n - k] * g
                wl[k:] += filt[:n - k] * (g * 0.65)
    return stereo_bus + mix * np.column_stack([wl, wr])


def gate_envelope(n_samples: int, windows: list) -> np.ndarray:
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


def render_bank(sound_id: str, seed: int = 7, **kwargs) -> np.ndarray:
    try:
        y, _ = bank.render(sound_id, seed=seed, peak_db=-1.5, checks=False, **kwargs)
    except Exception:
        y, _ = bank.render(sound_id, seed=seed, peak_db=-1.5, checks=False)
    return np.asarray(y, dtype=np.float32)


# -----------------------------------------------------------------------------
# 2. 16-Bit SNES Hybrid Score Builder (Sampled Orchestra + Warm Chiptune)
# -----------------------------------------------------------------------------

def build_pixel_music_bus() -> np.ndarray:
    """
    Composes the 28.0s 16-Bit SNES Hybrid Soundtrack with generous breathing room:
      - 0.00 ~ 1.55s: Sparse intro (lets pipe assembly & warp portal pop shine)
      - 1.60 ~ 9.55s: Section 1A — Cheerful 16-Bit SNES Overworld Theme (marimba + flute +
        pizzicato strings + warm pulse lead + triangle/jazz_bass groove)
      - 9.65 ~ 12.50s: STOP-DOWN #1 — Cliff & Hidden Block Puzzle (music drops out so [?] at
        10.07s and [!] at 11.20s speak in quiet space)
      - 12.60 ~ 15.65s: Section 1B — Ascending Cloud-Ladder Curiosity Harp & Pizzicato Climb
      - 15.65 ~ 16.05s: STOP-DOWN #2 — Breath of silence before Gold [?] Block head-smash!
      - 16.10 ~ 21.25s: Section 2 — Rainbow Star Dash! Joyful upbeat SNES brass/xylophone/
        synth melody (no ear-fatiguing 16th-note square wall)
      - 21.30 ~ 22.80s: STOP-DOWN #3 — Flagpole Catch & Slide pause
      - 22.85 ~ 25.10s: Section 3 — Triumphant SNES Brass, Timpani & Harp Stage Clear Fanfare
      - 25.15 ~ 28.00s: Section 4 — Mysterious Cyber Rift C-minor9 Pad & Smooth Handover
    """
    S.seed(202)
    chip_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    orch_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)

    # =========================================================================
    # SECTION 1A (1.60s ~ 9.55s): Cheerful 16-Bit SNES Overworld Adventure
    # =========================================================================
    bpm_1 = 128.0
    beat_1 = 60.0 / bpm_1  # 0.46875s

    # Melodic phrases with natural rests (lead_note, harm_note, beats)
    melody_1 = [
        ("E5", "C5", 0.5), ("G5", "E5", 0.5), ("REST", "REST", 0.5), ("E5", "C5", 0.5),
        ("C5", "G4", 0.5), ("D5", "B4", 0.5), ("E5", "C5", 1.0),
        ("G5", "D5", 1.0), ("REST", "REST", 1.0), ("G4", "D4", 1.0), ("REST", "REST", 1.0),
        # Phrase B
        ("C5", "E4", 1.0), ("REST", "REST", 0.5), ("G4", "C4", 1.0), ("REST", "REST", 0.5),
        ("E4", "C4", 1.0), ("A4", "F4", 1.0), ("B4", "G4", 0.75), ("A4", "F4", 0.75), ("G4", "E4", 1.5),
        ("E5", "C5", 0.75), ("G5", "E5", 0.75), ("A5", "F5", 1.0), ("F5", "D5", 0.5), ("G5", "E5", 1.0),
        ("E5", "C5", 0.75), ("C5", "A4", 0.5), ("D5", "B4", 0.5), ("B4", "G4", 1.25),
    ]

    cur_t = 1.60
    m_idx = 0
    while cur_t < 9.45:
        l_nt, h_nt, d_beats = melody_1[m_idx % len(melody_1)]
        gap_s = d_beats * beat_1
        dur_s = min(gap_s * 0.86, 9.55 - cur_t)
        if dur_s <= 0.03:
            break
        if l_nt != "REST":
            # Layer warm 25% pulse with real sampled marimba & flute!
            w_pulse = snes_pulse_note(l_nt, dur_s, duty=0.25, cutoff=2300.0, vib=0.008)
            add_at(chip_bus, w_pulse, cur_t, gain=0.16, pan=-0.18)
            add_at(orch_bus, S.note("marimba", l_nt, dur=dur_s * 1.1, vel=0.68), cur_t, gain=0.34, pan=-0.15)
            if d_beats >= 0.75:
                add_at(orch_bus, lp(S.note("flute", l_nt, dur=dur_s, vel=0.60, attack=0.04), 2800.0), cur_t, gain=0.26, pan=0.18)
        if h_nt != "REST":
            add_at(orch_bus, S.note("violins_pizz", h_nt, dur=0.35, vel=0.62), cur_t, gain=0.28, pan=0.22)
        cur_t += gap_s
        m_idx += 1

    # Bouncy quarter-note bass & light woodblock/shaker groove (1.60s ~ 9.50s)
    bass_prog_1 = [
        ("C2", ["C4", "E4", "G4"]), ("G2", ["B3", "D4", "G4"]),
        ("A2", ["A3", "C4", "E4"]), ("E2", ["G3", "B3", "E4"]),
        ("F2", ["F3", "A3", "C4"]), ("C2", ["G3", "C4", "E4"]),
        ("D2", ["F3", "A3", "D4"]), ("G2", ["G3", "B3", "D4"]),
    ]
    t_beat = 1.60
    b_step = 0
    while t_beat < 9.45:
        b_root, ch_notes = bass_prog_1[(b_step // 2) % len(bass_prog_1)]
        b_pitch = b_root if (b_step % 2 == 0) else b_root.replace("2", "3")
        # Warm NES triangle + real contrabass pizzicato
        add_at(chip_bus, nes_tri_bass(b_pitch, beat_1 * 0.82), t_beat, gain=0.22, pan=0.0)
        add_at(orch_bus, S.note("contrabass_pizz", b_root, dur=0.38, vel=0.68), t_beat, gain=0.34, pan=-0.08)

        # Off-beat harp/pizzicato chord comping (light, airy, never dense)
        t_off = t_beat + beat_1 * 0.5
        if t_off < 9.45 and (b_step % 2 == 0):
            add_at(orch_bus, P.strum("harp", ch_notes, dur=0.35, vel=0.58, spread=0.015), t_off, gain=0.22, pan=0.20)
            add_at(orch_bus, S.hit("shaker", "down", vel=0.42), t_off, gain=0.14, pan=-0.22)

        # Light acoustic percussion on beats
        if b_step % 2 == 0:
            add_at(orch_bus, lp(S.hit("cajon", "bass", vel=0.62), 220.0), t_beat, gain=0.26, pan=0.0)
        else:
            add_at(orch_bus, S.hit("woodblock", "a", vel=0.52), t_beat, gain=0.18, pan=0.15)
        t_beat += beat_1
        b_step += 1

    # =========================================================================
    # STOP-DOWN #1 (9.65s ~ 12.50s): Cliff & Hidden Block Puzzle
    # Only two ultra-sparse pizzicato bass notes so [?] (10.07s) and [!] (11.20s)
    # sit in clean, quiet space!
    # =========================================================================
    add_at(orch_bus, S.note("contrabass_pizz", "F2", dur=0.50, vel=0.50), 9.65, gain=0.24, pan=-0.10)
    add_at(orch_bus, S.note("contrabass_pizz", "G2", dur=0.50, vel=0.52), 11.80, gain=0.24, pan=-0.10)

    # =========================================================================
    # SECTION 1B (12.60s ~ 15.65s): Cloud Ladder Ascent (Harp + Marimba + Pizzicato)
    # =========================================================================
    ladder_chords = [
        (12.65, "C3", ["C4", "E4", "G4", "C5"]),
        (13.20, "D3", ["D4", "F#4", "A4", "D5"]),
        (13.80, "E3", ["E4", "G#4", "B4", "E5"]),
        (14.40, "F3", ["F4", "A4", "C5", "F5"]),
        (15.00, "G3", ["G4", "B4", "D5", "G5"]),
    ]
    for t_lc, b_lc, ch_lc in ladder_chords:
        add_at(orch_bus, S.note("cellos_pizz", b_lc, dur=0.55, vel=0.68), t_lc, gain=0.36, pan=-0.12)
        add_at(orch_bus, P.strum("harp", ch_lc, dur=0.65, vel=0.70, spread=0.025), t_lc, gain=0.30, pan=0.15)
        add_at(orch_bus, S.note("marimba", ch_lc[-1], dur=0.45, vel=0.72), t_lc, gain=0.32, pan=0.20)

    # *** 15.65s ~ 16.05s: STOP-DOWN #2 (Breath of silence before Gold [?] Block hit at 16.07s!) ***

    # =========================================================================
    # SECTION 2 (16.10s ~ 21.25s): Rainbow Star Invincibility Theme!
    # Joyful, buoyant 150 BPM SNES Brass + Xylophone + Warm Pulse (no 16th-note noise wall!)
    # =========================================================================
    bpm_2 = 152.0
    beat_2 = 60.0 / bpm_2  # 0.3947s

    powerup_mel = [
        ("C6", "F5", 0.75), ("C6", "F5", 0.75), ("C6", "F5", 0.5),
        ("D5", "A4", 0.5), ("C6", "F5", 0.5), ("REST", "REST", 0.5), ("A5", "F5", 0.5),
        ("B5", "E5", 0.75), ("B5", "E5", 0.75), ("B5", "E5", 0.5),
        ("C5", "G4", 0.5), ("B5", "E5", 0.5), ("REST", "REST", 0.5), ("G5", "E5", 0.5),
    ]
    cur_t = 16.15
    s_idx = 0
    while cur_t < 21.15:
        l_nt, h_nt, d_beats = powerup_mel[s_idx % len(powerup_mel)]
        gap_s = d_beats * beat_2
        dur_s = min(gap_s * 0.85, 21.22 - cur_t)
        if dur_s <= 0.03:
            break
        if l_nt != "REST":
            w_l = snes_pulse_note(l_nt, dur_s, duty=0.5, cutoff=2500.0, vib=0.010)
            add_at(chip_bus, w_l, cur_t, gain=0.17, pan=-0.20)
            add_at(orch_bus, S.note("xylophone", l_nt, dur=dur_s, vel=0.74), cur_t, gain=0.32, pan=-0.15)
            add_at(orch_bus, lp(S.note("trumpet_stac", h_nt, dur=dur_s, vel=0.68), 2800.0), cur_t, gain=0.28, pan=0.22)
            add_at(orch_bus, S.note("glockenspiel", l_nt, dur=dur_s * 1.1, vel=0.60), cur_t, gain=0.18, pan=0.25)
        cur_t += gap_s
        s_idx += 1

    # Upbeat 8th-note bass & harp accompaniment for Power-up state (16.15s ~ 21.20s)
    t_st = 16.15
    st_step = 0
    step_2 = beat_2 * 0.5  # 8th note = 0.197s
    arp_dm = ["D4", "F4", "A4", "C5"]
    arp_cm = ["C4", "E4", "G4", "B4"]
    while t_st < 21.18:
        bar_half = (st_step // 8) % 2
        arp_notes = arp_dm if bar_half == 0 else arp_cm
        nt_a = arp_notes[st_step % 4]
        add_at(orch_bus, P.pluck("harp", nt_a, dur=0.28, vel=0.65), t_st, gain=0.24, pan=0.35 * math.sin(st_step))

        if st_step % 2 == 0:
            b_nt = ("D2" if (st_step // 2) % 2 == 0 else "A2") if bar_half == 0 else ("C2" if (st_step // 2) % 2 == 0 else "G2")
            add_at(chip_bus, nes_tri_bass(b_nt, beat_2 * 0.85), t_st, gain=0.24, pan=0.0)
            add_at(orch_bus, S.note("contrabass_pizz", b_nt, dur=0.34, vel=0.74), t_st, gain=0.36, pan=-0.05)
            if (st_step // 2) % 2 == 0:
                add_at(orch_bus, lp(S.hit("cajon", "bass", vel=0.72), 220.0), t_st, gain=0.30, pan=0.0)
            else:
                add_at(orch_bus, S.hit("snare2", "taps", vel=0.58), t_st, gain=0.22, pan=0.10)
        t_st += step_2
        st_step += 1

    # =========================================================================
    # STOP-DOWN #3 (21.30s ~ 22.80s): Flagpole Catch & Slide
    # Music pauses so the flagpole catch chime (21.70s), slide (21.77s), and
    # fireworks (22.40s, 22.60s, 22.77s) have total clarity!
    # =========================================================================

    # =========================================================================
    # SECTION 3 (22.85s ~ 25.10s): Triumphant SNES Stage Clear Fanfare!
    # Real Trumpet + French Horn + Timpani + Xylophone + Warm Pulse (C -> Ab -> Bb -> C)
    # =========================================================================
    fanfare_seq = [
        ("G4", "E4", "C2", 0.14), ("C5", "G4", "E2", 0.14), ("E5", "C5", "G2", 0.14),
        ("G5", "E5", "C2", 0.20), ("C6", "E5", "C3", 0.22),
        # Ab major climb
        ("Ab4", "Eb4", "Ab2", 0.14), ("C5", "Ab4", "C3", 0.14), ("Eb5", "C5", "Eb3", 0.14),
        ("Ab5", "Eb5", "Ab2", 0.24),
        # Bb major -> C major resolution!
        ("Bb4", "F4", "Bb2", 0.14), ("D5", "Bb4", "D3", 0.14), ("F5", "D5", "F3", 0.14),
        ("Bb5", "F5", "G2", 0.22),
        ("C6", "E5", "C2", 0.65),
    ]
    t_fan = 22.85
    for f_lead, f_harm, f_bass, f_dur in fanfare_seq:
        if t_fan >= 25.10:
            break
        actual_d = min(f_dur * 0.92, 25.12 - t_fan)
        add_at(chip_bus, snes_pulse_note(f_lead, actual_d, duty=0.5, cutoff=2400.0, vib=0.010), t_fan, gain=0.16, pan=-0.15)
        add_at(orch_bus, lp(S.note("trumpet", f_lead, dur=actual_d, vel=0.76), 2900.0), t_fan, gain=0.32, pan=-0.18)
        add_at(orch_bus, lp(S.note("horn", f_harm, dur=actual_d, vel=0.72), 2500.0), t_fan, gain=0.30, pan=0.20)
        add_at(orch_bus, S.note("timpani", f_bass, dur=actual_d * 1.4, vel=0.76), t_fan, gain=0.36, pan=0.0)
        if f_dur >= 0.20:
            add_at(orch_bus, S.note("glockenspiel", f_lead, dur=0.55, vel=0.70), t_fan, gain=0.24, pan=0.15)
        t_fan += f_dur

    # =========================================================================
    # SECTION 4 (25.15s ~ 28.00s): Cyber Portal Rift & 02 -> 03 Handover
    # Warm Cm9 Cello + Viola + Low-passed Synth Pad + Harp/Kalimba Data-Cube Cascade
    # =========================================================================
    for p_pad, pan_p in [("C2", -0.15), ("G2", 0.15), ("Eb3", -0.25), ("G3", 0.25), ("D4", -0.10)]:
        inst_nm = "cellos" if "2" in p_pad else "violas"
        add_at(orch_bus, lp(S.note(inst_nm, p_pad, dur=2.65, vel=0.68, attack=0.25), 2200.0), 25.20, gain=0.36, pan=pan_p)

    # Ascending C-Dorian Harp + Kalimba Data-Cube Cascade (26.30s ~ 27.80s)
    cube_notes = ["C4", "D4", "Eb4", "G4", "A4", "C5", "D5", "Eb5", "G5", "A5", "C6"]
    for i_cb, nt_cb in enumerate(cube_notes):
        t_cb = 26.30 + i_cb * 0.13
        if t_cb >= 27.85:
            break
        pan_cb = 0.45 * math.sin(i_cb * 1.1)
        add_at(orch_bus, P.pluck("harp", nt_cb, dur=0.55, vel=0.68), t_cb, gain=0.28, pan=pan_cb)
        if i_cb % 2 == 0:
            add_at(orch_bus, P.pluck("kalimba", nt_cb, dur=0.42, vel=0.64), t_cb + 0.02, gain=0.24, pan=-pan_cb)

    # Apply SNES 3-tap stereo echo to chip_bus & warm chamber room to orch_bus
    chip_wet = snes_echo(chip_bus, taps=(0.18, 0.27, 0.36), gains=(0.30, 0.20, 0.14), lpf=2300.0, mix=0.22)
    orch_wet = S.room(orch_bus, size=0.42, mix=0.20, predelay=0.012, damp=0.55)[:TOTAL_SAMPLES]
    music_bus = chip_wet + orch_wet

    # Enforce structural stop-downs for wide LRA and crystal-clear puzzle/climax moments
    music_bus *= gate_envelope(TOTAL_SAMPLES, [
        (0.00, 1.52, 0.00, 0.02),   # Let pipe assembly & warp portal pop speak in silence
        (9.65, 12.50, 0.12, 0.06),  # Stop-down #1: Cliff & Hidden Block puzzle ([?] & [!])
        (15.65, 16.06, 0.00, 0.03), # Stop-down #2: Pre-climax breath before Gold [?] Block smash
        (21.30, 22.80, 0.08, 0.05), # Stop-down #3: Flagpole catch & slide
        (27.75, 28.00, 0.00, 0.15), # Clean tail fade
    ])
    return music_bus


# -----------------------------------------------------------------------------
# 3. Tactile, Warm, Non-Harsh 16-Bit & Acoustic Foley Engine
# -----------------------------------------------------------------------------

def render_world_02_audio(audio_events: list, out_wav_path: str) -> dict:
    """
    Renders complete 28.0s 48kHz stereo soundtrack for World 02:
    Combines SNES hybrid BGM + tactile Foley (`earshot.forge.bank` + `sampler` + `pluck`),
    ducks music around key story impacts via `master.sidechain_times`, and masters
    to -14.0 LUFS / <= -2.27 dBTP via `master.finish`.
    """
    print("[Audio 02 Pixel] Building 28.0s SNES Hybrid BGM with structural stop-downs...")
    music_bus = build_pixel_music_bus()
    sfx_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    sc_hits = []

    ladder_notes = ["C5", "D5", "E5", "G5"]
    ladder_idx = 0

    print(f"[Audio 02 Pixel] Rendering {len(audio_events)} tactile Foley events...")
    for ev in audio_events:
        t_ev = float(ev[0])
        name = str(ev[1])
        if t_ev < 0.0 or t_ev >= TOTAL_DURATION - 0.04:
            continue

        if name == "block_assembly":
            # 0.05s: Shimmering harp + kalimba pixel-pipe assembly cascade
            for i, nt in enumerate(["C4", "E4", "G4", "B4", "C5", "E5", "G5"]):
                add_at(sfx_bus, P.pluck("kalimba", nt, dur=0.38, vel=0.64), t_ev + i * 0.065, gain=0.28, pan=-0.35 + i * 0.06)
                add_at(sfx_bus, S.note("harp", nt, dur=0.50, vel=0.60), t_ev + i * 0.065, gain=0.24, pan=-0.25 + i * 0.05)

        elif name == "pipe_pop":
            # 0.67s: Iconic 3-step warm Warp Portal emergence + juicy mouth_plop!
            for step_i, dt_s in enumerate([0.00, 0.068, 0.136]):
                n_b = int(0.062 * SR)
                tt = np.arange(n_b, dtype=np.float64) / SR
                f_arr = (480.0 - step_i * 65.0) + 180.0 * (tt / 0.062)
                w = lp(polyblep_pulse(f_arr, duty=0.5), 1850.0) * np.sin(math.pi * tt / 0.062)
                add_at(sfx_bus, w, t_ev + dt_s, gain=0.26, pan=-0.30)
            add_at(sfx_bus, render_bank("fit/pop/mouth_plop", seed=201), t_ev + 0.16, gain=0.46, pan=-0.28)
            sc_hits.append((t_ev, 0.85))

        elif name == "slime_bounce":
            # Soft squishy landing (`fit/land.light/fingertip_book` + `fit/pop/lip_pop`)
            add_at(sfx_bus, render_bank("fit/land.light/fingertip_book", seed=202), t_ev, gain=0.36, pan=-0.10)
            add_at(sfx_bus, render_bank("fit/pop/lip_pop", seed=203), t_ev + 0.01, gain=0.28, pan=-0.10)

        elif name == "card_appear":
            # 2.27s: [ LV.1 好奇史莱姆 ] RPG status card chime (warm vibraphone + kalimba triad)
            for i, nt in enumerate(["C5", "E5", "G5"]):
                add_at(sfx_bus, S.note("vibraphone", nt, dur=0.65, vel=0.68), t_ev + i * 0.055, gain=0.30, pan=-0.15 + i * 0.10)
                add_at(sfx_bus, P.pluck("music_box", nt, dur=0.45, vel=0.65), t_ev + i * 0.055, gain=0.22, pan=-0.15 + i * 0.10)
            sc_hits.append((t_ev, 0.65))

        elif name == "jump":
            # Warm, gentle 16-bit hop (low-passed pulse glide + soft lip_pop)
            n_j = int(0.16 * SR)
            tt = np.arange(n_j, dtype=np.float64) / SR
            f_arr = 210.0 + 340.0 * ((tt / 0.16) ** 1.3)
            w = lp(polyblep_pulse(f_arr, duty=0.25), 1900.0) * np.sin(math.pi * tt / 0.16) ** 0.8
            add_at(sfx_bus, w, t_ev, gain=0.20, pan=0.0)
            add_at(sfx_bus, render_bank("fit/pop/lip_pop", seed=int(t_ev * 10)), t_ev, gain=0.24, pan=0.0)

        elif name == "stomp":
            # 5.40s: Stomping the Red Ladybug ("啪叽！" — `pro_pop_in/round` + `fit/pop/mouth_plop` + pizzicato G3)
            add_at(sfx_bus, render_bank("pro_pop_in/round", seed=210), t_ev, gain=0.46, pan=-0.05)
            add_at(sfx_bus, render_bank("fit/pop/mouth_plop", seed=211), t_ev + 0.015, gain=0.44, pan=-0.05)
            add_at(sfx_bus, S.note("cellos_pizz", "G3", dur=0.35, vel=0.78), t_ev, gain=0.38, pan=-0.05)
            sc_hits.append((t_ev, 0.85))

        elif name == "coin_get":
            # Classic warm two-tone coin chime (B5 -> E6 on real glockenspiel + vibraphone, zero piercing square wave!)
            add_at(sfx_bus, S.note("vibraphone", "B5", dur=0.18, vel=0.72), t_ev, gain=0.32, pan=0.05)
            add_at(sfx_bus, S.note("glockenspiel", "B5", dur=0.18, vel=0.65), t_ev, gain=0.22, pan=0.05)
            add_at(sfx_bus, S.note("vibraphone", "E6", dur=0.55, vel=0.78), t_ev + 0.075, gain=0.36, pan=0.08)
            add_at(sfx_bus, S.note("glockenspiel", "E6", dur=0.50, vel=0.70), t_ev + 0.075, gain=0.25, pan=0.08)
            sc_hits.append((t_ev, 0.70))

        elif name in ("spring_launch", "super_jump"):
            # 6.80s / 20.87s: Springboard / Super-jump launch (bamboo_tok + warm upward harp/synth sweep)
            add_at(sfx_bus, render_bank("fit/hit/bamboo_tok", seed=220), t_ev, gain=0.42, pan=0.0)
            add_at(sfx_bus, lp(render_bank("whoosh_fast/sleeve", dur=0.38, seed=221), 2400.0), t_ev + 0.02, gain=0.34, pan=0.05)
            arp_sp = ["G4", "B4", "D5", "G5", "B5"] if name == "spring_launch" else ["C5", "E5", "G5", "C6", "E6"]
            add_at(sfx_bus, P.strum("harp", arp_sp, dur=0.48, vel=0.72, spread=0.028), t_ev + 0.01, gain=0.34, pan=0.05)
            sc_hits.append((t_ev, 0.85))

        elif name == "question_bubble":
            # 10.07s: [?] Puzzle Emote in Stop-Down #1 Silence!
            # Curious upward kalimba + clarinet inflection ("Huh?")
            add_at(sfx_bus, render_bank("fit/pop/lip_pop", seed=230), t_ev, gain=0.38, pan=-0.05)
            add_at(sfx_bus, render_bank("pluck/kalimba_soft", pitch="G4", seed=231), t_ev + 0.01, gain=0.38, pan=-0.05)
            add_at(sfx_bus, render_bank("pluck/kalimba_soft", pitch="D5", seed=232), t_ev + 0.11, gain=0.44, pan=0.05)
            add_at(sfx_bus, S.note("clarinet_stac", "D5", dur=0.18, vel=0.72), t_ev + 0.11, gain=0.34, pan=0.05)
            sc_hits.append((t_ev, 0.90))

        elif name == "idea_exclamation":
            # 11.20s: [!] Eureka Discovery in Stop-Down #1 Silence!
            # Radiant small_bell + vibraphone + harp triad (C5 - E5 - G5 - C6)
            add_at(sfx_bus, render_bank("fit/bell/small_bell", seed=240), t_ev, gain=0.42, pan=0.0)
            for i, nt in enumerate(["C5", "E5", "G5", "C6"]):
                add_at(sfx_bus, S.note("vibraphone", nt, dur=0.60, vel=0.74), t_ev + i * 0.045, gain=0.30, pan=-0.12 + i * 0.08)
                add_at(sfx_bus, P.pluck("harp", nt, dur=0.55, vel=0.72), t_ev + i * 0.045, gain=0.28, pan=0.12 - i * 0.08)
            sc_hits.append((t_ev, 0.95))

        elif name in ("hidden_block_hit", "block_hit_gold", "head_smash"):
            # Tactile mechanical block bump (`fit/key.space/thock_space` + `fit/hit/bamboo_tok` + timpani/marimba)
            add_at(sfx_bus, render_bank("fit/key.space/thock_space", seed=250), t_ev, gain=0.52, pan=0.0)
            add_at(sfx_bus, render_bank("fit/hit/bamboo_tok", seed=251), t_ev + 0.005, gain=0.44, pan=0.0)
            add_at(sfx_bus, S.note("marimba", "G4" if name == "hidden_block_hit" else "C5", dur=0.35, vel=0.80), t_ev, gain=0.38, pan=0.0)
            sc_hits.append((t_ev, 0.90))

        elif name == "ladder_grow":
            # 12.63s: 3-Step Cloud Ladder sprouting upward (warm marimba + kalimba + harp scale)
            for i, nt in enumerate(["C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6"]):
                add_at(sfx_bus, P.pluck("kalimba", nt, dur=0.35, vel=0.68), t_ev + i * 0.052, gain=0.30, pan=-0.20 + i * 0.05)
                if i % 2 == 0:
                    add_at(sfx_bus, S.note("marimba", nt, dur=0.35, vel=0.70), t_ev + i * 0.052, gain=0.28, pan=0.15)

        elif name == "ladder_step":
            nt = ladder_notes[ladder_idx % len(ladder_notes)]
            ladder_idx += 1
            add_at(sfx_bus, render_bank("fit/land.light/fingertip_book", seed=260 + ladder_idx), t_ev, gain=0.32, pan=0.0)
            add_at(sfx_bus, P.pluck("kalimba", nt, dur=0.32, vel=0.68), t_ev, gain=0.30, pan=0.0)

        elif name == "coins_fountain":
            # 16.15s: Sparkling coin fountain out of the Gold [?] Block (right after Stop-Down #2!)
            for i, nt in enumerate(["G5", "B5", "D6", "G6", "B6"]):
                add_at(sfx_bus, S.note("glockenspiel", nt, dur=0.45, vel=0.72), t_ev + i * 0.055, gain=0.26, pan=-0.20 + i * 0.10)
                add_at(sfx_bus, S.note("vibraphone", nt, dur=0.50, vel=0.74), t_ev + i * 0.055, gain=0.28, pan=0.20 - i * 0.10)
            sc_hits.append((t_ev, 0.85))

        elif name in ("star_power_up", "invincible_bgm_start"):
            # 16.93s: Rainbow Star power-up cascade (concert harp + tubular bell + shimmer)
            if name == "star_power_up":
                add_at(sfx_bus, P.strum("harp", ["C5", "E5", "G5", "B5", "D6", "G6"], dur=0.80, vel=0.80, spread=0.035), t_ev, gain=0.38, pan=0.0)
                add_at(sfx_bus, lp(render_bank("shimmer/m0", seed=270), 4200.0), t_ev, gain=0.24, pan=0.0)
                sc_hits.append((t_ev, 0.80))

        elif name == "enemy_ram":
            # 18.63s / 19.40s / 26.17s: Bowling-pin knock-out of Cloud Monsters!
            add_at(sfx_bus, render_bank("pro_impact/short", seed=int(t_ev * 10)), t_ev, gain=0.48, pan=0.10)
            add_at(sfx_bus, render_bank("fit/hit/bamboo_tok", seed=int(t_ev * 10) + 1), t_ev + 0.01, gain=0.42, pan=0.12)
            add_at(sfx_bus, S.note("timpani", "G2", dur=0.45, vel=0.78), t_ev, gain=0.36, pan=0.10)
            sc_hits.append((t_ev, 0.85))

        elif name == "extra_life_sound":
            # 19.48s: Warm, sweet 6-note 1-UP jingle (E5 - G5 - E6 - C6 - D6 - G6 on vibraphone + glockenspiel)
            for i, nt in enumerate(["E5", "G5", "E6", "C6", "D6", "G6"]):
                add_at(sfx_bus, S.note("vibraphone", nt, dur=0.25, vel=0.74), t_ev + i * 0.072, gain=0.30, pan=0.15)
                add_at(sfx_bus, S.note("glockenspiel", nt, dur=0.25, vel=0.68), t_ev + i * 0.072, gain=0.22, pan=0.15)
            sc_hits.append((t_ev, 0.80))

        elif name in ("flagpole_top_catch", "score_jackpot"):
            # 21.70s: Catching the top of the flagpole (+5000) in Stop-Down #3 silence!
            if name == "flagpole_top_catch":
                add_at(sfx_bus, S.note("tubular_bells", "G5", dur=1.20, vel=0.80), t_ev, gain=0.38, pan=0.15)
                add_at(sfx_bus, P.strum("harp", ["G4", "B4", "D5", "G5", "B5", "D6"], dur=0.85, vel=0.78, spread=0.03), t_ev, gain=0.36, pan=0.15)
                sc_hits.append((t_ev, 0.90))

        elif name == "flagpole_slide":
            # 21.77s: Smooth flagpole slide-down (descending harp + xylophone + soft cloth swipe)
            add_at(sfx_bus, lp(render_bank("swipe/cloth", dur=0.75, seed=280), 2200.0), t_ev, gain=0.32, pan=0.15)
            slide_nts = ["G6", "E6", "D6", "B5", "G5", "E5", "D5", "B4", "G4"]
            for i, nt in enumerate(slide_nts):
                add_at(sfx_bus, S.note("xylophone", nt, dur=0.18, vel=0.65), t_ev + i * 0.075, gain=0.26, pan=0.15)

        elif name == "firework_bang":
            # 22.40s, 22.60s, 22.77s: 3 Pixel Fireworks above the red-brick castle!
            add_at(sfx_bus, render_bank("pro_sub_drop/soft", dur=0.45, seed=int(t_ev * 100)), t_ev, gain=0.38, pan=0.20)
            add_at(sfx_bus, S.note("timpani", "C2", dur=0.50, vel=0.78), t_ev, gain=0.36, pan=0.20)
            add_at(sfx_bus, S.note("hand_chimes", "E6", dur=0.65, vel=0.70), t_ev + 0.03, gain=0.26, pan=0.25)
            sc_hits.append((t_ev, 0.75))

        elif name in ("star_coin_absorb", "stage_clear_jingle"):
            if name == "star_coin_absorb":
                # 23.87s: Absorbing the 16-Bit Arcade Coin Token!
                add_at(sfx_bus, render_bank("fit/bell/small_bell", seed=290), t_ev, gain=0.40, pan=0.10)
                add_at(sfx_bus, P.strum("harp", ["C5", "E5", "G5", "B5", "C6", "E6"], dur=0.90, vel=0.80, spread=0.035), t_ev, gain=0.38, pan=0.10)
                sc_hits.append((t_ev, 0.85))

        elif name == "cyber_rift_tear":
            # 25.13s: Purple-cyan Cyber Portal Rift opening inside the dark castle doorway
            add_at(sfx_bus, render_bank("pro_sub_drop/ref", dur=1.10, seed=295), t_ev, gain=0.48, pan=0.0)
            add_at(sfx_bus, lp(render_bank("whoosh_big/swell", dur=1.25, seed=296), 2400.0), t_ev, gain=0.34, pan=0.0)
            add_at(sfx_bus, S.note("tubular_bells", "C4", dur=1.60, vel=0.76), t_ev + 0.05, gain=0.34, pan=0.0)
            sc_hits.append((t_ev, 0.90))

    # Place Foley in a cohesive warm room
    sfx_wet = S.room(lp(sfx_bus, 5200.0), size=0.32, mix=0.15, predelay=0.010, damp=0.58)[:TOTAL_SAMPLES]

    # Sidechain duck music under foreground Foley hits
    sc_env = earshot_master.sidechain_times(sc_hits, TOTAL_SAMPLES, depth=0.45, tau=0.14).astype(np.float32)
    raw_mix = music_bus * sc_env + sfx_wet

    # Master to exact -14.0 LUFS and <= -2.27 dBTP (ceiling=0.77)
    mastered, _ = earshot_master.finish(
        raw_mix,
        lufs=-14.0,
        ceiling=0.77,
        mono_hz=120.0,
        comp=True,
        drive=1.08,
        air=0.10,
        hp_hz=28.0,
        end_fade=0.08,
        tail_zero=480,
    )
    mastered = mastered[:TOTAL_SAMPLES].astype(np.float32)

    os.makedirs(os.path.dirname(os.path.abspath(out_wav_path)), exist_ok=True)
    sf.write(out_wav_path, mastered, SR, subtype="PCM_24")
    metrics = earshot_master.measure(mastered)
    print(f"[Audio 02 Pixel] Mastered {out_wav_path} -> {metrics}")
    return metrics


if __name__ == "__main__":
    from sim_02_pixel import simulate_world_02
    _, events = simulate_world_02()
    out_wav = os.path.join(CUR_DIR, "world_02_pixel.wav")
    render_world_02_audio(events, out_wav)
