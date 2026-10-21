# `corelib/` —— 极薄纯工具基层

## 核心设计原则（必读）

1. **基层绝对中立，只做纯工程提效，零审美预设**：
   - 顶层模块（`math_ops.py`、`camera.py`、`pipeline.py`、`audio_dsp.py`）属于**纯工具层**。
   - **不包含**任何固定画面风格、背景色、字幕样式（如底部金色关键词高亮）、或品牌片尾包装（品牌资产由后期自由合入，不写入基层）。
   - 目的是省去每次重复编写 FFmpeg 多核并发推流、缓动公式、摄像机坐标投影、DSP 滤波器与音频防削波母带导出的 Token 消耗，把 100% 的创作自由度留给具体剧本。
2. **纯工具模块划分**：
   - 仅提供数学插值、2D 摄像机投影、FFmpeg 多核并发编码管线与声学 DSP 原语。

---

## 目录结构与职责边界

```text
corelib/
├── __init__.py                   # 导出纯工具层 API（零视觉预设）
├── math_ops.py                   # 纯数学与物理缓动：clamp, lerp, smoothstep, ease_out_back, spring_val 等
├── camera.py                     # 纯几何 2D 虚拟摄像机：Camera2D (推拉摇移/物理震动/世界↔屏幕坐标正逆投影) + 字体缓存 get_font
├── pipeline.py                   # 纯编码与质检管线：单流推流、8核多进程分片并发推流 (render_video_parallel)、缩略图网格 (generate_contact_sheet)
└── audio_dsp.py                  # 纯声学 DSP 工具：滤波器、包络、粉红/布朗噪声、混响 IR、模态共振、-1.5dBFS 母带导出、TTS 气口检测

---

## 快速调用方式

在任意渲染或音频脚本中，只需将仓库根目录加入 `sys.path` 即可直接调用纯工具层：

```python
from corelib import (
    clamp, lerp, smoothstep, smootherstep, ease_out_cubic, ease_out_back, spring_val,
    Camera2D, get_font,
    render_video_streaming, render_video_parallel, generate_contact_sheet,
    SR, make_env, exp_decay, butter_filter, pink_noise, brown_noise,
    pan_stereo, mix_into, build_reverb_ir, apply_reverb, modal_strike, master_and_export_wav,
)

```
