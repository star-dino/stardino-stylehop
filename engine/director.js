/**
 * Shot-List Director (`engine/director.js`).
 *
 * A scene is not one camera move: it is a short list of shots with hard cuts between them.
 * Each shot names WHAT to look at (`subject`) and HOW BIG it should read (`size`); the director
 * measures the subject and computes the camera distance for the actual aspect ratio, so the
 * same shot list frames correctly at 16:9, 9:16 and 1:1 and never needs hand-tuned positions.
 *
 *   const director = createDirector(THREE, { camera, scenes, subjects: { bear, door }, shots: {
 *     'lost-in-woods': [
 *       { dur: 1.4, size: 'wide',  subject: 'forest', height: 'high', move: 'push' },
 *       { dur: 1.0, size: 'close', subject: 'bearHead', angle: 25 },
 *       {           size: 'full',  subject: 'bear', angle: -35, move: 'orbit', follow: true },
 *     ],
 *   } });
 *   // per frame: director.update(frame); studio.render();
 *
 * Shot fields:
 *   dur      seconds; shots without `dur` share the rest of the scene equally
 *   subject  name in `subjects` | Object3D | { center: [x,y,z], size: [w,h,d] } | array (union);
 *            a `subjects` entry may itself be an array (frames the group of props together)
 *   size     'extreme-wide' | 'wide' | 'full' | 'medium' | 'close' | 'extreme-close'
 *            (ews/ws/fs/ms/cu/ecu) — how much of the frame the subject fills
 *   angle    yaw in degrees around the subject; 0 = from the front (+z), + = camera to the right;
 *            for subjects with `userData.facing` (puppets) 0 = in front of the character's face
 *   height   'low' | 'eye' | 'high' | 'top' or elevation in degrees
 *   move     'static' | 'push' | 'pull' | 'orbit' | 'rise' | 'drop' | 'truck', combine with '+'
 *   amount   move strength multiplier (default 1)
 *   place    'center' | 'left' | 'right' — put the subject on a third of the frame
 *   focus    vertical aim inside the subject box, 0 = bottom … 1 = top
 *   follow   true = track the subject's live x/z, 'xyz' = also y; default frames its rest pose
 *            (subjects with `userData.follow`, e.g. puppets, follow by default)
 *   fov      lens override in degrees (scaled for portrait/square like the base fov)
 *   ease     'smooth' | 'linear' | 'ease-out' | 'ease-in'
 *   roll / rollDeg, sway   gentle camera drift; there is no camera shake by default (`boil` /
 *            `impacts` are ignored unless `shake: true`, then capped) — show impacts on props
 *
 * Subjects are measured once when the director is created, so build props at their rest pose
 * before calling `createDirector`.
 */

import { clamp, lerp, smootherstep } from './motion.js';
import { applyMicroMotion, applyThreeCamera } from './camera.js';

// `fill`: projected span of the subject box relative to the frame (1 = edge to edge).
// Sizes describe the subject you name. A subject can carry hints in
// `userData.shotTargets` (puppets do): `close` on a character then frames its head and
// `medium` its upper body, using `HINT_FILL` on that part instead.
export const SHOT_SIZES = {
  'extreme-wide': { fill: 0.45, focus: 0.5 },
  wide: { fill: 0.68, focus: 0.5 },
  full: { fill: 0.8, focus: 0.5 },
  medium: { fill: 0.95, focus: 0.54 },
  close: { fill: 1.1, focus: 0.52 },
  'extreme-close': { fill: 1.6, focus: 0.56 },
};
const HINT_FILL = { medium: 0.9, close: 0.82, 'extreme-close': 1.25 };
const SIZE_ALIASES = { ews: 'extreme-wide', ws: 'wide', fs: 'full', ms: 'medium', cu: 'close', ecu: 'extreme-close' };
const SIZE_ORDER = ['extreme-wide', 'wide', 'full', 'medium', 'close', 'extreme-close'];

export const SHOT_HEIGHTS = { low: 4, eye: 14, high: 32, top: 64 };

const DEG = Math.PI / 180;

