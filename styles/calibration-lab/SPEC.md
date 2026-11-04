# Calibration Lab · 计量实验室（`styles/calibration-lab/SPEC.md`）

> 一句话：**机器不是展品，是正在被标定的样件。** 浅色无缝影棚、高反差工业反射灯带、程序化机加工法线/粗糙度微纹理、真 Stencil 剖切封盖、安全橙强调与 3D 尺寸公差引线；读数与姿态来自同一个函数。
> 设计迭代记录见本目录的 git 提交历史。

---

## 1. Visual Medium, Stage Mode & Topic Routing（视觉媒介与题材路由）

- **Style ID**: `calibration-lab`
- **Display Name**: Calibration Lab / 计量实验室
- **Stage Mode**: `'3d-pure'`（`defaultOverlay: 'none'`）。`scenes.html` 只含时间轴容器，**零检视文字卡**；仪表在 3D 画布内绘制。
- **Best-Fit Topics**: 机械原理与结构拆解（发动机 / 泵 / 减速箱 / 连杆机构 / 多自由度机械臂 / 仿生机构）；量具、标定与公差；工程教学与“它为什么这么动”；专利与论文机制可视化。
- **Avoid For**: 需要情绪与角色的故事短片；高密度金融 K 线与报表；纯命令行终端演示。

---

## 2. Style Kernel vs. Story World Separation

1. **`kernel.js`（可复用媒介 · v6 工业级解剖升级）**：
   - **色彩、GTAO 与零额外 Pass 屏幕空间折痕墨线（`CAL_PALETTE` / `CAL_LOOK`）**：启用 `env.studioStrips: true` 高反差工业影棚反射阵列，同时在 `CAL_LOOK.ao` 中强制启用 **GTAO（`intensity: 0.72`）+ 屏幕空间深度拉普拉斯与法线折痕墨线描边（`inkStrength: 0.36, inkColor: '#181C22'`）**，让浅色背景上的近白/浅银装甲外壳、沉头孔、倒角与分缝自带锐利工程图纸级轮廓暗线，彻底消除早期 WebGL 塑料玩具感。
   - **工业粗糙度与 IBL 反射纪律强制器（`governIndustrialMaterial` / `createSurfaceMaps` / `createMaterials`）**：
     - 确定性生成阳极氧化拉丝喷砂（`anodized`）、车床同心精密刀纹（`machined`）、压铸喷粉橘皮微颗粒（`cast`）、**45°/135° 高频菱形编织液压软管（`braided`）**法线与粗糙度贴图，以及 45° CNC 机械剖面线（`hatchMap`）与装配缝隙接触遮蔽贴图（`aoRadialTex`）；
     - `governIndustrialMaterial(mat, role)` 强制大面积外壳与结构金属（`alu`, `aluDark`, `titanium`, `white`, `black`, `liner`, `graphite`）满足 **`roughness >= 0.45`、`clearcoat <= 0.14`、`envMapScale = 0.56`**，严禁大面积壳体出现低粗糙度塑料反光条；精密轴销与黄铜接头（`steel`, `chrome`, `bronze`, `brass`, `anodizedRed`）保持高光金属质感。
   - **高密度复合工业部件生成器（Compound Industrial Assemblies，替代裸几何体拼凑）**：
     - `segmentedShellPanel`：生成包含**外层倒角分块面板 + 内缩深色结构内衬底座（`linerMat`，形成真实暗部分缝）+ 四角沉头内六角螺栓座与 `creviceAoRing` + 分缝处红色阳极氧化快拆卡扣（`anodizedRed`）+ 高清丝印编号牌（`01~08`）**的完整工业外壳单元；
     - `braidedHoseBundle`：生成包含**多根菱形编织液压软管 + 两端六角黄铜压接箍（`brass`）+ 中段红色阳极氧化双螺栓管夹**的复合管束，支持 `update(newRoutes)` 随关节动态形变；
     - `flangedRingBulkhead`：生成带内外加厚凸缘、腹板凹槽、周向减重孔阵列与双面螺栓阵列的工字截面环形隔框（替代简陋的裸 `TorusGeometry`）；
     - `createSilkscreenDecal`：生成高清 `JetBrains Mono` 工业编号丝印贴花（`01~08` / 模块代号 / 对位靶标）。
   - **父子层级骨骼链与无碰撞子系统状态机拆解（Hierarchical Kinematics & State-Machine Teardown）**：
     - `createArticulatedChain`：构建真正的**父子嵌套骨骼树（`joint_0 -> seg_0 -> joint_1 -> ...`）**，每节套在前一节的球头万向节（`ballJointGeometry`）上做带硬锥角限位（`maxConeAngle`）的局部旋转，并支持沿局部轴向导轨做无碰撞爆炸分离（`explodeStep`），严禁在世界坐标系下用正弦波直接偏移独立零件导致穿模；
     - `createSubsystemRig`：注册各子系统的局部拆解导轨向量（`explodeVec`）、局部铰链旋转轴（`rotAxis` / `rotAngle`）与材质表，支持按子系统状态权重独立开启（如 `COVER OPEN` / `MANTLE OPEN` / `ARM APART` / `TEARDOWN`）以及非焦点子系统的半透明幽灵化隔离（`solo` / `soloFade`）；
     - `createTeardownController`：状态机分镜控制器，同步驱动子系统状态插值、底部控制台模式按钮高亮、**自动防重叠排布的 3D-to-2D 折线引线标注（`callouts`）**以及带点击波纹环的自动化操作游标（`cursor`）。
   - **工业 CSG-2D 孔槽特征、真 Stencil 剖切封盖（`createSectionCutManager`）与物理场着色器（`createPressureFieldMaterial`）**。
