/**
 * Calibration Lab · Subject-Agnostic Style Kernel (`styles/calibration-lab/kernel.js`).
 *
 * This module holds ONLY the reusable medium of the "machine under measurement" style:
 *   1. Palette + look tokens (`CAL_PALETTE`, `CAL_LOOK`) with high-contrast studio reflection strips
 *   2. Procedural micro-surface textures (`createSurfaceMaps`, `normalizeGeometryUVs`) & PBR materials (`createMaterials`)
 *   3. Industrial CSG-2D, multi-axis & bionic geometry primitives + Crevice AO (`blockGeometry`, `machinedPlateGeometry`,
 *      `counterboreBossGeometry`, `ribbedLinkGeometry`, `gearGeometry`, `helixGeometry`, `boltGeometry`,
 *      `sweptProfileGeometry`, `updateSweptGeometry`, `bellowsGeometry`, `ballJointGeometry`,
 *      `creviceAoRing`, `creviceAoBox`, `mergeGeometries`)
 *   4. True Stencil section-cut manager (`createSectionCutManager`) with 45° CNC cross-hatch caps
 *   5. Multi-DOF kinematics & secondary linkage solvers (`solveFabrikChain`, `solveKinematicChain`,
 *      `solveFourBar`, `solveTwoLinkIK2D`, `poseActuator`, `poseCompressedSpring`, `updateDynamicCable`, `layerEase`)
 *   6. Physical field shaders & 3D metrology callouts (`createPressureFieldMaterial`, `createTorqueArc`,
 *      `createDimensionCallout`, `lerpFramingBox`, `weightedCoreBox`)
 *   7. Turnkey pale studio stage (`createCalLabStudio`) + Instrument HUD (`createGaugeHud`)
 *
 * AI authoring rule: build any mechanical or bionic subject by importing this kernel in `world.js`.
 * Never hardcode subject-specific assemblies in this file; the kernel must remain able to build
 * an engine, a gearbox, a hydraulic pump, or a multi-DOF robotic octopus after `world.js` is replaced.
 */

import '../../engine/vendor/three.min.js';
import { clamp, lerp, smootherstep } from '../../engine/motion.js';
import { LOOK_DEFAULTS, LOOK_PRESETS, resolveLook, lookFromRefPalette, normalizeRefPalette } from '../../engine/look.js';
import { createStudio3D } from '../../engine/studio3d.js';

export const THREE = globalThis.THREE;

// ============================================================================
// 1. PALETTE & LOOK (WITH HIGH-CONTRAST STUDIO REFLECTION STRIPS)
// ============================================================================

export const CAL_PALETTE = {
  backdrop: '#EDEFF1',
  bench: '#F3F4F5',
  benchLine: '#D5D8DC',
  ink: '#15181C',
  muted: '#7C838C',
  line: '#C9CDD2',
  accent: '#FF5A1F',
  accentSoft: 'rgba(255, 90, 31, 0.16)',
  anodized: '#C8CDD3',
  anodizedDark: '#868D96',
  powder: '#ECEEF0',
  structure: '#1A1D21',
  steel: '#C6CCD2',
  chrome: '#DCE2E8',
  bronze: '#B88E58',
  glass: '#EAF2F6',
  rubber: '#23262A',
  sectionCap: '#4E5660',
  panel: 'rgba(250, 251, 252, 0.92)',
};

/**
 * Resolved over `LOOK_DEFAULTS` by `createCalLabStudio`.
 * `env.studioStrips: true` injects high-contrast specular light strips and negative-fill absorber
 * cards into the PMREM studio dome so cylindrical steel shafts, bearings and anodized chamfers
 * exhibit crisp metallic reflection bands instead of flat plastic grey.
 */
export const CAL_LOOK = {
  color: { output: 'srgb', toneMapping: 'aces', exposure: 1.05 },
  light: {
    illuminance: 2.45,
    keyRatio: 2.35,
    key: {
      color: '#FFFFFF',
      pos: [-9, 16, 11],
      shadow: {
        type: 'pcf-soft',
        mapSize: 2048,
        extent: [5, 5],
        near: 1,
        far: 40,
        bias: -0.0005,
        normalBias: 0.01,
        radius: 4,
        blurSamples: 12,
      },
    },
    sky: '#FFFFFF',
    ground: '#C2C7CE',
    bounce: { color: '#F4F7FA', pos: [8, -3, -9], share: 0.22 },
  },
  env: { enabled: true, share: 0.58, softbox: 3.2, studioStrips: true },
  backdrop: {
    color: CAL_PALETTE.backdrop,
    fog: 0.006,
  },
  contact: {
    enabled: true,
    opacity: 0.45,
    blur: 2.4,
    size: [9, 6.4],
    center: [0, 0],
    height: 1.2,
    resolution: 512,
    updateInterval: 1,
  },
  ao: {
    enabled: true,
    intensity: 0.72,
    radius: 0.14,
    thickness: 0.55,
    distanceExponent: 1.4,
    distanceFallOff: 1.0,
    scale: 1.0,
    samples: 16,
    denoiseRadius: 6.0,
    lumaPhi: 10.0,
    depthPhi: 2.0,
    normalPhi: 3.0,
    inkStrength: 0.36,
    inkColor: '#181C22',
  },
};

export const CAL_LOOK_PRESETS = {};

// ============================================================================
// 2. PROCEDURAL MICRO-SURFACE MAPS, UV NORMALIZATION & PBR MATERIALS
// ============================================================================

function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Convert a 2D scalar heightfield `heights` (size × size, values in 0..1) into a tangent-space
 * normal map + roughness map pair with seamless wrap-around differences.
 */
function buildNormalAndRoughnessFromHeight(size, heights, { strength = 2.4, baseRough = 0.4, roughSpan = 0.18 } = {}) {
  const normCanvas = document.createElement('canvas');
  const roughCanvas = document.createElement('canvas');
  normCanvas.width = normCanvas.height = size;
  roughCanvas.width = roughCanvas.height = size;
  const nCtx = normCanvas.getContext('2d');
  const rCtx = roughCanvas.getContext('2d');
  const nImg = nCtx.createImageData(size, size);
  const rImg = rCtx.createImageData(size, size);
  const nd = nImg.data;
  const rd = rImg.data;
  const mask = size - 1;

  for (let y = 0; y < size; y++) {
    const ym = ((y - 1) & mask) * size;
    const yp = ((y + 1) & mask) * size;
    const y0 = y * size;
    for (let x = 0; x < size; x++) {
      const xm = (x - 1) & mask;
      const xp = (x + 1) & mask;
      const dx = (heights[y0 + xp] - heights[y0 + xm]) * strength;
      const dy = (heights[yp + x] - heights[ym + x]) * strength;
      const invLen = 1 / Math.hypot(dx, dy, 1);
      const nx = -dx * invLen;
      const ny = -dy * invLen;
      const nz = invLen;
      const idx = (y0 + x) * 4;
      nd[idx] = Math.round(clamp((nx * 0.5 + 0.5) * 255, 0, 255));
      nd[idx + 1] = Math.round(clamp((ny * 0.5 + 0.5) * 255, 0, 255));
      nd[idx + 2] = Math.round(clamp((nz * 0.5 + 0.5) * 255, 128, 255));
      nd[idx + 3] = 255;

      const h = heights[y0 + x];
      const rv = Math.round(clamp((baseRough + (h - 0.5) * roughSpan) * 255, 8, 250));
      rd[idx] = rv;
      rd[idx + 1] = rv;
      rd[idx + 2] = rv;
      rd[idx + 3] = 255;
    }
  }
  nCtx.putImageData(nImg, 0, 0);
  rCtx.putImageData(rImg, 0, 0);

  const configure = (c, repeat = 4) => {
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(repeat, repeat);
    t.anisotropy = 4;
    return t;
  };
  return {
    normalMap: configure(normCanvas),
    roughnessMap: configure(roughCanvas),
  };
}

let cachedSurfaceMaps = null;

/**
 * Deterministic procedural industrial surface textures:
 *   - `anodized`: fine bead-blasted micro-pits + subtle directional brush grain
 *   - `machined`: precision lathe/milling tool marks + harmonic micro-grooves
 *   - `cast`: sand-cast / powder-coat micro-pebble & orange-peel relief
 *   - `hatch`: 45° technical section-cut CNC cross-hatching (albedo + normal)
 *   - `aoRing` / `aoBox`: soft analytical contact-occlusion alpha maps
 */
export function createSurfaceMaps() {
  if (cachedSurfaceMaps) return cachedSurfaceMaps;
  const size = 128;
  const mask = size - 1;

  // 1. Anodized aluminium (bead-blasted + fine horizontal brush)
  const randA = mulberry32(0xCA11AB01);
  const rawA = new Float32Array(size * size);
  for (let i = 0; i < rawA.length; i++) rawA[i] = randA();
  const hAnodized = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    const rowJitter = (randA() - 0.5) * 0.28;
    for (let x = 0; x < size; x++) {
      // Horizontal brush correlation + isotropic bead-blast
      const b =
        rawA[y * size + x] * 0.4 +
        rawA[y * size + ((x + 1) & mask)] * 0.25 +
        rawA[y * size + ((x + 2) & mask)] * 0.2 +
        rawA[((y + 1) & mask) * size + x] * 0.15;
      hAnodized[y * size + x] = clamp(b + rowJitter * 0.35, 0, 1);
    }
  }
  const anodized = buildNormalAndRoughnessFromHeight(size, hAnodized, {
    strength: 1.8,
    baseRough: 0.34,
    roughSpan: 0.16,
  });

  // 2. Machined steel / bronze / graphite (fine parallel/lathe turning grooves + micro-grain)
  const randM = mulberry32(0xCA11AB02);
  const hMachined = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    const v = (y / size) * Math.PI * 2;
    const groove =
      Math.sin(v * 24) * 0.28 +
      Math.sin(v * 52 + 0.7) * 0.16 +
      Math.cos(v * 11 - 0.4) * 0.1;
    for (let x = 0; x < size; x++) {
      const u = (x / size) * Math.PI * 2;
      const cross = Math.sin(u * 18 + v * 6) * 0.08 + (randM() - 0.5) * 0.14;
      hMachined[y * size + x] = clamp(0.5 + groove + cross, 0, 1);
    }
  }
  const machined = buildNormalAndRoughnessFromHeight(size, hMachined, {
    strength: 2.1,
    baseRough: 0.26,
    roughSpan: 0.14,
  });

  // 3. Cast / powder-coated housing (multi-octave smoothed cellular pebble relief)
  const randC = mulberry32(0xCA11AB03);
  let bufC = new Float32Array(size * size);
  for (let i = 0; i < bufC.length; i++) bufC[i] = randC();
  for (let pass = 0; pass < 3; pass++) {
    const next = new Float32Array(size * size);
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        next[y * size + x] =
          (bufC[y * size + x] * 4 +
            bufC[y * size + ((x - 1) & mask)] +
            bufC[y * size + ((x + 1) & mask)] +
            bufC[((y - 1) & mask) * size + x] +
            bufC[((y + 1) & mask) * size + x]) /
          8;
      }
    }
    bufC = next;
  }
  const cast = buildNormalAndRoughnessFromHeight(size, bufC, {
    strength: 3.2,
    baseRough: 0.54,
    roughSpan: 0.22,
  });

  // 4. 45° CNC section-cut hatching texture (albedo + normal)
  const hatchSize = 128;
  const hCanvas = document.createElement('canvas');
  hCanvas.width = hCanvas.height = hatchSize;
  const hCtx = hCanvas.getContext('2d');
  hCtx.fillStyle = '#4A525C';
  hCtx.fillRect(0, 0, hatchSize, hatchSize);
  hCtx.strokeStyle = '#67717D';
  hCtx.lineWidth = 2.2;
  const step = 8;
  for (let offset = -hatchSize; offset < hatchSize * 2; offset += step) {
    hCtx.beginPath();
    hCtx.moveTo(offset, 0);
    hCtx.lineTo(offset - hatchSize, hatchSize);
    hCtx.stroke();
  }
  hCtx.strokeStyle = '#343A42';
  hCtx.lineWidth = 1.1;
  for (let offset = -hatchSize + 3; offset < hatchSize * 2; offset += step) {
    hCtx.beginPath();
    hCtx.moveTo(offset, 0);
    hCtx.lineTo(offset - hatchSize, hatchSize);
    hCtx.stroke();
  }
  const hatchMap = new THREE.CanvasTexture(hCanvas);
  hatchMap.wrapS = hatchMap.wrapT = THREE.RepeatWrapping;
  hatchMap.repeat.set(18, 18);
  hatchMap.encoding = THREE.sRGBEncoding;

  // 5. Soft radial & rectangular crevice AO alpha maps
  const aoRadCanvas = document.createElement('canvas');
  aoRadCanvas.width = aoRadCanvas.height = 128;
  const arCtx = aoRadCanvas.getContext('2d');
  const grad = arCtx.createRadialGradient(64, 64, 18, 64, 64, 62);
  grad.addColorStop(0.0, 'rgba(10, 12, 16, 0.95)');
  grad.addColorStop(0.45, 'rgba(10, 12, 16, 0.65)');
  grad.addColorStop(0.8, 'rgba(10, 12, 16, 0.18)');
  grad.addColorStop(1.0, 'rgba(10, 12, 16, 0.0)');
  arCtx.fillStyle = grad;
  arCtx.fillRect(0, 0, 128, 128);
  const aoRadialTex = new THREE.CanvasTexture(aoRadCanvas);

  // 6. High-density 45°/135° diamond-weave braided hydraulic hose relief map
  const hBraided = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = (x / size) * Math.PI * 2 * 14;
      const v = (y / size) * Math.PI * 2 * 14;
      const strandA = Math.sin(u + v);
      const strandB = Math.sin(u - v);
      const overUnder = strandA * strandB;
      const ridge = Math.max(Math.abs(strandA), Math.abs(strandB));
      hBraided[y * size + x] = clamp(0.35 + ridge * 0.45 + overUnder * 0.2, 0, 1);
    }
  }
  const braided = buildNormalAndRoughnessFromHeight(size, hBraided, {
    strength: 3.4,
    baseRough: 0.68,
    roughSpan: 0.22,
  });

  cachedSurfaceMaps = { anodized, machined, cast, hatchMap, aoRadialTex, braided };
  return cachedSurfaceMaps;
}

/**
 * Tri-planar box UV projection in millimeter space (`mmScale` mm per UV tile).
 * Ensures `ExtrudeGeometry`, `LatheGeometry`, and merged parts share a uniform physical
 * texture density without stretching across bevels or side walls.
 */
export function normalizeGeometryUVs(geometry, mmScale = 56) {
  const pos = geometry.attributes.position;
  if (!pos) return geometry;
  if (!geometry.attributes.normal) geometry.computeVertexNormals();
  const nor = geometry.attributes.normal;
  const uvs = new Float32Array(pos.count * 2);
  const inv = 1 / Math.max(1e-3, mmScale);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const nx = Math.abs(nor.getX(i));
    const ny = Math.abs(nor.getY(i));
    const nz = Math.abs(nor.getZ(i));
    if (ny >= nx && ny >= nz) {
      uvs[i * 2] = x * inv;
      uvs[i * 2 + 1] = z * inv;
    } else if (nx >= ny && nx >= nz) {
      uvs[i * 2] = z * inv;
      uvs[i * 2 + 1] = y * inv;
    } else {
      uvs[i * 2] = x * inv;
      uvs[i * 2 + 1] = y * inv;
    }
  }
  geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  return geometry;
}

/**
 * Enforce `teardown` industrial roughness & IBL reflection discipline on a Three.js material:
 *   - `'shell'` / `'structural'`: clamps `roughness >= 0.45`, `clearcoat <= 0.14`, and `envMapScale = 0.56`
 *     so large housings, plates, and fairings never exhibit plastic/wet specular streaks under key light.
 *   - `'precision'`: allows lower roughness (`>= 0.12`) and full `envMapScale = 1.0` for shafts, pins, and bearings.
 */
export function governIndustrialMaterial(mat, role = 'shell') {
  if (!mat) return mat;
  mat.userData = mat.userData || {};
  if (MATERIAL_ROLES[role]) return governMaterialRole(mat, role);
  if (role === 'shell' || role === 'structural') {
    if (typeof mat.roughness === 'number') mat.roughness = Math.max(0.45, mat.roughness);
    if (typeof mat.clearcoat === 'number') mat.clearcoat = Math.min(0.14, mat.clearcoat);
    mat.userData.envMapScale = mat.userData.envMapScale ?? 0.56;
  } else {
    mat.userData.envMapScale = mat.userData.envMapScale ?? 1.0;
  }
  return mat;
}

/** Palette declared by the product's ref.json (set by `createCalLabStudio`); null = style defaults, unchanged. */
let ACTIVE_REF_PALETTE = null;

export function createMaterials() {
  const mats = createMaterialsRaw();
  const P = ACTIVE_REF_PALETTE;
  if (!P) return mats;
  // ref.json drives defaults: shell family <- shell, mechanism structure <- mechanism, accents <- accent, warm metals <- warm_metal.
  // Structure (roughness, metalness, maps, roles) stays the style's; only the base colour moves. Missing keys leave the style colour.
  const tint = (names, hex) => { if (hex) for (const n of names) mats[n]?.color?.set(hex); };
  tint(['white', 'alu'], P.shell);
  tint(['aluDark', 'graphite', 'titanium'], P.mechanism);
  tint(['accent', 'accentGlow', 'anodizedRed'], P.accent);
  tint(['bronze', 'brass'], P.warm_metal);
  return mats;
}

