---
name: world-07-rubberhose
description: World 07 · 1930s 橡皮管爵士舞台（35mm 胶片、钢琴键、黑音符、留声机 Boss、Iris-Out）。Use when building, reviewing, or debugging world_07_rubberhose / rubber-hose jazz style-hop.
version: 1.0.0
---

# World 07 · 橡皮管爵士舞台 (`world_07_rubberhose`)

- **定位**：1930s 35mm 赛璐璐；132 BPM 弹簧舞台、S 型钢琴键、拟人留声机 Boss、Iris-Out。
- **成片**：26.0s / 780f / 6 幕；Python/PyCairo + `styles/style_07_rubberhose.py`。
- **入口**：`sim_07_rubberhose.run_simulation` → `level_07_rubberhose.render_frame_from_state`；`build_world_07.py`；`audio_07_rubberhose.py`。
- **核心实现**：
  - `styles/style_07_rubberhose.py` 的 `draw_35mm_sprocket_borders`、`draw_vintage_theater_curtains`、`draw_stage_floorboards_and_spotlights`；
  - `draw_rubber_hose_piano_keyboard`、`draw_rubber_hose_gramophone`；
  - `draw_technicolor_jazz_soundwave_ring`、`apply_celluloid_film_grain_and_scratches`；
  - 本关 `draw_note_critter`、`draw_pop_icon`、`draw_35mm_countdown`、`draw_iris_out`。
- **节奏锚点**：0–4 胶片倒计时/舞台；4–8.8 黑音符；8.8–14.2 三连踩/彩环；14.0–15.0 黑胶盘 token；14.2–19.5 头槌；19.5–23 眩晕/旋涡；25.0–25.75 Iris-Out。
- **信物**：黑胶盘 token ✅（黑盘+金色中心；八分音符未独立）。
- **复用要点**：35mm 齿孔 + 胶片颗粒；钢琴键高度场；Boss 用橡皮管手臂 + 8 瓣喇叭；彩环用 Technicolor 三色。
- **坑**：星芒入喇叭没有清晰单星镜头；音频在 16.8–18.5s、22.8–24.1s 有近静音，若是设计停顿则保留。
- **验收**：15.5s 黑胶盘；21.8s Boss 眩晕；25.5s Iris-Out 收在喇叭口。

## 相关文件

- [`STORY.md`](../../worlds/world_07_rubberhose/STORY.md)
- [`build_world_07.py`](../../worlds/world_07_rubberhose/build_world_07.py)
- [`sim_07_rubberhose.py`](../../worlds/world_07_rubberhose/sim_07_rubberhose.py)
- [`level_07_rubberhose.py`](../../worlds/world_07_rubberhose/level_07_rubberhose.py)
- [`audio_07_rubberhose.py`](../../worlds/world_07_rubberhose/audio_07_rubberhose.py)
- [`../../styles/style_07_rubberhose.py`](../../styles/style_07_rubberhose.py)