function ease(u, mode = 'smooth') {
  const x = clamp(u, 0, 1);
  if (mode === 'linear') return x;
  if (mode === 'ease-out') return 1 - Math.pow(1 - x, 3);
  if (mode === 'ease-in') return x * x * x;
  return smootherstep(0, 1, x);
}

export function resolveSize(size) {
  const name = SIZE_ALIASES[size] || size || 'full';
  return { name, ...(SHOT_SIZES[name] || SHOT_SIZES.full) };
}

function resolveHeight(h) {
  if (typeof h === 'number') return h;
  return SHOT_HEIGHTS[h] ?? SHOT_HEIGHTS.eye;
}

function parseMoves(move) {
  if (!move) return [];
  return (Array.isArray(move) ? move : String(move).split('+')).map((m) => m.trim()).filter((m) => m && m !== 'static');
}

/** Lay a scene's shots out on its local clock: `[{ ...shot, start, dur }]`. */
export function layoutShots(list, sceneDur) {
  const fixed = list.reduce((acc, s) => acc + (s.dur > 0 ? s.dur : 0), 0);
  const free = list.filter((s) => !(s.dur > 0)).length;
  const share = free ? Math.max(0, sceneDur - fixed) / free : 0;
  let cursor = 0;
  const out = list.map((s) => {
    const dur = s.dur > 0 ? s.dur : share;
    const shot = { ...s, start: cursor, dur };
    cursor += dur;
    return shot;
  });
  // A list shorter than the scene holds its last shot to the end.
  if (out.length && cursor < sceneDur) out[out.length - 1].dur += sceneDur - cursor;
  return out;
}

/**
 * Camera state for a shot at shot progress `k` (already eased) — pure math.
 * @param {{center:number[], size:number[]}} box  subject box (world units)
 * @param {{fov:number, aspect:number}} lens      vertical fov (deg) and aspect of the frame
 */
export function frameShot(shot, box, lens, k = 0) {
  const size = resolveSize(shot.size);
  const amount = shot.amount ?? 1;
  const moves = parseMoves(shot.move);
  const [w, h, d] = box.size;

  let yaw = (shot.angle ?? 0) * DEG;
  let elev = resolveHeight(shot.height) * DEG;
  let distMul = 1;
  let truck = 0;
  for (const m of moves) {
    if (m === 'push') distMul *= lerp(1 + 0.14 * amount, 1 - 0.1 * amount, k);
    else if (m === 'pull') distMul *= lerp(1 - 0.1 * amount, 1 + 0.16 * amount, k);
    else if (m === 'orbit') yaw += lerp(-9, 9, k) * amount * DEG;
    else if (m === 'rise') elev += lerp(-7, 7, k) * amount * DEG;
    else if (m === 'drop') elev += lerp(7, -7, k) * amount * DEG;
    else if (m === 'truck') truck = lerp(-1, 1, k) * amount;
  }
  elev = clamp(elev, -10 * DEG, 85 * DEG);

  const fov = shot.fov ?? lens.fov;
  const tanV = Math.tan((fov * DEG) / 2);
  const tanH = tanV * lens.aspect;
  const fill = shot.fill ?? size.fill;
  const focus = shot.focus ?? size.focus;
  const target = [box.center[0], box.center[1] + (focus - 0.5) * h, box.center[2]];

  // Camera basis looking at `target` from (yaw, elev).
  const dir = [Math.sin(yaw) * Math.cos(elev), Math.sin(elev), Math.cos(yaw) * Math.cos(elev)];
  const right = [Math.cos(yaw), 0, -Math.sin(yaw)];
  const up = [-Math.sin(elev) * Math.sin(yaw), Math.cos(elev), -Math.sin(elev) * Math.cos(yaw)];
  const dot = (u, v) => u[0] * v[0] + u[1] * v[1] + u[2] * v[2];

  // Exact perspective fit: the subject box's projected span is `fill` of the frame
  // (1 = edge to edge on its tighter axis, > 1 = overflowing for close-ups).
  const corners = [];
  for (const sx of [-0.5, 0.5]) for (const sy of [-0.5, 0.5]) for (const sz of [-0.5, 0.5]) {
    const c = [box.center[0] + sx * w - target[0], box.center[1] + sy * h - target[1], box.center[2] + sz * d - target[2]];
    corners.push([dot(c, right), dot(c, up), dot(c, dir)]);
  }
  const span = (dist) => {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const [cx, cy, cz] of corners) {
      const z = Math.max(dist - cz, 1e-3);
      x0 = Math.min(x0, cx / (z * tanH)); x1 = Math.max(x1, cx / (z * tanH));
      y0 = Math.min(y0, cy / (z * tanV)); y1 = Math.max(y1, cy / (z * tanV));
    }
    return Math.max((x1 - x0) / 2, (y1 - y0) / 2);
  };
  let lo = Math.max(...corners.map((c) => c[2])) + 0.3;
  let hi = lo + 400;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (span(mid) > fill) lo = mid;
    else hi = mid;
  }
  let dist = hi * distMul;
  if (lens.maxDist) dist = Math.min(dist, lens.maxDist);

  // Lateral shift (rule of thirds / truck) along the camera's right vector.
  const halfFrameW = dist * tanH;
  const place = shot.place === 'left' ? 1 / 3 : shot.place === 'right' ? -1 / 3 : 0;
  const lateral = place * halfFrameW + truck * halfFrameW * 0.12;
  target[0] += right[0] * lateral;
  target[2] += right[2] * lateral;

  const pos = [target[0] + dir[0] * dist, target[1] + dir[1] * dist, target[2] + dir[2] * dist];
  pos[1] = Math.max(pos[1], shot.minY ?? 0.25); // never below the table / ground

  const roll =
    shot.roll != null ? (Array.isArray(shot.roll) ? lerp(shot.roll[0], shot.roll[1], k) : shot.roll)
    : shot.rollDeg != null ? (Array.isArray(shot.rollDeg) ? lerp(shot.rollDeg[0], shot.rollDeg[1], k) : shot.rollDeg) * DEG
    : 0;
  return { pos, target, fov, roll, size: size.name };
}

