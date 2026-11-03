#!/usr/bin/env node
/**
 * StyleHop Automated DOM-Native Style Auditor (`tools/audit.mjs`).
 *
 * Opens a style in Headless Chrome 157+ via `gallery/player.html?style=<id>&size=<WxH>&mode=offline`,
 * steps deterministically across all scenes (0..DUR at 0.15s steps + each scene's settle timestamp),
 * and verifies 5 hard quality gates:
 *   1. Zero Runtime / Shader Errors (`pageerror`, `console.error`, WebGL context errors)
 *   2. DOM Overflow & Viewport Bounds (every visible leaf text node inside [0, 0, W, H], no horizontal clip)
 *   3. Minimum Font Size (`computed fontSize >= 12px` at 1080p equivalent)
 *   4. Reading Hold Duration (`CJK/5.5 + Latin/18 + 0.8s` on primary scene narrative copy <= scene `data-dur`)
 *   5. Floating Layer Occlusion (`[data-layer]` cards overlap <= 30% of any `[data-focus]` target in the scene)
 *   6. Facts (with `--facts "..."`): every number on screen is a user fact, a `data-derived` formula over
 *      them, or a labelled `data-illustrative` example — no invented figures (see `tools/factcheck.mjs`)
 *   8. Framing (ADR-021, warn by default, `--framing-strict` fails): per storyboard shot, the share of the visible 3D
 *      subject (vertex samples of every visible mesh below `world.subjectRoot || scene`, HUD / bench / contact-shadow
 *      planes excluded) that lies inside the free area (default: the frame minus a 5% margin; `--free x0,y0,x1,y1`
 *      as fractions, or `free` in `<world dir>/ref.json`). Needs the world to expose `scene` + `camera`.
 *      Full / wide shots must keep >= 85%; closer shots are reported only (the subject may leave the frame on purpose).
 *   9. Metal brightness (ADR-021, warn only): per shot, mean CIE L* of the pixels whose material role is metal (role-id pass,
 *      `engine/studio3d.js roleReport`); below METAL_FLOOR (30) -> "metal has nothing bright to reflect: add softbox environment".
 *      The comparison with the reference's mechanism layer is done by `lookcheck.py --gates`.
 *  10. Self-review checklist (ADR-021, warn only; `--notes-strict` fails): a product (`--world`) must carry the fixed checklist
 *      block from styles/calibration-lab/SPEC.md §9 in its `NOTES.md` (heading "自检清单" + the six items, each answered).
 *   7. Originality (with a custom `--world`): at most 30% of the topic's composition lines (lines with
 *      numbers) may be copied verbatim from the style's showcase `world.js`. Kernels may also report
 *      contract violations (e.g. a placement primitive called without placement) via `console.error`,
 *      which gate 1 turns into a failure.
 *
 * Usage:
 *   node tools/audit.mjs --style clay-macaron [--size 1920x1080] [--all-sizes] [--facts "营收1280万, 同比32%"]
 *   node tools/audit.mjs --style vintage-naturalist --all-sizes --min-font 23
 *   node tools/audit.mjs --style calibration-lab --world <product>/world.js --content <product>/scenes.html --all-sizes [--framing-strict] [--free x0,y0,x1,y1]
 *     (a product world needs BOTH --world and --content; baselines / gates for the same product: tools/lookcheck.py --gates, reference side by side: tools/render.mjs --pair)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { launchHtmlCanvasBrowser, createHtmlCanvasPage } from '../engine/browser.mjs';
import { startStaticServer } from '../engine/server.mjs';
import { extractFacts, collectPageNumbers, checkNumbers, FACT_HELP } from './factcheck.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function rel(p) {
  const abs = path.resolve(p);
  // A product under $STYLEHOP_OUT (e.g. a scratch copy) is served by engine/server.mjs as /out/<path inside STYLEHOP_OUT>.
  if (process.env.STYLEHOP_OUT) {
    const outRoot = path.resolve(process.env.STYLEHOP_OUT);
    const r = path.relative(outRoot, abs);
    if (!r.startsWith('..') && !path.isAbsolute(r)) return 'out/' + r.split(path.sep).join('/');
  }
  return path.relative(REPO_ROOT, abs).split(path.sep).join('/');
}

function parseArgs(argv) {
  const o = {
    style: 'clay-macaron',
    content: null,
    world: null,
    sizes: ['1920x1080', '1080x1920'],
    step: 0.15,
    json: false,
    facts: null,
    minFont: null,
    free: null,
    framingStrict: false,
    notesStrict: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === '--style') o.style = next();
    else if (a === '--content') o.content = next();
    else if (a === '--world') o.world = next();
    else if (a === '--size') o.sizes = next().split(',');
    else if (a === '--all-sizes') o.sizes = ['1920x1080', '1080x1920', '1080x1080'];
    else if (a === '--step') o.step = parseFloat(next());
    else if (a === '--json') o.json = true;
    else if (a === '--facts') o.facts = next();
    else if (a === '--min-font') o.minFont = parseFloat(next());
    else if (a === '--free') o.free = next().split(',').map(Number);
    else if (a === '--framing-strict') o.framingStrict = true;
    else if (a === '--notes-strict') o.notesStrict = true;
  }
  return o;
}

// Max share of a topic world's composition lines (lines carrying numeric literals) that may be copied
// verbatim from the style's showcase `world.js`.
const ORIGINALITY_MAX_SHARED = 0.3;

/**
 * Static originality scan: a custom `--world` must not be the showcase world with the names changed.
 * Compares whitespace-normalised source lines that contain a number (coordinates, timings, scales —
 * the composition fingerprint) against the style's own `world.js`.
 */
