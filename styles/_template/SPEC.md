# Style Specification Template (`styles/<style-id>/SPEC.md`)

> Copy `styles/_template/` to `styles/<style-id>/` and fill this spec in order — §1 (Stage Mode & Topic Routing) and §2 (Medium Kernel vs Story World) must be defined before §5 (Scenes & Camera).

---

## 1. Visual Medium, Stage Mode & Topic Routing (视觉媒介与题材路由)
- **Style ID**: `<style-id>`
- **Display Name**: `<English Name>` / `<中文名称>`
- **Stage Mode (`style.js -> stageMode`)**:
  - `'3d-pure'`: Pure 3D / Canvas animation stage (`defaultOverlay: 'none'`). `scenes.html` contains ONLY `<section class="frame scene" data-cues="...">` timeline containers—**zero developer inspection text cards**.
  - `'dom-bento'`: Typography, data visualization, MathML, and editorial card layout (`defaultOverlay: 'typography'`).
  - `'hybrid'`: 3D background world paired with minimal narrative titles.
- **Best-Fit Topics (`style.js -> bestFor`)**: List 3–5 concrete user topic categories where an AI agent should select this style.
- **Avoid For (`style.js -> avoidFor`)**: List topic categories better served by another style.

## 2. Style Kernel vs. Story World Separation (`kernel.js` vs `world.js`)
For any 3D or custom Canvas style (`stageMode: '3d-pure'` or `'hybrid'`):
1. **`kernel.js` (Reusable Medium Kernel)**:
   - Must export only **subject-agnostic** building blocks: color palette tokens, procedural textures, PBR/shader material factories, deterministic physics/animation primitives, and the turnkey studio lighting + camera rig (`applyShot` wrapping `engine/camera.js`).
2. **`world.js` (Default Showcase Story)**:
   - Imports `./kernel.js` and `../../engine/camera.js` to build the style's default 4-scene showcase film.
   - **Zero Demo Asset Reuse Rule**: Future AI runs authoring a video for a user topic MUST import `./kernel.js` and create original models/scenes for that topic—never copy the default showcase props into unrelated stories.
3. **Never include the gallery mascot** (`Star-Spark Slime / 星芒史莱姆` is strictly reserved for promo material outside this repository).

## 3. Rendering Pipeline, Camera Grammar & Shader Recipe (渲染管线与运镜配置)
- **Camera Choreography (`engine/camera.js`)**:
  - Specify which camera moves (`push`, `pull`, `orbit`, `crane`, `track`, `dolly-zoom`, `whip`, `static`) belong to this style's visual grammar. Keep the camera steady: no whole-frame shake (the engine ignores `impacts` / `boil` unless a shot sets `shake: true`); show impacts on the props.
- **Pass Chain (`style.js -> passes`)**:
  - Primary medium/optical pass: `['<pass>', { ...params }]`
  - Optional finishing pass: `['grain', { amount: 0.025, paper: 0.03, vignette: 0.25 }]`
- **3D Floating Layer Feel (`style.js -> layers`)**:
  - `tilt`: `0.15 – 0.25`, `lift`: `24 – 44`, `shadow`: `0.35 – 0.60`

## 4. Color, Material & Typography Tokens (`kernel.js` / `theme.css`)
- **Palette**: `--bg`, `--surface`, `--surface-2`, `--ink`, `--muted`, `--accent`, `--accent-2`, `--line`
- **Typography**: `--font-display`, `--font-body`, `--font-mono`, `--font-cjk-serif`

## 5. Multi-Scene Timeline & Camera Sheet (`scenes.html` / `world.js`)
Define 3–5 scenes (`<section class="frame scene" data-scene="..." data-dur="..." data-cues="...">`).

| Scene | ID | Window | Camera Move (`engine/camera.js`) | Scene Action & Subject Choreography | Foley Cues (`data-cues`) |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **01** | `scene-01` | `0.0s–3.5s` | `<orbit / push / ...>` | `<Scene 01 description>` | `<0.18:enter:..., 0.65:impact:...>` |
| **02** | `scene-02` | `3.5s–7.0s` | `<crane / track / ...>` | `<Scene 02 description>` | `<...>` |
| **03** | `scene-03` | `7.0s–10.5s` | `<track / dolly-zoom / ...>` | `<Scene 03 description>` | `<...>` |
| **04** | `scene-04` | `10.5s–14.0s` | `<orbit / pull / ...>` | `<Scene 04 description>` | `<...>` |

## 6. Tactile Assets & Sound Preset (质感贴图与声学预设)
- **Tactile Surface Texture (`paperTexture`)**: `../assets/textures/paper_fiber.png` | `clay_thumbprint.png` | `halftone_screen.png` | `brushed_metal.png` | `blueprint_cyanotype.png`
- **Sound Preset (`soundPreset`)**: `glass` | `clay` | `paper` | `cyber` | `ink` | `terminal`

## 7. Verification Checklist (门禁与交付清单)
- [ ] `kernel.js` cleanly separates reusable medium materials/lighting/physics from `world.js` demo props
- [ ] If `stageMode: '3d-pure'`, `scenes.html` has zero developer-inspection text cards blocking the 3D viewport
- [ ] `node tools/audit.mjs --style <style-id> --all-sizes` passes on `1920x1080`, `1080x1920`, and `1080x1080` with **0 issues**
- [ ] `node tools/render.mjs --style <style-id> --sheet styles/<style-id>/contact_sheet.jpg` inspected visually
- [ ] Registered in `gallery/catalog.js` with `stageMode`, `bestFor`, `avoidFor`, and `cameraPresets`
