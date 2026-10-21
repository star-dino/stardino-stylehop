# -*- coding: utf-8 -*-
"""
纯数学、缓动曲线与物理弹簧算子库（风格中立 / 零视觉设定）
供任何 2D / 3D / Shader / 故事动画或运镜轨迹计算直接调用。
"""

import math


def clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_tuple(c1: tuple, c2: tuple, t: float) -> tuple:
    t = clamp(t)
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(len(c1)))


def sub_progress(t: float, start: float, end: float) -> float:
    """计算时间 t 在区间 [start, end] 内的归一化进度 [0.0, 1.0]。"""
    if end <= start:
        return 1.0 if t >= end else 0.0
    return clamp((t - start) / (end - start), 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 0.0 if x < edge0 else 1.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 0.0 if x < edge0 else 1.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def ease_in_cubic(t: float) -> float:
    t = clamp(t)
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = clamp(t)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def ease_out_quint(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 5


def ease_out_back(t: float, overshoot: float = 1.4) -> float:
    t = clamp(t) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0


def ease_out_elastic(t: float, amplitude: float = 1.0, period: float = 0.35) -> float:
    t = clamp(t)
    if t <= 0.0 or t >= 1.0:
        return t
    s = period / math.tau * math.asin(1.0 / max(1.0, amplitude))
    return amplitude * (2.0 ** (-10.0 * t)) * math.sin((t - s) * math.tau / period) + 1.0


def spring_val(t: float, stiffness: float = 14.0, damping: float = 0.65) -> float:
    """物理欠阻尼弹簧阶跃响应 (0 -> 1，带自然过冲与衰减)。"""
    t = clamp(t)
    if t <= 0.0:
        return 0.0
    decay = math.exp(-stiffness * damping * t)
    d2 = max(0.01, 1.0 - damping * damping)
    omega = stiffness * math.sqrt(d2)
    return 1.0 - decay * (math.cos(omega * t) + (damping / math.sqrt(d2)) * math.sin(omega * t))


def pulse_wave(t_sec: float, freq: float = 1.8, lo: float = 0.85, hi: float = 1.15) -> float:
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(t_sec * freq * math.tau))
