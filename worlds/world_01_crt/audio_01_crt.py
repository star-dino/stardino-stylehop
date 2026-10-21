# -*- coding: utf-8 -*-
"""
World 01 · 矩阵终端序章 (audio_01_crt.py)
Re-scored & mastered with lemo-opuscar (PolyBLEP + 4-pole Moog ladder filter + tape wow +
sampled vibraphone/piano/strings/tubular_bells/harp/kalimba) and earshot (forge/bank + master).

Design Principles (Addressing "好吵的音效"):
  1. Warm Analog & Acoustic Palette: All synth oscillators pass through a 4-pole ladder
     lowpass filter (cutoff <= 2.2 kHz) with tape wow/flutter and 375ms low-passed ping-pong delay,
     layered with real acoustic samples (vibraphone, upright piano, harp, kalimba, strings).
  2. Narrative Breathing Room (Stop-Downs):
     - 0.0 ~ 4.0s: Sparse CRT boot hum + warm D-minor9 analog pad + gentle star wake-up.
     - 6.20 ~ 8.45s: Full musical STOP-DOWN when Slime bonks into the firewall, letting
       [?] question_pop and [!] idea_ping ring out in quiet, uncluttered space.
     - 8.80 ~ 12.50s: Minimal bass/pad pulse during the 3 mechanical key stomps so the
       ASMR key thocks ('fit/key/thock' + 'fit/key.space/thock_space') and vibraphone notes shine.
     - 12.53 ~ 26.0s: Warm compilation chord bloom, gentle zipline glide, and clean warp-pipe exit.
  3. Sidechain Ducking & Broadcast Mastering:
     - Music bus ducks (depth=0.45, tau=0.14s) on key story SFX hits.
     - Mastered via earshot `master.finish(mix, lufs=-14.0, ceiling=0.77)` -> -14.0 LUFS, -2.27 dBTP.
"""

import os
import sys
import math
import numpy as np
import soundfile as sf
from scipy import signal
from numba import njit

# Repository root derived from __file__ (no absolute paths)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from audio_deps import require_audio_upstream
require_audio_upstream()   # 缺失时抛出带安装指引的错误，绝不静默降级

from core.audio import sampler, pluck
from earshot.forge import bank
import master as earshot_master

SR = 48000
TOTAL_DURATION = 26.0
TOTAL_SAMPLES = int(round(TOTAL_DURATION * SR))

# =============================================================================
# 1. Pitch Helpers & Analog CRT Synth Primitives (@njit)
# =============================================================================

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
def polyblep_osc(freq, kind, pw=0.5):
    """Band-limited PolyBLEP oscillator (0=saw, 1=pulse, 2=tri)."""
    n = len(freq)
    y = np.zeros(n)
    ph = 0.0
    tri = 0.0
    for i in range(n):
        dt = freq[i] / SR
        if dt >= 0.5:
            dt = 0.49
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
        if kind == 0:
            v = 2.0 * ph - 1.0 - _blep(ph, dt)
        else:
            v = 1.0 if ph < pw else -1.0
            v += _blep(ph, dt)
            v -= _blep((ph - pw + 1.0) % 1.0, dt)
            if kind == 2:
                tri = 0.999 * tri + 4.0 * dt * v
                v = tri
        y[i] = v
    return y


@njit
def moog_ladder(x, cut, res):
    """4-pole nonlinear Moog ladder lowpass filter (classic analog topology)."""
    n = len(x)
    y = np.zeros(n)
    s0 = s1 = s2 = s3 = 0.0
    for i in range(n):
        fc = cut[i]
        if fc < 20.0:
            fc = 20.0
        if fc > 16000.0:
            fc = 16000.0
        g = math.tan(math.pi * fc / SR)
        G = g / (1.0 + g)
        u = math.tanh(x[i] - 4.0 * res * s3)
        v0 = G * (u - s0)
        y0 = v0 + s0
        s0 = y0 + v0
        v1 = G * (y0 - s1)
        y1 = v1 + s1
        s1 = y1 + v1
        v2 = G * (y1 - s2)
        y2 = v2 + s2
        s2 = y2 + v2
        v3 = G * (y2 - s3)
        y3 = v3 + s3
        s3 = y3 + v3
        y[i] = y3
    return y


