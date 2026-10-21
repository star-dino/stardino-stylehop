---
name: world-06-stainedglass
description: World 06 · 哥特玫瑰彩窗圣殿（棱镜色散、4 级玻璃台阶、拉绳敲钟、声波环、七彩桥、玫瑰窗）。Use when building, reviewing, or debugging world_06_stainedglass / stained-glass style-hop.
version: 1.0.0
---

# World 06 · 哥特玫瑰彩窗圣殿 (`world_06_stainedglass`)

- **定位**：`-10°` 倾斜哥特圣殿；棱镜色散、4 级玻璃台阶、拉绳敲钟、声波环、七彩桥、玫瑰窗。
- **成片**：26.0s / 780f / **4 幕**；Python/PyCairo。
- **入口**：`sim_06_stainedglass.run_simulation` → `level_06_stainedglass.render_frame_from_state`；`build_world_06.py`；`audio_06_stainedglass.py`。
- **核心实现**：
  - `draw_pointed_lancet_window`、`draw_grand_gothic_rose_window`、`draw_expansive_cathedral_background`；
  - `draw_crystal_prism_and_refraction`、`draw_dynamic_shockwaves`；
  - `draw_golden_bell_rope`、`draw_dynamic_ribbon_bridge`；
  - 28 切面 Voronoi 琉璃 + 粗黑铅条 + 硬切面高光。
- **节奏锚点**：0–5.2 入场/三扇柳叶窗；5.2–12 棱镜/4 级台阶；12–19.4 拉绳/敲钟/声波/彩带桥；16.6–18.65 钟铃 token；19.4–26 七彩桥/玫瑰窗；25.2 黑白胶片倒计时。
- **信物**：彩绘琉璃小钟铃；成片 16.6–18.65s 生成，但与星芒/黄色光晕重叠，钟形不可辨。
- **复用要点**：Voronoi 切面 + 铅条；棱镜折射用多色扇面；声波环用同心圆 + 碎片；玫瑰窗用三层同心花瓣。
- **坑**：本关是 4 幕，不是 6 幕；token 辨识度低；25.2s 才进黑白胶片。
- **验收**：14.1s 撞钟；16.2s 声波环；18.3s 彩虹桥 + token；25.2s 黑白胶片。

## 相关文件

- [`STORY.md`](../../worlds/world_06_stainedglass/STORY.md)
- [`build_world_06.py`](../../worlds/world_06_stainedglass/build_world_06.py)
- [`sim_06_stainedglass.py`](../../worlds/world_06_stainedglass/sim_06_stainedglass.py)
- [`level_06_stainedglass.py`](../../worlds/world_06_stainedglass/level_06_stainedglass.py)
- [`audio_06_stainedglass.py`](../../worlds/world_06_stainedglass/audio_06_stainedglass.py)
- [`../../styles/style_06_stainedglass.py`](../../styles/style_06_stainedglass.py)
