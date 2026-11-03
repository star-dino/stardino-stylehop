#!/usr/bin/env python3
"""
StyleHop Cue-Driven Procedural Sound, Physical Modeling & Score Synthesizer (`tools/sound.py`).

Pure Python (NumPy + SciPy + stdlib `wave`) synthesizer that turns a deterministic
DOM & runtime motion cue sheet (`window.CUES` -> `cues.json`) into a mastered 48kHz 16-bit
stereo WAV soundtrack with medium-specific physical modeling instruments, rhythmic
sequencers, acoustic body Impulse Response (IR) convolution, and frame-accurate foley:

  - `ink` (`ink-wash`): Extended Karplus-Strong Guqin waveguide (`散音` open bass, `泛音`
    crystalline harmonics, `走手音/吟猱` sliding press notes) convolved with a Paulownia
    wooden soundbox IR + overblown bamboo Xiao flute (`洞箫`) + water/silk/sword foley.
  - `jazz` (`rubber-hose`): 1930s 126-BPM Swing sequencer (2:1 swing ratio) with walking
    upright bass, wire-brush snare groove, nonlinear waveshaped Wah-Wah plunger-muted brass
    stabs & trombone glissando, cartoon foley, and 1930s optical film / 78rpm shellac patina.
  - `clay` (`clay-macaron`): Euler-Bernoulli modal synthesis rosewood marimba & kalimba tine
    arpeggiator + matte polymer clay squish & woodblock tabletop foley.
  - `paper` (`paper-popup`): Plucked acoustic harp/guitar harmonics + multi-stage cardstock
    crease, pop-up snap, and page-turn foley.
  - `twilight` (`twilight-fable`): Celesta bell-tine modal synth + warm felt-piano chords +
    bioluminescent night-forest breeze shimmer.
  - `glass` / `cyber` / `terminal`: Modern crystalline / synth harmonic beds & UI foley.

Usage:
  python3 tools/sound.py --cues cues.json --out <work-dir>/mix.wav [--preset ink|jazz|clay|paper|twilight|glass|cyber|terminal]
  python3 tools/sound.py --cues cues.json --voice voice.wav --out mix.wav [--duck-db -10] [--voice-gain 0]
"""

import argparse
import json
from pathlib import Path
import sys
import wave
import zlib
import numpy as np
from scipy import signal

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))
try:
    from audio_grains import ensure_audio_grains
except Exception:
    ensure_audio_grains = None

SR = 48000

PRESETS = {
    "ink": {
        "scale": [146.83, 164.81, 196.00, 220.00, 261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33],
        "chords": [
            [98.00, 146.83, 196.00, 293.66, 392.00],   # G2 - D3 - G3 - D4 - G4 (散音五度)
            [110.00, 164.81, 220.00, 329.63, 440.00],  # A2 - E3 - A3 - E4 - A4
            [82.41, 123.47, 164.81, 246.94, 329.63],   # E2 - B2 - E3 - B3 - E4
            [98.00, 146.83, 220.00, 293.66, 440.00],   # G2 - D3 - A3 - D4 - A4
        ],
        "pad_gain": 0.14,
        "chime_freqs": [587.33, 880.00, 1174.66, 1567.98],
        "tap_freq": 340.0,
        "tick_freq": 1180.0,
    },
    "naturalist": {
        "scale": [146.83, 164.81, 174.61, 196.00, 220.00, 233.08, 261.63, 293.66, 329.63, 349.23, 392.00, 440.00],
        "chords": [
            [146.83, 220.00, 293.66, 349.23, 440.00],  # Dm (Baroque plate curiosity)
            [116.54, 174.61, 233.08, 293.66, 440.00],  # Bbmaj7 (Comparative anatomy)
            [110.00, 164.81, 220.00, 277.18, 349.23],  # A7b9 / Gm6 tension (Selection pressure)
            [146.83, 220.00, 293.66, 369.99, 440.00],  # D major Picardy third (Tree of Life revelation)
        ],
        "pad_gain": 0.13,
        "chime_freqs": [587.33, 880.00, 1174.66, 1479.98],
        "tap_freq": 460.0,
        "tick_freq": 2180.0,
    },
    "jazz": {
        "bpm": 126.0,
        "chords": [
            [116.54, 146.83, 174.61, 207.65, 261.63],  # Bb6/7
            [98.00, 123.47, 146.83, 174.61, 220.00],   # G7
            [130.81, 155.56, 196.00, 233.08, 293.66],  # Cm9
            [174.61, 220.00, 261.63, 311.13, 392.00],  # F13
        ],
        "bass_walk": [
            [116.54, 146.83, 174.61, 185.00],  # Bb2 - D3 - F3 - F#3
            [196.00, 164.81, 146.83, 123.47],  # G3 - E3 - D3 - B2
            [130.81, 146.83, 155.56, 164.81],  # C3 - D3 - Eb3 - E3
            [174.61, 146.83, 130.81, 110.00],  # F3 - D3 - C3 - A2
        ],
        "pad_gain": 0.16,
        "chime_freqs": [466.16, 587.33, 698.46, 880.00],
        "tap_freq": 480.0,
        "tick_freq": 1850.0,
    },
    "clay": {
        "chords": [
            [261.63, 329.63, 392.00, 523.25, 659.25],  # Sunny Cmaj6/9
            [349.23, 440.00, 523.25, 659.25],          # Fmaj7
            [293.66, 392.00, 493.88, 587.33],          # G6
            [220.00, 329.63, 392.00, 493.88, 587.33],  # Am9 -> C
        ],
        "pad_gain": 0.14,
        "chime_freqs": [659.25, 783.99, 1046.50, 1318.51],
        "tap_freq": 520.0,
        "tick_freq": 1680.0,
    },
    "paper": {
        "chords": [
            [293.66, 369.99, 440.00, 587.33, 659.25],  # Dadd9
            [246.94, 329.63, 392.00, 493.88, 587.33],  # Em7
            [196.00, 293.66, 392.00, 493.88, 659.25],  # Gmaj9
            [220.00, 293.66, 369.99, 440.00, 587.33],  # A6sus4
        ],
        "pad_gain": 0.13,
        "chime_freqs": [783.99, 987.77, 1174.66, 1567.98],
        "tap_freq": 420.0,
        "tick_freq": 1350.0,
    },
    "twilight": {
        "chords": [
            [261.63, 329.63, 392.00, 523.25, 587.33],  # Scene 1: Cadd9 (C4 - E4 - G4 - C5 - D5, pure open consonant)
            [220.00, 261.63, 329.63, 392.00, 523.25],  # Scene 2: Am7 (A3 - C4 - E4 - G4 - C5)
            [174.61, 261.63, 349.23, 440.00, 523.25],  # Scene 3: Fadd9 (F3 - C4 - F4 - A4 - C5)
            [261.63, 329.63, 392.00, 523.25, 659.25],  # Scene 4: Cmaj (C4 - E4 - G4 - C5 - E5, warm home resolution)
        ],
        "pad_gain": 0.11,
        "chime_freqs": [392.00, 523.25, 587.33, 659.25],
        "tap_freq": 261.63,
        "tick_freq": 523.25,
    },
    "glass": {
        "chords": [
            [261.63, 329.63, 392.00, 493.88, 587.33],
            [220.00, 261.63, 329.63, 392.00, 493.88],
            [174.61, 220.00, 261.63, 349.23, 392.00],
            [196.00, 246.94, 293.66, 392.00, 440.00],
        ],
        "pad_gain": 0.14,
        "chime_freqs": [1046.50, 1318.51, 1567.98, 1975.53],
        "tap_freq": 880.0,
        "tick_freq": 2100.0,
    },
    "cyber": {
        "chords": [
            [130.81, 196.00, 261.63, 311.13, 392.00],
            [103.83, 155.56, 207.65, 261.63, 311.13],
            [116.54, 174.61, 233.08, 293.66, 349.23],
            [98.00, 146.83, 196.00, 246.94, 293.66],
        ],
        "pad_gain": 0.16,
        "chime_freqs": [1046.50, 1244.51, 1567.98, 2093.00],
        "tap_freq": 640.0,
        "tick_freq": 2600.0,
    },
    "terminal": {
        "chords": [
            [55.00, 82.41, 110.00, 146.83],
            [49.00, 73.42, 98.00, 130.81],
            [58.27, 87.31, 116.54, 146.83],
            [55.00, 82.41, 110.00, 138.59],
        ],
        "pad_gain": 0.09,
        "chime_freqs": [165.00, 220.00, 246.94, 293.66],
        "tap_freq": 185.0,
        "tick_freq": 280.0,
    },
    "mech": {
        "chords": [
            [55.00, 82.41, 110.00, 146.83],
            [49.00, 73.42, 98.00, 130.81],
            [58.27, 87.31, 116.54, 146.83],
            [55.00, 82.41, 110.00, 138.59],
        ],
        "pad_gain": 0.09,
        "chime_freqs": [165.00, 220.00, 246.94, 293.66],
        "tap_freq": 185.0,
        "tick_freq": 280.0,
    },
}

PRESET_ALIASES = {
    "glass_bento": "glass",
    "clay_desk": "clay",
    "claymation": "clay",
    "clay-macaron": "clay",
    "riso_press": "paper",
    "paper-popup": "paper",
    "ink_scroll": "ink",
    "ink-wash": "ink",
    "rubber-hose": "jazz",
    "swing": "jazz",
    "twilight-fable": "twilight",
    "vintage-naturalist": "naturalist",
    "copperplate": "naturalist",
    "crt_synth": "mech",
    "terminal": "mech",
    "industrial-mech": "mech",
    "calibration-lab": "mech",
    "blueprint_mech": "cyber",
}


def resolve_preset(name: str) -> str:
    if not name:
        return "glass"
    key = PRESET_ALIASES.get(name, name)
    return key if key in PRESETS else "glass"


# =============================================================================
# 0. HYBRID GRAIN BANK LOADER & CORE PHYSICAL MODELING TOOLKIT
# =============================================================================

_GRAIN_CACHE = {}


def load_grain(name: str) -> np.ndarray:
    """Loads a 48kHz WAV grain from `assets/audio/<name>.wav` (auto-building if missing)."""
    key = name if name.endswith(".wav") else f"{name}.wav"
    if key in _GRAIN_CACHE:
        return _GRAIN_CACHE[key]
    audio_dir = REPO_ROOT / "assets" / "audio"
    fpath = audio_dir / key
    if not fpath.exists() and ensure_audio_grains is not None:
        ensure_audio_grains(audio_dir)
    if not fpath.exists():
        return np.zeros(int(0.2 * SR), dtype=np.float64)
    with wave.open(str(fpath), "rb") as wf:
        nch = wf.getnchannels()
        nframes = wf.getnframes()
        raw = np.frombuffer(wf.readframes(nframes), dtype=np.int16).astype(np.float64) / 32768.0
        if nch > 1:
            raw = raw.reshape(-1, nch)
    _GRAIN_CACHE[key] = raw
    return raw


def slice_grain(
    name: str,
    dur: float,
    pitch=1.0,
    rng: np.random.Generator = None,
    random_offset: bool = True,
    gain: float = 1.0,
) -> np.ndarray:
    """
    Slices a mono segment from a pre-baked acoustic grain in `assets/audio/`, applies
    fractional pitch-shifting (so every event has unique formant/pitch variation), and
    applies smooth raised-cosine anti-click fades.
    Accepts `dur` either in seconds (float <= 60) or in sample count (int > 60), and
    allows the 3rd positional arg to be either `pitch` (float) or `rng` (Generator).
    """
    if isinstance(pitch, np.random.Generator):
        rng = pitch
        pitch = 1.0
    if rng is None:
        rng = np.random.default_rng(101)
    raw = load_grain(name)
    if raw.ndim == 2:
        raw = raw.mean(axis=1)
    if isinstance(dur, (int, np.integer)) and dur > 60:
        n_out = max(16, int(dur))
    else:
        n_out = max(16, int(round(float(dur) * SR)))
    pitch_eff = float(np.clip(float(pitch) * rng.uniform(0.95, 1.05), 0.55, 1.95))
    n_src = max(16, int(round(n_out * pitch_eff)))

    if len(raw) <= n_src:
        reps = int(np.ceil(n_src / max(1, len(raw)))) + 1
        src = np.tile(raw, reps)[:n_src]
    else:
        max_off = len(raw) - n_src
        off = int(rng.integers(0, max_off + 1)) if random_offset and max_off > 0 else 0
        src = raw[off : off + n_src]

    # Fast linear interpolation resampling for pitch shift
    x_old = np.linspace(0.0, 1.0, len(src))
    x_new = np.linspace(0.0, 1.0, n_out)
    out = np.interp(x_new, x_old, src)
    return fade_in_out(out, 0.002, 0.015) * float(gain)


