# Credits & Third-Party Notices (`CREDITS.md`)

## 1. Author & AI Generation Disclosure

- **Author / Maintainer**: **Star Dinosaur (星星恐龙)**
- **License**: [MIT License](LICENSE)
- **AI Generation Statement**: The procedural animation scripts, level simulations, shaders, sound design recipes, and skill documentation in this repository were generated and iteratively refined using **Gemini 4**.

---

## 2. Upstream Open-Source Toolchains (MIT License)

This project builds upon the architecture, procedural audio synthesis, and sound mastering toolchains of two parent MIT-licensed projects:

### A. `lemo-opuscar`
- **Repository**: [https://github.com/lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar)
- **Copyright**: `Copyright (c) 2026 LemoLab`
- **License**: MIT License
- **License text**: full MIT notice reproduced in [LICENSE-THIRD-PARTY](LICENSE-THIRD-PARTY) because this repository contains **adapted** code, not just imports:
  - `corelib/audio_dsp.py` — `quick_click` / `quick_thump` / `quick_whoosh` are ports of upstream `core/audio/sfx.py` (`click` / `thump` / `whoosh`), refactored onto local helper functions but sharing the same durations, partials and envelopes.
  - `worlds/*/audio_*.py` — synthesis recipes (instrument layering, filter settings, mastering targets) derived from upstream style demos.
- **Distribution**: the library itself is a **runtime dependency only**, cloned separately via `LEMO_OPUSCAR_ROOT`; no upstream source tree is vendored here.
- **Not from upstream**: `worlds/world_01_crt/audio_01_crt.py:moog_ladder` is an independently written 4-pole Moog ladder filter (a textbook DSP topology). An earlier comment claimed it came from `lemo-opuscar/styles/ascii-crt`, which is not the case — no such function exists upstream; the comment has been corrected.

### B. `earshot`
- **Repository**: [https://github.com/Leonxlnx/earshot](https://github.com/Leonxlnx/earshot)
- **Copyright**: `Copyright (c) 2026 Leon Lin`
- **License**: MIT License (full text reproduced in [LICENSE-THIRD-PARTY](LICENSE-THIRD-PARTY))
- **Usage in `stardino-stylehop`**:
  - Acoustically fitted modal/spectral Foley bank (`earshot.forge.bank`) and EBU R128 loudness mastering & sidechain ducking (`master.py`).
- **Distribution**: referenced as a **runtime dependency only** — cloned separately via `EARSHOT_ROOT`; no earshot source is vendored in this repository.

---

## 3. Audio Sample Libraries & Fitted Foley Attribution

When rendering or distributing audio/video files produced by the `audio_XX_*.py` scripts via `lemo-opuscar`'s instrument sample packs, the following sample library attributions apply:

### Required CC-BY Attributions (Used in soundtrack synthesis)
```text
Piano: "Salamander Grand Piano V3" by Alexander Holm, licensed under CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/)
Drums: "MuldjordKit" by Lars Muldjord (drumgizmo.org), FreePats version, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
```

### Public Domain (CC0 1.0) Sample & Foley Acknowledgments
- **Instrument Samples (CC0 1.0)**:
  - Versilian Studios Chamber Orchestra: Community Edition (`VSCO 2 CE`, Sam Gossner) & Versilian Community Sample Library (`VCSL`)
  - FreePats Project (`freepats.zenvoid.org`)
  - Karoryfer Samples (`github.com/sfzinstruments`)
- **Fitted Foley Recipes (`earshot/forge/bank/fit.json`, CC0 1.0 recordings on Freesound)**:
  - Parametric modal/spectral recipes measured from CC0 1.0 recordings by `steffcaffrey`, `qubodup`, `michorvath`, `Sadiquecat`, `zrrion`, `bigmonmulgrew`, `jentlemen`, `kyles`, `IENBA`, `deraj`, `CapsLok`, `IanStarGem`, `Macif`, and `Kinoton` (no raw audio recordings are bundled).
