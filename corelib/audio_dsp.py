# -*- coding: utf-8 -*-
"""
纯工具类：数字信号处理 (DSP)、程序化物理拟音 (Foley) 原语与母带导出工具。
融合了：
- 高精度滤波器、包络、混响 IR、模态打击、气泡共振、ITD 立体声与 -1.5dBFS 归一化母带
- lemo-opuscar/core/audio/sfx.py 的轻量快捷拟音原语 (click, clack, crash, whoosh, thump, ding, pop)
- 语音有效气口检测 (detect_speech_window)
"""

import os
import re
import wave
import subprocess
import numpy as np
from scipy import signal

SR = 48000
_DEFAULT_RNG = np.random.default_rng(20261015)


# =============================================================================
# 1. 基础滤波器、包络与噪声源
# =============================================================================

def db_to_amp(db: float) -> float:
    return 10.0 ** (db / 20.0)


def make_env(
    n: int,
    attack_s: float,
    release_s: float,
    hold_level: float = 1.0,
    curve: float = 1.0,
    sr: int = SR,
) -> np.ndarray:
    """平滑余弦起音/释音包络（零爆音）。"""
    env = np.full(n, hold_level, dtype=np.float64)
    n_att = min(int(attack_s * sr), n)
    n_rel = min(int(release_s * sr), n - n_att)
    if n_att > 0:
        t = np.linspace(0.0, 1.0, n_att, endpoint=False)
        env[:n_att] = ((0.5 - 0.5 * np.cos(np.pi * t)) ** curve) * hold_level
    if n_rel > 0:
        t = np.linspace(0.0, 1.0, n_rel, endpoint=False)
        env[n - n_rel:] = ((0.5 + 0.5 * np.cos(np.pi * t)) ** curve) * hold_level
    return env


def exp_decay(n: int, tau_s: float, attack_s: float = 0.002, sr: int = SR) -> np.ndarray:
    """快速平滑起音 + 自然指数物理衰减包络。"""
    t = np.arange(n, dtype=np.float64) / sr
    env = np.exp(-t / max(tau_s, 1e-5))
    n_att = min(int(attack_s * sr), n)
    if n_att > 1:
        att = 0.5 - 0.5 * np.cos(np.pi * np.arange(n_att) / n_att)
        env[:n_att] *= att
    n_tail = min(int(0.002 * sr), n)
    if n_tail > 1:
        env[-n_tail:] *= np.linspace(1.0, 0.0, n_tail)
    return env


def butter_filter(sig: np.ndarray, cutoff, btype: str = "low", order: int = 4, sr: int = SR) -> np.ndarray:
    nyq = 0.5 * sr
    if isinstance(cutoff, (list, tuple, np.ndarray)):
        wn = [np.clip(c / nyq, 1e-4, 0.999) for c in cutoff]
    else:
        wn = np.clip(cutoff / nyq, 1e-4, 0.999)
    sos = signal.butter(order, wn, btype=btype, output="sos")
    return signal.sosfilt(sos, sig)


def pink_noise(n: int, rng: np.random.Generator = None, sr: int = SR) -> np.ndarray:
    """1/f 粉红噪声。"""
    rng = rng or _DEFAULT_RNG
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    scale = 1.0 / np.maximum(np.sqrt(freqs), 1.0)
    scale[0] = 0.0
    out = np.fft.irfft(spec * scale, n=n)
    std = np.std(out)
    return out / (std if std > 1e-9 else 1.0)


def brown_noise(n: int, rng: np.random.Generator = None, sr: int = SR) -> np.ndarray:
    """1/f^2 布朗噪声（已做 25Hz 高通消除直流漂移）。"""
    rng = rng or _DEFAULT_RNG
    white = rng.standard_normal(n)
    out = np.cumsum(white)
    out = butter_filter(out, 25.0, btype="high", order=2, sr=sr)
    std = np.std(out)
    return out / (std if std > 1e-9 else 1.0)


