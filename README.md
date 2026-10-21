# StarDino StyleHop · 星星恐龙九界画风跃迁 (`stardino-stylehop`)

> **A 9-World Multi-Style Procedural Animation & Reusable Skill Library** — *work in progress*
> Created by **Star Dinosaur (星星恐龙)** · Generated with **Gemini 4** · Licensed under **MIT**
>
> **⚠️ Status: 2 of 9 worlds are in this repository** (`world_01_crt`, `world_02_pixel`).
> The other seven are listed in the roadmap below but their code is **not yet published**.

---

## 1. 项目简介 (Overview)

**`stardino-stylehop`** 是一个纯代码驱动（Python / PyCairo / NumPy / Pillow / Three.js / Playwright + 48kHz 物理建模与采样音频合成）的**跨画风微电影与可复用技能（Skills）开源工程**。

故事讲述一颗沉睡在老式 CRT 终端里的灰白线框小球，被一颗从天而降的四角凹弧星芒 `✦` 唤醒，化作 Q 弹的**星芒史莱姆（Star-Spark Slime）**，开启了一场横跨 **9 种截然不同视觉媒介与画风** 的奇幻解谜与追逐之旅。

本项目将每个世界拆解为独立的**代码实现 (`worlds/world_XX_*`)** 与标准化的**技能卡 (`skills/world-XX-*/SKILL.md`)**，方便开发者直接复用任意画风管线、物理弹簧角色绑定或音画同步方案。

---

## 2. 九大世界与技能路线图 (9 Worlds & Skills Roadmap)

> 当前进度：**项目基础框架 + World 01 (CRT) & World 02 (Pixel) 已完成去品牌化整理与 Skill 提取**（其余世界陆续合入中）。

| 序号 | 世界目录 (`worlds/`) | 名称 | 视觉媒介与渲染管线 | 时长 | 本关实物信物 (Token) | 提取技能 (`skills/`) | 状态 |
| :--: | :-- | :-- | :-- | :--: | :-- | :-- | :--: |
| **01** | [`world_01_crt`](worlds/world_01_crt/) | 矩阵终端序章 | CRT 曲面磷光字符 + ASCII 球面映射 (PyCairo/NumPy) | 26.0s | 磷光回车键帽 (`[ ↵ ]`) | [`world-01-crt`](skills/world-01-crt/SKILL.md) | ✅ 已就绪 |
| **02** | [`world_02_pixel`](worlds/world_02_pixel/) | 16-Bit 像素大闯关 | 320×180 原生像素 + Bayer 抖动 + 6× NEAREST (PyCairo) | 28.0s | 16-Bit 像素游戏币 | [`world-02-pixel`](skills/world-02-pixel/SKILL.md) | ✅ 已就绪 |
| **03** | `world_03_cyber` | 赛博霓虹疾驰列车 | 3D 赛博都市列车 + 2D 纯白刀锋眼漫画破框 (Three.js) | 24.0s | 破框星芒 | `world-03-cyber` | ⏳ 待迁入 |
| **04** | `world_04_inkwash` | 水墨宣纸千里长卷 | 宋代水墨宣纸 + 悬空巨笔画桥 + 太极化荷 (PyCairo) | 28.0s | 朱砂墨印 / 莲心星 | `world-04-inkwash` | ⏳ 待迁入 |
| **05** | `world_05_paper` | 纸雕立体书山谷 | 3D 折纸群山 + 乘千纸鹤 + 180° 净空大翻页 (Three.js) | 30.0s | 灯笼星徽 | `world-05-paper` | ⏳ 待迁入 |
| **06** | `world_06_stainedglass` | 哥特玫瑰彩窗圣殿 | -10° 倾斜彩窗圣殿 + 敲钟声波架彩虹桥 (PyCairo) | 26.0s | 彩绘琉璃小钟铃 | `world-06-stainedglass` | ⏳ 待迁入 |
| **07** | `world_07_rubberhose` | 1930s 橡皮管爵士舞台 | 3D 波浪琴键 + 赛璐璐胶片噪点 + 留声机 Boss (PyCairo) | 26.0s | 黄金黑胶唱片 | `world-07-rubberhose` | ⏳ 待迁入 |
| **08** | `world_08_clay` | 移轴微缩粘土书桌 | 粘土指纹肌理 + 多米诺骨牌搭咖啡河桥 (Three.js) | 15.0s | 引路星徽 | `world-08-clay` | ⏳ 待迁入 |
| **09** | `world_09_blueprint` | 工程蓝图 ↔ 3D 浮岛 | 普鲁士蓝 CAD 线框撕裂升维 3D 马卡龙浮岛 (Three.js) | 34.0s | 蓝图星盘 (Compass-Star) | `world-09-blueprint` | ⏳ 待迁入 |

---

## 3. 核心架构与通用角色物理铁律

1. **主角「星芒史莱姆 (Star-Spark Slime)」六大锚点**（由 [`slime_engine.py`](slime_engine.py) 驱动）：
   - **体积守恒弹性球体**：水平拉伸系数严格满足 $s_x = 1 / \sqrt{s_y}$，底部锚定解析高度场 `cy = ground_y(cx, t) - R * sy * 0.96`，零穿模、零浮空。
   - **二阶弹簧阻尼器 (`SpringDamper1D` / `SpringDamper2D`)**：所有视线切换 `(look_x, look_y)`、身体倾角与挤压恢复均由物理微分方程驱动，严禁 `if/elif` 折线硬切。
   - **严格无嘴 (`MOUTHLESS`)、无鼻、无手脚**。
   - **纯白圆角胶囊眼 + $C^\infty$ 连续 3D 球面正交投影 (`compute_3d_eye_projection`)**：默认 `-30°` 倾角，标准 3/4 视角下远端眼宽为近端眼的 `81%`。
   - **身体与内部材质随视角 3D 联动**：上半身随视线自然倾侧，内部纹理（CRT 磷光字符、像素抖动、水墨晕染、彩窗切面）绑定局部球面坐标。
   - **三色极光基因**：天际蓝 (`#4285F4` / `#4FADFF`) → 鸢尾紫 (`#7559E8` / `#9B72CB`) → 晨曦珊瑚粉 (`#D96570`)，随各世界媒介原生转译。