2. **`world.js`（默认样片）**：机械鹦鹉螺 Archive / 007（5 幕 7 镜 26.0s：巡航 → 核心 → 隔板 → 触手 → 喷口/爆炸），由 teardown 最终版移植。题材代码全部在 `sample/`（`nautilus-model.js` 模型、`kin.js` 运动学、`palette.js`、`kit-compat*` 把 teardown kit 接口跑在 r147 上、`hull.glb` Blender 外壳），kernel 不含任何题材名。背景与光色由同目录 `ref.json` 驱动（参考为最终版自己的渲染）。来历见 `lineage/mech-nautilus/`。删除 `world.js` 与 `sample/` 后，kernel 仍能构建任意机械或仿生机构。
3. **零复用规则**：新题材必须重写 `world.js`，不得把本样片的道具当贴纸拼贴（ADR-013）。

---

## 3. Rendering Pipeline, Camera Grammar & Shader Recipe

- **运镜（`engine/director.js` shot list）**：`push` / `pull` / `orbit` / `rise`，恒定 26–31° 焦段；**无抖**。支持 `{ from: HERO, to: EXPLODED }` 动态插值取景盒与 `coreBox / coreWeight` 稀疏主体核心加权取景。
- **相机距离不设上限**：`createCalLabStudio({ maxDist: null })`。
- **Pass Chain**：`['grain', { amount: 0.014, paper: 0.0, vignette: 0.16 }]`。
- **剖切（True Stencil Section Cut）**：`renderer.localClippingEnabled = true` 且 `WebGLRenderer({ stencil: true })`；`THREE.Plane((-1,0,0), c)` 沿 X 轴在世界空间扫过（**0.92 → 0.02**，0.1–1.7s）。通过 `createSectionCutManager` 自动为机匣、散热鳍缸套、缸盖与凸轮室生成带 45° CNC 剖面线的精确 Stencil 截面封盖，同时缸内保留 `createPressureFieldMaterial` 热力学压力波梯度场。
- **HUD**：相机子节点平面 + `CanvasTexture`，`depthTest:false / toneMapped:false`，每帧按 `camera.fov` 重算尺寸；`userData.skipContactShadow = true`。

---