function originalityScan(opts) {
  const none = { checked: false, passed: true };
  if (!opts.world) return none;
  const sample = path.join(REPO_ROOT, 'styles', opts.style, 'world.js');
  const topic = path.resolve(opts.world);
  if (!fs.existsSync(sample) || !fs.existsSync(topic) || path.resolve(sample) === topic) return none;
  const norm = (src) =>
    src
      .split(/\r?\n/)
      .map((l) => l.trim().replace(/\s+/g, ' '))
      .filter((l) => l.length >= 24 && /\d/.test(l) && !/^(\/\/|\*|\/\*|import |export )/.test(l));
  const sampleSet = new Set(norm(fs.readFileSync(sample, 'utf8')));
  const lines = norm(fs.readFileSync(topic, 'utf8'));
  const copied = lines.filter((l) => sampleSet.has(l));
  const ratio = lines.length ? copied.length / lines.length : 0;
  return {
    checked: true,
    passed: ratio < ORIGINALITY_MAX_SHARED,
    shared: copied.length,
    total: lines.length,
    ratio,
    sample: rel(sample),
    examples: copied.slice(0, 5),
  };
}

async function auditSize(browser, baseUrl, opts, sizeStr, stepSec) {
  const styleId = opts.style;
  const [width, height] = sizeStr.split('x').map(Number);
  const page = await createHtmlCanvasPage(browser, { width, height });
  const runtimeErrors = [];

  page.on('console', (m) => {
    if (m.type() === 'error') runtimeErrors.push(`console.error: ${m.text()}`);
  });
  page.on('pageerror', (e) => {
    runtimeErrors.push(`pageerror: ${e.message}`);
  });

  const q = new URLSearchParams({ style: styleId, size: sizeStr, mode: 'offline' });
  if (opts.content) {
    const content = opts.content.endsWith('.html') ? '/' + rel(opts.content) : opts.content;
    q.set('content', content);
  }
  if (opts.world) {
    const world = opts.world.endsWith('.js') || opts.world.endsWith('.mjs') ? '/' + rel(opts.world) : opts.world;
    q.set('world', world);
  }
  const url = `${baseUrl}/gallery/player.html?${q}`;
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.READY === true, null, { timeout: 30000 });

  const meta = await page.evaluate(() => ({
    dur: window.DUR,
    cues: window.CUES || { scenes: [], cues: [] },
  }));

  const scenes = meta.cues.scenes?.length
    ? meta.cues.scenes
    : [{ index: 0, id: 'main', title: 'Main', start: 0, dur: meta.dur, end: meta.dur, settle: +(meta.dur * 0.75).toFixed(2) }];

  // Step through timeline at `stepSec` intervals to verify deterministic motion, shader execution,
  // and collect peak-action spatial/interaction issues across all frames.
  const timelineSpatialIssuesByScene = new Map();
  for (let t = 0; t <= meta.dur + 1e-6; t += stepSec) {
    const clamped = Math.min(meta.dur, +t.toFixed(3));
    const stepAudit = await page.evaluate((ts) => {
      if (window.__STYLEHOP_SPATIAL_AUDIT) {
        window.__STYLEHOP_SPATIAL_AUDIT.issues = [];
        window.__STYLEHOP_SPATIAL_AUDIT.interactions = [];
      }
      window.render(ts);
      const sp = window.__STYLEHOP_SPATIAL_AUDIT;
      if (!sp) return null;
      const iss = [...(sp.issues || [])];
      for (const inter of sp.interactions || []) {
        if (inter.passed === false) {
          iss.push({
            kind: 'interaction_miss',
            detail: `3D action "${inter.verb}" missed target (${inter.dist} > maxDist=${inter.maxDist})`,
          });
        }
      }
      return iss.length ? iss : null;
    }, clamped);

    if (stepAudit && stepAudit.length) {
      const ownerSc =
        scenes.find((s) => clamped >= s.start - 1e-4 && clamped <= s.end + 1e-4) || scenes[scenes.length - 1];
      if (ownerSc) {
        if (!timelineSpatialIssuesByScene.has(ownerSc.id)) {
          timelineSpatialIssuesByScene.set(ownerSc.id, new Map());
        }
        const map = timelineSpatialIssuesByScene.get(ownerSc.id);
        for (const item of stepAudit) {
          const key = `${item.kind}:${item.detail}`;
          if (!map.has(key)) map.set(key, { kind: item.kind, detail: `${item.detail} (at t=${clamped.toFixed(2)}s)` });
        }
      }
    }
  }

  const totalCueCount = await page.evaluate(() => window.CUES?.cues?.length || 0);

  const baseMinFont = Number.isFinite(opts.minFont) ? opts.minFont : 12;
  const minFontPx = Math.max(10, Math.round((Math.min(width, height) / 1080) * baseMinFont));
  const sceneReports = [];

  for (const sc of scenes) {
    const settleT = sc.settle ?? +(sc.start + sc.dur * 0.78).toFixed(3);
    await page.evaluate((ts) => {
      if (window.__STYLEHOP_SPATIAL_AUDIT) {
        window.__STYLEHOP_SPATIAL_AUDIT.issues = [];
        window.__STYLEHOP_SPATIAL_AUDIT.interactions = [];
      }
      window.render(ts);
    }, settleT);

    const check = await page.evaluate(
      ({ width, height, minFontPx, sc }) => {
        const stage = document.getElementById('stage');
        const cr = stage.getBoundingClientRect();
        const frame =
          stage.querySelector(':scope > .frame[data-active="true"]') ||
          [...stage.querySelectorAll(':scope > .frame')].find((el) => el.style.display !== 'none');

        const issues = [];
        if (!frame) {
          issues.push({ kind: 'missing_scene', detail: `No active .frame for scene ${sc.id}` });
          return { issues, stats: {} };
        }

        const isVisible = (el) => {
          for (let cur = el; cur && cur !== stage; cur = cur.parentElement) {
            const cs = getComputedStyle(cur);
            if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false;
          }
          const r = el.getBoundingClientRect();
          return r.width > 0.5 && r.height > 0.5;
        };

        // 1. Leaf text elements: bounds, overflow, min font size
        let leafCount = 0;
        let minObservedFont = Infinity;
        const allEls = [...frame.querySelectorAll('*')];
        for (const el of allEls) {
          if (el.closest('svg, math')) continue;
          const hasDirectText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 0);
          if (!hasDirectText) continue;
          if (!isVisible(el)) continue;

          leafCount++;
          const r = el.getBoundingClientRect();
          const left = r.left - cr.left;
          const top = r.top - cr.top;
          const right = r.right - cr.left;
          const bottom = r.bottom - cr.top;
          const cs = getComputedStyle(el);
          const fontPx = parseFloat(cs.fontSize) || 0;
          if (fontPx < minObservedFont) minObservedFont = fontPx;

          const textSample = el.textContent.trim().slice(0, 32);

          if (left < -2 || top < -2 || right > width + 2 || bottom > height + 2) {
            issues.push({
              kind: 'out_of_bounds',
              detail: `"${textSample}" rect [${Math.round(left)}, ${Math.round(top)}, ${Math.round(right)}, ${Math.round(bottom)}] outside [0, 0, ${width}, ${height}]`,
            });
          }

          if ((cs.overflowX === 'hidden' || cs.overflowX === 'clip') && el.scrollWidth > el.clientWidth + 2) {
            issues.push({
              kind: 'text_overflow',
              detail: `"${textSample}" horizontal clip (${el.scrollWidth}px > ${el.clientWidth}px)`,
            });
          }

          if (fontPx + 0.25 < minFontPx) {
            issues.push({
              kind: 'small_font',
              detail: `"${textSample}" font-size ${fontPx.toFixed(1)}px < min ${minFontPx}px`,
            });
          }
        }

        // 2. Reading hold duration on primary scene narrative copy (.title, .lead, .vertical), if any
        const narrativeNodes = frame.querySelectorAll('.title, .lead, .vertical');
        let narrativeText = '';
        for (const n of narrativeNodes) {
          if (isVisible(n)) narrativeText += ' ' + n.textContent;
        }
        const cjkChars = (narrativeText.match(/[\u4e00-\u9fff]/g) || []).length;
        const latinChars = (narrativeText.match(/[A-Za-z0-9]/g) || []).length;
        const requiredDur =
          cjkChars === 0 && latinChars === 0 ? 0 : +(cjkChars / 5.5 + latinChars / 18 + 0.8).toFixed(2);
        if (requiredDur > sc.dur + 0.15) {
          issues.push({
            kind: 'reading_hold',
            detail: `Scene "${sc.id}" narrative copy needs ${requiredDur}s (CJK=${cjkChars}, Latin=${latinChars}) > data-dur=${sc.dur}s`,
          });
        }

        // 3. Floating [data-layer] occlusion against [data-focus] elements
        const focusEls = [...frame.querySelectorAll('[data-focus]')].filter(isVisible);
        const activeLayers = [...stage.querySelectorAll(':scope > [data-layer]')].filter(
          (l) => l.style.display !== 'none' && isVisible(l)
        );
        let maxOcclusion = 0;

        for (const layer of activeLayers) {
          const lr = layer.getBoundingClientRect();
          for (const focusEl of focusEls) {
            const fr = focusEl.getBoundingClientRect();
            const ix = Math.max(0, Math.min(lr.right, fr.right) - Math.max(lr.left, fr.left));
            const iy = Math.max(0, Math.min(lr.bottom, fr.bottom) - Math.max(lr.top, fr.top));
            const inter = ix * iy;
            const fArea = Math.max(1, fr.width * fr.height);
            const ratio = inter / fArea;
            if (ratio > maxOcclusion) maxOcclusion = ratio;
            if (ratio > 0.3) {
              issues.push({
                kind: 'layer_occlusion',
                detail: `[data-layer] overlaps ${(ratio * 100).toFixed(1)}% (> 30%) of [data-focus] (${focusEl.className || focusEl.tagName})`,
              });
            }
          }
        }

        // 4. Spatial Semantics Gate: 2D Z-order inversions, ground contact & 2D/3D interaction contact distance
        const sp = window.__STYLEHOP_SPATIAL_AUDIT;
        let spatialElements = 0;
        let interactionsChecked = 0;
        if (sp) {
          spatialElements = sp.elements?.length || 0;
          interactionsChecked = sp.interactions?.length || 0;
          for (const sIss of sp.issues || []) {
            issues.push({ kind: sIss.kind, detail: sIss.detail });
          }
          for (const inter of sp.interactions || []) {
            if (inter.passed === false) {
              issues.push({
                kind: 'interaction_miss',
                detail: `Action "${inter.verb}" missed target (${inter.dist} > maxDist=${inter.maxDist})`,
              });
            }
          }
        }

        return {
          issues,
          stats: {
            leafCount,
            minFontPx: minObservedFont === Infinity ? null : +minObservedFont.toFixed(1),
            cjkChars,
            latinChars,
            requiredDur,
            sceneDur: sc.dur,
            maxOcclusionPct: +(maxOcclusion * 100).toFixed(1),
            spatialElements,
            interactionsChecked,
          },
        };
      },
      { width, height, minFontPx, sc }
    );

    // Merge any timeline peak-action spatial issues that occurred during this scene
    const scTimelineIssues = timelineSpatialIssuesByScene.get(sc.id);
    if (scTimelineIssues) {
      const existingKeys = new Set(check.issues.map((i) => `${i.kind}:${i.detail.replace(/ \(at t=.*$/, '')}`));
      for (const [k, item] of scTimelineIssues.entries()) {
        if (!existingKeys.has(k)) {
          check.issues.push(item);
        }
      }
    }

    sceneReports.push({
      scene: sc.id,
      title: sc.title,
      window: `${sc.start.toFixed(1)}s–${sc.end.toFixed(1)}s`,
      settle: settleT,
      passed: check.issues.length === 0,
      issues: check.issues,
      stats: check.stats,
    });
  }

  // Facts gate: numbers on screen must come from the user (checked once, at the first size).
  let factIssues = [];
  if (opts.facts !== null && sizeStr === opts.sizes[0]) {
    factIssues = checkNumbers(await collectPageNumbers(page), extractFacts(opts.facts));
  }

  await page.close();
  const passed = runtimeErrors.length === 0 && factIssues.length === 0 && sceneReports.every((r) => r.passed);
  return { size: sizeStr, dur: meta.dur, cueCount: totalCueCount || meta.cues.cues?.length || 0, passed, runtimeErrors, factIssues, scenes: sceneReports };
}