def fade_in_out(sig: np.ndarray, fade_in_s: float = 0.002, fade_out_s: float = 0.015) -> np.ndarray:
    """Smooth raised-cosine fade-in and fade-out so event boundaries never click."""
    n = len(sig)
    if n < 4:
        return sig
    out = sig.copy()
    fi = min(int(fade_in_s * SR), n // 3)
    fo = min(int(fade_out_s * SR), n // 3)
    if fi > 1:
        w_in = 0.5 * (1.0 - np.cos(np.pi * np.arange(fi) / fi))
        out[:fi] *= w_in[:, None] if out.ndim == 2 else w_in
    if fo > 1:
        w_out = 0.5 * (1.0 + np.cos(np.pi * np.arange(fo) / fo))
        out[-fo:] *= w_out[:, None] if out.ndim == 2 else w_out
    return out


def generate_pink_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    """True 1/f pink noise via FFT spectral shaping (never harsh white noise)."""
    if n < 8:
        return np.zeros(max(1, n), dtype=np.float64)
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / SR)
    scale = 1.0 / np.sqrt(np.maximum(freqs, 20.0))
    scale[0] = 0.0
    pink = np.fft.irfft(spec * scale, n=n)
    return pink / (np.max(np.abs(pink)) + 1e-12)


def time_varying_bandpass(
    sig: np.ndarray,
    f_curve,
    q: float = 2.6,
    btype: str = "bandpass",
    block: int = 128,
) -> np.ndarray:
    """Zipper-free block-wise biquad filter sweep carrying exact state `zi` across blocks."""
    n = len(sig)
    if np.ndim(f_curve) == 0:
        f_arr = np.full(n, float(f_curve), dtype=np.float64)
    else:
        f_arr = np.asarray(f_curve, dtype=np.float64)
    out = np.zeros(n, dtype=np.float64)
    nyq = 0.5 * SR
    zi = None
    for i in range(0, n, block):
        j = min(n, i + block)
        fc = float(np.clip(f_arr[min(len(f_arr) - 1, (i + j) // 2)], 35.0, nyq * 0.92))
        if btype == "bandpass":
            bw = max(fc / max(q, 0.5), 28.0)
            low = np.clip((fc - 0.5 * bw) / nyq, 0.001, 0.94)
            high = np.clip((fc + 0.5 * bw) / nyq, low + 0.002, 0.96)
            sos = signal.butter(2, [low, high], btype="bandpass", output="sos")
        elif btype == "low":
            sos = signal.butter(2, np.clip(fc / nyq, 0.002, 0.96), btype="low", output="sos")
        else:
            sos = signal.butter(2, np.clip(fc / nyq, 0.002, 0.96), btype="high", output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2), dtype=np.float64)
        out[i:j], zi = signal.sosfilt(sos, sig[i:j], zi=zi)
    return out


def modal_strike(
    f0: float,
    dur: float,
    material: str = "wood",
    pitch_drop=0.0,
    rng: np.random.Generator = None,
    amp: float = 1.0,
) -> np.ndarray:
    """Physical modal resonator + contact transient for wood, marimba, ceramic, glass, bell, brass, timpani, metal."""
    if isinstance(pitch_drop, np.random.Generator):
        rng = pitch_drop
        pitch_drop = 0.0
    if rng is None:
        rng = np.random.default_rng(101)
    n = max(16, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR

    if material == "wood":
        ratios, amps, decays = [1.0, 2.42, 4.15, 6.32], [1.0, 0.45, 0.22, 0.08], [0.055, 0.028, 0.014, 0.007]
        click_freq, click_dur, click_amp = 1400.0, 0.0035, 0.42
    elif material == "marimba":
        ratios, amps, decays = [1.0, 3.98, 9.25, 14.8], [1.0, 0.38, 0.14, 0.04], [0.18, 0.058, 0.018, 0.006]
        click_freq, click_dur, click_amp = 1800.0, 0.003, 0.30
    elif material == "ceramic":
        ratios, amps, decays = (
            [1.0, 1.58, 2.37, 3.44],
            [0.9, 0.55, 0.32, 0.14],
            [0.085, 0.055, 0.032, 0.018],
        )
        click_freq, click_dur, click_amp = 2200.0, 0.0025, 0.28
    elif material == "glass":
        ratios, amps, decays = [1.0, 2.0, 3.0], [1.0, 0.28, 0.08], [0.38, 0.18, 0.075]
        click_freq, click_dur, click_amp = 1800.0, 0.0025, 0.14
    elif material == "bell":
        ratios = [0.5, 1.0, 1.501, 2.0, 2.44]
        amps = [0.32, 1.0, 0.36, 0.40, 0.14]
        decays = [0.65, 0.52, 0.34, 0.24, 0.12]
        click_freq, click_dur, click_amp = 2100.0, 0.0025, 0.18
    elif material == "brass":
        ratios, amps, decays = (
            [1.0, 1.498, 2.002, 2.76, 3.85, 5.12],
            [1.0, 0.55, 0.48, 0.28, 0.15, 0.08],
            [0.34, 0.25, 0.19, 0.11, 0.065, 0.035],
        )
        click_freq, click_dur, click_amp = 2600.0, 0.0025, 0.40
    elif material == "timpani":
        ratios, amps, decays = (
            [1.0, 1.504, 1.742, 2.00, 2.295],
            [1.0, 0.62, 0.38, 0.26, 0.14],
            [0.52, 0.34, 0.22, 0.16, 0.10],
        )
        click_freq, click_dur, click_amp = 420.0, 0.008, 0.35
    else:  # metal
        ratios, amps, decays = (
            [1.0, 1.38, 1.92, 2.78, 4.05, 5.88],
            [0.9, 0.65, 0.5, 0.35, 0.22, 0.12],
            [0.09, 0.06, 0.045, 0.03, 0.018, 0.01],
        )
        click_freq, click_dur, click_amp = 2900.0, 0.002, 0.55

    out = np.zeros(n, dtype=np.float64)
    if abs(float(pitch_drop)) > 1e-4:
        f_env = f0 * (1.0 + float(pitch_drop) * np.exp(-t / 0.035))
        phase_base = 2.0 * np.pi * np.cumsum(f_env) / SR
    else:
        phase_base = 2.0 * np.pi * f0 * t

    att = 1.0 - np.exp(-t / 0.0008)
    for r, a, d in zip(ratios, amps, decays):
        if f0 * r >= 0.46 * SR:
            continue
        det = 1.0 + rng.uniform(-0.003, 0.003)
        out += a * att * np.exp(-t / d) * np.sin(r * det * phase_base)

    c_len = min(int(click_dur * SR * 4), n)
    if c_len > 8:
        t_c = np.arange(c_len) / SR
        burst = rng.standard_normal(c_len) * np.exp(-t_c / click_dur)
        nyq = 0.5 * SR
        bw_low = np.clip(click_freq * 0.5 / nyq, 0.01, 0.85)
        bw_high = np.clip(click_freq * 1.6 / nyq, bw_low + 0.02, 0.95)
        transient = signal.sosfilt(signal.butter(2, [bw_low, bw_high], btype="bandpass", output="sos"), burst)
        mallet = np.sin(np.pi * np.clip(t_c / (click_dur * 1.5), 0.0, 1.0)) * np.exp(-t_c / click_dur)
        out[:c_len] += click_amp * (0.65 * transient + 0.35 * mallet)

    mx = float(np.max(np.abs(out))) + 1e-12
    return fade_in_out(out / mx, fade_in_s=0.0004, fade_out_s=0.015) * float(amp)


def minnaert_bubble(f0: float, dur: float = 0.034, sweep_mult: float = 2.15, amp: float = 1.0) -> np.ndarray:
    """Minnaert physical bubble resonance sweeping upward as bubble neck pinches off."""
    n = max(10, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR
    tau = dur * 0.75
    f_inst = f0 * (1.0 + (sweep_mult - 1.0) * np.power(np.clip(t / tau, 0.0, 1.2), 1.7))
    phase = 2.0 * np.pi * np.cumsum(f_inst) / SR
    env = (1.0 - np.exp(-t / 0.0022)) * np.exp(-t / (dur * 0.33))
    return fade_in_out(env * np.sin(phase), 0.0004, 0.004) * float(amp)


def pan_stereo_haas(mono: np.ndarray, pan: float = 0.0, haas_ms: float = 0.16) -> np.ndarray:
    """Equal-power stereo panner with subtle Haas micro-delay on the contralateral channel."""
    pan = float(np.clip(pan, -1.0, 1.0))
    angle = (pan + 1.0) * (np.pi / 4.0)
    g_l, g_r = np.cos(angle), np.sin(angle)
    n = len(mono)
    out = np.zeros((n, 2), dtype=np.float64)
    delay_samples = int(abs(pan) * (haas_ms * 0.001 * SR))
    if 0 < delay_samples < n:
        if pan < 0:
            out[:, 0] = mono * g_l
            out[delay_samples:, 1] = mono[:-delay_samples] * g_r
        else:
            out[delay_samples:, 0] = mono[:-delay_samples] * g_l
            out[:, 1] = mono * g_r
    else:
        out[:, 0] = mono * g_l
        out[:, 1] = mono * g_r
    return out


def add_studio_tail(
    stereo: np.ndarray,
    wet: float = 0.14,
    rt60: float = 0.26,
    damp_hz: float = 3800.0,
    room_size: float = None,
) -> np.ndarray:
    """Finite 10-tap early reflection + air-damped room tail so foley events sit in a real acoustic space."""
    if room_size is not None:
        rt60 = float(room_size)
    tail_len = int(rt60 * 1.25 * SR)
    n_in = len(stereo)
    total_len = n_in + tail_len
    padded = np.zeros((total_len, 2), dtype=np.float64)
    padded[:n_in] = stereo
    taps_ms = [6.7, 11.3, 17.9, 24.1, 32.3, 43.7, 56.9, 73.1, 94.7, 121.3]
    refl = np.zeros_like(padded)
    for idx, t_ms in enumerate(taps_ms):
        d = int(t_ms * 0.001 * SR)
        if d >= total_len:
            continue
        decay_gain = (10.0 ** (-3.0 * (t_ms * 0.001) / max(rt60, 0.05))) * (0.85 ** idx)
        if idx % 2 == 0:
            refl[d:, 0] += padded[:-d, 0] * decay_gain
            refl[d:, 1] += padded[:-d, 1] * decay_gain * 0.90
        else:
            refl[d:, 0] += padded[:-d, 1] * decay_gain * 0.88
            refl[d:, 1] += padded[:-d, 0] * decay_gain
    sos_lp = signal.butter(2, float(np.clip(damp_hz, 250.0, 14000.0)) / (0.5 * SR), btype="low", output="sos")
    sos_hp = signal.butter(1, 110.0 / (0.5 * SR), btype="high", output="sos")
    refl = signal.sosfilt(sos_lp, refl, axis=0)
    refl = signal.sosfilt(sos_hp, refl, axis=0)
    return fade_in_out(padded + wet * refl, fade_in_s=0.0004, fade_out_s=0.025)


def load_sample_wav(path: str) -> np.ndarray:
    """Decode an indexed 48 kHz stereo wav to float32 (n, 2)."""
    from scipy.io import wavfile

    rate, data = wavfile.read(path)
    if rate != SR:
        raise ValueError(f"sample.py index must be 48 kHz, got {rate}: {path}")
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    return (data.astype(np.float32) / 32768.0)


def pitch_sample(sig: np.ndarray, ratio: float) -> np.ndarray:
    """Cheap linear resample: `ratio` < 1 lowers pitch, > 1 raises it."""
    if abs(ratio - 1.0) < 1e-4:
        return sig
    n = max(16, int(round(len(sig) / ratio)))
    src = np.linspace(0.0, len(sig) - 1.0, n)
    i0 = np.floor(src).astype(np.int64)
    i1 = np.minimum(i0 + 1, len(sig) - 1)
    frac = (src - i0)[:, None]
    return (sig[i0] * (1.0 - frac) + sig[i1] * frac).astype(np.float32)


def overlay_samples(stereo: np.ndarray, cue_data: dict, sample_map_path: str) -> tuple[np.ndarray, list[str]]:
    """
    Add recorded one-shots over the synthesized score.

    `sample_map_path` is a style-level JSON: an index path plus kind -> sample bindings:
      { "index": "../../../out/samples-cache/index.json",
        "map": { "brass_ratchet": {"sample": "ratchet-crank", "gain": 0.9} },
        "bed": {"sample": "cello-bed", "gain": 0.16, "pitch": 0.5} }
    A missing cache is not an error: the score falls back to synthesis.
    """
    import json as _json
    from pathlib import Path as _Path

    map_path = _Path(sample_map_path)
    if not map_path.is_file():
        return stereo, []
    cfg = _json.loads(map_path.read_text(encoding="utf-8"))
    index_path = _Path(cfg.get("index", "../../../out/samples-cache/index.json"))
    if not index_path.is_absolute():
        index_path = (map_path.parent / index_path).resolve()
    if not index_path.is_file():
        print(f"[sound] samples: no index at {index_path}; falling back to synthesis", file=sys.stderr)
        return stereo, []
    index = _json.loads(index_path.read_text(encoding="utf-8"))
    cache = _Path(index.get("cache", index_path.parent))
    entries = index.get("samples", {})
    used: list[str] = []

    def play(ident: str, t: float, gain: float, ratio: float, pan: float) -> None:
        entry = entries.get(ident)
        if not entry:
            return
        path = cache / entry["file"]
        if not path.is_file():
            return
        sig = pitch_sample(load_sample_wav(str(path)), ratio)
        sig = sig * float(gain) * float(entry.get("gain", 1.0))
        mix_into(stereo, int(round(t * SR)), sig, pan=pan)
        used.append(ident)

    bed = cfg.get("bed")
    if bed and bed.get("sample"):
        entry = entries.get(bed["sample"])
        if entry:
            path = cache / entry["file"]
            if path.is_file():
                sig = pitch_sample(load_sample_wav(str(path)), float(bed.get("pitch", 1.0)))
                gain = float(bed.get("gain", 0.12))
                reps = int(np.ceil(float(cue_data.get("dur", 6.0)) * SR / max(1, len(sig)))) + 1
                loop = np.tile(sig, (reps, 1))[: int(float(cue_data.get("dur", 6.0)) * SR)]
                loop *= gain
                loop = fade_in_out(loop, 0.6, 0.9)
                stereo[: len(loop)] += loop
                used.append(bed["sample"])

    bindings = cfg.get("map", {})
    for idx, cue in enumerate(cue_data.get("cues", [])):
        kind = str(cue.get("kind", ""))
        bind = bindings.get(kind)
        if not bind:
            continue
        intensity = float(cue.get("intensity", 0.75))
        pan = float(np.clip(((zlib.crc32(f"{kind}:{idx}".encode()) % 100) - 50) / 125.0, -0.4, 0.4))
        play(
            bind.get("sample", ""),
            float(cue.get("t", 0.0)),
            float(bind.get("gain", 1.0)) * (0.6 + 0.4 * intensity),
            float(bind.get("pitch", 1.0)),
            pan,
        )
    return stereo, used


def mix_into(stereo: np.ndarray, start_idx: int, sig: np.ndarray, pan: float = 0.0):
    """Mixes a mono or stereo signal into stereo buffer at `start_idx`."""
    if start_idx >= stereo.shape[0] or len(sig) == 0:
        return
    if start_idx < 0:
        sig = sig[-start_idx:]
        start_idx = 0
    end_idx = min(stereo.shape[0], start_idx + len(sig))
    n = end_idx - start_idx
    if n <= 0:
        return
    if sig.ndim == 2:
        stereo[start_idx:end_idx, 0] += sig[:n, 0]
        stereo[start_idx:end_idx, 1] += sig[:n, 1]
    else:
        panned = pan_stereo_haas(sig[:n], pan=pan)
        stereo[start_idx:end_idx] += panned


def _derive_topic_signature(cue_data: dict, base_seed: int = 77) -> dict:
    """
    Computes a deterministic musical variation signature from the video's scenes & cues so
    different topics within the same style have distinct key centers, chord progressions,
    melodic contours, and tempo breathing instead of identical background loops.
    """
    scenes = cue_data.get("scenes") or []
    cues = cue_data.get("cues") or []
    fingerprint = "|".join(
        [f"{s.get('id','')}:{s.get('title','')}:{s.get('look','')}:{s.get('dur',0)}" for s in scenes]
        + [f"{c.get('kind','')}:{c.get('label','')}" for c in cues[:16]]
    )
    h = zlib.crc32(fingerprint.encode("utf-8")) & 0xFFFFFFFF
    semitones = [-3, -2, 0, 2, 3, 4, 5][h % 7]
    pitch_mult = float(2.0 ** (semitones / 12.0))
    prog_orders = [
        [0, 1, 2, 3],
        [0, 3, 1, 2],
        [1, 3, 0, 2],
        [0, 2, 3, 1],
    ]
    arp_patterns = [
        [0, 2, 1, 3, 2, 4, 1, 2],
        [0, 1, 3, 2, 4, 3, 1, 2],
        [2, 0, 3, 1, 4, 2, 3, 0],
        [0, 3, 2, 4, 1, 3, 2, 0],
    ]
    tempo_scale = 0.94 + 0.03 * ((h >> 8) % 5)
    prog_order = prog_orders[(h >> 3) % len(prog_orders)]
    return {
        "hash": h,
        "seed": (int(base_seed) ^ int(h)) & 0xFFFFFFFF,
        "semitones": semitones,
        "pitch_mult": pitch_mult,
        "pitch_ratio": pitch_mult,
        "prog_order": prog_order,
        "chord_rot": prog_order[0],
        "arp_pattern": arp_patterns[(h >> 5) % len(arp_patterns)],
        "tempo_scale": tempo_scale,
    }


def _transpose_chords(chords: list, sig_or_ratio, chord_rot: int = 0) -> list:
    if isinstance(sig_or_ratio, dict):
        mult = float(sig_or_ratio.get("pitch_mult", sig_or_ratio.get("pitch_ratio", 1.0)))
        order = sig_or_ratio.get("prog_order", [i for i in range(len(chords))])
        return [[f * mult for f in chords[idx % len(chords)]] for idx in order]
    mult = float(sig_or_ratio)
    n = len(chords)
    return [[f * mult for f in chords[(i + int(chord_rot)) % n]] for i in range(n)]


def _build_foley_pocket_mask(n_samples: int, scenes: list, cues: list, duck_floor: float = 0.58) -> np.ndarray:
    """
    Builds a smooth dynamic envelope (0..1) for the score bed that:
      1. Honors explicit scene `silence` or tension moods;
      2. Ducks melodic accompaniment slightly (`duck_floor`) around prominent foley cues
         so physical actions (ratchets, footsteps, page turns, splashes) read clearly;
      3. Gives scenes a natural dramatic arc (gentle intro -> fuller middle -> warm resolution).
    """
    mask = np.ones(n_samples, dtype=np.float64)
    for idx, sc in enumerate(scenes or []):
        s0 = max(0, int(round(float(sc.get("start", 0.0)) * SR)))
        s1 = min(n_samples, int(round(float(sc.get("end", float(sc.get("start", 0.0)) + float(sc.get("dur", 3.5)))) * SR)))
        if s1 <= s0:
            continue
        mood = str(sc.get("mood") or sc.get("look") or "").lower()
        if any(w in mood for w in ("suspend", "tension", "dusk", "drought")):
            mask[s0:s1] *= 0.72
        elif idx == 0:
            mask[s0:s1] *= 0.85
        if sc.get("silence"):
            try:
                parts = [float(x) for x in str(sc.get("silence")).split(":")]
                if len(parts) >= 2:
                    q0 = max(s0, s0 + int(round(parts[0] * SR)))
                    q1 = min(s1, s0 + int(round(parts[1] * SR)))
                    if q1 > q0:
                        mask[q0:q1] = 0.08
            except Exception:
                pass

    for c in cues or []:
        t_c = float(c.get("t", -1.0))
        inten = float(c.get("intensity", 0.7))
        if t_c < 0 or inten < 0.55:
            continue
        c_idx = int(round(t_c * SR))
        w_pre = int(0.03 * SR)
        w_hold = int(0.22 * SR)
        i0 = max(0, c_idx - w_pre)
        i1 = min(n_samples, c_idx + w_hold)
        if i1 > i0:
            t_local = np.linspace(0.0, 1.0, i1 - i0)
            dip = 1.0 - (1.0 - duck_floor) * min(1.0, inten) * (np.sin(np.pi * t_local) ** 1.2)
            mask[i0:i1] = np.minimum(mask[i0:i1], dip)
    return mask


# =============================================================================
# 1. ACOUSTIC BODY & SPACE IMPULSE RESPONSE (IR) CONVOLUTION ENGINE
# =============================================================================

_IR_CACHE = {}


def build_body_ir(ir_kind: str) -> np.ndarray:
    """Builds a procedural physical-cavity + room early-reflection Impulse Response."""
    if ir_kind in _IR_CACHE:
        return _IR_CACHE[ir_kind]

    rng = np.random.default_rng(abs(hash(ir_kind)) % 100000)
    if ir_kind == "guqin_wood":
        # Hollowed aged Paulownia & Catalpa wood cavity (桐木梓木琴腔) + mountain canyon air tail
        # Balanced modes across 165Hz-1480Hz so open bass never muddies the 100-140Hz chest register
        n = int(0.85 * SR)
        t = np.arange(n, dtype=np.float64) / SR
        ir = np.zeros(n, dtype=np.float64)
        ir[0] = 0.62
        modes = [
            (168.0, 0.16, 0.065),
            (284.0, 0.28, 0.062),
            (436.0, 0.26, 0.052),
            (685.0, 0.22, 0.040),
            (1080.0, 0.15, 0.028),
            (1640.0, 0.08, 0.018),
        ]
        for freq, amp, tau in modes:
            ir += amp * np.sin(2.0 * np.pi * freq * t) * np.exp(-t / tau)
        # Early canyon reflections + warm silk tail
        for delay_ms, gain in [(21.0, 0.15), (46.0, -0.10), (92.0, 0.07), (158.0, 0.045)]:
            idx = int(delay_ms * 0.001 * SR)
            if idx < n:
                ir[idx] += gain
        tail = generate_pink_noise(n, rng) * np.exp(-t / 0.28) * 0.009
        sos = signal.butter(2, [220.0 / (0.5 * SR), 2200.0 / (0.5 * SR)], btype="band", output="sos")
        ir += signal.sosfilt(sos, tail)
    elif ir_kind == "vintage_horn":
        # 1930s acoustic brass / gramophone horn formant + studio slapback
        n = int(0.28 * SR)
        t = np.arange(n, dtype=np.float64) / SR
        ir = np.zeros(n, dtype=np.float64)
        ir[0] = 0.62
        for freq, amp, tau in [(510.0, 0.28, 0.018), (1180.0, 0.34, 0.014), (2150.0, 0.24, 0.011), (3100.0, 0.14, 0.008)]:
            ir += amp * np.sin(2.0 * np.pi * freq * t) * np.exp(-t / tau)
        for delay_ms, gain in [(14.0, -0.18), (38.0, 0.14), (72.0, 0.07)]:
            idx = int(delay_ms * 0.001 * SR)
            if idx < n:
                ir[idx] += gain
    elif ir_kind == "marimba_resonator":
        # Warm rosewood resonator tube + cozy tabletop reflection
        n = int(0.32 * SR)
        t = np.arange(n, dtype=np.float64) / SR
        ir = np.zeros(n, dtype=np.float64)
        ir[0] = 0.68
        for freq, amp, tau in [(262.0, 0.26, 0.042), (524.0, 0.18, 0.028), (1048.0, 0.09, 0.016)]:
            ir += amp * np.sin(2.0 * np.pi * freq * t) * np.exp(-t / tau)
        for delay_ms, gain in [(11.0, 0.14), (27.0, -0.09)]:
            idx = int(delay_ms * 0.001 * SR)
            if idx < n:
                ir[idx] += gain
    else:
        # `forest_canyon`: Dreamy twilight glade early reflections + lush shimmer tail
        n = int(0.95 * SR)
        t = np.arange(n, dtype=np.float64) / SR
        ir = np.zeros(n, dtype=np.float64)
        ir[0] = 0.60
        for delay_ms, gain in [(23.0, 0.18), (51.0, 0.14), (108.0, 0.10), (195.0, 0.07), (310.0, 0.045)]:
            idx = int(delay_ms * 0.001 * SR)
            if idx < n:
                ir[idx] += gain
        tail = rng.standard_normal(n) * np.exp(-t / 0.36) * 0.014
        sos = signal.butter(2, [240.0 / (0.5 * SR), 4200.0 / (0.5 * SR)], btype="band", output="sos")
        ir += signal.sosfilt(sos, tail)

    energy = np.sqrt(np.sum(ir ** 2) + 1e-12)
    ir = ir / max(energy, 1.0)
    _IR_CACHE[ir_kind] = ir
    return ir


def convolve_body_ir(sig: np.ndarray, ir_kind: str, wet: float = 0.45) -> np.ndarray:
    """Convolves a 1D or 2D audio signal with a physical body/space IR via `fftconvolve`."""
    ir = build_body_ir(ir_kind)
    if sig.ndim == 1:
        conv = signal.fftconvolve(sig, ir, mode="full")[: len(sig)]
        return (1.0 - wet) * sig + wet * conv
    out = np.zeros_like(sig)
    out[:, 0] = (1.0 - wet) * sig[:, 0] + wet * signal.fftconvolve(sig[:, 0], ir, mode="full")[: sig.shape[0]]
    # Slightly decorrelated right channel IR for natural stereo width
    ir_r = np.roll(ir, 11)
    out[:, 1] = (1.0 - wet) * sig[:, 1] + wet * signal.fftconvolve(sig[:, 1], ir_r, mode="full")[: sig.shape[0]]
    return out


# =============================================================================
# 2. MEDIUM-SPECIFIC PHYSICAL MODELING & SCORE ENGINES
# =============================================================================


def synth_guqin_note(
    freq: float,
    dur: float,
    mode: str,
    rng: np.random.Generator,
    slide_ratio: float = 1.125,
) -> np.ndarray:
    """
    Physical silk-string modal & waveguide synthesizer for Chinese seven-string Guqin (`古琴`):
      - `open` (`散音`): Deep silk-string pluck with rich 2nd-6th woody overtones & sympathetic string beating
      - `harmonic` (`泛音`): Jade-like 7th/9th-hui harmonic chime (`如珠落玉盘`, zero white-noise click)
      - `slide` (`走手音 / 吟猱`): Expressive pitch-gliding press note with warm silk fingerboard resonance
    """
    n = max(16, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR

    if mode == "harmonic":
        # 泛音: Round, jade-like flageolet node (octave 2*f0 + warm f0 body + fifth 3*f0), zero noise click
        f0 = min(freq * 2.0, 880.0)
        env = np.sin(0.5 * np.pi * np.clip(t / 0.008, 0.0, 1.0)) * (
            0.74 * np.exp(-t / (dur * 0.56)) + 0.26 * np.exp(-t / (dur * 0.92))
        )
        harm = (
            0.66 * np.sin(2.0 * np.pi * f0 * t)
            + 0.24 * np.sin(2.0 * np.pi * (f0 * 0.5) * t + 0.2) * np.exp(-t / (dur * 0.48))
            + 0.22 * np.sin(2.0 * np.pi * (f0 * 1.499) * t + 0.4) * np.exp(-t / (dur * 0.32))
            + 0.09 * np.sin(2.0 * np.pi * (f0 * 2.001) * t + 0.8) * np.exp(-t / (dur * 0.20))
        )
        # Soft flesh-and-nail touch transient (warm wooden modal ping, no high white noise)
        touch = np.sin(2.0 * np.pi * min(f0 * 2.5, 1320.0) * t) * np.exp(-t / 0.012) * 0.08
        return fade_in_out((harm * env + touch) * 0.36, 0.004, 0.03)

    if mode == "slide":
        # 走手音 + 吟猱: Smooth pitch glide from `freq` to `freq * slide_ratio` with 5.2 Hz Yin-Nao vibrato
        glide_curve = 0.5 - 0.5 * np.cos(np.pi * np.clip((t - 0.08) / max(0.18, dur * 0.42), 0.0, 1.0))
        yin_nao = 0.0072 * np.sin(2.0 * np.pi * 5.2 * t) * np.clip((t - 0.16) / 0.26, 0.0, 1.0)
        inst_freq = freq * (1.0 + (slide_ratio - 1.0) * glide_curve + yin_nao)
        phase = 2.0 * np.pi * np.cumsum(inst_freq) / SR

        out = np.zeros(n, dtype=np.float64)
        # Silk string harmonic weights: warm 2nd, 3rd, 4th partials give singing `走手音` body
        weights = [0.46, 0.54, 0.38, 0.24, 0.14, 0.08, 0.04]
        for k, w_k in enumerate(weights, 1):
            harm_decay = np.exp(-t / (dur * (0.72 / (k ** 0.58))))
            out += w_k * np.sin(k * phase + 0.18 * k) * harm_decay

        # Subtle warm silk fingerboard friction (260-1150 Hz pink noise, never harsh hiss)
        slide_win = np.exp(-((t - 0.22) / 0.14) ** 2)
        friction = generate_pink_noise(n, rng) * slide_win * 0.012
        sos_fr = signal.butter(2, [260.0 / (0.5 * SR), 1150.0 / (0.5 * SR)], btype="band", output="sos")
        out += signal.sosfilt(sos_fr, friction)
        attack = np.sin(0.5 * np.pi * np.clip(t / 0.008, 0.0, 1.0))
        return fade_in_out(out * attack * 0.42, 0.005, 0.03)

    # Default `open` (`散音`): Multi-harmonic silk-string modal synthesis with natural stiffness inharmonicity
    # and sympathetic string beating so 200-900 Hz woody overtones bloom alongside the deep fundamental
    stiffness_b = 0.00018
    # Balanced partial weights: moderate fundamental so <150Hz never booms, rich 2nd/3rd/4th woody harmonics
    f0_w = 0.42 if freq < 135.0 else 0.52
    harm_weights = [f0_w, 0.58, 0.44, 0.28, 0.17, 0.10, 0.055, 0.028]
    out = np.zeros(n, dtype=np.float64)
    for k, w_k in enumerate(harm_weights, 1):
        fk = freq * k * np.sqrt(1.0 + stiffness_b * (k ** 2))
        if fk >= 2200.0:
            break
        tau_k = dur * (0.76 / (k ** 0.62))
        env_k = np.exp(-t / max(0.06, tau_k))
        # Subtle sympathetic string / soundboard dual-mode beating on 2nd & 3rd partials (`余韵`)
        beat = 0.88 + 0.12 * np.cos(2.0 * np.pi * (0.34 * k) * t) if k in (2, 3) else 1.0
        out += w_k * np.sin(2.0 * np.pi * fk * t + 0.22 * k) * env_k * beat

    # Warm flesh-and-nail pluck transient (band-limited 220-1450 Hz)
    pluck_env = np.exp(-t / 0.016) * np.sin(0.5 * np.pi * np.clip(t / 0.003, 0.0, 1.0))
    pluck_body = np.sin(2.0 * np.pi * min(freq * 3.0, 920.0) * (1.0 + 0.18 * np.exp(-t / 0.008)) * t) * pluck_env * 0.14
    attack = np.sin(0.5 * np.pi * np.clip(t / 0.006, 0.0, 1.0))
    return fade_in_out((out * attack + pluck_body) * 0.40, 0.004, 0.035)


def synth_xiao_phrase(freq: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    """Synthesizes a warm, hollow Chinese vertical bamboo flute (`洞箫`) phrase with low-noise breath & vibrato."""
    n = max(16, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR
    attack = np.clip(t / 0.34, 0.0, 1.0)
    release = np.clip((dur - t) / 0.44, 0.0, 1.0)
    env = (np.sin(0.5 * np.pi * attack) ** 1.4) * np.sin(0.5 * np.pi * release)

    # Abdominal vibrato (`腹震音`) that blooms after 0.35s
    vib = 0.0048 * np.sin(2.0 * np.pi * 4.6 * t) * np.clip((t - 0.35) / 0.32, 0.0, 1.0)
    phase = 2.0 * np.pi * np.cumsum(freq * (1.0 + vib)) / SR

    # Hollow bamboo cylindrical bore: strong fundamental + woody odd-harmonic warmth (3rd) + soft 2nd
    pipe = (
        0.64 * np.sin(phase)
        + 0.22 * np.sin(2.0 * phase + 0.4)
        + 0.20 * np.sin(3.0 * phase + 1.1)
        + 0.06 * np.sin(4.0 * phase + 0.5)
        + 0.04 * np.sin(5.0 * phase + 1.6)
    )
    # Warm bamboo embouchure breath (360-1380 Hz pink noise, gentle onset chiff tapering to a quiet whisper)
    breath_env = 0.006 + 0.018 * np.exp(-t / 0.14)
    breath = generate_pink_noise(n, rng) * breath_env
    sos = signal.butter(2, [360.0 / (0.5 * SR), 1380.0 / (0.5 * SR)], btype="band", output="sos")
    breath_filt = signal.sosfilt(sos, breath)
    return fade_in_out((pipe + breath_filt) * env * 0.22, 0.02, 0.06)


def synth_taiko_impact(intensity: float, rng: np.random.Generator) -> np.ndarray:
    """
    Synthesizes a heavy Chinese Da-Tang-Gu / War Taiko drum slam (`重低音大堂鼓/太鼓轰击`):
      - Pitch-dropping sub-bass skin membrane fundamental (92Hz -> 44Hz)
      - Inharmonic circular membrane modes (1.59x, 2.14x) + wooden shell cavity resonance
      - Heavy leather mallet transient & rim crack
    """
    dur = 1.45
    n = int(round(dur * SR))
    t = np.arange(n, dtype=np.float64) / SR
    f_env = 44.0 + 52.0 * np.exp(-t / 0.045)
    phase = 2.0 * np.pi * np.cumsum(f_env) / SR

    sub_skin = np.sin(phase) * np.exp(-t / 0.38) * 0.62
    mode2 = np.sin(1.59 * phase + 0.3) * np.exp(-t / 0.19) * 0.28
    mode3 = np.sin(2.14 * phase + 0.8) * np.exp(-t / 0.11) * 0.15

    # Mallet impact transient & drumhead roar
    noise = rng.standard_normal(n)
    sos_thump = signal.butter(2, [65.0 / (0.5 * SR), 420.0 / (0.5 * SR)], btype="band", output="sos")
    sos_crack = signal.butter(2, [950.0 / (0.5 * SR), 3400.0 / (0.5 * SR)], btype="band", output="sos")
    thump = signal.sosfilt(sos_thump, noise) * np.exp(-t / 0.055) * 0.32
    crack = signal.sosfilt(sos_crack, noise) * np.exp(-t / 0.014) * 0.22

    attack = np.clip(t / 0.0025, 0.0, 1.0)
    sig = (sub_skin + mode2 + mode3 + thump + crack) * attack
    return np.tanh(sig * 1.45) * 0.72 * intensity


def synth_qin_strumming_slash(chord: list, dur: float, intensity: float, rng: np.random.Generator) -> np.ndarray:
    """
    Synthesizes a fierce martial Guqin/Pipa strumming roll (`古琴滚拂 / 琵琶杀伐扫弦摧音`):
    Rapid 7-string cascade with warm fingernail transient, silk-string fret buzz (`煞音`), and urgent tremolando.
    """
    n = int(round(dur * SR))
    out = np.zeros(n, dtype=np.float64)
    base_freqs = list(chord) + [chord[0] * 2.0, chord[1] * 2.0]

    # 1. Rapid initial 7-string sweep (`杀伐滚拂扫弦`, 16ms inter-string cascade)
    for s_idx, f_str in enumerate(base_freqs):
        s_off = int(round(s_idx * 0.016 * SR))
        if s_off >= n:
            break
        rem_dur = max(0.25, dur - s_idx * 0.016)
        note = synth_guqin_note(f_str, rem_dur, "open", rng)
        t_n = np.arange(len(note), dtype=np.float64) / SR
        # Warm Pipa/Guqin fingernail attack & silk string-fret buzz (`杀伐煞音`, band-limited 750-2400 Hz)
        nail = generate_pink_noise(len(note), rng) * np.exp(-t_n / 0.008) * 0.08
        sos_nail = signal.butter(2, [750.0 / (0.5 * SR), 2400.0 / (0.5 * SR)], btype="band", output="sos")
        buzz = np.tanh(note * 2.1) * 0.26 + signal.sosfilt(sos_nail, nail)
        end_i = min(n, s_off + len(note))
        out[s_off:end_i] += (note[: end_i - s_off] * 0.80 + buzz[: end_i - s_off]) * (0.85 + 0.05 * s_idx)

    # 2. Secondary urgent martial tremolando / reverse sweep (`拂弦余威`) at +0.36s and +0.74s
    for accent_t, gain in [(0.36, 0.68), (0.74, 0.52)]:
        if accent_t + 0.3 < dur:
            for s_idx, f_str in enumerate(reversed(base_freqs[:5])):
                s_off = int(round((accent_t + s_idx * 0.012) * SR))
                if s_off >= n:
                    break
                note = synth_guqin_note(f_str * 1.5, min(0.95, dur - accent_t), "slide", rng, slide_ratio=1.06)
                end_i = min(n, s_off + len(note))
                out[s_off:end_i] += note[: end_i - s_off] * gain

    return out * 0.58 * intensity


def _infer_ink_scene_mood(sc: dict, idx: int, total_scenes: int, cues: list) -> str:
    """Resolves the dramatic score mood (`serene | suspend | kill_burst | vast_aftermath`) for an ink scene."""
    explicit = str(sc.get("mood") or "").strip().lower()
    if explicit in ("serene", "suspend", "kill_burst", "vast_aftermath"):
        return explicit

    sc_id = f"{sc.get('id', '')} {sc.get('title', '')}".lower()
    start_t = float(sc.get("start", 0.0))
    end_t = float(sc.get("end", start_t + float(sc.get("dur", 4.0))))
    sc_cues = [
        f"{c.get('kind', '')}:{c.get('label', '')}".lower()
        for c in (cues or [])
        if start_t - 0.05 <= float(c.get("t", -1.0)) <= end_t + 0.05
    ]
    joined_cues = " ".join(sc_cues)

    if any(k in joined_cues for k in ("blade_cleave", "blood_splatter", "calligraphy_slam", "taiko_impact")) or any(
        k in sc_id for k in ("kill", "burst", "sha", "climax")
    ):
        return "kill_burst"
    if "blade_clique" in joined_cues or any(k in sc_id for k in ("suspend", "tense", "unsheathe", "heng", "kneel")):
        return "suspend"
    if "blade_sheathe" in joined_cues or any(k in sc_id for k in ("aftermath", "sheathe", "qianli", "gone")):
        return "vast_aftermath"
    return "serene"


def synth_ink_guqin_bed(
    dur: float,
    scenes: list,
    cfg: dict,
    rng: np.random.Generator,
    cues: list = None,
    sig: dict = None,
) -> np.ndarray:
    """
    Synthesizes a Scene-Dramatic Song-Yuan Guqin, Xiao Flute & Wuxia War-Drum Score (`Scene Dramatic Score Envelope`):
      - `serene` (`平缓疏朗`): Sparse Guqin open bass (`散音`), expressive sliding `走手吟猱`, and pine breeze breathing space.
      - `suspend` (`肃杀蓄力`): Tense press-slide decrescendo into a **0.45s–0.60s absolute breathless silence hold (`silence hold`)**.
      - `kill_burst` (`杀伐爆发`): **0.45s anticipation silence** followed by **Da-Tang-Gu war drum (`taiko_impact`) + fierce Guqin/Pipa strumming (`qin_strumming_slash`)**.
      - `vast_aftermath` (`收刀拉远 · 余韵`): Intimate quiet opening for sword sheathing -> deep open bass & cascading harmonics (`泛音`) dissolving into mountain wind.
    """
    n_samples = int(round(dur * SR))
    stereo = np.zeros((n_samples, 2), dtype=np.float64)
    climax_stereo = np.zeros((n_samples, 2), dtype=np.float64)
    silence_mask = np.ones(n_samples, dtype=np.float64)
    wind_mask = np.ones(n_samples, dtype=np.float64)

    if not scenes:
        scenes = [{"start": 0.0, "dur": dur, "end": dur}]

    sig = sig or {"pitch_ratio": 1.0, "chord_rot": 0}
    chords = _transpose_chords(cfg["chords"], sig["pitch_ratio"], sig["chord_rot"])
    for idx, sc in enumerate(scenes):
        start_t = float(sc.get("start", 0.0))
        sc_dur = float(sc.get("dur", max(1.0, dur - start_t)))
        end_t = min(dur, start_t + sc_dur)
        chord = chords[idx % len(chords)]
        mood = _infer_ink_scene_mood(sc, idx, len(scenes), cues or [])

        if mood == "suspend":
            # Find `blade_clique` cue inside scene if present, else place silence window in the final third
            clique_t = None
            for c in cues or []:
                ct = float(c.get("t", -1.0))
                ck = f"{c.get('kind', '')}:{c.get('label', '')}".lower()
                if start_t <= ct <= end_t and ("blade_clique" in ck or "unsheathe" in ck):
                    clique_t = ct - start_t
                    break
            sil_end_local = clique_t if clique_t is not None else min(sc_dur - 0.45, sc_dur * 0.72)
            sil_start_local = max(0.65, sil_end_local - 0.56)

            # Opening tense Guqin open fifth + low sliding press note before the silence hold
            n_open = synth_guqin_note(chord[0], min(sil_start_local + 0.15, 1.65), "open", rng) * 0.85
            mix_into(stereo, int(round(start_t * SR)), n_open, pan=-0.20)
            if sil_start_local > 0.75:
                n_slide = synth_guqin_note(chord[1], sil_start_local - 0.35, "slide", rng, slide_ratio=16.0 / 15.0) * 0.78
                mix_into(stereo, int(round((start_t + 0.38) * SR)), n_slide, pan=0.18)

            # Carve out the 0.55s breathless silence hold (`绝对屏息死寂`)
            s0 = max(0, int(round((start_t + sil_start_local) * SR)))
            s1 = min(n_samples, int(round((start_t + min(sc_dur, sil_end_local + 0.25)) * SR)))
            fade_len = min(int(0.12 * SR), max(1, (s1 - s0) // 4))
            if s1 > s0:
                silence_mask[s0:s1] = 0.0
                if s0 - fade_len >= 0:
                    silence_mask[s0 - fade_len : s0] = np.linspace(1.0, 0.0, fade_len)
                wind_mask[max(0, s0 - fade_len) : min(n_samples, int(round(end_t * SR)))] = 0.05

        elif mood == "kill_burst":
            # Find burst timestamp (default +0.45s anticipation stillness -> burst!)
            burst_local = 0.46
            for c in cues or []:
                ct = float(c.get("t", -1.0))
                ck = f"{c.get('kind', '')}:{c.get('label', '')}".lower()
                if start_t + 0.15 <= ct <= end_t and any(
                    w in ck for w in ("blade_cleave", "taiko_impact", "kill", "burst")
                ):
                    burst_local = clamp_val = max(0.35, min(1.1, ct - start_t))
                    break

            # 1. 0.45s Anticipation Silence Hold (`蓄力绝对静默`)
            s0 = max(0, int(round(start_t * SR)))
            s1 = min(n_samples, int(round((start_t + burst_local) * SR)))
            if s1 > s0:
                silence_mask[s0:s1] = 0.0
                wind_mask[s0:s1] = 0.0

            # 2. Explosive Burst: Heavy Taiko War Drum + Fierce Guqin/Pipa Strumming Slash!
            burst_idx = int(round((start_t + burst_local) * SR))
            taiko_main = synth_taiko_impact(1.0, rng)
            mix_into(climax_stereo, burst_idx, taiko_main, pan=0.0)

            rem_dur = max(1.2, sc_dur - burst_local)
            qin_slash = synth_qin_strumming_slash(chord, rem_dur, 0.96, rng)
            mix_into(climax_stereo, burst_idx, qin_slash, pan=-0.12)
            mix_into(climax_stereo, burst_idx + int(0.018 * SR), qin_slash * 0.82, pan=0.22)

            # Secondary war-drum punctuation hits syncing with calligraphy slam
            for sub_off, sub_int, sub_pan in [(0.42, 0.78, -0.18), (0.88, 0.85, 0.18)]:
                if burst_local + sub_off + 0.3 < sc_dur:
                    mix_into(
                        climax_stereo,
                        int(round((start_t + burst_local + sub_off) * SR)),
                        synth_taiko_impact(sub_int, rng),
                        pan=sub_pan,
                    )

        elif mood == "vast_aftermath":
            # Keep first ~1.15s quiet & intimate so close-up slow-motion `blade_sheathe` rings out clearly
            sheathe_window = min(1.15, sc_dur * 0.32)
            s0 = max(0, int(round(start_t * SR)))
            s1 = min(n_samples, int(round((start_t + sheathe_window * 0.85) * SR)))
            if s1 > s0:
                silence_mask[s0:s1] = 0.18

            # At `start_t + sheathe_window`, as camera pulls back (2.4x -> 1.0x), bloom deep Guqin open bass + cascading harmonics + lone Xiao flute
            reveal_t = start_t + sheathe_window
            rem = max(1.5, end_t - reveal_t)
            n_open = synth_guqin_note(chord[0], min(3.8, rem), "open", rng) * 0.95
            mix_into(stereo, int(round(reveal_t * SR)), n_open, pan=-0.18)

            if rem > 1.4:
                n_slide = synth_guqin_note(chord[2], min(3.0, rem - 0.3), "slide", rng, slide_ratio=9.0 / 8.0) * 0.85
                mix_into(stereo, int(round((reveal_t + 0.45) * SR)), n_slide, pan=0.16)

            for h_i, h_off in enumerate([0.25, 0.92, 1.65, 2.38, 3.10]):
                if sheathe_window + h_off + 0.3 < sc_dur:
                    h_freq = chord[(h_i + 1) % len(chord)]
                    n_harm = synth_guqin_note(h_freq, 1.95, "harmonic", rng) * (0.92 - 0.1 * h_i)
                    pan = -0.35 if (h_i % 2 == 0) else 0.35
                    mix_into(stereo, int(round((reveal_t + h_off) * SR)), n_harm, pan=pan)

            if rem > 1.6:
                xiao = synth_xiao_phrase(chord[3], min(3.2, rem - 0.4), rng) * 0.92
                mix_into(stereo, int(round((reveal_t + 0.55) * SR)), xiao, pan=0.24)

        else:
            # Default `serene`: Unhurried Song-Yuan mountain scroll (`古琴散音/走手吟猱 + 松风留白`)
            n_open = synth_guqin_note(chord[0], min(3.4, sc_dur * 0.95), "open", rng)
            mix_into(stereo, int(round(start_t * SR)), n_open, pan=-0.22)

            if sc_dur > 1.2:
                n_slide = synth_guqin_note(chord[2], min(2.8, sc_dur - 0.5), "slide", rng, slide_ratio=9.0 / 8.0)
                mix_into(stereo, int(round((start_t + 0.68) * SR)), n_slide, pan=0.18)

            # Sparse, unhurried harmonics (2 gentle notes instead of a mechanical 4-note metronome)
            for h_i, h_off in enumerate([1.55, 2.68]):
                if h_off + 0.35 < sc_dur:
                    h_freq = chord[(h_i + 2) % len(chord)]
                    n_harm = synth_guqin_note(h_freq, 1.75, "harmonic", rng) * 0.85
                    pan = -0.30 if (h_i % 2 == 0) else 0.30
                    mix_into(stereo, int(round((start_t + h_off) * SR)), n_harm, pan=pan)

            if sc_dur > 1.9:
                xiao_freq = chord[3] if idx % 2 == 0 else chord[4]
                xiao = synth_xiao_phrase(xiao_freq, min(2.5, sc_dur - 0.8), rng) * 0.85
                mix_into(stereo, int(round((start_t + 0.95) * SR)), xiao, pan=0.25 if idx % 2 == 0 else -0.25)

    # Convolve melodic Guqin/Xiao stems with Paulownia wood cavity IR, then enforce `silence_mask`
    stereo = convolve_body_ir(stereo, "guqin_wood", wet=0.46)
    stereo *= silence_mask[:, None]

    # Add climax war-drum & martial strumming with lighter canyon room reflection so transients stay razor-sharp
    if np.max(np.abs(climax_stereo)) > 1e-6:
        climax_stereo = convolve_body_ir(climax_stereo, "guqin_wood", wet=0.22)
        stereo += climax_stereo

    # Mountain pine wind & silk stream ambience (`松风呼吸`), gated by `wind_mask * silence_mask`
    t_all = np.arange(n_samples, dtype=np.float64) / SR
    breeze_mod = 0.55 + 0.45 * np.sin(2.0 * np.pi * 0.19 * t_all)
    wind = rng.standard_normal((n_samples, 2)) * 0.0032 * breeze_mod[:, None]
    sos_wind = signal.butter(2, [220.0 / (0.5 * SR), 1450.0 / (0.5 * SR)], btype="band", output="sos")
    stereo += signal.sosfilt(sos_wind, wind, axis=0) * (wind_mask * silence_mask)[:, None]
    return stereo


def synth_wah_brass_note(freq: float, dur: float, wah_open: float, rng: np.random.Generator, gliss: float = 0.0) -> np.ndarray:
    """
    Synthesizes a 1930s Fleischer-style Wah-Wah plunger-muted trumpet/trombone note:
    Nonlinear brass lip-reed waveshaper + dynamic formant bandpass swept by the plunger mute.
    """
    n = int(round(dur * SR))
    t = np.arange(n, dtype=np.float64) / SR
    # Optional trombone glissando + playful vibrato
    vib = 0.007 * np.sin(2.0 * np.pi * 6.2 * t) * np.clip((t - 0.08) / 0.12, 0.0, 1.0)
    glide = gliss * (1.0 - np.exp(-t / max(0.06, dur * 0.4)))
    inst_f = freq * (1.0 + glide + vib)
    phase = 2.0 * np.pi * np.cumsum(inst_f) / SR

    # Rich brass sawtooth/lip-reed excitation via tanh waveshaping
    raw = np.sin(phase) + 0.55 * np.sin(2.0 * phase + 0.2) + 0.35 * np.sin(3.0 * phase)
    brass = np.tanh(raw * 2.4)

    # Two-stage plunger-mute formant (closed "doo" ~520Hz + open "wah" ~1850Hz)
    sos_closed = signal.butter(2, [340.0 / (0.5 * SR), 820.0 / (0.5 * SR)], btype="band", output="sos")
    sos_open = signal.butter(2, [950.0 / (0.5 * SR), 2650.0 / (0.5 * SR)], btype="band", output="sos")
    closed_sig = signal.sosfilt(sos_closed, brass)
    open_sig = signal.sosfilt(sos_open, brass)

    # Plunger envelope sweeps from closed -> open -> closed ("dwaa-ooh")
    wah_env = np.clip(wah_open * np.sin(np.pi * np.clip(t / max(0.08, dur * 0.78), 0.0, 1.0)) ** 1.3, 0.0, 1.0)
    voiced = (1.0 - wah_env) * closed_sig + wah_env * open_sig * 1.35

    # Breath attack transient
    lip_buzz = rng.standard_normal(n) * np.exp(-t / 0.012) * 0.08
    amp_env = np.clip(t / 0.012, 0.0, 1.0) * np.exp(-t / (dur * 0.72)) * np.clip((dur - t) / 0.025, 0.0, 1.0)
    return (voiced + lip_buzz) * amp_env * 0.32


def synth_upright_bass_note(freq: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    """Synthesizes a woody pizzicato upright double-bass quarter note with fingerboard slap."""
    n = int(round(dur * SR))
    t = np.arange(n, dtype=np.float64) / SR
    env = np.clip(t / 0.006, 0.0, 1.0) * np.exp(-t / 0.24)
    body = (
        0.72 * np.sin(2.0 * np.pi * freq * t)
        + 0.42 * np.sin(4.0 * np.pi * freq * t + 0.3) * np.exp(-t / 0.14)
        + 0.18 * np.sin(6.0 * np.pi * freq * t) * np.exp(-t / 0.08)
    )
    # Woody finger slap at attack
    slap = rng.standard_normal(n) * np.exp(-t / 0.008) * 0.12
    sos = signal.butter(2, [650.0 / (0.5 * SR), 2200.0 / (0.5 * SR)], btype="band", output="sos")
    return body * env * 0.38 + signal.sosfilt(sos, slap)


def synth_jazz_swing_bed(
    dur: float,
    scenes: list,
    cfg: dict,
    rng: np.random.Generator,
    cues: list = None,
    sig: dict = None,
) -> np.ndarray:
    """
    Synthesizes a 1930s Fleischer / Broadway Swing band score with per-scene arrangement dynamics:
      - Topic-adaptive key transposition & tempo breathing
      - Walking Upright Bass + Wire-Brush Snare & Swung Ride/Hi-Hat groove
      - Scene-aware Wah-Wah Plunger-Muted Brass stabs, call-and-response & finale crescendo
      - Hybrid `vinyl_optical_grain` 1930s optical sound-on-film patina
    """
    sig = sig or _derive_topic_signature({"scenes": scenes, "cues": cues})
    n_samples = int(round(dur * SR))
    stereo = np.zeros((n_samples, 2), dtype=np.float64)
    bpm = float(cfg.get("bpm", 126.0)) * sig["tempo_scale"]
    beat_sec = 60.0 / bpm
    swing_off = beat_sec * 0.667

    p_mult = sig["pitch_mult"]
    bass_bars = [[f * p_mult for f in bar] for bar in cfg["bass_walk"]]
    chords = _transpose_chords(cfg["chords"], sig)
    total_beats = int(np.ceil(dur / beat_sec))

    sos_brush = signal.butter(2, [1400.0 / (0.5 * SR), 6800.0 / (0.5 * SR)], btype="band", output="sos")
    sos_hat = signal.butter(2, 5200.0 / (0.5 * SR), btype="high", output="sos")

    for b in range(total_beats):
        t_beat = b * beat_sec
        if t_beat >= dur:
            break
        bar_idx = (b // 4) % len(bass_bars)
        beat_in_bar = b % 4

        # Determine current scene index for arrangement density
        sc_idx = 0
        for idx_s, s_obj in enumerate(scenes or []):
            if float(s_obj.get("start", 0.0)) <= t_beat < float(s_obj.get("end", dur)):
                sc_idx = idx_s
                break

        # 1. Walking Upright Bass on every beat
        bass_f = bass_bars[bar_idx][beat_in_bar]
        bass_note = synth_upright_bass_note(bass_f, beat_sec * 0.92, rng)
        mix_into(stereo, int(round(t_beat * SR)), bass_note, pan=-0.16)

        # 2. Wire-Brush Snare & Hi-Hat Swing Groove
        n_tap = int(0.11 * SR)
        t_tap = np.arange(n_tap, dtype=np.float64) / SR
        brush_hit = signal.sosfilt(sos_brush, rng.standard_normal(n_tap)) * np.exp(-t_tap / 0.032) * 0.082
        if beat_in_bar in (1, 3):
            snare_body = np.sin(2.0 * np.pi * 185.0 * t_tap * np.exp(-t_tap * 6.0)) * np.exp(-t_tap / 0.038) * 0.13
            hat_chick = signal.sosfilt(sos_hat, rng.standard_normal(n_tap)) * np.exp(-t_tap / 0.018) * 0.072
            mix_into(stereo, int(round(t_beat * SR)), brush_hit * 1.3 + snare_body + hat_chick, pan=0.18)
        else:
            mix_into(stereo, int(round(t_beat * SR)), brush_hit, pan=0.15)

        if beat_in_bar in (1, 3) and (t_beat + swing_off) < dur:
            skip_hit = signal.sosfilt(sos_hat, rng.standard_normal(n_tap)) * np.exp(-t_tap / 0.024) * 0.075
            mix_into(stereo, int(round((t_beat + swing_off) * SR)), skip_hit, pan=0.22)

        # 3. Scene-aware Wah-Wah Plunger-Muted Brass Stabs & Call-and-Response
        chord = chords[bar_idx]
        horn_gain = 0.72 if sc_idx == 0 else (1.08 if sc_idx >= len(scenes or []) - 1 else 0.92)
        if beat_in_bar == 0 and (sc_idx > 0 or b >= 2):
            for v_i, f_v in enumerate(chord[1:4]):
                horn = synth_wah_brass_note(f_v * 2.0, beat_sec * 0.56, wah_open=0.85, rng=rng)
                mix_into(stereo, int(round(t_beat * SR)), horn * 0.38 * horn_gain, pan=-0.28 + 0.22 * v_i)
        elif beat_in_bar == 1 and (t_beat + swing_off) < dur:
            lead_f = chord[(2 + sc_idx) % len(chord)] * 2.0
            horn = synth_wah_brass_note(lead_f, beat_sec * 0.64, wah_open=0.95, rng=rng, gliss=0.07)
            mix_into(stereo, int(round((t_beat + swing_off) * SR)), horn * 0.50 * horn_gain, pan=0.26)
        elif beat_in_bar == 3:
            tb_f = chord[2] * 1.5
            gliss_dir = 0.13 if ((bar_idx + sc_idx) % 2 == 0) else -0.11
            tb = synth_wah_brass_note(tb_f, beat_sec * 0.76, wah_open=0.75, rng=rng, gliss=gliss_dir)
            mix_into(stereo, int(round(t_beat * SR)), tb * 0.44 * horn_gain, pan=-0.24)

    stereo = convolve_body_ir(stereo, "vintage_horn", wet=0.36)
    pocket = _build_foley_pocket_mask(n_samples, scenes, cues, duck_floor=0.64)
    stereo *= pocket[:, None]

    # Hybrid 1930s optical sound-on-film & 78rpm shellac grain layer
    vinyl_grain = slice_grain("vinyl_optical_grain", dur, pitch=1.0, rng=rng, random_offset=False) * 0.032
    stereo[:, 0] += vinyl_grain
    stereo[:, 1] += np.roll(vinyl_grain, 19) * 0.92
    return stereo


def synth_marimba_note(freq: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    """Euler-Bernoulli modal synthesis for a rosewood Marimba bar + hybrid woodblock transient."""
    n = int(round(dur * SR))
    t = np.arange(n, dtype=np.float64) / SR
    strike = rng.standard_normal(n) * np.exp(-t / 0.0035) * 0.08
    sos = signal.butter(2, [400.0 / (0.5 * SR), 3200.0 / (0.5 * SR)], btype="band", output="sos")
    strike = signal.sosfilt(sos, strike)

    modes = (
        0.74 * np.sin(2.0 * np.pi * freq * t) * np.exp(-t / 0.26)
        + 0.22 * np.sin(2.0 * np.pi * (freq * 3.98) * t + 0.4) * np.exp(-t / 0.055)
        + 0.06 * np.sin(2.0 * np.pi * (freq * 9.18) * t + 1.1) * np.exp(-t / 0.018)
    )
    return (modes * np.clip(t / 0.002, 0.0, 1.0) + strike) * 0.34


def synth_clay_marimba_bed(
    dur: float,
    scenes: list,
    cfg: dict,
    rng: np.random.Generator,
    cues: list = None,
    sig: dict = None,
) -> np.ndarray:
    """
    Synthesizes a scene-dramatic Rosewood Marimba & Kalimba score (`clay-macaron`):
      - Topic-adaptive key center, chord progression & arpeggio contour
      - Alternates warm rosewood marimba with crystalline Kalimba tines on golden/dusk scenes
      - Ducks under physical clay squish, pour & unboxing foley cues
    """
    sig = sig or _derive_topic_signature({"scenes": scenes, "cues": cues})
    n_samples = int(round(dur * SR))
    stereo = np.zeros((n_samples, 2), dtype=np.float64)
    step_sec = (60.0 / (110.0 * sig["tempo_scale"])) / 2.0
    chords = _transpose_chords(cfg["chords"], sig)
    arp_pattern = sig["arp_pattern"]
    total_steps = int(np.ceil(dur / step_sec))

    for s in range(total_steps):
        t_s = s * step_sec
        if t_s >= dur:
            break
        # Find active scene mood/look
        sc_look = "day"
        sc_idx = 0
        for idx_s, sc in enumerate(scenes or []):
            if float(sc.get("start", 0.0)) <= t_s < float(sc.get("end", dur)):
                sc_look = str(sc.get("look") or sc.get("mood") or "day").lower()
                sc_idx = idx_s
                break

        # Leave a brief musical breath right at scene transitions
        if any(abs(t_s - float(sc.get("start", -9.0))) < 0.14 for sc in (scenes or [])[1:]):
            continue

        bar_idx = (s // 8 + sc_idx) % len(chords)
        chord = chords[bar_idx]
        deg = arp_pattern[(s + sc_idx) % len(arp_pattern)] % len(chord)
        freq = chord[deg]

        if sc_look in ("dusk", "night", "indoor") and (s % 2 == 1):
            # Delicate Kalimba thumb-piano tine overtone
            note = modal_strike(freq * 2.0, 0.38, material="bell", rng=rng) * 0.16
        else:
            note = synth_marimba_note(freq, 0.42, rng) * (0.85 if sc_idx == 0 else 1.0)

        pan = -0.28 + 0.14 * ((s + sc_idx) % 5)
        mix_into(stereo, int(round(t_s * SR)), note, pan=pan)

        if s % 4 == 0:
            bass = synth_marimba_note(chord[0] * 0.5, 0.58, rng) * 0.80
            mix_into(stereo, int(round(t_s * SR)), bass, pan=0.0)

    stereo = convolve_body_ir(stereo, "marimba_resonator", wet=0.38)
    pocket = _build_foley_pocket_mask(n_samples, scenes, cues, duck_floor=0.58)
    return stereo * pocket[:, None]


def synth_paper_harp_bed(
    dur: float,
    scenes: list,
    cfg: dict,
    rng: np.random.Generator,
    cues: list = None,
    sig: dict = None,
) -> np.ndarray:
    """
    Synthesizes an acoustic plucked harp & music-box harmonic score for `paper-popup`:
      - Pauses melodic plucks during 180° book page turns so cardstock folding & pop-up snaps shine
      - Shifts register & harmonic density from `day` -> `golden` -> `dusk` -> `night`
    """
    sig = sig or _derive_topic_signature({"scenes": scenes, "cues": cues})
    n_samples = int(round(dur * SR))
    stereo = np.zeros((n_samples, 2), dtype=np.float64)
    step_sec = 0.36 / sig["tempo_scale"]
    chords = _transpose_chords(cfg["chords"], sig)
    arp_pattern = sig["arp_pattern"]
    total_steps = int(np.ceil(dur / step_sec))

    for s in range(total_steps):
        t_s = s * step_sec
        if t_s >= dur:
            break
        # Leave a 0.42s breathing window at scene page-turn boundaries
        if any(abs(t_s - float(sc.get("start", -9.0))) < 0.26 for sc in (scenes or [])[1:]):
            continue

        sc_idx = 0
        sc_look = "day"
        for idx_s, sc in enumerate(scenes or []):
            if float(sc.get("start", 0.0)) <= t_s < float(sc.get("end", dur)):
                sc_idx = idx_s
                sc_look = str(sc.get("look") or "day").lower()
                break

        chord = chords[sc_idx % len(chords)]
        deg = arp_pattern[(s + sc_idx) % len(arp_pattern)] % len(chord)
        freq = chord[deg]
        mode = "harmonic" if (sc_look in ("night", "starlight") and s % 3 == 0) else "open"
        pluck = synth_guqin_note(freq, 0.92, mode, rng) * 0.62
        pan = -0.32 if (s % 2 == 0) else 0.32
        mix_into(stereo, int(round(t_s * SR)), pluck, pan=pan)

    stereo = convolve_body_ir(stereo, "marimba_resonator", wet=0.35)
    pocket = _build_foley_pocket_mask(n_samples, scenes, cues, duck_floor=0.52)
    return stereo * pocket[:, None]


def _synth_felt_piano_voice(freq: float, dur: float, rng: np.random.Generator, vel: float = 0.85) -> np.ndarray:
    """Warm, velvety nocturnal felt-piano note (pure harmonic overtones, soft 18ms attack, zero noise click)."""
    n = max(16, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR
    attack = np.sin(0.5 * np.pi * np.clip(t / 0.018, 0.0, 1.0))
    decay = 0.72 * np.exp(-t / (dur * 0.55)) + 0.28 * np.exp(-t / (dur * 1.15))
    env = attack * decay
    sig = (
        0.76 * np.sin(2.0 * np.pi * freq * t)
        + 0.19 * np.sin(2.0 * np.pi * (freq * 2.0) * t + 0.2) * np.exp(-t / 0.38)
        + 0.05 * np.sin(2.0 * np.pi * (freq * 3.0) * t + 0.5) * np.exp(-t / 0.18)
    )
    sos_lp = signal.butter(2, min(1600.0, freq * 3.6) / (0.5 * SR), btype="low", output="sos")
    out = signal.sosfilt(sos_lp, sig * env) * 0.20 * vel
    return fade_in_out(out, 0.008, 0.04)


def _synth_celesta_bell(freq: float, dur: float, vel: float = 0.85) -> np.ndarray:
    """Warm, round music-box / soft celesta tone (zero metallic inharmonic partials, soft 14ms attack)."""
    n = max(16, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR
    attack = np.sin(0.5 * np.pi * np.clip(t / 0.014, 0.0, 1.0))
    env = attack * (0.75 * np.exp(-t / 0.58) + 0.25 * np.exp(-t / 1.25))
    tine = (
        0.82 * np.sin(2.0 * np.pi * freq * t)
        + 0.15 * np.sin(2.0 * np.pi * (freq * 2.0) * t + 0.15) * np.exp(-t / 0.26)
        + 0.03 * np.sin(2.0 * np.pi * (freq * 3.0) * t + 0.4) * np.exp(-t / 0.12)
    )
    sos_lp = signal.butter(2, 1850.0 / (0.5 * SR), btype="low", output="sos")
    return fade_in_out(signal.sosfilt(sos_lp, tine * env) * 0.15 * vel, 0.006, 0.04)


def synth_twilight_celesta_bed(
    dur: float,
    scenes: list,
    cfg: dict,
    rng: np.random.Generator,
    cues: list = None,
    sig: dict = None,
) -> np.ndarray:
    """
    Synthesizes a warm, soothing, Studio-Ghibli style nocturnal lake score (`twilight-fable`):
      - All instruments stay strictly in the warm middle register (65 Hz - 988 Hz), with zero metallic/high-frequency harshness.
      - Soft Felt-Piano Arpeggios + Warm Bowed Cello (`arco` & `pizz`) + Round Music-Box Celesta Melody.
    """
    sig = sig or _derive_topic_signature({"scenes": scenes, "cues": cues})
    n_samples = int(round(dur * SR))
    chords = cfg["chords"]
    stereo = synth_ambient_bed(dur, scenes, cfg, rng) * 0.82

    if not scenes:
        scenes = [{"start": 0.0, "dur": dur, "end": dur, "look": "twilight"}]

    # 1. Warm Cello Foundation (low-passed arco & soft wooden pizzicato)
    for idx, sc in enumerate(scenes):
        start_t = float(sc.get("start", 0.0))
        sc_dur = float(sc.get("dur", max(1.0, dur - start_t)))
        chord = chords[idx % len(chords)]

        if idx == 0:
            for b_i in range(int(sc_dur / 1.5)):
                bt = start_t + 0.2 + b_i * 1.5
                if bt < dur - 0.35:
                    f_b = chord[0] * 0.5 if (b_i % 2 == 0) else chord[2] * 0.5
                    pizz = synth_cello_voice(f_b, 0.95, "pizz", rng) * 0.58
                    mix_into(stereo, int(round(bt * SR)), pizz, pan=-0.18)
        elif idx == 1:
            c1 = synth_cello_voice(chord[0] * 0.5, min(sc_dur * 0.52, 2.5), "arco", rng) * 0.62
            c2 = synth_cello_voice(chord[2] * 0.5, min(sc_dur * 0.52, 2.5), "arco", rng) * 0.58
            mix_into(stereo, int(round((start_t + 0.12) * SR)), c1, pan=-0.20)
            mix_into(stereo, int(round((start_t + sc_dur * 0.46) * SR)), c2, pan=-0.15)
        elif idx == 2:
            for b_i in range(int(sc_dur / 1.15)):
                bt = start_t + 0.12 + b_i * 1.15
                if bt < dur - 0.35:
                    f_b = chord[b_i % 2] * 0.5
                    pizz = synth_cello_voice(f_b, 0.80, "pizz", rng) * 0.55
                    mix_into(stereo, int(round(bt * SR)), pizz, pan=-0.18)
            leap_arco = synth_cello_voice(chord[2] * 0.5, min(2.3, sc_dur * 0.52), "arco", rng) * 0.58
            mix_into(stereo, int(round((start_t + sc_dur * 0.40) * SR)), leap_arco, pan=0.16)
        else:
            c1 = synth_cello_voice(chord[0] * 0.5, min(sc_dur * 0.52, 2.4), "arco", rng) * 0.52
            c2 = synth_cello_voice(chord[2] * 0.5, min(sc_dur * 0.52, 2.4), "arco", rng) * 0.48
            mix_into(stereo, int(round((start_t + 0.12) * SR)), c1, pan=-0.18)
            mix_into(stereo, int(round((start_t + sc_dur * 0.46) * SR)), c2, pan=0.16)

    # 2. Unhurried, Breathing Felt-Piano Arpeggios & Warm Middle-Register Celesta Melody
    step_sec = 0.44
    arp_cycle = [0, 2, 3, 4, 2, 1, 3, 2]
    melody_degrees = [2, 3, 4, 2, 1, 2, 3, 1, 4, 3, 2, 0, 1, 2, 3, 4]
    total_steps = int(np.ceil(dur / step_sec))

    for s in range(total_steps):
        t_s = s * step_sec
        if t_s >= dur - 1.6:
            break
        sc_idx = 0
        for idx_s, sc in enumerate(scenes):
            if float(sc.get("start", 0.0)) <= t_s < float(sc.get("end", dur)):
                sc_idx = idx_s
                break

        if sc_idx == 0 and (s % 4 == 3):
            continue

        chord = chords[sc_idx % len(chords)]
        arp_deg = arp_cycle[s % len(arp_cycle)] % len(chord)
        # Keep piano strictly in warm middle register (196 Hz - 587 Hz)
        f_arp = chord[arp_deg] * (0.5 if arp_deg >= 3 and (s % 2 == 0) else 1.0)

        vel_arp = 0.62 if sc_idx == 0 else (0.76 if sc_idx in (1, 2) else 0.72)
        piano_note = _synth_felt_piano_voice(f_arp, 1.15, rng, vel=vel_arp)
        pan_arp = np.sin(s * 0.6 + sc_idx) * 0.28
        mix_into(stereo, int(round(t_s * SR)), piano_note, pan=pan_arp)

        # Lyrical Celesta melody strictly capped below 988 Hz (B5)
        play_melody = (s % 2 == 0) if sc_idx in (1, 2, 3) else (s % 3 == 0)
        if play_melody:
            m_deg = melody_degrees[(s // 2 + sc_idx * 2) % len(melody_degrees)] % len(chord)
            f_mel = chord[m_deg] * (1.0 if chord[m_deg] > 420.0 else 2.0)
            f_mel = min(f_mel, 987.77)
            vel_mel = 0.68 if sc_idx == 0 else (0.82 if sc_idx in (1, 3) else 0.78)
            cel = _synth_celesta_bell(f_mel, 1.25, vel=vel_mel)
            mix_into(stereo, int(round((t_s + 0.015) * SR)), cel, pan=-pan_arp * 0.8)

    # Gentle 3-note final resolution arpeggio after regular steps finish (no stacking)
    if dur > 2.2:
        final_t = max(0.0, dur - 1.55)
        final_chord = chords[(len(scenes) - 1) % len(chords)]
        for v_i, nf in enumerate(final_chord[:3]):
            p_note = _synth_felt_piano_voice(nf, 1.45, rng, vel=0.52)
            idx_sample = int(round((final_t + v_i * 0.22) * SR))
            mix_into(stereo, idx_sample, p_note, pan=-0.18 + 0.18 * v_i)

    # Silky, noise-free stereo hall shimmer (decorrelated smooth early reflections, zero comb harshness)
    reverb_l = np.zeros(n_samples, dtype=np.float64)
    reverb_r = np.zeros(n_samples, dtype=np.float64)
    for delay_ms, gain_l, gain_r in [(31.0, 0.14, 0.11), (53.0, 0.10, 0.13), (89.0, 0.08, 0.07), (142.0, 0.05, 0.06), (218.0, 0.035, 0.035)]:
        d = int(delay_ms * 0.001 * SR)
        if d < n_samples:
            reverb_l[d:] += stereo[:-d, 1] * gain_l
            reverb_r[d:] += stereo[:-d, 0] * gain_r
    sos_rev = signal.butter(2, 1400.0 / (0.5 * SR), btype="low", output="sos")
    stereo[:, 0] = stereo[:, 0] * 0.84 + signal.sosfilt(sos_rev, reverb_l)
    stereo[:, 1] = stereo[:, 1] * 0.84 + signal.sosfilt(sos_rev, reverb_r)
    return stereo


def synth_cello_voice(freq: float, dur: float, mode: str, rng: np.random.Generator) -> np.ndarray:
    """Synthesizes a warm 19th-century chamber Cello note (`arco` bowed sustain or `pizz` wooden pluck)."""
    n = max(16, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR
    if mode == "pizz":
        return synth_upright_bass_note(freq, dur, rng) * 0.88
    # Bowed `arco` with warm wooden body formants (no harsh high-frequency rosin hiss)
    attack = np.clip(t / min(0.28, dur * 0.25), 0.0, 1.0)
    release = np.clip((dur - t) / min(0.35, dur * 0.3), 0.0, 1.0)
    env = (np.sin(0.5 * np.pi * attack) ** 1.3) * np.sin(0.5 * np.pi * release)
    vib = 0.0042 * np.sin(2.0 * np.pi * 5.1 * t) * np.clip((t - 0.22) / 0.25, 0.0, 1.0)
    phase = 2.0 * np.pi * np.cumsum(freq * (1.0 + vib)) / SR
    out = np.zeros(n, dtype=np.float64)
    for k in range(1, 8):
        out += (0.52 / (k ** 1.18)) * np.sin(k * phase + 0.2 * k)
    sos_body = signal.butter(2, [95.0 / (0.5 * SR), 1050.0 / (0.5 * SR)], btype="band", output="sos")
    return signal.sosfilt(sos_body, out * env) * 0.30


def synth_fortepiano_note(freq: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    """Synthesizes a period 19th-century wooden-frame Fortepiano / Harpsichord plucked-hammer note."""
    n = max(16, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float64) / SR
    env = np.clip(t / 0.003, 0.0, 1.0) * (0.72 * np.exp(-t / (dur * 0.42)) + 0.28 * np.exp(-t / (dur * 0.85)))
    tone = (
        0.66 * np.sin(2.0 * np.pi * freq * t)
        + 0.32 * np.sin(2.0 * np.pi * (freq * 2.001) * t + 0.3) * np.exp(-t / 0.28)
        + 0.16 * np.sin(2.0 * np.pi * (freq * 3.004) * t + 0.7) * np.exp(-t / 0.16)
        + 0.07 * np.sin(2.0 * np.pi * (freq * 4.01) * t) * np.exp(-t / 0.09)
    )
    hammer = modal_strike(freq * 2.0, min(0.08, dur), material="wood", rng=rng) * 0.18
    out = tone * env * 0.28
    out[: len(hammer)] += hammer
    return out


def synth_naturalist_chamber_bed(
    dur: float,
    scenes: list,
    cfg: dict,
    rng: np.random.Generator,
    cues: list = None,
    sig: dict = None,
) -> np.ndarray:
    """
    Synthesizes a 19th-Century Naturalist Chamber Score (`vintage-naturalist`):
      - Instrumentation: Warm Cello (`arco` & `pizzicato`) + Period Fortepiano + Glass Armonica
      - 4-Stage Scientific Narrative Envelope:
          1. `plate / curiosity`: Sparse cello pizzicato + delicate fortepiano intervals, leaving
             clear space for copperplate quill etching & specimen pin foley.
          2. `amber / comparison`: Structured Baroque counterpoint across comparative specimens.
          3. `dusk / selection_tension`: Low cello tension sustain + carved foley window so the
             brass dial ratchet & balance scale tilt take acoustic center stage.
          4. `starlight / revelation`: Warm Picardy-third major chord bloom + Glass Armonica shimmer.
    """
    sig = sig or _derive_topic_signature({"scenes": scenes, "cues": cues})
    n_samples = int(round(dur * SR))
    stereo = np.zeros((n_samples, 2), dtype=np.float64)
    if not scenes:
        scenes = [{"start": 0.0, "dur": dur, "end": dur, "look": "plate"}]

    chords = _transpose_chords(cfg["chords"], sig)
    arp_pattern = sig["arp_pattern"]

    for idx, sc in enumerate(scenes):
        start_t = float(sc.get("start", 0.0))
        sc_dur = float(sc.get("dur", max(1.0, dur - start_t)))
        look = str(sc.get("look") or sc.get("mood") or "").lower()
        chord = chords[idx % len(chords)]

        if "dusk" in look or "selection" in str(sc.get("id", "")).lower() or idx == 2:
            # Stage 3 `selection_tension`: Low bowed cello root + fifth tension drone, sparse piano
            cello_low = synth_cello_voice(chord[0] * 0.5, min(sc_dur * 0.92, 3.6), "arco", rng) * 0.85
            mix_into(stereo, int(round(start_t * SR)), cello_low, pan=-0.22)
            # Single tense fortepiano dyad at start and at verdict
            for p_off, deg in [(0.18, 1), (min(sc_dur - 0.65, 2.85), 3)]:
                if p_off > 0 and p_off < sc_dur - 0.2:
                    fp = synth_fortepiano_note(chord[deg % len(chord)], 0.85, rng) * 0.72
                    mix_into(stereo, int(round((start_t + p_off) * SR)), fp, pan=0.20)
        elif "starlight" in look or "tree" in str(sc.get("id", "")).lower() or idx == len(scenes) - 1:
            # Stage 4 `revelation`: Warm bowed cello + ascending fortepiano arpeggio + Glass Armonica bloom
            cello_warm = synth_cello_voice(chord[0] * 0.5, min(sc_dur * 0.96, 3.8), "arco", rng) * 0.92
            mix_into(stereo, int(round(start_t * SR)), cello_warm, pan=-0.18)
            step = 0.42 / sig["tempo_scale"]
            n_steps = int((sc_dur - 0.25) / step)
            for s_i in range(n_steps):
                deg = arp_pattern[s_i % len(arp_pattern)] % len(chord)
                fp = synth_fortepiano_note(chord[deg], 0.95, rng) * 0.78
                mix_into(stereo, int(round((start_t + 0.15 + s_i * step) * SR)), fp, pan=-0.25 + 0.16 * (s_i % 4))
            shimmer = slice_grain("crystal_shimmer_grain", min(sc_dur * 0.8, 2.4), pitch=sig["pitch_mult"], rng=rng) * 0.16
            mix_into(stereo, int(round((start_t + 0.45) * SR)), shimmer, pan=0.15)
        else:
            # Stage 1 & 2 (`curiosity` / `comparison`): Pizzicato cello bass + measured Baroque keyboard
            pizz_step = 0.92 / sig["tempo_scale"]
            n_pizz = max(1, int((sc_dur - 0.2) / pizz_step))
            for p_i in range(n_pizz):
                f_b = chord[0] * 0.5 if (p_i % 2 == 0) else chord[1] * 0.5
                pizz = synth_cello_voice(f_b, 0.65, "pizz", rng) * 0.76
                mix_into(stereo, int(round((start_t + 0.12 + p_i * pizz_step) * SR)), pizz, pan=-0.20)

            fp_step = 0.46 / sig["tempo_scale"]
            n_fp = int((sc_dur - 0.25) / fp_step)
            for f_i in range(n_fp):
                if idx == 0 and (f_i % 3 == 1):
                    continue  # Extra breathing space on opening specimen plate
                deg = arp_pattern[(f_i + idx) % len(arp_pattern)] % len(chord)
                fp = synth_fortepiano_note(chord[deg], 0.72, rng) * 0.72
                mix_into(stereo, int(round((start_t + 0.18 + f_i * fp_step) * SR)), fp, pan=0.22 if f_i % 2 == 0 else -0.18)

    stereo = convolve_body_ir(stereo, "marimba_resonator", wet=0.34)
    pocket = _build_foley_pocket_mask(n_samples, scenes, cues, duck_floor=0.48)
    return stereo * pocket[:, None]


def synth_industrial_mech_bed(
    dur: float,
    scenes: list,
    cfg: dict,
    rng: np.random.Generator,
    cues: list = None,
    sig: dict = None,
) -> np.ndarray:
    """
    Pure Diegetic Mechanical & Hydraulic Acoustic Bed (`mech` / `industrial-mech` / `calibration-lab`):
      - ZERO musical chords, ZERO synth pads, ZERO high-frequency chimes/beeps.
      - Layer 1: Deep-sea / laboratory hydraulic pump & fluid flow bed (38-135 Hz low-passed pink/brown noise
        + damped 52 Hz turbine fundamental with gentle kinematic breathing).
      - Layer 2: Cyclic mechanical power-stroke / propulsion thud cadence (soft 56-74 Hz damped sub-thumps
        paired with low-mid pneumatic valve breaths, inspired by teardown's score_kit.thud & airy).
      - Layer 3: Per-scene servo/actuator gimbal glide on camera & subsystem transitions.
    """
    sig = sig or _derive_topic_signature({"scenes": scenes, "cues": cues})
    n_samples = int(round(dur * SR))
    stereo = np.zeros((n_samples, 2), dtype=np.float64)
    if not scenes:
        scenes = [{"start": 0.0, "dur": dur, "end": dur}]

    t_full = np.arange(n_samples, dtype=np.float64) / SR

    # 1. Continuous deep hydraulic & fluid flow bed (warm 38-135 Hz low-passed pink noise + 52 Hz pump hum)
    pink_l = generate_pink_noise(n_samples, rng)
    pink_r = generate_pink_noise(n_samples, rng)
    fc_flow = 88.0 + 28.0 * np.sin(2.0 * np.pi * 0.42 * t_full) + 14.0 * np.sin(2.0 * np.pi * 1.15 * t_full)
    flow_l = time_varying_bandpass(pink_l, fc_flow, btype="low") * 0.085
    flow_r = time_varying_bandpass(pink_r, fc_flow * 1.04, btype="low") * 0.085

    # Subtle 52 Hz hydraulic pump fundamental + 104 Hz second harmonic (heavily damped, warm)
    f_pump = 52.0 * (1.0 + 0.018 * np.sin(2.0 * np.pi * 0.35 * t_full))
    ph_pump = 2.0 * np.pi * np.cumsum(f_pump) / SR
    pump_mod = 0.78 + 0.22 * np.sin(2.0 * np.pi * 1.35 * t_full)
    pump_hum = (np.sin(ph_pump) + 0.28 * np.sin(2.0 * ph_pump)) * pump_mod * 0.042

    stereo[:, 0] += flow_l + pump_hum * 0.96
    stereo[:, 1] += flow_r + pump_hum * 1.04

    # 2. Cyclic mechanical power-stroke thuds & soft valve air across scenes
    for idx, sc in enumerate(scenes):
        start_t = float(sc.get("start", 0.0))
        sc_dur = float(sc.get("dur", max(1.0, dur - start_t)))
        stroke_period = 0.74 if idx in (1, 2) else 0.84
        t_cursor = start_t + 0.22
        stroke_i = 0
        while t_cursor < min(dur - 0.25, start_t + sc_dur - 0.15):
            thud_dur = 0.32
            n_th = int(round(thud_dur * SR))
            t_th = np.arange(n_th, dtype=np.float64) / SR
            f_th = (64.0 if (stroke_i % 2 == 0) else 56.0) + 28.0 * np.exp(-t_th / 0.028)
            ph_th = 2.0 * np.pi * np.cumsum(f_th) / SR
            att_th = np.clip(t_th / 0.005, 0.0, 1.0)
            thud_sig = np.sin(ph_th) * np.exp(-t_th / 0.085) * att_th * 0.068

            air_noise = generate_pink_noise(n_th, rng)
            air_fc = 190.0 + 140.0 * np.sin(np.pi * t_th / thud_dur)
            air_sig = time_varying_bandpass(air_noise, air_fc, q=1.4, btype="bandpass") * np.sin(np.pi * t_th / thud_dur) * 0.028

            pan_pos = -0.16 if (stroke_i % 2 == 0) else 0.16
            mix_into(stereo, int(round(t_cursor * SR)), thud_sig + air_sig, pan=pan_pos)
            t_cursor += stroke_period
            stroke_i += 1

        # 3. Scene-opening gimbal servo & pneumatic actuator transit
        servo_dur = min(1.15, sc_dur * 0.35)
        if servo_dur > 0.25:
            n_sv = int(round(servo_dur * SR))
            t_sv = np.arange(n_sv, dtype=np.float64) / SR
            env_sv = np.sin(np.pi * t_sv / servo_dur) ** 1.15
            f_rot = 135.0 + 42.0 * np.sin(np.pi * t_sv / servo_dur)
            ph_rot = 2.0 * np.pi * np.cumsum(f_rot) / SR
            rotor = (np.sin(ph_rot) + 0.32 * np.sin(2.0 * ph_rot)) * env_sv * 0.024
            sv_air = time_varying_bandpass(
                generate_pink_noise(n_sv, rng),
                240.0 + 220.0 * np.sin(np.pi * t_sv / servo_dur),
                q=1.2,
                btype="bandpass",
            ) * env_sv * 0.036
            mix_into(stereo, int(round((start_t + 0.06) * SR)), rotor + sv_air, pan=0.12 if idx % 2 == 0 else -0.12)

    pocket = _build_foley_pocket_mask(n_samples, scenes, cues, duck_floor=0.68)
    return fade_in_out(stereo * pocket[:, None], 0.18, 0.35)


def synth_ambient_bed(dur: float, scenes: list, cfg: dict, rng: np.random.Generator) -> np.ndarray:
    """Synthesizes a warm evolving stereo harmonic pad across scenes (for glass/cyber/terminal)."""
    n_samples = int(round(dur * SR))
    stereo = np.zeros((n_samples, 2), dtype=np.float64)

    if not scenes:
        scenes = [{"start": 0.0, "dur": dur, "end": dur}]

    chords = cfg["chords"]
    for idx, sc in enumerate(scenes):
        start_t = float(sc.get("start", 0.0))
        sc_dur = float(sc.get("dur", max(1.0, dur - start_t)))
        pad_len = min(dur - start_t, sc_dur + 0.45)
        if pad_len <= 0.05:
            continue
        n = int(round(pad_len * SR))
        t = np.arange(n, dtype=np.float64) / SR
        chord = chords[idx % len(chords)]

        attack = np.clip(t / 0.45, 0.0, 1.0)
        release = np.clip((pad_len - t) / 0.55, 0.0, 1.0)
        env = np.sin(0.5 * np.pi * attack) * np.sin(0.5 * np.pi * release)

        left = np.zeros(n, dtype=np.float64)
        right = np.zeros(n, dtype=np.float64)
        for v_i, freq in enumerate(chord):
            detune = 1.0 + (v_i - 2) * 0.0018
            lfo = 1.0 + 0.12 * np.sin(2.0 * np.pi * (0.28 + 0.07 * v_i) * t)
            sig_l = np.sin(2.0 * np.pi * freq * t) + 0.25 * np.sin(4.0 * np.pi * freq * t)
            sig_r = np.sin(2.0 * np.pi * (freq * detune) * t + 0.4) + 0.25 * np.sin(4.0 * np.pi * (freq * detune) * t)
            weight = 0.45 / (1.0 + 0.35 * v_i)
            left += sig_l * lfo * weight
            right += sig_r * lfo * weight

        sos = signal.butter(2, 1600.0 / (0.5 * SR), btype="low", output="sos")
        left = signal.sosfilt(sos, left) * env * cfg["pad_gain"]
        right = signal.sosfilt(sos, right) * env * cfg["pad_gain"]

        s0 = int(round(start_t * SR))
        s1 = min(n_samples, s0 + n)
        stereo[s0:s1, 0] += left[: s1 - s0]
        stereo[s0:s1, 1] += right[: s1 - s0]

    return stereo


# =============================================================================
# 3. FRAME-ACCURATE SEMANTIC FOLEY & SCENE TRANSITION CUES
# =============================================================================


def synth_scene_cut(cfg: dict, preset: str, intensity: float, idx: int, rng: np.random.Generator) -> np.ndarray:
    """Medium-authentic scene transition cue: Guqin harmonic gliss, Jazz rimshot/brass, cardstock fold, parchment turn, twilight breeze, or ceramic chime."""
    if preset == "ink":
        chord = cfg["chords"][idx % len(cfg["chords"])]
        harm = synth_guqin_note(chord[2], 1.15, "harmonic", rng)
        n = len(harm)
        scroll = slice_grain("silk_brush_grain", n, rng, gain=0.42)
        return (harm + scroll) * intensity

    if preset == "jazz":
        f0 = cfg["chime_freqs"][idx % len(cfg["chime_freqs"])]
        brass = synth_wah_brass_note(f0, 0.48, wah_open=0.92, rng=rng, gliss=0.08)
        n = len(brass)
        rim = modal_strike(390.0, 0.22, "wood", rng, amp=0.35)
        out = np.zeros(n, dtype=np.float64)
        out += brass
        out[: min(n, len(rim))] += rim[: min(n, len(rim))]
        return out * intensity

    if preset == "paper":
        dur = 0.62
        n = int(round(dur * SR))
        fold = slice_grain("cardstock_fold_grain", n, rng, gain=0.68)
        f0 = cfg["chime_freqs"][idx % len(cfg["chime_freqs"])]
        snap = modal_strike(f0 * 0.5, dur, "wood", rng, amp=0.22)
        return (fold + snap[:n]) * intensity

    if preset == "naturalist":
        dur = 0.64
        n = int(round(dur * SR))
        quill = slice_grain("parchment_quill_grain", n, rng, gain=0.52)
        gear = slice_grain("brass_escapement_grain", min(n, int(0.32 * SR)), rng, gain=0.45)
        f0 = cfg["chime_freqs"][idx % len(cfg["chime_freqs"])]
        bell = modal_strike(f0, dur, "brass", rng, amp=0.20)
        out = quill + bell[:n]
        out[: len(gear)] += gear
        return out * intensity

    if preset == "twilight":
        dur = 0.75
        f0 = cfg["chime_freqs"][idx % len(cfg["chime_freqs"])]
        warm_bell = _synth_felt_piano_voice(f0, dur, rng, vel=0.55)
        return warm_bell * (0.45 * intensity)

    if preset == "clay":
        dur = 0.55
        n = int(round(dur * SR))
        squish = slice_grain("clay_squish_grain", min(n, int(0.28 * SR)), rng, gain=0.52)
        f0 = cfg["chime_freqs"][idx % len(cfg["chime_freqs"])]
        marimba = modal_strike(f0, dur, "marimba", rng, amp=0.28)
        out = marimba[:n].copy()
        out[: len(squish)] += squish
        return out * intensity

    if preset in ("mech", "terminal"):
        dur = 0.58
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_sub = 48.0 + 54.0 * np.exp(-t / 0.038)
        sub_thud = np.sin(2.0 * np.pi * np.cumsum(f_sub) / SR) * np.exp(-t / 0.13) * np.clip(t / 0.004, 0.0, 1.0) * 0.42
        noise = generate_pink_noise(n, rng)
        air_release = time_varying_bandpass(noise, 180.0 + 340.0 * np.exp(-t / 0.18), 1.5) * np.sin(np.pi * np.clip(t / 0.38, 0.0, 1.0)) * 0.24
        clunk = modal_strike(168.0, 0.18, "wood", rng, amp=0.22)
        out = sub_thud + air_release
        out[: min(n, len(clunk))] += clunk[: min(n, len(clunk))]
        return out * intensity

    dur = 0.68
    n = int(round(dur * SR))
    t = np.arange(n, dtype=np.float64) / SR
    phase = 2.0 * np.pi * (44.0 * t + 48.0 * (1.0 - np.exp(-t / 0.14)) * 0.14)
    sub = np.sin(phase) * np.exp(-t / 0.22) * np.clip(t / 0.012, 0.0, 1.0) * 0.36
    noise = generate_pink_noise(n, rng)
    whoosh = time_varying_bandpass(noise, 240.0 + 1600.0 * np.sin(np.pi * t / dur), 2.2) * 0.14
    f0 = cfg["chime_freqs"][idx % len(cfg["chime_freqs"])]
    bell = modal_strike(f0, dur, "bell", rng, amp=0.22)
    return (sub + whoosh + bell[:n]) * intensity


def synth_card_enter(cfg: dict, preset: str, intensity: float, idx: int, rng: np.random.Generator) -> np.ndarray:
    """Medium-authentic physical transient + micro-grain for card/element entrances."""
    f0 = cfg["tap_freq"] * (1.0 + ((idx * 3) % 5) * 0.055)
    if preset == "naturalist":
        dur = 0.24
        n = int(round(dur * SR))
        strike = modal_strike(f0 * 1.15, dur, "brass", rng, amp=0.22)
        grain = slice_grain("parchment_quill_grain", n, rng, gain=0.38)
        return (strike[:n] + grain) * intensity
    if preset == "twilight":
        dur = 0.26
        n = int(round(dur * SR))
        strike = modal_strike(f0 * 0.85, dur, "wood", rng, amp=0.16)
        grain = slice_grain("foliage_paw_grain", n, rng, gain=0.28)
        return (strike[:n] + grain) * intensity
    if preset == "paper":
        dur = 0.25
        n = int(round(dur * SR))
        strike = modal_strike(f0, dur, "wood", rng, amp=0.22)
        grain = slice_grain("cardstock_fold_grain", n, rng, gain=0.48)
        return (strike[:n] + grain) * intensity
    if preset == "clay":
        dur = 0.24
        n = int(round(dur * SR))
        strike = modal_strike(f0, dur, "marimba", rng, amp=0.25)
        grain = slice_grain("clay_squish_grain", n, rng, gain=0.42)
        return (strike[:n] + grain) * intensity
    if preset == "jazz":
        dur = 0.20
        n = int(round(dur * SR))
        strike = modal_strike(f0 * 1.25, dur, "wood", rng, amp=0.28)
        grain = slice_grain("woodblock_mallet_grain", n, rng, gain=0.45)
        return (strike[:n] + grain) * intensity
    if preset == "ink":
        dur = 0.28
        n = int(round(dur * SR))
        strike = modal_strike(f0 * 0.8, dur, "wood", rng, amp=0.22)
        grain = slice_grain("silk_brush_grain", n, rng, gain=0.40)
        return (strike[:n] + grain) * intensity
    if preset in ("mech", "terminal"):
        dur = 0.18
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_thock = (145.0 + 65.0 * np.exp(-t / 0.018)) * (0.94 + 0.04 * (idx % 3))
        thock = np.sin(2.0 * np.pi * np.cumsum(f_thock) / SR) * np.exp(-t / 0.042) * np.clip(t / 0.002, 0.0, 1.0) * 0.30
        detent = modal_strike(240.0, dur, "wood", rng, amp=0.18)
        return (thock + detent[:n]) * intensity
    return modal_strike(f0, 0.20, "wood", rng, amp=0.26) * intensity


def synth_layer_float(cfg: dict, preset: str, intensity: float, idx: int, rng: np.random.Generator) -> np.ndarray:
    """Medium-authentic harmonic lift shimmer or acoustic resonance."""
    dur = 0.46
    n = int(round(dur * SR))
    f1 = cfg["chime_freqs"][(idx + 1) % len(cfg["chime_freqs"])]
    if preset == "naturalist":
        strike = modal_strike(f1, dur, "glass", rng, amp=0.20)
        grain = slice_grain("brass_escapement_grain", n, rng, gain=0.30)
        return (strike[:n] + grain) * intensity
    if preset == "twilight":
        warm_tone = _synth_celesta_bell(min(f1, 659.25), dur, vel=0.50)
        return warm_tone[:n] * (0.45 * intensity)
    if preset == "paper":
        strike = synth_guqin_note(f1, dur, "open", rng) * 0.45
        grain = slice_grain("cardstock_fold_grain", n, rng, gain=0.35)
        return (strike[:n] + grain) * intensity
    if preset == "clay":
        strike = modal_strike(f1, dur, "ceramic", rng, amp=0.22)
        grain = slice_grain("ceramic_clink_grain", n, rng, gain=0.38)
        return (strike[:n] + grain) * intensity
    if preset == "jazz":
        return synth_wah_brass_note(f1, 0.36, wah_open=0.75, rng=rng, gliss=0.05) * (0.65 * intensity)
    if preset in ("mech", "terminal"):
        t = np.arange(n, dtype=np.float64) / SR
        noise = generate_pink_noise(n, rng)
        glide = time_varying_bandpass(noise, 190.0 + 220.0 * np.sin(np.pi * t / dur), 1.6) * np.sin(np.pi * t / dur) * 0.22
        stop_thud = np.sin(2.0 * np.pi * 68.0 * t) * np.exp(-t / 0.09) * np.clip(t / 0.005, 0.0, 1.0) * 0.18
        return (glide + stop_thud) * intensity
    t = np.arange(n, dtype=np.float64) / SR
    f2 = f1 * 1.25
    env = np.sin(np.pi * np.clip(t / dur, 0.0, 1.0)) * np.exp(-t / 0.24)
    shimmer = (np.sin(2.0 * np.pi * f1 * t) + 0.65 * np.sin(2.0 * np.pi * f2 * t)) * env * 0.16
    return shimmer * intensity


def synth_count_tick(cfg: dict, preset: str, intensity: float, idx: int, rng: np.random.Generator) -> np.ndarray:
    """Medium-authentic micro mechanical / escapement / woodblock / droplet tick."""
    f0 = cfg["tick_freq"] * (1.0 + (idx % 4) * 0.04)
    if preset == "naturalist":
        n = int(round(0.09 * SR))
        grain = slice_grain("brass_escapement_grain", n, rng, gain=0.55)
        ping = modal_strike(f0 * 1.4, 0.09, "brass", rng, amp=0.18)
        return (grain + ping[:n]) * intensity
    if preset == "twilight":
        return minnaert_bubble(f0 * 0.72, 0.09, amp=0.22 * intensity)
    if preset == "paper":
        n = int(round(0.08 * SR))
        return slice_grain("cardstock_fold_grain", n, rng, gain=0.52 * intensity)
    if preset == "clay":
        n = int(round(0.09 * SR))
        return modal_strike(f0 * 0.85, 0.09, "marimba", rng, amp=0.24 * intensity)[:n]
    if preset == "jazz":
        n = int(round(0.08 * SR))
        return modal_strike(f0 * 0.9, 0.08, "wood", rng, amp=0.26 * intensity)[:n]
    if preset in ("mech", "terminal"):
        dur = 0.048
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        thock = np.sin(2.0 * np.pi * (210.0 + 18.0 * (idx % 3)) * t) * np.exp(-t / 0.009) * 0.16
        burst = time_varying_bandpass(generate_pink_noise(n, rng), 420.0, 1.8) * np.exp(-t / 0.004) * 0.12
        return fade_in_out((thock + burst) * intensity, 0.0005, 0.008)
    dur = 0.055
    n = int(round(dur * SR))
    t = np.arange(n, dtype=np.float64) / SR
    return np.sin(2.0 * np.pi * f0 * t) * np.exp(-t / 0.010) * 0.14 * intensity


def synth_stroke_draw(preset: str, intensity: float, rng: np.random.Generator) -> np.ndarray:
    """Calligraphic wolf-hair brush sweep, iron-gall quill scratch, or cardstock knife score."""
    dur = 0.38
    n = int(round(dur * SR))
    if preset == "naturalist":
        return slice_grain("parchment_quill_grain", n, rng, gain=0.62 * intensity)
    if preset == "paper":
        return slice_grain("cardstock_fold_grain", n, rng, gain=0.58 * intensity)
    if preset == "ink":
        return slice_grain("silk_brush_grain", n, rng, gain=0.62 * intensity)
    if preset == "twilight":
        return slice_grain("foliage_paw_grain", n, rng, gain=0.52 * intensity)
    if preset == "clay":
        return slice_grain("clay_squish_grain", n, rng, gain=0.52 * intensity)
    t = np.arange(n, dtype=np.float64) / SR
    noise = generate_pink_noise(n, rng)
    f_c = 700.0 + 1800.0 * np.sin(np.pi * t / dur)
    return time_varying_bandpass(noise, f_c, 2.8) * np.sin(np.pi * t / dur) * 0.16 * intensity


def synth_runtime_foley(
    kind: str,
    preset: str,
    intensity: float,
    rng: np.random.Generator,
    pitch: float = 1.0,
) -> np.ndarray:
    """
    Synthesizes 32+ physical & hybrid-grain semantic action foley cues across all 6 styles.
    """
    p_scale = float(np.clip(pitch * rng.uniform(0.95, 1.05), 0.65, 1.55))

    # --- WUXIA & INK-WASH FOLEY ---
    if kind == "blade_clique":
        dur = 0.56
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        guard_click = modal_strike(680.0 * p_scale, dur, "brass", rng, amp=0.26)
        scrape_env = np.exp(-((t - 0.052) / 0.036) ** 2) * np.clip((t - 0.008) / 0.012, 0.0, 1.0)
        scrape = time_varying_bandpass(generate_pink_noise(n, rng), 980.0 + 1350.0 * (t / dur), 3.6) * scrape_env * 0.22
        ring = synth_guqin_note(293.66 * p_scale, dur, "harmonic", rng) * 0.72
        return (guard_click[:n] + scrape + ring[:n]) * intensity

    if kind == "blade_cleave":
        dur = 0.68
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_sub = (54.0 + 135.0 * np.exp(-t / 0.042)) * p_scale
        sub_wave = np.sin(2.0 * np.pi * np.cumsum(f_sub) / SR) * np.exp(-t / 0.14) * np.clip(t / 0.003, 0.0, 1.0) * 0.42
        noise = generate_pink_noise(n, rng)
        f_whip = 1580.0 * np.exp(-t / 0.16) + 260.0
        whip = time_varying_bandpass(noise, f_whip, 2.2) * np.exp(-((t - 0.055) / 0.052) ** 2) * 0.38
        steel_ring = modal_strike(1180.0 * p_scale, dur, "metal", rng, amp=0.26)
        return (sub_wave + whip + steel_ring[:n]) * intensity

    if kind == "blood_splatter":
        dur = 0.62
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        wet = slice_grain("stream_bubble_grain", n, rng, gain=0.65)
        t_fall = np.maximum(0.0, t - 0.15)
        fall_gate = (t >= 0.15).astype(np.float64) * np.clip(t_fall / 0.006, 0.0, 1.0)
        f_thud = 46.0 + 78.0 * np.exp(-t_fall / 0.045)
        body_thud = np.sin(2.0 * np.pi * np.cumsum(f_thud) / SR) * np.exp(-t_fall / 0.13) * fall_gate * 0.38
        brush = slice_grain("silk_brush_grain", n, rng, gain=0.42)
        return (wet + body_thud + brush) * intensity

    if kind == "calligraphy_slam":
        dur = 0.54
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_slam = 62.0 + 95.0 * np.exp(-t / 0.030)
        slam_thud = np.sin(2.0 * np.pi * np.cumsum(f_slam) / SR) * np.exp(-t / 0.075) * np.clip(t / 0.003, 0.0, 1.0) * 0.36
        tear = slice_grain("silk_brush_grain", n, rng, gain=0.72)
        return (slam_thud + tear) * intensity

    if kind == "blade_sheathe":
        dur = 0.78
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        glide_win = np.sin(np.pi * np.clip(t / 0.44, 0.0, 1.0)) ** 0.85 * (t <= 0.44).astype(np.float64)
        f_slide = (780.0 + 920.0 * np.clip(t / 0.44, 0.0, 1.0) ** 1.2) * p_scale
        glide = time_varying_bandpass(generate_pink_noise(n, rng), np.clip(f_slide, 260.0, 2400.0), 4.0) * glide_win * 0.22
        lock_idx = int(round(0.47 * SR))
        clasp = modal_strike(580.0 * p_scale, 0.28, "wood", rng, amp=0.28) + modal_strike(1420.0 * p_scale, 0.28, "brass", rng, amp=0.24)
        out = glide.copy()
        rem = min(len(clasp), n - lock_idx)
        if rem > 0:
            out[lock_idx : lock_idx + rem] += clasp[:rem]
        return out * intensity

    if kind == "cinnabar_seal_stamp":
        dur = 0.34
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_stone = (88.0 + 110.0 * np.exp(-t / 0.022)) * p_scale
        stone_thud = np.sin(2.0 * np.pi * np.cumsum(f_stone) / SR) * np.exp(-t / 0.065) * 0.34
        wood = modal_strike(420.0 * p_scale, dur, "wood", rng, amp=0.26)
        paper = slice_grain("parchment_quill_grain", n, rng, gain=0.38)
        return (stone_thud + wood[:n] + paper) * intensity

    if kind == "taiko_impact":
        return synth_taiko_impact(intensity, rng)

    if kind == "qin_strumming_slash":
        chord = PRESETS.get(preset, PRESETS["ink"]).get("chords", [[146.83, 196.00, 220.00, 293.66, 329.63]])[2 % 4]
        return synth_qin_strumming_slash(chord, 1.35, intensity, rng)

    if kind == "wave_surge":
        dur = 0.88
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        noise = generate_pink_noise(n, rng)
        f_sweep = 160.0 + 980.0 * np.sin(np.pi * t / dur) ** 1.4
        roar = time_varying_bandpass(noise, f_sweep, 1.4) * np.sin(np.pi * t / dur) * 0.28
        bubbles = slice_grain("stream_bubble_grain", n, rng, gain=0.52)
        return (roar + bubbles) * intensity

    if kind == "sword_slash":
        dur = 0.38
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        noise = generate_pink_noise(n, rng)
        f_whip = 1650.0 * np.exp(-t / 0.12) + 340.0
        whoosh = time_varying_bandpass(noise, f_whip, 2.2) * np.exp(-((t - 0.08) / 0.055) ** 2) * 0.28
        ring = synth_guqin_note(329.63 * p_scale, dur, "harmonic", rng) * 0.55
        return (whoosh + ring[:n]) * intensity

    if kind == "drink_sip":
        dur = 0.38
        n = int(round(dur * SR))
        b1 = minnaert_bubble(420.0 * p_scale, 0.14, amp=0.22)
        b2 = minnaert_bubble(560.0 * p_scale, 0.14, amp=0.18)
        clink = modal_strike(780.0 * p_scale, dur, "ceramic", rng, amp=0.16)
        out = clink[:n].copy()
        out[: len(b1)] += b1
        s2 = min(n - len(b2), int(0.08 * SR))
        if s2 > 0:
            out[s2 : s2 + len(b2)] += b2
        return out * intensity

    # --- VINTAGE-NATURALIST FOLEY (Quill, Specimen Pin, Brass Escapement, Balance Scale, Astral Bloom) ---
    if kind == "quill_etch":
        dur = 0.42
        n = int(round(dur * SR))
        grain = slice_grain("parchment_quill_grain", n, rng, gain=0.72)
        nib = modal_strike(1850.0 * p_scale, dur, "brass", rng, amp=0.12)
        return (grain + nib[:n]) * intensity

    if kind == "specimen_pin":
        dur = 0.32
        n = int(round(dur * SR))
        pin_ping = modal_strike(2420.0 * p_scale, dur, "brass", rng, amp=0.28)
        wood_thud = modal_strike(310.0 * p_scale, dur, "wood", rng, amp=0.25)
        paper = slice_grain("parchment_quill_grain", n, rng, gain=0.35)
        return (pin_ping[:n] + wood_thud[:n] + paper) * intensity

    if kind == "brass_ratchet":
        if preset in ("mech", "terminal"):
            dur = 0.42
            n = int(round(dur * SR))
            t = np.arange(n, dtype=np.float64) / SR
            out = np.zeros(n, dtype=np.float64)
            for click_i, t_off in enumerate((0.01, 0.085, 0.165, 0.255)):
                s0 = int(round(t_off * SR))
                c_len = min(int(0.065 * SR), n - s0)
                if c_len > 8:
                    tc = np.arange(c_len, dtype=np.float64) / SR
                    f_det = (185.0 + 22.0 * click_i) * p_scale
                    det = np.sin(2.0 * np.pi * f_det * tc) * np.exp(-tc / 0.012) * 0.24
                    clunk = modal_strike(260.0 * p_scale, 0.065, "wood", rng, amp=0.18)
                    out[s0 : s0 + c_len] += det + clunk[:c_len]
            flow = time_varying_bandpass(generate_pink_noise(n, rng), 220.0 * p_scale, 1.6) * np.sin(np.pi * t / dur) * 0.16
            return fade_in_out((out + flow) * intensity, 0.002, 0.02)
        dur = 0.44
        n = int(round(dur * SR))
        grain = slice_grain("brass_escapement_grain", n, rng, gain=0.75)
        bell = modal_strike(1320.0 * p_scale, dur, "brass", rng, amp=0.22)
        return (grain + bell[:n]) * intensity

    if kind == "scale_tilt":
        if preset in ("mech", "terminal"):
            dur = 0.50
            n = int(round(dur * SR))
            t = np.arange(n, dtype=np.float64) / SR
            f_servo = (128.0 + 48.0 * np.sin(np.pi * t / dur)) * p_scale
            ph_servo = 2.0 * np.pi * np.cumsum(f_servo) / SR
            servo = (np.sin(ph_servo) + 0.35 * np.sin(2.0 * ph_servo)) * np.sin(np.pi * t / dur) * 0.18
            valve = time_varying_bandpass(generate_pink_noise(n, rng), (240.0 + 160.0 * np.sin(np.pi * t / dur)) * p_scale, 1.8) * np.sin(np.pi * t / dur) * 0.20
            lock_thud = np.sin(2.0 * np.pi * 74.0 * t) * np.exp(-t / 0.095) * np.clip(t / 0.004, 0.0, 1.0) * 0.28
            return fade_in_out((servo + valve + lock_thud) * intensity, 0.003, 0.025)
        dur = 0.52
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        creak_f = (380.0 + 180.0 * np.sin(2.0 * np.pi * 3.5 * t)) * p_scale
        chain = time_varying_bandpass(generate_pink_noise(n, rng), creak_f, 6.5) * np.sin(np.pi * t / dur) * 0.22
        chime = modal_strike(980.0 * p_scale, dur, "brass", rng, amp=0.26)
        return (chain + chime[:n]) * intensity

    if kind == "astral_bloom":
        dur = 0.68
        n = int(round(dur * SR))
        shimmer = slice_grain("crystal_shimmer_grain", n, rng, gain=0.58)
        chord_bell = (
            modal_strike(587.33 * p_scale, dur, "glass", rng, amp=0.20)
            + modal_strike(880.0 * p_scale, dur, "glass", rng, amp=0.16)
        )
        return (shimmer + chord_bell[:n]) * intensity

    # --- TWILIGHT-FABLE FOLEY (100% Noise-Free, Silky Musical Foley) ---
    if kind == "paw_step":
        dur = 0.16
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        # Ultra-soft low velvet cushion thud (62Hz -> 40Hz) with smooth sine attack, zero noise
        f_pad = (40.0 + 22.0 * np.exp(-t / 0.025)) * p_scale
        pad = np.sin(2.0 * np.pi * np.cumsum(f_pad) / SR) * np.sin(0.5 * np.pi * np.clip(t / 0.012, 0.0, 1.0)) * np.exp(-t / 0.042)
        return fade_in_out(pad * 0.08 * intensity, 0.008, 0.03)

    if kind == "ear_perk":
        dur = 0.45
        return _synth_felt_piano_voice(392.00, dur, rng, vel=0.28) * (0.28 * intensity)

    if kind == "critter_hop":
        dur = 0.55
        n = int(round(dur * SR))
        n1 = _synth_felt_piano_voice(293.66, dur, rng, vel=0.32)
        n2 = _synth_felt_piano_voice(440.00, dur, rng, vel=0.28)
        out = n1[:n].copy()
        s2 = int(0.07 * SR)
        if s2 < n:
            out[s2:] += n2[: n - s2]
        return fade_in_out(out * (0.30 * intensity), 0.01, 0.05)

    if kind == "water_ripple":
        dur = 0.65
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        # Pure, round water droplet (smooth sine glide 330Hz -> 440Hz, soft 12ms attack, zero noise)
        f_drop = (330.0 + 110.0 * (1.0 - np.exp(-t / 0.045))) * p_scale
        env_d = np.sin(0.5 * np.pi * np.clip(t / 0.012, 0.0, 1.0)) * np.exp(-t / 0.085)
        drop = np.sin(2.0 * np.pi * np.cumsum(f_drop) / SR) * env_d * 0.11
        warm_echo = _synth_celesta_bell(523.25, dur, vel=0.26)
        out = drop + warm_echo[:n] * 0.45
        return fade_in_out(out * (0.32 * intensity), 0.01, 0.05)

    if kind == "spirit_shimmer":
        dur = 0.85
        n = int(round(dur * SR))
        n1 = _synth_felt_piano_voice(392.00, dur, rng, vel=0.34)
        n2 = _synth_celesta_bell(587.33, dur, vel=0.28)
        out = n1[:n].copy()
        s2 = int(0.11 * SR)
        if s2 < n:
            out[s2:] += n2[: n - s2]
        return fade_in_out(out * (0.32 * intensity), 0.015, 0.06)

    if kind == "wood_creak":
        dur = 0.48
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        # Stick-slip wooden door / branch creak
        rate = 28.0 + 18.0 * np.sin(np.pi * t / dur)
        pulses = np.maximum(0.0, np.sin(2.0 * np.pi * np.cumsum(rate) / SR)) ** 6.0
        exc = pulses * generate_pink_noise(n, rng)
        creak = time_varying_bandpass(exc, (360.0 + 140.0 * np.sin(2.0 * np.pi * 2.5 * t)) * p_scale, 5.5) * 0.45
        body = modal_strike(210.0 * p_scale, dur, "wood", rng, amp=0.22)
        return (creak + body[:n]) * intensity

    # --- PAPER-POPUP FOLEY (Page Turn, Pop-up Snap, Origami Wing, Paper Bell) ---
    if kind == "page_turn":
        dur = 0.52
        n = int(round(dur * SR))
        return slice_grain("cardstock_fold_grain", n, rng, gain=0.78 * intensity)

    if kind == "popup_snap":
        dur = 0.34
        n = int(round(dur * SR))
        fold = slice_grain("cardstock_fold_grain", n, rng, gain=0.64)
        snap = modal_strike(520.0 * p_scale, dur, "wood", rng, amp=0.28)
        return (fold + snap[:n]) * intensity

    if kind == "origami_wing":
        dur = 0.32
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        flap_env = np.exp(-((t - 0.07) / 0.035) ** 2) + 0.75 * np.exp(-((t - 0.19) / 0.04) ** 2)
        whoosh = time_varying_bandpass(generate_pink_noise(n, rng), 950.0 * p_scale, 2.5) * flap_env * 0.32
        paper = slice_grain("cardstock_fold_grain", n, rng, gain=0.45)
        return (whoosh + paper) * intensity

    if kind == "paper_bell":
        dur = 0.48
        n = int(round(dur * SR))
        harp = synth_guqin_note(659.25 * p_scale, dur, "open", rng) * 0.55
        bell = modal_strike(1318.5 * p_scale, dur, "bell", rng, amp=0.20)
        return (harp[:n] + bell[:n]) * intensity

    # --- CLAY-MACARON FOLEY (Clay Squish, Liquid Pour, Wood Roll, Musicbox Chime, Ceramic Clink) ---
    if kind == "clay_squish":
        dur = 0.30
        n = int(round(dur * SR))
        squish = slice_grain("clay_squish_grain", n, rng, gain=0.76)
        pop = minnaert_bubble(340.0 * p_scale, 0.12, amp=0.22)
        out = squish.copy()
        out[: len(pop)] += pop
        return out * intensity

    if kind == "liquid_pour":
        dur = 0.54
        n = int(round(dur * SR))
        stream = slice_grain("stream_bubble_grain", n, rng, gain=0.65)
        clink = slice_grain("ceramic_clink_grain", n, rng, gain=0.48)
        return (stream + clink) * intensity

    if kind == "wood_roll":
        dur = 0.38
        n = int(round(dur * SR))
        mallet = slice_grain("woodblock_mallet_grain", n, rng, gain=0.72)
        marimba = modal_strike(587.33 * p_scale, dur, "marimba", rng, amp=0.24)
        return (mallet + marimba[:n]) * intensity

    if kind == "musicbox_chime":
        dur = 0.52
        n = int(round(dur * SR))
        tine1 = modal_strike(1046.5 * p_scale, dur, "bell", rng, amp=0.24)
        tine2 = modal_strike(1318.5 * p_scale, dur, "bell", rng, amp=0.20)
        out = tine1[:n].copy()
        s2 = int(0.07 * SR)
        if s2 < n:
            out[s2:] += tine2[: n - s2]
        return out * intensity

    if kind == "ceramic_clink":
        dur = 0.32
        n = int(round(dur * SR))
        grain = slice_grain("ceramic_clink_grain", n, rng, gain=0.68)
        strike = modal_strike(1760.0 * p_scale, dur, "ceramic", rng, amp=0.24)
        return (grain + strike[:n]) * intensity

    # --- RUBBER-HOSE JAZZ FOLEY (Projector, Curtain Whoosh, Gramophone Crank, Horn Blast, Cartoon Boing, Bass Slap, Cymbal Clang, Slide Whistle, Xylophone Run) ---
    if kind == "reel_projector":
        dur = 0.46
        n = int(round(dur * SR))
        opt = slice_grain("vinyl_optical_grain", n, rng, gain=0.70)
        gear = slice_grain("brass_escapement_grain", n, rng, gain=0.52)
        return (opt + gear) * intensity

    if kind == "curtain_whoosh":
        dur = 0.44
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_sw = (320.0 + 1600.0 * np.sin(np.pi * t / dur)) * p_scale
        sw = time_varying_bandpass(generate_pink_noise(n, rng), f_sw, 2.2) * np.sin(np.pi * t / dur) * 0.34
        return sw * intensity

    if kind == "gramophone_crank":
        dur = 0.42
        n = int(round(dur * SR))
        gear = slice_grain("brass_escapement_grain", n, rng, gain=0.78)
        wood = modal_strike(340.0 * p_scale, dur, "wood", rng, amp=0.22)
        return (gear + wood[:n]) * intensity

    if kind == "horn_blast":
        return synth_wah_brass_note(523.25 * p_scale, 0.42, wah_open=0.95, rng=rng, gliss=0.14) * (1.15 * intensity)

    if kind in ("boing_hop", "cartoon_boing"):
        dur = 0.34
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_curve = 230.0 * p_scale * (1.0 + 0.92 * (1.0 - np.exp(-t / 0.08)) + 0.22 * np.sin(2.0 * np.pi * 22.0 * t))
        phase = 2.0 * np.pi * np.cumsum(f_curve) / SR
        boing = (np.sin(phase) + 0.35 * np.sin(2.0 * phase)) * np.exp(-t / 0.16) * 0.24
        return boing * intensity

    if kind == "bass_slap":
        return synth_upright_bass_note(110.0 * p_scale, 0.32, rng) * (1.15 * intensity)

    if kind == "cymbal_clang":
        dur = 0.58
        n = int(round(dur * SR))
        cym = modal_strike(1180.0 * p_scale, dur, "metal", rng, amp=0.32)
        sizzle = time_varying_bandpass(generate_pink_noise(n, rng), 5200.0, 1.8) * np.exp(-np.arange(n) / (0.18 * SR)) * 0.22
        return (cym[:n] + sizzle) * intensity

    if kind == "slide_whistle":
        dur = 0.42
        n = int(round(dur * SR))
        t = np.arange(n, dtype=np.float64) / SR
        f_gliss = (540.0 + 1320.0 * np.sin(np.pi * np.clip(t / dur, 0.0, 1.0)) ** 1.2) * p_scale
        whistle = np.sin(2.0 * np.pi * np.cumsum(f_gliss) / SR) * np.sin(np.pi * t / dur) * 0.24
        breath = time_varying_bandpass(generate_pink_noise(n, rng), f_gliss, 6.0) * 0.08
        return (whistle + breath) * intensity

    if kind == "xylophone_run":
        dur = 0.36
        n = int(round(dur * SR))
        grain = slice_grain("woodblock_mallet_grain", n, rng, gain=0.78)
        strike = modal_strike(880.0 * p_scale, dur, "marimba", rng, amp=0.24)
        return (grain + strike[:n]) * intensity

    if kind == "foot_step":
        if preset == "twilight":
            return synth_runtime_foley("paw_step", preset, intensity, rng, pitch=pitch)
        if preset == "clay":
            return synth_runtime_foley("clay_squish", preset, intensity, rng, pitch=pitch)
        dur = 0.14
        n = int(round(dur * SR))
        thud = modal_strike(155.0 * p_scale, dur, "wood", rng, amp=0.22)
        scuff = slice_grain("foliage_paw_grain", n, rng, gain=0.28)
        return (thud[:n] + scuff) * intensity

    return synth_stroke_draw(preset, intensity, rng)


def _resolve_cue_semantic_action(kind: str, label: str, preset: str) -> str:
    """Maps (kind, label) from HTML data-cues, [data-sfx], and runtime cues to 32+ exact acoustic synthesis primitives."""
    k = (kind or "").strip().lower()
    lbl = (label or "").strip().lower()

    direct_foley = {
        "blade_clique",
        "blade_cleave",
        "blood_splatter",
        "calligraphy_slam",
        "blade_sheathe",
        "cinnabar_seal_stamp",
        "taiko_impact",
        "qin_strumming_slash",
        "wave_surge",
        "sword_slash",
        "drink_sip",
        "brush_sweep",
        "foot_step",
        "boing_hop",
        "cartoon_boing",
        "quill_etch",
        "specimen_pin",
        "brass_ratchet",
        "scale_tilt",
        "astral_bloom",
        "paw_step",
        "ear_perk",
        "critter_hop",
        "water_ripple",
        "spirit_shimmer",
        "wood_creak",
        "page_turn",
        "popup_snap",
        "origami_wing",
        "paper_bell",
        "clay_squish",
        "liquid_pour",
        "wood_roll",
        "musicbox_chime",
        "ceramic_clink",
        "reel_projector",
        "curtain_whoosh",
        "gramophone_crank",
        "horn_blast",
        "bass_slap",
        "cymbal_clang",
        "slide_whistle",
        "xylophone_run",
    }
    if k in direct_foley:
        return k
    if lbl in direct_foley:
        return lbl

    # Direct [data-sfx] aliases from paper-popup / rubber-hose / clay-macaron / twilight-fable
    if k in ("whoosh", "swipe"):
        if preset == "paper":
            return "page_turn"
        if preset == "jazz":
            return "curtain_whoosh"
        if preset == "twilight":
            return "ear_perk"
        return "sword_slash" if preset == "ink" else "page_turn"
    if k == "pop":
        if preset == "paper":
            return "popup_snap"
        if preset == "clay":
            return "clay_squish"
        if preset == "jazz":
            return "cartoon_boing"
        return "specimen_pin" if preset == "naturalist" else "popup_snap"
    if k == "chime":
        if preset == "paper":
            return "paper_bell"
        if preset == "clay":
            return "musicbox_chime"
        if preset == "twilight":
            return "spirit_shimmer"
        if preset == "naturalist":
            return "astral_bloom"
        return "paper_bell"
    if k == "thud":
        if preset == "paper":
            return "popup_snap"
        if preset == "clay":
            return "clay_squish"
        if preset == "ink":
            return "cinnabar_seal_stamp"
        return "foot_step"

    for token in (lbl, k):
        if not token:
            continue
        # Wuxia / Ink-wash
        if any(w in token for w in ("blade_clique", "clique", "unsheathe", "thumb_hilt", "guard_push")):
            return "blade_clique"
        if any(w in token for w in ("blade_cleave", "cleave", "kill_slash", "crescent_slash")):
            return "blade_cleave"
        if any(w in token for w in ("blood_splatter", "blood", "splatter", "crimson_burst")):
            return "blood_splatter"
        if any(w in token for w in ("calligraphy_slam", "kuangcao", "verse_slam", "brush_slam")):
            return "calligraphy_slam"
        if any(w in token for w in ("blade_sheathe", "sheathe", "scabbard_lock")):
            return "blade_sheathe"
        if any(w in token for w in ("cinnabar", "seal_stamp", "seal")):
            return "cinnabar_seal_stamp"
        if any(w in token for w in ("taiko", "war_drum", "drum_slam")):
            return "taiko_impact"
        if any(w in token for w in ("qin_strumming", "strumming_slash", "pipa_slash")):
            return "qin_strumming_slash"
        if "sword" in token or "slash" in token:
            return "sword_slash"

        # Vintage-Naturalist
        if any(w in token for w in ("quill", "etch", "crosshatch", "calligraphy", "copperplate", "fig_label", "binomial", "latin")):
            return "quill_etch"
        if any(w in token for w in ("specimen", "pin", "beetle", "moth", "shell", "botanical", "fern", "plate")):
            return "specimen_pin"
        if any(w in token for w in ("dial", "compass", "caliper", "escapement", "ratchet", "chronometer", "gear", "vernier")):
            return "brass_ratchet"
        if any(w in token for w in ("balance", "scale", "tilt", "pendulum", "equilibrium")):
            return "scale_tilt"
        if any(w in token for w in ("tree", "phylo", "branch_grow", "astral", "constellation", "orbit", "darwin")):
            return "astral_bloom"

        # Twilight-Fable
        if any(w in token for w in ("paw", "pad_step", "forest_step", "moss_step", "trot")):
            return "paw_step"
        if any(w in token for w in ("ear", "perk", "whisker", "blink", "sniff", "head_tilt")):
            return "ear_perk"
        if any(w in token for w in ("creak", "door", "trunk", "bark", "hollow", "branch")):
            return "wood_creak"
        if any(w in token for w in ("ripple", "pond", "stream", "brook", "water", "reflection", "lotus")):
            return "water_ripple"
        if any(w in token for w in ("spirit", "lantern", "firefly", "spore", "glow", "wisp", "beacon", "starlight")):
            return "spirit_shimmer"
        if any(w in token for w in ("fawn", "deer", "fox", "cat", "bunny", "rabbit", "squirrel", "critter", "leap", "bound")):
            return "critter_hop"

        # Paper-Popup
        if any(w in token for w in ("page", "turn", "unfurl", "book_open", "spread", "cover")):
            return "page_turn"
        if any(w in token for w in ("popup", "v_fold", "v-fold", "crease", "tab", "cardstock", "fold", "arch", "pagoda", "bridge")):
            return "popup_snap"
        if any(w in token for w in ("crane", "origami", "wing", "flap", "bird", "heron", "swallow", "kite")):
            return "origami_wing"

        # Clay-Macaron
        if any(w in token for w in ("pour", "tea", "coffee", "syrup", "honey", "milk", "kettle", "brew", "drip")):
            return "liquid_pour"
        if any(w in token for w in ("squash", "squish", "dough", "knead", "clay", "puff", "pastry", "macaron", "bun", "cake")):
            return "clay_squish"
        if any(w in token for w in ("domino", "roll", "marble", "wheel", "cart", "track", "gear_turn", "conveyor")):
            return "wood_roll"
        if any(w in token for w in ("pearl", "cup", "saucer", "spoon", "plate", "porcelain", "ceramic", "jar", "bottle")):
            return "ceramic_clink"
        if any(w in token for w in ("musicbox", "carousel", "windup", "chime", "bell", "ding", "sparkle")):
            return "musicbox_chime" if preset == "clay" else ("paper_bell" if preset == "paper" else "spirit_shimmer")

        # Rubber-Hose Jazz
        if any(w in token for w in ("reel", "projector", "countdown", "celluloid", "shutter", "title_card")):
            return "reel_projector"
        if any(w in token for w in ("curtain", "drape", "spotlight", "stage")):
            return "curtain_whoosh"
        if any(w in token for w in ("gramophone", "crank", "vinyl", "phonograph", "needle")):
            return "gramophone_crank"
        if any(w in token for w in ("horn", "trumpet", "trombone", "brass", "sax", "wah", "fanfare", "riff")):
            return "horn_blast"
        if any(w in token for w in ("bass", "slap", "contrabass", "upright", "plunk")):
            return "bass_slap"
        if any(w in token for w in ("clang", "cymbal", "crash", "starburst", "anvil", "smash", "pie")):
            return "cymbal_clang"
        if any(w in token for w in ("whistle", "slide_whistle", "siren", "eyeball", "jaw_drop", "take")):
            return "slide_whistle"
        if any(w in token for w in ("xylo", "marimba", "skeleton", "rib", "tiptoe", "scurry", "keys")):
            return "xylophone_run"
        if any(w in token for w in ("boing", "hop", "bounce", "spring", "jump", "glove")):
            return "critter_hop" if preset == "twilight" else ("clay_squish" if preset == "clay" else "cartoon_boing")

        # Shared water / sip / step / brush
        if "wave" in token or "surge" in token:
            return "wave_surge"
        if "drink" in token or "wine" in token or "sip" in token:
            return "drink_sip"
        if "step" in token or "walk" in token or "stride" in token:
            return "paw_step" if preset == "twilight" else "foot_step"
        if any(w in token for w in ("xingcao", "verse", "colophon", "brush", "stroke", "inscription")):
            return "quill_etch" if preset == "naturalist" else "stroke_draw"

    if k in ("scene_cut", "cut"):
        return "scene_cut"
    if k in ("layer_float", "float", "mist"):
        return "layer_float"
    if k in ("count_tick", "tick"):
        return "count_tick"
    if k in ("stroke_draw", "stroke"):
        return "quill_etch" if preset == "naturalist" else "stroke_draw"
    if k in ("impact", "hit", "slam"):
        if preset == "ink":
            return "cinnabar_seal_stamp"
        if preset == "jazz":
            return "cymbal_clang"
        if preset == "clay":
            return "clay_squish"
        if preset == "paper":
            return "popup_snap"
        if preset == "twilight":
            return "wood_creak"
        if preset == "naturalist":
            return "specimen_pin"
        return "card_enter"
    if k in ("enter", "card_enter"):
        return "stroke_draw" if preset == "ink" else "card_enter"

    return "card_enter"


def master_bus(stereo: np.ndarray, preset: str = "glass", ceiling_db: float = -1.2) -> np.ndarray:
    """Applies medium-appropriate tonal shaping, DC block, dynamic-range-preserving leveling, and true-peak limiting."""
    # High-pass to remove DC/rumble (1930s optical film rolls off below 95Hz; ink rolls off sub-48Hz rumble; others 28Hz)
    hp_hz = 95.0 if preset == "jazz" else (48.0 if preset == "ink" else 28.0)
    sos_hp = signal.butter(2, hp_hz / (0.5 * SR), btype="high", output="sos")
    out = signal.sosfilt(sos_hp, stereo, axis=0)

    if preset == "jazz":
        # Vintage 1930s optical sound-on-film high roll-off at 5.6 kHz for authentic warm celluloid tone
        sos_lp = signal.butter(2, 5600.0 / (0.5 * SR), btype="low", output="sos")
        out = signal.sosfilt(sos_lp, out, axis=0)
    elif preset == "twilight":
        # Warm picture-book nocturnal tone: roll off harsh highs above 2.6 kHz
        sos_lp = signal.butter(2, 2600.0 / (0.5 * SR), btype="low", output="sos")
        out = signal.sosfilt(sos_lp, out, axis=0)
    elif preset in ("mech", "terminal"):
        # Warm heavy-machinery / deep-sea lab acoustic roll-off at 2.2 kHz: zero harsh metallic/electronic highs
        sos_lp = signal.butter(2, 2200.0 / (0.5 * SR), btype="low", output="sos")
        out = signal.sosfilt(sos_lp, out, axis=0)
    elif preset == "ink":
        # Warm Song-Yuan silk-scroll Guqin/Xiao tone: roll off harsh highs above 3.8 kHz
        sos_lp = signal.butter(2, 3800.0 / (0.5 * SR), btype="low", output="sos")
        out = signal.sosfilt(sos_lp, out, axis=0)
    else:
        # Gentle high roll-off at 6.8 kHz across all other styles so no preset has piercing >7kHz transients
        sos_lp = signal.butter(2, 6800.0 / (0.5 * SR), btype="low", output="sos")
        out = signal.sosfilt(sos_lp, out, axis=0)

    # Measure RMS only on active (non-silent) regions so dramatic silence holds are never pumped up
    mono_abs = np.max(np.abs(out), axis=1)
    active_mask = mono_abs > 1.5e-3
    if np.any(active_mask):
        active_rms = np.sqrt(np.mean(out[active_mask] ** 2) + 1e-12)
    else:
        active_rms = np.sqrt(np.mean(out ** 2) + 1e-12)

    # Preserve wide Crest Factor for dramatic ink-wash & gentle twilight scores while keeping healthy loudness
    target_rms = 0.095 if preset in ("twilight", "mech", "terminal") else (0.115 if preset == "ink" else 0.135)
    max_gain = 1.8 if preset in ("twilight", "mech", "terminal") else (2.4 if preset == "ink" else 3.6)
    gain = float(np.clip(target_rms / active_rms, 0.55, max_gain))
    out = out * gain

    # Soft-knee transparent limiting only above knee_thresh (0.68 ~ -3.3 dBFS) so silence & quiet passages stay linear
    knee_thresh = 0.95 if preset == "twilight" else 0.68
    mag = np.abs(out)
    over = mag > knee_thresh
    if np.any(over) and preset != "twilight":
        sign = np.sign(out[over])
        excess = (mag[over] - knee_thresh) / (1.0 - knee_thresh)
        out[over] = sign * (knee_thresh + (1.0 - knee_thresh) * np.tanh(excess))

    # True-peak ceiling at ceiling_db (-1.2 dBTP)
    ceiling = 10.0 ** (ceiling_db / 20.0)
    peak = float(np.max(np.abs(out)))
    if peak > ceiling:
        out *= ceiling / peak
    elif peak > 1e-5:
        out *= min(1.22, ceiling / peak)

    # Gentle 40ms fade-in and 120ms fade-out
    n = out.shape[0]
    fi = min(n, int(0.04 * SR))
    fo = min(n, int(0.12 * SR))
    if fi > 0:
        out[:fi] *= np.linspace(0.0, 1.0, fi)[:, None]
    if fo > 0:
        out[-fo:] *= np.linspace(1.0, 0.0, fo)[:, None]

    return out


def _load_voice(path: str, n: int) -> np.ndarray:
    """Read a mono/stereo voice WAV, resample to 48 kHz, and fit it to `n` samples."""
    try:
        import soundfile as sf
    except ImportError:
        raise SystemExit("sound.py: --voice needs soundfile (pip install soundfile)")
    try:
        audio, sr = sf.read(path, dtype="float32", always_2d=False)
    except Exception as e:
        raise SystemExit(f"sound.py: cannot read voice '{path}': {e}")
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.reshape(-1)
    if sr != SR and audio.size:
        audio = signal.resample_poly(audio, SR, sr).astype(np.float32)
    if audio.size < n:
        audio = np.pad(audio, (0, n - audio.size))
    else:
        audio = audio[:n]
    return audio


def voice_envelope(voice: np.ndarray, attack: float = 0.02, release: float = 0.25) -> np.ndarray:
    """10 ms RMS envelope (0..1) with a fast attack and a slow release for sidechain ducking."""
    hop = max(1, int(0.01 * SR))
    frames = voice.size // hop
    if frames <= 0:
        return np.zeros(voice.size, dtype=np.float32)
    rms = np.sqrt(np.mean(voice[: frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-12)
    ref = float(np.percentile(rms, 95))
    if ref < 1e-5:
        return np.zeros(voice.size, dtype=np.float32)
    target = np.clip((rms / ref - 0.04) / 0.96, 0.0, 1.0)
    ca = 1.0 - np.exp(-hop / (max(float(attack), 1e-3) * SR))
    cr = 1.0 - np.exp(-hop / (max(float(release), 1e-3) * SR))
    env = np.empty_like(target)
    y = 0.0
    for i, x in enumerate(target):
        y += (x - y) * (ca if x > y else cr)
        env[i] = y
    env = np.repeat(env, hop)
    if env.size < voice.size:
        env = np.pad(env, (0, voice.size - env.size), constant_values=float(env[-1]) if env.size else 0.0)
    return env[: voice.size].astype(np.float32)


def mix_voice_into(
    stereo: np.ndarray,
    voice_path: str,
    duck_db: float = -10.0,
    voice_gain_db: float = 0.0,
    attack: float = 0.02,
    release: float = 0.25,
    ceiling_db: float = -1.2,
) -> np.ndarray:
    """
    Carve a Mid-channel spectral vocal pocket (220 Hz - 3800 Hz) under the voice with 18 ms lookahead,
    preserving <220 Hz bass fundamentals and stereo Side ambience, then blend the voice with a subtle
    decorrelated early-reflection halo and soft-knee true-peak limiting.
    """
    n = stereo.shape[0]
    voice = _load_voice(voice_path, n)
    if not np.any(voice):
        return stereo
    duck_db = min(0.0, float(duck_db))
    bg = np.asarray(stereo, dtype=np.float64)
    v = np.asarray(voice, dtype=np.float64)

    if duck_db < 0.0:
        lookahead = int(0.018 * SR)
        v_det = np.pad(v[lookahead:], (0, min(lookahead, v.size))) if lookahead < v.size else v
        env = voice_envelope(v_det.astype(np.float32), attack=attack, release=max(release, 0.28)).astype(np.float64)

        mid = 0.5 * (bg[:, 0] + bg[:, 1])
        side = 0.5 * (bg[:, 0] - bg[:, 1])
        sos_formant = signal.butter(2, [220.0 / (0.5 * SR), 3800.0 / (0.5 * SR)], btype="band", output="sos")
        mid_formant = signal.sosfilt(sos_formant, mid)
        mid_outer = mid - mid_formant

        floor_mid = 10.0 ** (duck_db / 20.0)
        floor_outer = 10.0 ** ((duck_db * 0.35) / 20.0)
        floor_side = 10.0 ** ((duck_db * 0.22) / 20.0)

        mid_ducked = mid_formant * (1.0 - (1.0 - floor_mid) * env) + mid_outer * (1.0 - (1.0 - floor_outer) * env)
        side_ducked = side * (1.0 - (1.0 - floor_side) * env)
        bg = np.column_stack((mid_ducked + side_ducked, mid_ducked - side_ducked))

    v_scaled = v * (10.0 ** (float(voice_gain_db) / 20.0))
    sos_halo = signal.butter(2, [200.0 / (0.5 * SR), 2800.0 / (0.5 * SR)], btype="band", output="sos")
    v_halo = signal.sosfilt(sos_halo, v_scaled) * 0.18
    d_l, d_r = int(0.013 * SR), int(0.021 * SR)
    halo_l = np.pad(v_halo[:-d_l], (d_l, 0)) if d_l < n else np.zeros_like(v_scaled)
    halo_r = -np.pad(v_halo[:-d_r], (d_r, 0)) if d_r < n else np.zeros_like(v_scaled)

    out = np.column_stack((bg[:, 0] + v_scaled + halo_l, bg[:, 1] + v_scaled + halo_r))
    ceiling = 10.0 ** (float(ceiling_db) / 20.0)
    knee = ceiling * 0.78
    mag = np.abs(out)
    over = mag > knee
    if np.any(over):
        sign = np.sign(out[over])
        excess = (mag[over] - knee) / max(ceiling - knee, 1e-6)
        out[over] = sign * (knee + (ceiling - knee) * np.tanh(excess))
    peak = float(np.max(np.abs(out)))
    if peak > ceiling:
        out = out * (ceiling / peak)
    return out.astype(np.float32)


def synthesize_from_cues(cue_data: dict, preset: str = "glass", seed: int = 77, skip_kinds: set | None = None) -> np.ndarray:
    preset = resolve_preset(preset)
    cfg = PRESETS[preset]
    dur = float(cue_data.get("dur", 6.0))
    scenes = cue_data.get("scenes", [])
    cues = cue_data.get("cues", [])

    # Derive topic-unique acoustic signature so different topics in the same style have distinct keys, tempos & chord rotations
    sig = _derive_topic_signature(cue_data, base_seed=seed)
    rng = np.random.default_rng(sig["seed"])

    if preset == "ink":
        stereo = synth_ink_guqin_bed(dur, scenes, cfg, rng, cues=cues, sig=sig)
    elif preset == "naturalist":
        stereo = synth_naturalist_chamber_bed(dur, scenes, cfg, rng, cues=cues, sig=sig)
    elif preset == "jazz":
        stereo = synth_jazz_swing_bed(dur, scenes, cfg, rng, cues=cues, sig=sig)
    elif preset == "clay":
        stereo = synth_clay_marimba_bed(dur, scenes, cfg, rng, cues=cues, sig=sig)
    elif preset == "paper":
        stereo = synth_paper_harp_bed(dur, scenes, cfg, rng, cues=cues, sig=sig)
    elif preset == "twilight":
        stereo = synth_twilight_celesta_bed(dur, scenes, cfg, rng, cues=cues, sig=sig)
    elif preset in ("mech", "terminal"):
        stereo = synth_industrial_mech_bed(dur, scenes, cfg, rng, cues=cues, sig=sig)
    else:
        stereo = synth_ambient_bed(dur, scenes, cfg, rng)

    foley_actions = {
        "blade_clique",
        "blade_cleave",
        "blood_splatter",
        "calligraphy_slam",
        "blade_sheathe",
        "cinnabar_seal_stamp",
        "taiko_impact",
        "qin_strumming_slash",
        "wave_surge",
        "sword_slash",
        "drink_sip",
        "brush_sweep",
        "foot_step",
        "boing_hop",
        "cartoon_boing",
        "quill_etch",
        "specimen_pin",
        "brass_ratchet",
        "scale_tilt",
        "astral_bloom",
        "paw_step",
        "ear_perk",
        "critter_hop",
        "water_ripple",
        "spirit_shimmer",
        "wood_creak",
        "page_turn",
        "popup_snap",
        "origami_wing",
        "paper_bell",
        "clay_squish",
        "liquid_pour",
        "wood_roll",
        "musicbox_chime",
        "ceramic_clink",
        "reel_projector",
        "curtain_whoosh",
        "gramophone_crank",
        "horn_blast",
        "bass_slap",
        "cymbal_clang",
        "slide_whistle",
        "xylophone_run",
    }

    room_size = 0.34 if preset in ("ink", "twilight", "naturalist") else 0.22
    room_wet = 0.14 if preset in ("ink", "twilight", "naturalist") else 0.08

    last_action_t = {}
    skip_kinds = skip_kinds or set()
    for idx, cue in enumerate(cues):
        t = float(cue.get("t", 0.0))
        kind = str(cue.get("kind", "card_enter"))
        if kind in skip_kinds:
            # A recorded sample replaces the synthetic foley for this kind (no flam, no double hit).
            continue
        label = str(cue.get("label", ""))
        intensity = float(cue.get("intensity", 0.75))
        pitch = float(cue.get("pitch", 1.0))
        start_sample = int(round(t * SR))

        # Per-event deterministic RNG seeded by CRC32 so every cue instance has organic micro-variation
        cue_crc = zlib.crc32(f"{preset}:{idx}:{kind}:{label}:{int(round(t * 1000))}".encode("utf-8")) & 0xFFFFFFFF
        cue_rng = np.random.default_rng(cue_crc)

        if "pan" in cue and cue["pan"] is not None:
            pan = float(np.clip(float(cue["pan"]), -0.75, 0.75))
        else:
            pan = float(np.clip(((cue_crc % 100) - 50) / 125.0, -0.40, 0.40))

        action = _resolve_cue_semantic_action(kind, label, preset)
        if action != "scene_cut":
            min_gap = 0.65 if action in ("paw_step", "critter_hop", "foot_step", "boing_hop") else (0.40 if preset == "twilight" else 0.24)
            if action in last_action_t and (t - last_action_t[action]) < min_gap:
                continue
            last_action_t[action] = t

        if action == "scene_cut":
            if preset == "ink":
                cut_mood = ""
                for s_idx, s in enumerate(scenes):
                    if abs(float(s.get("start", 0.0)) - t) < 0.08:
                        cut_mood = _infer_ink_scene_mood(s, s_idx, len(scenes), cues)
                        break
                if cut_mood == "kill_burst":
                    continue
                if cut_mood == "suspend":
                    intensity *= 0.45
            mono = synth_scene_cut(cfg, preset, intensity, idx, cue_rng)
            pan = 0.0
        elif action == "layer_float":
            mono = synth_layer_float(cfg, preset, intensity, idx, cue_rng)
        elif action == "count_tick":
            mono = synth_count_tick(cfg, preset, intensity, idx, cue_rng)
        elif action == "stroke_draw":
            mono = synth_stroke_draw(preset, intensity, cue_rng)
        elif action in foley_actions:
            mono = synth_runtime_foley(action, preset, intensity, cue_rng, pitch=pitch)
            if action in ("taiko_impact", "blade_cleave", "blade_clique", "blade_sheathe"):
                pan = 0.0
        else:
            mono = synth_card_enter(cfg, preset, intensity, idx, cue_rng)

        cue_st = pan_stereo_haas(mono, pan=pan)
        cue_st = add_studio_tail(cue_st, room_size=room_size, wet=room_wet)
        n_c = cue_st.shape[0]
        if start_sample < stereo.shape[0] and n_c > 0:
            s0 = max(0, start_sample)
            c0 = max(0, -start_sample)
            length = min(stereo.shape[0] - s0, n_c - c0)
            if length > 0:
                stereo[s0 : s0 + length] += cue_st[c0 : c0 + length]

    return master_bus(stereo, preset=preset, ceiling_db=-1.2)


def write_wav(path: Path, stereo: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm16 = np.clip(stereo * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm16.tobytes())


def default_cue_sheet() -> dict:
    """Fallback 4-scene cue sheet when --cues is omitted in standalone CLI invocations."""
    return {
        "dur": 14.0,
        "scenes": [
            {"index": 0, "id": "scene-01", "start": 0.0, "dur": 3.5, "end": 3.5},
            {"index": 1, "id": "scene-02", "start": 3.5, "dur": 3.7, "end": 7.2},
            {"index": 2, "id": "scene-03", "start": 7.2, "dur": 3.6, "end": 10.8},
            {"index": 3, "id": "scene-04", "start": 10.8, "dur": 3.2, "end": 14.0},
        ],
        "cues": [
            {"t": 0.0, "kind": "scene_cut", "intensity": 0.8},
            {"t": 0.18, "kind": "card_enter", "intensity": 0.78},
            {"t": 0.42, "kind": "stroke_draw", "intensity": 0.65},
            {"t": 1.1, "kind": "layer_float", "intensity": 0.85},
            {"t": 1.6, "kind": "drink_sip", "intensity": 0.72},
            {"t": 3.5, "kind": "scene_cut", "intensity": 1.0},
            {"t": 3.72, "kind": "card_enter", "intensity": 0.75},
            {"t": 3.95, "kind": "count_tick", "intensity": 0.55},
            {"t": 4.5, "kind": "sword_slash", "intensity": 0.85},
            {"t": 7.2, "kind": "scene_cut", "intensity": 1.0},
            {"t": 7.45, "kind": "card_enter", "intensity": 0.75},
            {"t": 7.8, "kind": "wave_surge", "intensity": 0.8},
            {"t": 8.3, "kind": "layer_float", "intensity": 0.85},
            {"t": 10.8, "kind": "scene_cut", "intensity": 1.0},
            {"t": 11.05, "kind": "card_enter", "intensity": 0.75},
            {"t": 12.0, "kind": "layer_float", "intensity": 0.85},
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Cue-driven procedural sound & physical modeling score synthesizer for StyleHop.")
    parser.add_argument("--cues", required=False, default=None, help="Path to cues.json extracted from window.CUES")
    parser.add_argument("--out", required=True, help="Output 48kHz stereo WAV path")
    parser.add_argument(
        "--preset",
        default="glass",
        help="Sonic palette preset (ink, jazz, clay, paper, twilight, glass, cyber, terminal, or style aliases)",
    )
    parser.add_argument("--samples", default=None, help="Style sample map (JSON): recorded one-shots layered over the score")
    parser.add_argument("--voice", default=None, help="48 kHz mono/stereo voice WAV to mix over the score")
    parser.add_argument("--duck-db", type=float, default=-10.0, help="Music gain reduction under speech (0 disables ducking)")
    parser.add_argument("--voice-gain", type=float, default=0.0, help="Voice gain in dB before the final limiter")
    parser.add_argument("--duck-attack", type=float, default=0.02, help="Sidechain attack in seconds")
    parser.add_argument("--duck-release", type=float, default=0.25, help="Sidechain release in seconds")
    args = parser.parse_args()

    if args.cues:
        cue_path = Path(args.cues)
        cue_data = json.loads(cue_path.read_text(encoding="utf-8"))
    else:
        cue_data = default_cue_sheet()

    preset = resolve_preset(cue_data.get("soundPreset") or args.preset)

    # Only retire a synthesized cue kind when the sample it maps to is actually on disk;
    # otherwise a missing cache would silently delete foley instead of falling back.
    sample_kinds: set = set()
    if args.samples:
        try:
            _map = json.loads(Path(args.samples).read_text(encoding="utf-8"))
            _idx_path = Path(_map.get("index", "../../../out/samples-cache/index.json"))
            if not _idx_path.is_absolute():
                _idx_path = (Path(args.samples).resolve().parent / _idx_path).resolve()
            if _idx_path.is_file():
                _idx = json.loads(_idx_path.read_text(encoding="utf-8"))
                _cache = Path(_idx.get("cache", _idx_path.parent))
                for kind, bind in (_map.get("map") or {}).items():
                    entry = (_idx.get("samples") or {}).get(bind.get("sample", ""))
                    if entry and (_cache / entry["file"]).is_file():
                        sample_kinds.add(kind)
        except Exception:
            sample_kinds = set()
    stereo = synthesize_from_cues(cue_data, preset=preset, skip_kinds=sample_kinds)
    samples_used: list[str] = []
    if args.samples:
        stereo, samples_used = overlay_samples(stereo, cue_data, args.samples)
    if args.voice:
        voice_path = Path(args.voice)
        if not voice_path.is_file():
            raise SystemExit(f"sound.py: voice file not found: {voice_path}")
        stereo = mix_voice_into(
            stereo,
            str(voice_path),
            duck_db=args.duck_db,
            voice_gain_db=args.voice_gain,
            attack=args.duck_attack,
            release=args.duck_release,
        )
    out_path = Path(args.out)
    write_wav(out_path, stereo)
    peak_db = 20.0 * np.log10(max(1e-9, float(np.max(np.abs(stereo)))))
    rms_db = 20.0 * np.log10(max(1e-9, float(np.sqrt(np.mean(stereo ** 2)))))
    print(
        json.dumps(
            {
                "out": str(out_path),
                "preset": preset,
                "dur": float(cue_data.get("dur", 0)),
                "cues": len(cue_data.get("cues", [])),
                "samples": sorted(set(samples_used)),
                "voice": str(Path(args.voice)) if args.voice else None,
                "peak_dbtp": round(peak_db, 2),
                "rms_dbfs": round(rms_db, 2),
            }
        )
    )


if __name__ == "__main__":
    main()
