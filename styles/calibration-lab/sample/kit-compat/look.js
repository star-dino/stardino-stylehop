// The industrial look, shared by every machine: procedural micro-surface maps (anodized, machined, cast, braided,
// section hatch), a material set that obeys the roughness rules in SKILL.md, a screen-space ink pass that draws
// crease and silhouette lines from the GTAO pass's own depth and normals, and a silhouette mode for
// `capture.mjs --mask` (the form gate in docs/form.md).
//
//   import {createMaterials, InkPass, installSilhouette} from 'teardown-kit/look.js';
//   const M = createMaterials();                       // M.white, M.alu, M.steel, M.brass, M.liner, ...
//   composer.addPass(gtao); composer.addPass(new InkPass(gtao, camera, {strength: 0.4}));
//   installSilhouette(scene);                          // capture.mjs --mask now renders a black-on-white mask
//
// Ported from the calibration-lab kernel (stardino-stylehop), adapted to three r186 and to GTAOPass.
import {THREE} from '/styles/calibration-lab/kernel.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// a size x size heightfield (0..1, wraps) → tangent-space normal map + roughness map
function mapsFromHeight(size, h, {strength = 2.4, baseRough = 0.4, roughSpan = 0.18} = {}) {
  const mk = () => {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    return c;
  };
  const nc = mk();
  const rc = mk();
  const ni = nc.getContext('2d').createImageData(size, size);
  const ri = rc.getContext('2d').createImageData(size, size);
  const m = size - 1;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (h[y * size + ((x + 1) & m)] - h[y * size + ((x - 1) & m)]) * strength;
      const dy = (h[((y + 1) & m) * size + x] - h[((y - 1) & m) * size + x]) * strength;
      const il = 1 / Math.hypot(dx, dy, 1);
      const i = (y * size + x) * 4;
      ni.data[i] = Math.round((-dx * il * 0.5 + 0.5) * 255);
      ni.data[i + 1] = Math.round((-dy * il * 0.5 + 0.5) * 255);
      ni.data[i + 2] = Math.round(clamp((il * 0.5 + 0.5) * 255, 128, 255));
      ni.data[i + 3] = 255;
      const r = Math.round(clamp((baseRough + (h[y * size + x] - 0.5) * roughSpan) * 255, 8, 250));
      ri.data[i] = ri.data[i + 1] = ri.data[i + 2] = r;
      ri.data[i + 3] = 255;
    }
  }
  nc.getContext('2d').putImageData(ni, 0, 0);
  rc.getContext('2d').putImageData(ri, 0, 0);
  const tex = (c) => {
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 4;
    return t;
  };
  return {normalMap: tex(nc), roughnessMap: tex(rc)};
}