function createMaterialsRaw() {
  const std = (o) => new THREE.MeshStandardMaterial(o);
  const phys = (o) => new THREE.MeshPhysicalMaterial(o);
  const maps = createSurfaceMaps();
  const v2 = (s) => new THREE.Vector2(s, s);

  return {
    alu: governIndustrialMaterial(
      std({
        color: CAL_PALETTE.anodized,
        metalness: 0.86,
        roughness: 0.45,
        normalMap: maps.anodized.normalMap,
        roughnessMap: maps.anodized.roughnessMap,
        normalScale: v2(0.16),
      }),
      'shell',
    ),
    aluDark: governIndustrialMaterial(
      std({
        color: CAL_PALETTE.anodizedDark,
        metalness: 0.84,
        roughness: 0.48,
        normalMap: maps.anodized.normalMap,
        roughnessMap: maps.anodized.roughnessMap,
        normalScale: v2(0.18),
      }),
      'shell',
    ),
    titanium: governIndustrialMaterial(
      std({
        color: '#9AA2AD',
        metalness: 0.85,
        roughness: 0.46,
        normalMap: maps.anodized.normalMap,
        roughnessMap: maps.anodized.roughnessMap,
        normalScale: v2(0.18),
      }),
      'shell',
    ),
    white: governIndustrialMaterial(
      phys({
        color: CAL_PALETTE.powder,
        metalness: 0.06,
        roughness: 0.56,
        clearcoat: 0.12,
        clearcoatRoughness: 0.42,
        normalMap: maps.cast.normalMap,
        roughnessMap: maps.cast.roughnessMap,
        normalScale: v2(0.18),
      }),
      'shell',
    ),
    black: governIndustrialMaterial(
      phys({
        color: CAL_PALETTE.structure,
        metalness: 0.36,
        roughness: 0.46,
        clearcoat: 0.14,
        clearcoatRoughness: 0.34,
        normalMap: maps.cast.normalMap,
        roughnessMap: maps.cast.roughnessMap,
        normalScale: v2(0.20),
      }),
      'shell',
    ),
    liner: governIndustrialMaterial(
      std({
        color: '#16191E',
        metalness: 0.28,
        roughness: 0.68,
        normalMap: maps.cast.normalMap,
        roughnessMap: maps.cast.roughnessMap,
        normalScale: v2(0.22),
      }),
      'shell',
    ),
    steel: governIndustrialMaterial(
      std({
        color: CAL_PALETTE.steel,
        metalness: 0.96,
        roughness: 0.24,
        normalMap: maps.machined.normalMap,
        roughnessMap: maps.machined.roughnessMap,
        normalScale: v2(0.18),
      }),
      'precision',
    ),
    chrome: governIndustrialMaterial(
      std({
        color: CAL_PALETTE.chrome,
        metalness: 1.0,
        roughness: 0.12,
        normalMap: maps.machined.normalMap,
        normalScale: v2(0.08),
      }),
      'precision',
    ),
    bronze: governIndustrialMaterial(
      std({
        color: CAL_PALETTE.bronze,
        metalness: 0.92,
        roughness: 0.28,
        normalMap: maps.machined.normalMap,
        roughnessMap: maps.machined.roughnessMap,
        normalScale: v2(0.16),
      }),
      'precision',
    ),
    brass: governIndustrialMaterial(
      std({
        color: '#C8A24E',
        metalness: 0.92,
        roughness: 0.26,
        normalMap: maps.machined.normalMap,
        roughnessMap: maps.machined.roughnessMap,
        normalScale: v2(0.16),
      }),
      'precision',
    ),
    anodizedRed: governIndustrialMaterial(
      std({
        color: '#D93824',
        metalness: 0.78,
        roughness: 0.36,
        normalMap: maps.anodized.normalMap,
        roughnessMap: maps.anodized.roughnessMap,
        normalScale: v2(0.15),
      }),
      'precision',
    ),
    graphite: governIndustrialMaterial(
      std({
        color: '#464C53',
        metalness: 0.62,
        roughness: 0.46,
        normalMap: maps.machined.normalMap,
        roughnessMap: maps.machined.roughnessMap,
        normalScale: v2(0.18),
      }),
      'shell',
    ),
    rubber: std({
      color: CAL_PALETTE.rubber,
      metalness: 0.06,
      roughness: 0.88,
      normalMap: maps.cast.normalMap,
      normalScale: v2(0.24),
    }),
    braidedHose: std({
      color: '#1E2126',
      metalness: 0.18,
      roughness: 0.70,
      normalMap: maps.braided.normalMap,
      roughnessMap: maps.braided.roughnessMap,
      normalScale: v2(0.38),
    }),
    sectionCap: std({
      color: '#FFFFFF',
      map: maps.hatchMap,
      normalMap: maps.machined.normalMap,
      normalScale: v2(0.22),
      metalness: 0.55,
      roughness: 0.48,
      side: THREE.DoubleSide,
    }),
    glass: phys({
      color: CAL_PALETTE.glass,
      metalness: 0,
      roughness: 0.06,
      transparent: true,
      opacity: 0.18,
      depthWrite: false,
      side: THREE.DoubleSide,
      envMapIntensity: 1.4,
    }),
    accent: new THREE.MeshBasicMaterial({ color: CAL_PALETTE.accent, toneMapped: false }),
    accentGlow: new THREE.MeshBasicMaterial({
      color: CAL_PALETTE.accent,
      transparent: true,
      opacity: 0.22,
      toneMapped: false,
      depthWrite: false,
    }),
  };
}

// ============================================================================
// 3. INDUSTRIAL CSG-2D, MULTI-AXIS & BIONIC GEOMETRY PRIMITIVES + CREVICE AO
// ============================================================================

function makeRoundedRectShape(w, d, r = 4) {
  const rr = Math.max(0.01, Math.min(r, Math.min(w, d) / 2 - 0.01));
  const hw = w / 2;
  const hd = d / 2;
  const s = new THREE.Shape();
  s.moveTo(-hw + rr, -hd);
  s.lineTo(hw - rr, -hd);
  s.quadraticCurveTo(hw, -hd, hw, -hd + rr);
  s.lineTo(hw, hd - rr);
  s.quadraticCurveTo(hw, hd, hw - rr, hd);
  s.lineTo(-hw + rr, hd);
  s.quadraticCurveTo(-hw, hd, -hw, hd - rr);
  s.lineTo(-hw, -hd + rr);
  s.quadraticCurveTo(-hw, -hd, -hw + rr, -hd);
  s.closePath();
  return s;
}

function makeRoundedSlotPath(cx, cz, w, d, r = 2) {
  const rr = Math.max(0.01, Math.min(r, Math.min(w, d) / 2 - 0.01));
  const hw = w / 2;
  const hd = d / 2;
  // Clockwise winding so ExtrudeGeometry treats it as an interior hole
  const p = new THREE.Path();
  p.moveTo(cx - hw + rr, cz - hd);
  p.quadraticCurveTo(cx - hw, cz - hd, cx - hw, cz - hd + rr);
  p.lineTo(cx - hw, cz + hd - rr);
  p.quadraticCurveTo(cx - hw, cz + hd, cx - hw + rr, cz + hd);
  p.lineTo(cx + hw - rr, cz + hd);
  p.quadraticCurveTo(cx + hw, cz + hd, cx + hw, cz + hd - rr);
  p.lineTo(cx + hw, cz - hd + rr);
  p.quadraticCurveTo(cx + hw, cz - hd, cx + hw - rr, cz - hd);
  p.closePath();
  return p;
}

/** Rounded-corner box, extruded and centred on the origin. `w` × `d` is the footprint, `h` the height. */
export function blockGeometry({ w, h, d, r = 4, bevel = 1.2 }) {
  const s = makeRoundedRectShape(w, d, r);
  const bv = Math.min(bevel, Math.min(w, h, d) * 0.22);
  const g = new THREE.ExtrudeGeometry(s, {
    depth: Math.max(0.2, h - bv * 2),
    bevelEnabled: bv > 0.01,
    bevelThickness: bv,
    bevelSize: bv,
    bevelSegments: 2,
    curveSegments: 8,
    steps: 1,
  });
  g.rotateX(-Math.PI / 2);
  g.translate(0, -h / 2 + bv, 0);
  g.computeVertexNormals();
  return normalizeGeometryUVs(g);
}

/**
 * 2D CSG boolean-subtracted plate / bulkhead / flange (`machinedPlateGeometry`).
 * Subtracts circular bores (`holes: [{ x = 0, z = 0, r }]`) and stadium/rounded-rect weight-relief
 * pockets or windows (`slots: [{ x = 0, z = 0, w, d, r }]`) before bevelled extrusion.
 */
export function machinedPlateGeometry({
  w,
  h,
  d,
  r = 5,
  bevel = 1.0,
  holes = [],
  slots = [],
  curveSegments = 24,
}) {
  const s = makeRoundedRectShape(w, d, r);
  for (const hole of holes) {
    const p = new THREE.Path();
    p.absarc(hole.x || 0, -(hole.z || 0), hole.r, 0, Math.PI * 2, true);
    s.holes.push(p);
  }
  for (const slot of slots) {
    s.holes.push(makeRoundedSlotPath(slot.x || 0, -(slot.z || 0), slot.w, slot.d, slot.r ?? Math.min(slot.w, slot.d) * 0.45));
  }
  const bv = Math.min(bevel, Math.min(w, h, d) * 0.2);
  const g = new THREE.ExtrudeGeometry(s, {
    depth: Math.max(0.2, h - bv * 2),
    bevelEnabled: bv > 0.01,
    bevelThickness: bv,
    bevelSize: bv,
    bevelSegments: 2,
    curveSegments,
    steps: 1,
  });
  g.rotateX(-Math.PI / 2);
  g.translate(0, -h / 2 + bv, 0);
  g.computeVertexNormals();
  return normalizeGeometryUVs(g);
}

/**
 * Recessed counterbore boss / bearing seat (`counterboreBossGeometry`).
 * Lathes a watertight profile with a through-bore `rBore`, outer chamfered cylinder `rOuter`,
 * and stepped top counterbore pocket `rCounter` of depth `hCounter` so fasteners sit inside a
 * machined recess instead of floating on a flat surface.
 */
export function counterboreBossGeometry({
  rOuter = 11,
  rBore = 3.2,
  rCounter = 6.8,
  hTotal = 9,
  hCounter = 3.8,
  bevel = 0.8,
  seg = 32,
} = {}) {
  const y0 = -hTotal / 2;
  const y1 = hTotal / 2;
  const yc = y1 - clamp(hCounter, 0.5, hTotal - 1.0);
  const b = Math.min(bevel, (rOuter - rCounter) * 0.4, hTotal * 0.2);
  const profile = [
    [rBore, y0],
    [rOuter - b, y0],
    [rOuter, y0 + b],
    [rOuter, y1 - b],
    [rOuter - b, y1],
    [rCounter, y1],
    [rCounter, yc],
    [rBore, yc],
    [rBore, y0],
  ];
  const g = new THREE.LatheGeometry(
    profile.map(([r, y]) => new THREE.Vector2(r, y)),
    seg,
  );
  g.computeVertexNormals();
  return normalizeGeometryUVs(g);
}

/**
 * Forged/machined I-beam connecting link or robotic limb segment (`ribbedLinkGeometry`).
 * Origin is at the midpoint between the two bearing centres (`y = -length/2` and `y = +length/2`).
 * Includes bored big/small ends, tapered flanges, and recessed front/back I-beam pockets.
 */
export function ribbedLinkGeometry({
  length = 143,
  rBig = 23,
  rSmall = 13.5,
  rBoreBig = 15,
  rBoreSmall = 8.5,
  beamW = 19,
  thickness = 16,
  webThickness = 5.5,
  bevel = 0.9,
} = {}) {
  const halfL = length / 2;
  const sh = new THREE.Shape();
  const w0 = beamW * 0.56;
  const w1 = beamW * 0.42;
  const yBig = -halfL;
  const ySmall = halfL;

  const aBig = Math.acos(clamp(w0 / rBig, -0.95, 0.95));
  const aSmall = Math.acos(clamp(w1 / rSmall, -0.95, 0.95));

  sh.absarc(0, yBig, rBig, aBig, Math.PI - aBig, true);
  sh.lineTo(-w1, ySmall - rSmall * Math.sin(aSmall));
  sh.absarc(0, ySmall, rSmall, Math.PI + aSmall, -aSmall, true);
  sh.closePath();

  if (rBoreBig > 0) {
    const hBig = new THREE.Path();
    hBig.absarc(0, yBig, rBoreBig, 0, Math.PI * 2, false);
    sh.holes.push(hBig);
  }
  if (rBoreSmall > 0) {
    const hSmall = new THREE.Path();
    hSmall.absarc(0, ySmall, rBoreSmall, 0, Math.PI * 2, false);
    sh.holes.push(hSmall);
  }

  // Subtract recessed I-beam web channels on front and back by building a central web + raised rim
  const rim = new THREE.Shape();
  rim.absarc(0, yBig, rBig, aBig, Math.PI - aBig, true);
  rim.lineTo(-w1, ySmall - rSmall * Math.sin(aSmall));
  rim.absarc(0, ySmall, rSmall, Math.PI + aSmall, -aSmall, true);
  rim.closePath();
  if (rBoreBig > 0) {
    const hBig = new THREE.Path();
    hBig.absarc(0, yBig, rBoreBig, 0, Math.PI * 2, false);
    rim.holes.push(hBig);
  }
  if (rBoreSmall > 0) {
    const hSmall = new THREE.Path();
    hSmall.absarc(0, ySmall, rBoreSmall, 0, Math.PI * 2, false);
    rim.holes.push(hSmall);
  }

  const slotBottom = yBig + rBig + 4;
  const slotTop = ySmall - rSmall - 4;
  const slotH = slotTop - slotBottom;
  const slotW = Math.max(3, (w0 + w1) - 7);
  if (slotH > 8 && slotW > 3) {
    const pocket = new THREE.Path();
    const cy = (slotBottom + slotTop) / 2;
    const hw = slotW / 2;
    const hh = slotH / 2;
    const pr = Math.min(hw * 0.85, 4);
    pocket.moveTo(-hw + pr, cy - hh);
    pocket.lineTo(hw - pr, cy - hh);
    pocket.quadraticCurveTo(hw, cy - hh, hw, cy - hh + pr);
    pocket.lineTo(hw, cy + hh - pr);
    pocket.quadraticCurveTo(hw, cy + hh, hw - pr, cy + hh);
    pocket.lineTo(-hw + pr, cy + hh);
    pocket.quadraticCurveTo(-hw, cy + hh, -hw, cy + hh - pr);
    pocket.lineTo(-hw, cy - hh + pr);
    pocket.quadraticCurveTo(-hw, cy - hh, -hw + pr, cy - hh);
    pocket.closePath();
    rim.holes.push(pocket);
  }

  const webGeo = new THREE.ExtrudeGeometry(sh, {
    depth: webThickness,
    bevelEnabled: false,
    curveSegments: 28,
  });
  webGeo.translate(0, 0, -webThickness / 2);

  const rimGeo = new THREE.ExtrudeGeometry(rim, {
    depth: Math.max(1, thickness - bevel * 2),
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 2,
    curveSegments: 28,
  });
  rimGeo.translate(0, 0, -(thickness - bevel * 2) / 2);

  return normalizeGeometryUVs(mergeGeometries([webGeo, rimGeo]));
}

/**
 * Spur/helical gear blank from a tooth count — the rule that makes any two gears mesh:
 * pitch radius follows from the teeth, so a 24-tooth and a 52-tooth turn at 52:24.
 */
export function gearGeometry({
  teeth,
  rOut,
  rRoot,
  width,
  helix = 0,
  holeR = 0,
  lighteningHoles = 0,
  lighteningR = 0,
  bevel = 0.8,
}) {
  const sh = new THREE.Shape();
  const da = (Math.PI * 2) / teeth;
  for (let i = 0; i < teeth; i++) {
    const a0 = i * da;
    const pts = [
      [rRoot, a0],
      [rRoot, a0 + da * 0.2],
      [rOut, a0 + da * 0.33],
      [rOut, a0 + da * 0.62],
      [rRoot, a0 + da * 0.75],
    ];
    for (let k = 0; k < pts.length; k++) {
      const [rr, a] = pts[k];
      const x = rr * Math.cos(a);
      const y = rr * Math.sin(a);
      if (i === 0 && k === 0) sh.moveTo(x, y);
      else sh.lineTo(x, y);
    }
  }
  sh.closePath();
  if (holeR > 0) {
    const hole = new THREE.Path();
    hole.absarc(0, 0, holeR, 0, Math.PI * 2, true);
    sh.holes.push(hole);
  }
  if (lighteningHoles > 0) {
    const pitchR = (rRoot + Math.max(holeR, rRoot * 0.25)) * 0.52;
    const lr = lighteningR || Math.min((rRoot - holeR) * 0.24, (pitchR * Math.PI) / (lighteningHoles * 1.8));
    if (lr > 1.5) {
      for (let i = 0; i < lighteningHoles; i++) {
        const a = (i * Math.PI * 2) / lighteningHoles;
        const p = new THREE.Path();
        p.absarc(Math.cos(a) * pitchR, Math.sin(a) * pitchR, lr, 0, Math.PI * 2, true);
        sh.holes.push(p);
      }
    }
  }
  const g = new THREE.ExtrudeGeometry(sh, {
    depth: width,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 1,
    curveSegments: 4,
  });
  g.translate(0, 0, -width / 2);
  if (helix) {
    const pos = g.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const a = (pos.getZ(i) / width) * helix;
      const x = pos.getX(i);
      const y = pos.getY(i);
      pos.setXY(i, x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a));
    }
    pos.needsUpdate = true;
  }
  g.computeVertexNormals();
  return normalizeGeometryUVs(g);
}

/** Coil spring as a swept tube; callers scale it along y (or use `poseCompressedSpring`) to show compression. */
export function helixGeometry({ r, wire, turns, len, seg = 160 }) {
  const pts = [];
  for (let i = 0; i <= seg; i++) {
    const u = i / seg;
    const a = u * turns * Math.PI * 2;
    pts.push(new THREE.Vector3(Math.cos(a) * r, u * len, Math.sin(a) * r));
  }
  const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), seg, wire, 10, false);
  return normalizeGeometryUVs(g);
}

/**
 * Hex-head / Socket-head fastener (`boltGeometry`) with recessed allen socket and flanged washer.
 */
export function boltGeometry({ r = 4, h = 6, washer = true }) {
  const profile = [
    [r * 0.46, h * 0.12],
    [r * 0.46, h * 0.5],
    [r * 0.92, h * 0.5],
    [r, h * 0.38],
    [r, -h * 0.5],
    [0, -h * 0.5],
    [0, h * 0.12],
    [r * 0.46, h * 0.12],
  ];
  const head = new THREE.LatheGeometry(
    profile.map(([rx, y]) => new THREE.Vector2(rx, y)),
    6,
  );
  if (!washer) {
    head.computeVertexNormals();
    return normalizeGeometryUVs(head);
  }
  const w = new THREE.CylinderGeometry(r * 1.62, r * 1.68, h * 0.28, 20);
  w.translate(0, -h / 2 + h * 0.14, 0);
  return normalizeGeometryUVs(mergeGeometries([head, w]));
}

/**
 * Parallel-transport (Bishop frame) variable-radius / elliptical spline sweep (`sweptProfileGeometry`).
 * Ideal for bionic octopus tentacles, tapered manifolds, hydraulic lines, and compliant continuum arms.
 * Pair with `updateSweptGeometry` for real-time deformation without recreating buffers.
 */