@njit
def pingpong_delay(L, R, d_samp=18000, fb=0.36, mix=0.26):
    """Warm low-passed ping-pong stereo delay (375ms at 48kHz)."""
    n = len(L)
    oL = np.zeros(n)
    oR = np.zeros(n)
    bL = np.zeros(d_samp)
    bR = np.zeros(d_samp)
    p = 0
    lpL = 0.0
    lpR = 0.0
    for i in range(n):
        dL = bL[p]
        dR = bR[p]
        lpL = 0.35 * (L[i] + dR * fb) + 0.65 * lpL
        lpR = 0.35 * (R[i] + dL * fb) + 0.65 * lpR
        bL[p] = lpL
        bR[p] = lpR
        p = (p + 1) % d_samp
        oL[i] = L[i] + dL * mix
        oR[i] = R[i] + dR * mix
    return oL, oR


@njit
def lush_reverb(L, R, mix=0.22):
    """Schroeder/Freeverb stereo reverb with dark damping."""
    n = len(L)
    cs = (1557, 1617, 1491, 1422, 1277, 1356)
    aps = (225, 556, 441)
    oL = np.zeros(n)
    oR = np.zeros(n)
    for ch in range(2):
        x = L if ch == 0 else R
        acc = np.zeros(n)
        for ci in range(6):
            d = cs[ci] + ch * 23
            buf = np.zeros(d)
            p = 0
            lp = 0.0
            for i in range(n):
                v = buf[p]
                lp = 0.55 * v + 0.45 * lp
                buf[p] = x[i] + lp * 0.80
                p = (p + 1) % d
                acc[i] += v
        y = acc * (1.0 / 6.0)
        for ai in range(3):
            d = aps[ai] + ch * 19
            buf = np.zeros(d)
            p = 0
            for i in range(n):
                w = buf[p]
                v = -0.5 * y[i] + w
                buf[p] = y[i] + 0.5 * w
                p = (p + 1) % d
                y[i] = v
        if ch == 0:
            oL = x * (1.0 - mix) + y * mix
        else:
            oR = x * (1.0 - mix) + y * mix
    return oL, oR


def tape_wow(n, rate=0.45, depth=0.0020):
    t = np.arange(n, dtype=np.float64) / SR
    return 1.0 + depth * np.sin(2.0 * math.pi * rate * t) + (depth * 0.35) * np.sin(2.0 * math.pi * 2.9 * t + 0.8)


def pan_mono(sig: np.ndarray, pan: float = 0.0) -> np.ndarray:
    """Constant-power stereo panner (-1.0 left .. +1.0 right)."""
    x = np.asarray(sig, dtype=np.float64).ravel()
    angle = (np.clip(pan, -1.0, 1.0) + 1.0) * (math.pi / 4.0)
    gL = math.cos(angle)
    gR = math.sin(angle)
    out = np.zeros((len(x), 2), dtype=np.float64)
    out[:, 0] = x * gL
    out[:, 1] = x * gR
    return out


def mix_stereo(bus: np.ndarray, clip: np.ndarray, t_sec: float, gain: float = 1.0):
    """Mixes mono or stereo clip into stereo bus at t_sec (in seconds)."""
    start = max(0, int(round(t_sec * SR)))
    if start >= len(bus):
        return
    if clip.ndim == 1:
        st = pan_mono(clip, 0.0)
    else:
        st = clip
    end = min(len(bus), start + len(st))
    n = end - start
    if n > 0:
        bus[start:end] += st[:n] * float(gain)


def lowpass(sig: np.ndarray, cutoff_hz: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, min(cutoff_hz, SR * 0.45), btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, sig)