let MAPS = null;
/** Deterministic surface maps, built once: anodized, machined, cast, braided ({normalMap, roughnessMap}), hatch. */
export function createSurfaceMaps() {
  if (MAPS) return MAPS;
  const S = 128;
  const m = S - 1;
  const rA = mulberry32(0xca11ab01);
  const raw = Float32Array.from({length: S * S}, rA);
  const hA = new Float32Array(S * S);
  for (let y = 0; y < S; y++) {
    const j = (rA() - 0.5) * 0.28;
    for (let x = 0; x < S; x++) {
      const b = raw[y * S + x] * 0.4 + raw[y * S + ((x + 1) & m)] * 0.25 + raw[y * S + ((x + 2) & m)] * 0.2 + raw[((y + 1) & m) * S + x] * 0.15;
      hA[y * S + x] = clamp(b + j * 0.35, 0, 1);
    }
  }
  const rM = mulberry32(0xca11ab02);
  const hM = new Float32Array(S * S);
  for (let y = 0; y < S; y++) {
    const v = (y / S) * Math.PI * 2;
    const g = Math.sin(v * 24) * 0.28 + Math.sin(v * 52 + 0.7) * 0.16 + Math.cos(v * 11 - 0.4) * 0.1;
    for (let x = 0; x < S; x++) {
      const u = (x / S) * Math.PI * 2;
      hM[y * S + x] = clamp(0.5 + g + Math.sin(u * 18 + v * 6) * 0.08 + (rM() - 0.5) * 0.14, 0, 1);
    }
  }
  const rC = mulberry32(0xca11ab03);
  let hC = Float32Array.from({length: S * S}, rC);
  for (let p = 0; p < 3; p++) {
    const n = new Float32Array(S * S);
    for (let y = 0; y < S; y++)
      for (let x = 0; x < S; x++)
        n[y * S + x] = (hC[y * S + x] * 4 + hC[y * S + ((x - 1) & m)] + hC[y * S + ((x + 1) & m)] + hC[((y - 1) & m) * S + x] + hC[((y + 1) & m) * S + x]) / 8;
    hC = n;
  }
  const hB = new Float32Array(S * S);
  for (let y = 0; y < S; y++)
    for (let x = 0; x < S; x++) {
      const u = (x / S) * Math.PI * 28;
      const v = (y / S) * Math.PI * 28;
      const a = Math.sin(u + v);
      const b = Math.sin(u - v);
      hB[y * S + x] = clamp(0.35 + Math.max(Math.abs(a), Math.abs(b)) * 0.45 + a * b * 0.2, 0, 1);
    }
  // 45° section hatch for cut faces
  const hc = document.createElement('canvas');
  hc.width = hc.height = 128;
  const g = hc.getContext('2d');
  g.fillStyle = '#4A525C';
  g.fillRect(0, 0, 128, 128);
  for (const [col, lw, off] of [['#67717D', 2.2, 0], ['#343A42', 1.1, 3]]) {
    g.strokeStyle = col;
    g.lineWidth = lw;
    for (let o = -128 + off; o < 256; o += 8) {
      g.beginPath();
      g.moveTo(o, 0);
      g.lineTo(o - 128, 128);
      g.stroke();
    }
  }
  const hatch = new THREE.CanvasTexture(hc);
  hatch.wrapS = hatch.wrapT = THREE.RepeatWrapping;
  if ('sRGBEncoding' in THREE) hatch.encoding = THREE.sRGBEncoding; // r147: encoding, not colorSpace
  MAPS = {
    anodized: mapsFromHeight(S, hA, {strength: 1.8, baseRough: 0.34, roughSpan: 0.16}),
    machined: mapsFromHeight(S, hM, {strength: 2.1, baseRough: 0.26, roughSpan: 0.14}),
    cast: mapsFromHeight(S, hC, {strength: 3.2, baseRough: 0.54, roughSpan: 0.22}),
    braided: mapsFromHeight(S, hB, {strength: 3.4, baseRough: 0.68, roughSpan: 0.22}),
    hatch,
  };
  return MAPS;
}

/**
 * Box-projected UVs at a fixed physical density (`scale` model units per texture tile), so extrudes, lathes and
 * merged parts all carry the same grain size. Call it on geometry built in your model units.
 */
export function boxUVs(geometry, scale = 56) {
  const pos = geometry.attributes.position;
  if (!geometry.attributes.normal) geometry.computeVertexNormals();
  const nor = geometry.attributes.normal;
  const uv = new Float32Array(pos.count * 2);
  const k = 1 / Math.max(1e-6, scale);
  for (let i = 0; i < pos.count; i++) {
    const ax = Math.abs(nor.getX(i));
    const ay = Math.abs(nor.getY(i));
    const az = Math.abs(nor.getZ(i));
    const [a, b] = ay >= ax && ay >= az ? [pos.getX(i), pos.getZ(i)] : ax >= az ? [pos.getZ(i), pos.getY(i)] : [pos.getX(i), pos.getY(i)];
    uv[i * 2] = a * k;
    uv[i * 2 + 1] = b * k;
  }
  geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return geometry;
}

/**
 * The roughness rule as code. 'shell' (housings, armour, plates, anything big): roughness ≥ 0.45, clearcoat ≤ 0.14,
 * envMapIntensity 0.56, so a large surface never shows a wet plastic streak. 'precision' (pins, shafts, bearings,
 * brass fittings): left glossy, full reflections.
 */
export function governMaterial(mat, role = 'shell') {
  if (!mat) return mat;
  if (role === 'shell') {
    if (typeof mat.roughness === 'number') mat.roughness = Math.max(0.45, mat.roughness);
    if (typeof mat.clearcoat === 'number') mat.clearcoat = Math.min(0.14, mat.clearcoat);
    mat.envMapIntensity = Math.min(mat.envMapIntensity ?? 1, 0.56);
  }
  mat.userData.role = role;
  return mat;
}