export function sweptProfileGeometry({
  points,
  radiusAt = 6,
  scaleZAt = null,
  tubularSeg = 48,
  radialSeg = 20,
  capEnds = true,
}) {
  const ringCount = tubularSeg + 1;
  const stride = radialSeg + 1;
  const bodyVerts = ringCount * stride;
  const capVerts = capEnds ? 2 * (radialSeg + 2) : 0;
  const totalVerts = bodyVerts + capVerts;

  const pos = new Float32Array(totalVerts * 3);
  const nor = new Float32Array(totalVerts * 3);
  const uvs = new Float32Array(totalVerts * 2);
  const indices = [];

  for (let i = 0; i < tubularSeg; i++) {
    for (let j = 0; j < radialSeg; j++) {
      const a = i * stride + j;
      const b = (i + 1) * stride + j;
      const c = (i + 1) * stride + (j + 1);
      const d = i * stride + (j + 1);
      indices.push(a, b, d, b, c, d);
    }
  }
  if (capEnds) {
    const startCenter = bodyVerts;
    for (let j = 0; j < radialSeg; j++) {
      indices.push(startCenter, startCenter + 1 + ((j + 1) % stride), startCenter + 1 + j);
    }
    const endCenter = bodyVerts + radialSeg + 2;
    for (let j = 0; j < radialSeg; j++) {
      indices.push(endCenter, endCenter + 1 + j, endCenter + 1 + ((j + 1) % stride));
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.userData.sweepMeta = { tubularSeg, radialSeg, capEnds };

  updateSweptGeometry(geo, points, radiusAt, scaleZAt);
  return geo;
}

/**
 * Recompute vertex positions and normals of a `sweptProfileGeometry` along updated 3D `points`.
 */
export function updateSweptGeometry(geo, points, radiusAt = 6, scaleZAt = null) {
  const { tubularSeg, radialSeg, capEnds } = geo.userData.sweepMeta;
  const ringCount = tubularSeg + 1;
  const stride = radialSeg + 1;
  const bodyVerts = ringCount * stride;

  const vecPts = points.map((p) => (p.isVector3 ? p : new THREE.Vector3(p[0], p[1], p[2])));
  const curve = new THREE.CatmullRomCurve3(vecPts);
  const rFn = typeof radiusAt === 'function' ? radiusAt : () => radiusAt;
  const zFn = typeof scaleZAt === 'function' ? scaleZAt : () => (scaleZAt ?? 1);

  const posAttr = geo.attributes.position;
  const uvsAttr = geo.attributes.uv;
  const pos = posAttr.array;
  const uvs = uvsAttr.array;

  const T = new THREE.Vector3();
  const prevT = new THREE.Vector3();
  const N = new THREE.Vector3();
  const B = new THREE.Vector3();
  const rotAxis = new THREE.Vector3();
  const q = new THREE.Quaternion();
  const P = new THREE.Vector3();

  for (let i = 0; i <= tubularSeg; i++) {
    const u = i / tubularSeg;
    curve.getPointAt(u, P);
    curve.getTangentAt(u, T).normalize();

    if (i === 0) {
      const up = Math.abs(T.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
      B.crossVectors(T, up).normalize();
      N.crossVectors(B, T).normalize();
    } else {
      rotAxis.crossVectors(prevT, T);
      const sinA = rotAxis.length();
      if (sinA > 1e-5) {
        rotAxis.divideScalar(sinA);
        const cosA = clamp(prevT.dot(T), -1, 1);
        q.setFromAxisAngle(rotAxis, Math.atan2(sinA, cosA));
        N.applyQuaternion(q);
      }
      N.sub(T.clone().multiplyScalar(N.dot(T))).normalize();
      B.crossVectors(T, N).normalize();
    }
    prevT.copy(T);

    const rx = rFn(u);
    const rz = rx * zFn(u);
    for (let j = 0; j <= radialSeg; j++) {
      const v = j / radialSeg;
      const ang = v * Math.PI * 2;
      const ca = Math.cos(ang);
      const sa = Math.sin(ang);
      const idx = (i * stride + j) * 3;
      pos[idx] = P.x + N.x * ca * rx + B.x * sa * rz;
      pos[idx + 1] = P.y + N.y * ca * rx + B.y * sa * rz;
      pos[idx + 2] = P.z + N.z * ca * rx + B.z * sa * rz;
      const uvIdx = (i * stride + j) * 2;
      uvs[uvIdx] = u * 6;
      uvs[uvIdx + 1] = v * 2;
    }

    if (capEnds && (i === 0 || i === tubularSeg)) {
      const capBase = i === 0 ? bodyVerts : bodyVerts + radialSeg + 2;
      pos[capBase * 3] = P.x;
      pos[capBase * 3 + 1] = P.y;
      pos[capBase * 3 + 2] = P.z;
      for (let j = 0; j <= radialSeg; j++) {
        const ringIdx = (i * stride + j) * 3;
        const cIdx = (capBase + 1 + j) * 3;
        pos[cIdx] = pos[ringIdx];
        pos[cIdx + 1] = pos[ringIdx + 1];
        pos[cIdx + 2] = pos[ringIdx + 2];
      }
    }
  }

  posAttr.needsUpdate = true;
  uvsAttr.needsUpdate = true;
  geo.computeVertexNormals();
  return geo;
}

/**
 * Accordion-pleated hydraulic/pneumatic bellows or soft actuator (`bellowsGeometry`).
 */
export function bellowsGeometry({ rInner = 9, rOuter = 14, rBore = 0, ribs = 7, len = 36, seg = 36 } = {}) {
  const profile = [];
  const y0 = -len / 2;
  const step = len / ribs;
  if (rBore > 0) profile.push([rBore, y0]);
  else profile.push([0, y0]);
  profile.push([rInner, y0]);

  for (let i = 0; i < ribs; i++) {
    const ya = y0 + i * step;
    const ym = ya + step * 0.5;
    const yb = ya + step;
    profile.push([rInner, ya + step * 0.12]);
    profile.push([rOuter, ym - step * 0.08]);
    profile.push([rOuter, ym + step * 0.08]);
    profile.push([rInner, yb - step * 0.12]);
  }
  profile.push([rInner, y0 + len]);
  if (rBore > 0) {
    profile.push([rBore, y0 + len]);
    profile.push([rBore, y0]);
  } else {
    profile.push([0, y0 + len]);
  }

  const g = new THREE.LatheGeometry(
    profile.map(([r, y]) => new THREE.Vector2(r, y)),
    seg,
  );
  g.computeVertexNormals();
  return normalizeGeometryUVs(g);
}

/**
 * Spherical ball-and-socket joint primitive (`ballJointGeometry`) for multi-DOF arms & tentacles.
 */
export function ballJointGeometry({
  rBall = 10,
  rSocket = 12.6,
  neckR = 4.6,
  neckLen = 14,
  cupAngle = Math.PI * 0.62,
  seg = 32,
} = {}) {
  const ball = new THREE.SphereGeometry(rBall, seg, Math.round(seg * 0.65));
  const neck = new THREE.CylinderGeometry(neckR, neckR * 1.12, neckLen, Math.round(seg * 0.75));
  neck.translate(0, -rBall * 0.7 - neckLen / 2, 0);
  const ballGeo = normalizeGeometryUVs(mergeGeometries([ball, neck]));

  const socketProfile = [];
  const steps = 16;
  const rInner = rBall + 0.35;
  for (let i = 0; i <= steps; i++) {
    const a = -Math.PI / 2 + (i / steps) * cupAngle;
    socketProfile.push([Math.max(0, Math.cos(a) * rSocket), Math.sin(a) * rSocket]);
  }
  for (let i = steps; i >= 0; i--) {
    const a = -Math.PI / 2 + (i / steps) * cupAngle;
    socketProfile.push([Math.max(0, Math.cos(a) * rInner), Math.sin(a) * rInner]);
  }
  socketProfile.push(socketProfile[0]);
  const socketGeo = normalizeGeometryUVs(
    new THREE.LatheGeometry(
      socketProfile.map(([r, y]) => new THREE.Vector2(r, y)),
      seg,
    ),
  );
  return { ballGeo, socketGeo };
}

/**
 * Analytical Crevice AO ring (`creviceAoRing`) for fastener bases, cylinder flanges, and shaft shoulders.
 * Grounds intersecting parts so they never look pasted together.
 */
export function creviceAoRing({ rIn = 4, rOut = 9, opacity = 0.46, seg = 32 } = {}) {
  const g = new THREE.RingGeometry(rIn, rOut, seg, 1);
  g.rotateX(-Math.PI / 2);
  const pos = g.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  const alphas = new Float32Array(pos.count);
  for (let i = 0; i < pos.count; i++) {
    const r = Math.hypot(pos.getX(i), pos.getZ(i));
    const u = clamp((r - rIn) / Math.max(1e-3, rOut - rIn), 0, 1);
    const fade = Math.pow(1 - u, 1.8);
    colors[i * 3] = 0.05;
    colors[i * 3 + 1] = 0.06;
    colors[i * 3 + 2] = 0.08;
    alphas[i] = fade;
  }
  g.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const maps = createSurfaceMaps();
  const mat = new THREE.MeshBasicMaterial({
    color: '#0D1014',
    alphaMap: maps.aoRadialTex,
    transparent: true,
    opacity,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -2,
    toneMapped: false,
  });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(rOut * 2.1, rOut * 2.1).rotateX(-Math.PI / 2), mat);
  m.castShadow = false;
  m.receiveShadow = false;
  m.userData.skipContactShadow = true;
  return m;
}

/**
 * Rectangular Crevice AO collar (`creviceAoBox`) for box walls, deck joints, and mounting bases.
 */
export function creviceAoBox({ w = 100, d = 100, spread = 12, opacity = 0.38 } = {}) {
  const maps = createSurfaceMaps();
  const mat = new THREE.MeshBasicMaterial({
    color: '#0D1014',
    alphaMap: maps.aoRadialTex,
    transparent: true,
    opacity,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -2,
    toneMapped: false,
  });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w + spread * 2, d + spread * 2).rotateX(-Math.PI / 2), mat);
  m.castShadow = false;
  m.receiveShadow = false;
  m.userData.skipContactShadow = true;
  return m;
}

/** Minimal BufferGeometry merge (preserves position, normal, and uv attributes). */
export function mergeGeometries(list) {
  let vCount = 0;
  let iCount = 0;
  for (const g of list) {
    vCount += g.attributes.position.count;
    iCount += g.index ? g.index.count : g.attributes.position.count;
  }
  const pos = new Float32Array(vCount * 3);
  const nor = new Float32Array(vCount * 3);
  const uvs = new Float32Array(vCount * 2);
  const idx = new Uint32Array(iCount);
  let vo = 0;
  let io = 0;
  for (const g of list) {
    pos.set(g.attributes.position.array, vo * 3);
    if (g.attributes.normal) nor.set(g.attributes.normal.array, vo * 3);
    if (g.attributes.uv) uvs.set(g.attributes.uv.array, vo * 2);
    const c = g.attributes.position.count;
    if (g.index) {
      const a = g.index.array;
      for (let k = 0; k < a.length; k++) idx[io++] = a[k] + vo;
    } else {
      for (let k = 0; k < c; k++) idx[io++] = k + vo;
    }
    vo += c;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  out.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  out.setIndex(new THREE.BufferAttribute(idx, 1));
  out.computeVertexNormals();
  return out;
}

// ============================================================================
// 3B. COMPOUND INDUSTRIAL ASSEMBLIES (DE-STICKERIZED PARAMETRIC SUB-ASSEMBLIES)
// ============================================================================

/**
 * High-DPI Technical Silkscreen Decal (`createSilkscreenDecal`).
 * Renders crisp `JetBrains Mono` serial numbers (`01`~`08`), inspection stencil markings,
 * and fiducial registration ticks onto a polygon-offset decal plane flush with any shell face.
 */
export function createSilkscreenDecal({
  text = '01',
  subText = 'MOD-A',
  width = 22,
  height = 12,
  fg = '#181C22',
  accent = CAL_PALETTE.accent,
} = {}) {
  const c = document.createElement('canvas');
  c.width = 256;
  c.height = 140;
  const g = c.getContext('2d');
  g.clearRect(0, 0, 256, 140);

  // Registration bracket & accent bar
  g.fillStyle = accent;
  g.fillRect(10, 18, 8, 104);
  g.strokeStyle = fg;
  g.lineWidth = 3;
  g.strokeRect(10, 18, 236, 104);

  // Primary stencil serial number
  g.fillStyle = fg;
  g.font = '800 68px "JetBrains Mono", monospace';
  g.textBaseline = 'alphabetic';
  g.fillText(String(text), 30, 88);

  if (subText) {
    g.font = '700 22px "JetBrains Mono", monospace';
    g.fillStyle = '#565E68';
    g.fillText(String(subText).toUpperCase(), 32, 114);
  }

  // Corner fiducial ticks
  g.fillStyle = fg;
  g.fillRect(228, 28, 10, 10);
  g.fillRect(228, 46, 10, 4);

  const tex = new THREE.CanvasTexture(c);
  tex.encoding = THREE.sRGBEncoding;
  tex.minFilter = THREE.LinearFilter;
  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
    toneMapped: false,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), mat);
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  mesh.userData.skipContactShadow = true;
  return mesh;
}

/**
 * Compound Segmented Bevelled Shell Panel (`segmentedShellPanel`).
 * Replaces bare single-mesh covers with a multi-layer industrial fairing assembly (`Pelagos OC-8` standard):
 *   1. Bevelled outer shell plate with countersunk perimeter fastener bores;
 *   2. Recessed dark structural chassis liner (`linerMat`, inset by `partingGap`) so panel seams read
 *      with crisp dark shadow lines even on pale white/silver shells;
 *   3. Countersunk socket-head perimeter bolts (`boltGeometry`) + `creviceAoRing` collars;
 *   4. Anodized red/orange mechanical quick-release latches (`accentMat`) on the parting edge;
 *   5. Flush technical silkscreen serial number decal (`01`~`08`).
 */
export function segmentedShellPanel({
  width = 78,
  length = 96,
  thickness = 6.5,
  cornerR = 5,
  bevel = 1.1,
  partingGap = 2.2,
  linerThickness = 3.2,
  boltInset = 9.5,
  boltRadius = 2.6,
  latchCount = 2,
  serialText = '01',
  serialSub = 'PNL',
  slots = [],
  holes = [],
  shellMat = null,
  linerMat = null,
  accentMat = null,
  boltMat = null,
} = {}) {
  const M = createMaterials();
  const sMat = governIndustrialMaterial(shellMat || M.white, 'shell');
  const lMat = governIndustrialMaterial(linerMat || M.liner, 'shell');
  const aMat = accentMat || M.anodizedRed;
  const bMat = boltMat || M.steel;

  const group = new THREE.Group();
  const hw = width / 2 - boltInset;
  const hl = length / 2 - boltInset;
  const cornerBolts = [
    [-hw, -hl],
    [hw, -hl],
    [-hw, hl],
    [hw, hl],
  ];
  const allHoles = [
    ...holes,
    ...cornerBolts.map(([bx, bz]) => ({ x: bx, z: bz, r: boltRadius * 0.95 })),
  ];

  // 1. Dark recessed chassis liner (sits beneath the outer shell and extends into parting seams)
  const linerGeo = machinedPlateGeometry({
    w: Math.max(8, width - partingGap * 2),
    h: linerThickness,
    d: Math.max(8, length - partingGap * 2),
    r: Math.max(2, cornerR - 1),
    bevel: 0.6,
    slots,
  });
  const linerMesh = new THREE.Mesh(linerGeo, lMat);
  linerMesh.position.y = -thickness * 0.5 - linerThickness * 0.35;
  linerMesh.castShadow = true;
  linerMesh.receiveShadow = true;
  group.add(linerMesh);

  // 2. Outer bevelled machined shell plate
  const shellGeo = machinedPlateGeometry({
    w: width,
    h: thickness,
    d: length,
    r: cornerR,
    bevel,
    holes: allHoles,
    slots,
  });
  const shellMesh = new THREE.Mesh(shellGeo, sMat);
  shellMesh.castShadow = true;
  shellMesh.receiveShadow = true;
  group.add(shellMesh);

  // 3. Countersunk corner boss seats + hex fasteners + crevice AO rings
  const bossGeo = counterboreBossGeometry({
    rOuter: boltRadius * 1.95,
    rBore: boltRadius * 0.72,
    rCounter: boltRadius * 1.35,
    hTotal: thickness * 0.92,
    hCounter: thickness * 0.38,
    bevel: 0.4,
    seg: 24,
  });
  const fastenerGeo = boltGeometry({ r: boltRadius, h: boltRadius * 1.35, washer: true });

  for (const [bx, bz] of cornerBolts) {
    const boss = new THREE.Mesh(bossGeo, lMat);
    boss.position.set(bx, 0.2, bz);
    group.add(boss);

    const bolt = new THREE.Mesh(fastenerGeo, bMat);
    bolt.position.set(bx, thickness * 0.5 + 0.4, bz);
    bolt.castShadow = true;
    group.add(bolt);

    const ao = creviceAoRing({ rIn: boltRadius * 1.4, rOut: boltRadius * 2.5, opacity: 0.44 });
    ao.position.set(bx, thickness * 0.5 + 0.08, bz);
    group.add(ao);
  }

  // 4. Anodized red/orange mechanical latches along the parting seam
  if (latchCount > 0) {
    const latchW = Math.min(12, width * 0.16);
    const latchH = thickness * 0.85;
    const latchD = 5.4;
    const latchGeo = blockGeometry({ w: latchW, h: latchH, d: latchD, r: 1.2, bevel: 0.5 });
    for (let i = 0; i < latchCount; i++) {
      const side = i % 2 === 0 ? 1 : -1;
      const zOff = latchCount > 2 ? ((Math.floor(i / 2) - 0.5) * length * 0.42) : 0;
      const latch = new THREE.Mesh(latchGeo, aMat);
      latch.position.set(side * (width * 0.5 - latchW * 0.32), 0.35, zOff);
      latch.castShadow = true;
      group.add(latch);
    }
  }

  // 5. Silkscreen serial number decal flush on the outer face
  if (serialText) {
    const decalW = Math.min(width * 0.42, 26);
    const decalH = decalW * 0.54;
    const decal = createSilkscreenDecal({
      text: serialText,
      subText: serialSub,
      width: decalW,
      height: decalH,
    });
    decal.rotation.x = -Math.PI / 2;
    decal.position.set(-width * 0.18, thickness * 0.5 + 0.12, length * 0.22);
    group.add(decal);
  }

  return { group, shellMesh, linerMesh };
}

/**
 * Compound Braided Hydraulic Hose Bundle (`braidedHoseBundle`).
 * Generates a high-density routed hydraulic bundle with:
 *   - Diamond-weave braided rubber hoses (`sweptProfileGeometry` + `M.braidedHose`);
 *   - Hex brass crimp ferrules & stepped union collars at both ends of every hose;
 *   - Intermediate anodized retaining clamp blocks with socket fasteners;
 *   - Live `update(newRoutes)` method for real-time deformation across moving joints.
 */