const FRAMING_MIN = 0.85;
const METAL_FLOOR = 30; // mean L* of role=metal pixels below this = metals read as holes (ADR-021)
const NOTES_ITEMS = [['mechanism', /机构|mechanism/i], ['background hue', /背景.*色相|background/i], ['accents', /点缀|accent/i], ['appendages', /附肢|触手|appendage/i], ['glaze highlights', /釉面高光|glaze/i], ['大疏大密', /大疏大密/]];

/** ADR-021 self-review checklist presence in <product>/NOTES.md (warn only). */
function notesCheck(opts) {
  if (!opts.world) return { checked: false };
  const f = path.join(path.dirname(path.resolve(opts.world)), 'NOTES.md');
  if (!fs.existsSync(f)) return { checked: true, ok: false, why: 'NOTES.md missing' };
  const t = fs.readFileSync(f, 'utf8');
  const i = t.search(/自检清单/);
  if (i < 0) return { checked: true, ok: false, why: 'no "自检清单" block (copy the template from styles/calibration-lab/SPEC.md §9)' };
  const block = t.slice(i);
  const missing = NOTES_ITEMS.filter(([, re]) => !re.test(block)).map(([n]) => n);
  const unanswered = (block.match(/\[\s\]/g) || []).length;
  if (missing.length) return { checked: true, ok: false, why: `checklist items missing: ${missing.join(', ')}` };
  if (unanswered) return { checked: true, ok: false, why: `${unanswered} checklist item(s) still unchecked "[ ]" (answer each with [x] or [!] plus a note)` };
  return { checked: true, ok: true };
}