2. **中立工程基层 (`corelib/`)**：
   - `corelib/math_ops.py`：缓动与插值函数库。
   - `corelib/camera.py`：2D 摄像机视口变换与字体缓存。
   - `corelib/pipeline.py`：多进程分片并行 FFmpeg 渲染管线与分镜缩略图生成。
   - `corelib/audio_dsp.py`：48kHz 立体声基础滤波、混响与母带工具。
3. **画风渲染层 (`styles/`)**：
   - `styles/style_01_crt.py` / `styles/style_02_pixel.py`：与 sim 解耦的纯绘制入口；`render_keyframe()` / `build_native_world()` 可脱离剧情直接出单帧，`worlds/*/level_*.py` 只做「状态 → 帧」的总装。

---

## 4. 环境依赖与运行方式 (Setup & Usage)

### 外部音频依赖（可选，仅合成音轨时需要）

配乐与拟音脚本（`audio_XX_*.py`）依赖两个 **MIT 协议**的上游项目，它们**不随本仓库分发**：

- [`lemo-opuscar`](https://github.com/lemomo-ai/lemo-opuscar)：采样乐器 / 物理拨弦 / 拟音原语
- `earshot`：拟合拟音库（`earshot.forge.bank`）与响度母带（`master.py`）

用环境变量指向本地克隆（未设置时自动探测仓库同级目录）：

```bash
export LEMO_OPUSCAR_ROOT="/path/to/lemo-opuscar"
export EARSHOT_ROOT="/path/to/earshot"
```

缺失时 `audio_deps.require_audio_upstream()` 会**直接抛出带安装指引的错误**，不会静默生成无声轨。
只想看画面时，可用下面的 `render_keyframe()` / `render_frame_from_state()` 抽帧，无需安装音频依赖；完整成片 `world_*.mp4` 走 GitHub Releases（不入库）。

### 中文字体（可选）

画面内的中文全部走 Pillow 字体回退链：`STARDINO_FONT_DIR` → `STARDINO_FONT_CJK_{BOLD,MED,REG}` → 系统已装的 Noto CJK / PingFang / 微软雅黑 → Pillow 内置位图字体。
Linux 上没有 Noto CJK 时，建议：

```bash
export STARDINO_FONT_DIR="/usr/share/fonts/opentype/noto"   # 或放 NotoSansCJKsc-*.otf 的目录
```

字体文件按 `.gitignore` 不入库。

### 渲染单个世界（以 World 01 / World 02 为例）

```bash
# 先出单帧：不需要音频上游，验证环境
python3 -c "from styles.style_01_crt import render_keyframe; \
render_keyframe().save('/tmp/world01_keyframe.png')"           # 1920x1080
python3 -c "from styles.style_02_pixel import render_keyframe; \
render_keyframe().save('/tmp/world02_keyframe.png')"           # 1920x1080

# 一步到位（需要上面的音频上游：sim → 48kHz 立体声 → 多核并行渲染 → contact sheet）
python3 worlds/world_01_crt/build_world_01.py     # 26.0s / 780f → world_01_crt.mp4
python3 worlds/world_02_pixel/build_world_02.py   # 28.0s / 840f → world_02_pixel.mp4

# 分步：只出音轨 / 只出某一帧
python3 worlds/world_01_crt/audio_01_crt.py
python3 -c "from worlds.world_01_crt.sim_01_crt import run_simulation; \
from worlds.world_01_crt.level_01_crt import render_frame_from_state; \
from PIL import Image; s,_=run_simulation(); \
Image.fromarray(render_frame_from_state(s[630])[:,:,:3]).save('/tmp/f210.png')"
```

`.mp4` / `.wav` 与除 `contact_sheet_*.png` 外的图片均被 `.gitignore` 排除，产物只留在本地；发布时挂 GitHub Releases。

---

## 5. 开源协议与致谢声明 (License & Acknowledgments)

- **许可证 (License)**：本项目采用 **[MIT License](LICENSE)** 开源，`Copyright (c) 2026 Star Dinosaur (星星恐龙)`。
- **AI 生成声明 (AI Disclosure)**：本项目的动画渲染代码、分镜脚本与视听合成逻辑由 **Gemini 4** 生成与打磨。
- **上游开源致谢 (Upstream MIT Projects)**：
  - **[`lemo-opuscar`](https://github.com/lemomo-ai/lemo-opuscar)** (`Copyright (c) 2026 LemoLab`, MIT License) — 提供了真实乐器采样器 (`sampler.py`)、物理拨弦建模 (`pluck.py`)、程序化拟音 (`sfx.py`) 及多项画风工程范式启发。
  - **`earshot`** (`Copyright (c) 2026 Leon Lin`, MIT License) — 提供了基于 CC0 录音测量的模态/频谱拟合拟音库 (`earshot.forge.bank`) 与响度母带工具 (`master.py`)。
- **音频采样署名 (Sample Attributions)**：
  - Piano: *"Salamander Grand Piano V3"* by Alexander Holm, licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)
  - Drums: *"MuldjordKit"* by Lars Muldjord (drumgizmo.org), FreePats version, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
  - 完整致谢清单详见 [`CREDITS.md`](CREDITS.md)。