export function braidedHoseBundle({
  routes = [],
  hoseRadius = 3.2,
  ferruleLen = 9.0,
  clampAt = [0.5],
  hoseMat = null,
  brassMat = null,
  clampMat = null,
  boltMat = null,
} = {}) {
  const M = createMaterials();
  const hMat = hoseMat || M.braidedHose;
  const fMat = brassMat || M.brass;
  const cMat = clampMat || M.anodizedRed;
  const bMat = boltMat || M.steel;

  const group = new THREE.Group();
  const hoseEntries = [];

  // Hex crimp ferrule geometry (6-sided hex nut + cylindrical crimp sleeve)
  const hexNut = new THREE.CylinderGeometry(hoseRadius * 1.58, hoseRadius * 1.58, ferruleLen * 0.46, 6);
  hexNut.translate(0, ferruleLen * 0.22, 0);
  const sleeve = new THREE.CylinderGeometry(hoseRadius * 1.32, hoseRadius * 1.38, ferruleLen * 0.54, 18);
  sleeve.translate(0, -ferruleLen * 0.24, 0);
  const ferruleGeo = normalizeGeometryUVs(mergeGeometries([hexNut, sleeve]));

  const upVec = new THREE.Vector3(0, 1, 0);
  const tmpTan = new THREE.Vector3();

  for (let i = 0; i < routes.length; i++) {
    const pts = routes[i].map((p) => (p.isVector3 ? p.clone() : new THREE.Vector3(p[0], p[1], p[2])));
    const r = typeof hoseRadius === 'function' ? hoseRadius(i) : hoseRadius;
    const geo = sweptProfileGeometry({
      points: pts,
      radiusAt: r,
      tubularSeg: 36,
      radialSeg: 14,
      capEnds: true,
    });
    const mesh = new THREE.Mesh(geo, hMat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);

    const ferruleStart = new THREE.Mesh(ferruleGeo, fMat);
    const ferruleEnd = new THREE.Mesh(ferruleGeo, fMat);
    ferruleStart.castShadow = true;
    ferruleEnd.castShadow = true;
    group.add(ferruleStart, ferruleEnd);

    hoseEntries.push({ mesh, geo, r, ferruleStart, ferruleEnd, pts });
  }

  // Intermediate retaining clamp blocks
  const clamps = [];
  if (routes.length >= 2 && clampAt && clampAt.length > 0) {
    const span = Math.max(12, routes.length * hoseRadius * 2.8);
    const clampGeo = blockGeometry({
      w: span + 6,
      h: hoseRadius * 3.1,
      d: hoseRadius * 2.8,
      r: 1.8,
      bevel: 0.6,
    });
    const boltGeo = boltGeometry({ r: hoseRadius * 0.65, h: hoseRadius * 1.1, washer: true });
    for (const uClamp of clampAt) {
      const cGroup = new THREE.Group();
      const cMesh = new THREE.Mesh(clampGeo, cMat);
      cMesh.castShadow = true;
      cGroup.add(cMesh);
      const bL = new THREE.Mesh(boltGeo, bMat);
      const bR = new THREE.Mesh(boltGeo, bMat);
      bL.position.set(-span * 0.42, hoseRadius * 1.6, 0);
      bR.position.set(span * 0.42, hoseRadius * 1.6, 0);
      cGroup.add(bL, bR);
      group.add(cGroup);
      clamps.push({ group: cGroup, u: clamp(uClamp, 0.1, 0.9) });
    }
  }

  function poseEndsAndClamps(currentRoutes) {
    for (let i = 0; i < hoseEntries.length; i++) {
      const entry = hoseEntries[i];
      const pts = (currentRoutes[i] || entry.pts).map((p) => (p.isVector3 ? p : new THREE.Vector3(p[0], p[1], p[2])));
      entry.pts = pts;
      const curve = new THREE.CatmullRomCurve3(pts);

      const p0 = curve.getPointAt(0.02);
      curve.getTangentAt(0.02, tmpTan).normalize();
      entry.ferruleStart.position.copy(p0);
      entry.ferruleStart.quaternion.setFromUnitVectors(upVec, tmpTan);

      const p1 = curve.getPointAt(0.98);
      curve.getTangentAt(0.98, tmpTan).normalize();
      entry.ferruleEnd.position.copy(p1);
      entry.ferruleEnd.quaternion.setFromUnitVectors(upVec, tmpTan.negate());
    }

    if (clamps.length > 0 && hoseEntries.length > 0) {
      for (const cl of clamps) {
        const center = new THREE.Vector3();
        for (const entry of hoseEntries) {
          const curve = new THREE.CatmullRomCurve3(entry.pts);
          center.add(curve.getPointAt(cl.u));
        }
        center.divideScalar(hoseEntries.length);
        const refCurve = new THREE.CatmullRomCurve3(hoseEntries[0].pts);
        refCurve.getTangentAt(cl.u, tmpTan).normalize();
        cl.group.position.copy(center);
        cl.group.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tmpTan);
      }
    }
  }

  poseEndsAndClamps(routes);

  function update(newRoutes = []) {
    for (let i = 0; i < hoseEntries.length; i++) {
      if (!newRoutes[i]) continue;
      updateSweptGeometry(hoseEntries[i].geo, newRoutes[i], hoseEntries[i].r);
    }
    poseEndsAndClamps(newRoutes);
  }

  return { group, hoses: hoseEntries, clamps, update };
}

/**
 * Compound Flanged Bulkhead Ring / Rib Arch (`flangedRingBulkhead`).
 * Replaces raw `TorusGeometry` / `CylinderGeometry` ribs with an engineered I-section bulkhead:
 *   - Outer and inner raised stiffening flanges + recessed structural web;
 *   - Circumferential weight-relief lightening bores (`lighteningHoles`);
 *   - Counterbored bolt bosses + hex fasteners (`boltCount`).
 */
export function flangedRingBulkhead({
  rOuter = 68,
  rInner = 46,
  thickness = 10,
  webThickness = 4.2,
  flangeRim = 3.8,
  lighteningHoles = 8,
  boltCount = 8,
  bevel = 0.8,
  mat = null,
  boltMat = null,
} = {}) {
  const M = createMaterials();
  const ringMat = governIndustrialMaterial(mat || M.alu, 'shell');
  const bMat = boltMat || M.steel;

  const rMid = (rOuter + rInner) * 0.5;
  const radialSpan = rOuter - rInner;
  const holeR = Math.min(radialSpan * 0.24, (rMid * Math.PI) / Math.max(4, lighteningHoles * 2.2));

  const webSh = new THREE.Shape();
  webSh.absarc(0, 0, rOuter, 0, Math.PI * 2, false);
  const innerHole = new THREE.Path();
  innerHole.absarc(0, 0, rInner, 0, Math.PI * 2, true);
  webSh.holes.push(innerHole);
  if (lighteningHoles > 0 && holeR > 1.2) {
    for (let i = 0; i < lighteningHoles; i++) {
      const a = (i * Math.PI * 2) / lighteningHoles;
      const p = new THREE.Path();
      p.absarc(Math.cos(a) * rMid, Math.sin(a) * rMid, holeR, 0, Math.PI * 2, true);
      webSh.holes.push(p);
    }
  }

  const webGeo = new THREE.ExtrudeGeometry(webSh, {
    depth: webThickness,
    bevelEnabled: false,
    curveSegments: 40,
  });
  webGeo.translate(0, 0, -webThickness / 2);

  const rimDepth = Math.max(1, thickness - bevel * 2);
  const makeRingRim = (rO, rI) => {
    const sh = new THREE.Shape();
    sh.absarc(0, 0, rO, 0, Math.PI * 2, false);
    const h = new THREE.Path();
    h.absarc(0, 0, rI, 0, Math.PI * 2, true);
    sh.holes.push(h);
    const g = new THREE.ExtrudeGeometry(sh, {
      depth: rimDepth,
      bevelEnabled: true,
      bevelThickness: bevel,
      bevelSize: bevel,
      bevelSegments: 2,
      curveSegments: 40,
    });
    g.translate(0, 0, -rimDepth / 2);
    return g;
  };
  const outerRimGeo = makeRingRim(rOuter, Math.max(rInner + 1, rOuter - flangeRim));
  const innerRimGeo = makeRingRim(Math.min(rOuter - 1, rInner + flangeRim), rInner);

  const bodyGeo = normalizeGeometryUVs(mergeGeometries([webGeo, outerRimGeo, innerRimGeo]));
  const group = new THREE.Group();
  const bodyMesh = new THREE.Mesh(bodyGeo, ringMat);
  bodyMesh.castShadow = true;
  bodyMesh.receiveShadow = true;
  group.add(bodyMesh);

  if (boltCount > 0) {
    const bGeo = boltGeometry({ r: Math.min(2.6, flangeRim * 0.65), h: 3.6, washer: true });
    bGeo.rotateX(Math.PI / 2);
    for (let i = 0; i < boltCount; i++) {
      const a = ((i + 0.5) * Math.PI * 2) / boltCount;
      const bx = Math.cos(a) * rMid;
      const by = Math.sin(a) * rMid;
      for (const sz of [-1, 1]) {
        const bolt = new THREE.Mesh(bGeo, bMat);
        bolt.position.set(bx, by, sz * (thickness * 0.5 + 0.6));
        if (sz < 0) bolt.rotation.y = Math.PI;
        group.add(bolt);
      }
    }
  }

  return { group, bodyMesh, geometry: bodyGeo };
}

// ============================================================================
// 4. TRUE STENCIL SECTION-CUT MANAGER (AUTOMATIC CROSS-HATCH CAPS)
// ============================================================================

/**
 * Automatic Stencil-Buffer Section Cut Manager (`createSectionCutManager`).
 *
 * Replaces fragile hand-placed `BoxGeometry` caps with exact WebGL Stencil Capping:
 *   1. Every registered shell mesh (`addShell(mesh)`) gets `BackSide` (increment stencil) and
 *      `FrontSide` (decrement stencil) stencil helper children attached directly to `mesh`, so even
 *      rotating, exploding, or multi-DOF tentacle parts carry their stencil volumes automatically.
 *   2. A single 45° CNC cross-hatched `capPlaneMesh` aligned with `plane` draws ONLY where
 *      `stencil != 0` and resets the stencil buffer to 0, sealing cooling fins, rounded corners,
 *      bored holes, and curved manifolds with pixel-perfect accuracy.
 */
export function createSectionCutManager({
  scene,
  plane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0.9),
  capMaterial = null,
  size = 16,
} = {}) {
  const materials = new Set();
  const stencilHelpers = [];

  const backStencilMat = new THREE.MeshBasicMaterial({
    side: THREE.BackSide,
    clippingPlanes: [plane],
    depthTest: false,
    depthWrite: false,
    colorWrite: false,
    stencilWrite: true,
    stencilFunc: THREE.AlwaysStencilFunc,
    stencilFail: THREE.KeepStencilOp,
    stencilZFail: THREE.KeepStencilOp,
    stencilZPass: THREE.IncrementWrapStencilOp,
  });

  const frontStencilMat = new THREE.MeshBasicMaterial({
    side: THREE.FrontSide,
    clippingPlanes: [plane],
    depthTest: false,
    depthWrite: false,
    colorWrite: false,
    stencilWrite: true,
    stencilFunc: THREE.AlwaysStencilFunc,
    stencilFail: THREE.KeepStencilOp,
    stencilZFail: THREE.KeepStencilOp,
    stencilZPass: THREE.DecrementWrapStencilOp,
  });

  const baseCapMat = capMaterial || createMaterials().sectionCap;
  const stencilCapMat = baseCapMat.clone();
  stencilCapMat.stencilWrite = true;
  stencilCapMat.stencilRef = 0;
  stencilCapMat.stencilFunc = THREE.NotEqualStencilFunc;
  stencilCapMat.stencilFail = THREE.ReplaceStencilOp;
  stencilCapMat.stencilZFail = THREE.ReplaceStencilOp;
  stencilCapMat.stencilZPass = THREE.ReplaceStencilOp;
  stencilCapMat.polygonOffset = true;
  stencilCapMat.polygonOffsetFactor = -1;
  stencilCapMat.polygonOffsetUnits = -1;

  const capPlaneMesh = new THREE.Mesh(new THREE.PlaneGeometry(size, size), stencilCapMat);
  capPlaneMesh.renderOrder = 2;
  capPlaneMesh.castShadow = false;
  capPlaneMesh.receiveShadow = false;
  capPlaneMesh.visible = false;
  capPlaneMesh.userData.isSectionCap = true;
  capPlaneMesh.userData.skipContactShadow = true;
  if (scene) scene.add(capPlaneMesh);

  function addShell(meshOrGroup) {
    meshOrGroup.traverse((m) => {
      if (!m.isMesh || m.userData.isStencilHelper) return;
      if (m.material) {
        const list = Array.isArray(m.material) ? m.material : [m.material];
        for (const mat of list) materials.add(mat);
      }
      const bMesh = new THREE.Mesh(m.geometry, backStencilMat);
      bMesh.renderOrder = 1;
      bMesh.castShadow = false;
      bMesh.receiveShadow = false;
      bMesh.visible = false;
      bMesh.userData.isStencilHelper = true;
      bMesh.userData.skipContactShadow = true;

      const fMesh = new THREE.Mesh(m.geometry, frontStencilMat);
      fMesh.renderOrder = 1;
      fMesh.castShadow = false;
      fMesh.receiveShadow = false;
      fMesh.visible = false;
      fMesh.userData.isStencilHelper = true;
      fMesh.userData.skipContactShadow = true;

      m.add(bMesh, fMesh);
      stencilHelpers.push(bMesh, fMesh);
    });
    return meshOrGroup;
  }

  let activeState = null;
  const tmpPt = new THREE.Vector3();
  const tmpLook = new THREE.Vector3();

  function update({ enabled = false, constant = plane.constant, normal = null } = {}) {
    if (normal) plane.normal.copy(normal).normalize();
    plane.constant = constant;

    if (enabled !== activeState) {
      activeState = enabled;
      for (const mat of materials) {
        mat.clippingPlanes = enabled ? [plane] : null;
        mat.side = enabled ? THREE.DoubleSide : THREE.FrontSide;
        mat.needsUpdate = true;
      }
      for (const h of stencilHelpers) h.visible = enabled;
      capPlaneMesh.visible = enabled;
      if (scene) {
        scene.userData.activeClippingPlanes = enabled ? [plane] : null;
      }
    }

    if (enabled) {
      plane.coplanarPoint(tmpPt);
      capPlaneMesh.position.copy(tmpPt);
      tmpLook.copy(tmpPt).sub(plane.normal);
      capPlaneMesh.lookAt(tmpLook);
    }
  }

  return { plane, capPlaneMesh, materials, addShell, update };
}

// ============================================================================
// 5. MULTI-DOF KINEMATICS & SECONDARY LINKAGE SOLVERS
// ============================================================================

/**
 * 3D FABRIK Inverse Kinematics Solver (`solveFabrikChain`) with joint cone limits.
 * Mutates and returns `joints` (array of `THREE.Vector3` in world/root space).
 */
export function solveFabrikChain({
  joints,
  lengths,
  target,
  basePos = null,
  maxIter = 8,
  maxConeAngle = Math.PI * 0.42,
}) {
  const n = joints.length;
  if (n < 2) return joints;
  const root = basePos ? new THREE.Vector3(...(basePos.isVector3 ? [basePos.x, basePos.y, basePos.z] : basePos)) : joints[0].clone();
  const goal = target.isVector3 ? target : new THREE.Vector3(target[0], target[1], target[2]);
  const dir = new THREE.Vector3();
  const prevDir = new THREE.Vector3();
  const axis = new THREE.Vector3();

  for (let iter = 0; iter < maxIter; iter++) {
    // Backward reaching: pull tip to target
    joints[n - 1].copy(goal);
    for (let i = n - 2; i >= 0; i--) {
      dir.subVectors(joints[i], joints[i + 1]).normalize();
      joints[i].copy(joints[i + 1]).addScaledVector(dir, lengths[i]);
    }
    // Forward reaching: anchor root and enforce cone angle limits
    joints[0].copy(root);
    for (let i = 0; i < n - 1; i++) {
      dir.subVectors(joints[i + 1], joints[i]).normalize();
      if (i > 0 && maxConeAngle < Math.PI) {
        prevDir.subVectors(joints[i], joints[i - 1]).normalize();
        const dot = clamp(prevDir.dot(dir), -1, 1);
        const ang = Math.acos(dot);
        if (ang > maxConeAngle) {
          axis.crossVectors(prevDir, dir);
          if (axis.lengthSq() > 1e-6) {
            axis.normalize();
            dir.copy(prevDir).applyAxisAngle(axis, maxConeAngle);
          }
        }
      }
      joints[i + 1].copy(joints[i]).addScaledVector(dir, lengths[i]);
    }
  }
  return joints;
}

/**
 * Multi-DOF Traveling-Wave + Whip-Damped + IK-Blended Kinematic Chain (`solveKinematicChain`).
 * Designed for bionic octopus tentacles, hyper-redundant continuum arms, and articulated spines.
 */
export function solveKinematicChain({
  count = 10,
  segLengths = 18,
  basePos = [0, 0, 0],
  baseDir = [0, 1, 0],
  upDir = [0, 0, 1],
  t = 0,
  freq = 2.2,
  waveNumber = 2.6,
  ampYaw = 0.28,
  ampPitch = 0.18,
  whip = 1.45,
  curl = 0.0,
  target = null,
  ikMix = 0.0,
} = {}) {
  const lengths = Array.from({ length: count }, (_, i) =>
    typeof segLengths === 'function' ? segLengths(i) : Array.isArray(segLengths) ? segLengths[i] : segLengths,
  );
  const positions = [new THREE.Vector3(...(basePos.isVector3 ? [basePos.x, basePos.y, basePos.z] : basePos))];
  const tangents = [];
  const quaternions = [];

  const T = new THREE.Vector3(...baseDir).normalize();
  const U = new THREE.Vector3(...upDir).normalize();
  const R = new THREE.Vector3().crossVectors(T, U).normalize();
  U.crossVectors(R, T).normalize();

  const qSeg = new THREE.Quaternion();
  const basisMat = new THREE.Matrix4();

  for (let i = 0; i < count; i++) {
    const u = i / Math.max(1, count - 1);
    const env = Math.pow(u + 0.15, whip);
    const phase = t * freq - u * waveNumber * Math.PI * 2;
    const dYaw = Math.sin(phase) * ampYaw * env;
    const dPitch = Math.cos(phase * 0.85 + 0.6) * ampPitch * env + curl / count;

    qSeg.setFromAxisAngle(U, dYaw);
    T.applyQuaternion(qSeg).normalize();
    R.crossVectors(T, U).normalize();

    qSeg.setFromAxisAngle(R, dPitch);
    T.applyQuaternion(qSeg).normalize();
    U.crossVectors(R, T).normalize();

    positions.push(positions[i].clone().addScaledVector(T, lengths[i]));
  }

  if (target && ikMix > 1e-3) {
    const ikPts = positions.map((p) => p.clone());
    solveFabrikChain({ joints: ikPts, lengths, target, basePos: positions[0] });
    for (let i = 1; i <= count; i++) {
      positions[i].lerp(ikPts[i], clamp(ikMix, 0, 1));
    }
  }

  const prevT = new THREE.Vector3(...baseDir).normalize();
  for (let i = 0; i < count; i++) {
    const segT = new THREE.Vector3().subVectors(positions[i + 1], positions[i]).normalize();
    tangents.push(segT);
    const segR = new THREE.Vector3().crossVectors(segT, U);
    if (segR.lengthSq() < 1e-5) segR.set(1, 0, 0);
    else segR.normalize();
    const segU = new THREE.Vector3().crossVectors(segR, segT).normalize();
    basisMat.makeBasis(segR, segT, segU);
    quaternions.push(new THREE.Quaternion().setFromRotationMatrix(basisMat));
    prevT.copy(segT);
  }

  return { positions, tangents, quaternions, lengths };
}

