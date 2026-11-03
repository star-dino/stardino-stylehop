/**
 * Style-agnostic 3D Studio (`engine/studio3d.js`).
 *
 * Everything a 3D style needs that is NOT about its medium: renderer + aspect-adapted camera,
 * the look rig (energy budget, IBL, contact shadow), per-scene looks from `data-look`, the
 * shot-list director and the single per-frame `render(frame)`. A style kernel calls
 * `createStudio3D` and adds only its own medium (palette, textures, materials, set floor):
 *
 *   const studio = createStudio3D(THREE, {
 *     width, height, scenes,
 *     look: resolveLook(LOOK_DEFAULTS, MY_STYLE_LOOK, style.look),
 *     presets: { ...MY_STYLE_PRESETS, ...style.looks },
 *     maxDist: 26,
 *   });
 *   // ...build materials / props...
 *   const director = studio.director({ subjects, shots });
 *   // per frame: pose props; director.update(frame); studio.render(frame);
 */

import { resolveAspectFraming, evalCameraShot, applyThreeCamera } from './camera.js';
import { LOOK_PRESETS, createLookRig, createLookTimeline } from './look.js';
import { createDirector } from './director.js';
import { loadBlenderGlb, parseGlbBuffer } from './three_bridge.js';

/**
 * @param {object} THREE
 * @param {object} opts
 * @param {number} opts.width
 * @param {number} opts.height
 * @param {object} opts.look            fully resolved look (see `resolveLook`)
 * @param {object} [opts.presets]       name -> look layer for `data-look`; defaults to `LOOK_PRESETS`
 * @param {object[]} [opts.scenes]      `scenes` passed to `createWorld`
 * @param {number} [opts.baseFov=31]    landscape vertical fov; portrait / square widen it
 * @param {number} [opts.maxDist]       director camera distance cap (set edge / fog falloff)
 */