/** ADR-021 framing check: where does the visible subject sit relative to the free area, shot by shot. */
async function framingCheck(browser, baseUrl, opts, sizeStr) {
  const [width, height] = sizeStr.split('x').map(Number);
  let free = opts.free;
  if (!free && opts.world) {
    const rj = path.join(path.dirname(path.resolve(opts.world)), 'ref.json');
    if (fs.existsSync(rj)) free = JSON.parse(fs.readFileSync(rj, 'utf8')).free || null;
  }
  free = free || [0.05, 0.05, 0.95, 0.95];
  const page = await createHtmlCanvasPage(browser, { width, height });
  const q = new URLSearchParams({ style: opts.style, size: sizeStr, mode: 'offline' });
  if (opts.content) q.set('content', opts.content.endsWith('.html') ? '/' + rel(opts.content) : opts.content);
  if (opts.world) q.set('world', opts.world.endsWith('.js') || opts.world.endsWith('.mjs') ? '/' + rel(opts.world) : opts.world);
  await page.goto(`${baseUrl}/gallery/player.html?${q}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.READY === true, null, { timeout: 30000 });
  const shots = await page.evaluate(() => window.SHOTS || null);
  const has = await page.evaluate(() => !!(window.WORLD && window.WORLD.scene && window.WORLD.camera));
  if (!shots || !has) {
    await page.close();
    return { checked: false, passed: true, rows: [], free };
  }
  const rows = [];
  for (const sh of shots) {
    const r = await page.evaluate(async ({ t, free }) => {
      await window.render(t);
      const metal = window.__stylehopStudio && window.__stylehopStudio.roleReport ? (window.__stylehopStudio.roleReport().metal || null) : null;
      const { scene, camera } = window.WORLD;
      const root = window.WORLD.subjectRoot || scene;
      scene.updateMatrixWorld(true);
      camera.updateMatrixWorld(true);
      const THREE = window.THREE || null;
      const pts = [];
      const v = { x: 0, y: 0, z: 0 };
      const proj = camera.projectionMatrix.elements;
      const inv = camera.matrixWorldInverse.elements;
      const project = (x, y, z, out) => {
        const cx = inv[0] * x + inv[4] * y + inv[8] * z + inv[12];
        const cy = inv[1] * x + inv[5] * y + inv[9] * z + inv[13];
        const cz = inv[2] * x + inv[6] * y + inv[10] * z + inv[14];
        const w = -cz;
        if (w <= 1e-4) return false;
        out[0] = (proj[0] * cx) / w * 0.5 + 0.5;
        out[1] = 0.5 - (proj[5] * cy) / w * 0.5;
        return true;
      };
      let total = 0, inFrame = 0, inFree = 0;
      const o = [0, 0];
      root.traverse((m) => {
        if (!m.isMesh || m.userData?.isHudOverlay || m.userData?.skipContactShadow || m.userData?.auditIgnore) return;
        for (let p = m; p; p = p.parent) if (p.visible === false) return;
        const pos = m.geometry?.attributes?.position;
        if (!pos) return;
        const e = m.matrixWorld.elements;
        const stride = Math.max(1, Math.floor(pos.count / 400));
        const inst = m.isInstancedMesh ? Math.min(m.count, 64) : 1;
        for (let k = 0; k < inst; k++) {
          const me = e;
          for (let i = 0; i < pos.count; i += stride) {
            const px = pos.getX(i), py = pos.getY(i), pz = pos.getZ(i);
            const x = me[0] * px + me[4] * py + me[8] * pz + me[12];
            const y = me[1] * px + me[5] * py + me[9] * pz + me[13];
            const z = me[2] * px + me[6] * py + me[10] * pz + me[14];
            if (!project(x, y, z, o)) continue;
            total++;
            if (o[0] >= 0 && o[0] <= 1 && o[1] >= 0 && o[1] <= 1) {
              inFrame++;
              if (o[0] >= free[0] && o[0] <= free[2] && o[1] >= free[1] && o[1] <= free[3]) inFree++;
            }
          }
          if (inst > 1) break; // instanced: one representative instance is enough for a share estimate
        }
      });
      return { total, inFrame, inFree, metal };
    }, { t: sh.t, free });
    const inFreeShare = r.inFrame ? r.inFree / r.inFrame : 0;
    const visible = r.total ? r.inFrame / r.total : 0;
    const strict = ['full', 'wide', 'extreme-wide'].includes(String(sh.size));
    rows.push({ shot: `S${sh.scene + 1}.${sh.shot + 1}`, size: sh.size, inFreeShare, visible, strict, metal: r.metal, ok: !strict || inFreeShare >= FRAMING_MIN });
  }
  await page.close();
  return { checked: true, passed: rows.every((r) => r.ok), rows, free };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const originality = originalityScan(opts);
  const { server, baseUrl } = await startStaticServer(REPO_ROOT);
  const browser = await launchHtmlCanvasBrowser();

  try {
    const results = [];
    for (const sz of opts.sizes) {
      results.push(await auditSize(browser, baseUrl, opts, sz, opts.step));
    }

    const framing = await framingCheck(browser, baseUrl, opts, opts.sizes[0]);
    const notes = notesCheck(opts);
    const allPassed = results.every((r) => r.passed) && originality.passed && (!opts.framingStrict || framing.passed) && (!opts.notesStrict || !notes.checked || notes.ok);
    if (opts.json) {
      console.log(JSON.stringify({ style: opts.style, passed: allPassed, originality, framing, notes, results }, null, 2));
    } else {
      for (const r of results) {
        console.log(`\n=== StyleHop DOM Audit · style=${opts.style} · size=${r.size} · dur=${r.dur}s · cues=${r.cueCount} ===`);
        if (r.runtimeErrors.length) {
          for (const err of r.runtimeErrors) console.log(`  [FAIL] ${err}`);
        }
        for (const sc of r.scenes) {
          const badge = sc.passed ? 'PASS' : 'FAIL';
          console.log(
            `  [${badge}] Scene "${sc.scene}" (${sc.window}, settle=${sc.settle}s) · leaves=${sc.stats.leafCount} · minFont=${sc.stats.minFontPx}px · read=${sc.stats.requiredDur}s/${sc.stats.sceneDur}s · maxOcc=${sc.stats.maxOcclusionPct}%`
          );
          for (const iss of sc.issues) {
            console.log(`         -> [${iss.kind}] ${iss.detail}`);
          }
        }
        if (opts.facts !== null && r.size === opts.sizes[0]) {
          console.log(`  [${r.factIssues.length ? 'FAIL' : 'PASS'}] Facts · user gave: ${opts.facts}`);
          for (const iss of r.factIssues) console.log(`         -> [${iss.kind}] scene "${iss.scene}": ${iss.detail}`);
          if (r.factIssues.length) console.log(`         ${FACT_HELP}`);
        }
      }
      if (originality.checked) {
        console.log(
          `\n  [${originality.passed ? 'PASS' : 'FAIL'}] Originality · ${originality.shared}/${originality.total} composition lines ` +
            `(${(originality.ratio * 100).toFixed(1)}%) copied from ${originality.sample} (limit ${(ORIGINALITY_MAX_SHARED * 100).toFixed(0)}%)`
        );
        if (!originality.passed) {
          for (const l of originality.examples) console.log(`         -> copied: ${l}`);
          console.log('         Compose this topic yourself: the showcase world is a reference, not a template (see the style SPEC).');
        }
      }
      if (framing.checked) {
        console.log(`\n  Framing (free area ${framing.free.map((v) => v.toFixed(2)).join(',')}; full/wide need >= ${(FRAMING_MIN * 100).toFixed(0)}% of the visible subject inside; ${opts.framingStrict ? 'STRICT' : 'warn-only'})`);
        for (const r of framing.rows) {
          console.log(`    [${r.ok ? 'ok  ' : 'WARN'}] ${r.shot.padEnd(6)} ${String(r.size).padEnd(8)} in-free ${(r.inFreeShare * 100).toFixed(0).padStart(3)}%  in-frame ${(r.visible * 100).toFixed(0).padStart(3)}%${r.strict ? '' : '  (info only)'}`);
        }
        const mrows = framing.rows.filter((r) => r.metal && r.metal.share >= 0.003);
        if (mrows.length) {
          console.log(`\n  Metal brightness (role-id pass; warn only, floor L* ${METAL_FLOOR})`);
          for (const r of mrows) {
            const low = r.metal.meanL < METAL_FLOOR;
            console.log(`    [${low ? 'WARN' : 'ok  '}] ${r.shot.padEnd(6)} metal ${(r.metal.share * 100).toFixed(1).padStart(5)}% of frame, mean L* ${r.metal.meanL.toFixed(0)}${low ? '  -> metal has nothing bright to reflect: add softbox environment' : ''}`);
          }
        }
      } else {
        console.log('\n  Framing: skipped (world exposes no scene/camera or no storyboard)');
      }
      if (notes.checked) {
        console.log(`\n  Self-review checklist (NOTES.md): ${notes.ok ? 'ok' : 'WARN ' + notes.why}${notes.ok || !opts.notesStrict ? '' : '  [STRICT]'}`);
      }
      console.log(`\nAudit result: ${allPassed ? 'PASSED (0 issues)' : 'FAILED'}`);
    }

    if (!allPassed) process.exitCode = 1;
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
