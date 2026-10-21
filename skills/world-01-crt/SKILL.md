---
name: world-01-crt
description: CRT 曲面磷光字符世界 + 「敲命令即改变物理」机关链（ERR_403 防火墙、三连踩键编译、3D 窗口阶梯、光标滑索、巨型回车键）；用 PyCairo 逐帧渲染，适合复用 CRT 后处理、ASCII 角色材质与「状态快照 → 帧」管线。
version: 1.0.0
---

# World 01 · 矩阵终端序章 (`world_01_crt`)

- **定位**：单色磷光 CRT 显像管内部空间；终端文字是可交互实体——报错弹窗挡路、踩踏命令键会真的执行编译并改变世界物理，全屏唯一彩色是史莱姆与星芒。
- **成片规格**：26.0s / 780f（30fps，1920×1080）/ 6 幕；PyCairo + NumPy + Pillow 逐帧渲染；48kHz 立体声由 lemo-opuscar 合成、earshot 母带。
- **入口**：`sim_01_crt.run_simulation()` → `level_01_crt.render_frame_from_state(state)`；整片 `build_world_01.py`；音轨 `audio_01_crt.render_audio(events, out_wav_path)`。
- **核心函数**：
  - `styles.style_01_crt.render_world(cam_x, cam_y, t, state)` / `render_keyframe()`：不依赖 sim 的自洽场景渲染，可直接出单帧。
  - `style_01_crt.draw_slime(...)`：内部 ASCII 字符绑定局部 `(du, dv)`，随 `look` 做球面投影偏移；纯白胶囊眼、严格无嘴。
  - `style_01_crt.draw_star(...)`：四角凹弧星芒 `✦` 与三色字符尾迹。
  - `style_01_crt._apply_crt_post_processing(img)`：桶形坐标重映射 + RGB 色差 + 扫描线 + 3D 边框 + bloom，全部 CRT 观感的唯一出口。
  - `level_01_crt.render_frame_from_state(state)`：状态字典 → `(1080, 1920, 4)` BGRA 帧。
  - `level_01_crt.draw_firewall` / `draw_staircase_windows` / `draw_giant_enter_key`：机关实体在屏幕空间的绘制。
  - `sim_01_crt.run_simulation()`：780 帧状态 + 29 条绝对时间音频事件，姿态/视线/相机由 `SpringDamper1D/2D` 驱动。
  - `audio_01_crt.render_audio(events, out_wav_path)`：事件驱动 DSP、音乐/拟音双总线侧链 ducking，母带 -14.0 LUFS。
- **节奏锚点**：`0–1.0` 扫描线开机 → `2.8` 星芒砸中唤醒 → `4.8` 追星 → `6.2–8.5` 撞 `ERR_403`（音乐 stop-down）→ `8.5–13.8` 三连踩键 `./compile --jump --overclock`、进度 100% → `13.8–18.8` 窗口阶梯 + 砸碎 `ERR_404` → `18.8–22.5` 光标滑索、`21.0` 吸键帽 → `24.0–24.25` ENTER 砸底 → `25.25–25.5` 钻绿管。
- **信物**：磷光回车键帽 `[ ↵ ]`，`21.0s` 吸入（`draw_world_token(ctx, 1, ...)`）。
- **复用要点**：
  1. 状态与渲染解耦：sim 只产出 `frames_state[]`，`render_frame_from_state` 是纯函数，任意 `t` 可单帧复现；抽帧、并行分片都靠这条契约。
  2. CRT 观感集中在 `_apply_crt_post_processing`：几何先在常规 1920×1080 空间画完，最后一次性做桶形重映射 + 扫描线，不要逐元素做畸变。
  3. 角色材质用「局部坐标绑定」：字符按 `(du, dv)` 采样并随挤压/转头变换，否则会被拉成花纹。
  4. 音频事件是 `(t, kind)` 绝对时间列表，音乐床与拟音分总线，再按事件做 sidechain；改画面不必重写配乐结构。
- **已知坑**：
  1. `24.5–25.25s` 不是全屏粒子爆发，而是借反冲升起；「粒子拼成绿管」实际发生在 World 02 的 `0–0.5s`。
  2. ENTER 实际按压点比旧分镜早约 0.5s（`24.0–24.25`），按旧稿卡 `24.5` 会对不上画面。
  3. `audio_01_crt.py` 必须先 `require_audio_upstream()` 再 `from core.audio ...`；上游缺失时它直接抛错，这是有意设计（不静默生成无声轨）。
  4. CRT 畸变坐标图按 `(w, h, k)` 缓存，首帧一次预计算、内存占用明显；多进程分片时每个进程各自预热，不要按帧重建缓存。
- **验收抽帧**：`2.5s` 休眠态史莱姆（单色暗绿字符、无三色极光）+ 左下 `stardino@crt:~$` 提示符，全屏仅磷光绿；`10.2s` 彩色 ASCII 史莱姆踩键，`[ ./compile ]` 键列与 `ERR_403` 弹窗同屏；`21.0s` 光标滑索 + 浮起的 `[↵]` 键帽信物 + 巨型 `[ ENTER ↵ ]`；`24.2s` 键帽压到底、史莱姆在其正上方。

## 相关文件

- [`STORY.md`](../../worlds/world_01_crt/STORY.md)
- [`sim_01_crt.py`](../../worlds/world_01_crt/sim_01_crt.py)
- [`level_01_crt.py`](../../worlds/world_01_crt/level_01_crt.py)
- [`audio_01_crt.py`](../../worlds/world_01_crt/audio_01_crt.py)
- [`build_world_01.py`](../../worlds/world_01_crt/build_world_01.py)
- [`../../slime_engine.py`](../../slime_engine.py)
- [`../../styles/style_01_crt.py`](../../styles/style_01_crt.py)
