---
name: world-02-pixel
description: 16-Bit 像素横版大闯关（隐藏云梯砖、[?] 无敌星、乌云怪、旗杆烟花、像素币）。Use when building, reviewing, or debugging world_02_pixel / pixel platformer style-hop.
version: 1.0.0
---

# World 02 · 16-Bit 像素横版大闯关 (`world_02_pixel`)

- **定位**：Stardino 世界观第 2 关，5 屏宽16-Bit 横版横版关卡；星芒史莱姆从像素绿管登场，靠隐藏云梯砖解谜取得无敌星，撞飞乌云怪后抱旗杆、进城堡黑门撕开赛博裂缝。
- **成片规格**：28.0s / 840f / 6 幕；Python + Pillow + PyCairo（原生 320×180 像素画布 → 6× NEAREST 放大 → 1920×1080 平滑视口裁切）；音频 48kHz 立体声，-14.0 LUFS。
- **入口**：`sim_02_pixel.simulate_world_02()` → `level_02_pixel.render_frame_from_state(state)`；整片 `build_world_02.py`；配乐 `audio_02_pixel.py:render_world_02_audio(events, out_wav)`。
- **核心函数**：
  - `sim_02_pixel.simulate_world_02()`：确定性物理模拟，返回 `(frames_state, audio_events)`，30fps × 840 帧。
  - `level_02_pixel.render_frame_from_state(state)`：单帧总装（世界层 → 角色/机关 → 视口裁切 → HUD）。
  - `level_02_pixel.create_pixel_slime_sprite(...)`：3D 球面凝视耦合的像素史莱姆精灵，支持无敌彩虹残影。
  - `level_02_pixel.render_cyber_void_cutscene(viewport, cr, t, frame)`：Beat 6 城堡黑门内的紫青裂缝与数据方块。
  - `styles.style_02_pixel.get_static_world_background()`：Bayer 抖动天空 + 视差云层静态底图（缓存）。
  - `styles.style_02_pixel.draw_slime(ctx, ...)` / `draw_star(ctx, ...)`：Cairo 侧的角色与四角星绘制契约。
  - `audio_02_pixel.render_world_02_audio(events, out_wav)`：SNES 混合音色 BGM + 拟音，母带后写 PCM_24。
- **节奏锚点**：0.0–4.2 磷光方块拼管/史莱姆弹出；4.2–8.8 踩扁瓢虫/弹簧飞越尖刺坑；8.8–14.5 顶隐藏砖长云梯；14.5–19.2 登梯顶 `[?]` 砖、吃无敌星；19.2–24.8 撞飞两只乌云怪、抱旗杆、三朵烟花；24.8–28.0 吸入像素币、进城堡黑门、赛博裂缝。
- **信物**：16-Bit 像素游戏币（23.5s 前后在城堡门前旋转，24.8s 起被吸入）。
- **复用要点**：
  1. 一切机关走同一套事件驱动：`sim` 产出 `frames_state` 字段，`level` 只按字段画，不改物理；想换节奏只改 sim 的时间码。
  2. 原生低分辨率绘制 + `SCALE=6` NEAREST 放大 + 浮点裁切，是像素锐利且镜头不抖的关键；不要在 1920 画布上直接画像素。
  3. 隐藏砖用「每 0.5s 闪一粒白点」提示，`[?]` 砖与隐藏砖是两段解谜，缺一段玩家会卡死。
  4. HUD/飘字统一走 `get_pil_font()`，字体缺失时自动回退，不写死字体绝对路径。
- **已知坑**：
  1. 管道拼合完成后必须清零残留绿色粒子，否则管口上方会留绿点。
  2. 旗杆/烟花/金币在 22–24s 连续触发，时间码错 0.1s 就会叠帧。
  3. 史莱姆脚底必须严格贴地（`foot_y` 锚定），压缩形变时底部一行不能跟着缩放，否则穿地或悬空。
  4. 音频脚本在导入期就调用 `require_audio_upstream()`；未设 `LEMO_OPUSCAR_ROOT` / `EARSHOT_ROOT` 会直接报错，这是预期行为，不要改成静默降级。
- **验收抽帧**：
  - 6.65s：弹簧跳板压到最低，史莱姆在其上，瓢虫已被踩扁。
  - 16.07s：史莱姆顶 `[?]` 砖瞬间，金币与星芒 `✦` 喷出（画面 std ≈ 93）。
  - 23.5s：城堡黑门前像素币旋转，HUD 显示终局分数。
  - 26.5s：全屏黑底 + 紫青裂缝 / 数据方块，画面整体偏暗（mean ≈ 40）。

## 相关文件

- [`STORY.md`](../../worlds/world_02_pixel/STORY.md)
- [`sim_02_pixel.py`](../../worlds/world_02_pixel/sim_02_pixel.py)
- [`level_02_pixel.py`](../../worlds/world_02_pixel/level_02_pixel.py)
- [`audio_02_pixel.py`](../../worlds/world_02_pixel/audio_02_pixel.py)
- [`build_world_02.py`](../../worlds/world_02_pixel/build_world_02.py)
- [`../../slime_engine.py`](../../slime_engine.py)
- [`../../styles/style_02_pixel.py`](../../styles/style_02_pixel.py)