## 4. Color, Material & Typography Tokens

| Token | Value | 用途 |
| :-- | :-- | :-- |
| `--bg` / backdrop | `#EDEFF1` | 无缝浅灰影棚 |
| `--surface` | `#FAFBFC` | HUD 面板底 |
| `--ink` | `#15181C` | 读数与轴线 |
| `--muted` | `#7C838C` | 微标签 |
| `--accent` | `#FF5A1F` | **唯一**强调色：正在工作/被测量的那件 |
| `--line` | `rgba(21,24,28,.12)` | 1px 分隔与面板边 |
| `--font-mono` | JetBrains Mono | 所有数字，`tabular-nums` |
| sectionCap | `#4A525C` + 45° CNC Hatch | Stencil 解析剖切截面封盖 |
| `--font-body` | Inter | 标题与说明 |

---

## 5. Multi-Scene Timeline & Camera Sheet

| Scene | ID | Window | Camera | Action | Cues |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **01** | `lab-run` | 0.0–4.2s | `orbit` 34° → `push` 14° | 样件在台面上运行；前端带减重孔斜齿轮与扭矩弧带旋转，右侧 3D 尺寸引线实时追踪活塞余隙 | `brass_ratchet` ×3 |
| **02** | `lab-section` | 4.2–8.2s | 切到侧视 `pull`（70°）→ `push`（82°） | Stencil 切面 1.6s 内扫到缸孔：散热鳍、机匣壁呈现精确 45° 剖面线，缸内热力学压力波场与工字连杆清晰可读 | `scale_tilt`, `count_tick` |
| **03** | `lab-explode` | 8.2–12.2s | `{from:HERO,to:EXPLODED}` → `rise` | 缸套抬 205 mm 越过活塞冠面，缸盖抬 300 mm；3D 尺寸引线切换为跟踪缸套分离行程 `ΔY` | `card_enter` ×4 |
| **04** | `lab-valves` | 12.2–16.0s | `wide` → 推近缸盖（18°） | 回装（**solid**）；开放缸盖内凸轮经摇臂压迫气门与体积守恒青铜弹簧，配升程曲线 | `count_tick` ×2 |

---

## 6. Tactile Assets & Sound Preset

- **Tactile Surface Texture**：`../assets/textures/brushed_metal.png`（台面/图版底色参考）+ 内核程序化生成法线/粗糙度微纹理。
- **Sound Preset**：`terminal`；绑定 `samples.json` 真实机械拟音采样。

---

## 7. Verification Checklist

- [x] `kernel.js` 只含题材无关的材质/微表面纹理/CSG与仿生几何/Stencil剖切/多自由度运动学/物理场与3D引线/影棚/仪表；`world.js` 只含默认样片
- [x] `stageMode: '3d-pure'`，`scenes.html` 无任何文字卡
- [x] `node tools/audit.mjs --style calibration-lab --all-sizes` → **PASSED (0 issues)** on 1920×1080 / 1080×1920 / 1080×1080
- [x] `node tools/render.mjs --style calibration-lab --sheet styles/calibration-lab/contact_sheet.jpg` 已生成并逐格读图（2026-11-01，v5 升级）
- [x] `node tools/render.mjs --style calibration-lab --storyboard …` 零告警
- [x] `python3 tools/lookcheck.py --style calibration-lab` → 地板检查 OK

---

## 8. Machine-Feel Primitives, Material Roles & Gates (ADR-021, 2026-11-03)

