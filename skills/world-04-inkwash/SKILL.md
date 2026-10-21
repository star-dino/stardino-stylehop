---
name: world-04-inkwash
description: World 04 · 水墨宣纸千里长卷（竹枝弹射、留白断桥、巨笔补桥、朱砂双鲤、太极化荷、朱砂印门）。Use when building, reviewing, or debugging world_04_inkwash / ink-wash style-hop.
version: 1.0.0
---

# World 04 · 水墨宣纸千里长卷 (`world_04_inkwash`)

- **定位**：宋代设色手卷；留白断桥、悬空巨笔、太极化荷、朱砂印门。
- **成片**：28.0s / 840f / 6 幕；Python/PyCairo。
- **入口**：`sim_04_inkwash.run_simulation` → `level_04_inkwash.render_frame_from_state`；`build_world_04.py`；`audio_04_inkwash.py`。
- **核心实现**：
  - `draw_zone1_bamboo_grove`、`draw_poetic_stone_arch_bridge`、`draw_master_calligraphy_brush`；
  - `draw_lotus_pond_and_koi`、`draw_taiji_yinyang_array`；
  - `draw_cinnabar_gold_star_mandala`、`draw_cinnabar_book_cover_transition`；
  - 墨分五色、飞白、宣纸纤维；朱砂/花青/胭脂转译三色。
- **节奏锚点**：0–4.5 开卷/竹枝；4.5–10.2 断桥/巨笔补桥；10.2–15.2 荷塘/双鲤；15.2–21 墨涡化荷；19.65–21.35 莲心 token；21–24.8 登云山/印门；24.8–27 扎印/翻转；27.0 起全屏朱红。
- **信物**：设计「墨印」；成片为莲心红/橙四角星（20.8–21.2 被吸走），方形印章面不可辨。
- **复用要点**：竹枝是单自由度弹性悬臂；桥面用「未画完的留白」做受阻；墨涡净化用颜色插值 + 花瓣逐层绽放。
- **坑**：印面没有「双子奇观」篆书；token 不在 24.8s，而在莲心 20.8–21.2s；全屏朱红在 27.0s，不是 26.2s。
- **验收**：9.2s 桥补完；20.8s 莲心星；21.2s 吸入；27.0s 全屏朱红。

## 相关文件

- [`STORY.md`](../../worlds/world_04_inkwash/STORY.md)
- [`build_world_04.py`](../../worlds/world_04_inkwash/build_world_04.py)
- [`sim_04_inkwash.py`](../../worlds/world_04_inkwash/sim_04_inkwash.py)
- [`level_04_inkwash.py`](../../worlds/world_04_inkwash/level_04_inkwash.py)
- [`audio_04_inkwash.py`](../../worlds/world_04_inkwash/audio_04_inkwash.py)
- [`../../styles/style_04_inkwash.py`](../../styles/style_04_inkwash.py)
