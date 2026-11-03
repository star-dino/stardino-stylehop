#!/usr/bin/env python3
"""
StyleHop Look Regression Guard (`tools/lookcheck.py`).

Renders a style's 2x2 contact sheet and measures it against a stored baseline, so every
look change (new light, env map, pass, palette tweak) shows up as numbers instead of a
gut feeling. Drift beyond the guard thresholds is flagged; intentional changes are
re-baselined with `--accept`.

Per-panel metrics (CIE Lab, D65 + Spatial Composition):
  L         mean lightness (exposure)         contrast  std of L (flat / milky vs punchy)
  p5        shadow depth (lower = deeper)     p95       highlight level
  chroma    mean Lab chroma (saturation)      grit      median |L - blur(L)| (fine texture /
                                                        screen-space pattern energy)
  com_y     vertical center-of-mass of visual salience (0 = top edge, 1 = bottom edge)
  half_void max dead-void fraction in upper or lower half (16x9 grid cells with near-zero
            texture & tonal deviation from background median)
  dE        mean CIE76 colour difference against the baseline panel

Absolute readability & spatial composition floors (checked on every run, including the first run
of a new story, which only stores a baseline and therefore compares nothing):
  L in [35, 92]        not murky / not blown out      p95 >= 55         something catches light
  contrast >= 7        not a flat milky wash          p95 - p5 >= 18    real tonal range
  com_y in [0.36,0.66] balanced vertical weight       half_void <= 0.72 no dead-white empty half

Originality gate (every --style run; exit 3 on failure, independent of --strict):
  the rendered sheet is compared panel-by-panel with the style's showcase contact sheet, archived
  showcases ($STYLEHOP_OUT/look/archive/<style>_*contact_sheet*.jpg) and every OTHER topic baseline of the style
  ($STYLEHOP_OUT/look/<style>__*/look_baseline.jpg). sim = layout correlation x colour proximity must stay < 0.33,
  layout correlation alone < 0.78. A new story must not be an old film with the names changed.

Gates (ADR-021, tier a; `--gates`, measured on the per-shot lossless frames of `render.mjs --storyboard --shots-dir`):
  silhouette   ONLY when the product folder holds a `ref.json` declaring a reference (image / mask, long axis, which
               shot is the reference view). Subject mask -> aligned by length -> IoU, aspect ratio, per-band edge
               deviation, plus a red/blue diff overlay. WARN by default (`--strict-gates` fails).
  machine-feel inside the outline, BOTH bounds: detail (edge-pixel share) vs the reference or the style norm in
               [0.8, 1.6], OPENING share in [0.6, 1.6] (see below; if the
               reference has < 1% openings an absolute cap of 0.30 applies instead of a ratio), and on full/wide shots no 6x3 cell below 0.5 or
               above 3.0 of the mean (a dense focal area is allowed, a hole or a noise field is not). It is a guard
               rail, not a target: the upper bounds exist so nobody stacks detail to pass.
  openings vs dark material: the old metric counted every pixel with L < 38, so a near-black glaze plate read as a gap.
               Now `dark_split()` labels connected dark components and calls one an OPENING only if it is deep (median L < 24),
               flat (mean gradient < 9: no highlight / texture) and sharply framed (lit ring >= 28 L brighter): a hole cut in a
               lit surface. Other dark pixels are reported as `dark-mat` (informational, not gated). Luminance + local structure
               only: a renderer id / depth pass was not used because it cannot be applied to the photographed reference.
  colour/value   (ADR-021 colour gate, needs ref.json `image`; the render is compared with the reference, never with a palette
               you wrote down) background Lab (median of pixels outside the dilated subject mask; ref.json `crop.exclude_boxes_px`
               are left out of the reference), and INSIDE the subject mask three layers split by robust bands, not k-means
               seeds: accent = warm saturated (C* >= 45, L >= 35, hue 0-95 deg); warm metal = copper/bronze/brass band (hue 20-85,
               C* 18-45, L 25-72); of the rest, an Otsu split of L gives shell (bright) / mechanism (dark). Per layer: area share,
               trimmed-mean L, chroma-weighted mean hue. WARN thresholds (GATE_COLOR): background dL > 8 or dE76 > 14 or hue
               diff > 25 deg; shell dL > 12 or hue diff > 25 deg; mechanism darker than the reference by > 12 L (or brighter by
               > 20); warm-metal share < 0.35x the reference's (when the reference has >= 1%); accent share outside [0.3, 3]x.
               Layer rules run on the reference shot and full/wide shots (close-ups crop the layers); background on every shot.
               Metal brightness (render.mjs --shots-dir writes `roles` into shots.json from a role-id pass): mean L of
               role=metal pixels < 30 or > 15 L below the reference mechanism layer -> "metal has nothing bright to reflect:
               add softbox environment". All colour findings are WARN; `--strict-gates` fails.
  Both reuse this file's Lab / measure helpers; the per-shot subject-in-free-area check lives in tools/audit.mjs.

Usage:
  python3 tools/lookcheck.py --style calibration-lab --world <product>/world.js --gates   # + silhouette / machine-feel
  python3 tools/lookcheck.py --style calibration-lab --world <product>/world.js --content <product>/scenes.html --gates-only [--shots-dir D]
                  # gates only: no contact sheet, no baseline written (read-only on the product; shots go to $STYLEHOP_OUT/look/gates__<product>/ or D)
  python3 tools/lookcheck.py --style clay-macaron            # render + compare vs baseline
  python3 tools/lookcheck.py --style clay-macaron --accept   # store current render as baseline
  python3 tools/lookcheck.py --a before.jpg --b after.jpg    # compare any two sheets
  python3 tools/lookcheck.py --style clay-macaron --look '{"env":{"enabled":false}}' --tag noenv
  [--world $STYLEHOP_OUT/custom-world.js] [--content $STYLEHOP_OUT/custom-scenes.html]  (own baseline under $STYLEHOP_OUT/look/<style>__<product-dir>/ = the name of the directory that holds the world file, first run stores it)
  [--originality-ref other_sheet.jpg]  (extra originality reference, repeatable)
  [--strict]  (exit 2 on drift)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rendered artifacts, look baselines and archived showcases live OUTSIDE the repo, so a public
# clone never carries private output. Override with STYLEHOP_OUT (absolute path; a relative value
# resolves against the current directory); defaults to the sibling `../out`.
OUT_ROOT = os.path.abspath(os.environ.get('STYLEHOP_OUT') or os.path.join(REPO_ROOT, os.pardir, 'out'))

# Max drift tolerated for a change that is NOT meant to alter the look (per panel).
GUARD = {'L': 4.0, 'contrast_pct': 20.0, 'chroma_pct': 25.0, 'dE': 6.0}

METRICS = ['L', 'contrast', 'p5', 'p95', 'chroma', 'grit', 'com_y', 'half_void']

# Absolute floors any shippable panel must meet, whatever the story or time of day.
ABS = {
    'L_min': 35.0,
    'L_max': 92.0,
    'p95_min': 55.0,
    'contrast_min': 7.0,
    'range_min': 18.0,
    'com_y_min': 0.36,
    'com_y_max': 0.66,
    'half_void_max': 0.72,
}

# Medium-specific overrides:
# - `ink-wash`: honors classical `计白当黑` (expansive blank Xuan-paper voids up to `half_void <= 0.88`,
#   high/low horizon `com_y in [0.24, 0.78]`) and stark nocturnal martial scenes (`L_min = 18.0`).
# - `paper-popup`: tabletop pop-up book theater requires >=45% desk/page breathing margin and a single
#   central pop-up mechanism per spread (`half_void <= 0.82`, `com_y in [0.30, 0.72]`).
# - `rubber-hose`: 1930s single-focus stage & large facial reaction close-ups keep upper backdrops clean
#   rather than stuffing the sky with floating filler (`half_void <= 0.80`, `com_y in [0.30, 0.72]`).
# - `twilight-fable`: nocturnal bioluminescent woodland fables feature deep night skies and low-key lighting
#   (`L_min = 18.0`, `half_void <= 0.84`, `com_y in [0.28, 0.74]`).
# - `calibration-lab`: seamless pale studio with one sample on a bench and no set dressing — the empty upper
#   frame *is* the medium (no horizon, no props to fill it); the HUD anchors the top-left corner
#   (`half_void <= 0.80`).
STYLE_ABS_OVERRIDES = {
    'ink-wash': {
        'L_min': 18.0,
        'com_y_min': 0.24,
        'com_y_max': 0.78,
        'half_void_max': 0.88,
    },
    'paper-popup': {
        'com_y_min': 0.30,
        'com_y_max': 0.72,
        'half_void_max': 0.82,
    },
    'rubber-hose': {
        'com_y_min': 0.30,
        'com_y_max': 0.72,
        'half_void_max': 0.80,
    },
    'twilight-fable': {
        'L_min': 18.0,
        'com_y_min': 0.28,
        'com_y_max': 0.74,
        'half_void_max': 0.84,
    },
    'calibration-lab': {
        'half_void_max': 0.80,
    },
}


def resolve_panel_floors(style=None, path=None):
    eff_style = style
    if not eff_style and path:
        base = os.path.basename(str(path))
        for k in STYLE_ABS_OVERRIDES:
            if k in base:
                eff_style = k
                break
    floors = dict(ABS)
    if eff_style in STYLE_ABS_OVERRIDES:
        floors.update(STYLE_ABS_OVERRIDES[eff_style])
    return floors


def absolute_check(path, style=None):
    img = Image.open(path).convert('RGB')
    floors = resolve_panel_floors(style=style, path=path)
    fails = []
    for i, p in enumerate(panels(img)):
        m = measure(p)[0]
        f = []
        if not floors['L_min'] <= m['L'] <= floors['L_max']:
            f.append(f"L {m['L']:.1f} outside [{floors['L_min']:.0f}, {floors['L_max']:.0f}]")
        if m['p95'] < floors['p95_min']:
            f.append(f"p95 {m['p95']:.1f} < {floors['p95_min']:.0f} (nothing catches light)")
        if m['contrast'] < floors['contrast_min']:
            f.append(f"contrast {m['contrast']:.1f} < {floors['contrast_min']:.0f} (flat)")
        if m['p95'] - m['p5'] < floors['range_min']:
            f.append(f"tonal range {m['p95'] - m['p5']:.1f} < {floors['range_min']:.0f}")
        if not floors['com_y_min'] <= m['com_y'] <= floors['com_y_max']:
            f.append(
                f"com_y {m['com_y']:.3f} outside [{floors['com_y_min']:.2f}, {floors['com_y_max']:.2f}] "
                "(vertical center-of-mass imbalance: top-heavy or bottom-heavy frame)"
            )
        if m['half_void'] > floors['half_void_max']:
            f.append(
                f"half_void {m['half_void']:.2f} > {floors['half_void_max']:.2f} "
                "(dead-void empty upper/lower half; anchor foreground/midground across vertical planes)"
            )
        if f:
            fails.append((i, f))
    if fails:
        print('\n  READABILITY & SPATIAL COMPOSITION floors failed:')
        for i, f in fails:
            print(f'    panel {i}: ' + ', '.join(f))
    else:
        print('\n  readability & spatial composition floors: OK')
    return fails


def srgb_to_lab(rgb):
    c = rgb.astype(np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def panels(img):
    w, h = img.size
    cols = 3 if (w / max(h, 1)) > 2.2 else 2
    rows = 2
    pw, ph = w // cols, h // rows
    return [img.crop((c * pw, r * ph, (c + 1) * pw, (r + 1) * ph)) for r in range(rows) for c in range(cols)]


def measure(panel):
    lab = srgb_to_lab(np.asarray(panel.convert('RGB')))
    L = lab[..., 0]
    chroma_map = np.hypot(lab[..., 1], lab[..., 2])
    gray = panel.convert('L')
    hp = np.abs(np.asarray(gray, np.float64) - np.asarray(gray.filter(ImageFilter.GaussianBlur(3)), np.float64))

    # Spatial salience center-of-mass (com_y in [0, 1]) & 16x9 grid dead-void check
    bg_L = float(np.median(L))
    bg_C = float(np.median(chroma_map))
    sal = hp + 0.30 * np.abs(L - bg_L) + 0.20 * np.abs(chroma_map - bg_C)
    h, w = sal.shape
    ys = (np.arange(h, dtype=np.float64) + 0.5) / max(h, 1)
    row_sal = sal.mean(axis=1)
    com_y = float((row_sal * ys).sum() / max(float(row_sal.sum()), 1e-6))

    gh, gw = 9, 16
    ch, cw = max(1, h // gh), max(1, w // gw)
    void_cells = np.zeros((gh, gw), dtype=bool)
    for r in range(gh):
        for c in range(gw):
            sub_hp = float(hp[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw].mean())
            sub_dL = float(np.abs(L[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] - bg_L).mean())
            if sub_hp < 0.85 and sub_dL < 3.2:
                void_cells[r, c] = True
    top_void = float(void_cells[:4, :].mean())
    bot_void = float(void_cells[5:, :].mean())
    half_void = max(top_void, bot_void)

    return {
        'L': float(L.mean()),
        'contrast': float(L.std()),
        'p5': float(np.percentile(L, 5)),
        'p95': float(np.percentile(L, 95)),
        'chroma': float(chroma_map.mean()),
        'grit': float(np.median(hp)),
        'com_y': com_y,
        'half_void': half_void,
    }, lab


def compare(path_a, path_b, out_img=None):
    a_img, b_img = Image.open(path_a).convert('RGB'), Image.open(path_b).convert('RGB')
    if b_img.size != a_img.size:
        b_img = b_img.resize(a_img.size, Image.LANCZOS)
    rows, drift = [], []
    for i, (pa, pb) in enumerate(zip(panels(a_img), panels(b_img))):
        ma, la = measure(pa)
        mb, lb = measure(pb)
        de = float(np.linalg.norm(la - lb, axis=-1).mean())
        rows.append((i, ma, mb, de))
        flags = []
        if abs(mb['L'] - ma['L']) > GUARD['L']:
            flags.append(f"L {mb['L'] - ma['L']:+.1f}")
        if abs(mb['contrast'] / max(ma['contrast'], 1e-6) - 1) * 100 > GUARD['contrast_pct']:
            flags.append(f"contrast {(mb['contrast'] / ma['contrast'] - 1) * 100:+.0f}%")
        if abs(mb['chroma'] / max(ma['chroma'], 1e-6) - 1) * 100 > GUARD['chroma_pct']:
            flags.append(f"chroma {(mb['chroma'] / ma['chroma'] - 1) * 100:+.0f}%")
        if de > GUARD['dE']:
            flags.append(f'dE {de:.1f}')
        if flags:
            drift.append((i, flags))

    print(f'\n  baseline: {os.path.relpath(path_a, REPO_ROOT)}\n  current : {os.path.relpath(path_b, REPO_ROOT)}\n')
    print('  panel  metric      base    curr    delta')
    for i, ma, mb, de in rows:
        for k in METRICS:
            print(f'  {i:>5}  {k:<9} {ma[k]:7.2f} {mb[k]:7.2f} {mb[k] - ma[k]:+8.2f}')
        print(f'  {i:>5}  {"dE":<9} {"":7} {"":7} {de:8.2f}\n')

    if out_img:
        w, h = a_img.size
        sheet = Image.new('RGB', (w * 2, h + 40), (24, 24, 24))
        sheet.paste(a_img, (0, 40))
        sheet.paste(b_img, (w, 40))
        d = ImageDraw.Draw(sheet)
        d.text((16, 12), 'BASELINE', fill=(240, 240, 240))
        d.text((w + 16, 12), 'CURRENT', fill=(240, 240, 240))
        os.makedirs(os.path.dirname(out_img), exist_ok=True)
        sheet.save(out_img, quality=90)
        print(f'  side-by-side: {os.path.relpath(out_img, REPO_ROOT)}')
    return rows, drift


def render_sheet(style, out, world=None, look=None, content=None):
    cmd = ['node', os.path.join(REPO_ROOT, 'tools', 'render.mjs'), '--style', style, '--sheet', out]
    if world:
        cmd += ['--world', world]
    if content:
        cmd += ['--content', content]
    if look:
        cmd += ['--look', look]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT, stdout=subprocess.DEVNULL)


# Originality gate (calibrated on known clones vs genuinely different stories of the same style):
#   sim  = layout correlation (64x36 luminance) x colour proximity exp(-dE/25), best-matching reference
#          panel per current panel, averaged over the 4 panels
#   corr = the layout correlation alone (catches a re-coloured clone)
ORIG = {'sim_max': 0.33, 'corr_max': 0.78, 'clone_sim': 0.6}


def _panel_features(path):
    img = Image.open(path).convert('RGB')
    feats = []
    for p in panels(img):
        lum = np.asarray(p.convert('L').resize((64, 36)), np.float64).ravel()
        lab = srgb_to_lab(np.asarray(p.resize((48, 27))))
        feats.append((lum, lab))
    return feats


def _similarity(ref_feats, cur_feats):
    sims, corrs = [], []
    for lum_b, lab_b in cur_feats:
        best_s, best_c = -1.0, -1.0
        for lum_a, lab_a in ref_feats:
            c = float(np.corrcoef(lum_a, lum_b)[0, 1]) if lum_a.std() > 1e-6 and lum_b.std() > 1e-6 else 0.0
            de = float(np.linalg.norm(lab_a - lab_b, axis=-1).mean())
            best_s = max(best_s, c * float(np.exp(-de / 25.0)))
            best_c = max(best_c, c)
        sims.append(best_s)
        corrs.append(best_c)
    return float(np.mean(sims)), float(np.mean(corrs))


def originality_references(style, own_dir=None, is_showcase=False, extra=None):
    """Showcase contact sheet, archived showcases ($STYLEHOP_OUT/look/archive/<style>_*contact_sheet*.jpg) and the
    look baselines of every other topic world of this style ($STYLEHOP_OUT/look/<style>__*/look_baseline.jpg)."""
    import glob
    refs = []
    sheet = os.path.join(REPO_ROOT, 'styles', style, 'contact_sheet.jpg')
    if not is_showcase and os.path.exists(sheet):
        refs.append(('showcase', sheet))
    for p in sorted(glob.glob(os.path.join(OUT_ROOT, 'look', 'archive', f'{style}_*contact_sheet*.jpg'))):
        refs.append(('archived showcase ' + os.path.basename(p), p))
    if not is_showcase:
        for p in sorted(glob.glob(os.path.join(OUT_ROOT, 'look', f'{style}__*', 'look_baseline.jpg'))):
            d = os.path.dirname(p)
            if own_dir and os.path.abspath(d) == os.path.abspath(own_dir):
                continue
            refs.append(('topic ' + os.path.basename(d).split('__', 1)[1], p))
    for p in extra or []:
        refs.append(('ref ' + os.path.basename(p), p))
    return refs


def originality_check(current, refs):
    """Fails when the current sheet is too close to the showcase, an archived showcase or another topic."""
    if not refs:
        print('\n  originality: no references to compare against')
        return []
    cur = _panel_features(current)
    fails = []
    print('\n  ORIGINALITY (sim = layout x colour; limits sim < %.2f, layout corr < %.2f)' % (ORIG['sim_max'], ORIG['corr_max']))
    for label, path in refs:
        sim, corr = _similarity(_panel_features(path), cur)
        bad = sim >= ORIG['sim_max'] or corr >= ORIG['corr_max']
        tag = ('CLONE' if sim >= ORIG['clone_sim'] else 'TOO SIMILAR') if bad else 'ok'
        print(f'    {tag:<11} sim {sim:.2f}  corr {corr:.2f}  vs {label}')
        if bad:
            fails.append((label, sim, corr))
    if fails:
        print('\n  ORIGINALITY failed: this film re-uses the composition / palette of an existing one.')
        print('  Re-compose the places (ground type, horizon height, subject position and size) and looks for THIS story.')
    else:
        print('  originality: OK')
    return fails


# ----------------------------------------------------------------------------------------------------------
# Gates (ADR-021 tier a): silhouette IoU (only with a declared reference) + machine-feel density with upper bounds
# ----------------------------------------------------------------------------------------------------------
GATE_SIL = {'iou_len_min': 0.80, 'iou_len_min_limbs': 0.70, 'aspect_tol': 0.08, 'edge_tol': 0.08}
GATE_FEEL = {'detail': (0.8, 1.6), 'dark': (0.6, 1.6), 'cell_min': 0.5, 'cell_max': 3.0, 'open_abs': 0.30, 'min_cell_cover': 0.35}
# Style norms for the no-reference case, calibrated on single-cylinder-four-stroke (v5 world) full/wide shots;
# re-calibrate whenever a second product of the style exists (ADR-021 §6).
FEEL_STYLE_NORM = {'calibration-lab': {'detail': 0.0, 'dark': 0.0}}
CANON_LEN = 640  # bbox length (px) both masks are rescaled to before measuring, so density is resolution-independent


def subject_mask(img, bg_cols=0.08, thr=14.0):
    """Subject = pixels differing from the per-row background (median of the outer left/right columns, robust to the
    studio's vertical gradient). Works for a seamless-studio frame without HUD clutter; keeps the biggest blobs."""
    from scipy import ndimage as ndi
    lab = srgb_to_lab(np.asarray(img.convert('RGB')))
    h, w, _ = lab.shape
    k = max(2, int(w * bg_cols))
    edge = np.concatenate([lab[:, :k], lab[:, w - k:]], axis=1)
    bg = np.median(edge, axis=1)[:, None, :]
    d = np.linalg.norm(lab - bg, axis=-1)
    m = d > thr
    m = ndi.binary_opening(m, iterations=1)
    m = ndi.binary_closing(m, iterations=1)
    # fill specular holes inside the body, but not the real gaps between limbs and body (holes > 0.4% of the area)
    holes, nh = ndi.label(~m)
    if nh:
        hs = ndi.sum(~m, holes, range(1, nh + 1))
        border = set(np.unique(np.concatenate([holes[0], holes[-1], holes[:, 0], holes[:, -1]])))
        small = [i + 1 for i, a in enumerate(hs) if a < 0.004 * m.sum() and (i + 1) not in border]
        m = m | np.isin(holes, small)
    lbl, n = ndi.label(m)
    if n == 0:
        return m
    sizes = ndi.sum(m, lbl, range(1, n + 1))
    keep = [i + 1 for i, sz in enumerate(sizes) if sz >= 0.04 * sizes.max()]
    return np.isin(lbl, keep)


def _bbox(m):
    ys, xs = np.nonzero(m)
    return xs.min(), xs.max() + 1, ys.min(), ys.max() + 1


def _norm_to_len(m, axis, length=CANON_LEN):
    """Crop to bbox and rescale so the bbox length along `axis` ('x' or 'y') is `length` px. Returns mask, scale."""
    x0, x1, y0, y1 = _bbox(m)
    crop = m[y0:y1, x0:x1]
    L = (x1 - x0) if axis == 'x' else (y1 - y0)
    sc = length / max(L, 1)
    im = Image.fromarray((crop * 255).astype('uint8')).resize((max(1, round(crop.shape[1] * sc)), max(1, round(crop.shape[0] * sc))), Image.BILINEAR)
    return np.asarray(im) > 127


def silhouette_gate(frame_mask, ref_mask, axis, limbs=False, diff_out=None):
    a = _norm_to_len(frame_mask, axis)
    b = _norm_to_len(ref_mask, axis)
    H = max(a.shape[0], b.shape[0]) + 4
    W = max(a.shape[1], b.shape[1]) + 4
    def put(m):
        c = np.zeros((H, W), bool)
        oy, ox = (H - m.shape[0]) // 2, (W - m.shape[1]) // 2
        c[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
        return c
    A, B = put(a), put(b)
    iou = float((A & B).sum() / max((A | B).sum(), 1))
    asp = lambda m: m.shape[1] / max(m.shape[0], 1)
    aspect_dev = asp(a) / asp(b) - 1.0
    # per-band edge deviation along the length axis, as a fraction of the length
    bands, devs = 10, []
    for k in range(bands):
        sl = (slice(None), slice(int(W * k / bands), int(W * (k + 1) / bands))) if axis == 'x' else (slice(int(H * k / bands), int(H * (k + 1) / bands)), slice(None))
        ea, eb = [], []
        for M, e in ((A, ea), (B, eb)):
            sub = M[sl]
            idx = np.nonzero(sub.any(axis=0 if axis == 'y' else 1))[0]
            e.append((idx.min(), idx.max()) if len(idx) else (0, 0))
        (a0, a1), (b0, b1) = ea[0], eb[0]
        devs.append((abs(a0 - b0) + abs(a1 - b1)) / 2 / CANON_LEN)
    edge_dev = float(np.mean(devs))
    if diff_out:
        rgb = np.full((H, W, 3), 255, np.uint8)
        rgb[A & B] = (150, 150, 150)
        rgb[A & ~B] = (220, 60, 50)   # red: in the frame, not in the reference
        rgb[B & ~A] = (50, 90, 220)   # blue: in the reference, missing in the frame
        os.makedirs(os.path.dirname(diff_out), exist_ok=True)
        Image.fromarray(rgb).save(diff_out)
    need = GATE_SIL['iou_len_min_limbs'] if limbs else GATE_SIL['iou_len_min']
    return {
        'iou_length_aligned': iou, 'iou_required': need, 'aspect_dev': aspect_dev, 'edge_dev_mean': edge_dev,
        'warn': [m for ok, m in (
            (iou >= need, f'IoU {iou:.2f} < {need:.2f}'),
            (abs(aspect_dev) <= GATE_SIL['aspect_tol'], f'aspect {aspect_dev:+.1%} beyond +-{GATE_SIL["aspect_tol"]:.0%}'),
            (edge_dev <= GATE_SIL['edge_tol'], f'edge deviation {edge_dev:.1%} > {GATE_SIL["edge_tol"]:.0%} of length')) if not ok],
    }


# Openings vs dark material (replaces the old "luminance < 38" share, which counted a near-black glaze plate as a gap).
# No renderer mask / depth pass is used (the player exposes the scene, but a per-pixel id / depth pass would need a second
# render path and cannot be applied to the photographed reference at all, and the gate must compare against the reference),
# so the split uses luminance + local structure on the canonical-scale crop:
#   1. candidate = pixel inside the outline with L < DARK_L (38)
#   2. connected components of candidates (8-neighbour), ignoring specks < DARK_MIN_AREA px
#   3. a component is an OPENING when it is deep (median L < OPEN_MEDIAN), flat (mean gradient inside < OPEN_GRAD, no highlight
#      or texture - a glaze plate carries specular gradients) and sharply framed (the lit ring around it is >= OPEN_RIM brighter
#      than its median: a real gap / window is a dark hole cut in a lit surface); everything else is dark MATERIAL
#      (soft shading falloff has no sharp rim, black paint / glaze has highlights and a median above the opening depth).
DARK_REF_MIN = 0.01  # reference opening share below this -> compare with an absolute cap instead of a ratio
DARK_L, DARK_MIN_AREA, OPEN_MEDIAN, OPEN_GRAD, OPEN_RIM = 38, 12, 24.0, 9.0, 28.0


def dark_split(g, inner, mag):
    """Return {'opening': share, 'material': share} of the inside-outline pixels (shares of `inner`)."""
    from scipy import ndimage as ndi
    cand = inner & (g < DARK_L)
    lab, n = ndi.label(cand, structure=np.ones((3, 3)))
    if n == 0:
        return {'opening': 0.0, 'material': 0.0}
    idx = np.arange(1, n + 1)
    area = ndi.sum(np.ones_like(g), lab, idx)
    med = ndi.median(g, lab, idx)
    grad = ndi.mean(mag, lab, idx)
    opening_px = material_px = 0
    for k in idx[area >= DARK_MIN_AREA]:
        comp = lab == k
        ring = ndi.binary_dilation(comp, iterations=4) & ~ndi.binary_dilation(comp, iterations=1) & inner & ~cand
        rim = float(np.median(g[ring])) - float(med[k - 1]) if ring.sum() >= 8 else 0.0
        is_open = med[k - 1] < OPEN_MEDIAN and grad[k - 1] < OPEN_GRAD and rim >= OPEN_RIM
        if is_open:
            opening_px += area[k - 1]
        else:
            material_px += area[k - 1]
    tot = float(inner.sum())
    return {'opening': float(opening_px / tot), 'material': float(material_px / tot)}


def machine_feel(img, mask, axis='y'):
    """Inside-the-outline density: detail (edge-pixel share), dark share and the 6x3 cell map (mean-normalised)."""
    from scipy import ndimage as ndi
    x0, x1, y0, y1 = _bbox(mask)
    L = (x1 - x0) if axis == 'x' else (y1 - y0)
    sc = CANON_LEN / max(L, 1)
    crop_img = img.convert('RGB').crop((x0, y0, x1, y1))
    crop_m = Image.fromarray((mask[y0:y1, x0:x1] * 255).astype('uint8'))
    size = (max(8, round(crop_img.width * sc)), max(8, round(crop_img.height * sc)))
    g = np.asarray(crop_img.resize(size, Image.LANCZOS).convert('L'), np.float64)
    m = np.asarray(crop_m.resize(size, Image.BILINEAR)) > 127
    inner = ndi.binary_erosion(m, iterations=3)
    if inner.sum() < 400:
        return None
    gx, gy = ndi.sobel(ndi.gaussian_filter(g, 0.8), axis=1), ndi.sobel(ndi.gaussian_filter(g, 0.8), axis=0)
    mag = np.hypot(gx, gy) / 8.0
    detail = float((mag[inner] > 6.0).mean())
    dark_all = float((g[inner] < 38).mean())
    dark = dark_split(g, inner, mag)  # openings only; the old `dark_all` also counted near-black glaze / paint
    gh, gw = (6, 3) if axis == 'y' else (3, 6)
    ch, cw = size[1] // gh, size[0] // gw
    cells = np.full((gh, gw), np.nan)
    mean_detail = max(detail, 1e-6)
    for r in range(gh):
        for c in range(gw):
            sub = inner[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
            if sub.mean() >= GATE_FEEL['min_cell_cover']:
                cells[r, c] = float((mag[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw][sub] > 6.0).mean()) / mean_detail
    return {'detail': detail, 'dark': dark['opening'], 'dark_all': dark_all, 'dark_material': dark['material'], 'cells': cells}


def feel_verdict(cur, ref, strict_cells):
    """Bands apply to cur/ref ratios (ref = reference image or style norm); cells apply on full/wide shots only."""
    w = []
    if ref:
        if ref['dark'] < DARK_REF_MIN and cur['dark'] > GATE_FEEL['open_abs']:
            w.append(f'openings {cur["dark"]:.3f} of the outline > {GATE_FEEL["open_abs"]} (reference has almost none: gaps should not dominate)')
        for key in ('detail', 'dark'):
            if key == 'dark' and ref[key] < DARK_REF_MIN:
                continue  # ratio against ~0 is meaningless; the absolute cap above applies
            if ref[key] > 1e-6:
                r = cur[key] / ref[key]
                lo, hi = GATE_FEEL[key]
                if not lo <= r <= hi:
                    w.append(f'{key} ratio {r:.2f} outside [{lo}, {hi}]')
    if strict_cells:
        c = cur['cells'][~np.isnan(cur['cells'])]
        if len(c):
            # the floor is relaxed to the reference's own quietest cell: a glossy plate that is smooth in the reference
            # may be smooth here (large-sparse / small-dense), only a hole the reference does not have is flagged
            floor = GATE_FEEL['cell_min']
            if ref and ref.get('cells') is not None and not np.all(np.isnan(ref['cells'])):
                floor = min(floor, float(np.nanmin(ref['cells'])) * 0.8)
            if c.min() < floor:
                w.append(f'empty cell {c.min():.2f} < {floor:.2f} of mean (a hole in the surface)')
            if c.max() > GATE_FEEL['cell_max']:
                w.append(f'dense cell {c.max():.2f} > {GATE_FEEL["cell_max"]} of mean (a noise field, not a focal area)')
    return w


GATE_COLOR = {'bg_dL': 8.0, 'bg_dE': 14.0, 'hue_deg': 25.0, 'shell_dL': 12.0, 'mech_dark': 12.0, 'mech_light': 20.0,
              'warm_ratio': 0.35, 'warm_ref_min': 0.01, 'accent_ratio': (0.3, 3.0), 'metal_floor': 30.0, 'metal_vs_mech': 15.0}


def _hue(a, b):
    return float(np.degrees(np.arctan2(b, a)) % 360.0)


def _hue_diff(h1, h2):
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)


def background_stats(img, mask, exclude_boxes=None):
    """Median Lab of pixels outside the subject (dilated 12 px), minus any exclude boxes (px rects of the image)."""
    from scipy import ndimage as ndi
    lab = srgb_to_lab(np.asarray(img.convert('RGB')))
    keep = ~ndi.binary_dilation(mask, iterations=12)
    for r in exclude_boxes or []:
        x0, y0, x1, y1 = r
        keep[y0:y1, x0:x1] = False
    px = lab[keep]
    if len(px) < 500:
        return None
    L, a, b = np.median(px, axis=0)
    return {'L': float(L), 'a': float(a), 'b': float(b), 'C': float(np.hypot(a, b)), 'h': _hue(a, b)}


def _otsu(v):
    hist, edges = np.histogram(v, bins=64, range=(0, 100))
    p = hist / max(hist.sum(), 1)
    w = np.cumsum(p)
    mu = np.cumsum(p * (edges[:-1] + edges[1:]) / 2)
    mt = mu[-1]
    sb = (mt * w - mu) ** 2 / np.maximum(w * (1 - w), 1e-9)
    return float(edges[int(np.argmax(sb)) + 1])


def _layer(px):
    if len(px) == 0:
        return {'share': 0.0, 'L': None, 'C': None, 'h': None}
    lo, hi = np.percentile(px[:, 0], [10, 90])
    t = px[(px[:, 0] >= lo) & (px[:, 0] <= hi)]  # trimmed: speculars and deep creases do not move the mean
    a, b = float(t[:, 1].mean()), float(t[:, 2].mean())
    return {'L': float(t[:, 0].mean()), 'C': float(np.hypot(a, b)), 'h': _hue(a, b)}


def color_layers(img, mask):
    """Accent / warm metal / shell / mechanism split inside the subject mask (see module docstring)."""
    lab = srgb_to_lab(np.asarray(img.convert('RGB')))
    px = lab[mask]
    n = len(px)
    if n < 2000:
        return None
    L, a, b = px[:, 0], px[:, 1], px[:, 2]
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360.0
    accent = (C >= 45) & (L >= 35) & (h <= 95)
    warm = ~accent & (h >= 20) & (h <= 85) & (C >= 18) & (C < 45) & (L >= 25) & (L <= 72)
    rest = ~accent & ~warm
    t = _otsu(L[rest]) if rest.sum() > 100 else 50.0
    shell, mech = rest & (L >= t), rest & (L < t)
    out = {'otsu': t, 'L_p10': float(np.percentile(L, 10)), 'L_p50': float(np.percentile(L, 50)), 'L_p90': float(np.percentile(L, 90))}
    for name, m in (('shell', shell), ('mechanism', mech), ('warm_metal', warm), ('accent', accent)):
        d = _layer(px[m])
        d['share'] = float(m.sum() / n)
        out[name] = d
    return out


def color_verdict(cur_bg, ref_bg, cur_l, ref_l, layers_on):
    w = []
    G = GATE_COLOR
    if cur_bg and ref_bg:
        dL = cur_bg['L'] - ref_bg['L']
        dE = float(np.linalg.norm([cur_bg['L'] - ref_bg['L'], cur_bg['a'] - ref_bg['a'], cur_bg['b'] - ref_bg['b']]))
        dh = _hue_diff(cur_bg['h'], ref_bg['h']) if max(cur_bg['C'], ref_bg['C']) >= 6 else 0.0
        if abs(dL) > G['bg_dL'] or dE > G['bg_dE'] or dh > G['hue_deg']:
            w.append(f'background differs from the reference: dL {dL:+.1f}, dE {dE:.1f}, hue {dh:.0f} deg '
                     f'(render L{cur_bg["L"]:.0f} h{cur_bg["h"]:.0f} C{cur_bg["C"]:.0f} vs ref L{ref_bg["L"]:.0f} h{ref_bg["h"]:.0f} C{ref_bg["C"]:.0f})')
    if layers_on and cur_l and ref_l:
        s, rs = cur_l['shell'], ref_l['shell']
        if s['L'] is not None and rs['L'] is not None:
            dh = _hue_diff(s['h'], rs['h']) if min(s['C'], rs['C']) >= 5 else 0.0
            if abs(s['L'] - rs['L']) > G['shell_dL'] or dh > G['hue_deg']:
                w.append(f'shell off the reference: dL {s["L"] - rs["L"]:+.1f}, hue {dh:.0f} deg (render L{s["L"]:.0f} h{s["h"]:.0f} vs ref L{rs["L"]:.0f} h{rs["h"]:.0f})')
        m, rm = cur_l['mechanism'], ref_l['mechanism']
        if m['L'] is not None and rm['L'] is not None:
            d = m['L'] - rm['L']
            if d < -G['mech_dark']:
                w.append(f'mechanism darker than the reference by {-d:.1f} L (render {m["L"]:.0f} vs ref {rm["L"]:.0f}): metals read as holes')
            elif d > G['mech_light']:
                w.append(f'mechanism lighter than the reference by {d:.1f} L (render {m["L"]:.0f} vs ref {rm["L"]:.0f})')
        wr, wc = ref_l['warm_metal']['share'], cur_l['warm_metal']['share']
        if wr >= G['warm_ref_min'] and wc < G['warm_ratio'] * wr:
            w.append(f'warm metal missing: share {wc:.3f} vs reference {wr:.3f} (< {G["warm_ratio"]}x): add the copper/bronze the reference shows')
        ar, ac = ref_l['accent']['share'], cur_l['accent']['share']
        if ar >= G['warm_ref_min'] / 2:
            lo, hi = G['accent_ratio']
            if not lo <= ac / ar <= hi:
                w.append(f'accent share {ac:.3f} vs reference {ar:.3f} outside x[{lo}, {hi}]')
    return w


def metal_verdict(roles, ref_l):
    """roles = shots.json `roles` entry written by render.mjs (role-id pass). Warns on dark metals."""
    m = (roles or {}).get('metal')
    if not m or m.get('share', 0) < 0.003:
        return []
    G = GATE_COLOR
    low = m['meanL'] < G['metal_floor']
    ml = ref_l['mechanism']['L'] if ref_l and ref_l['mechanism']['L'] is not None else None
    rel = ml is not None and m['meanL'] < ml - G['metal_vs_mech']
    if low or rel:
        why = f'mean L {m["meanL"]:.0f} of {m["share"]:.1%} of the frame' + (f', reference mechanism layer L {ml:.0f}' if ml is not None else '') + f', floor {G["metal_floor"]:.0f}'
        return [f'metal has nothing bright to reflect: add softbox environment ({why}); if the softbox rig is already on (calibration-lab adds it for metal/glaze roles) the metal base colours themselves are too dark']
    return []



def run_gates(shots_dir, ref_json, style, out_dir, strict=False):
    """Reads shot_###.png + shots.json written by `render.mjs --storyboard --shots-dir`."""
    import glob
    shots = json.load(open(os.path.join(shots_dir, 'shots.json')))
    frames = sorted(f for f in glob.glob(os.path.join(shots_dir, 'shot_*.png')) if not f.endswith('_mask.png'))
    ref = json.load(open(ref_json)) if ref_json and os.path.exists(ref_json) else None
    axis = (ref or {}).get('axis', 'y')
    ref_img = ref_mask = ref_feel = None
    if ref:
        base = os.path.dirname(ref_json)
        ref_img = Image.open(os.path.join(base, ref['image'])).convert('RGB')
        if ref.get('mask'):
            ref_mask = np.asarray(Image.open(os.path.join(base, ref['mask'])).convert('L')) > 127
        else:
            ref_mask = subject_mask(ref_img)
        ref_feel = machine_feel(ref_img, ref_mask, axis)
    ref_bg = ref_layers = None
    if ref_img is not None:
        ref_bg = background_stats(ref_img, ref_mask, [tuple(b['rect']) for b in (ref.get('crop') or {}).get('exclude_boxes_px', [])])
        ref_layers = color_layers(ref_img, ref_mask)
        if ref_bg and ref_layers:
            print(f'  ref colour: background L{ref_bg["L"]:.0f} h{ref_bg["h"]:.0f} C{ref_bg["C"]:.0f} | ' + '  '.join(
                f'{k} {ref_layers[k]["share"]:.2f}/L{ref_layers[k]["L"] or 0:.0f}/h{ref_layers[k]["h"] or 0:.0f}' for k in ('shell', 'mechanism', 'warm_metal', 'accent')))
    norm = FEEL_STYLE_NORM.get(style)
    os.makedirs(out_dir, exist_ok=True)
    results, any_warn = [], False
    print('\n  GATES (ADR-021)  silhouette: ' + ('declared reference ' + ref['image'] if ref else 'no reference declared -> not run') +
          f'   machine-feel baseline: {"reference" if ref_feel else "style norm" if norm and norm["detail"] > 0 else "none (absolute cell map only)"}')
    for i, (fp, sh) in enumerate(zip(frames, shots)):
        img = Image.open(fp).convert('RGB')
        mp = fp[:-4] + '_mask.png'
        # renderer-side mask (render.mjs --shots-dir) when present: colour-independent; else background difference
        mask = (np.asarray(Image.open(mp).convert('L')) > 127) if os.path.exists(mp) else subject_mask(img)
        row = {'shot': f'S{sh["scene"] + 1}.{sh["shot"] + 1}', 'size': sh.get('size'), 'warn': []}
        if mask.sum() < 2000:
            row['warn'].append('no subject mask found')
            results.append(row); continue
        if ref and ref.get('hero_shot') == i:
            # ref.json `frame_clip: [a, b]` = the part (fractions of the frame mask's length) that the reference crop
            # actually shows; needed when the reference crop cuts the subject (horn tip, leg tips).
            clipped = mask
            if ref.get('frame_clip'):
                x0, x1, y0, y1 = _bbox(mask)
                clipped = mask.copy()
                if axis == 'y':
                    ya, yb = int(y0 + (y1 - y0) * ref['frame_clip'][0]), int(y0 + (y1 - y0) * ref['frame_clip'][1])
                    clipped[:ya] = False; clipped[yb:] = False
                else:
                    xa, xb = int(x0 + (x1 - x0) * ref['frame_clip'][0]), int(x0 + (x1 - x0) * ref['frame_clip'][1])
                    clipped[:, :xa] = False; clipped[:, xb:] = False
            row['silhouette'] = silhouette_gate(clipped, ref_mask, axis, ref.get('limb_dominated', False), os.path.join(out_dir, 'silhouette_diff.png'))
            row['warn'] += ['silhouette: ' + m for m in row['silhouette']['warn']]
        # machine-feel runs on the long axis of the visible mask
        x0, x1, y0, y1 = _bbox(mask)
        feel = machine_feel(img, mask, 'x' if (x1 - x0) > (y1 - y0) else 'y')
        if feel:
            base = ref_feel or (norm if norm and norm['detail'] > 0 else None)
            strict_cells = str(sh.get('size')) in ('full', 'wide', 'extreme-wide')
            row['feel'] = {'detail': feel['detail'], 'dark': feel['dark'], 'dark_all': feel['dark_all'], 'dark_material': feel['dark_material'],
                           'cell_min': float(np.nanmin(feel['cells'])) if not np.all(np.isnan(feel['cells'])) else None,
                           'cell_max': float(np.nanmax(feel['cells'])) if not np.all(np.isnan(feel['cells'])) else None}
            if base:
                row['feel']['detail_ratio'] = feel['detail'] / base['detail']
                if base['dark'] >= DARK_REF_MIN:
                    row['feel']['dark_ratio'] = feel['dark'] / base['dark']
            row['warn'] += ['feel: ' + m for m in feel_verdict(feel, base, strict_cells)]
        # colour / value gate (needs a declared reference image) + absolute colour report on every run
        bg = background_stats(img, mask)
        is_ref_shot = bool(ref) and ref.get('hero_shot') == i
        layers_on = is_ref_shot or str(sh.get('size')) in ('full', 'wide', 'extreme-wide')
        lay = color_layers(img, mask)
        row['color'] = {'background': bg, 'layers': lay}
        if ref_bg:
            row['warn'] += ['colour: ' + m for m in color_verdict(bg, ref_bg, lay, ref_layers, layers_on)]
        if sh.get('roles'):
            row['metal'] = sh['roles'].get('metal')
            row['warn'] += ['colour: ' + m for m in metal_verdict(sh['roles'], ref_layers)]
        results.append(row)
        any_warn |= bool(row['warn'])
        f = row.get('feel', {})
        sil = row.get('silhouette')
        print(f'    {row["shot"]:<6} {str(row["size"]):<8} detail {f.get("detail", 0):.3f}' +
              (f' (x{f["detail_ratio"]:.2f})' if 'detail_ratio' in f else '') + f' open {f.get("dark", 0):.3f}' +
              (f' (x{f["dark_ratio"]:.2f})' if 'dark_ratio' in f else '') + f' dark-mat {f.get("dark_material", 0):.3f}' +
              (f' cells {f["cell_min"]:.2f}..{f["cell_max"]:.2f}' if f.get('cell_min') is not None else '') +
              (f'  | IoU {sil["iou_length_aligned"]:.2f} aspect {sil["aspect_dev"]:+.1%} edge {sil["edge_dev_mean"]:.1%}' if sil else ''))
        if bg and lay:
            print(f'           colour: bg L{bg["L"]:.0f} h{bg["h"]:.0f} C{bg["C"]:.0f} | ' + '  '.join(
                f'{k} {lay[k]["share"]:.2f}/L{lay[k]["L"] or 0:.0f}/h{lay[k]["h"] or 0:.0f}' for k in ('shell', 'mechanism', 'warm_metal', 'accent')) +
                (f' | metal L{row["metal"]["meanL"]:.0f} ({row["metal"]["share"]:.1%})' if row.get('metal') else ''))
        for m in row['warn']:
            print(f'           WARN {m}')
    json.dump(results, open(os.path.join(out_dir, 'gates.json'), 'w'), indent=1, default=float)
    print('  gates: ' + ('WARNINGS above (warn-only unless --strict-gates)' if any_warn else 'OK'))
    return any_warn


def gates_for(o, style_dir):
    """Render per-shot PNGs (unless --shots-dir is given) and run the ADR-021 gates for this product."""
    wdir = os.path.dirname(os.path.abspath(o.world)) if o.world else None
    shots_dir = o.shots_dir or os.path.join(style_dir, 'gate_shots')
    if not o.shots_dir:
        cmd = ['node', os.path.join(REPO_ROOT, 'tools', 'render.mjs'), '--style', o.style, '--storyboard', os.path.join(style_dir, 'gate_storyboard.jpg'), '--sheet', os.path.join(style_dir, 'gate_sheet.jpg'), '--shots-dir', shots_dir]
        if o.world:
            cmd += ['--world', o.world]
        if o.content:
            cmd += ['--content', o.content]
        subprocess.run(cmd, check=True, cwd=REPO_ROOT, stdout=subprocess.DEVNULL)
    ref_json = os.path.join(wdir, 'ref.json') if wdir else None
    return run_gates(shots_dir, ref_json, o.style, style_dir, o.strict_gates)


def color_pair(render_png, ref_json, roles_json=None):
    """Print reference vs render colour numbers (ADR-021). Informational + warnings, never fails."""
    ref = json.load(open(ref_json))
    base = os.path.dirname(os.path.abspath(ref_json))
    rimg = Image.open(os.path.join(base, ref['image'])).convert('RGB')
    rmask = np.asarray(Image.open(os.path.join(base, ref['mask'])).convert('L')) > 127 if ref.get('mask') else subject_mask(rimg)
    img = Image.open(render_png).convert('RGB')
    mask = subject_mask(img)
    rb = background_stats(rimg, rmask, [tuple(b['rect']) for b in (ref.get('crop') or {}).get('exclude_boxes_px', [])])
    cb = background_stats(img, mask)
    rl, cl = color_layers(rimg, rmask), color_layers(img, mask)
    print('\n  colour numbers (ADR-021)         reference                 render')
    if rb and cb:
        print(f'    background  L/h/C            {rb["L"]:5.1f} {rb["h"]:5.0f} {rb["C"]:5.1f}        {cb["L"]:5.1f} {cb["h"]:5.0f} {cb["C"]:5.1f}')
    if rl and cl:
        for k in ('shell', 'mechanism', 'warm_metal', 'accent'):
            a, b = rl[k], cl[k]
            f = lambda d: f'{d["share"]*100:4.1f}%  L{(d["L"] or 0):4.0f} h{(d["h"] or 0):4.0f}'
            print(f'    {k:<11} share/L/h       {f(a)}      {f(b)}')
    roles = json.load(open(roles_json)) if roles_json and os.path.exists(roles_json) else {}
    if roles.get('metal'):
        print(f'    metal pixels                 -                         {roles["metal"]["share"]:.1%} of frame, mean L {roles["metal"]["meanL"]:.0f}')
    for m in color_verdict(cb, rb, cl, rl, True) + metal_verdict(roles, rl):
        print('    WARN ' + m)



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--style')
    ap.add_argument('--world')
    ap.add_argument('--content', help='custom scenes.html (same as render.mjs --content)')
    ap.add_argument('--look', help='JSON deep-merged over style.look, e.g. \'{"env":{"enabled":false}}\'')
    ap.add_argument('--tag', default='current', help='name for the rendered sheet ($STYLEHOP_OUT/look/<style>_<tag>.jpg)')
    ap.add_argument('--a')
    ap.add_argument('--b')
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--gates', action='store_true', help='ADR-021 gates: silhouette (needs <world dir>/ref.json) + machine-feel density')
    ap.add_argument('--color-pair', help='one render PNG: print the colour gate numbers against --ref (used by render.mjs --pair)')
    ap.add_argument('--ref', help='ref.json for --color-pair')
    ap.add_argument('--roles', help='json {metal:{share,meanL},...} for --color-pair')
    ap.add_argument('--gates-only', action='store_true', help='run only the gates (implies --gates): no contact sheet, no look baseline written; needs --world')
    ap.add_argument('--strict-gates', action='store_true', help='exit 4 when a gate warns')
    ap.add_argument('--shots-dir', help='reuse an existing render.mjs --shots-dir output instead of re-rendering')
    ap.add_argument('--originality-ref', action='append', default=[],
                    help='extra reference sheet(s) for the originality gate (repeatable)')
    o = ap.parse_args()

    if o.color_pair:
        color_pair(o.color_pair, o.ref, o.roles)
        return
    if o.gates_only:
        if not o.style:
            ap.error('--gates-only needs --style (and --world for a product; without it the style default world is checked, no reference)')
        key = os.path.basename(os.path.dirname(os.path.abspath(o.world))) if o.world else f'{o.style}-default'
        gdir = os.path.join(OUT_ROOT, 'look', f'gates__{key}')
        os.makedirs(gdir, exist_ok=True)
        o.gates = True
        warn = gates_for(o, gdir)
        if warn and o.strict_gates:
            sys.exit(4)
        return
    if o.a and o.b:
        _, drift = compare(o.a, o.b)
    elif o.style:
        style_dir = os.path.join(REPO_ROOT, 'styles', o.style)
        baseline = os.path.join(style_dir, 'look_baseline.jpg')
        if o.world:
            # A custom story world has different content, so it gets its own (uncommitted) baseline;
            # the first run stores it, later runs guard that world's look.
            # Keyed by the PRODUCT DIRECTORY (<world dir name>), not the file stem: every product's file is called world.js,
            # so the stem made different products share one baseline (calibration-lab__world). Legacy dirs are never reused.
            wabs = os.path.abspath(o.world)
            key = os.path.basename(os.path.dirname(wabs)) or os.path.splitext(os.path.basename(wabs))[0]
            style_dir = os.path.join(OUT_ROOT, 'look', f'{o.style}__{key}')
            legacy = os.path.join(OUT_ROOT, 'look', f'{o.style}__{os.path.splitext(os.path.basename(wabs))[0]}')
            if os.path.isdir(legacy) and not os.path.isdir(style_dir):
                print(f'  note: legacy baseline dir {os.path.relpath(legacy, REPO_ROOT)} exists (keyed by file stem, shared by every product '
                      f'called world.js); this run stores a fresh baseline in {os.path.relpath(style_dir, REPO_ROOT)}. Move the legacy dir there if it is this product\'s.')
            os.makedirs(style_dir, exist_ok=True)
            baseline = os.path.join(style_dir, 'look_baseline.jpg')
        current = os.path.join(OUT_ROOT, 'look', f'{o.style}_{o.tag}.jpg')
        os.makedirs(os.path.dirname(current), exist_ok=True)
        render_sheet(o.style, current, o.world, o.look, o.content)
        abs_fails = absolute_check(current, style=o.style)
        orig_fails = originality_check(
            current,
            originality_references(o.style, own_dir=style_dir if o.world else None, is_showcase=not o.world, extra=o.originality_ref),
        )
        if o.accept or not os.path.exists(baseline):
            first = not os.path.exists(baseline)
            shutil.copyfile(current, baseline)
            img = Image.open(baseline).convert('RGB')
            with open(os.path.join(style_dir, 'look_baseline.json'), 'w') as f:
                json.dump([measure(p)[0] for p in panels(img)], f, indent=2)
            print(f'  baseline stored: {os.path.relpath(baseline, REPO_ROOT)}')
            if o.gates:
                gates_for(o, style_dir)
            if first:
                print('  (first run: nothing was compared; later runs guard this look against drift)')
            if orig_fails:
                sys.exit(3)
            if abs_fails and o.strict:
                sys.exit(2)
            return
        gates_warn = False
        if o.gates:
            gates_warn = gates_for(o, style_dir)
        _, drift = compare(baseline, current, os.path.join(OUT_ROOT, 'look', f'{o.style}_{o.tag}_compare.jpg'))
        drift = drift or []
        if orig_fails:
            sys.exit(3)
        if abs_fails and o.strict:
            sys.exit(2)
        if gates_warn and o.strict_gates:
            sys.exit(4)
    else:
        ap.error('pass --style <id> or --a/--b')
        return

    if drift:
        print('\n  DRIFT beyond guard (intentional? re-run with --accept):')
        for i, flags in drift:
            print(f'    panel {i}: ' + ', '.join(flags))
        if o.strict:
            sys.exit(2)
    else:
        print('\n  OK · within guard')


if __name__ == '__main__':
    main()