export const PALETTE = {
  white: '#ECEEF0',
  ceramic: '#E8E6E0',
  alu: '#C8CDD3',
  aluDark: '#868D96',
  titanium: '#9AA2AD',
  structure: '#1A1D21',
  liner: '#16191E',
  graphite: '#464C53',
  steel: '#C6CCD2',
  chrome: '#DCE2E8',
  bronze: '#B88E58',
  brass: '#C8A24E',
  rubber: '#23262A',
  accent: '#FF5A1F',
};

/**
 * The material set. Pass colours to override the palette: createMaterials({white: '#efece6', accent: '#e8792b'}).
 * `normalScale` (default 1) scales every micro-normal at once, e.g. 0.5 for a model seen from far away.
 * Texture repeat is per material (`M.white.normalMap.repeat`), shared between materials using the same map: clone
 * the map before changing it on one.
 */
export function createMaterials(colors = {}, {normalScale = 1} = {}) {
  const P = {...PALETTE, ...colors};
  const T = createSurfaceMaps();
  const ns = (s) => new THREE.Vector2(s * normalScale, s * normalScale);
  const std = (o, role) => governMaterial(new THREE.MeshStandardMaterial(o), role);
  const phys = (o, role) => governMaterial(new THREE.MeshPhysicalMaterial(o), role);
  const mapped = (kind, s) => ({normalMap: T[kind].normalMap, roughnessMap: T[kind].roughnessMap, normalScale: ns(s)});
  return {
    white: phys({color: P.white, metalness: 0.06, roughness: 0.56, clearcoat: 0.12, clearcoatRoughness: 0.42, ...mapped('cast', 0.18)}, 'shell'),
    ceramic: phys({color: P.ceramic, metalness: 0.04, roughness: 0.6, clearcoat: 0.1, clearcoatRoughness: 0.5, ...mapped('cast', 0.22)}, 'shell'),
    alu: std({color: P.alu, metalness: 0.86, roughness: 0.45, ...mapped('anodized', 0.16)}, 'shell'),
    aluDark: std({color: P.aluDark, metalness: 0.84, roughness: 0.48, ...mapped('anodized', 0.18)}, 'shell'),
    titanium: std({color: P.titanium, metalness: 0.85, roughness: 0.46, ...mapped('anodized', 0.18)}, 'shell'),
    structure: phys({color: P.structure, metalness: 0.36, roughness: 0.46, clearcoat: 0.14, clearcoatRoughness: 0.34, ...mapped('cast', 0.2)}, 'shell'),
    liner: std({color: P.liner, metalness: 0.28, roughness: 0.68, ...mapped('cast', 0.22)}, 'shell'),
    graphite: std({color: P.graphite, metalness: 0.62, roughness: 0.46, ...mapped('machined', 0.18)}, 'shell'),
    steel: std({color: P.steel, metalness: 0.96, roughness: 0.24, ...mapped('machined', 0.18)}, 'precision'),
    chrome: std({color: P.chrome, metalness: 1, roughness: 0.12, normalMap: T.machined.normalMap, normalScale: ns(0.08)}, 'precision'),
    bronze: std({color: P.bronze, metalness: 0.92, roughness: 0.28, ...mapped('machined', 0.16)}, 'precision'),
    brass: std({color: P.brass, metalness: 0.92, roughness: 0.26, ...mapped('machined', 0.16)}, 'precision'),
    rubber: std({color: P.rubber, metalness: 0.06, roughness: 0.88, normalMap: T.cast.normalMap, normalScale: ns(0.24)}, 'shell'),
    hose: std({color: '#1E2126', metalness: 0.18, roughness: 0.7, ...mapped('braided', 0.38)}, 'shell'),
    section: new THREE.MeshStandardMaterial({color: '#ffffff', map: T.hatch, metalness: 0.55, roughness: 0.48, side: THREE.DoubleSide}),
    accent: new THREE.MeshBasicMaterial({color: P.accent, toneMapped: false}),
  };
}

/**
 * The studio a metal needs to look like metal: bright softboxes against a dark surround. A metal shows nothing but
 * what it reflects, so a uniformly pale environment turns steel, brass and gunmetal into grey plastic, and a
 * uniformly dark one turns them into black holes. Boxes give the highlight bands and the dark between them the
 * contrast; dark parts then show their bevels as thin bright edges. Returns the PMREM texture for scene.environment.
 *   scene.environment = studioEnvironment(renderer);  scene.environmentIntensity = 0.9;
 * surround: the dark between the boxes (#2a2c30 reads as a photo studio; above ~#70 metals start to go flat).
 */