`kernel.js` §8 adds generative primitives (method borrowed from the MIT `teardown` skill, see `CREDITS.md` §D). **Admission rules**: no species / object names; **no good-looking defaults, a missing parameter throws** (take every number from your reference reading and list it in the product's `TREATMENT.md`); shape + material role only, never colour; each primitive is demonstrated on two different subjects.

| Primitive | Behaviour | Subject 1: `rhino-beetle-v1` | Subject 2: `primitive-demo-t1` (rotary pump) |
| :-- | :-- | :-- | :-- |
| `cutWindow` + `windowRim` | signed-function window with exact clipping, outline held by a band; rim wall + lip | two windows in the abdominal deck over the wing hinges | eccentric window in the cast cover over the impeller |
| `seamHardware` | sunk liner + clasps at an exact pitch, ray-seated on both plates when `surfaces` is given | elytral suture (seated) + pronotum/elytron seam | circular flange (`surfaces: null`, unseated) |
| `toothedRingGeometry` + `ringStack` | concentric toothed rings, neighbours counter-rotate, lift with `open` | hinge motor in each window | the impeller |
| `radialFins` | exact angular pitch, every N-th longer/thicker, instanced | hind-wing veins (3.2 deg pitch, 3 wing segments) | impeller vanes (10 deg pitch) |
| `curveSleeve` | armour sleeve rebuilt on a curve each frame, lip rings, optional open arc | leg segments, wing ribs | flexible line leaving the drum (animated bend) |
| `wearMaps` | wear painted into the COLOUR map (+ bump / roughness), every knob required | almost clean glossy plate (reference is clean) | heavy wear (cracks, chips, rivet columns) |
| `createLod` / `lodScaleIn` / `lodLerpMaterial` | detail by camera distance, smoothstep, nothing pops | suture / seam clasps, tibial teeth | flange clasps, tank glaze |
| roles `metal` / `glaze` / `liner` / `emissive` + `metalReport` | `governMaterialRole`; per-role triangle report | glaze plates, metal veins | glaze tank, cast metal, liner |

**Roles.** `shell` / `structural` keep the matte rule from section 2 (`roughness >= 0.45`, `clearcoat <= 0.14`). **`glaze` is a separate role and is exempt** (user decision 2026-11-03): glossy clearcoat ~0.7, `roughness <= 0.16`, for plates that are lacquered / enamelled / ceramic in the reference; pair it with a strong key (`look.light.keyRatio >= 3`). `metal` forces `metalness >= 0.8`; `liner` is dielectric matte and carries the dark gaps; `emissive` follows "at most one emissive subject per shot". Treatment is decided by the material, never by the species.

**Large-sparse / small-dense (大疏大密).** One dense focal area, the rest of the form quiet; accent colour only on focal points; detail scales with camera distance (`createLod`); the machine-feel gate has an **upper** bound, so stacking detail does not pass it.

**Gates (warn by default).** `python3 tools/lookcheck.py --style calibration-lab --world <product>/world.js --content <product>/scenes.html --gates` (silhouette IoU only when `<product>/ref.json` declares a reference; machine-feel density with lower + upper bounds; `--strict-gates` fails) and `node tools/audit.mjs ... --all-sizes` (adds the subject-in-free-area framing check; `--framing-strict` fails). `render.mjs --shots-dir <dir>` writes the per-shot lossless frames the gates read, plus `shot_NNN_mask.png`: a renderer-side subject mask (subject meshes flat white, backdrop / fog / ground slab / decals hidden) that the silhouette and colour gates use instead of a background-difference mask (which fails for cream shell on cream backdrop). Default output of `render.mjs` sheets / storyboards is never a repo file: `<world dir>/contact_sheet.jpg` for `--world`, else `$STYLEHOP_OUT/look/<style>_contact_sheet.jpg`; a repo path is written only when passed to `--sheet` explicitly.

**Gate update (2026-11-03, P4).** (1) The machine-feel "dark" metric now separates **openings** from **dark material**: dark pixels (L < 38) are grouped into connected components; a component counts as an opening only if it is deep (median L < 24), flat (no highlight / texture) and sharply framed by a lit ring (>= 28 L brighter). Near-black glaze or paint is reported as `dark-mat` (informational, not gated). If the reference has < 1% openings, an absolute cap (<= 0.30 of the outline) replaces the ratio band. (2) `lookcheck --world` baselines are keyed by **product directory** (`out/look/<style>__<product-dir>/`), not file stem (every product's file is `world.js`). (3) `render.mjs --world <p>/world.js --content <p>/scenes.html --pair out.jpg [--pair-shot N]` renders one shot beside the reference declared in `<p>/ref.json` (left reference, right render; default shot = `ref.json` `hero_shot`): look at it, do not score it. (4) `engine/director.js` has opt-in `cinema` defaults (drift, swing-proportional pull-back on `blend` shots, fog density following camera distance); see the file header. Products that do not pass `cinema` are pixel-identical to before.

**Colour / light gate, ref.json defaults, role studio, self-review checklist: see section 9.**

**Known debt.** The v5 compound assemblers (`segmentedShellPanel`, `braidedHoseBundle`, `flangedRingBulkhead`) still ship written-in defaults (serial `01`, two red clasps, fixed sizes). They are "components with a preset look" under ADR-013 and should become fully-explicit or world-local helpers.

---

## 9. 颜色/光线默认与关卡、自检清单（ADR-021 实施记录 8，2026-11-03）

起因：外部 agent 照概念图做出 `mech-nautilus-v1`，剪影关与机器感关都过了，但颜色与光是错的（冷蓝灰背景对暖奶油参考、壳偏黄、机构金属近黑、几乎无铜、釉面无高光、主光弱无轮廓光）。这些规则原先只在文字里，现在是默认行为与关卡。

**9.1 `ref.json` 驱动默认值。** `ref.json` 的 `palette`（规范键均为 `#RRGGBB`）：

| 键 | 含义 | 驱动什么 |
| :-- | :-- | :-- |
| `background` | 参考的影棚背景 | `look.backdrop.color`（雾同色）、`light.sky`（背景提亮 25%）、`light.ground`（背景压暗 22%）、`light.bounce.color` |
| `shell` | 壳层（亮） | `createMaterials()` 的 `white` / `alu` 底色 |
| `mechanism` | 机构层（中暗） | `aluDark` / `graphite` / `titanium` 底色 |
| `accent` | 点缀（暖饱和） | `accent` / `accentGlow` / `anodizedRed` |
| `glow` | 发光体 | 仅通过 `studio.refPalette.glow` 提供给 world（内核不自动给任何东西发光） |
| `warm_metal`（可选） | 铜/青铜/黄铜 | `bronze` / `brass` |
| `light.kelvin`（可选） | 主光色温 | `light.key.color`（6500 K = 中性） |

旧写法 `palette.sampled_hex`（`studio_backdrop`、`shell_glaze_mid`、`mechanism_dark_steel`、`focal_accent_orange`、`eye_emissive_orange`、`mechanism_muted_bronze`）经固定别名表读取，旧 `ref.json` 不用改。链路：`gallery/player.html` 把 `?world=` 同目录的 `ref.json` 作为 `style.ref` 交给内核；内核解析顺序 `LOOK_DEFAULTS < CAL_LOOK < ref 派生 < style.look（成品覆盖）`。风格保留结构（照度、keyRatio、阴影、AO、材质粗糙度/金属度/贴图/角色）；**不声明 palette 则什么都不派生，外观与此前逐像素一致**。成品在 `world.js` 里显式写的 `look.*` 叶子仍然优先——所以想让参考色生效，就不要在 world 里再硬写一遍冷灰背景。

**9.2 角色影棚（`glaze` / `metal` 角色自动）。** world 一旦用了这两个角色（`governMaterialRole`），内核在渲染时通知 look rig，自动补齐：① **柔光箱环境**（`env.softboxRig`：五块亮面板——顶、主光侧、轮廓光侧、前侧细条、前方暗淡大卡——立在更暗的环境里；金属只反射它看到的东西，全亮环境=灰塑料，全暗=黑洞；金属/釉面的 IBL 强度另乘角色增益 金属 x4 / 釉面 x2，因为金属没有漫反射项）；② `keyRatio >= 3`（主光 >= 3x 全部补光之和，轮廓光不计入补光）；③ **轮廓光**（`light.rim`，主光反侧后上方，强度 = 主光 x 0.32，不投影）。没有这两类角色的 world 不受影响。**显式退出**：`look.studio = { auto: false }` 整体关闭，或 `{ softbox: false, keyRatio: false, rim: false }` 逐项关闭（`render.mjs --look '{"studio":{"auto":false}}'` 可在命令行试）。注意：已有用了 `glaze`/`metal` 的成品（`rhino-beetle-v1`、`primitive-demo-t1`、`mech-nautilus-v1`）重渲会变（金属变亮、釉面出高光、多一条轮廓光）；这是设计内行为。

**9.3 关卡（warn 默认，`--strict-gates` 才失败）。** 调用：`python3 tools/lookcheck.py --style calibration-lab --world <p>/world.js --content <p>/scenes.html --gates`（`--gates-only` 只跑关卡、不写基线；无 `--world` 则查风格默认世界且无参考）。以 `ref.json` 的 `image` 为参考（对参考图本身测量，不是对你写的色板），在每个镜头的无损帧上：

- **背景**：主体蒙版膨胀 12 px 之外的像素取 Lab 中位数（参考端再排除 `crop.exclude_boxes_px`）。WARN：dL > 8、或 dE76 > 14、或色相差 > 25 度（两者最大色度 >= 6 时才比色相）。
- **主体内三层**（稳健分带，不用 k-means 的随机初值）：点缀 = 暖饱和（C* >= 45、L >= 35、色相 0–95 度）；暖金属 = 铜/青铜带（色相 20–85、C* 18–45、L 25–72）；其余用 Otsu 在 L 上二分为 壳（亮）/ 机构（暗）。每层给面积占比、10–90 分位截尾平均 L、色度加权平均色相。WARN：壳 dL > 12 或色相差 > 25 度；**机构比参考暗 > 12 L（亮 > 20 L）**；**暖金属占比 < 参考的 0.35 倍**（参考占比 >= 1% 时）；点缀占比不在参考的 x[0.3, 3]。层规则只在参考镜头与全景/远景镜头上跑（特写会裁掉分层），背景每镜都跑。
- **金属亮度**（`render.mjs --shots-dir`、`audit.mjs` 在渲染时做**角色 id 通道**：把每个网格临时换成按角色着的纯色（金属红/釉面绿/衬垫蓝），无雾无环境无 AO 再渲一次，取像素对应的亮帧 L* 均值，边缘抗锯齿像素丢弃）。WARN：金属平均 L* < 30，或比参考机构层低 > 15 L → "metal has nothing bright to reflect: add softbox environment"。`audit.mjs` 只用绝对下限 30。
- `render.mjs --pair` 现在在出图的同时打印参考 vs 渲染的上述数字（图仍是给人看的）。

**9.4 自检清单（必填，写进成品 `NOTES.md`；`audit.mjs` 缺失则 WARN，`--notes-strict` 失败）。** 逐条先看 `pair.jpg` 再答，`[x]` 是、`[!]` 否并写原因与处理，不许留 `[ ]`：

```markdown
## 自检清单（Self-Review Checklist）
- [ ] 机构层是否比参考暗？（对照 lookcheck 的 mechanism dL 与金属亮度数字，目视银色反光是否存在）
- [ ] 背景色相是否与参考一致？（lookcheck background 行，冷/暖不能反）
- [ ] 点缀色是否只出现在焦点处？（accent 占比与位置；暖金属/铜是否出现）
- [ ] 附肢的交叉与前后深度是否如参考？（交叉、遮挡、前后景明暗层次，对照 pair.jpg）
- [ ] 釉面高光是否可见？（glaze 板上是否有柔光箱的亮带，而不是一片平色）
- [ ] 大疏大密？（一个致密焦点区，其余安静；机器感关的上限没被堆细节冲破）
```

数字以工具输出为准，勾选要附上工具给的值；与观感冲突时以观感为准并写明（同 ADR-021 后果）。
