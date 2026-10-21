# -*- coding: utf-8 -*-
"""
corelib (Core Engineering Utilities)
===================================
极薄、完全风格中立（Style-Agnostic）的底层纯工具库。

设计铁律：
1. 基层核心只提供「纯数学缓动、2D 摄像机几何投影、多核/流式 FFmpeg 视频编码、质检缩略图拼接、DSP 声学滤波与母带导出」等纯工程工具。
2. 零审美/视觉预设：不包含任何固定的画面配色、字体排版（如底部金色高亮字幕）、或品牌片尾包装。
3. 适用于所有画风的程序化动画、物理模拟与音频合成。
"""

from .math_ops import (
    clamp,
    lerp,
    lerp_tuple,
    sub_progress,
    smoothstep,
    smootherstep,
    ease_in_cubic,
    ease_out_cubic,
    ease_in_out_cubic,
    ease_out_quint,
    ease_out_back,
    ease_out_elastic,
    spring_val,
    pulse_wave,
)
from .camera import (
    Camera2D,
    get_font,
    DEFAULT_FONT_MED,
    DEFAULT_FONT_REG,
)
from .pipeline import (
    render_video_streaming,
    render_video_parallel,
    generate_contact_sheet,
)
from .audio_dsp import (
    SR,
    db_to_amp,
    make_env,
    exp_decay,
    butter_filter,
    pink_noise,
    brown_noise,
    swept_bandpass_noise,
    pan_stereo,
    mix_into,
    build_reverb_ir,
    apply_reverb,
    modal_strike,
    synth_minnaert_bubble,
    quick_click,
    quick_thump,
    quick_whoosh,
    master_and_export_wav,
    detect_speech_window,
)

__all__ = [
    "clamp",
    "lerp",
    "lerp_tuple",
    "sub_progress",
    "smoothstep",
    "smootherstep",
    "ease_in_cubic",
    "ease_out_cubic",
    "ease_in_out_cubic",
    "ease_out_quint",
    "ease_out_back",
    "ease_out_elastic",
    "spring_val",
    "pulse_wave",
    "Camera2D",
    "get_font",
    "DEFAULT_FONT_MED",
    "DEFAULT_FONT_REG",
    "render_video_streaming",
    "render_video_parallel",
    "generate_contact_sheet",
    "SR",
    "db_to_amp",
    "make_env",
    "exp_decay",
    "butter_filter",
    "pink_noise",
    "brown_noise",
    "swept_bandpass_noise",
    "pan_stereo",
    "mix_into",
    "build_reverb_ir",
    "apply_reverb",
    "modal_strike",
    "synth_minnaert_bubble",
    "quick_click",
    "quick_thump",
    "quick_whoosh",
    "master_and_export_wav",
    "detect_speech_window",
]