export function studioEnvironment(renderer, {surround = '#2a2c30', floor = '#77736b', boxes} = {}) {
  const env = new THREE.Scene();
  env.background = new THREE.Color(surround);
  const list = boxes || [
    // [w, h, position, colour, intensity]: top, key right, cool rim left, a thin front strip for edge glints, and
    // a large dim front card: faces turned to the camera (a hub, a flange, a gear face) reflect it instead of the
    // dark surround, so they read as polished metal rather than holes
    [28, 22, [2, 24, 6], '#ffffff', 3.4],
    [16, 22, [20, 10, 16], '#fffcf5', 2.8],
    [14, 24, [-20, 12, 10], '#e2ecfa', 2.4],
    [26, 5, [0, 8, 24], '#ffffff', 2.2],
    [26, 14, [-4, -1, 26], '#f4f2ee', 1.15],
  ];
  for (const [w, h, pos, col, k] of list) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({color: new THREE.Color(col).multiplyScalar(k), side: THREE.DoubleSide}));
    m.position.set(...pos);
    m.lookAt(0, 0, 0);
    env.add(m);
  }
  const fl = new THREE.Mesh(new THREE.CircleGeometry(55, 32), new THREE.MeshBasicMaterial({color: floor, side: THREE.DoubleSide}));
  fl.rotation.x = -Math.PI / 2;
  fl.position.y = -8;
  env.add(fl);
  const pm = new THREE.PMREMGenerator(renderer);
  const tex = pm.fromScene(env, 0.03).texture;
  pm.dispose();
  return tex;
}

// ---- Post passes: stylehop r147 has no EffectComposer addons. These are harmless stand-ins with the same names and
// constructor signatures; the real ink / AO come from stylehop's engine/look.js lookRig (see NOTES, section B).
export class InkPass {
  constructor(gtao, camera, {strength = 0.38, normalWeight = 0.68, color = '#181C22'} = {}) {
    this.isStubPass = true;
    this.enabled = false;
    this.gtao = gtao;
    this.camera = camera;
    this.strength = strength;
    this.normalWeight = normalWeight;
    this.color = color;
  }
  setSize() {}
  render() {}
  dispose() {}
}

export class CallPass {
  constructor(fn) {
    this.isStubPass = true;
    this.enabled = true;
    this.needsSwap = false;
    this.fn = fn;
  }
  setSize() {}
  /** Not part of a composer here: call it by hand around lookRig.render if the hide/show matters. */
  render() {
    this.fn();
  }
  dispose() {}
}

/**
 * Silhouette mode for the form gate. Registers window.__SILHOUETTE(on): every mesh renders flat black on a white
 * background; shadow catchers, sprites, lines and anything with userData.noSilhouette render nothing. Materials are
 * swapped per mesh (not scene.overrideMaterial), so a sim that toggles visibility per frame cannot bring a floor
 * back. capture.mjs --mask calls it and hides the DOM overlay; silhouette.mjs compares the result with the
 * reference. Call once after the scene is built.
 */
export function installSilhouette(scene) {
  const black = new THREE.MeshBasicMaterial({color: 0x000000, side: THREE.DoubleSide});
  const none = new THREE.MeshBasicMaterial({colorWrite: false, depthWrite: false});
  let saved = null;
  window.__SILHOUETTE = (on) => {
    if (on && !saved) {
      saved = {bg: scene.background, fog: scene.fog, mats: []};
      scene.traverse((o) => {
        if (!o.material) return;
        const ms = Array.isArray(o.material) ? o.material : [o.material];
        const skip = o.userData.noSilhouette || o.isSprite || o.isLine || o.isPoints || ms.some((m) => m.isShadowMaterial);
        saved.mats.push([o, o.material]);
        o.material = skip ? none : black;
      });
      scene.background = new THREE.Color(0xffffff);
      scene.fog = null;
    } else if (!on && saved) {
      for (const [o, m] of saved.mats) o.material = m;
      scene.background = saved.bg;
      scene.fog = saved.fog;
      saved = null;
    }
  };
}