/** Exact closed-form 2-link planar IK solver (`solveTwoLinkIK2D`). */
export function solveTwoLinkIK2D(dx, dy, L1, L2, elbowSign = 1) {
  const d = clamp(Math.hypot(dx, dy), Math.abs(L1 - L2) + 1e-4, L1 + L2 - 1e-4);
  const cosKnee = clamp((dx * dx + dy * dy - L1 * L1 - L2 * L2) / (2 * L1 * L2), -1, 1);
  const q2 = elbowSign * Math.acos(cosKnee);
  const q1 = Math.atan2(dy, dx) - Math.atan2(L2 * Math.sin(q2), L1 + L2 * Math.cos(q2));
  return {
    q1,
    q2,
    elbow: [Math.cos(q1) * L1, Math.sin(q1) * L1],
    tip: [Math.cos(q1) * L1 + Math.cos(q1 + q2) * L2, Math.sin(q1) * L1 + Math.sin(q1 + q2) * L2],
  };
}

/**
 * Align a 2-part telescopic hydraulic actuator, shock absorber or pushrod between `pointA` and `pointB`.
 */
export function poseActuator(cylinderObj, plungerObj, pointA, pointB) {
  const a = pointA.isVector3 ? pointA : new THREE.Vector3(...pointA);
  const b = pointB.isVector3 ? pointB : new THREE.Vector3(...pointB);
  const dir = new THREE.Vector3().subVectors(b, a);
  const dist = dir.length();
  if (dist < 1e-4) return dist;
  dir.divideScalar(dist);
  const up = new THREE.Vector3(0, 1, 0);
  if (cylinderObj) {
    cylinderObj.position.copy(a);
    cylinderObj.quaternion.setFromUnitVectors(up, dir);
  }
  if (plungerObj) {
    plungerObj.position.copy(b);
    plungerObj.quaternion.setFromUnitVectors(up, dir.clone().negate());
  }
  return dist;
}

/**
 * Compress/extend a coil spring or bellows along Y with volume-conserving radial bulge (`scaleXZ`).
 */
export function poseCompressedSpring(springObj, restLen, currentLen) {
  const sy = clamp(currentLen / Math.max(1e-3, restLen), 0.15, 2.5);
  const sxz = 1 + (1 - sy) * 0.11;
  springObj.scale.set(sxz, sy, sxz);
}

/**
 * Staged-explode easing (`layerEase`): layers leave in order inside `[from, to]`.
 */
export function layerEase(ex, [from, to], distance) {
  return smootherstep(from, to, clamp(ex, 0, 1)) * distance;
}

// ============================================================================
// 5B. HIERARCHICAL KINEMATIC RIGGING & STATE-MACHINE SUBSYSTEM TEARDOWN
// ============================================================================

/**
 * Hierarchical Ball-and-Socket Articulated Chain (`createArticulatedChain`).
 * Enforces true parent-child skeletal nesting (`joint_0 -> seg_0 -> joint_1 -> ...`) with hard
 * angular cone limits (`maxConeAngle`) and local-axis teardown separation (`explodeStep`),
 * eliminating the world-space sine-wave interpenetration bug (`Pelagos OC-8` arm standard).
 */
export function createArticulatedChain({
  count = 6,
  segLength = 26,
  radiusAt = (i) => 16 - i * 1.4,
  maxConeAngle = 0.42,
  serialPrefix = '',
  shellMat = null,
  jointMat = null,
  linerMat = null,
  accentMat = null,
} = {}) {
  const M = createMaterials();
  const sMat = governIndustrialMaterial(shellMat || M.white, 'shell');
  const jMat = governIndustrialMaterial(jointMat || M.titanium, 'shell');
  const lMat = governIndustrialMaterial(linerMat || M.liner, 'shell');
  const aMat = accentMat || M.anodizedRed;

  const root = new THREE.Group();
  const segments = [];
  let parentNode = root;

  for (let i = 0; i < count; i++) {
    const len = typeof segLength === 'function' ? segLength(i) : Array.isArray(segLength) ? segLength[i] : segLength;
    const r = typeof radiusAt === 'function' ? radiusAt(i) : radiusAt;
    const rNext = typeof radiusAt === 'function' ? radiusAt(i + 1) : r * 0.88;

    const jointPivot = new THREE.Group();
    if (i > 0) {
      const prevLen = typeof segLength === 'function' ? segLength(i - 1) : Array.isArray(segLength) ? segLength[i - 1] : segLength;
      jointPivot.position.y = prevLen;
    }
    parentNode.add(jointPivot);

    // Spherical ball-and-socket collar at the base of the segment
    const rBall = Math.max(3.5, r * 0.48);
    const { ballGeo, socketGeo } = ballJointGeometry({
      rBall,
      rSocket: rBall * 1.24,
      neckR: rBall * 0.48,
      neckLen: len * 0.28,
      seg: 24,
    });
    const ballMesh = new THREE.Mesh(ballGeo, M.chrome);
    ballMesh.castShadow = true;
    parentNode.add(ballMesh);
    if (i > 0) {
      const prevLen = typeof segLength === 'function' ? segLength(i - 1) : Array.isArray(segLength) ? segLength[i - 1] : segLength;
      ballMesh.position.y = prevLen;
    }

    const segBody = new THREE.Group();
    jointPivot.add(segBody);

    const socketMesh = new THREE.Mesh(socketGeo, jMat);
    socketMesh.castShadow = true;
    segBody.add(socketMesh);

    // Tapered machined outer collar + dark inner liner sleeve + anodized retention ring
    const collarLen = Math.max(4, len * 0.68);
    const linerGeo = normalizeGeometryUVs(new THREE.CylinderGeometry(rNext * 0.82, r * 0.82, collarLen * 0.94, 24));
    const linerMesh = new THREE.Mesh(linerGeo, lMat);
    linerMesh.position.y = len * 0.52;
    segBody.add(linerMesh);

    const outerGeo = flangedRingBulkhead({
      rOuter: r,
      rInner: r * 0.66,
      thickness: collarLen * 0.56,
      webThickness: collarLen * 0.24,
      flangeRim: Math.max(1.8, r * 0.14),
      lighteningHoles: 6,
      boltCount: 6,
      mat: sMat,
      boltMat: M.steel,
    }).geometry;
    outerGeo.rotateX(Math.PI / 2);
    const outerMesh = new THREE.Mesh(outerGeo, sMat);
    outerMesh.position.y = len * 0.52;
    outerMesh.castShadow = true;
    outerMesh.receiveShadow = true;
    segBody.add(outerMesh);

    if (i % 2 === 0) {
      const latchGeo = blockGeometry({ w: Math.max(2.5, r * 0.24), h: collarLen * 0.42, d: 3.2, r: 0.8, bevel: 0.3 });
      const latch = new THREE.Mesh(latchGeo, aMat);
      latch.position.set(r * 0.96, len * 0.52, 0);
      segBody.add(latch);
    }

    if (serialPrefix && i < 8) {
      const decal = createSilkscreenDecal({
        text: `${serialPrefix}${String(i + 1).padStart(2, '0')}`,
        subText: 'JNT',
        width: Math.max(6, r * 0.72),
        height: Math.max(3.5, r * 0.40),
      });
      decal.position.set(0, len * 0.52, r + 0.3);
      segBody.add(decal);
    }

    segments.push({ index: i, jointPivot, segBody, len, r });
    parentNode = segBody;
  }

  function pose({
    angles = null,
    t = 0,
    freq = 2.0,
    waveNumber = 1.8,
    ampPitch = 0.18,
    ampYaw = 0.22,
    curl = 0.0,
    explode = 0.0,
    explodeStep = 14,
  } = {}) {
    const ex = clamp(explode, 0, 1);
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const u = i / Math.max(1, segments.length - 1);
      let yaw = 0;
      let pitch = 0;
      let roll = 0;
      if (Array.isArray(angles) && angles[i]) {
        yaw = angles[i][0] || 0;
        pitch = angles[i][1] || 0;
        roll = angles[i][2] || 0;
      } else {
        const env = 0.35 + 0.65 * u;
        const ph = t * freq - u * waveNumber * Math.PI * 2;
        yaw = Math.sin(ph) * ampYaw * env;
        pitch = Math.cos(ph * 0.85 + 0.5) * ampPitch * env + curl / segments.length;
      }
      // Enforce hard mechanical cone limits so adjacent collars never interpenetrate
      seg.jointPivot.rotation.set(
        clamp(pitch, -maxConeAngle, maxConeAngle),
        clamp(roll, -maxConeAngle * 0.5, maxConeAngle * 0.5),
        clamp(yaw, -maxConeAngle, maxConeAngle),
      );
      // Axial teardown separation along local segment rail (`ARM APART` mode)
      seg.segBody.position.set(0, ex * explodeStep * (1 + i * 0.15), 0);
    }
  }

  pose({ t: 0, explode: 0 });
  return { root, segments, pose };
}

/**
 * State-Machine Subsystem Rig & Ghost Solo Isolator (`createSubsystemRig`).
 * Implements `teardown`'s two core mechanical choreography rules:
 *   1. Collision-free local-rail / local-hinge subsystem opening (`MANTLE OPEN`, `OPTICS OPEN`, `ARM APART`);
 *   2. Subsystem `solo` isolation (`fade` smoothly transitions non-soloed subsystems to translucent ghost meshes).
 */
export function createSubsystemRig({ ghostOpacity = 0.16 } = {}) {
  const subsystems = new Map();
  const rotQuat = new THREE.Quaternion();
  const rotAxisVec = new THREE.Vector3();

  function register(
    id,
    object3d,
    {
      explodeVec = [0, 0, 0],
      rotAxis = [1, 0, 0],
      rotAngle = 0,
      window = [0, 1],
    } = {},
  ) {
    if (!object3d) return null;
    const basePos = object3d.position.clone();
    const baseQuat = object3d.quaternion.clone();
    const meshMaterials = [];

    object3d.traverse((m) => {
      if (!m.isMesh || m.userData?.isStencilHelper || m.userData?.isSectionCap || m.userData?.isHudOverlay) return;
      if (!m.material || Array.isArray(m.material)) return;
      const origMat = m.material;
      const ghostMat = origMat.clone();
      ghostMat.transparent = true;
      ghostMat.depthWrite = false;
      ghostMat.opacity = ghostOpacity;
      meshMaterials.push({ mesh: m, origMat, ghostMat });
    });

    const entry = {
      id,
      object3d,
      basePos,
      baseQuat,
      explodeVec: new THREE.Vector3(...explodeVec),
      rotAxis: new THREE.Vector3(...rotAxis).normalize(),
      rotAngle,
      window,
      meshMaterials,
      currentWeight: 0,
    };
    subsystems.set(id, entry);
    return entry;
  }

  function update({ states = {}, explode = 0, solo = null, soloFade = 0 } = {}) {
    const globalEx = clamp(explode, 0, 1);
    const fade = clamp(soloFade, 0, 1);

    for (const [id, sub] of subsystems.entries()) {
      const stateW = states[id] !== undefined ? clamp(states[id], 0, 1) : 0;
      const globalW = globalEx > 0 ? smootherstep(sub.window[0], sub.window[1], globalEx) : 0;
      const w = clamp(Math.max(stateW, globalW), 0, 1);
      sub.currentWeight = w;

      // Rigid-body translation along local rail vector
      sub.object3d.position.copy(sub.basePos).addScaledVector(sub.explodeVec, w);

      // Optional hinge rotation around local axis
      if (Math.abs(sub.rotAngle) > 1e-4) {
        rotAxisVec.copy(sub.rotAxis);
        rotQuat.setFromAxisAngle(rotAxisVec, sub.rotAngle * w);
        sub.object3d.quaternion.copy(sub.baseQuat).multiply(rotQuat);
      } else {
        sub.object3d.quaternion.copy(sub.baseQuat);
      }

      // Solo isolation ghosting (`teardown` `engine.js` lines 588-619)
      const isGhost = Boolean(solo && solo !== id && fade > 0.02);
      for (const mm of sub.meshMaterials) {
        if (isGhost) {
          mm.ghostMat.opacity = lerp(1.0, ghostOpacity, fade);
          mm.mesh.material = mm.ghostMat;
        } else {
          mm.mesh.material = mm.origMat;
        }
      }
    }
  }

  return { subsystems, register, update };
}

/**
 * State-Machine Teardown Script Controller (`createTeardownController`).
 * Drives named subsystem states (`OPTICS OPEN` -> `MANTLE OPEN` -> `ARM APART` -> `TEARDOWN`),
 * solo isolation fades, 3D leader callouts, and an automated operator cursor with click ripples
 * synchronized with `createGaugeHud`.
 */
export function createTeardownController({ stages = [], subRig = null } = {}) {
  const pillLabels = stages.map((s) => s.label || s.id || 'STAGE');

  function evaluate({ sceneIndex = 0, localT = 0, sceneDur = 3.5 } = {}) {
    const idx = clamp(sceneIndex, 0, Math.max(0, stages.length - 1));
    const cur = stages[idx] || {};
    const prev = idx > 0 ? stages[idx - 1] : cur;

    const transDur = cur.transitionDur ?? 1.1;
    const u = smootherstep(0.08, Math.max(0.25, transDur), localT);

    // Blend per-subsystem weights between previous stage and current stage
    const allKeys = new Set([
      ...Object.keys(prev.states || {}),
      ...Object.keys(cur.states || {}),
    ]);
    const states = {};
    for (const k of allKeys) {
      states[k] = lerp(prev.states?.[k] ?? 0, cur.states?.[k] ?? 0, u);
    }

    const explode = lerp(prev.explode ?? 0, cur.explode ?? 0, u);
    const solo = cur.solo || null;
    const soloFade = solo ? smootherstep(0.15, 0.85, localT) : 0;

    if (subRig) {
      subRig.update({ states, explode, solo, soloFade });
    }

    // Operator cursor choreography: glides from previous pill to current pill & clicks at t ≈ 0.28s
    const moveK = smootherstep(0.0, 0.28, localT);
    const clickTime = localT - 0.26;
    const press = clickTime >= 0 && clickTime < 0.22 ? Math.sin((clickTime / 0.22) * Math.PI) : 0;
    const ring = clickTime >= 0 && clickTime < 0.58 ? clamp(clickTime / 0.58, 0, 1) : 0;
    const cursorFadeOut = 1 - smootherstep(1.45, Math.min(sceneDur - 0.1, 2.2), localT);

    const cursor = {
      fromIndex: idx > 0 ? idx - 1 : idx,
      toIndex: idx,
      moveK,
      press,
      ring,
      opacity: clamp(cursorFadeOut, 0, 1),
    };

    const calloutAlpha = smootherstep(0.25, 0.75, localT) * (1 - smootherstep(sceneDur - 0.45, sceneDur, localT));
    const callouts = (cur.callouts || []).map((c) => ({
      ...c,
      opacity: (c.opacity ?? 1) * calloutAlpha,
    }));

    return {
      stage: cur,
      stageIndex: idx,
      pillLabels,
      states,
      explode,
      solo,
      soloFade,
      cursor,
      callouts,
    };
  }

  return { stages, pillLabels, evaluate };
}

// ============================================================================
// 6. PHYSICAL FIELD SHADERS, TORQUE ARCS & 3D METROLOGY CALLOUTS
// ============================================================================

const PRESSURE_VS = `
#include <clipping_planes_pars_vertex>
varying vec2 vUv;
varying vec3 vNormalView;
varying vec3 vViewPos;
void main() {
  #include <begin_vertex>
  vUv = uv;
  vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.0);
  vViewPos = -mvPosition.xyz;
  vNormalView = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * mvPosition;
  #include <clipping_planes_vertex>
}
`;

const PRESSURE_FS = `
#include <clipping_planes_pars_fragment>
uniform vec3 uBaseColor;
uniform vec3 uHotColor;
uniform float uPressure;
uniform float uBurn;
uniform float uTime;
uniform float uOpacity;
varying vec2 vUv;
varying vec3 vNormalView;
varying vec3 vViewPos;

void main() {
  #include <clipping_planes_fragment>
  vec3 N = normalize(vNormalView);
  vec3 V = normalize(vViewPos);
  float fresnel = pow(1.0 - abs(dot(N, V)), 1.35);
  float core = 0.38 + 0.62 * (1.0 - fresnel * 0.65);

  // Stratified axial pressure waves + crown combustion front near vUv.y = 1.0
  float crownHeat = smoothstep(0.32, 0.98, vUv.y) * (0.45 + 0.55 * uBurn);
  float wave = 0.5 + 0.5 * sin((vUv.y * 16.0 - uTime * 5.0) + uPressure * 4.0);
  float band = smoothstep(0.25, 0.85, wave) * (0.28 + 0.52 * uPressure);

  vec3 col = mix(uBaseColor, uHotColor, clamp(crownHeat + band * 0.45 * uBurn, 0.0, 1.0));
  float alpha = uOpacity * core * (0.55 + 0.45 * crownHeat + 0.35 * band);
  gl_FragColor = vec4(col, clamp(alpha, 0.0, 0.78));
}
`;

/**
 * Thermodynamic / Fluid Pressure Field Shader Material (`createPressureFieldMaterial`).
 * Renders stratified axial isobar waves and crown thermal gradients inside an actuator or bore,
 * while natively respecting `clippingPlanes` during section cuts.
 */
export function createPressureFieldMaterial({ clipPlane = null } = {}) {
  return new THREE.ShaderMaterial({
    vertexShader: PRESSURE_VS,
    fragmentShader: PRESSURE_FS,
    uniforms: {
      uBaseColor: { value: new THREE.Color('#6E9EC2') },
      uHotColor: { value: new THREE.Color(CAL_PALETTE.accent) },
      uPressure: { value: 0.4 },
      uBurn: { value: 0.0 },
      uTime: { value: 0.0 },
      uOpacity: { value: 0.42 },
    },
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    clipping: true,
    clippingPlanes: clipPlane ? [clipPlane] : null,
  });
}

const GHOST_SHELL_VS = `
#include <clipping_planes_pars_vertex>
varying vec3 vNormalView;
varying vec3 vViewPos;
void main() {
  #include <begin_vertex>
  vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.0);
  vViewPos = -mvPosition.xyz;
  vNormalView = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * mvPosition;
  #include <clipping_planes_vertex>
}
`;

const GHOST_SHELL_FS = `
#include <clipping_planes_pars_fragment>
uniform vec3 uColor;
uniform vec3 uRimColor;
uniform float uOpacity;
uniform float uPower;
varying vec3 vNormalView;
varying vec3 vViewPos;
void main() {
  #include <clipping_planes_fragment>
  vec3 N = normalize(vNormalView);
  vec3 V = normalize(vViewPos);
  float ndv = abs(dot(N, V));
  float rim = pow(clamp(1.0 - ndv, 0.0, 1.0), uPower);
  vec3 col = mix(uColor, uRimColor, rim * 0.72);
  float alpha = clamp(uOpacity * (0.14 + 0.86 * rim), 0.0, 0.92);
  gl_FragColor = vec4(col, alpha);
}
`;

/**
 * Fresnel X-Ray / Ghost Shell Material (`createGhostShellMaterial`).
 * Renders outer hull/fuselage/carapace plates as a silhouette-preserving translucent X-ray veil
 * (`alpha = uOpacity * (0.14 + 0.86 * pow(1 - |N·V|, uPower))`) so internal mechanisms read
 * clearly through the outer envelope while maintaining crisp contour edges.
 */