/** Spherical glide between two camera states with swing-proportional pull-back (opt-in `cinema.pullback`). */
function glide(a, b, k, amount) {
  const sph = (s) => {
    const v = [s.pos[0] - s.target[0], s.pos[1] - s.target[1], s.pos[2] - s.target[2]];
    const d = Math.hypot(...v);
    return { d, az: Math.atan2(v[0], v[2]), el: Math.asin(clamp(v[1] / d, -1, 1)) };
  };
  const A = sph(a), B = sph(b);
  const daz = ((B.az - A.az + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;
  const swing = Math.min(1, Math.abs(daz) / (Math.PI / 2));
  const target = a.target.map((v, i) => lerp(v, b.target[i], k));
  const az = A.az + daz * k, el = lerp(A.el, B.el, k);
  const d = lerp(A.d, B.d, k) * (1 + amount * swing * Math.sin(Math.PI * k));
  const pos = [target[0] + d * Math.sin(az) * Math.cos(el), target[1] + d * Math.sin(el), target[2] + d * Math.cos(az) * Math.cos(el)];
  return { ...b, pos, target, fov: lerp(a.fov, b.fov, k), roll: lerp(a.roll || 0, b.roll || 0, k) };
}

/**
 * Shot-list director bound to a THREE camera.
 * @param {object} THREE
 * @param {object} opts
 * @param {object} opts.camera     THREE.PerspectiveCamera (its current fov is the base lens)
 * @param {object[]} opts.scenes   `scenes` passed to `createWorld` (for timing and storyboard)
 * @param {object} [opts.subjects] name -> Object3D | { center, size }
 * @param {object|object[][]} opts.shots  scene id (or index) -> shot list
 * @param {number} [opts.aspect]   defaults to camera.aspect
 * @param {number} [opts.lensBase=31]  landscape fov that `shot.fov` values are written against
 * @param {number} [opts.maxDist]      cap on camera distance (set edge / fog falloff)
 * @param {boolean|object} [opts.cinema]  OPT-IN cinema defaults (absent = exactly the old behaviour):
 *   drift     {yaw=2.5, push=0.04}  slow drift on every shot (yaw degrees and fractional push-in over the shot),
 *             skipped per axis where the shot already has an `orbit` / `push` / `pull` move; `drift: false` on a shot opts out
 *   pullback  {amount=0.25, dur=1.2}  a shot with `blend: <seconds>` (or dur from `pullback.dur` when `blend: true`)
 *             glides in from the previous shot's end pose instead of cutting; the path is spherical (azimuth/elevation/
 *             distance around the lerped target) and pulls back by `amount * swing`, swing = azimuth change / 90deg (clamped),
 *             so a big swing clears the subject and a small swing is a straight dolly
 *   fog       true  fog density scales with 1/(camera distance) relative to the first shot, so the subject keeps the
 *             same haze at any distance (needs `lookRig`, passed by studio.director)
 */
export function createDirector(THREE, { camera, scenes = [], subjects = {}, shots = {}, aspect = null, lensBase = 31, maxDist = null, cinema = null, lookRig = null }) {
  // Opt-in cinema defaults (ADR-021; `cinema: true` or an object). All off unless named, so existing products are unchanged.
  const cin = cinema === true ? { drift: true, pullback: true, fog: true } : cinema || {};
  // camera.fov is already adapted to the aspect (portrait/square get a wider lens);
  // `shot.fov` is written for landscape and scaled the same way.
  const baseFov = camera.fov;
  const fovScale = baseFov / lensBase;
  const lensAspect = aspect ?? camera.aspect;
  const tmp = new THREE.Vector3();
  const measured = new Map();

  function measure(obj) {
    if (measured.has(obj)) return measured.get(obj);
    obj.updateWorldMatrix(true, true);
    const box = new THREE.Box3().setFromObject(obj);
    const origin = obj.getWorldPosition(new THREE.Vector3());
    let m;
    if (box.isEmpty()) {
      m = { offset: [0, 0.5, 0], size: [1, 1, 1], rest: origin.toArray() };
    } else {
      const c = box.getCenter(new THREE.Vector3());
      const s = box.getSize(new THREE.Vector3());
      m = { offset: c.clone().sub(origin).toArray(), size: s.toArray(), rest: origin.toArray() };
    }
    measured.set(obj, m);
    return m;
  }

  function lookup(ref) {
    return typeof ref === 'string' ? subjects[ref] : ref;
  }

  function blendBoxes(a, b, t) {
    return {
      center: a.center.map((v, i) => lerp(v, b.center[i], t)),
      size: a.size.map((v, i) => lerp(v, b.size[i], t)),
    };
  }

  function boxOf(ref, follow, k = 0) {
    if (typeof ref === 'string' && Array.isArray(subjects[ref])) ref = subjects[ref];
    if (Array.isArray(ref) && ref.length && typeof ref[0] !== 'number') {
      const boxes = ref.map((r) => boxOf(r, follow, k));
      const lo = [0, 1, 2].map((i) => Math.min(...boxes.map((b) => b.center[i] - b.size[i] / 2)));
      const hi = [0, 1, 2].map((i) => Math.max(...boxes.map((b) => b.center[i] + b.size[i] / 2)));
      return { center: lo.map((v, i) => (v + hi[i]) / 2), size: lo.map((v, i) => hi[i] - v) };
    }
    const obj = lookup(ref);
    if (!obj) throw new Error(`director: unknown subject "${ref}"`);
    if (typeof obj === 'function') {
      return boxOf(obj(k), follow, k);
    }
    if (!obj.isObject3D) {
      if (obj.from && obj.to) {
        return blendBoxes(boxOf(obj.from, follow, k), boxOf(obj.to, follow, k), k);
      }
      const full = { center: [...obj.center], size: [...(obj.size || [1, 1, 1])] };
      if (obj.coreBox) {
        const core = boxOf(obj.coreBox, follow, k);
        return blendBoxes(full, core, clamp(obj.coreWeight ?? 0.72, 0, 1));
      }
      return full;
    }
    if (follow === 'live-box') {
      obj.updateWorldMatrix(true, true);
      const liveBox = new THREE.Box3().setFromObject(obj);
      if (!liveBox.isEmpty()) {
        const c = liveBox.getCenter(new THREE.Vector3()).toArray();
        const s = liveBox.getSize(new THREE.Vector3()).toArray();
        const full = { center: c, size: s };
        if (obj.userData?.coreBox) {
          const core = boxOf(obj.userData.coreBox, follow, k);
          return blendBoxes(full, core, clamp(obj.userData.coreWeight ?? 0.72, 0, 1));
        }
        return full;
      }
    }
    const m = measure(obj);
    let base = m.rest;
    if (follow) {
      const live = obj.getWorldPosition(tmp).toArray();
      base = follow === 'xyz' ? live : [live[0], m.rest[1], live[2]];
    }
    const full = { center: base.map((v, i) => v + m.offset[i]), size: m.size };
    if (obj.userData?.coreBox) {
      const core = boxOf(obj.userData.coreBox, follow, k);
      return blendBoxes(full, core, clamp(obj.userData.coreWeight ?? 0.72, 0, 1));
    }
    return full;
  }

  /** Subject for a shot after size hints (`userData.shotTargets`) and follow defaults. */
  function resolveSubject(shot) {
    const ref = shot.subject ?? Object.keys(subjects)[0];
    const obj = typeof ref === 'string' && !Array.isArray(subjects[ref]) ? subjects[ref] : ref;
    const size = resolveSize(shot.size).name;
    const follow = shot.follow ?? (obj?.isObject3D && obj.userData.follow ? true : undefined);
    const hint = obj?.isObject3D && obj.userData.shotTargets?.[size];
    let yaw = 0;
    if (obj?.isObject3D && obj.userData.facing) {
      const f = obj.getWorldDirection(tmp);
      yaw = Math.atan2(f.x, f.z) / DEG;
    }
    if (hint) return { ref: hint, fill: HINT_FILL[size], follow, yaw };
    return { ref, fill: undefined, follow, yaw };
  }

  function listFor(scene) {
    if (!scene) return null;
    const byId = Array.isArray(shots) ? null : shots[scene.id];
    return byId || shots[scene.index] || null;
  }

  const layouts = new Map();
  function layoutFor(scene) {
    const list = listFor(scene);
    if (!list || !list.length) return null;
    if (!layouts.has(scene.index)) layouts.set(scene.index, layoutShots(list, scene.dur));
    return layouts.get(scene.index);
  }

  // Measure every subject at its rest pose now, before any animation runs.
  const measureAll = (o) => {
    measure(o);
    for (const h of Object.values(o.userData.shotTargets || {})) if (h?.isObject3D) measure(h);
  };
  for (const ref of Object.values(subjects)) for (const r of [].concat(ref)) if (r?.isObject3D) measureAll(r);
  for (const list of Object.values(shots)) {
    for (const s of list || []) {
      for (const r of [].concat(s.subject ?? [])) {
        const o = lookup(r);
        if (o?.isObject3D) measureAll(o);
      }
    }
  }

  /** Current shot for a frame: `{ shot, index, count, localT, u }` or null when unscripted. */
  function pick(frame) {
    const scene = frame.scene || scenes[frame.sceneIndex ?? 0];
    const layout = layoutFor(scene);
    if (!layout) return null;
    const localT = frame.localT ?? 0;
    let index = layout.findIndex((s) => localT >= s.start && localT < s.start + s.dur);
    if (index < 0) index = localT < 0 ? 0 : layout.length - 1;
    const shot = layout[index];
    return { shot, index, count: layout.length, localT, u: clamp((localT - shot.start) / Math.max(shot.dur, 1e-3), 0, 1) };
  }

  /** Camera state for a shot at eased progress k (no micro-motion). */
  function shotState(shot, k, live = true) {
    const { ref, fill, follow, yaw } = resolveSubject(shot);
    let box = boxOf(ref, live && follow, k);
    if (shot.coreBox) {
      const core = boxOf(shot.coreBox, live && follow, k);
      box = blendBoxes(box, core, clamp(shot.coreWeight ?? 0.72, 0, 1));
    }
    const lens = { fov: shot.fov ? shot.fov * fovScale : baseFov, aspect: lensAspect, maxDist };
    let framed = { ...shot, fov: lens.fov, fill: shot.fill ?? fill, angle: (shot.angle ?? 0) + (live ? yaw : 0) };
    if (cin.drift && shot.drift !== false) {
      const d = typeof cin.drift === 'object' ? cin.drift : {};
      const mv = parseMoves(shot.move);
      const kd = k * 2 - 1; // centred so the shot's framed pose is the middle of the drift
      if (!mv.includes('orbit')) framed.angle += (d.yaw ?? 2.5) * kd;
      if (!mv.includes('push') && !mv.includes('pull')) framed = { ...framed, move: [...mv, 'push'].join('+'), amount: (shot.amount ?? 1) * ((d.push ?? 0.04) / 0.24) };
    }
    return frameShot(framed, box, lens, k);
  }

  // Live readability check: while rendering, find characters (puppets) that are visible and in
  // frame; if the biggest one is under ~12% of frame height it is a dot on a phone screen.
  let cast = null;
  const ndc = new THREE.Vector3();
  function findCast() {
    const first = Object.values(subjects).flat().find((o) => o?.isObject3D);
    let root = first;
    while (root?.parent) root = root.parent;
    cast = [];
    root?.traverse((o) => {
      if (o.userData.facing) cast.push(o);
    });
  }
  const shown = (o) => {
    for (let n = o; n; n = n.parent) if (!n.visible) return false;
    return true;
  };
  function castScale() {
    if (!cast) findCast();
    camera.updateMatrixWorld();
    let best = -1;
    for (const pup of cast) {
      if (!shown(pup)) continue;
      const m = measure(pup);
      const c = pup.getWorldPosition(tmp).toArray().map((v, k) => v + m.offset[k]);
      ndc.set(c[0], c[1], c[2]).project(camera);
      if (Math.abs(ndc.x) > 1 || Math.abs(ndc.y) > 1 || ndc.z > 1) continue;
      const top = ndc.set(c[0], c[1] + m.size[1] / 2, c[2]).project(camera).y;
      const bottom = ndc.set(c[0], c[1] - m.size[1] / 2, c[2]).project(camera).y;
      best = Math.max(best, Math.abs(top - bottom) / 2);
    }
    return best; // -1 = no character in frame
  }
  let board = null;
  let refDist = null;

  /** Frame the camera for `frame`; returns the picked shot, or null if this scene has no list. */
  function update(frame) {
    const p = pick(frame);
    if (!p) return null;
    const { shot } = p;
    let state = shotState(shot, ease(p.u, shot.ease));
    const bl = cin.pullback && shot.blend ? (shot.blend === true ? cin.pullback.dur ?? 1.2 : shot.blend) : 0;
    const into = p.localT - shot.start;
    if (bl > 0 && p.index > 0 && into < bl) {
      const prev = layoutFor(frame.scene || scenes[frame.sceneIndex ?? 0])[p.index - 1];
      state = glide(shotState(prev, ease(1, prev.ease)), state, smootherstep(0, 1, into / bl), cin.pullback.amount ?? 0.25);
    }
    applyMicroMotion(state, shot, p.localT);
    if (cin.fog && lookRig?.setFogScale) {
      const dist = Math.hypot(state.pos[0] - state.target[0], state.pos[1] - state.target[1], state.pos[2] - state.target[2]);
      if (refDist == null) refDist = dist;
      lookRig.setFogScale(refDist / Math.max(dist, 1e-3));
    }
    applyThreeCamera(camera, state);
    const entry = board?.find((e) => e.scene === (frame.scene?.index ?? frame.sceneIndex) && e.shot === p.index);
    if (entry && !entry.checked && Math.abs((frame.t ?? -1) - entry.t) < 0.02) {
      entry.checked = true;
      const frac = castScale();
      if (frac >= 0 && frac < 0.12) entry.warn.push(`characters fill only ${Math.round(frac * 100)}% of frame height: tighten the shot or frame the character`);
      // Main subjects must not pass through themselves (an arm sunk into the body).
      for (const pup of cast) {
        const api = pup.userData.puppet;
        if (!api?.limbClearance || !shown(pup)) continue;
        const c = api.limbClearance();
        if (c < 0.9) {
          const name = Object.keys(subjects).find((k) => subjects[k] === pup) || pup.name || 'a character';
          entry.warn.push(`${name}: arm passes into its body (clearance ${c.toFixed(2)}): widen shoulders or change the pose`);
        }
      }
    }
    return p;
  }

  /**
   * One entry per shot with a representative global time (for `render.mjs --storyboard`) and
   * continuity warnings (jump cuts, over-long static holds, shots pushed past the scene end).
   */
  function storyboard() {
    const out = [];
    for (const scene of scenes) {
      const layout = layoutFor(scene);
      if (!layout) {
        out.push({ t: +(scene.start + scene.dur * 0.6).toFixed(3), scene: scene.index, shot: 0, size: '-', subject: '-', dur: scene.dur, warn: [] });
        continue;
      }
      layout.forEach((s, i) => {
        const warn = [];
        const prev = layout[i - 1];
        if (prev) {
          const same = String(prev.subject) === String(s.subject);
          const dSize = Math.abs(SIZE_ORDER.indexOf(resolveSize(prev.size).name) - SIZE_ORDER.indexOf(resolveSize(s.size).name));
          const dAngle = Math.abs((prev.angle ?? 0) - (s.angle ?? 0));
          const dHeight = Math.abs(resolveHeight(prev.height) - resolveHeight(s.height));
          if (same && dSize === 0 && dAngle < 30 && dHeight < 15) warn.push('jump cut: change size or angle >= 30deg');
        }
        if (s.start >= scene.dur - 1e-3) warn.push('starts after scene end');
        if ((s.impacts || s.boil || s.boilAmp) && s.shake !== true) warn.push('camera shake ignored (impacts/boil): show the impact on the prop instead');
        if (scene.index === 0 && i === 0 && ['wide', 'extreme-wide'].includes(resolveSize(s.size).name) && s.dur > 1.0) {
          warn.push('opens on a long wide shot: hook the first second with the subject, reveal the set later');
        }
        out.push({
          t: +(scene.start + s.start + Math.min(s.dur * 0.6, s.dur - 0.05)).toFixed(3),
          scene: scene.index,
          shot: i,
          size: resolveSize(s.size).name,
          subject: typeof s.subject === 'string' ? s.subject : Array.isArray(s.subject) ? s.subject.join('+') : 'custom',
          dur: +s.dur.toFixed(2),
          box: boxOf(resolveSubject(s).ref, false).size.map((v) => +v.toFixed(2)),
          warn,
        });
      });
    }
    // Report ignored camera shake once, not on every shot.
    const shaky = out.filter((e) => e.warn.some((w) => w.startsWith('camera shake ignored')));
    for (const e of shaky) e.warn = e.warn.filter((w) => !w.startsWith('camera shake ignored'));
    if (shaky.length) shaky[0].warn.push(`camera shake (impacts/boil) ignored on ${shaky.length} shot(s): keep the camera steady, show impacts on the props`);
    // Rhythm: the same shot-size pattern in most scenes reads as a template, not a film.
    const patterns = new Map();
    for (const e of out) {
      if (e.size === '-') continue;
      patterns.set(e.scene, [...(patterns.get(e.scene) || []), e.size]);
    }
    const seqs = [...patterns.values()];
    if (seqs.length >= 3) {
      const counts = new Map();
      for (const q of seqs) counts.set(q.join('>'), (counts.get(q.join('>')) || 0) + 1);
      const [top, n] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
      const lastSizes = new Set(seqs.map((q) => q[q.length - 1]));
      const firstOf = (sc) => out.find((e) => e.scene === sc);
      if (n > seqs.length / 2) {
        for (const [sc, q] of patterns) if (q.join('>') === top) firstOf(sc).warn.push(`same shot pattern (${top}) in ${n}/${seqs.length} scenes: vary shot count and order`);
      } else if (lastSizes.size === 1) {
        firstOf([...patterns.keys()][0]).warn.push(`every scene ends on a ${[...lastSizes][0]} shot: vary how scenes end`);
      }
    }
    board = out;
    return out;
  }

  return { update, pick, storyboard, measure: (ref) => boxOf(ref, false) };
}
