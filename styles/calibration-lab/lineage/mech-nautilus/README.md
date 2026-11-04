# 机械鹦鹉螺 · calibration-lab 的来历

calibration-lab 的机器感原语与关卡（`kernel.js` §8、`tools/lookcheck.py --gates`）是从这只鹦鹉螺上长出来的。
它由作者用 Gemini 在 `teardown` 工作台（MIT，见 `CREDITS.md` §D）里逐版迭代完成，每一版的改动与原因都有记录；
做完之后，把其中通用的部分搬进了本风格。

![lineage](img/lineage-strip.jpg)

## 怎么走过来的

- **早期**：让 Gemini 直接照原项目做。机器感有了，外形不对，不满意。
- **重做**：推倒重来，外壳改在 Blender 里建模（`src/shared/nautilus_hull.blend` → `hull.glb`），按参考图对剪影。从这时起，整体已经接近参考。
- **迭代**：之后一直在抠细节：机器感、主光与釉面、触手走向、细节随相机距离出现。回头看有些地方改得过头了，效果差别不大，时间花得不少。这也是我们把"看起来对不对"做成能出数字的关卡的原因：知道什么时候该停。

| 核心 | 拆解 |
| :-: | :-: |
| ![core](img/core.jpg) | ![explode](img/explode.jpg) |
| **触手** | **隔板** |
| ![tentacles](img/tentacles.jpg) | ![septa](img/septa.jpg) |

## `src/`：最终版源码（参考，不在本引擎里直接运行）

- `shared/`：模型（`nautilus.js`）、运动学（`kin.js`）、镜头（`film.js`）、配色开关（`palette.js`）、舞台、控制台、配乐（`score.py`）、Blender 源文件与导出的 `hull.glb`、`ref.json`。
- `film/`、`live/`：成片与交互页入口。
- 代码依赖 teardown 的 `teardown-kit/*`（three.js 运行时、`look.js`、`parts.js`、`lod.js` 等），需要在 teardown 里构建：
  `node sims/build.mjs nautilus-live`。本仓库的 calibration-lab 内核提供的是同类能力的通用原语（不带物种语义），
  新的机械题材请用内核写，不要以这份代码为模板（ADR-013 / `SPEC.md` 零复用规则）。
- 参考概念图不随仓库分发。