export function createGhostShellMaterial({
  color = '#8CA0B5',
  rimColor = '#DCE6F0',
  opacity = 0.28,
  power = 2.4,
  clipPlane = null,
} = {}) {
  return new THREE.ShaderMaterial({
    vertexShader: GHOST_SHELL_VS,
    fragmentShader: GHOST_SHELL_FS,
    uniforms: {
      uColor: { value: new THREE.Color(color) },
      uRimColor: { value: new THREE.Color(rimColor) },
      uOpacity: { value: opacity },
      uPower: { value: power },
    },
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    clipping: true,
    clippingPlanes: clipPlane ? [clipPlane] : null,
  });
}

/**
 * Sleek 3D Torque / Force Flow Ribbon (`createTorqueArc`) with directional chevron tip.
 * Replaces toy-like cone arrows with an instrument-grade concentric vector arc.
 */
export function createTorqueArc({
  radius = 42,
  width = 5.5,
  thick = 1.6,
  spanDeg = 96,
  color = CAL_PALETTE.accent,
} = {}) {
  const group = new THREE.Group();
  const span = (spanDeg * Math.PI) / 180;
  const segs = 32;
  const arcPts = [];
  for (let i = 0; i <= segs; i++) {
    const a = -span / 2 + (i / segs) * span * 0.82;
    arcPts.push(new THREE.Vector3(Math.cos(a) * radius, Math.sin(a) * radius, 0));
  }
  const mat = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.9,
    side: THREE.DoubleSide,
    toneMapped: false,
  });
  const bodyGeo = sweptProfileGeometry({
    points: arcPts,
    radiusAt: width * 0.38,
    scaleZAt: thick / Math.max(1, width * 0.76),
    tubularSeg: segs,
    radialSeg: 12,
  });
  const body = new THREE.Mesh(bodyGeo, mat);
  body.castShadow = false;
  body.userData.skipContactShadow = true;
  group.add(body);

  // Precision arrowhead at the leading end of the arc
  const aTip = span / 2;
  const aBase = -span / 2 + span * 0.80;
  const head = new THREE.Mesh(new THREE.ConeGeometry(width * 0.9, width * 2.1, 14), mat);
  head.position.set(Math.cos(aBase) * radius, Math.sin(aBase) * radius, 0);
  const tangent = new THREE.Vector3(-Math.sin(aBase), Math.cos(aBase), 0).normalize();
  head.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
  head.castShadow = false;
  head.userData.skipContactShadow = true;
  void aTip;
  group.add(head);

  return {
    group,
    material: mat,
    setDirection(ccw = true) {
      group.scale.y = ccw ? 1 : -1;
    },
  };
}

/**
 * 3D Engineering Dimension & Tolerance Callout (`createDimensionCallout`).
 * Draws extension witness lines, opposing precision tick arrows, and a high-DPI `JetBrains Mono`
 * dimension plaque in 3D space (e.g. `Ø84.00 ±0.02`, `STROKE 86.0 mm`) that can track moving
 * or exploding parts in real time via `update({ y0, y1, text, opacity })`.
 */
export function createDimensionCallout({
  text = 'Ø84.00 ±0.02',
  label = 'BORE',
  x = 92,
  y0 = 32,
  y1 = 212,
  witnessX = 72,
  accent = false,
} = {}) {
  const group = new THREE.Group();
  group.userData.skipContactShadow = true;

  const lineColor = accent ? CAL_PALETTE.accent : '#2A3038';
  const lineMat = new THREE.MeshBasicMaterial({
    color: lineColor,
    transparent: true,
    opacity: 0.88,
    toneMapped: false,
  });

  const stem = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1, 1.1), lineMat);
  const ext0 = new THREE.Mesh(new THREE.BoxGeometry(1, 1.0, 1.0), lineMat);
  const ext1 = new THREE.Mesh(new THREE.BoxGeometry(1, 1.0, 1.0), lineMat);
  const tip0 = new THREE.Mesh(new THREE.ConeGeometry(2.4, 6.5, 10), lineMat);
  const tip1 = new THREE.Mesh(new THREE.ConeGeometry(2.4, 6.5, 10), lineMat);
  tip0.rotation.z = Math.PI;
  group.add(stem, ext0, ext1, tip0, tip1);

  // High-DPI canvas badge for the dimension value
  const bCanvas = document.createElement('canvas');
  bCanvas.width = 320;
  bCanvas.height = 88;
  const bCtx = bCanvas.getContext('2d');
  const bTex = new THREE.CanvasTexture(bCanvas);
  bTex.encoding = THREE.sRGBEncoding;
  bTex.minFilter = THREE.LinearFilter;
  const badgeMat = new THREE.MeshBasicMaterial({
    map: bTex,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    toneMapped: false,
  });
  const badge = new THREE.Mesh(new THREE.PlaneGeometry(78, 21.5), badgeMat);
  group.add(badge);

  let lastText = '';
  let lastLabel = '';

  function drawBadge(valText, subLabel) {
    if (valText === lastText && subLabel === lastLabel) return;
    lastText = valText;
    lastLabel = subLabel;
    bCtx.clearRect(0, 0, 320, 88);
    bCtx.fillStyle = 'rgba(250, 251, 252, 0.94)';
    bCtx.fillRect(2, 2, 316, 84);
    bCtx.strokeStyle = accent ? CAL_PALETTE.accent : '#8A929C';
    bCtx.lineWidth = 3;
    bCtx.strokeRect(2, 2, 316, 84);
    bCtx.fillStyle = accent ? CAL_PALETTE.accent : '#15181C';
    bCtx.fillRect(2, 2, 8, 84);

    bCtx.font = '700 18px "JetBrains Mono", monospace';
    bCtx.fillStyle = '#68707A';
    bCtx.fillText(subLabel.toUpperCase(), 22, 29);

    bCtx.font = '800 30px "JetBrains Mono", monospace';
    bCtx.fillStyle = '#15181C';
    bCtx.fillText(valText, 22, 68);
    bTex.needsUpdate = true;
  }

  function update(opts = {}) {
    const ya = opts.y0 ?? y0;
    const yb = opts.y1 ?? y1;
    const cx = opts.x ?? x;
    const wx = opts.witnessX ?? witnessX;
    const op = opts.opacity ?? 1;
    group.visible = op > 0.02;
    if (!group.visible) return;

    lineMat.opacity = 0.86 * op;
    badgeMat.opacity = op;
    drawBadge(opts.text ?? text, opts.label ?? label);

    const span = Math.max(8, Math.abs(yb - ya));
    const midY = (ya + yb) / 2;
    stem.position.set(cx, midY, 0);
    stem.scale.y = span;

    const extLen = Math.abs(cx - wx) + 6;
    const extMid = (wx + cx + Math.sign(cx - wx) * 3) / 2;
    ext0.position.set(extMid, ya, 0);
    ext0.scale.x = extLen;
    ext1.position.set(extMid, yb, 0);
    ext1.scale.x = extLen;

    tip0.position.set(cx, ya + 3.2, 0);
    tip1.position.set(cx, yb - 3.2, 0);
    badge.position.set(cx + Math.sign(cx || 1) * 46, midY, 2);
  }

  update({ y0, y1, text, label, opacity: 1 });
  return { group, update };
}

/** Interpolate two director framing boxes (`{ center, size }`). */
export function lerpFramingBox(boxA, boxB, u) {
  const k = clamp(u, 0, 1);
  return {
    center: boxA.center.map((v, i) => lerp(v, boxB.center[i], k)),
    size: boxA.size.map((v, i) => lerp(v, boxB.size[i], k)),
  };
}

/** Blend a sparse radial outer bounding box with a dense core bounding box by `coreWeight`. */
export function weightedCoreBox(coreBox, fullBox, coreWeight = 0.72) {
  return lerpFramingBox(fullBox, coreBox, clamp(coreWeight, 0, 1));
}

// ============================================================================
// 7. STUDIO + ENGRAVED BENCH + INSTRUMENT HUD
// ============================================================================

/** Fine calibration grid engraved into the bench top: 25 mm fines, 100 mm majors, corner fiducials. */
function createBenchTexture() {
  const size = 512;
  const c = document.createElement('canvas');
  c.width = size;
  c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = '#EAECEF';
  g.fillRect(0, 0, size, size);
  g.strokeStyle = '#A8AEB5';
  g.lineWidth = 2.2;
  for (let i = 1; i < 20; i++) {
    const p = Math.round((i * size) / 20) + 0.5;
    g.globalAlpha = i % 4 === 0 ? 0.95 : 0.6;
    g.beginPath();
    g.moveTo(p, 0);
    g.lineTo(p, size);
    g.moveTo(0, p);
    g.lineTo(size, p);
    g.stroke();
  }
  g.globalAlpha = 0.85;
  g.strokeStyle = '#C2C6CB';
  g.lineWidth = 2;
  g.strokeRect(1, 1, size - 2, size - 2);
  g.globalAlpha = 1;
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(6, 6);
  tex.anisotropy = 4;
  return tex;
}

/**
 * `style.ref` = the product's parsed ref.json (injected by gallery/player.html next to a `?world=` file). When it declares a
 * palette, `lookFromRefPalette` sits between the style defaults and `style.look` (product overrides still win) and
 * `createMaterials()` tints the shell / mechanism / accent / warm-metal families. No palette -> nothing derived.
 * Returns `refPalette` (normalised, or null) for worlds that build their own materials.
 */
export function createCalLabStudio({ width, height, scenes = [], style = {}, maxDist = null }) {
  ACTIVE_REF_PALETTE = normalizeRefPalette(style.ref);
  const refLook = lookFromRefPalette(style.ref);
  const studio = createStudio3D(THREE, {
    width,
    height,
    baseFov: 28,
    scenes,
    look: resolveLook(LOOK_DEFAULTS, CAL_LOOK, refLook, style.look),
    presets: resolveLook(LOOK_PRESETS, CAL_LOOK_PRESETS, style.looks),
    maxDist,
  });
  studio.renderer.localClippingEnabled = true;

  const benchTex = createBenchTexture();
  const bench = new THREE.Mesh(
    new THREE.BoxGeometry(9, 0.12, 6.4),
    new THREE.MeshStandardMaterial({ map: benchTex, color: '#FFFFFF', roughness: 0.86, metalness: 0.02 }),
  );
  bench.position.set(0, -0.06, 0);
  bench.receiveShadow = true;
  studio.scene.add(bench);

  // Role studio: the world builds its materials AFTER the studio exists, so the roles it used are read at render time.
  const baseRender = studio.render;
  function render(frame) {
    if (ROLES_USED.glaze || ROLES_USED.metal) studio.lookRig.setRoleDemand(ROLES_USED);
    baseRender(frame);
  }
  return { ...studio, render, bench, benchTex, refPalette: ACTIVE_REF_PALETTE, rolesUsed: ROLES_USED };
}

const MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace';
const SANS = 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif';

function spacedText(ctx, text, x, y, spacing) {
  if (!spacing) {
    ctx.fillText(text, x, y);
    return;
  }
  const align = ctx.textAlign;
  let total = 0;
  for (const ch of text) total += ctx.measureText(ch).width + spacing;
  total = Math.max(0, total - spacing);
  let cx = align === 'right' ? x - total : align === 'center' ? x - total / 2 : x;
  for (const ch of text) {
    ctx.fillText(ch, cx, y);
    cx += ctx.measureText(ch).width + spacing;
  }
}