def swept_bandpass_noise(
    n: int,
    f_start: float,
    f_end: float,
    q: float = 2.5,
    rng: np.random.Generator = None,
    curve: float = 1.0,
    noise_type: str = "pink",
    sr: int = SR,
) -> np.ndarray:
    """平滑时变带通扫频噪声（适合运动呼啸 whoosh、气流与镜头推进）。"""
    rng = rng or _DEFAULT_RNG
    src = pink_noise(n, rng, sr=sr) if noise_type == "pink" else rng.standard_normal(n)
    out = np.zeros(n, dtype=np.float64)
    hop = 512
    win_len = 1024
    win = np.hanning(win_len)
    nyq = 0.5 * sr

    n_frames = max(1, (n - win_len) // hop + 1)
    for i in range(n_frames):
        s = i * hop
        e = min(s + win_len, n)
        chunk_len = e - s
        if chunk_len < 64:
            break
        frac = (s + 0.5 * chunk_len) / max(n, 1)
        frac_curved = frac ** curve
        fc = f_start * ((f_end / max(f_start, 1.0)) ** frac_curved)
        bw = max(fc / max(q, 0.5), 30.0)
        low = np.clip((fc - 0.5 * bw) / nyq, 0.001, 0.98)
        high = np.clip((fc + 0.5 * bw) / nyq, low + 0.002, 0.995)
        sos = signal.butter(2, [low, high], btype="band", output="sos")
        pad_s = max(0, s - 256)
        filtered = signal.sosfilt(sos, src[pad_s:e])[s - pad_s:]
        out[s:e] += filtered * win[:chunk_len]

    peak = np.max(np.abs(out))
    return out / (peak if peak > 1e-9 else 1.0)


# =============================================================================
# 2. 空间声像、混音与卷积混响 (Stereo Panning, Mixing & Reverb IR)
# =============================================================================

def pan_stereo(mono: np.ndarray, pan=0.0, itd_max_s: float = 0.00028, sr: int = SR) -> np.ndarray:
    """等功率立体声声像定位 + 双耳时间差 (ITD)。pan 范围 [-1.0 左, +1.0 右]，支持标量或等长数组。"""
    n = len(mono)
    p = np.clip(np.asarray(pan, dtype=np.float64), -1.0, 1.0)
    theta = (p + 1.0) * (np.pi / 4.0)
    gain_l = np.cos(theta)
    gain_r = np.sin(theta)

    if np.ndim(p) == 0 and abs(float(p)) > 0.05 and itd_max_s > 0:
        shift = int(abs(float(p)) * itd_max_s * sr)
        if 0 < shift < n:
            delayed = np.zeros_like(mono)
            delayed[shift:] = mono[:-shift]
            if float(p) < 0:
                return np.column_stack((mono * gain_l, delayed * gain_r))
            return np.column_stack((delayed * gain_l, mono * gain_r))

    return np.column_stack((mono * gain_l, mono * gain_r))


def mix_into(master: np.ndarray, clip: np.ndarray, start_s: float, gain: float = 1.0, pan: float = None, sr: int = SR):
    """将单声道或立体声片段安全混入立体声主总线 `master` 的 `start_s` 秒位置。"""
    idx0 = int(round(start_s * sr))
    if clip.ndim == 1:
        clip = pan_stereo(clip, pan if pan is not None else 0.0, sr=sr)
    n_clip = clip.shape[0]
    if idx0 < 0:
        clip = clip[-idx0:]
        idx0 = 0
        n_clip = clip.shape[0]
    if idx0 >= master.shape[0] or n_clip <= 0:
        return
    idx1 = min(idx0 + n_clip, master.shape[0])
    master[idx0:idx1] += clip[:idx1 - idx0] * gain


def build_reverb_ir(
    rt60: float = 1.65,
    damp_hz: float = 6800.0,
    early_ms: list = None,
    predelay_ms: float = 10.0,
    rng: np.random.Generator = None,
    sr: int = SR,
) -> np.ndarray:
    """合成无金属振铃感的立体声早期反射 + 扩散混响脉冲响应 (IR)。"""
    rng = rng or _DEFAULT_RNG
    if early_ms is None:
        early_ms = [14.0, 23.5, 37.0, 54.0, 79.0]
    n_ir = int((rt60 * 1.35 + predelay_ms * 0.001) * sr)
    ir_l = np.zeros(n_ir, dtype=np.float64)
    ir_r = np.zeros(n_ir, dtype=np.float64)

    for i, ms in enumerate(early_ms):
        idx_l = int((predelay_ms + ms) * 0.001 * sr)
        idx_r = int((predelay_ms + ms * 1.07 + 1.3) * 0.001 * sr)
        gain = (0.65 ** (i * 0.45)) * (1.0 if i % 2 == 0 else -0.85)
        if idx_l < n_ir:
            ir_l[idx_l] += gain
        if idx_r < n_ir:
            ir_r[idx_r] += gain * 0.92

    tail_start = int(predelay_ms * 0.001 * sr)
    n_tail = n_ir - tail_start
    t = np.arange(n_tail, dtype=np.float64) / sr
    decay = np.exp(-6.9078 * t / max(rt60, 0.05))
    onset = 1.0 - np.exp(-t / 0.018)

    noise_l = butter_filter(pink_noise(n_tail, rng, sr=sr), [85.0, damp_hz], btype="band", order=2, sr=sr)
    noise_r = butter_filter(pink_noise(n_tail, rng, sr=sr), [85.0, damp_hz], btype="band", order=2, sr=sr)

    ir_l[tail_start:] += noise_l * decay * onset * 0.28
    ir_r[tail_start:] += noise_r * decay * onset * 0.28

    ir = np.column_stack((ir_l, ir_r))
    norm = np.sqrt(np.sum(ir[:, 0] ** 2) + 1e-9)
    return ir / norm


def apply_reverb(stereo_sig: np.ndarray, ir: np.ndarray, wet: float = 0.35, dry: float = 1.0) -> np.ndarray:
    """使用 FFT 卷积为信号添加立体声混响。"""
    if stereo_sig.ndim == 1:
        stereo_sig = np.column_stack((stereo_sig, stereo_sig))
    wet_l = signal.fftconvolve(stereo_sig[:, 0], ir[:, 0], mode="full")
    wet_r = signal.fftconvolve(stereo_sig[:, 1], ir[:, 1], mode="full")
    n_out = len(wet_l)
    out = np.zeros((n_out, 2), dtype=np.float64)
    n_in = stereo_sig.shape[0]
    out[:n_in] += stereo_sig * dry
    out[:, 0] += wet_l * wet
    out[:, 1] += wet_r * wet
    return out


# =============================================================================
# 3. 物理模态合成与快捷 Foley 拟音原语 (Modal & Quick Foley Primitives)
# =============================================================================

def modal_strike(
    duration_s: float,
    freqs: list,
    amps: list,
    decays: list,
    freq_drop: float = 0.0,
    drop_tau: float = 0.025,
    sr: int = SR,
) -> np.ndarray:
    """通用物理模态共振打击合成（可调参模拟水晶、岩石、金属、木块或钟琴）。"""
    n = int(round(duration_s * sr))
    t = np.arange(n, dtype=np.float64) / sr
    out = np.zeros(n, dtype=np.float64)
    for f, a, d in zip(freqs, amps, decays):
        if freq_drop > 0.0:
            inst_f = f * (1.0 + freq_drop * np.exp(-t / drop_tau))
            phase = np.cumsum(2.0 * np.pi * inst_f / sr)
        else:
            phase = 2.0 * np.pi * f * t
        out += a * np.sin(phase) * exp_decay(n, d, attack_s=0.0008, sr=sr)
    return out


def synth_minnaert_bubble(f0: float, dur_s: float = 0.024, chirp_ratio: float = 1.42, sr: int = SR) -> np.ndarray:
    """物理 Minnaert 气泡声学共振（流体/水滴/入水音效基元）。"""
    n = int(round(dur_s * sr))
    t = np.arange(n, dtype=np.float64) / sr
    f_t = f0 * (1.0 + (chirp_ratio - 1.0) * ((t / max(dur_s, 1e-4)) ** 1.4))
    phase = np.cumsum(2.0 * np.pi * f_t / sr)
    env = (np.sin(np.pi * (t / dur_s)) ** 0.7) * np.exp(-t / (dur_s * 0.48))
    return np.sin(phase) * env


def quick_click(pitch: float = 1.0, gain: float = 1.0, sr: int = SR) -> np.ndarray:
    """短促清脆的机械扣合/点击声。"""
    d = 0.06
    n = int(round(d * sr))
    tt = np.arange(n, dtype=np.float64) / sr
    tr = butter_filter(_DEFAULT_RNG.standard_normal(n), 2500.0, btype="high", order=2, sr=sr) * exp_decay(n, 0.0015, sr=sr)
    res = modal_strike(d, [2900 * pitch, 4600 * pitch, 1500 * pitch], [0.6, 0.4, 0.35], [0.012, 0.008, 0.018], sr=sr)
    body = np.sin(2 * np.pi * 190 * pitch * tt) * exp_decay(n, 0.01, sr=sr) * 0.5
    sig = tr * 0.8 + res + body
    m = np.max(np.abs(sig))
    return (sig / m if m > 1e-9 else sig) * gain


def quick_thump(f0: float = 70.0, gain: float = 1.0, sr: int = SR) -> np.ndarray:
    """低沉物理撞击/重物落地声。"""
    d = 0.35
    n = int(round(d * sr))
    tt = np.arange(n, dtype=np.float64) / sr
    sub = np.sin(2 * np.pi * f0 * tt * (1.0 - 0.3 * tt)) * exp_decay(n, 0.07, sr=sr)
    punch = butter_filter(_DEFAULT_RNG.standard_normal(n), 300.0, btype="low", order=2, sr=sr) * exp_decay(n, 0.02, sr=sr) * 0.5
    sig = sub + punch
    m = np.max(np.abs(sig))
    return (sig / m if m > 1e-9 else sig) * gain


def quick_whoosh(dur_s: float = 0.35, f_start: float = 400.0, f_end: float = 2400.0, gain: float = 1.0, sr: int = SR) -> np.ndarray:
    """快速平滑扫频呼啸声。"""
    n = int(round(dur_s * sr))
    tt = np.arange(n, dtype=np.float64) / sr
    sw = swept_bandpass_noise(n, f_start, f_end, q=2.2, sr=sr)
    env = np.sin(np.pi * tt / dur_s) ** 2
    sig = sw * env
    m = np.max(np.abs(sig))
    return (sig / m if m > 1e-9 else sig) * gain


# =============================================================================
# 4. 母带归一化导出与 TTS 语音气口检测工具
# =============================================================================

def master_and_export_wav(
    master: np.ndarray,
    out_wav_path: str,
    target_peak_dbfs: float = -1.5,
    silent_windows_s: list[tuple[float, float]] = None,
    tail_fade_start_s: float = None,
    sr: int = SR,
    seed: int = 20261015,
) -> dict:
    """
    工业级母带处理并导出 16-bit 立体声 PCM WAV：
    - 18Hz 高通消除超低频直流偏移
    - 软膝饱和胶合 (tanh soft-knee glue)
    - 精确峰值归一化到 `target_peak_dbfs` (默认 -1.5 dBFS，零削波)
    - TPDF 抖动量化
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_wav_path)), exist_ok=True)
    rng = np.random.default_rng(seed)

    buf = np.array(master, dtype=np.float64, copy=True)
    if buf.ndim == 1:
        buf = np.column_stack((buf, buf))

    for ch in range(2):
        buf[:, ch] = butter_filter(buf[:, ch], 18.0, btype="high", order=2, sr=sr)
        buf[:, ch] -= np.mean(buf[:, ch])

    if tail_fade_start_s is not None:
        idx_tail = min(buf.shape[0], int(round(tail_fade_start_s * sr)))
        fade_n = min(idx_tail, int(0.15 * sr))
        if fade_n > 0:
            fade_w = np.linspace(1.0, 0.0, fade_n)
            buf[idx_tail - fade_n:idx_tail, 0] *= fade_w
            buf[idx_tail - fade_n:idx_tail, 1] *= fade_w
        buf[idx_tail:] = 0.0

    if silent_windows_s:
        for s0, s1 in silent_windows_s:
            i0 = max(0, int(round(s0 * sr)))
            i1 = min(buf.shape[0], int(round(s1 * sr)))
            buf[i0:i1] = 0.0

    peak_raw = np.max(np.abs(buf))
    if peak_raw > 1e-9:
        buf /= peak_raw
    buf = np.tanh(1.18 * buf) / np.tanh(1.18)

    buf[:, 0] -= np.mean(buf[:, 0])
    buf[:, 1] -= np.mean(buf[:, 1])

    if silent_windows_s:
        for s0, s1 in silent_windows_s:
            i0 = max(0, int(round(s0 * sr)))
            i1 = min(buf.shape[0], int(round(s1 * sr)))
            buf[i0:i1] = 0.0
    if tail_fade_start_s is not None:
        idx_tail = min(buf.shape[0], int(round(tail_fade_start_s * sr)))
        buf[idx_tail:] = 0.0

    target_peak = db_to_amp(target_peak_dbfs)
    current_peak = np.max(np.abs(buf))
    if current_peak > 1e-9:
        buf *= target_peak / current_peak

    dither = (rng.uniform(-0.5, 0.5, buf.shape) + rng.uniform(-0.5, 0.5, buf.shape)) / 32768.0
    if silent_windows_s:
        for s0, s1 in silent_windows_s:
            i0 = max(0, int(round(s0 * sr)))
            i1 = min(buf.shape[0], int(round(s1 * sr)))
            dither[i0:i1] = 0.0
    if tail_fade_start_s is not None:
        idx_tail = min(buf.shape[0], int(round(tail_fade_start_s * sr)))
        dither[idx_tail:] = 0.0

    pcm16 = np.clip(np.round((buf + dither) * 32767.0), -32767, 32767).astype(np.int16)
    with wave.open(out_wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())

    max_int = int(np.max(np.abs(pcm16)))
    final_peak_dbfs = 20.0 * np.log10(max(max_int, 1) / 32767.0)
    return {
        "path": out_wav_path,
        "samples": int(pcm16.shape[0]),
        "duration_s": round(pcm16.shape[0] / float(sr), 4),
        "peak_dbfs": round(float(final_peak_dbfs), 2),
        "dc_offset_l": round(float(np.mean(pcm16[:, 0]) / 32767.0), 6),
        "dc_offset_r": round(float(np.mean(pcm16[:, 1]) / 32767.0), 6),
    }


def detect_speech_window(audio_path: str) -> tuple[float, float, list[dict]]:
    """
    辅助工具（用于带 TTS 旁白的视频）：
    利用 ffmpeg silencedetect 仅识别句首空白 (onset) 与句尾空白 (off)，
    保留句内原生自然停顿与字尾 0.16s 余韵，不切碎句内呼吸。
    """
    dur_proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio_path)],
        capture_output=True, text=True, check=True,
    )
    dur = float(dur_proc.stdout.strip())

    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(audio_path), "-af", "silencedetect=noise=-40dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    starts, ends = [], []
    for line in proc.stderr.splitlines():
        if "silence_start:" in line:
            starts.append(float(line.split("silence_start:")[1].strip().split()[0]))
        elif "silence_end:" in line:
            ends.append(float(line.split("silence_end:")[1].strip().split()[0]))

    onset, off = 0.0, dur
    if starts and starts[0] == 0.0 and ends:
        onset = ends[0]
    if ends and abs(ends[-1] - dur) < 0.06 and len(starts) >= len(ends):
        off = starts[-1]

    onset_safe = max(0.0, onset - 0.04)
    off_safe = min(dur, off + 0.16)

    natural_pauses = []
    for s, e in zip(starts, ends):
        if s > onset + 0.08 and e < off - 0.08 and (e - s) >= 0.15:
            natural_pauses.append({
                "start_in_clip_sec": round(s - onset_safe, 4),
                "end_in_clip_sec": round(e - onset_safe, 4),
                "natural_silence_sec": round(e - s, 4),
            })

    return onset_safe, off_safe, natural_pauses