export function createStudio3D(THREE, { width, height, look, presets = LOOK_PRESETS, scenes = [], baseFov = 31, maxDist = null, near = 0.5, far = 200 }) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    stencil: true,
    preserveDrawingBuffer: true,
    powerPreference: 'high-performance',
  });
  renderer.setSize(width, height, false);

  const scene = new THREE.Scene();
  // The look rig must exist before any material is created (colour management).
  const lookRig = createLookRig(THREE, { renderer, scene, look });
  const lookTimeline = createLookTimeline(THREE, { base: look, presets, scenes });
  if (lookTimeline.targets.length) {
    lookRig.prewarm(lookTimeline.targets);
  }

  const framing = resolveAspectFraming(width, height, baseFov);
  const camera = new THREE.PerspectiveCamera(framing.fov, framing.aspect, near, far);

  /** Hand-placed camera move from `engine/camera.js` (orbit / crane / track ...). */
  function applyShot(shotSpec, u, localT = 0, opts = {}) {
    const state = evalCameraShot(shotSpec, u, localT, { baseFov: framing.fov, ...opts });
    applyThreeCamera(camera, state, { distScale: framing.distScale });
    return state;
  }

  /** Shot-list director for this camera; create it after the props are built and posed. */
  function director({ subjects = {}, shots = {}, cinema = null } = {}) {
    return createDirector(THREE, { camera, scenes, subjects, shots, aspect: framing.aspect, lensBase: baseFov, maxDist, cinema, lookRig });
  }

  /**
   * Load a high-precision `.glb` 3D prop/character asset via `engine/three_bridge.js`
   * and optionally skin it with the style's procedural material (`materialOverride` / `materialFactory`)
   * and add it to the scene or attach it to a parent/puppet joint.
   */
  async function loadModel(url, opts = {}) {
    const gltf = await loadBlenderGlb(THREE, url, opts);
    if (opts.position && Array.isArray(opts.position)) {
      gltf.scene.position.fromArray(opts.position);
    }
    if (opts.rotationY != null) {
      gltf.scene.rotation.y = opts.rotationY;
    }
    if (opts.scale != null) {
      if (typeof opts.scale === 'number') gltf.scene.scale.multiplyScalar(opts.scale);
      else if (Array.isArray(opts.scale)) gltf.scene.scale.fromArray(opts.scale);
    }
    if (opts.parent) {
      opts.parent.add(gltf.scene);
    } else if (opts.addToScene !== false) {
      scene.add(gltf.scene);
    }
    return gltf;
  }

  function parseModelBuffer(arrayBuffer, opts = {}) {
    return parseGlbBuffer(THREE, arrayBuffer, opts);
  }

  /** Draw a frame. Pass the frame so per-scene looks (`data-look`) apply. */
  function render(frame = null) {
    if (frame && lookTimeline.animated) {
      const { look: l, envLook } = lookTimeline.at(frame.sceneIndex ?? 0, frame.localT ?? 0);
      lookRig.apply(l, { envLook });
    }
    lookRig.render(camera);
  }

  /**
   * Role-id pass (ADR-021 metal brightness check). Call right after `render(frame)`: reads the lit frame from the canvas,
   * re-renders the same camera with every mesh swapped for a flat colour per material role (metal = red, glaze = green,
   * liner = blue, anything else black; no fog / environment / AO / contact shadow), reads that, restores everything and
   * re-renders the normal frame. Returns { role: { share, meanL, p90L } } with `share` = fraction of the frame and
   * `meanL` = mean CIE L* of the lit pixels with that role. A material counts as `metal` when `userData.role === 'metal'`
   * or (no role) metalness >= 0.8. Only pixels whose id colour is pure are used (anti-aliased edges are dropped).
   */
  function roleReport(frame = null) {
    const gl = renderer.getContext();
    const W = canvas.width, H = canvas.height;
    const read = () => { const b = new Uint8Array(W * H * 4); gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, b); return b; };
    const lit = read();
    const ids = {
      metal: new THREE.MeshBasicMaterial({ color: 0xff0000, toneMapped: false, fog: false }),
      glaze: new THREE.MeshBasicMaterial({ color: 0x00ff00, toneMapped: false, fog: false }),
      liner: new THREE.MeshBasicMaterial({ color: 0x0000ff, toneMapped: false, fog: false }),
      other: new THREE.MeshBasicMaterial({ color: 0x000000, toneMapped: false, fog: false }),
    };
    const roleOf = (m) => {
      const r = m.userData?.role;
      if (r === 'metal' || r === 'glaze' || r === 'liner') return r;
      if (!r && m.metalness >= 0.8 && !m.transparent) return 'metal';
      return 'other';
    };
    const saved = [];
    scene.traverse((o) => {
      if (o.isMesh && o.material) {
        saved.push([o, o.material, o.visible]);
        const arr = Array.isArray(o.material);
        const sw = (m) => {
          const id = ids[roleOf(m)].clone();
          id.side = m.side; id.clippingPlanes = m.clippingPlanes; id.clipShadows = m.clipShadows; id.skinning = m.skinning;
          return id;
        };
        o.material = arr ? o.material.map(sw) : sw(o.material);
        if (o.userData?.isHudOverlay) o.visible = false;
      } else if (o.isLine || o.isPoints || o.isSprite) {
        saved.push([o, null, o.visible]);
        o.visible = false;
      }
    });
    const bg = scene.background, fog = scene.fog, env = scene.environment;
    scene.background = new THREE.Color(0x000000); scene.fog = null; scene.environment = null;
    const prevTm = renderer.toneMapping, prevEnc = renderer.outputEncoding;
    renderer.toneMapping = THREE.NoToneMapping;
    renderer.render(scene, camera);
    const idb = read();
    renderer.toneMapping = prevTm;
    for (const [o, m, v] of saved) { if (m) { (Array.isArray(o.material) ? o.material : [o.material]).forEach((x) => x.dispose()); o.material = m; } o.visible = v; }
    scene.background = bg; scene.fog = fog; scene.environment = env;
    render(frame);

    const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    const Ls = (r, g, b) => { const y = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b); const f = y > 216 / 24389 ? Math.cbrt(y) : (24389 / 27 * y + 16) / 116; return 116 * f - 16; };
    const acc = { metal: [], glaze: [], liner: [] };
    for (let i = 0; i < W * H * 4; i += 4) {
      const r = idb[i], g = idb[i + 1], b = idb[i + 2];
      let k = null;
      if (r > 250 && g < 5 && b < 5) k = 'metal'; else if (g > 250 && r < 5 && b < 5) k = 'glaze'; else if (b > 250 && r < 5 && g < 5) k = 'liner';
      if (k) acc[k].push(Ls(lit[i], lit[i + 1], lit[i + 2]));
    }
    const out = {};
    for (const [k, a] of Object.entries(acc)) {
      if (!a.length) { out[k] = { share: 0, meanL: 0, p90L: 0 }; continue; }
      a.sort((x, y) => x - y);
      out[k] = { share: a.length / (W * H), meanL: a.reduce((s, v) => s + v, 0) / a.length, p90L: a[Math.floor(a.length * 0.9)] };
    }
    return out;
  }

  const api = { canvas, renderer, scene, camera, framing, lookRig, applyShot, director, loadModel, parseModelBuffer, render, roleReport };
  if (typeof globalThis !== 'undefined') globalThis.__stylehopStudio = api; // read by tools/render.mjs / tools/audit.mjs
  return api;
}