export function createGaugeHud({ camera, width, height }) {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(2, Math.round(width));
  canvas.height = Math.max(2, Math.round(height));
  const ctx = canvas.getContext('2d');

  const tex = new THREE.CanvasTexture(canvas);
  tex.encoding = THREE.sRGBEncoding;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;

  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false, toneMapped: false });
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat);
  plane.frustumCulled = false;
  plane.renderOrder = 999;
  plane.position.set(0, 0, -1);
  plane.userData.isHudOverlay = true;
  plane.userData.skipContactShadow = true;
  camera.add(plane);

  function fit() {
    const h = 2 * Math.tan((camera.fov * Math.PI) / 360);
    plane.scale.set(h * camera.aspect, h, 1);
  }
  fit();

  function panel(x, y, w, h, { alpha = 0.92 } = {}) {
    ctx.fillStyle = `rgba(250, 251, 252, ${alpha})`;
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = CAL_PALETTE.line;
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  }

  function crosshair(x, y, s = 9) {
    ctx.strokeStyle = 'rgba(21, 24, 28, 0.34)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x - s, y);
    ctx.lineTo(x + s, y);
    ctx.moveTo(x, y - s);
    ctx.lineTo(x, y + s);
    ctx.stroke();
  }

  function draw(state = {}) {
    const W = canvas.width;
    const H = canvas.height;
    const accent = state.accent || CAL_PALETTE.accent;
    const u = Math.min(W, H) / 1080;
    const m = Math.round(Math.min(W, H) * 0.055);
    const portrait = H > W * 1.15;
    const square = !portrait && W < H * 1.15;

    ctx.clearRect(0, 0, W, H);
    ctx.textBaseline = 'alphabetic';

    crosshair(m * 0.55, m * 0.55);
    crosshair(W - m * 0.55, m * 0.55);
    crosshair(m * 0.55, H - m * 0.55);
    crosshair(W - m * 0.55, H - m * 0.55);

    ctx.fillStyle = accent;
    ctx.fillRect(m, m, Math.round(46 * u), Math.max(2, Math.round(3 * u)));
    ctx.fillStyle = CAL_PALETTE.ink;
    ctx.font = `700 ${Math.round(27 * u)}px ${SANS}`;
    ctx.fillText(state.title || 'CALIBRATION', m, m + Math.round(34 * u));
    ctx.font = `500 ${Math.round(12.5 * u)}px ${MONO}`;
    ctx.fillStyle = CAL_PALETTE.muted;
    spacedText(ctx, (state.subtitle || '').toUpperCase(), m, m + Math.round(54 * u), 1.6 * u);

    const bigY = m + Math.round((portrait ? 104 : 118) * u);
    const big = state.big || { label: '', value: '—', unit: '' };
    ctx.fillStyle = CAL_PALETTE.muted;
    ctx.font = `600 ${Math.round(12 * u)}px ${MONO}`;
    spacedText(ctx, (big.label || '').toUpperCase(), m, bigY - Math.round(10 * u), 1.5 * u);
    ctx.fillStyle = CAL_PALETTE.ink;
    ctx.font = `800 ${Math.round((portrait ? 54 : 62) * u)}px ${MONO}`;
    const bigText = String(big.value);
    ctx.fillText(bigText, m, bigY + Math.round(54 * u));
    const bw = ctx.measureText(bigText).width;
    ctx.fillStyle = CAL_PALETTE.muted;
    ctx.font = `600 ${Math.round(18 * u)}px ${MONO}`;
    ctx.fillText(big.unit || '', m + bw + Math.round(9 * u), bigY + Math.round(54 * u));

    const phase = state.phase;
    let stripLayout = null;
    if (phase && phase.labels) {
      const cellW = Math.round(portrait ? (W - m * 2) / phase.labels.length : 138 * u);
      const cellH = Math.round(28 * u);
      const py = H - m - cellH - Math.round(16 * u);
      const stripW = cellW * phase.labels.length;
      stripLayout = { x0: m, py, cellW, cellH, count: phase.labels.length };
      ctx.fillStyle = 'rgba(250, 251, 252, 0.90)';
      ctx.fillRect(m - 6 * u, py - 6 * u, stripW + 12 * u, cellH + 12 * u);
      ctx.strokeStyle = CAL_PALETTE.line;
      ctx.lineWidth = 1;
      ctx.strokeRect(m - 6 * u + 0.5, py - 6 * u + 0.5, stripW + 12 * u - 1, cellH + 12 * u - 1);
      phase.labels.forEach((label, i) => {
        const x = m + i * cellW;
        const on = i === phase.index;
        ctx.fillStyle = on ? accent : 'rgba(21, 24, 28, 0.04)';
        ctx.fillRect(x + 1, py, cellW - 3, cellH);
        ctx.fillStyle = on ? '#FFFFFF' : '#5E666F';
        ctx.font = `600 ${Math.round(11.5 * u)}px ${MONO}`;
        ctx.textAlign = 'center';
        ctx.fillText(label, x + cellW / 2, py + cellH * 0.68);
        ctx.textAlign = 'left';
      });
      ctx.fillStyle = CAL_PALETTE.muted;
      ctx.font = `500 ${Math.round(12 * u)}px ${MONO}`;
      spacedText(ctx, phase.caption || 'CYCLE 0–720° · 1 DOF DERIVED', m, py - Math.round(8 * u), 1.2 * u);
    }

    // 3D-to-2D Projected Collision-Free Stacked Leader Callouts (`teardown` `film.js` standard)
    const callouts = state.callouts;
    if (Array.isArray(callouts) && callouts.length > 0) {
      camera.updateMatrixWorld();
      const projVec = new THREE.Vector3();
      const leftCol = [];
      const rightCol = [];

      for (const item of callouts) {
        const alpha = clamp(item.opacity ?? 1, 0, 1);
        if (alpha <= 0.02) continue;
        if (item.target && item.target.isObject3D) {
          item.target.getWorldPosition(projVec);
          if (item.offset) {
            projVec.x += item.offset[0] || 0;
            projVec.y += item.offset[1] || 0;
            projVec.z += item.offset[2] || 0;
          }
        } else if (Array.isArray(item.worldPos)) {
          projVec.set(item.worldPos[0], item.worldPos[1], item.worldPos[2]);
        } else if (item.worldPos?.isVector3) {
          projVec.copy(item.worldPos);
        } else {
          continue;
        }
        projVec.project(camera);
        if (projVec.z > 1.0 || projVec.z < -1.0) continue;
        const sx = (projVec.x * 0.5 + 0.5) * W;
        const sy = (-projVec.y * 0.5 + 0.5) * H;
        const side = item.side || (sx < W * 0.5 ? 'left' : 'right');
        const entry = {
          label: String(item.label || '').toUpperCase(),
          sub: String(item.sub || '').toUpperCase(),
          sx,
          sy,
          ly: clamp(sy, m + 180 * u, H - m - 96 * u),
          alpha,
          accent: Boolean(item.accent),
        };
        if (side === 'left') leftCol.push(entry);
        else rightCol.push(entry);
      }

      const minGap = Math.round(52 * u);
      const stackColumn = (col) => {
        col.sort((a, b) => a.ly - b.ly);
        for (let i = 1; i < col.length; i++) {
          if (col[i].ly - col[i - 1].ly < minGap) {
            col[i].ly = col[i - 1].ly + minGap;
          }
        }
      };
      stackColumn(leftCol);
      stackColumn(rightCol);

      const drawColumn = (col, isLeft) => {
        const cardW = Math.round((portrait ? 176 : 210) * u);
        const cardH = Math.round(42 * u);
        const cardX = isLeft ? m : W - m - cardW;
        const anchorEdgeX = isLeft ? cardX + cardW : cardX;
        const elbowDx = isLeft ? Math.round(18 * u) : -Math.round(18 * u);

        for (const c of col) {
          ctx.save();
          ctx.globalAlpha = c.alpha;
          const strokeCol = c.accent ? accent : 'rgba(21, 24, 28, 0.72)';

          // Anchor target ring on 3D part
          ctx.strokeStyle = strokeCol;
          ctx.lineWidth = Math.max(1.2, 1.6 * u);
          ctx.beginPath();
          ctx.arc(c.sx, c.sy, Math.max(3.5, 4.5 * u), 0, Math.PI * 2);
          ctx.stroke();
          ctx.fillStyle = c.accent ? accent : CAL_PALETTE.ink;
          ctx.beginPath();
          ctx.arc(c.sx, c.sy, Math.max(1.6, 2.0 * u), 0, Math.PI * 2);
          ctx.fill();

          // Crisp technical elbow leader line
          ctx.beginPath();
          ctx.moveTo(c.sx, c.sy);
          ctx.lineTo(anchorEdgeX + elbowDx, c.ly);
          ctx.lineTo(anchorEdgeX, c.ly);
          ctx.stroke();

          // Callout card
          const cy = Math.round(c.ly - cardH * 0.5);
          panel(cardX, cy, cardW, cardH, { alpha: 0.92 });
          ctx.fillStyle = c.accent ? accent : CAL_PALETTE.ink;
          ctx.fillRect(isLeft ? cardX : cardX + cardW - Math.max(3, Math.round(3.5 * u)), cy, Math.max(3, Math.round(3.5 * u)), cardH);

          ctx.fillStyle = CAL_PALETTE.ink;
          ctx.font = `700 ${Math.round(12.5 * u)}px ${MONO}`;
          ctx.fillText(c.label, cardX + Math.round(10 * u), cy + Math.round(17 * u));
          if (c.sub) {
            ctx.fillStyle = CAL_PALETTE.muted;
            ctx.font = `500 ${Math.round(10.5 * u)}px ${MONO}`;
            ctx.fillText(c.sub, cardX + Math.round(10 * u), cy + Math.round(33 * u));
          }
          ctx.restore();
        }
      };

      drawColumn(leftCol, true);
      drawColumn(rightCol, false);
    }

    const plot = state.plot;
    if (plot) {
      const size = Math.round(portrait ? Math.min(W * 0.62, 360 * u) : square ? 300 * u : 340 * u);
      const px = W - m - size;
      const py = portrait ? m + Math.round(90 * u) : m + Math.round(28 * u);
      panel(px, py, size, size + Math.round(30 * u));
      ctx.fillStyle = CAL_PALETTE.ink;
      ctx.font = `700 ${Math.round(12 * u)}px ${MONO}`;
      spacedText(ctx, plot.title || 'PLOT', px + Math.round(12 * u), py + Math.round(20 * u), 1.3 * u);
      const x0 = px + Math.round(34 * u);
      const y0 = py + Math.round(30 * u);
      const pw = size - Math.round(48 * u);
      const ph = size - Math.round(46 * u);
      const X = (v) => x0 + clamp(v / (plot.xMax || 1), 0, 1) * pw;
      const Y = (v) => y0 + ph - clamp(v / (plot.yMax || 1), 0, 1) * ph;
      ctx.strokeStyle = 'rgba(21, 24, 28, 0.7)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x0, y0 + ph);
      ctx.lineTo(x0 + pw, y0 + ph);
      ctx.stroke();
      ctx.strokeStyle = 'rgba(201, 205, 210, 0.7)';
      for (let i = 1; i <= 3; i++) {
        const gy = y0 + (ph * i) / 4;
        ctx.beginPath();
        ctx.moveTo(x0, gy);
        ctx.lineTo(x0 + pw, gy);
        ctx.stroke();
      }
      for (const s of plot.series || []) {
        if (!s.points || s.points.length < 2) continue;
        ctx.strokeStyle = s.color || CAL_PALETTE.ink;
        ctx.lineWidth = (s.width || 1.6) * u;
        ctx.beginPath();
        s.points.forEach(([vx, vy], i) => {
          const X0 = X(vx);
          const Y0 = Y(vy);
          if (i === 0) ctx.moveTo(X0, Y0);
          else ctx.lineTo(X0, Y0);
        });
        ctx.stroke();
      }
      if (plot.dot) {
        ctx.fillStyle = accent;
        ctx.beginPath();
        ctx.arc(X(plot.dot[0]), Y(plot.dot[1]), Math.max(2.6, 3.4 * u), 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.fillStyle = CAL_PALETTE.muted;
      ctx.font = `500 ${Math.round(12 * u)}px ${MONO}`;
      if (plot.yText) ctx.fillText(plot.yText, px + Math.round(8 * u), y0 + Math.round(9 * u));
      if (plot.xText) {
        ctx.textAlign = 'right';
        ctx.fillText(plot.xText, x0 + pw, y0 + ph + Math.round(14 * u));
        ctx.textAlign = 'left';
      }
      if (plot.note) {
        ctx.fillText(plot.note, px + Math.round(12 * u), py + size + Math.round(22 * u));
      }
    }

    // Animated Operator Pointer & Click Ripple Ring (`teardown` `makeCursor` standard)
    const cur = state.cursor;
    if (cur && (cur.opacity ?? 1) > 0.02 && stripLayout) {
      const fromX = stripLayout.x0 + (cur.fromIndex ?? 0) * stripLayout.cellW + stripLayout.cellW * 0.52;
      const toX = stripLayout.x0 + (cur.toIndex ?? 0) * stripLayout.cellW + stripLayout.cellW * 0.52;
      const cx = cur.x ?? lerp(fromX, toX, clamp(cur.moveK ?? 1, 0, 1));
      const cy = cur.y ?? (stripLayout.py + stripLayout.cellH * 0.58);

      ctx.save();
      ctx.globalAlpha = clamp(cur.opacity ?? 1, 0, 1);

      if ((cur.ring ?? 0) > 0.01) {
        const rk = clamp(cur.ring, 0, 1);
        ctx.strokeStyle = accent;
        ctx.globalAlpha = clamp(cur.opacity ?? 1, 0, 1) * (1 - rk) * 0.85;
        ctx.lineWidth = Math.max(1.5, 2.2 * u);
        ctx.beginPath();
        ctx.arc(toX, cy, (6 + rk * 22) * u, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = clamp(cur.opacity ?? 1, 0, 1);
      }

      const scale = (1 - (cur.press ?? 0) * 0.16) * Math.max(0.75, u);
      ctx.translate(cx, cy);
      ctx.scale(scale, scale);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(0, 20);
      ctx.lineTo(5.5, 15.5);
      ctx.lineTo(9.5, 23.5);
      ctx.lineTo(12.5, 22);
      ctx.lineTo(8.5, 14);
      ctx.lineTo(15, 14);
      ctx.closePath();
      ctx.fillStyle = '#15181C';
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.6;
      ctx.stroke();
      ctx.restore();
    }

    tex.needsUpdate = true;
  }

  return { plane, canvas, texture: tex, draw, fit };
}

// ============================================================================
// 8. MACHINE-FEEL PRIMITIVES + MATERIAL ROLES (ADR-021, teardown absorption)
// ============================================================================
//
// Method borrowed from the `teardown` skill (MIT, elvarofficial; see CREDITS.md): seams carry sunk liners and
// pitch-exact clasps, rings stack and counter-rotate, fins repeat at an exact pitch, sleeves follow a curve,
// wear is painted into the COLOUR map, detail arrives with camera distance, metals are metals. Reimplemented here
// for this engine; nothing of the teardown models, palettes or shot lists is carried over.
//
// Admission rules (ADR-021): (1) no species / object words in any name; (2) NO good-looking defaults - every
// distribution parameter must be passed explicitly and a missing one throws (read it off your reference);
// (3) shape and material role only, never colour; (4) each primitive is shown on two different subjects (SPEC §8).

function need(fn, o, keys) {
  if (!o || typeof o !== 'object') throw new Error(`${fn}: options object required`);
  for (const k of keys) {
    if (o[k] === undefined) throw new Error(`${fn}: missing required parameter "${k}" (no default by design: take it from your reference reading)`);
  }
  return o;
}

// ---------------------------------------------------------------- material roles

/**
 * Roles decide treatment, not species (GEMINI.md rule 6). `shell`/`structural`/`precision` keep their matte rules
 * above; the roles below are added by ADR-021. `glaze` is EXEMPT from the matte-shell rule
 * (roughness >= 0.45, clearcoat <= 0.14): it is a separate role with a glossy clearcoat so a softbox draws a
 * sharp highlight on the panel. Use it only where the reference shows lacquered / enamelled / ceramic plates.
 */
export const MATERIAL_ROLES = {
  metal: { metalnessMin: 0.8, roughnessMin: 0.12, envMapScale: 1.0 },
  glaze: { metalnessMax: 0.2, roughnessMax: 0.16, clearcoatMin: 0.6, clearcoatRoughnessMax: 0.12, envMapScale: 1.0 },
  liner: { metalnessMax: 0.4, roughnessMin: 0.6, envMapScale: 0.4 },
  emissive: { emissive: true },
};

/** Roles the running world has used so far; `createCalLabStudio().render` hands them to the look rig (role studio). */
const ROLES_USED = { glaze: false, metal: false };

export function governMaterialRole(mat, role) {
  const r = MATERIAL_ROLES[role];
  if (!r) throw new Error(`governMaterialRole: unknown role "${role}"`);
  mat.userData = mat.userData || {};
  mat.userData.role = role;
  if (role === 'glaze' || role === 'metal') ROLES_USED[role] = true;
  if (role === 'glaze' && !mat.isMeshPhysicalMaterial) {
    throw new Error('governMaterialRole: glaze needs a MeshPhysicalMaterial (clearcoat)');
  }
  if (r.metalnessMin !== undefined) mat.metalness = Math.max(r.metalnessMin, mat.metalness ?? 0);
  if (r.metalnessMax !== undefined) mat.metalness = Math.min(r.metalnessMax, mat.metalness ?? 0);
  if (r.roughnessMin !== undefined) mat.roughness = Math.max(r.roughnessMin, mat.roughness ?? 1);
  if (r.roughnessMax !== undefined) mat.roughness = Math.min(r.roughnessMax, mat.roughness ?? 0);
  if (r.clearcoatMin !== undefined) mat.clearcoat = Math.max(r.clearcoatMin, mat.clearcoat ?? 0);
  if (r.clearcoatRoughnessMax !== undefined) mat.clearcoatRoughness = Math.min(r.clearcoatRoughnessMax, mat.clearcoatRoughness ?? 0);
  if (r.envMapScale !== undefined) mat.userData.envMapScale = mat.userData.envMapScale ?? r.envMapScale;
  return mat;
}

/** Triangle-weighted metalness bands of everything visible under `root` (+ per-role counts). Prints with `log`. */
export function metalReport(root, { log = true } = {}) {
  const bands = { metal: 0, mid: 0, dielectric: 0 };
  const roles = {};
  const emissiveVisible = new Set();
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!o.isMesh || !o.visible || !o.material) return;
    const g = o.geometry;
    const tris = ((g.index ? g.index.count : g.attributes.position.count) / 3) * (o.isInstancedMesh ? o.count : 1);
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (m.userData?.role === 'emissive') emissiveVisible.add(m);
      if (m.metalness === undefined || m.transparent) continue;
      const band = m.metalness >= 0.8 ? 'metal' : m.metalness >= 0.4 ? 'mid' : 'dielectric';
      bands[band] += tris;
      const role = m.userData?.role || 'unassigned';
      roles[role] = (roles[role] || 0) + tris;
    }
  });
  const total = bands.metal + bands.mid + bands.dielectric || 1;
  const pct = (v) => Math.round((v / total) * 100);
  const res = { metal: pct(bands.metal), mid: pct(bands.mid), dielectric: pct(bands.dielectric), roles, emissiveSubjects: emissiveVisible.size };
  if (log) console.log(`metalReport: metal>=0.8 ${res.metal}%  mid ${res.mid}%  dielectric ${res.dielectric}%  emissive subjects ${res.emissiveSubjects}`);
  return res;
}

// ---------------------------------------------------------------- distance LOD

/** k = 1 at distance <= near, 0 at >= far, smoothstep in between (nothing pops). */
export function lodAt(distance, near, far) {
  return smootherstep(0, 1, (far - distance) / Math.max(1e-6, far - near));
}

/**
 * Detail by camera distance: far read stays quiet, close-ups grow their small parts. Register setters with
 * `add(fn)`; call `update(cameraDistance)` once per frame before render. Both `near` and `far` are required.
 */
export function createLod(opts) {
  const { near, far } = need('createLod', opts, ['near', 'far']);
  const setters = [];
  let k = -1;
  return {
    add(fn) { setters.push(fn); if (k >= 0) fn(k); },
    update(distance) {
      const nk = lodAt(distance, near, far);
      if (nk === k) return k;
      k = nk;
      for (const fn of setters) fn(k);
      return k;
    },
    get k() { return k; },
  };
}

/** Meshes grow from nothing about their own origin; hidden at k = 0. */
export function lodScaleIn(meshes, opts) {
  const { from, to } = need('lodScaleIn', opts, ['from', 'to']);
  return (k) => {
    const s = from + (to - from) * k;
    for (const m of meshes) { m.scale.setScalar(Math.max(s, 1e-4)); m.visible = k > 0.002; }
  };
}

/** A material that moves between two looks, `{color:[far,near], metalness:[..], roughness:[..]}` (any subset). */
export function lodLerpMaterial(mat, spec, objects = []) {
  if (!spec || (!spec.color && !spec.metalness && !spec.roughness)) throw new Error('lodLerpMaterial: give at least one of color / metalness / roughness as [far, near]');
  const c0 = spec.color && new THREE.Color(spec.color[0]);
  const c1 = spec.color && new THREE.Color(spec.color[1]);
  return (k) => {
    if (spec.color) mat.color.lerpColors(c0, c1, k);
    if (spec.metalness) mat.metalness = lerp(spec.metalness[0], spec.metalness[1], k);
    if (spec.roughness) mat.roughness = lerp(spec.roughness[0], spec.roughness[1], k);
    for (const o of objects) o.visible = k > 0.002;
  };
}

// ---------------------------------------------------------------- window cut + rim

/**
 * Cut a window out of any mesh. `keep(x,y,z)` is signed: surface stays where >= 0. Straddling triangles are
 * clipped exactly (position / normal / uv interpolated) so the edge is as clean as the function. Returns
 * `{ geometry, edges }`, edges being boundary polylines `{points, normals}[]` for `windowRim`.
 * Hold the outline: keep a band at the outer rim in `keep` so the silhouette does not change.
 */
export function cutWindow(geometry, keep) {
  if (typeof keep !== 'function') throw new Error('cutWindow: keep(x,y,z) signed function required');
  const src = geometry.index ? geometry.toNonIndexed() : geometry;
  if (!src.attributes.normal) src.computeVertexNormals();
  const P = src.attributes.position, N = src.attributes.normal, U = src.attributes.uv;
  const outP = [], outN = [], outU = [], segs = [];
  const V = (i) => ({ p: new THREE.Vector3(P.getX(i), P.getY(i), P.getZ(i)), n: new THREE.Vector3(N.getX(i), N.getY(i), N.getZ(i)), u: U ? [U.getX(i), U.getY(i)] : null });
  const cross = (a, b, fa, fb) => {
    // interpolate from the lexically smaller end so neighbouring triangles agree on the point
    if (a.p.x > b.p.x || (a.p.x === b.p.x && (a.p.y > b.p.y || (a.p.y === b.p.y && a.p.z > b.p.z)))) [a, b, fa, fb] = [b, a, fb, fa];
    const t = fa / (fa - fb);
    return { p: a.p.clone().lerp(b.p, t), n: a.n.clone().lerp(b.n, t).normalize(), u: a.u ? [a.u[0] + (b.u[0] - a.u[0]) * t, a.u[1] + (b.u[1] - a.u[1]) * t] : null };
  };
  const emit = (v) => { outP.push(v.p.x, v.p.y, v.p.z); outN.push(v.n.x, v.n.y, v.n.z); if (v.u) outU.push(v.u[0], v.u[1]); };
  for (let i = 0; i < P.count; i += 3) {
    const vs = [V(i), V(i + 1), V(i + 2)];
    const f = vs.map((v) => keep(v.p.x, v.p.y, v.p.z));
    if (f[0] >= 0 && f[1] >= 0 && f[2] >= 0) { vs.forEach(emit); continue; }
    if (f[0] < 0 && f[1] < 0 && f[2] < 0) continue;
    const poly = [], cut = [];
    for (let k = 0; k < 3; k++) {
      const a = vs[k], b = vs[(k + 1) % 3], fa = f[k], fb = f[(k + 1) % 3];
      if (fa >= 0) poly.push(a);
      if ((fa >= 0) !== (fb >= 0)) { const x = cross(a, b, fa, fb); poly.push(x); cut.push(x); }
    }
    for (let k = 1; k + 1 < poly.length; k++) [poly[0], poly[k], poly[k + 1]].forEach(emit);
    if (cut.length === 2) segs.push(cut);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(outP, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(outN, 3));
  if (U) g.setAttribute('uv', new THREE.Float32BufferAttribute(outU, 2));
  return { geometry: g, edges: chainCutSegments(segs) };
}

function chainCutSegments(segs) {
  const key = (v) => `${Math.round(v.p.x * 1e4)},${Math.round(v.p.y * 1e4)},${Math.round(v.p.z * 1e4)}`;
  const at = new Map();
  segs.forEach((s, i) => { for (const e of [0, 1]) { const k = key(s[e]); if (!at.has(k)) at.set(k, []); at.get(k).push([i, e]); } });
  const used = new Uint8Array(segs.length);
  const walk = (line, i, e) => {
    for (;;) {
      const next = (at.get(key(segs[i][e])) || []).find(([j]) => !used[j]);
      if (!next) return;
      const [j, ej] = next;
      used[j] = 1;
      line.push(segs[j][1 - ej]);
      i = j; e = 1 - ej;
    }
  };
  const lines = [];
  for (let i = 0; i < segs.length; i++) {
    if (used[i]) continue;
    used[i] = 1;
    const fwd = [segs[i][0], segs[i][1]]; walk(fwd, i, 1);
    const back = []; walk(back, i, 0);
    const pts = [...back.reverse(), ...fwd];
    if (pts.length >= 3) lines.push({ points: pts.map((v) => v.p), normals: pts.map((v) => v.n) });
  }
  return lines;
}

/**
 * Rim of a cut window: side wall sunk `depth` along -normal (the panel thickness, so the hole reads as cut through
 * something solid) plus a lip tube of radius `lip` on the edge. Edges shorter than `minLength` are skipped.
 */
export function windowRim(edge, opts) {
  const { depth, lip, minLength, wallMat, lipMat } = need('windowRim', opts, ['depth', 'lip', 'minLength', 'wallMat', 'lipMat']);
  const grp = new THREE.Group();
  const { points, normals } = edge;
  let len = 0;
  for (let i = 1; i < points.length; i++) len += points[i].distanceTo(points[i - 1]);
  if (len < minLength) return grp;
  if (wallMat) {
    const pos = [], idx = [];
    points.forEach((p, i) => {
      const n = normals[i];
      pos.push(p.x, p.y, p.z, p.x - n.x * depth, p.y - n.y * depth, p.z - n.z * depth);
      if (i) idx.push((i - 1) * 2, i * 2, (i - 1) * 2 + 1, i * 2, i * 2 + 1, (i - 1) * 2 + 1);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    const m = wallMat.clone(); m.side = THREE.DoubleSide;
    grp.add(new THREE.Mesh(g, m));
  }
  if (lipMat && lip > 0) {
    const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
    const n = Math.max(12, Math.round(len / (lip * 1.6)));
    grp.add(new THREE.Mesh(new THREE.TubeGeometry(curve, n, lip, 8, false), lipMat));
  }
  return grp;
}

// ---------------------------------------------------------------- seam hardware

/**
 * Hardware along a seam so it reads as a joint, not a drawn line: a liner tube sunk into the gap and clasps that
 * bridge the gap at an EXACT `pitch` (every `altEvery`-th clasp takes `altMat`). `points`/`normals` describe any
 * curve you own (normals point out of the surface). With `surfaces` (the plates either side) each clasp is seated by
 * a ray per side and dropped when either side misses (a window cut it, or the plate turns away). `space` is the
 * object the group will be added to (matrixWorld converts the ray hits).
 */
export function seamHardware(opts) {
  const { points, normals, pitch, skipEnds, liner, clasp, surfaces, space } = need('seamHardware', opts, ['points', 'normals', 'pitch', 'skipEnds', 'liner', 'clasp', 'surfaces', 'space']);
  const grp = new THREE.Group();
  if (points.length < 2) return grp;
  const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
  const nCurve = new THREE.CatmullRomCurve3(normals.map((n) => n.clone()), false, 'centripetal');
  const len = curve.getLength();
  if (liner) {
    need('seamHardware.liner', liner, ['mat', 'radius', 'sink']);
    const pts = curve.getSpacedPoints(Math.max(8, Math.round(len / (liner.radius * 2.5)))).map((q, i, a) => q.clone().addScaledVector(nCurve.getPoint(i / (a.length - 1)).normalize(), -liner.sink));
    grp.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), pts.length * 2, liner.radius, 8, false), liner.mat));
  }
  if (clasp) {
    need('seamHardware.clasp', clasp, ['mat', 'size', 'altEvery']);
    const [cl, ch, cw] = clasp.size;
    const count = Math.max(1, Math.floor((len * (1 - 2 * skipEnds)) / pitch));
    const box = new THREE.BoxGeometry(cl, ch, cw);
    const T = new THREE.Vector3(), B = new THREE.Vector3(), seatN = new THREE.Vector3();
    const m = new THREE.Matrix4();
    const ray = surfaces ? new THREE.Raycaster() : null;
    const inv = space ? new THREE.Matrix4().copy(space.matrixWorld).invert() : null;
    const toWorld = (v) => (space ? v.clone().applyMatrix4(space.matrixWorld) : v.clone());
    const seat = (q, n) => {
      const hits = [];
      for (const side of [-1, 1]) {
        const o = q.clone().addScaledVector(B, side * cw * 0.42).addScaledVector(n, ch * 6);
        const ow = toWorld(o);
        ray.set(ow, toWorld(o.clone().sub(n)).sub(ow).normalize());
        ray.far = ch * 12;
        const h = ray.intersectObjects(surfaces, false)[0];
        if (!h || !h.face) return null;
        hits.push(inv ? h.point.clone().applyMatrix4(inv) : h.point.clone());
        const fn = h.face.normal.clone().transformDirection(h.object.matrixWorld);
        if (inv) fn.transformDirection(inv);
        if (fn.dot(n) < 0) fn.negate();
        seatN.add(fn);
      }
      if (hits[0].distanceTo(hits[1]) > cw * 1.6) return null;
      const mid = hits[0].add(hits[1]).multiplyScalar(0.5);
      return mid.distanceTo(q) < cw * 1.2 ? mid : null;
    };
    for (let k = 0; k <= count; k++) {
      const u = skipEnds + ((1 - 2 * skipEnds) * k) / Math.max(1, count);
      let q = curve.getPointAt(u);
      curve.getTangentAt(u, T).normalize();
      let n = nCurve.getPoint(u).normalize();
      B.crossVectors(T, n).normalize();
      if (ray) {
        seatN.set(0, 0, 0);
        q = seat(q, n);
        if (!q) continue;
        n = seatN.normalize();
        T.addScaledVector(n, -T.dot(n)).normalize();
        B.crossVectors(T, n).normalize();
      }
      const mesh = new THREE.Mesh(box, k % clasp.altEvery === clasp.altEvery - 1 && clasp.altMat ? clasp.altMat : clasp.mat);
      m.makeBasis(T, n, B);
      mesh.quaternion.setFromRotationMatrix(m);
      mesh.position.copy(q).addScaledVector(n, ch * 0.2);
      grp.add(mesh);
    }
  }
  return grp;
}