def synth_warm_pad(notes, dur_s: float, cutoff_hz: float = 1400.0, amp: float = 0.12) -> np.ndarray:
    """Warm stereo analog pad using PolyBLEP saw + triangle and 4-pole Moog ladder filter."""
    n = int(round(dur_s * SR))
    if n <= 0:
        return np.zeros((1, 2), dtype=np.float64)
    t = np.arange(n, dtype=np.float64) / SR
    wow = tape_wow(n, rate=0.42, depth=0.0022)
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)
    for i, nt in enumerate(notes):
        f0 = n2f(nt)
        f_arr_L = np.full(n, f0 * 0.997, dtype=np.float64) * wow
        f_arr_R = np.full(n, f0 * 1.003, dtype=np.float64) * wow
        wL = 0.55 * polyblep_osc(f_arr_L, 2) + 0.45 * polyblep_osc(f_arr_L, 0)
        wR = 0.55 * polyblep_osc(f_arr_R, 2) + 0.45 * polyblep_osc(f_arr_R, 0)
        pan_w = 0.35 + 0.30 * ((i % 2) * 2 - 1) * 0.5
        L += wL * (1.0 - pan_w * 0.4)
        R += wR * (0.6 + pan_w * 0.4)
    cut_env = np.full(n, cutoff_hz, dtype=np.float64) * (0.82 + 0.18 * np.sin(math.pi * t / max(dur_s, 0.01)))
    L = moog_ladder(L / max(len(notes), 1), cut_env, 0.18)
    R = moog_ladder(R / max(len(notes), 1), cut_env, 0.18)
    att = min(int(0.28 * SR), n // 3)
    rel = min(int(0.45 * SR), n // 3)
    env = np.ones(n, dtype=np.float64)
    if att > 0:
        env[:att] = np.linspace(0.0, 1.0, att) ** 1.4
    if rel > 0:
        env[-rel:] = np.linspace(1.0, 0.0, rel) ** 1.6
    out = np.column_stack([L * env * amp, R * env * amp])
    return out


def synth_warm_arp_pluck(note, dur_s: float = 0.28, cutoff_hz: float = 1750.0, amp: float = 0.11, pan: float = 0.0) -> np.ndarray:
    """Soft, warm low-passed analog pluck layered with gentle kalimba/vibraphone body."""
    n = int(round(dur_s * SR))
    f0 = n2f(note)
    f_arr = np.full(n, f0, dtype=np.float64) * tape_wow(n, rate=0.6, depth=0.0015)
    raw = 0.65 * polyblep_osc(f_arr, 2) + 0.35 * polyblep_osc(f_arr, 1, pw=0.35)
    t = np.arange(n, dtype=np.float64) / SR
    cut = cutoff_hz * np.exp(-t * 5.5) + 320.0
    filt = moog_ladder(raw, cut, 0.22)
    env = np.exp(-t * 7.5)
    att = min(int(0.008 * SR), n)
    if att > 0:
        env[:att] *= np.linspace(0.0, 1.0, att)
    sig = filt * env * amp
    return pan_mono(sig, pan)


# =============================================================================
# 2. Score / BGM Builder with Narrative Breathing Room & Stop-Downs
# =============================================================================

def build_crt_music_bus() -> np.ndarray:
    """
    Builds the 26.0s stereo music bus for World 01 with clear stop-downs:
      - 0.00 ~ 4.00s: Ambient CRT warm-up pad (Dm9 -> Bbmaj7), soft star shimmer
      - 4.00 ~ 6.20s: Gentle curiosity D-dorian pulse + upright bass
      - 6.20 ~ 8.45s: STOP-DOWN (near silence) for Firewall Bonk -> [?] -> [!]
      - 8.45 ~ 12.50s: Sparse bass heartbeat during the 3 mechanical key stomps
      - 12.53 ~ 18.00s: Compilation bloom (D major/Lydian warm pad + vibraphone + strings)
      - 18.00 ~ 25.20s: Zipline glide & triumphant Enter-key resolution, clean tail at 25.2s
    """
    L_bus = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    R_bus = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    acoustic_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float64)

    def add_pad(notes, t0, dur, cutoff=1350.0, amp=0.11):
        pad = synth_warm_pad(notes, dur, cutoff_hz=cutoff, amp=amp)
        s = int(round(t0 * SR))
        e = min(TOTAL_SAMPLES, s + len(pad))
        if e > s:
            L_bus[s:e] += pad[:e - s, 0]
            R_bus[s:e] += pad[:e - s, 1]

    # --- Section 1 (0.05 ~ 4.0s): Warm CRT Boot Pad ---
    add_pad(["D2", "A2", "D3", "F3", "A3", "E4"], 0.08, 3.85, cutoff=1150.0, amp=0.11)
    # Soft vibraphone shimmer when Slime wakes up at 3.60s
    for i, (nt, p) in enumerate([("D4", -0.25), ("A4", 0.20), ("E5", -0.15), ("F5", 0.25)]):
        vib = sampler.note("vibraphone", nt, dur=1.2, vel=0.34)
        mix_stereo(acoustic_bus, pan_mono(vib, p), 3.55 + i * 0.08, gain=0.45)

    # --- Section 2A (4.00 ~ 6.20s): Gentle Curiosity Arpeggio before Firewall ---
    add_pad(["D2", "A2", "F3", "A3", "C4"], 4.00, 2.25, cutoff=1250.0, amp=0.095)
    arp_seq_1 = ["D3", "A3", "C4", "D4", "F4", "E4", "C4", "A3"]
    step = 0.24
    t_cur = 4.05
    idx = 0
    while t_cur < 6.05:
        nt = arp_seq_1[idx % len(arp_seq_1)]
        pan_v = -0.30 if (idx % 2 == 0) else 0.30
        pl = synth_warm_arp_pluck(nt, dur_s=0.24, cutoff_hz=1550.0, amp=0.085, pan=pan_v)
        s = int(round(t_cur * SR))
        e = min(TOTAL_SAMPLES, s + len(pl))
        if e > s:
            L_bus[s:e] += pl[:e - s, 0]
            R_bus[s:e] += pl[:e - s, 1]
        t_cur += step
        idx += 1

    # --- Section 2B (6.20 ~ 8.45s): STOP-DOWN for Firewall Bonk, [?], and [!] ---
    # Only a barely-audible warm sub drone so the puzzle SFX have 100% clarity
    add_pad(["D2", "A2"], 6.25, 2.15, cutoff=520.0, amp=0.040)

    # --- Section 2C (8.45 ~ 12.50s): Sparse Key-Stomp Accompaniment ---
    # Soft pad + gentle contrabass pizzicato on the 3 hops before each key stomp
    add_pad(["Bb1", "F2", "D3", "F3", "A3"], 8.50, 2.00, cutoff=1050.0, amp=0.075)
    add_pad(["C2", "G2", "E3", "G3", "B3"], 10.50, 2.00, cutoff=1150.0, amp=0.080)
    for t_pizz, nt_pizz in [(8.55, "Bb1"), (9.85, "C2"), (11.15, "A1")]:
        pz = sampler.note("contrabass_pizz", nt_pizz, dur=0.55, vel=0.38)
        mix_stereo(acoustic_bus, pan_mono(pz, 0.0), t_pizz, gain=0.45)

    # --- Section 3 (12.53 ~ 18.00s): Compilation Bloom & Staircase Ascent ---
    add_pad(["D2", "A2", "D3", "F#3", "A3", "D4"], 12.53, 2.85, cutoff=1750.0, amp=0.125)
    add_pad(["G2", "D3", "G3", "B3", "D4", "F#4"], 15.35, 2.65, cutoff=1850.0, amp=0.125)

    # Acoustic piano + strings + tubular bell bloom at 12.53s
    for i, (nt, p) in enumerate([("D3", -0.3), ("A3", 0.3), ("D4", -0.2), ("F#4", 0.2), ("A4", 0.0)]):
        pno = sampler.note("piano", nt, dur=2.2, vel=0.42)
        mix_stereo(acoustic_bus, pan_mono(pno, p), 12.53 + i * 0.03, gain=0.48)
    vln = sampler.note("violins", "A4", dur=2.6, vel=0.32, attack=0.35)
    mix_stereo(acoustic_bus, pan_mono(vln, 0.15), 12.60, gain=0.38)
    vc = sampler.note("cellos", "D3", dur=2.6, vel=0.35, attack=0.30)
    mix_stereo(acoustic_bus, pan_mono(vc, -0.15), 12.60, gain=0.40)

    # Gentle 8th-note warm synth arpeggio during staircase climb (13.2 ~ 17.8s)
    arp_seq_2 = ["D3", "F#3", "A3", "D4", "E4", "F#4", "D4", "A3"]
    t_cur = 13.10
    idx = 0
    while t_cur < 17.80:
        # Dip slightly around monster_growl (15.85 ~ 16.30s)
        amp_scale = 0.45 if (15.80 <= t_cur <= 16.35) else 1.0
        nt = arp_seq_2[idx % len(arp_seq_2)]
        pan_v = -0.35 if (idx % 2 == 0) else 0.35
        pl = synth_warm_arp_pluck(nt, dur_s=0.22, cutoff_hz=1700.0, amp=0.075 * amp_scale, pan=pan_v)
        s = int(round(t_cur * SR))
        e = min(TOTAL_SAMPLES, s + len(pl))
        if e > s:
            L_bus[s:e] += pl[:e - s, 0]
            R_bus[s:e] += pl[:e - s, 1]
        t_cur += 0.22
        idx += 1

    # --- Section 4 (18.00 ~ 25.30s): Zipline Glide, Star Token & Enter Slam ---
    add_pad(["B1", "F#2", "B2", "D3", "F#3", "A3"], 18.00, 2.40, cutoff=1750.0, amp=0.115)
    add_pad(["G1", "D2", "G2", "B2", "D3", "G3"], 20.40, 2.55, cutoff=1800.0, amp=0.115)
    add_pad(["C2", "G2", "C3", "E3", "G3", "B3", "C4"], 23.00, 2.25, cutoff=1950.0, amp=0.130)

    # Warm soaring vibraphone & harp line on the zipline (18.25 ~ 20.1s)
    zip_notes = [(18.25, "F#4"), (18.60, "A4"), (18.95, "B4"), (19.30, "D5"), (19.65, "E5")]
    for t_z, nt_z in zip_notes:
        vb = sampler.note("vibraphone", nt_z, dur=0.75, vel=0.36)
        mix_stereo(acoustic_bus, pan_mono(vb, 0.2 * math.sin(t_z * 3.0)), t_z, gain=0.45)

    # Triumphant tubular bell + piano chord at 23.00s (mega_enter_slam)
    bell = sampler.note("tubular_bells", "C4", dur=1.8, vel=0.38)
    mix_stereo(acoustic_bus, pan_mono(bell, 0.0), 23.00, gain=0.42)
    for i, nt in enumerate(["C3", "G3", "C4", "E4", "G4"]):
        pno = sampler.note("piano", nt, dur=1.8, vel=0.42)
        mix_stereo(acoustic_bus, pan_mono(pno, (i - 2) * 0.15), 23.02 + i * 0.02, gain=0.45)

    # Apply ping-pong delay + lush reverb to the analog synth stem
    L_del, R_del = pingpong_delay(L_bus, R_bus, d_samp=18000, fb=0.34, mix=0.25)
    L_rev, R_rev = lush_reverb(L_del, R_del, mix=0.24)
    synth_bus = np.column_stack([L_rev, R_rev])

    # Apply gentle reverb to acoustic bus as well
    aL, aR = lush_reverb(acoustic_bus[:, 0], acoustic_bus[:, 1], mix=0.20)
    acoustic_wet = np.column_stack([aL, aR])

    music_bus = synth_bus + acoustic_wet
    return music_bus


# =============================================================================
# 3. Warm, Tactile, Non-Harsh Foley & Story SFX (earshot.forge.bank + sampler)
# =============================================================================

def render_audio(audio_events: list, out_wav_path: str, duration_s: float = 26.0) -> str:
    """
    Renders the 26.0s World 01 CRT audio track, applies sidechain ducking to the
    music bus on key story events, and masters to -14.0 LUFS / -2.27 dBTP.
    """
    music_bus = build_crt_music_bus()
    sfx_bus = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float64)
    duck_hits = []

    key_stomp_notes = ["D4", "F4", "A4"]
    key_stomp_idx = 0
    stair_notes = ["D4", "E4", "F#4", "A4"]
    stair_idx = 0

    for ev in audio_events:
        if isinstance(ev, dict):
            t_sec = float(ev.get("time", ev.get("t", 0.0)))
            name = str(ev.get("name", ""))
        else:
            t_sec = float(ev[0])
            name = str(ev[1])
        if t_sec < 0.0 or t_sec >= TOTAL_DURATION:
            continue

        if name == "crt_turn_on":
            # Warm sub thump + gentle 50Hz/100Hz CRT power-up hum (no piercing 15kHz whine!)
            sub, _ = bank.render("pro_sub_drop/soft", seed=101, dur=0.55, peak_db=-9.0)
            sw, _ = bank.render("fit/snap/switch_flip", seed=102, peak_db=-10.0)
            mix_stereo(sfx_bus, pan_mono(sw, -0.1), t_sec, gain=0.65)
            mix_stereo(sfx_bus, pan_mono(sub, 0.0), t_sec + 0.02, gain=0.65)
            duck_hits.append(t_sec)

        elif name == "star_descend":
            # Gentle descending harp + vibraphone cascade (low-passed, warm)
            notes = ["A5", "F5", "E5", "D5", "A4", "F4"]
            for i, nt in enumerate(notes):
                hp = sampler.note("harp", nt, dur=0.35, vel=0.34)
                hp = lowpass(hp, 2800.0)
                mix_stereo(sfx_bus, pan_mono(hp, -0.25 + 0.10 * i), t_sec + i * 0.085, gain=0.55)

        elif name == "star_strike":
            pop, _ = bank.render("pro_pop_in/deep", seed=103, peak_db=-7.0)
            vb = sampler.note("vibraphone", "D5", dur=0.65, vel=0.45)
            mix_stereo(sfx_bus, pan_mono(pop, 0.0), t_sec, gain=0.70)
            mix_stereo(sfx_bus, pan_mono(vb, 0.0), t_sec + 0.01, gain=0.55)
            duck_hits.append(t_sec)

        elif name == "wake_pop":
            plop, _ = bank.render("fit/pop/mouth_plop", seed=104, peak_db=-8.0)
            rnd, _ = bank.render("pro_pop_in/round", seed=105, peak_db=-8.0)
            mix_stereo(sfx_bus, pan_mono(plop, -0.1), t_sec, gain=0.65)
            mix_stereo(sfx_bus, pan_mono(rnd, 0.1), t_sec + 0.02, gain=0.60)
            duck_hits.append(t_sec)

        elif name == "slime_hop":
            plop, _ = bank.render("fit/pop/mouth_plop", seed=110 + int(t_sec * 10), peak_db=-10.0)
            plop = lowpass(plop, 2200.0)
            mix_stereo(sfx_bus, pan_mono(plop, -0.15), t_sec, gain=0.52)

        elif name == "firewall_alarm":
            # Warm, dark low-passed alert pulse (D3 -> A2), zero harsh sawtooth buzz
            n = int(0.42 * SR)
            t = np.arange(n, dtype=np.float64) / SR
            f_arr = np.where(t < 0.21, n2f("A3"), n2f("D3"))
            osc_w = polyblep_osc(f_arr, 2)
            filt = moog_ladder(osc_w, np.full(n, 1150.0), 0.20)
            env = np.sin(math.pi * t / 0.42) ** 0.8
            mix_stereo(sfx_bus, pan_mono(filt * env * 0.22, 0.15), t_sec, gain=0.75)
            duck_hits.append(t_sec)

        elif name == "wall_bonk":
            # Clean muffled thump + warm 2-tone descending synth (440 -> 293 Hz, LP 1.5 kHz)
            imp, _ = bank.render("pro_impact/short", seed=120, peak_db=-6.5)
            imp = lowpass(imp, 1600.0)
            n = int(0.32 * SR)
            t = np.arange(n, dtype=np.float64) / SR
            f_arr = np.linspace(410.0, 260.0, n)
            bonk_tone = moog_ladder(polyblep_osc(f_arr, 2), np.full(n, 1300.0), 0.25) * np.exp(-t * 9.5) * 0.26
            mix_stereo(sfx_bus, pan_mono(imp, 0.10), t_sec, gain=0.75)
            mix_stereo(sfx_bus, pan_mono(bonk_tone, 0.10), t_sec + 0.01, gain=0.75)
            duck_hits.append(t_sec)

        elif name == "question_pop":
            # Warm kalimba + rising vibraphone interval (A4 -> E5) in the quiet stop-down window
            kal, _ = bank.render("pluck/kalimba_soft", seed=130, peak_db=-7.5)
            vb1 = sampler.note("vibraphone", "A4", dur=0.40, vel=0.45)
            vb2 = sampler.note("vibraphone", "E5", dur=0.55, vel=0.50)
            mix_stereo(sfx_bus, pan_mono(kal, -0.10), t_sec, gain=0.70)
            mix_stereo(sfx_bus, pan_mono(vb1, -0.15), t_sec + 0.01, gain=0.65)
            mix_stereo(sfx_bus, pan_mono(vb2, 0.15), t_sec + 0.11, gain=0.68)
            duck_hits.append(t_sec)

        elif name == "idea_ping":
            # Clear warm chime ('pro_notify/ding_1822' + vibraphone D5 + harp A5)
            ding, _ = bank.render("pro_notify/ding_1822", seed=140, peak_db=-8.0)
            ding = lowpass(ding, 3200.0)
            vb = sampler.note("vibraphone", "D5", dur=0.65, vel=0.52)
            hp = sampler.note("harp", "A5", dur=0.65, vel=0.48)
            mix_stereo(sfx_bus, pan_mono(ding, 0.0), t_sec, gain=0.62)
            mix_stereo(sfx_bus, pan_mono(vb, -0.15), t_sec, gain=0.65)
            mix_stereo(sfx_bus, pan_mono(hp, 0.15), t_sec + 0.05, gain=0.60)
            duck_hits.append(t_sec)

        elif name.startswith("key_click"):
            # Satisfying ASMR mechanical keycap stomp: thock + thock_space + deep pop + vibraphone note
            thock, _ = bank.render("fit/key/thock", seed=150 + key_stomp_idx, peak_db=-6.0)
            space, _ = bank.render("fit/key.space/thock_space", seed=160 + key_stomp_idx, peak_db=-6.5)
            deep, _ = bank.render("pro_pop_in/deep", seed=170 + key_stomp_idx, peak_db=-8.0)
            nt = key_stomp_notes[key_stomp_idx % len(key_stomp_notes)]
            vb = sampler.note("vibraphone", nt, dur=0.55, vel=0.48)
            pan_k = -0.25 + 0.25 * (key_stomp_idx % 3)
            mix_stereo(sfx_bus, pan_mono(thock, pan_k), t_sec, gain=0.80)
            mix_stereo(sfx_bus, pan_mono(space, pan_k), t_sec + 0.008, gain=0.75)
            mix_stereo(sfx_bus, pan_mono(deep, pan_k), t_sec + 0.012, gain=0.65)
            mix_stereo(sfx_bus, pan_mono(vb, pan_k), t_sec + 0.015, gain=0.60)
            key_stomp_idx += 1
            duck_hits.append(t_sec)

        elif name == "compile_chord":
            # Warm notify chord + harp arpeggio
            notif, _ = bank.render("notify/m0", seed=180, peak_db=-7.5)
            notif = lowpass(notif, 2800.0)
            mix_stereo(sfx_bus, pan_mono(notif, 0.0), t_sec, gain=0.68)
            duck_hits.append(t_sec)

        elif name == "stair_rise":
            for i, nt in enumerate(["D4", "F#4", "A4", "D5"]):
                kl = sampler.note("kalimba", nt, dur=0.35, vel=0.40)
                mix_stereo(sfx_bus, pan_mono(kl, -0.2 + i * 0.12), t_sec + i * 0.07, gain=0.55)

        elif name.startswith("stair_hop"):
            plop, _ = bank.render("fit/pop/mouth_plop", seed=190 + stair_idx, peak_db=-9.0)
            nt = stair_notes[stair_idx % len(stair_notes)]
            kl = sampler.note("kalimba", nt, dur=0.32, vel=0.42)
            mix_stereo(sfx_bus, pan_mono(plop, 0.0), t_sec, gain=0.55)
            mix_stereo(sfx_bus, pan_mono(kl, 0.10), t_sec + 0.01, gain=0.52)
            stair_idx += 1

        elif name == "monster_growl":
            # Warm low cello/bass swell (no harsh sawtooth buzz)
            vc = sampler.note("cellos", "Eb2", dur=0.48, vel=0.48, attack=0.06)
            vc = lowpass(vc, 950.0)
            mix_stereo(sfx_bus, pan_mono(vc, 0.20), t_sec, gain=0.65)

        elif name == "jump_high":
            sw, _ = bank.render("fit/whoosh.short/bamboo_swish", seed=201, peak_db=-8.5)
            pop, _ = bank.render("pro_pop_in/round", seed=202, peak_db=-8.5)
            mix_stereo(sfx_bus, pan_mono(pop, 0.0), t_sec, gain=0.62)
            mix_stereo(sfx_bus, pan_mono(sw, 0.05), t_sec + 0.02, gain=0.58)

        elif name == "smash_impact":
            imp, _ = bank.render("pro_impact/deep", seed=210, peak_db=-6.0)
            imp = lowpass(imp, 1800.0)
            mix_stereo(sfx_bus, pan_mono(imp, 0.15), t_sec, gain=0.78)
            duck_hits.append(t_sec)

        elif name == "exp_chime":
            for i, nt in enumerate(["D5", "F#5", "A5", "D6"]):
                vb = sampler.note("vibraphone", nt, dur=0.45, vel=0.42)
                vb = lowpass(vb, 3000.0)
                mix_stereo(sfx_bus, pan_mono(vb, -0.15 + i * 0.10), t_sec + i * 0.055, gain=0.55)

        elif name == "zipline_latch":
            clk, _ = bank.render("fit/click/floss_lid", seed=220, peak_db=-8.0)
            mix_stereo(sfx_bus, pan_mono(clk, -0.20), t_sec, gain=0.62)

        elif name == "zipline_whoosh":
            wh, _ = bank.render("whoosh_big/cape", seed=221, dur=1.2, peak_db=-8.5)
            wh = lowpass(wh, 2000.0)
            mix_stereo(sfx_bus, pan_mono(wh, 0.0), t_sec, gain=0.62)

        elif name == "star_token_drop":
            kl, _ = bank.render("pluck/kalimba_ring", seed=230, peak_db=-8.0)
            mix_stereo(sfx_bus, pan_mono(kl, 0.20), t_sec, gain=0.60)

        elif name == "token_absorb_ding":
            ntf, _ = bank.render("notify/m2", seed=231, peak_db=-7.0)
            ntf = lowpass(ntf, 2900.0)
            hp = sampler.note("harp", "D5", dur=0.65, vel=0.46)
            mix_stereo(sfx_bus, pan_mono(ntf, 0.15), t_sec, gain=0.68)
            mix_stereo(sfx_bus, pan_mono(hp, 0.15), t_sec + 0.02, gain=0.58)
            duck_hits.append(t_sec)

        elif name == "charge_up":
            swl, _ = bank.render("whoosh_big/swell", seed=240, dur=0.48, peak_db=-8.5)
            swl = lowpass(swl, 2100.0)
            mix_stereo(sfx_bus, pan_mono(swl, 0.10), t_sec, gain=0.62)

        elif name == "rocket_leap":
            wh, _ = bank.render("whoosh_big/deep", seed=241, dur=0.52, peak_db=-7.5)
            wh = lowpass(wh, 2000.0)
            mix_stereo(sfx_bus, pan_mono(wh, 0.10), t_sec, gain=0.68)
            duck_hits.append(t_sec)

        elif name == "mega_enter_slam":
            sub, _ = bank.render("pro_sub_drop/soft", seed=250, dur=0.65, peak_db=-6.5)
            spc, _ = bank.render("fit/key.space/thock_space", seed=251, peak_db=-6.0)
            mix_stereo(sfx_bus, pan_mono(spc, 0.0), t_sec, gain=0.82)
            mix_stereo(sfx_bus, pan_mono(sub, 0.0), t_sec + 0.01, gain=0.75)
            duck_hits.append(t_sec)

        elif name == "pixel_crystallize":
            for i, nt in enumerate(["C4", "E4", "G4", "B4", "C5", "E5"]):
                hp = sampler.note("harp", nt, dur=0.45, vel=0.40)
                hp = lowpass(hp, 2800.0)
                mix_stereo(sfx_bus, pan_mono(hp, -0.2 + i * 0.08), t_sec + i * 0.06, gain=0.55)

        elif name in ("pipe_enter_warp", "pipe_enter"):
            # Warm 3-step classic warp portal descent (low-passed at 1.9 kHz) + soft sub whoosh
            for step_i in range(3):
                n_s = int(0.115 * SR)
                tt = np.arange(n_s, dtype=np.float64) / SR
                f0 = 560.0 - step_i * 85.0
                f_arr = f0 - 240.0 * (tt / 0.115)
                w = moog_ladder(polyblep_osc(f_arr, 1, pw=0.5), np.full(n_s, 1750.0), 0.22)
                env = np.sin(math.pi * tt / 0.115) ** 0.7
                mix_stereo(sfx_bus, pan_mono(w * env * 0.25, 0.20), t_sec + step_i * 0.135, gain=0.75)
            duck_hits.append(t_sec)

    # Apply subtle room reverb to SFX bus so Foley sits warmly in the CRT space
    sL, sR = lush_reverb(sfx_bus[:, 0], sfx_bus[:, 1], mix=0.16)
    sfx_bus = np.column_stack([sL, sR])

    # Balance music_bus vs sfx_bus so music provides a warm cushion and SFX sit
    # naturally in front via sidechain ducking without slamming the limiter
    m_pk = float(np.max(np.abs(music_bus)))
    if m_pk > 1e-9:
        music_bus = music_bus * (0.36 / m_pk)
    s_pk = float(np.max(np.abs(sfx_bus)))
    if s_pk > 1e-9:
        sfx_bus = sfx_bus * (0.34 / s_pk)

    # Sidechain ducking: duck the music bus by 45% (tau=0.14s) whenever a key story SFX hits
    sc_env = earshot_master.sidechain_times([(t, 1.0) for t in duck_hits], TOTAL_SAMPLES, depth=0.45, tau=0.14)
    mix = music_bus * sc_env + sfx_bus

    # Macro-dynamic contour: keep CRT boot (0~3.8s), firewall stop-down (6.15~8.45s),
    # and key-stomp puzzle (8.5~12.45s) gentler so the 12.53s compilation bloom & 23.0s Enter slam soar (LRA >= 5.5 LU)
    macro_env = np.ones(TOTAL_SAMPLES, dtype=np.float64)
    for t0, t1, g_val in [(0.0, 3.80, 0.58), (6.18, 8.45, 0.28), (8.45, 12.45, 0.62)]:
        i0, i1 = int(t0 * SR), int(t1 * SR)
        macro_env[i0:i1] = g_val
    macro_env = signal.sosfilt(signal.butter(1, 3.0, btype="low", fs=SR, output="sos"), macro_env)
    mix *= macro_env[:, None]

    # Master to exact -14.0 LUFS and <= -2.27 dBTP (ceiling=0.77) with zeroed tail
    mastered, info = earshot_master.finish(mix, lufs=-14.0, ceiling=0.77, comp=False, drive=1.06, air=0.10)
    os.makedirs(os.path.dirname(os.path.abspath(out_wav_path)), exist_ok=True)
    sf.write(out_wav_path, mastered, SR, subtype="PCM_24")
    print(f"[audio_01_crt] Mastered {out_wav_path}: {info}")
    return out_wav_path


# Alias for compatibility
generate_audio_01 = render_audio


if __name__ == "__main__":
    from sim_01_crt import run_simulation
    _, events = run_simulation()
    out_wav = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_01_crt.wav")
    render_audio(events, out_wav)