// ---------------------------------------------------------------- toothed rings + radial fins

/** Flat ring (axis +z) with `teeth` rounded teeth on the outside. */
export function toothedRingGeometry(opts) {
  const { rOuter, rInner, thick, teeth, toothDepth, bevel } = need('toothedRingGeometry', opts, ['rOuter', 'rInner', 'thick', 'teeth', 'toothDepth', 'bevel']);
  const s = new THREE.Shape();
  const n = teeth * 8;
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * Math.PI * 2;
    const wave = 0.5 + 0.5 * Math.cos(a * teeth);
    const r = rOuter * (1 - toothDepth * (1 - Math.min(1, wave * 2.2)));
    i ? s.lineTo(Math.cos(a) * r, Math.sin(a) * r) : s.moveTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  const hole = new THREE.Path();
  for (let i = 0; i <= 48; i++) {
    const a = -(i / 48) * Math.PI * 2;
    i ? hole.lineTo(Math.cos(a) * rInner, Math.sin(a) * rInner) : hole.moveTo(Math.cos(a) * rInner, Math.sin(a) * rInner);
  }
  s.holes.push(hole);
  const g = new THREE.ExtrudeGeometry(s, { depth: thick, bevelEnabled: bevel > 0, bevelSize: bevel, bevelThickness: bevel, bevelSegments: 1, curveSegments: 4 });
  g.translate(0, 0, -thick / 2);
  return g;
}

/**
 * Concentric toothed rings stepping out of a well, adjacent rings turning opposite ways. rings:
 * `[{rOut, rIn, z, thick, teeth, toothDepth, bevel, mat, spin}]` (all required per ring). With `mirror` every ring is
 * repeated at -z turning the other way. `update(t, open)` spins them; `open` 0..1 lifts ring i by `spread*(i+1)`.
 */
export function ringStack(opts) {
  const { rings, mirror, spread } = need('ringStack', opts, ['rings', 'mirror', 'spread']);
  const group = new THREE.Group();
  const live = [];
  rings.forEach((rc, i) => {
    need(`ringStack.rings[${i}]`, rc, ['rOut', 'rIn', 'z', 'thick', 'teeth', 'toothDepth', 'bevel', 'mat', 'spin']);
    const geo = toothedRingGeometry({ rOuter: rc.rOut, rInner: rc.rIn, thick: rc.thick, teeth: rc.teeth, toothDepth: rc.toothDepth, bevel: rc.bevel });
    for (const sz of mirror ? [1, -1] : [1]) {
      const mesh = new THREE.Mesh(geo, rc.mat);
      mesh.position.z = sz * rc.z;
      group.add(mesh);
      live.push({ mesh, spin: rc.spin * sz * (i % 2 ? -1 : 1), z: sz * rc.z, lift: sz * spread * (i + 1) });
    }
  });
  return {
    group,
    update(t, open = 0) { for (const r of live) { r.mesh.rotation.z = r.spin * t; r.mesh.position.z = r.z + r.lift * open; } },
  };
}

/**
 * Blades at an exact angular `pitch` between radii r0..r1 over [a0, a1] around +z: every `majorEvery`-th one full
 * length and thicker, the rest `minorLength` (0..1) of it. Exact pitch is the point; the big/small beat breaks
 * monotony without randomness. Returns a Group of two InstancedMeshes.
 */
export function radialFins(opts) {
  const { r0, r1, a0, a1, pitch, depth, thick, z, mat, minorMat, majorEvery, minorLength } = need('radialFins', opts, ['r0', 'r1', 'a0', 'a1', 'pitch', 'depth', 'thick', 'z', 'mat', 'minorMat', 'majorEvery', 'minorLength']);
  const grp = new THREE.Group();
  const n = Math.floor((a1 - a0) / pitch) + 1;
  const len = r1 - r0;
  const blade = (l, t) => { const g = new THREE.BoxGeometry(l, t, depth); g.translate(l / 2, 0, 0); return g; };
  const big = [], small = [];
  const o = new THREE.Object3D();
  for (let i = 0; i < n; i++) {
    const a = a0 + i * pitch;
    const major = i % majorEvery === 0;
    const start = major ? r0 : r0 + len * (1 - minorLength);
    o.position.set(Math.cos(a) * start, Math.sin(a) * start, z);
    o.rotation.set(0, 0, a);
    o.updateMatrix();
    (major ? big : small).push(o.matrix.clone());
  }
  const inst = (geo, material, list) => {
    const m = new THREE.InstancedMesh(geo, material, list.length);
    list.forEach((mx, i) => m.setMatrixAt(i, mx));
    m.instanceMatrix.needsUpdate = true;
    m.frustumCulled = false; // vendored three has no InstancedMesh bounds
    return m;
  };
  if (big.length) grp.add(inst(blade(len, thick * 1.6), mat, big));
  if (small.length) grp.add(inst(blade(len * minorLength, thick), minorMat, small));
  return grp;
}

// ---------------------------------------------------------------- curve sleeve

/**
 * Armour sleeve that bends with the curve it rides: a tube over [u0,u1] of a THREE.Curve rebuilt on every `update`
 * (straight instanced sleeves kink where a limb curls). `profile` = `[[t, scale], ...]` rings along the sleeve,
 * t in 0..1 (put two rings close for a lip; group 1 is the first ring segment, give it the seam material, group 0
 * the rest). `axis` fixes the section frame (up = tangent x axis). `arc:[a0,a1]` makes an open shell instead of a
 * closed tube. `update(curve, u0, u1, radiusAt(u), { rx, rz, offset })` - the elliptic section rx/rz is required.
 */
export function curveSleeve(opts) {
  const { radial, profile, axis, arc } = need('curveSleeve', opts, ['radial', 'profile', 'axis', 'arc']);
  const rings = profile.length, stride = radial + 1;
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(rings * stride * 3), uv = new Float32Array(rings * stride * 2);
  const [a0, a1] = arc ?? [0, Math.PI * 2];
  for (let i = 0; i < rings; i++) for (let j = 0; j <= radial; j++) { uv[(i * stride + j) * 2] = profile[i][0]; uv[(i * stride + j) * 2 + 1] = j / radial; }
  const idx = [];
  for (let i = 0; i < rings - 1; i++) for (let j = 0; j < radial; j++) { const a = i * stride + j, b = a + stride; idx.push(a, a + 1, b, b, a + 1, b + 1); }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.addGroup(radial * 6, (rings - 2) * radial * 6, 0);
  g.addGroup(0, radial * 6, 1);
  const cs = Array.from({ length: stride }, (_, j) => { const a = a0 + (j / radial) * (a1 - a0); return [Math.cos(a), Math.sin(a)]; });
  const P = new THREE.Vector3(), T = new THREE.Vector3(), Y = new THREE.Vector3(), Z = new THREE.Vector3();
  function update(curve, u0, u1, radiusAt, o) {
    const { rx, rz } = need('curveSleeve.update', o, ['rx', 'rz']);
    for (let i = 0; i < rings; i++) {
      const [t, k] = profile[i];
      const u = clamp(u0 + (u1 - u0) * t, 0, 1);
      curve.getPointAt(u, P);
      curve.getTangentAt(u, T).normalize();
      Y.crossVectors(T, axis);
      if (Y.lengthSq() < 1e-8) Y.set(0, 1, 0);
      Y.normalize();
      Z.crossVectors(T, Y);
      if (o.offset) P.add(o.offset);
      const r = radiusAt(u) * k;
      for (let j = 0; j <= radial; j++) {
        const q = (i * stride + j) * 3, [c, s] = cs[j];
        pos[q] = P.x + (Y.x * c * rx + Z.x * s * rz) * r;
        pos[q + 1] = P.y + (Y.y * c * rx + Z.y * s * rz) * r;
        pos[q + 2] = P.z + (Y.z * c * rx + Z.z * s * rz) * r;
      }
    }
    g.attributes.position.needsUpdate = true;
    g.computeVertexNormals();
    g.computeBoundingSphere();
  }
  return { geometry: g, update };
}

// ---------------------------------------------------------------- wear into the colour map

/**
 * Wear painted for the COLOUR map (at viewing distance only colour is visible) plus matching bump / roughness
 * relief. Every knob 0..1 (count and contrast) and is REQUIRED: read it off the reference, count the cracks, chips
 * and rivet columns on ONE panel there. A clean reference is a clean panel (all near 0). u runs across the panel,
 * v along it. Returns `{ bumpMap, roughnessMap, overlay, colorMap(baseColor, tint) }`; `colorMap` composites the
 * hairlines and chips over a flat base colour and returns a CanvasTexture. `lineScale` thickens lines for panels
 * seen from far away.
 */
export function wearMaps(opts) {
  const { size, seed, grain, edges, chips, panels, cracks, rivets, lineScale, ink } = need('wearMaps', opts, ['size', 'seed', 'grain', 'edges', 'chips', 'panels', 'cracks', 'rivets', 'lineScale', 'ink']);
  const rnd = mulberry32(seed >>> 0 || 1);
  const W = size, s = W / 1024;
  const mk = () => { const c = document.createElement('canvas'); c.width = c.height = W; return c; };
  const [bc, rc, oc] = [mk(), mk(), mk()];
  const [b, r, o] = [bc, rc, oc].map((c) => c.getContext('2d'));
  b.fillStyle = 'rgb(140,140,140)'; b.fillRect(0, 0, W, W);
  r.fillStyle = 'rgb(150,150,150)'; r.fillRect(0, 0, W, W);
  o.strokeStyle = ink; o.fillStyle = ink;
  for (let i = 0, n = Math.round(4200 * grain); i < n; i++) {
    const pit = i % 3 === 0, a = 0.08 + 0.16 * grain;
    b.fillStyle = pit ? `rgba(60,60,60,${a})` : `rgba(215,215,215,${a * 0.7})`;
    r.fillStyle = pit ? `rgba(225,225,225,${a})` : `rgba(115,115,115,${a * 0.7})`;
    const x = rnd() * W, y = rnd() * W, w = (2 + rnd() * 14) * s, h = (1 + rnd() * 8) * s;
    b.fillRect(x, y, w, h); r.fillRect(x, y, w, h);
  }
  if (edges > 0) {
    const ew = 44 * s * (0.5 + edges * 0.5), dk = Math.round(140 - 105 * edges);
    for (const [x0, x1, flip] of [[0, ew, false], [W - ew, W, true]]) {
      const gr = b.createLinearGradient(x0, 0, x1, 0);
      for (const [t, c] of [[0, `rgb(${dk},${dk},${dk})`], [0.55, 'rgb(110,110,110)'], [0.8, 'rgb(185,185,185)'], [1, 'rgba(140,140,140,0)']]) gr.addColorStop(flip ? 1 - t : t, c);
      b.fillStyle = gr; b.fillRect(x0, 0, x1 - x0, W);
    }
  }
  const chipList = [];
  for (let i = 0, n = Math.round(140 * chips); i < n; i++) {
    const cw = (8 + rnd() * 28) * s, ch = (4 + rnd() * 18) * s, x = i % 2 ? W - cw : 0, y = rnd() * W;
    chipList.push([x, y, cw, ch]);
    b.fillStyle = 'rgb(28,28,28)'; b.fillRect(x, y, cw, ch);
    r.fillStyle = 'rgb(235,235,235)'; r.fillRect(x, y, cw, ch);
    o.fillRect(x, y, cw * 0.7, ch * 0.7);
  }
  const rows = Math.round(7 * panels);
  for (let k = 0; k < rows; k++) {
    const v = ((k + 1) / (rows + 1)) * W;
    b.strokeStyle = 'rgb(24,24,24)'; b.lineWidth = 4.5 * s; b.beginPath(); b.moveTo(0, v); b.lineTo(W, v); b.stroke();
    b.strokeStyle = 'rgb(230,230,230)'; b.lineWidth = 2.5 * s; b.beginPath(); b.moveTo(0, v + 4 * s); b.lineTo(W, v + 4 * s); b.stroke();
    r.strokeStyle = 'rgb(235,235,235)'; r.lineWidth = 6 * s; r.beginPath(); r.moveTo(0, v); r.lineTo(W, v); r.stroke();
    o.lineWidth = 2.2 * s * lineScale; o.beginPath(); o.moveTo(0, v); o.lineTo(W, v); o.stroke();
  }
  for (let c = 0, n = Math.round(56 * cracks); c < n; c++) {
    let x = rnd() * W, y = rnd() * W, ang = (rnd() - 0.5) * Math.PI * 1.6;
    const steps = 6 + Math.floor(rnd() * 7);
    b.strokeStyle = 'rgba(20,20,20,0.88)'; b.lineWidth = (1.6 + (c % 3) * 0.7) * s;
    r.strokeStyle = 'rgba(235,235,235,0.85)'; r.lineWidth = 2.4 * s;
    o.lineWidth = (1.2 + (c % 3) * 0.5) * s * lineScale;
    for (const g2 of [b, r, o]) { g2.beginPath(); g2.moveTo(x, y); }
    for (let k = 0; k < steps; k++) {
      ang += (rnd() - 0.5) * 1.15;
      const l = (12 + rnd() * 26) * s * Math.sqrt(lineScale);
      x += Math.cos(ang) * l; y += Math.sin(ang) * l;
      for (const g2 of [b, r, o]) g2.lineTo(x, y);
    }
    for (const g2 of [b, r, o]) g2.stroke();
  }
  if (rivets > 0) {
    const step = (36 / rivets) * s;
    for (let y = 28 * s; y < W - 20 * s; y += step) for (const x of [36 * s, W - 36 * s]) {
      b.fillStyle = 'rgb(22,22,22)'; b.beginPath(); b.arc(x, y, 5.2 * s, 0, 6.283); b.fill();
      r.fillStyle = 'rgb(230,230,230)'; r.beginPath(); r.arc(x, y, 6 * s, 0, 6.283); r.fill();
      o.beginPath(); o.arc(x, y, 3.2 * s * lineScale, 0, 6.283); o.fill();
    }
  }
  const tex = (c) => { const t = new THREE.CanvasTexture(c); t.anisotropy = 4; return t; };
  function colorMap(baseColor, tint = null) {
    const cc = mk(), g2 = cc.getContext('2d');
    g2.fillStyle = baseColor; g2.fillRect(0, 0, W, W);
    if (tint) { g2.fillStyle = tint; g2.globalAlpha = 0.18 * edges; g2.fillRect(0, 0, 44 * s, W); g2.fillRect(W - 44 * s, 0, 44 * s, W); g2.globalAlpha = 1; }
    g2.drawImage(oc, 0, 0);
    const t = tex(cc);
    if ('sRGBEncoding' in THREE) t.encoding = THREE.sRGBEncoding;
    return t;
  }
  return { bumpMap: tex(bc), roughnessMap: tex(rc), overlay: oc, colorMap };
}
