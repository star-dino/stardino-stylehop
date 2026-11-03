/**
 * Calibration Lab · Flagship Showcase v5 (`out/尝试/鲸鱼/world.js`)
 *
 * MECHANICAL HUMPBACK WHALE · SUBJECT_0017 (11,000+ Part Heavy-Metal & White-Titanium Edition)
 * Aquatic Biomechatronics Lab · Leviathan-Class · Rev 3.7.4
 *
 * v5 Precision Anatomical & Material Match to `reference.jpg`:
 *   1. Open-Bay High-Contrast Thoracic Spine (`SPINAL LINKAGE`):
 *      - 12 wide-spaced compound C-shaped Champagne-Brass & Steel rib arches (`width = 5.2`, `bay = 34`)
 *      - Compact `#080A0D` inner occlusion core (`r = 0.32 * rOuter`) leaving wide-open dark bays between rings
 *      - Sleek horizontal mirror-chrome hydraulic piston rods & brass rails spanning cleanly across the open dark bays!
 *   2. Tapered Diagonal Cutaway White-Titanium Fairings (`a0Start -> a0End`):
 *      - Lower-flank white-titanium hull behind the pectoral fin has a sweeping diagonal cutaway edge (`a0: 1.08 -> 1.98`)
 *      - 3 tapered leaf-shaped exploded flank shrouds floating below the rear peduncle
 *      - Shoulder shield starts at `u = 0.415` (`x = -100`), leaving the circular Sonar Core & 3 cranial rings 100% unobstructed!
 *   3. Rich Fiery Signal-Orange Voronoi Sonar Core (`#E63E00` -> `#FF9A18`) + Clean Converging Humpback Beak.
 *   4. Broad Banked Pectoral Hydrofoil Thruster & Gull-Wing Horizontal Tail Flukes.
 */

import '/engine/vendor/three.min.js';
import { clamp, lerp, smootherstep } from '/engine/motion.js';
import {
  blockGeometry,
  braidedHoseBundle,
  counterboreBossGeometry,
  createCalLabStudio,
  createMaterials,
  createSilkscreenDecal,
  gearGeometry,
  governIndustrialMaterial,
  mergeGeometries,
  normalizeGeometryUVs,
  ribbedLinkGeometry,
  sweptProfileGeometry,
} from '/styles/calibration-lab/kernel.js';

const THREE = globalThis.THREE;

// ============================================================================
// 1. CUSTOM SONAR CORE SHADER (FIERY SIGNAL-ORANGE VORONOI ACOUSTIC PLASMA)
// ============================================================================

const SONAR_VS = `
varying vec3 vNormalView;
varying vec3 vViewPos;
varying vec3 vLocalPos;
void main() {
  vLocalPos = normalize(position);
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  vViewPos = -mvPosition.xyz;
  vNormalView = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * mvPosition;
}
`;

const SONAR_FS = `
uniform float uTime;
uniform float uPulse;
varying vec3 vNormalView;
varying vec3 vViewPos;
varying vec3 vLocalPos;

vec3 hash3(vec3 p) {
  p = vec3(
    dot(p, vec3(127.1, 311.7, 74.7)),
    dot(p, vec3(269.5, 183.3, 246.1)),
    dot(p, vec3(113.5, 271.9, 124.6))
  );
  return fract(sin(p) * 43758.5453123);
}

vec2 voronoi3D(vec3 x) {
  vec3 p = floor(x);
  vec3 f = fract(x);
  float d1 = 8.0;
  float d2 = 8.0;
  for (int k = -1; k <= 1; k++) {
    for (int j = -1; j <= 1; j++) {
      for (int i = -1; i <= 1; i++) {
        vec3 b = vec3(float(i), float(j), float(k));
        vec3 r = b - f + hash3(p + b);
        float d = dot(r, r);
        if (d < d1) {
          d2 = d1;
          d1 = d;
        } else if (d < d2) {
          d2 = d;
        }
      }
    }
  }
  return vec2(sqrt(d1), sqrt(d2));
}

void main() {
  vec3 N = normalize(vNormalView);
  vec3 V = normalize(vViewPos);
  float ndotv = clamp(abs(dot(N, V)), 0.0, 1.0);
  float fresnel = pow(1.0 - ndotv, 2.2);

  vec2 vMain = voronoi3D(vLocalPos * 4.8 + vec3(0.0, uTime * 0.08, 0.0));
  vec2 vFine = voronoi3D(vLocalPos * 9.6 - vec3(uTime * 0.11, 0.0, 0.0));
  float edgeMain = smoothstep(0.10, 0.010, vMain.y - vMain.x);
  float edgeFine = smoothstep(0.08, 0.008, vFine.y - vFine.x);
  float cellDark = smoothstep(0.05, 0.42, vMain.x);

  float lat = acos(clamp(vLocalPos.y, -1.0, 1.0));
  float lon = atan(vLocalPos.z, vLocalPos.x);
  float graticule = smoothstep(0.94, 0.995, abs(sin(lat * 10.0))) + smoothstep(0.94, 0.995, abs(sin(lon * 10.0)));

  // Tight incandescent center spark + deep fiery orange-amber body (never washed-out pale yellow!)
  float hotSpot = pow(ndotv, 6.5) * (0.95 + 0.30 * uPulse);
  float midGlow = pow(ndotv, 1.45) * (1.0 - cellDark * 0.35);

  vec3 obsidianAmber = vec3(0.11, 0.018, 0.002);
  vec3 fieryOrange = vec3(0.88, 0.22, 0.01);
  vec3 brightAmber = vec3(1.00, 0.64, 0.10);
  vec3 whiteHot = vec3(1.00, 0.97, 0.86);

  vec3 col = mix(obsidianAmber, fieryOrange, midGlow);
  float webMask = clamp(edgeMain * 0.92 + edgeFine * 0.42 + graticule * 0.16, 0.0, 1.0);
  col = mix(col, brightAmber, webMask);
  col = mix(col, whiteHot, clamp(hotSpot + edgeMain * pow(ndotv, 2.4) * 0.48, 0.0, 1.0));
  col += vec3(0.85, 0.24, 0.02) * fresnel * 0.35;

  gl_FragColor = vec4(col, 0.99);
}
`;

function createSonarCoreMaterial() {
  return new THREE.ShaderMaterial({
    vertexShader: SONAR_VS,
    fragmentShader: SONAR_FS,
    uniforms: {
      uTime: { value: 0 },
      uPulse: { value: 0.5 },
    },
    transparent: true,
    toneMapped: false,
  });
}

// ============================================================================
// 2. FAST BATCH-MERGED GREEBLE BUILDER (`10,000+` PARTS -> `<100` DRAW CALLS)
// ============================================================================

const _mat4 = new THREE.Matrix4();
const _pos = new THREE.Vector3();
const _quat = new THREE.Quaternion();
const _euler = new THREE.Euler();
const _scl = new THREE.Vector3();
const _up = new THREE.Vector3(0, 1, 0);
const _dir = new THREE.Vector3();

let _templates = null;
function getTemplates() {
  if (_templates) return _templates;
  const box = normalizeGeometryUVs(new THREE.BoxGeometry(1, 1, 1), 18);
  const cyl = normalizeGeometryUVs(new THREE.CylinderGeometry(1, 1, 1, 10), 18);
  const hex = normalizeGeometryUVs(new THREE.CylinderGeometry(1, 1, 1, 6), 14);
  const cone = normalizeGeometryUVs(new THREE.ConeGeometry(1, 1, 8), 16);
  const ring = normalizeGeometryUVs(new THREE.TorusGeometry(1, 0.14, 8, 24), 18);
  _templates = { box, cyl, hex, cone, ring };
  return _templates;
}

function createBucketBuilder() {
  const buckets = new Map();
  let partCount = 0;

  function pushGeo(matKey, geo) {
    if (!buckets.has(matKey)) buckets.set(matKey, []);
    buckets.get(matKey).push(geo);
    partCount++;
  }

  function addPart(matKey, templateGeo, { x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1 }) {
    const g = templateGeo.clone();
    _pos.set(x, y, z);
    _euler.set(rx, ry, rz);
    _quat.setFromEuler(_euler);
    _scl.set(sx, sy, sz);
    _mat4.compose(_pos, _quat, _scl);
    g.applyMatrix4(_mat4);
    pushGeo(matKey, g);
  }

  function addStrut(matKey, templateGeo, pA, pB, radius = 1.2) {
    _dir.subVectors(pB, pA);
    const len = _dir.length();
    if (len < 1e-3) return;
    _dir.divideScalar(len);
    _quat.setFromUnitVectors(_up, _dir);
    _pos.addVectors(pA, pB).multiplyScalar(0.5);
    _scl.set(radius, len, radius);
    _mat4.compose(_pos, _quat, _scl);
    const g = templateGeo.clone();
    g.applyMatrix4(_mat4);
    pushGeo(matKey, g);
  }

  function flushTo(parentGroup, matMap, { castShadow = true, receiveShadow = true } = {}) {
    for (const [matKey, list] of buckets.entries()) {
      if (!list.length) continue;
      const merged = mergeGeometries(list);
      const mesh = new THREE.Mesh(merged, matMap[matKey]);
      mesh.castShadow = castShadow;
      mesh.receiveShadow = receiveShadow;
      parentGroup.add(mesh);
    }
    buckets.clear();
  }

  return { pushGeo, addPart, addStrut, flushTo, getPartCount: () => partCount };
}

// ============================================================================
// 3. ANATOMICAL ENVELOPE & 3-TIER HIGH-CONTRAST MATERIALS
// ============================================================================

function whaleEnvelope(u) {
  const x = lerp(-430, 345, u);
  const centerY =
    u < 0.26
      ? lerp(-16, 4, smootherstep(0, 1, u / 0.26))
      : lerp(4, 34, Math.pow(clamp((u - 0.26) / 0.74, 0, 1), 1.32));

  // Inside-Out Clearance Envelope: guaranteed to enclose the Cranial Sonar Core (x=-196, r=52),
  // 4 Cranial Collimator Rings (x=-140..-104, r=54), and all 12 Thoracic Spine Stations with >= 10mm clearance.
  let halfW = 10;
  let dorsalH = 6.0;
  let ventralH = 7.0;

  if (u < 0.22) {
    const k = clamp(u / 0.22, 0, 1);
    halfW = lerp(10, 74, Math.pow(k, 0.72));
    dorsalH = lerp(6.0, 58, Math.pow(k, 1.35));
    ventralH = lerp(7.0, 66, Math.pow(k, 0.72));
  } else if (u < 0.54) {
    const k = clamp((u - 0.22) / 0.32, 0, 1);
    const arch = Math.sin(k * Math.PI);
    halfW = lerp(74, 82, Math.sin(k * Math.PI * 0.65)) + arch * 6;
    dorsalH = lerp(58, 72, Math.sin(k * Math.PI * 0.65)) + arch * 6;
    ventralH = lerp(66, 76, Math.sin(k * Math.PI * 0.58)) + arch * 10;
  } else {
    const k = clamp((u - 0.54) / 0.46, 0, 1);
    const ease = smootherstep(0, 1, k);
    halfW = lerp(80, 14, ease);
    dorsalH = lerp(72, 13, ease);
    ventralH = lerp(74, 13, ease);
  }
  return {
    x,
    centerY,
    halfW,
    dorsalY: centerY + dorsalH,
    ventralY: centerY - ventralH,
    dorsalH,
    ventralH,
  };
}

/**
 * Deterministic axial spine wave evaluator shared by BOTH internal spine stations and outer segmented
 * hull fairings so the outer shell and internal ribs move as a single locked kinematic body with zero clipping.
 */
function evalSpineKinematics(x, t, swimSpeed = 2.45) {
  const sFrac = clamp((x - -86) / (310 - -86), 0, 1);
  const headBlend = smootherstep(-320, -86, x);
  const phase = t * swimSpeed - (sFrac + 0.25) * 3.2;
  const ampY = lerp(1.8, 11.5, Math.pow(sFrac, 1.35)) * (0.35 + 0.65 * headBlend);
  const ampZ = lerp(0.5, 3.2, Math.pow(sFrac, 1.4)) * headBlend;

  const dy = Math.sin(phase) * ampY;
  const dz = Math.cos(phase * 0.5) * ampZ;
  const pitchZ = Math.cos(phase) * lerp(0.012, 0.068, sFrac) * headBlend;
  const yawY = -Math.sin(phase * 0.5) * lerp(0.006, 0.024, sFrac) * headBlend;
  const rollX = Math.sin(t * 1.4 + sFrac * 3.3) * 0.022 * headBlend;
  return { sFrac, dy, dz, pitchZ, yawY, rollX };
}

/**
 * Evaluates a point `P(u, a)` on the whale hull surface along with its exact orthonormal surface frame
 * `(T_u, T_a, N_out)` so composite panels, latches, bolts, and silkscreen decals sit 100% flush.
 */
function evalHullSurfaceFrame(u, a, rScale = 1.04, radialOffset = 0.0) {
  const samplePt = (uu, aa) => {
    const env = whaleEnvelope(clamp(uu, 0, 1));
    const cosA = Math.cos(aa);
    const sinA = Math.sin(aa);
    const radY = cosA >= 0 ? env.dorsalH : env.ventralH;
    return new THREE.Vector3(
      env.x,
      env.centerY + cosA * (radY * rScale + radialOffset),
      sinA * (env.halfW * rScale + radialOffset),
    );
  };
  const p = samplePt(u, a);
  const du = 0.004;
  const da = 0.015;
  const pU1 = samplePt(Math.min(1, u + du), a);
  const pU0 = samplePt(Math.max(0, u - du), a);
  const pA1 = samplePt(u, a + da);
  const pA0 = samplePt(u, a - da);

  const tU = pU1.sub(pU0).normalize();
  const tA = pA1.sub(pA0).normalize();
  // Outward normal on (x(u), centerY + cos(a)*R_y, sin(a)*R_z) is normalize(tA x tU)
  const normal = new THREE.Vector3().crossVectors(tA, tU).normalize();
  // Upright circumferential tangent (-tA points toward dorsal crest +Y on the port side, forming right-handed basis (tU, upA, normal))
  const upA = new THREE.Vector3().crossVectors(normal, tU).normalize();

  const rotMat = new THREE.Matrix4().makeBasis(tU, upA, normal);
  const quat = new THREE.Quaternion().setFromRotationMatrix(rotMat);
  return { pos: p, tU, tA: upA, normal, quat };
}

export function buildMechanicalWhale(M) {
  const root = new THREE.Group();
  const rootScale = 0.00535;
  root.scale.setScalar(rootScale);
  root.position.set(-0.05, 1.30, 0.02);
  // Positive Y rotation (`+0.20`) brings the whale's HEAD (`-X`) forward toward `+Z` (the viewer)
  // and sends the TAIL (`+X`) receding into `-Z` (upper-right background), matching `reference.jpg`!
  root.rotation.y = 0.20;
  root.rotation.z = 0.145;

  const T = getTemplates();
  let totalSubParts = 0;

  // --------------------------------------------------------------------------
  // 3-TIER MATERIAL SYSTEM (Enforced `teardown` Industrial Roughness Discipline)
  // --------------------------------------------------------------------------
  // 1. Primary External Hull (`01 External Hull`): Matte Bead-Blasted White-Titanium (`#F4F1EA`, roughness >= 0.46)
  const hullIvory = governIndustrialMaterial(
    new THREE.MeshPhysicalMaterial({
      color: '#F4F1EA',
      metalness: 0.18,
      roughness: 0.48,
      clearcoat: 0.10,
      clearcoatRoughness: 0.42,
      normalMap: M.alu.normalMap,
      normalScale: new THREE.Vector2(0.14, 0.14),
      roughnessMap: M.alu.roughnessMap,
    }),
    'shell',
  );

  // 2. Secondary External Hull: Brushed Satin Silver-Titanium (`#C8CDD4`, roughness >= 0.45)
  const hullSilver = governIndustrialMaterial(M.alu.clone(), 'shell');
  hullSilver.color.set('#C8CDD4');
  hullSilver.metalness = 0.78;
  hullSilver.roughness = 0.46;

  // 3. Dark Anodized Gunmetal / Silicon-Carbide Structural Sub-Frame (`#20242B`, roughness >= 0.45)
  const hullDark = governIndustrialMaterial(M.graphite.clone(), 'shell');
  hullDark.color.set('#20242B');
  hullDark.metalness = 0.72;
  hullDark.roughness = 0.46;

  // 4. Deep Cavity Occlusion Black (absorbs stray interior light -> crisp pseudo-SSAO!)
  const cavityBlack = new THREE.MeshStandardMaterial({
    color: '#07090C',
    metalness: 0.16,
    roughness: 0.94,
  });

  // 5. Gleaming Champagne Gold-Brass (`02/04` thoracic ribs, sonar bezel & actuators)
  const goldBrass = M.bronze.clone();
  goldBrass.color.set('#F0C265');
  goldBrass.metalness = 0.92;
  goldBrass.roughness = 0.14;
  goldBrass.envMapIntensity = 1.90;

  // 6. Warm Polished Copper (induction coils & hydraulic sleeves)
  const copperGold = M.bronze.clone();
  copperGold.color.set('#DF7635');
  copperGold.metalness = 0.90;
  copperGold.roughness = 0.18;
  copperGold.envMapIntensity = 1.65;

  // 7. Mirror-Polished Hydraulic Chrome (piston rods & longitudinal rails)
  const chrome = M.chrome.clone();
  chrome.color.set('#F7FAFF');
  chrome.metalness = 0.98;
  chrome.roughness = 0.07;
  chrome.envMapIntensity = 2.05;

  // 8. Bright Machined Stainless Steel (flanges & bearing collars)
  const steel = M.steel.clone();
  steel.color.set('#DCE2EA');
  steel.metalness = 0.88;
  steel.roughness = 0.16;
  steel.envMapIntensity = 1.70;

  const matMap = {
    ivory: hullIvory,
    silver: hullSilver,
    dark: hullDark,
    cavity: cavityBlack,
    brass: goldBrass,
    copper: copperGold,
    chrome,
    steel,
  };

  const add = (parent, geo, mat, opts = {}) => {
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = opts.cast !== false;
    m.receiveShadow = opts.receive !== false;
    parent.add(m);
    totalSubParts++;
    return m;
  };

  // ==========================================================================
  // A. CRANIAL MODULE, UNOBSTRUCTED CIRCULAR SONAR CORE & STREAMLINED JAW (`x = -430 .. -100`)
  // ==========================================================================
  const headGroup = new THREE.Group();
  root.add(headGroup);

  // Positioned inside the cranial envelope (`z = 10`, `r_bezel = 52`, max `+Z = 62 < hull 82`)
  // so the closed Cranial Sonar Gull-Wing Hatch wraps it with 100% zero clipping in Scene 1!
  const sonarAnchor = new THREE.Group();
  sonarAnchor.position.set(-196, 6, 10);
  headGroup.add(sonarAnchor);

  // 1. Deep Dark Acoustic Socket Backing Bowl behind the Sonar Core
  const socketBowlGeo = new THREE.SphereGeometry(50, 32, 24, 0, Math.PI * 2, 0, Math.PI * 0.65);
  socketBowlGeo.rotateX(-Math.PI * 0.5);
  socketBowlGeo.rotateY(0.20);
  const socketBowl = add(sonarAnchor, socketBowlGeo, cavityBlack);
  socketBowl.position.set(2, 0, -10);

  // 2. Glowing Spherical Phased-Array Sonar Core (`R = 41.5`)
  const sonarMat = createSonarCoreMaterial();
  const sonarSphere = add(
    sonarAnchor,
    new THREE.SphereGeometry(41.5, 48, 36),
    sonarMat,
    { cast: false, receive: false },
  );
  sonarSphere.renderOrder = 4;

  const innerCoreMat = new THREE.MeshBasicMaterial({
    color: '#FFE8B0',
    transparent: true,
    opacity: 0.95,
    toneMapped: false,
  });
  add(sonarAnchor, new THREE.SphereGeometry(8.5, 24, 20), innerCoreMat, { cast: false, receive: false });

  const haloMat = new THREE.MeshBasicMaterial({
    color: '#FF5500',
    transparent: true,
    opacity: 0.16,
    side: THREE.BackSide,
    depthWrite: false,
    toneMapped: false,
  });
  const sonarHalo = add(sonarAnchor, new THREE.SphereGeometry(45.5, 32, 24), haloMat, { cast: false, receive: false });

  // Tight-radius point light so it illuminates the brass bezel WITHOUT washing out the white hull!
  const sonarLight = new THREE.PointLight('#FF6A10', 1.8, 0.95, 1.8);
  sonarAnchor.add(sonarLight);

  // 3. Delicate Golden Geodesic Filament Cage around the Sonar Sphere
  const geodesicCage = new THREE.Group();
  sonarAnchor.add(geodesicCage);
  {
    const cageB = createBucketBuilder();
    const ico = new THREE.IcosahedronGeometry(42.6, 2);
    const posAttr = ico.attributes.position;
    const vMap = new Map();
    const uniqueVerts = [];
    const keyOf = (v) => `${Math.round(v.x * 10)},${Math.round(v.y * 10)},${Math.round(v.z * 10)}`;
    const getIdx = (v) => {
      const k = keyOf(v);
      if (vMap.has(k)) return vMap.get(k);
      const idx = uniqueVerts.length;
      uniqueVerts.push(v.clone());
      vMap.set(k, idx);
      return idx;
    };
    const edgeSet = new Set();
    for (let i = 0; i < posAttr.count; i += 3) {
      const va = new THREE.Vector3().fromBufferAttribute(posAttr, i);
      const vb = new THREE.Vector3().fromBufferAttribute(posAttr, i + 1);
      const vc = new THREE.Vector3().fromBufferAttribute(posAttr, i + 2);
      const ia = getIdx(va);
      const ib = getIdx(vb);
      const ic = getIdx(vc);
      for (const [p, q] of [[ia, ib], [ib, ic], [ic, ia]]) {
        const ek = p < q ? `${p}_${q}` : `${q}_${p}`;
        if (!edgeSet.has(ek)) {
          edgeSet.add(ek);
          const pA = uniqueVerts[p];
          const pB = uniqueVerts[q];
          const rStrut = pA.z > 24 && pB.z > 24 ? 0.22 : 0.36;
          cageB.addStrut('brass', T.cyl, pA, pB, rStrut);
        }
      }
    }
    for (let i = 0; i < uniqueVerts.length; i++) {
      const v = uniqueVerts[i];
      if (v.z > 28) continue;
      _dir.copy(v).normalize();
      _quat.setFromUnitVectors(_up, _dir);
      _euler.setFromQuaternion(_quat);
      cageB.addPart('brass', T.hex, {
        x: v.x,
        y: v.y,
        z: v.z,
        rx: _euler.x,
        ry: _euler.y,
        rz: _euler.z,
        sx: 0.82,
        sy: 0.92,
        sz: 0.82,
      });
    }
    totalSubParts += cageB.getPartCount();
    cageB.flushTo(geodesicCage, matMap, { castShadow: false, receiveShadow: false });
  }

  // 4. Circular Phased-Array Aperture Bezel & Radial Ultrasonic Transducers
  {
    const bezelB = createBucketBuilder();
    const bezelRings = [
      { r: 45.0, tube: 1.8, zOff: 4, mat: 'brass', ry: -0.20 },
      { r: 48.8, tube: 2.2, zOff: 0, mat: 'steel', ry: -0.20 },
      { r: 52.5, tube: 1.8, zOff: -4, mat: 'dark', ry: -0.20 },
    ];
    for (const br of bezelRings) {
      const tGeo = normalizeGeometryUVs(new THREE.TorusGeometry(br.r, br.tube, 12, 48), 22);
      tGeo.rotateY(br.ry);
      tGeo.translate(0, 0, br.zOff);
      bezelB.pushGeo(br.mat, tGeo);
    }

    for (let ringIdx = 0; ringIdx < 2; ringIdx++) {
      const count = 32;
      const zOff = 3 - ringIdx * 5;
      for (let k = 0; k < count; k++) {
        const a = (k / count) * Math.PI * 2;
        const pIn = new THREE.Vector3(Math.cos(a) * 42.8, Math.sin(a) * 42.8, zOff + Math.cos(a) * 3.0);
        const pOut = new THREE.Vector3(Math.cos(a) * 54.0, Math.sin(a) * 54.0, zOff - 2 + Math.cos(a) * 3.8);
        bezelB.addStrut(k % 2 === 0 ? 'brass' : 'steel', T.cyl, pIn, pOut, 1.35);
        const pMid1 = pIn.clone().lerp(pOut, 0.25);
        const pMid2 = pIn.clone().lerp(pOut, 0.68);
        bezelB.addStrut('copper', T.cyl, pMid1, pMid2, 1.90);
        bezelB.addStrut('chrome', T.cyl, pIn.clone().multiplyScalar(0.96), pOut.clone().multiplyScalar(1.03), 0.85);
      }
    }
    totalSubParts += bezelB.getPartCount();
    bezelB.flushTo(sonarAnchor, matMap);

    // 5. Posterior Cranial Collimator Rings (`x = -140 .. -108`, centered at `z = 6` inside cranial envelope,
    //    ending at `x = -108` so the Shoulder Escutcheon Shield starting at `x = -100` has 100% zero clipping!)
    const headB = createBucketBuilder();
    const ringOffsets = [
      { dx: -140, r: 47, count: 32 },
      { dx: -129, r: 49.5, count: 36 },
      { dx: -118, r: 52, count: 38 },
      { dx: -108, r: 54, count: 40 },
    ];
    for (let rIdx = 0; rIdx < ringOffsets.length; rIdx++) {
      const { dx, r, count } = ringOffsets[rIdx];
      for (let k = 0; k < count; k++) {
        const a = (k / count) * Math.PI * 2;
        const ca = Math.cos(a);
        const sa = Math.sin(a);
        const py = 5 + ca * r;
        const pz = 6 + sa * r;
        const isNearArch = sa >= -0.15;
        const archMat = isNearArch ? (rIdx % 2 === 0 ? 'brass' : 'steel') : 'dark';
        headB.addPart(archMat, T.box, {
          x: dx,
          y: py,
          z: pz,
          rx: a,
          sx: 3.4,
          sy: 3.2,
          sz: (2 * Math.PI * r) / count + 1.0,
        });
        headB.addPart(isNearArch && k % 2 === 0 ? 'brass' : 'dark', T.cyl, {
          x: dx,
          y: py,
          z: pz,
          rx: a,
          sx: 1.4,
          sy: 6.2,
          sz: 1.4,
        });
        if (isNearArch) {
          headB.addPart('chrome', T.cyl, {
            x: dx - 5,
            y: py * 0.95,
            z: pz * 0.95,
            rz: Math.PI / 2,
            sx: 0.90,
            sy: 11.0,
            sz: 0.90,
          });
        }
      }
    }

    // 6. Sleek Converging Upper Rostrum & Cranial Hood (`x = -430 .. -95`)
    //    Slopes cleanly from forehead (`y = +64`) down to the sleek snout tip (`x = -430, y = -16`).
    //    NOTE: Do NOT call `.rotateX(Math.PI / 2)` on a curve whose Y coordinates are non-zero!
    //    Instead, `radiusAt` controls vertical thickness (`N` in X-Y) and `scaleZAt` controls horizontal width (`B` in Z).
    const rostrumSpinePts = [
      new THREE.Vector3(-430, -16, 4),
      new THREE.Vector3(-372, -6, 10),
      new THREE.Vector3(-308, 12, 16),
      new THREE.Vector3(-242, 42, 18),
      new THREE.Vector3(-180, 62, 14),
      new THREE.Vector3(-102, 68, 6),
    ];
    const rostrumDeckGeo = normalizeGeometryUVs(
      sweptProfileGeometry({
        points: rostrumSpinePts,
        radiusAt: (u) => lerp(4.2, 10.5, Math.pow(u, 0.65)),
        scaleZAt: 3.8,
        tubularSeg: 36,
        radialSeg: 18,
      }),
      28,
    );
    headB.pushGeo('ivory', rostrumDeckGeo);

    // Secondary satin-silver upper snout trim plate along the beak cheek (`x = -426 .. -232`)
    const rostrumTrimPts = [
      new THREE.Vector3(-426, -17, 8),
      new THREE.Vector3(-365, -9, 22),
      new THREE.Vector3(-298, 5, 34),
      new THREE.Vector3(-232, 26, 38),
    ];
    const rostrumTrimGeo = normalizeGeometryUVs(
      sweptProfileGeometry({
        points: rostrumTrimPts,
        radiusAt: (u) => lerp(3.4, 7.8, Math.pow(u, 0.70)),
        scaleZAt: 2.8,
        tubularSeg: 28,
        radialSeg: 14,
      }),
      26,
    );
    headB.pushGeo('silver', rostrumTrimGeo);

    // Exposed Horizontal Chrome & Brass Actuator Tubes along the mouth slit (`x = -415 .. -235`)
    const slitStart = new THREE.Vector3(-415, -20, 10);
    const slitEnd = new THREE.Vector3(-235, -16, 48);
    headB.addStrut('chrome', T.cyl, slitStart, slitEnd, 2.8);
    headB.addStrut('brass', T.cyl, new THREE.Vector3(-405, -22, 12), new THREE.Vector3(-238, -21, 50), 2.2);
    for (let k = 0; k < 12; k++) {
      const f = k / 11;
      const pCollar = slitStart.clone().lerp(slitEnd, f);
      headB.addPart(k % 2 === 0 ? 'brass' : 'dark', T.cyl, {
        x: pCollar.x,
        y: pCollar.y - 1,
        z: pCollar.z,
        rz: Math.PI / 2 - 0.05,
        ry: 0.20,
        sx: 4.0,
        sy: 4.2,
        sz: 4.0,
      });
    }

    // Dorsal sensor tubercles along the snout crest
    for (let tIdx = 0; tIdx < 15; tIdx++) {
      const f = tIdx / 14;
      const tx = lerp(-412, -112, f);
      const ty = lerp(-14, 69, Math.pow(f, 0.76));
      headB.addPart(tIdx % 2 === 0 ? 'silver' : 'dark', T.cyl, {
        x: tx,
        y: ty + 2.8,
        z: 4,
        sx: 3.4,
        sy: 2.4,
        sz: 4.6,
      });
    }

    // 7. Sculpted White-Titanium Lower Mandible Rim (`lip`) curving smoothly under the Sonar Core
    const mandibleLipPts = [
      new THREE.Vector3(-430, -21, 2),
      new THREE.Vector3(-355, -25, 24),
      new THREE.Vector3(-272, -33, 46),
      new THREE.Vector3(-188, -48, 60),
      new THREE.Vector3(-125, -42, 62),
      new THREE.Vector3(-82, -22, 58),
    ];
    const mandibleLipGeo = normalizeGeometryUVs(
      sweptProfileGeometry({
        points: mandibleLipPts,
        radiusAt: (u) => lerp(6.0, 14.5, Math.sin(u * Math.PI * 0.85 + 0.12)),
        scaleZAt: 0.56,
        tubularSeg: 36,
        radialSeg: 14,
      }),
      26,
    );
    headB.pushGeo('ivory', mandibleLipGeo);

    // Recessed dark throat core (without `.rotateX(Math.PI / 2)` so it stays inside the lower throat!)
    const jawCorePts = [
      new THREE.Vector3(-415, -24, 0),
      new THREE.Vector3(-330, -40, 8),
      new THREE.Vector3(-225, -56, 12),
      new THREE.Vector3(-135, -62, 10),
      new THREE.Vector3(-40, -52, 6),
    ];
    const jawCoreGeo = normalizeGeometryUVs(
      sweptProfileGeometry({
        points: jawCorePts,
        radiusAt: (u) => lerp(4, 16, Math.sin(u * Math.PI * 0.80)),
        scaleZAt: 2.6,
        tubularSeg: 28,
        radialSeg: 16,
      }),
      28,
    );
    headB.pushGeo('dark', jawCoreGeo);

    // 14 Bright White-Titanium & Satin-Silver Ventral Throat Pleats
    const pleatCount = 14;
    for (let p = 0; p < pleatCount; p++) {
      const f = p / (pleatCount - 1);
      const pts = [];
      const steps = 22;
      for (let s = 0; s <= steps; s++) {
        const u = s / steps;
        const x = lerp(-426, -22, u);
        const arch = Math.sin(u * Math.PI * 0.86);
        const yKeel = lerp(-24, -88, arch);
        const yRim = lerp(-21, -44, arch);
        const y = lerp(yKeel, yRim, Math.pow(f, 0.86)) - (1 - u) * 2;
        const zSpread = lerp(7, 74, arch) * Math.sin(f * Math.PI * 0.48 + 0.14);
        pts.push(new THREE.Vector3(x, y, zSpread));

        if (s > 1 && s < steps && s % 2 === 0) {
          headB.addPart(s % 4 === 0 ? 'brass' : 'dark', T.box, {
            x,
            y: y + 1.0,
            z: zSpread - 1.8,
            rz: 0.15,
            sx: 2.8,
            sy: 1.8,
            sz: 2.4,
          });
        }
      }
      const pleatGeo = normalizeGeometryUVs(
        sweptProfileGeometry({
          points: pts,
          radiusAt: (u) => lerp(2.5, 5.2, Math.sin(u * Math.PI * 0.85)),
          scaleZAt: 0.54,
          tubularSeg: 32,
          radialSeg: 12,
        }),
        24,
      );
      headB.pushGeo(p % 4 === 2 ? 'silver' : 'ivory', pleatGeo);
    }

    totalSubParts += headB.getPartCount();
    headB.flushTo(headGroup, matMap);
  }

  // ==========================================================================
  // B. 12-STATION OPEN-BAY SPINAL LINKAGE (PROUD CHAMPAGNE-BRASS ARCHES + CHROME PISTONS)
  // ==========================================================================
  const spineGroup = new THREE.Group();
  root.add(spineGroup);

  // 12 wide-spaced stations (`36` units apart!) so each bay has generous dark `#07090C` negative space
  // behind the gleaming Champagne-Brass C-rings and horizontal Mirror-Chrome hydraulic rods!
  const SPINE_COUNT = 12;
  const spineStations = [];
  const interLinks = [];

  for (let i = 0; i < SPINE_COUNT; i++) {
    const sFrac = i / (SPINE_COUNT - 1);
    const xBase = lerp(-86, 310, sFrac);
    const uEnv = (xBase - -430) / 775;
    const env = whaleEnvelope(uEnv);

    const station = new THREE.Group();
    station.position.set(xBase, env.centerY, 0);
    spineGroup.add(station);

    // Strictly 82% of envelope radius so the outer hull (104% envelope) has >= 14mm radial clearance!
    const rOuter = Math.min(env.halfW, env.dorsalH) * 0.82;
    // Compact inner core (`0.33 * rOuter`) so the outer 67% of the bay is wide-open dark mechanical space!
    const rCore = rOuter * 0.33;
    const stB = createBucketBuilder();

    // 1. Compact Deep Cavity Occlusion Core (`cavityBlack`) + Dark Gunmetal Pressure Cylinder
    stB.addPart('cavity', T.cyl, {
      x: 0,
      y: 0,
      z: 0,
      rz: Math.PI / 2,
      sx: rCore * 1.05,
      sy: 38,
      sz: rCore * 1.05,
    });

    // 2. Central Mirror-Chrome Spinal Drive Shaft & Copper Induction Coils
    stB.addPart('chrome', T.cyl, {
      x: 0,
      y: 0,
      z: 0,
      rz: Math.PI / 2,
      sx: rCore * 0.52,
      sy: 40,
      sz: rCore * 0.52,
    });
    for (const cxOff of [-10, 0, 10]) {
      stB.addPart(cxOff === 0 ? 'brass' : 'copper', T.cyl, {
        x: cxOff,
        y: 0,
        z: 0,
        rz: Math.PI / 2,
        sx: rCore * 1.22,
        sy: 4.2,
        sz: rCore * 1.22,
      });
    }

    // 3. Proud Compound Twin-Flange CNC Bulkhead C-Arch (`width = 5.4` out of `36` bay spacing!)
    const bulkheadGroup = new THREE.Group();
    station.add(bulkheadGroup);
    const ringB = createBucketBuilder();

    const ringWidth = lerp(5.8, 3.4, sFrac);
    const teethCount = Math.max(14, Math.round(lerp(24, 14, sFrac)));
    const mainGearGeo = gearGeometry({
      teeth: teethCount,
      rOut: rOuter * 0.94,
      rRoot: rOuter * 0.94 - lerp(3.2, 1.6, sFrac),
      width: ringWidth * 0.44,
      holeR: rOuter * 0.78,
      lighteningHoles: 12,
      lighteningR: Math.max(1.4, rOuter * 0.055),
    });
    mainGearGeo.rotateY(Math.PI / 2);
    ringB.pushGeo('dark', mainGearGeo);

    // Sculpted Near-Side Champagne-Brass & Brushed-Steel Twin-Flange C-Arch (`sa >= -0.18`)
    // Eliminates far-side ring criss-crossing so every rib station reads as a crisp `)` C-arch!
    const archSegs = 28;
    for (let k = 0; k < archSegs; k++) {
      const a = (k / archSegs) * Math.PI * 2;
      const ca = Math.cos(a);
      const sa = Math.sin(a);
      if (sa < -0.18) continue;
      const rArch = rOuter * 0.92;
      const segArcLen = (2 * Math.PI * rArch) / archSegs + 1.1;
      // Front flange (Champagne Brass)
      ringB.addPart('brass', T.box, {
        x: -ringWidth * 0.30,
        y: ca * rArch,
        z: sa * rArch,
        rx: a,
        sx: ringWidth * 0.46,
        sy: lerp(5.2, 3.0, sFrac),
        sz: segArcLen,
      });
      // Rear flange (Alternating Brushed Steel / Brass)
      ringB.addPart(i % 2 === 0 ? 'steel' : 'brass', T.box, {
        x: ringWidth * 0.30,
        y: ca * rArch,
        z: sa * rArch,
        rx: a,
        sx: ringWidth * 0.46,
        sy: lerp(4.8, 2.8, sFrac),
        sz: segArcLen,
      });
    }

    // 4. Crisp Radial Piston Spokes & Compact Clevis Lugs inside the Ring Plane (`x = 0`)
    const spokeCount = i < 8 ? 16 : 12;
    for (let s = 0; s < spokeCount; s++) {
      const a = (s / spokeCount) * Math.PI * 2;
      const ca = Math.cos(a);
      const sa = Math.sin(a);
      const isNear = sa >= -0.15;
      const rMid = (rOuter * 0.80 + rCore * 1.18) * 0.5;
      const spokeLen = rOuter * 0.80 - rCore * 1.18;

      ringB.addPart(isNear ? (s % 2 === 0 ? 'brass' : 'chrome') : 'dark', T.cyl, {
        x: 0,
        y: ca * rMid,
        z: sa * rMid,
        rx: a,
        sx: lerp(1.65, 1.0, sFrac),
        sy: spokeLen,
        sz: lerp(1.65, 1.0, sFrac),
      });

      if (isNear && s % 2 === 0) {
        ringB.addPart('copper', T.cyl, {
          x: 0,
          y: ca * (rMid * 0.88),
          z: sa * (rMid * 0.88),
          rx: a,
          sx: lerp(2.4, 1.3, sFrac),
          sy: spokeLen * 0.38,
          sz: lerp(2.4, 1.3, sFrac),
        });
      }

      // Compact clevis lug on the near-side C-arch so the ring looks like a precision CNC arch!
      if (isNear && s % 2 === 0) {
        const rLug = rOuter * 0.96;
        ringB.addPart(s % 4 === 0 ? 'brass' : 'steel', T.box, {
          x: 0,
          y: ca * rLug,
          z: sa * rLug,
          rx: a,
          sx: ringWidth * 1.15,
          sy: lerp(3.8, 2.2, sFrac),
          sz: lerp(3.0, 1.8, sFrac),
        });
        ringB.addPart('chrome', T.hex, {
          x: -ringWidth * 0.62,
          y: ca * (rOuter * 0.90),
          z: sa * (rOuter * 0.90),
          rz: Math.PI / 2,
          sx: lerp(1.2, 0.75, sFrac),
          sy: 1.6,
          sz: lerp(1.2, 0.75, sFrac),
        });
      }
    }

    totalSubParts += stB.getPartCount() + ringB.getPartCount();
    stB.flushTo(station, matMap);
    ringB.flushTo(bulkheadGroup, matMap);

    spineStations.push({
      index: i,
      sFrac,
      xBase,
      baseY: env.centerY,
      rOuter,
      rCore,
      group: station,
      bulkheadRing: bulkheadGroup,
    });
  }

  // 5. Sleek Longitudinal Mirror-Chrome Hydraulic Pistons & Brass Pushrods bridging the 12 stations
  const linkageGroup = new THREE.Group();
  spineGroup.add(linkageGroup);

  for (let i = 0; i < SPINE_COUNT - 1; i++) {
    const stA = spineStations[i];
    const stB = spineStations[i + 1];
    const segLen = Math.hypot(stB.xBase - stA.xBase, stB.baseY - stA.baseY);

    // 6 well-spaced angles in the cutaway window so each horizontal chrome/brass rod has dark space around it!
    const quadrantAngles = [0.24, 0.62, 1.00, 1.38, -0.35, -0.85];
    for (let q = 0; q < quadrantAngles.length; q++) {
      const ang = quadrantAngles[q];
      const radFactor = q % 2 === 0 ? 0.84 : 0.68;
      const rA = stA.rOuter * radFactor;
      const rB = stB.rOuter * radFactor;

      const linkHolder = new THREE.Group();
      linkageGroup.add(linkHolder);
      const lkB = createBucketBuilder();

      const scaleW = lerp(1.0, 0.48, stA.sFrac);
      // Outer cylinder barrel (brass or dark gunmetal) + long gleaming mirror-chrome piston rod
      lkB.addPart(q % 2 === 0 ? 'brass' : 'dark', T.cyl, {
        x: 0,
        y: -segLen * 0.24,
        z: 0,
        sx: 2.05 * scaleW,
        sy: segLen * 0.46,
        sz: 2.05 * scaleW,
      });
      lkB.addPart('chrome', T.cyl, {
        x: 0,
        y: segLen * 0.16,
        z: 0,
        sx: 1.35 * scaleW,
        sy: segLen * 0.68,
        sz: 1.35 * scaleW,
      });
      lkB.addPart('brass', T.hex, {
        x: 0,
        y: -segLen * 0.01,
        z: 0,
        sx: 2.5 * scaleW,
        sy: 2.8 * scaleW,
        sz: 2.5 * scaleW,
      });

      totalSubParts += lkB.getPartCount();
      lkB.flushTo(linkHolder, matMap);
      interLinks.push({ i, ang, rA, rB, segLen, mesh: linkHolder });
    }
  }

  // ==========================================================================
  // C. SCULPTED LONGITUDINAL HYDRODYNAMIC HULL FAIRINGS (`01 External Hull`)
  //    Matches `reference.jpg` 1:1 — Long, sweeping S-curve & diagonal-chevron sculpted fairings
  //    (ZERO vertical "barrel-ring" blocks, ZERO oversized shutters covering the circular Sonar Core!):
  //      1. Stepped Multi-Layer Forehead & Brow Cantilevered Cowling (`u = 0.12 .. 0.42`)
  //      2. Sculpted White-Titanium Swept Shoulder Wing Escutcheon (`u = 0.425 .. 0.565`, clears all 4 cranial rings!)
  //      3. Chevron-Segmented Longitudinal Dorsal Spine Carapace (`u = 0.465 .. 0.895`)
  //      4. Compound Diagonal-Seamed S-Curve Lower-Flank & Belly Hull (`u = 0.45 .. 0.83`)
  //      5. 3 Leaf-Tapered Lower-Peduncle Shrouds (`u = 0.56 .. 0.90`) with Articulated Inner Linkage Struts
  // ==========================================================================
  const armorGroup = new THREE.Group();
  root.add(armorGroup);
  const armorPanels = [];

  /**
   * Builds a continuous, sculpted hydrodynamic fairing with custom longitudinal S-curve boundaries
   * `a0At(fu)` and `a1At(fu)`, diagonal chevron seams (`chevronSplits` + `sweep`), perimeter clevis
   * greebles (`addEdgeGreebles`), and optional inner articulated linkage struts (`addInnerStruts`).
   */
  function addSculptedHydroFairing({
    u0,
    u1,
    a0At,
    a1At,
    sweepFront = 0.0,
    sweepRear = 0.0,
    taperFront = 0.0,
    taperRear = 0.0,
    thickness = 4.6,
    rScale = 1.045,
    matKey = 'ivory',
    trimMatKey = 'silver',
    hasTrimStripe = false,
    chevronSplits = null,
    addEdgeGreebles = false,
    addInnerStruts = false,
    explodeDir = [0, 1, 0],
    explodeDist = 58,
    cutawayLift = 0.0,
    cutawayRotX = 0.0,
    cutawayShift = [0, 0, 0],
    segU = 36,
    segA = 18,
  }) {
    const evalA0 = typeof a0At === 'function' ? a0At : () => a0At;
    const evalA1 = typeof a1At === 'function' ? a1At : () => a1At;

    const uMid = (u0 + u1) * 0.5;
    const baseEnv = whaleEnvelope(uMid);
    const pivotPos = new THREE.Vector3(baseEnv.x, baseEnv.centerY, 0);

    const panelHolder = new THREE.Group();
    panelHolder.position.copy(pivotPos);
    armorGroup.add(panelHolder);
    const pB = createBucketBuilder();

    const evalSurfacePoint = (fu, fa, rBase, dr = 0.0) => {
      let tipPinch = 1.0;
      if (taperFront > 0 && fu < 0.30) {
        tipPinch *= lerp(1.0 - taperFront, 1.0, smootherstep(0, 1, fu / 0.30));
      }
      if (taperRear > 0 && fu > 0.70) {
        tipPinch *= lerp(1.0 - taperRear, 1.0, smootherstep(0, 1, (1.0 - fu) / 0.30));
      }

      const rawA0 = evalA0(fu);
      const rawA1 = evalA1(fu);
      const aCenter = 0.5 * (rawA0 + rawA1);
      const aSpan = (rawA1 - rawA0) * tipPinch;
      const curA0 = aCenter - 0.5 * aSpan;
      const curA1 = aCenter + 0.5 * aSpan;
      const a = lerp(curA0, curA1, fa);

      // Diagonal chevron sweep + organic rounded end contour (never a vertical ring cut!)
      const endCurve = Math.sin(fa * Math.PI) * 0.010 * (u1 - u0);
      const sweepOff = lerp(sweepFront, sweepRear, fu) * (fa - 0.5);
      const u = clamp(lerp(u0, u1, fu) + sweepOff + (fu > 0.5 ? endCurve : -endCurve), 0.002, 0.995);

      const env = whaleEnvelope(u);
      const sinA = Math.sin(a);
      const cosA = Math.cos(a);
      const radY = cosA >= 0 ? env.dorsalH : env.ventralH;

      return {
        x: env.x - pivotPos.x,
        y: env.centerY + cosA * (radY * rBase + dr) - pivotPos.y,
        z: sinA * (env.halfW * rBase + dr) - pivotPos.z,
        a,
        env,
      };
    };

    const buildContouredPatch = (fuStart, fuEnd, faStart, faEnd, rBase, radThick, bevelEdge = 0.75, nU = segU, nA = segA) => {
      const positions = [];
      const indices = [];

      const evalVertex = (iu, ia, layer) => {
        const dr = layer === 0 ? radThick * 0.5 : -radThick * 0.5;
        const fuSub = iu / nU;
        const faSub = ia / nA;
        const fu = lerp(fuStart, fuEnd, fuSub);
        const fa = lerp(faStart, faEnd, faSub);
        const isEdge = iu === 0 || iu === nU || ia === 0 || ia === nA;
        const bevelDrop = layer === 0 && isEdge ? -bevelEdge : 0.0;
        const pt = evalSurfacePoint(fu, fa, rBase, dr + bevelDrop);
        return [pt.x, pt.y, pt.z];
      };

      for (let layer = 0; layer < 2; layer++) {
        for (let iu = 0; iu <= nU; iu++) {
          for (let ia = 0; ia <= nA; ia++) {
            const [vx, vy, vz] = evalVertex(iu, ia, layer);
            positions.push(vx, vy, vz);
          }
        }
      }
      const stride = nA + 1;
      const layerVerts = (nU + 1) * stride;
      for (let iu = 0; iu < nU; iu++) {
        for (let ia = 0; ia < nA; ia++) {
          const a = iu * stride + ia;
          const b = (iu + 1) * stride + ia;
          const c = (iu + 1) * stride + (ia + 1);
          const d = iu * stride + (ia + 1);
          indices.push(a, d, b, b, d, c);
          const a2 = layerVerts + a;
          const b2 = layerVerts + b;
          const c2 = layerVerts + c;
          const d2 = layerVerts + d;
          indices.push(a2, b2, d2, b2, c2, d2);
        }
      }

      const pushSideQuad = (p0, p1, p2, p3) => {
        const base = positions.length / 3;
        positions.push(...p0, ...p1, ...p2, ...p3);
        indices.push(base, base + 1, base + 3, base + 1, base + 2, base + 3);
      };
      for (let iu = 0; iu < nU; iu++) {
        pushSideQuad(evalVertex(iu, 0, 0), evalVertex(iu + 1, 0, 0), evalVertex(iu + 1, 0, 1), evalVertex(iu, 0, 1));
        pushSideQuad(evalVertex(iu + 1, nA, 0), evalVertex(iu, nA, 0), evalVertex(iu, nA, 1), evalVertex(iu + 1, nA, 1));
      }
      for (let ia = 0; ia < nA; ia++) {
        pushSideQuad(evalVertex(0, ia + 1, 0), evalVertex(0, ia, 0), evalVertex(0, ia, 1), evalVertex(0, ia + 1, 1));
        pushSideQuad(evalVertex(nU, ia, 0), evalVertex(nU, ia + 1, 0), evalVertex(nU, ia + 1, 1), evalVertex(nU, ia, 1));
      }

      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geo.setIndex(indices);
      geo.computeVertexNormals();
      normalizeGeometryUVs(geo, 28);
      return geo;
    };

    // 1. Recessed Dark Gunmetal Inner Gasket Liner (`#20242B`)
    const innerLinerGeo = buildContouredPatch(0.0, 1.0, 0.0, 1.0, rScale - 0.016, thickness * 0.58, 0.25, segU, segA);
    pB.pushGeo('dark', innerLinerGeo);

    // 2. Sculpted Outer White-Titanium & Satin-Silver Hydrodynamic Skin with Diagonal Chevron Seams
    const splits = chevronSplits || [0.008, 0.992];
    for (let sIdx = 0; sIdx < splits.length - 1; sIdx++) {
      const f0 = splits[sIdx] + (sIdx > 0 ? 0.005 : 0.0);
      const f1 = splits[sIdx + 1] - (sIdx < splits.length - 2 ? 0.005 : 0.0);
      const subU = Math.max(18, Math.round(segU * (f1 - f0)));
      const primaryMat = sIdx % 2 === 1 ? trimMatKey : matKey;
      const accentMat = sIdx % 2 === 1 ? matKey : trimMatKey;

      if (hasTrimStripe) {
        const mainSkin = buildContouredPatch(f0, f1, 0.02, 0.74, rScale + 0.008, thickness * 0.82, 0.85, subU, segA);
        pB.pushGeo(primaryMat, mainSkin);
        const trimSkin = buildContouredPatch(f0, f1, 0.76, 0.98, rScale + 0.005, thickness * 0.74, 0.75, subU, 8);
        pB.pushGeo(accentMat, trimSkin);
      } else {
        const skinGeo = buildContouredPatch(f0, f1, 0.02, 0.98, rScale + 0.008, thickness * 0.82, 0.85, subU, segA);
        pB.pushGeo(primaryMat, skinGeo);
      }
    }

    // 3. Perimeter Clevis Lugs, Countersunk Fastener Bosses & Micro Actuator Hinges along cutaway edges
    if (addEdgeGreebles) {
      const greebleFus = [0.16, 0.38, 0.62, 0.84];
      for (let gIdx = 0; gIdx < greebleFus.length; gIdx++) {
        const fuG = greebleFus[gIdx];
        const ptRim = evalSurfacePoint(fuG, 0.08, rScale, -thickness * 0.15);
        pB.addPart('dark', T.box, {
          x: ptRim.x,
          y: ptRim.y,
          z: ptRim.z,
          rx: -ptRim.a,
          sx: 6.4,
          sy: 3.2,
          sz: 4.2,
        });
        pB.addPart(gIdx % 2 === 0 ? 'brass' : 'chrome', T.cyl, {
          x: ptRim.x,
          y: ptRim.y,
          z: ptRim.z + 1.2,
          rz: Math.PI / 2,
          sx: 1.5,
          sy: 7.5,
          sz: 1.5,
        });
      }
    }

    // 4. Articulated Inner Linkage Struts for the 3 Floating Lower-Peduncle Shrouds (`reference.jpg` lower-right!)
    if (addInnerStruts) {
      for (const fuS of [0.28, 0.72]) {
        const ptOuter = evalSurfacePoint(fuS, 0.50, rScale, -thickness * 0.45);
        pB.addPart('dark', T.cyl, {
          x: ptOuter.x - 3.5,
          y: ptOuter.y + 8.5,
          z: ptOuter.z - 8.5,
          rx: 0.72,
          rz: -0.25,
          sx: 1.6,
          sy: 22.0,
          sz: 1.6,
        });
        pB.addPart('brass', T.cyl, {
          x: ptOuter.x - 1.8,
          y: ptOuter.y + 4.2,
          z: ptOuter.z - 4.2,
          rx: 0.72,
          rz: -0.25,
          sx: 2.3,
          sy: 8.5,
          sz: 2.3,
        });
      }
    }

    totalSubParts += pB.getPartCount();
    pB.flushTo(panelHolder, matMap);

    armorPanels.push({
      group: panelHolder,
      uMid,
      xPivot: baseEnv.x,
      pivotPos,
      explodeDir: new THREE.Vector3(...explodeDir).normalize(),
      explodeDist,
      cutawayLift,
      cutawayRotX,
      cutawayShift: new THREE.Vector3(...cutawayShift),
    });
  }

  // High-density braided hydraulic hose bundle (`braidedHoseBundle`) with hex brass crimp ferrules & red clamps
  // routing from the cranial sonar manifold through the open thoracic cavity into the spinal actuators
  const thoracicHoseBundle = braidedHoseBundle({
    routes: [
      [
        [-138, 12, 14],
        [-74, 8, 20],
        [12, 14, 18],
        [98, 22, 14],
      ],
      [
        [-138, 2, 18],
        [-72, -4, 24],
        [14, 4, 22],
        [98, 12, 16],
      ],
      [
        [-136, -10, 20],
        [-92, -20, 38],
        [-58, -24, 44],
      ],
    ],
    hoseRadius: 2.6,
    ferruleLen: 8.0,
    clampAt: [0.35, 0.72],
  });
  root.add(thoracicHoseBundle.group);

  // 1. Sculpted Cantilevered Cranial Brow & Forehead Cowling (`u = 0.21 .. 0.435`)
  //    Sits flush atop the upper rostrum & cranium right above the circular Sonar Core (zero floating umbrella gap!),
  //    sweeping back to a sharp cantilevered white-titanium & satin-silver aero-point above the cranial rings (`reference.jpg`).
  addSculptedHydroFairing({
    u0: 0.21,
    u1: 0.435,
    a0At: (fu) => lerp(-0.56, -0.34, fu),
    a1At: (fu) => {
      const sonarArch = Math.sin(clamp((fu - 0.12) / 0.72, 0, 1) * Math.PI) * 0.14;
      return lerp(0.36, 0.16, fu) - sonarArch;
    },
    sweepFront: -0.028,
    sweepRear: 0.042,
    taperFront: 0.48,
    taperRear: 0.80,
    thickness: 4.8,
    rScale: 0.992,
    matKey: 'ivory',
    trimMatKey: 'silver',
    hasTrimStripe: true,
    chevronSplits: [0.008, 0.48, 0.992],
    addEdgeGreebles: true,
    explodeDir: [-0.18, 0.95, 0.16],
    explodeDist: 68,
    cutawayLift: 0.0,
    cutawayShift: [0, 0, 0],
    segU: 34,
    segA: 16,
  });

  // 2. Sculpted White-Titanium Swept Shoulder Wing Escutcheon (`u = 0.425 .. 0.565`, `x = -100 .. +8`)
  //    Starts strictly behind the 4th cranial ring (`x = -108`) so ZERO rings clip into it, sweeping up-and-back
  //    over the anterior ribs above the pectoral shoulder gimbal (`reference.jpg` signature wing plate!).
  addSculptedHydroFairing({
    u0: 0.425,
    u1: 0.565,
    a0At: (fu) => lerp(0.08, 0.22, fu),
    a1At: (fu) => lerp(0.84, 0.30, Math.pow(fu, 0.76)),
    sweepFront: -0.022,
    sweepRear: 0.046,
    taperFront: 0.22,
    taperRear: 0.82,
    thickness: 5.2,
    rScale: 1.062,
    matKey: 'ivory',
    trimMatKey: 'silver',
    hasTrimStripe: true,
    addEdgeGreebles: true,
    explodeDir: [-0.08, 0.52, 0.85],
    explodeDist: 66,
    cutawayLift: 0.02,
    segU: 30,
    segA: 16,
  });

  // 3. Chevron-Segmented Longitudinal Dorsal Spine Carapace (`u = 0.455 .. 0.885`)
  //    Sits snugly atop the brass spinal ribs (`rScale = 1.026`, `a = -0.62 .. +0.34`) with 45-degree diagonal chevron seams!
  addSculptedHydroFairing({
    u0: 0.455,
    u1: 0.885,
    a0At: (fu) => lerp(-0.62, -0.44, fu),
    a1At: (fu) => lerp(0.34, 0.26, fu) + 0.05 * Math.sin(fu * Math.PI * 1.4),
    sweepFront: -0.036,
    sweepRear: 0.032,
    taperFront: 0.48,
    taperRear: 0.52,
    thickness: 4.8,
    rScale: 1.026,
    matKey: 'ivory',
    trimMatKey: 'silver',
    hasTrimStripe: true,
    chevronSplits: [0.008, 0.35, 0.68, 0.992],
    addEdgeGreebles: true,
    explodeDir: [0.08, 0.96, 0.14],
    explodeDist: 72,
    cutawayLift: 0.02,
    cutawayShift: [0, 1.5, 0],
    segU: 46,
    segA: 18,
  });

  // 4. Compound Diagonal-Seamed S-Curve Lower-Flank & Belly Hull (`u = 0.450 .. 0.830`, `reference.jpg` signature belly fairing!)
  //    Flows in an unbroken S-curve behind the pectoral shoulder down to the caudal peduncle with diagonal chevron seams!
  addSculptedHydroFairing({
    u0: 0.450,
    u1: 0.830,
    a0At: (fu) => {
      const sCurve = smootherstep(0.0, 1.0, fu);
      return lerp(1.22, 2.16, sCurve) - 0.12 * Math.sin(fu * Math.PI);
    },
    a1At: (fu) => lerp(2.84, 2.60, fu),
    sweepFront: -0.032,
    sweepRear: 0.042,
    taperFront: 0.18,
    taperRear: 0.72,
    thickness: 5.0,
    rScale: 1.050,
    matKey: 'ivory',
    trimMatKey: 'silver',
    hasTrimStripe: true,
    chevronSplits: [0.008, 0.42, 0.74, 0.992],
    addEdgeGreebles: true,
    explodeDir: [0.06, -0.78, 0.62],
    explodeDist: 64,
    cutawayLift: 0.03,
    segU: 46,
    segA: 18,
  });

  // 5. 3 Sleek Leaf-Tapered Lower-Peduncle Shrouds (`u = 0.56 .. 0.90`) with Articulated Inner Linkage Struts
  //    In Scene 1 (`cutaway = 0`), they sit flush against the lower-rear flank; in Scene 2 & 4 (`cutaway = 1`),
  //    they deploy outward/downward on twin hydraulic struts just like `reference.jpg` lower-right!
  const leafShrouds = [
    { u0: 0.56, u1: 0.70, a0: 1.36, a1: 1.96, expDist: 64, cutLift: 0.68, mat: 'ivory' },
    { u0: 0.68, u1: 0.81, a0: 1.32, a1: 1.90, expDist: 76, cutLift: 0.78, mat: 'silver' },
    { u0: 0.79, u1: 0.90, a0: 1.28, a1: 1.82, expDist: 86, cutLift: 0.88, mat: 'ivory' },
  ];
  for (const ls of leafShrouds) {
    addSculptedHydroFairing({
      u0: ls.u0,
      u1: ls.u1,
      a0At: (fu) => lerp(ls.a0, ls.a0 + 0.14, fu),
      a1At: (fu) => lerp(ls.a1, ls.a1 - 0.08, fu),
      sweepFront: -0.032,
      sweepRear: 0.036,
      taperFront: 0.74,
      taperRear: 0.80,
      thickness: 3.8,
      rScale: 1.062,
      matKey: ls.mat,
      trimMatKey: ls.mat === 'ivory' ? 'silver' : 'ivory',
      addInnerStruts: true,
      explodeDir: [0.26, -0.76, 0.58],
      explodeDist: ls.expDist,
      cutawayLift: ls.cutLift,
      segU: 24,
      segA: 12,
    });
  }

  // 6. Caudal Peduncle Tapered Tail-Stock Fairings (`u = 0.78 .. 0.965`, muscular mechanical tail-stock collar before flukes!)
  addSculptedHydroFairing({
    u0: 0.78,
    u1: 0.965,
    a0At: (fu) => lerp(-0.55, -0.45, fu),
    a1At: (fu) => lerp(0.58, 0.48, fu),
    sweepFront: -0.025,
    sweepRear: 0.025,
    taperFront: 0.45,
    taperRear: 0.55,
    thickness: 4.2,
    rScale: 1.06,
    matKey: 'silver',
    trimMatKey: 'ivory',
    hasTrimStripe: true,
    chevronSplits: [0.008, 0.52, 0.992],
    explodeDir: [0.35, 0.85, 0.25],
    explodeDist: 52,
    cutawayLift: 0.0,
    segU: 24,
    segA: 14,
  });
  addSculptedHydroFairing({
    u0: 0.80,
    u1: 0.965,
    a0At: (fu) => lerp(1.65, 1.55, fu),
    a1At: (fu) => lerp(2.75, 2.65, fu),
    sweepFront: -0.025,
    sweepRear: 0.025,
    taperFront: 0.45,
    taperRear: 0.55,
    thickness: 4.0,
    rScale: 1.06,
    matKey: 'ivory',
    trimMatKey: 'silver',
    hasTrimStripe: true,
    explodeDir: [0.35, -0.85, 0.25],
    explodeDist: 52,
    cutawayLift: 0.0,
    segU: 22,
    segA: 12,
  });

  // ==========================================================================
  // D. MULTI-AXIS PECTORAL FIN THRUSTERS (EXPOSED ACTUATOR ARM + BROAD HYDROFOIL)
  // ==========================================================================
  const pectoralFins = [];

  for (const side of [1, -1]) {
    const shoulderRoot = new THREE.Group();
    shoulderRoot.position.set(side > 0 ? -90 : -205, side > 0 ? -24 : -48, side * 64);
    if (side < 0) shoulderRoot.scale.setScalar(0.58);
    root.add(shoulderRoot);

    const gimbalHousing = add(
      shoulderRoot,
      counterboreBossGeometry({ rOuter: 23, rBore: 10, rCounter: 17, hTotal: 20, hCounter: 5, seg: 32 }),
      hullDark,
    );
    gimbalHousing.rotation.z = Math.PI / 2;

    const shoulderGear = add(
      shoulderRoot,
      gearGeometry({ teeth: 24, rOut: 21, rRoot: 17.5, width: 8, holeR: 9, lighteningHoles: 6, lighteningR: 3.0 }),
      goldBrass,
    );
    shoulderGear.rotation.x = Math.PI / 2;

    const finStage1 = new THREE.Group();
    finStage1.rotation.order = 'ZYX';
    shoulderRoot.add(finStage1);

    // Stage 1 (`x = 0 .. 84`): Exposed Cylindrical Multi-Piston Hydraulic Truss
    const armLen1 = 84;
    const f1B = createBucketBuilder();
    for (const [dy, dz, rBar, matK] of [
      [-6.5, -6.5, 3.2, 'chrome'],
      [6.5, -6.5, 3.2, 'brass'],
      [-6.5, 6.5, 3.2, 'brass'],
      [6.5, 6.5, 3.2, 'chrome'],
      [0, 0, 5.2, 'steel'],
    ]) {
      f1B.addPart(matK, T.cyl, {
        x: armLen1 * 0.5,
        y: dy,
        z: dz,
        rz: Math.PI / 2,
        sx: rBar,
        sy: armLen1 * 0.96,
        sz: rBar,
      });
      if (rBar < 4) {
        f1B.addPart('copper', T.cyl, {
          x: armLen1 * 0.30,
          y: dy,
          z: dz,
          rz: Math.PI / 2,
          sx: rBar * 1.42,
          sy: armLen1 * 0.36,
          sz: rBar * 1.42,
        });
      }
    }
    for (let fx = 10; fx <= 76; fx += 9.5) {
      f1B.addPart(fx % 19 === 10 ? 'brass' : 'dark', T.cyl, {
        x: fx,
        y: 0,
        z: 0,
        rz: Math.PI / 2,
        sx: 13.5,
        sy: 3.8,
        sz: 11.5,
      });
      for (let k = 0; k < 6; k++) {
        const a = (k / 6) * Math.PI * 2;
        f1B.addPart('chrome', T.hex, {
          x: fx,
          y: Math.cos(a) * 11.5,
          z: Math.sin(a) * 9.8,
          rz: Math.PI / 2,
          sx: 1.4,
          sy: 5.2,
          sz: 1.4,
        });
      }
    }
    totalSubParts += f1B.getPartCount();
    f1B.flushTo(finStage1, matMap);

    // Stage 2: Segmented Leading-Edge Slat Armor + Exposed Biomechatronic Skeleton (`reference.jpg` Pectoral Fin!)
    const finStage2 = new THREE.Group();
    finStage2.position.set(armLen1, 0, 0);
    finStage1.add(finStage2);

    const bladeLen2 = 152;
    const f2B = createBucketBuilder();

    // 1. Dark Gunmetal Internal Structural Frame & Trailing-Edge Fairing
    const bladeShape = new THREE.Shape();
    bladeShape.moveTo(-8, -28);
    bladeShape.quadraticCurveTo(32, -38, 74, -34);
    bladeShape.quadraticCurveTo(112, -32, 138, -18);
    bladeShape.quadraticCurveTo(148, -8, bladeLen2, 4);
    bladeShape.quadraticCurveTo(bladeLen2 + 2, 18, bladeLen2 - 16, 26);
    bladeShape.quadraticCurveTo(92, 34, 14, 28);
    bladeShape.quadraticCurveTo(-10, 18, -8, -28);

    const slotHole = new THREE.Path();
    slotHole.absellipse(56, 2, 48, 15.0, 0, Math.PI * 2, true, 0.02);
    bladeShape.holes.push(slotHole);

    const bladeGeo = normalizeGeometryUVs(
      new THREE.ExtrudeGeometry(bladeShape, {
        depth: 4.8,
        bevelEnabled: true,
        bevelThickness: 1.2,
        bevelSize: 1.2,
        bevelSegments: 2,
        curveSegments: 28,
      }),
      28,
    );
    bladeGeo.translate(0, 0, -2.4);
    f2B.pushGeo('silver', bladeGeo);

    // 2. 6 Sculpted White-Titanium & Satin-Silver Leading-Edge Slat Fairings (like `reference.jpg` armored fin tubercles!)
    const slatCount = 6;
    for (let sIdx = 0; sIdx < slatCount; sIdx++) {
      const f0 = sIdx / slatCount;
      const f1 = (sIdx + 0.86) / slatCount;
      const sx0 = lerp(-6, 136, f0);
      const sx1 = lerp(-6, 136, f1);
      const sy0 = lerp(-28, -16, Math.sin(f0 * Math.PI * 0.75));
      const sy1 = lerp(-28, -16, Math.sin(f1 * Math.PI * 0.75));
      const slatW = sx1 - sx0;
      pB_slat: {
        f2B.addPart(sIdx % 2 === 0 ? 'ivory' : 'silver', T.box, {
          x: (sx0 + sx1) * 0.5,
          y: (sy0 + sy1) * 0.5 - 3.5,
          z: 0,
          rz: Math.atan2(sy1 - sy0, slatW),
          sx: slatW,
          sy: 11.5 - sIdx * 0.6,
          sz: 8.2 - sIdx * 0.4,
        });
        f2B.addPart('dark', T.cyl, {
          x: sx0 + 2,
          y: sy0 + 1,
          z: 0,
          rz: Math.PI / 2,
          sx: 2.8,
          sy: 4.2,
          sz: 2.8,
        });
      }
    }

    // 3. Exposed Multi-Axis Internal Gold-Brass, Copper & Mirror-Chrome Hydraulic Truss inside the Fin Skeleton
    for (const [ryOff, rRod, matK] of [
      [-8, 2.4, 'chrome'],
      [0, 3.2, 'brass'],
      [8, 2.2, 'chrome'],
      [15, 1.8, 'copper'],
    ]) {
      f2B.addPart(matK, T.cyl, {
        x: 56,
        y: ryOff,
        z: 0,
        rz: Math.PI / 2,
        sx: rRod,
        sy: 112,
        sz: rRod,
      });
    }
    for (let bx = 4; bx <= 108; bx += 11.5) {
      f2B.addPart(bx % 23 < 10 ? 'brass' : 'dark', T.box, {
        x: bx,
        y: 3,
        z: 0,
        sx: 3.4,
        sy: 32,
        sz: 5.6,
      });
      f2B.addPart('copper', T.cyl, {
        x: bx + 5.5,
        y: -2,
        z: 2.2,
        rz: Math.PI / 2,
        sx: 2.6,
        sy: 7.5,
        sz: 2.6,
      });
      f2B.addPart('chrome', T.hex, {
        x: bx,
        y: -10,
        z: 3.2,
        sx: 1.8,
        sy: 2.0,
        sz: 1.8,
      });
    }

    totalSubParts += f2B.getPartCount();
    f2B.flushTo(finStage2, matMap);

    // Stage 3: Distal Articulated White-Titanium Wingtip
    const finStage3 = new THREE.Group();
    finStage3.position.set(bladeLen2 - 4, 4, 0);
    finStage2.add(finStage3);

    const tipPts = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(18, 2, side * 2),
      new THREE.Vector3(34, 5, side * 4),
    ];
    const tipGeo = normalizeGeometryUVs(
      sweptProfileGeometry({
        points: tipPts,
        radiusAt: (u) => lerp(13, 3.5, u),
        scaleZAt: 0.32,
        tubularSeg: 16,
        radialSeg: 14,
      }),
      24,
    );
    add(finStage3, tipGeo, hullIvory);

    pectoralFins.push({
      side,
      shoulderRoot,
      shoulderGear,
      finStage1,
      finStage2,
      finStage3,
    });
  }

  // ==========================================================================
  // E. TAIL ACTUATORS & GULL-WING HORIZONTAL CAUDAL FLUKES (`TAIL ACTUATORS`)
  // ==========================================================================
  const tailGroup = new THREE.Group();
  tailGroup.position.set(310, 34, 0);
  root.add(tailGroup);

  const tailGimbal = add(
    tailGroup,
    counterboreBossGeometry({ rOuter: 15, rBore: 6.5, rCounter: 11.5, hTotal: 20, hCounter: 4, seg: 28 }),
    goldBrass,
  );
  tailGimbal.rotation.z = Math.PI / 2;

  const flukeHub = new THREE.Group();
  flukeHub.position.set(14, 2, 0);
  tailGroup.add(flukeHub);

  for (const side of [-1, 1]) {
    const lobeGroup = new THREE.Group();
    lobeGroup.rotation.order = 'YZX';
    // Wide, sweeping horizontal gull-wing tail fluke posture matching `reference.jpg` top-right!
    // Left fluke (`side < 0`) sweeps wide toward upper-left (`-X, +Y, -Z`), right fluke (`side > 0`) sweeps toward upper-right (`+X, +Y, +Z`).
    if (side < 0) {
      lobeGroup.rotation.x = 0.28;
      lobeGroup.rotation.y = 0.78;
      lobeGroup.rotation.z = 0.14;
    } else {
      lobeGroup.rotation.x = -0.22;
      lobeGroup.rotation.y = -0.28;
      lobeGroup.rotation.z = 0.10;
    }
    flukeHub.add(lobeGroup);
    const flB = createBucketBuilder();

    const flukeShape = new THREE.Shape();
    flukeShape.moveTo(-10, 4);
    flukeShape.quadraticCurveTo(-4, 46, 16, 94);
    flukeShape.quadraticCurveTo(32, 128, 56, 144);
    flukeShape.quadraticCurveTo(68, 148, 62, 124);
    flukeShape.quadraticCurveTo(44, 84, 36, 40);
    flukeShape.quadraticCurveTo(28, 12, 14, 4);
    flukeShape.closePath();

    const flukeCutout = new THREE.Path();
    flukeCutout.absellipse(18, 60, 7.0, 30, 0, Math.PI * 2, true, -0.26);
    flukeShape.holes.push(flukeCutout);

    const flukeGeo = normalizeGeometryUVs(
      new THREE.ExtrudeGeometry(flukeShape, {
        depth: 4.6,
        bevelEnabled: true,
        bevelThickness: 1.2,
        bevelSize: 1.2,
        bevelSegments: 2,
        curveSegments: 24,
      }),
      28,
    );
    flukeGeo.rotateX(side > 0 ? Math.PI / 2 : -Math.PI / 2);
    flukeGeo.translate(0, side > 0 ? 2.3 : -2.3, 0);
    flukeGeo.computeVertexNormals();
    flB.pushGeo('silver', flukeGeo);

    const leadFlukeShape = new THREE.Shape();
    leadFlukeShape.moveTo(-10, 6);
    leadFlukeShape.quadraticCurveTo(-4, 46, 16, 94);
    leadFlukeShape.quadraticCurveTo(32, 128, 56, 144);
    leadFlukeShape.lineTo(46, 126);
    leadFlukeShape.quadraticCurveTo(22, 82, 4, 6);
    leadFlukeShape.closePath();
    const leadFlukeGeo = normalizeGeometryUVs(
      new THREE.ExtrudeGeometry(leadFlukeShape, {
        depth: 5.4,
        bevelEnabled: true,
        bevelThickness: 1.1,
        bevelSize: 1.1,
        bevelSegments: 2,
      }),
      28,
    );
    leadFlukeGeo.rotateX(side > 0 ? Math.PI / 2 : -Math.PI / 2);
    leadFlukeGeo.translate(0, side > 0 ? 2.7 : -2.7, 0);
    leadFlukeGeo.computeVertexNormals();
    flB.pushGeo('ivory', leadFlukeGeo);

    const pRoot = new THREE.Vector3(4, 0, side * 8);
    const pTip = new THREE.Vector3(40, 0, side * 116);
    flB.addStrut('brass', T.cyl, pRoot, pTip, 3.0);
    flB.addStrut('chrome', T.cyl, new THREE.Vector3(12, 1.5, side * 10), new THREE.Vector3(44, 1.5, side * 110), 1.9);

    for (let fz = 16; fz <= 118; fz += 11) {
      const fx = lerp(4, 44, fz / 128);
      flB.addPart(fz % 22 === 16 ? 'brass' : 'dark', T.box, { x: fx, y: 0, z: side * fz, sx: 11, sy: 5.4, sz: 2.8 });
      flB.addPart('chrome', T.hex, { x: fx, y: 3.2, z: side * fz, sx: 1.2, sy: 1.5, sz: 1.2 });
    }

    totalSubParts += flB.getPartCount();
    flB.flushTo(lobeGroup, matMap);
  }

  console.log(`[SUBJECT_0017] Built v5 heavy-metal & white-titanium mechanical whale with ${totalSubParts} procedural 3D sub-parts.`);

  // ==========================================================================
  // F. REAL-TIME KINEMATICS & EXPLODE / CUTAWAY UPDATE
  // ==========================================================================
  const anchors = {
    sonar: new THREE.Vector3(),
    spine: new THREE.Vector3(),
    pectoral: new THREE.Vector3(),
    tail: new THREE.Vector3(),
  };

  function update(t = 0, ops = {}) {
    const cutOpen = clamp(ops.cutaway ?? 1.0, 0, 1);
    const explode = clamp(ops.explode ?? 0.45, 0, 1);
    const swimSpeed = ops.swimSpeed ?? 2.3;

    const sonarPulse = 0.5 + 0.5 * Math.sin(t * 5.2);
    sonarMat.uniforms.uTime.value = t;
    sonarMat.uniforms.uPulse.value = sonarPulse;
    sonarHalo.scale.setScalar(1.0 + 0.04 * sonarPulse);
    sonarLight.intensity = 1.6 + 0.6 * sonarPulse;
    geodesicCage.rotation.y = t * 0.30;
    geodesicCage.rotation.z = Math.sin(t * 0.65) * 0.12;

    const headKin = evalSpineKinematics(-196, t, swimSpeed);
    headGroup.position.x = -explode * 42;
    headGroup.position.y = headKin.dy;
    headGroup.position.z = headKin.dz;
    headGroup.rotation.set(headKin.rollX, headKin.yawY, headKin.pitchZ);

    thoracicHoseBundle.group.position.set(0, headKin.dy * 0.7 + explode * 8, explode * 22);

    for (let i = 0; i < SPINE_COUNT; i++) {
      const st = spineStations[i];
      const kin = evalSpineKinematics(st.xBase, t, swimSpeed);
      st.group.position.set(st.xBase + (st.sFrac - 0.35) * explode * 28, st.baseY + kin.dy, kin.dz);
      st.group.rotation.set(kin.rollX, kin.yawY, kin.pitchZ);
      st.bulkheadRing.rotation.x = Math.sin(t * 2.2 + i * 0.45) * 0.04;
    }

    for (const lk of interLinks) {
      const stA = spineStations[lk.i];
      const stB = spineStations[lk.i + 1];
      const yA = stA.group.position.y + Math.cos(lk.ang) * lk.rA;
      const zA = stA.group.position.z + Math.sin(lk.ang) * lk.rA;
      const yB = stB.group.position.y + Math.cos(lk.ang) * lk.rB;
      const zB = stB.group.position.z + Math.sin(lk.ang) * lk.rB;

      const midX = (stA.group.position.x + stB.group.position.x) * 0.5;
      const midY = (yA + yB) * 0.5;
      const midZ = (zA + zB) * 0.5;
      lk.mesh.position.set(midX, midY, midZ);

      const dx = stB.group.position.x - stA.group.position.x;
      const dy = yB - yA;
      const dz = zB - zA;
      lk.mesh.rotation.set(0, -Math.atan2(dz, dx), Math.atan2(dy, dx) - Math.PI / 2);
    }

    const lastSpine = spineStations[SPINE_COUNT - 1];
    const tailKin = evalSpineKinematics(310, t, swimSpeed);
    tailGroup.position.set(310 + explode * 52, lastSpine.group.position.y + 4, lastSpine.group.position.z * 1.02);
    tailGroup.rotation.z = 0.12 + tailKin.pitchZ * 1.45;
    tailGroup.rotation.y = tailKin.yawY * 1.25;
    flukeHub.rotation.z = Math.sin(t * swimSpeed - 4.2) * 0.10;

    const shoulderKin = evalSpineKinematics(-90, t, swimSpeed);
    for (const pf of pectoralFins) {
      const side = pf.side;
      const finPhase = t * swimSpeed - 0.65;
      pf.shoulderGear.rotation.z = t * 1.2 * side;

      if (side > 0) {
        pf.shoulderRoot.position.set(-90 - explode * 14, -26 + shoulderKin.dy - explode * 18, side * (68 + explode * 48));
        pf.finStage1.rotation.z = -0.52 + Math.sin(finPhase) * 0.05;
        pf.finStage1.rotation.y = -0.18 + Math.cos(finPhase) * 0.04;
        pf.finStage1.rotation.x = 0.22 + Math.sin(finPhase - 0.3) * 0.05;
      } else {
        pf.shoulderRoot.position.set(-205 - explode * 14, -48 + headKin.dy - explode * 14, side * (66 + explode * 40));
        pf.finStage1.rotation.z = -0.44 + Math.sin(finPhase) * 0.05;
        pf.finStage1.rotation.y = -0.88 + Math.cos(finPhase) * 0.04;
        pf.finStage1.rotation.x = -0.25 + Math.sin(finPhase - 0.3) * 0.05;
      }

      // Telescopic stage separation along the hydrofoil blade axis during teardown (`explode`)
      pf.finStage2.position.x = 84 + explode * 28;
      pf.finStage3.position.x = 148 + explode * 26;

      pf.finStage2.rotation.z = Math.sin(finPhase - 0.65) * 0.06;
      pf.finStage2.rotation.y = -side * Math.cos(finPhase - 0.65) * 0.04;
      pf.finStage3.rotation.z = Math.sin(finPhase - 1.1) * 0.09;
    }

    // Locked Spine-Wave Tracking + Staged Cutaway / Explode Deployment for Sculpted Hydrodynamic Fairings!
    for (const ap of armorPanels) {
      const kin = evalSpineKinematics(ap.xPivot, t, swimSpeed);
      const axialExplodeX = (ap.uMid - 0.36) * explode * 28;
      const d = (ap.cutawayLift * cutOpen * 0.52 + explode * (0.78 + ap.cutawayLift * 0.28)) * ap.explodeDist;
      ap.group.position.set(
        ap.pivotPos.x + axialExplodeX + ap.cutawayShift.x * cutOpen + ap.explodeDir.x * d,
        ap.pivotPos.y + kin.dy + ap.cutawayShift.y * cutOpen + ap.explodeDir.y * d,
        ap.pivotPos.z + kin.dz + ap.cutawayShift.z * cutOpen + ap.explodeDir.z * d,
      );
      ap.group.rotation.set(kin.rollX + ap.cutawayRotX * cutOpen, kin.yawY, kin.pitchZ);
    }

    root.updateMatrixWorld(true);
    anchors.sonar.set(-182, 48 + headGroup.position.y, 24).applyMatrix4(root.matrixWorld);
    const midSpine = spineStations[5].group;
    anchors.spine.set(midSpine.position.x, midSpine.position.y + 56, 18).applyMatrix4(root.matrixWorld);
    anchors.pectoral.set(62, -92, 134).applyMatrix4(root.matrixWorld);
    anchors.tail.set(330, tailGroup.position.y - 4, 24).applyMatrix4(root.matrixWorld);
  }

  update(0, { cutaway: 1.0, explode: 0.45, swimSpeed: 2.3 });

  return {
    root,
    update,
    anchors,
    parts: {
      headGroup,
      sonarAnchor,
      spineGroup,
      tailGroup,
      pectoralNear: pectoralFins[0].shoulderRoot,
    },
  };
}

// ============================================================================
// 4. ARCHITECTURAL BIOMECHATRONICS BLUEPRINT HUD (`reference.jpg` 1:1 Layout)
// ============================================================================

const MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace';
const SANS = 'Inter, "Noto Sans CJK SC", system-ui, -apple-system, sans-serif';

export function createWhaleBlueprintHud({ camera, width, height }) {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(2, Math.round(width));
  canvas.height = Math.max(2, Math.round(height));
  const ctx = canvas.getContext('2d');

  const tex = new THREE.CanvasTexture(canvas);
  tex.encoding = THREE.sRGBEncoding;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;

  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    toneMapped: false,
  });
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

  const tmpV = new THREE.Vector3();
  function projectToScreen(worldVec, W, H) {
    tmpV.copy(worldVec).project(camera);
    return {
      x: (tmpV.x * 0.5 + 0.5) * W,
      y: (-tmpV.y * 0.5 + 0.5) * H,
    };
  }

  function drawScaleSilhouette(ctx, x, y, w, h, u) {
    ctx.save();
    ctx.fillStyle = 'rgba(118, 122, 126, 0.58)';
    ctx.beginPath();
    ctx.moveTo(x + w * 0.08, y + h * 0.46);
    ctx.bezierCurveTo(x + w * 0.22, y + h * 0.18, x + w * 0.48, y + h * 0.14, x + w * 0.66, y + h * 0.28);
    ctx.bezierCurveTo(x + w * 0.80, y + h * 0.36, x + w * 0.90, y + h * 0.38, x + w * 0.98, y + h * 0.24);
    ctx.lineTo(x + w * 0.94, y + h * 0.44);
    ctx.bezierCurveTo(x + w * 0.80, y + h * 0.46, x + w * 0.65, y + h * 0.54, x + w * 0.52, y + h * 0.62);
    ctx.lineTo(x + w * 0.44, y + h * 0.88);
    ctx.lineTo(x + w * 0.36, y + h * 0.62);
    ctx.bezierCurveTo(x + w * 0.22, y + h * 0.64, x + w * 0.12, y + h * 0.56, x + w * 0.08, y + h * 0.46);
    ctx.closePath();
    ctx.fill();

    const hx = x + 6 * u;
    const hy = y + h * 0.58;
    ctx.fillStyle = 'rgba(72, 76, 82, 0.82)';
    ctx.beginPath();
    ctx.arc(hx, hy - 12 * u, 2.2 * u, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillRect(hx - 1.8 * u, hy - 9 * u, 3.6 * u, 9 * u);

    const dy = y + h * 0.88;
    ctx.strokeStyle = 'rgba(90, 94, 100, 0.55)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, dy - 18 * u);
    ctx.lineTo(x, dy + 6 * u);
    ctx.moveTo(x + w, dy - 38 * u);
    ctx.lineTo(x + w, dy + 6 * u);
    ctx.moveTo(x, dy);
    ctx.lineTo(x + w * 0.40, dy);
    ctx.moveTo(x + w * 0.60, dy);
    ctx.lineTo(x + w, dy);
    ctx.stroke();

    ctx.fillStyle = '#4B4F56';
    ctx.font = `500 ${Math.round(11 * u)}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.fillText('24.8 m', x + w * 0.5, dy + 3.5 * u);
    ctx.textAlign = 'left';
    ctx.restore();
  }

  function drawSonarDetailInset(ctx, x, y, size, t, u) {
    ctx.save();
    ctx.fillStyle = '#181614';
    ctx.fillRect(x, y, size, size);
    ctx.strokeStyle = '#8C867B';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(x + 0.5, y + 0.5, size - 1, size - 1);

    const cx = x + size * 0.5;
    const cy = y + size * 0.5;
    const rOuter = size * 0.44;
    const rCore = size * 0.31;

    ctx.strokeStyle = '#A89F91';
    ctx.lineWidth = 5 * u;
    ctx.beginPath();
    ctx.arc(cx, cy, rOuter, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = '#C89B54';
    ctx.lineWidth = 2.2 * u;
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * Math.PI * 2 + t * 0.15;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * (rCore + 2 * u), cy + Math.sin(a) * (rCore + 2 * u));
      ctx.lineTo(cx + Math.cos(a) * (rOuter - 2 * u), cy + Math.sin(a) * (rOuter - 2 * u));
      ctx.stroke();
    }

    const pulse = 0.5 + 0.5 * Math.sin(t * 5.2);
    const grad = ctx.createRadialGradient(cx, cy, 2 * u, cx, cy, rCore);
    grad.addColorStop(0.0, '#FFFDF0');
    grad.addColorStop(0.22, '#FFB838');
    grad.addColorStop(0.62, '#EE520E');
    grad.addColorStop(0.92, '#6E1C04');
    grad.addColorStop(1.0, '#1C1410');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, rCore, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = `rgba(255, 224, 150, ${0.48 + 0.22 * pulse})`;
    ctx.lineWidth = 0.9 * u;
    for (let k = 0; k < 6; k++) {
      const a = (k * Math.PI) / 6 + t * 0.25;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rCore * 0.92, rCore * 0.36, a, 0, Math.PI * 2);
      ctx.stroke();
    }

    const tx = x + size + 16 * u;
    ctx.fillStyle = '#26292E';
    ctx.font = `700 ${Math.round(12.5 * u)}px ${SANS}`;
    ctx.fillText('SONAR CORE', tx, y + 22 * u);
    ctx.fillText('DETAIL', tx, y + 38 * u);

    ctx.fillStyle = '#555A62';
    ctx.font = `500 ${Math.round(11.5 * u)}px ${MONO}`;
    ctx.fillText('Diameter : 2.3 m', tx, y + 68 * u);
    ctx.fillText('Output   : 240 dB', tx, y + 86 * u);
    ctx.fillText('Material : Titanium Alloy', tx, y + 104 * u);
    ctx.restore();
  }

  function drawSideOrthographic(ctx, x, y, w, h, t, u) {
    ctx.save();
    ctx.strokeStyle = 'rgba(72, 76, 82, 0.65)';
    ctx.lineWidth = 1;
    const topY = y + 8 * u;
    ctx.beginPath();
    ctx.moveTo(x, topY);
    ctx.lineTo(x + w * 0.42, topY);
    ctx.moveTo(x + w * 0.58, topY);
    ctx.lineTo(x + w, topY);
    ctx.moveTo(x, topY - 4 * u);
    ctx.lineTo(x, y + h);
    ctx.moveTo(x + w, topY - 4 * u);
    ctx.lineTo(x + w, y + h);
    ctx.stroke();

    ctx.fillStyle = '#2B2F36';
    ctx.font = `600 ${Math.round(11.5 * u)}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.fillText('24.8 m', x + w * 0.5, topY + 4 * u);

    const lx = x - 18 * u;
    const vy0 = y + 22 * u;
    const vy1 = y + h - 6 * u;
    ctx.beginPath();
    ctx.moveTo(lx, vy0);
    ctx.lineTo(lx, (vy0 + vy1) * 0.5 - 14 * u);
    ctx.moveTo(lx, (vy0 + vy1) * 0.5 + 14 * u);
    ctx.lineTo(lx, vy1);
    ctx.moveTo(lx - 4 * u, vy0);
    ctx.lineTo(x + w, vy0);
    ctx.moveTo(lx - 4 * u, vy1);
    ctx.lineTo(x + w, vy1);
    ctx.stroke();

    ctx.save();
    ctx.translate(lx - 4 * u, (vy0 + vy1) * 0.5);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('6.2 m', 0, 0);
    ctx.restore();
    ctx.textAlign = 'left';

    const cy = (vy0 + vy1) * 0.5;
    const bh = (vy1 - vy0) * 0.42;

    ctx.strokeStyle = '#3A3E45';
    ctx.lineWidth = 1.3 * u;
    ctx.beginPath();
    ctx.moveTo(x + w * 0.03, cy + bh * 0.08);
    ctx.bezierCurveTo(x + w * 0.16, cy - bh * 0.86, x + w * 0.44, cy - bh * 0.92, x + w * 0.68, cy - bh * 0.35);
    ctx.bezierCurveTo(x + w * 0.82, cy - bh * 0.10, x + w * 0.90, cy - bh * 0.12, x + w * 0.97, cy - bh * 0.52);
    ctx.lineTo(x + w * 0.94, cy + bh * 0.06);
    ctx.bezierCurveTo(x + w * 0.80, cy + bh * 0.14, x + w * 0.62, cy + bh * 0.58, x + w * 0.42, cy + bh * 0.72);
    ctx.bezierCurveTo(x + w * 0.22, cy + bh * 0.82, x + w * 0.08, cy + bh * 0.48, x + w * 0.03, cy + bh * 0.08);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(218, 92, 32, 0.75)';
    ctx.beginPath();
    ctx.arc(x + w * 0.22, cy - bh * 0.06, bh * 0.38, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(70, 75, 82, 0.45)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 16; i++) {
      const f = 0.28 + (i / 15) * 0.58;
      const rx = x + w * f;
      const rh = bh * lerp(0.68, 0.16, i / 15);
      const waveY = Math.sin(t * 2.3 - i * 0.3) * 2.5 * u;
      ctx.beginPath();
      ctx.moveTo(rx, cy - rh + waveY);
      ctx.lineTo(rx, cy + rh * 0.85 + waveY);
      ctx.stroke();
    }

    ctx.strokeStyle = '#3A3E45';
    ctx.lineWidth = 1.1 * u;
    ctx.beginPath();
    ctx.moveTo(x + w * 0.34, cy + bh * 0.22);
    ctx.lineTo(x + w * 0.48, cy + bh * 0.95);
    ctx.lineTo(x + w * 0.54, cy + bh * 0.82);
    ctx.lineTo(x + w * 0.42, cy + bh * 0.18);
    ctx.stroke();
    ctx.restore();
  }

  function drawStructuralOverview(ctx, x, y, w, h, u) {
    ctx.save();
    ctx.fillStyle = '#23262B';
    ctx.font = `700 ${Math.round(13 * u)}px ${SANS}`;
    ctx.fillText('STRUCTURAL OVERVIEW', x, y + 18 * u);

    const items = [
      ['01', 'External Hull'],
      ['02', 'Pressure Chamber'],
      ['03', 'Power Core'],
      ['04', 'Movement Engine'],
      ['05', 'Sensory Array'],
      ['06', 'Stabilization Fin'],
    ];
    ctx.font = `500 ${Math.round(11.5 * u)}px ${MONO}`;
    items.forEach(([num, label], idx) => {
      const iy = y + (40 + idx * 17.5) * u;
      ctx.fillStyle = idx === 2 ? '#DF5A20' : '#6A7078';
      ctx.fillText(num, x, iy);
      ctx.fillStyle = '#383C42';
      ctx.fillText(label, x + 26 * u, iy);
    });

    const cx1 = x + 215 * u;
    const cy1 = y + 86 * u;
    ctx.strokeStyle = '#454950';
    ctx.lineWidth = 1.15 * u;
    ctx.beginPath();
    ctx.arc(cx1, cy1, 24 * u, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx1, cy1 - 2 * u, 11 * u, 0, Math.PI * 2);
    ctx.stroke();
    for (const sx of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(cx1 + sx * 22 * u, cy1 + 6 * u);
      ctx.quadraticCurveTo(cx1 + sx * 48 * u, cy1 + 18 * u, cx1 + sx * 56 * u, cy1 + 34 * u);
      ctx.quadraticCurveTo(cx1 + sx * 38 * u, cy1 + 26 * u, cx1 + sx * 18 * u, cy1 + 14 * u);
      ctx.stroke();
    }

    const cx2 = x + 365 * u;
    const cy2 = y + 86 * u;
    const dw = 155 * u;
    ctx.beginPath();
    ctx.moveTo(cx2 - dw * 0.48, cy2);
    ctx.bezierCurveTo(cx2 - dw * 0.30, cy2 - 22 * u, cx2 + dw * 0.05, cy2 - 20 * u, cx2 + dw * 0.38, cy2 - 3 * u);
    ctx.lineTo(cx2 + dw * 0.48, cy2 - 22 * u);
    ctx.lineTo(cx2 + dw * 0.44, cy2);
    ctx.lineTo(cx2 + dw * 0.48, cy2 + 22 * u);
    ctx.lineTo(cx2 + dw * 0.38, cy2 + 3 * u);
    ctx.bezierCurveTo(cx2 + dw * 0.05, cy2 + 20 * u, cx2 - dw * 0.30, cy2 + 22 * u, cx2 - dw * 0.48, cy2);
    ctx.stroke();
    for (const sy of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(cx2 - dw * 0.16, cy2 + sy * 16 * u);
      ctx.lineTo(cx2 + dw * 0.04, cy2 + sy * 44 * u);
      ctx.lineTo(cx2 + dw * 0.10, cy2 + sy * 38 * u);
      ctx.lineTo(cx2 - dw * 0.06, cy2 + sy * 15 * u);
      ctx.stroke();
    }
    ctx.restore();
  }

  function draw(state = {}) {
    const W = canvas.width;
    const H = canvas.height;
    const t = state.t ?? 0;
    const anchors = state.anchors;
    const u = Math.min(W, H) / 1080;

    ctx.clearRect(0, 0, W, H);
    ctx.textBaseline = 'alphabetic';

    ctx.strokeStyle = 'rgba(135, 130, 120, 0.22)';
    ctx.lineWidth = 1;
    const vLines = [0.245, 0.475, 0.875];
    for (const vx of vLines) {
      const px = Math.round(W * vx) + 0.5;
      ctx.beginPath();
      ctx.moveTo(px, 28 * u);
      ctx.lineTo(px, H - 28 * u);
      ctx.stroke();
    }
    const footerTopY = Math.round(H - 186 * u) + 0.5;
    ctx.beginPath();
    ctx.moveTo(36 * u, footerTopY);
    ctx.lineTo(W - 36 * u, footerTopY);
    ctx.stroke();

    const chX = Math.round(W * 0.305) + 0.5;
    const chY = Math.round(H * 0.082) + 0.5;
    ctx.strokeStyle = 'rgba(70, 74, 80, 0.55)';
    ctx.beginPath();
    ctx.moveTo(chX - 18 * u, chY);
    ctx.lineTo(chX + 38 * u, chY);
    ctx.moveTo(chX, chY - 32 * u);
    ctx.lineTo(chX, chY + 18 * u);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(chX, chY, 3.5 * u, 0, Math.PI * 2);
    ctx.stroke();

    const leftX = Math.round(44 * u);
    ctx.fillStyle = '#23252A';
    ctx.font = `600 ${Math.round(36 * u)}px ${SANS}`;
    ctx.fillText('MECHANICAL', leftX, Math.round(74 * u));
    ctx.fillText('HUMPBACK WHALE', leftX, Math.round(115 * u));

    ctx.font = `600 ${Math.round(15 * u)}px ${MONO}`;
    ctx.fillStyle = '#3A3E45';
    ctx.fillText('SUBJECT_0017', leftX, Math.round(145 * u));
    ctx.strokeStyle = '#5A5E66';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(leftX, Math.round(151 * u) + 0.5);
    ctx.lineTo(leftX + Math.round(118 * u), Math.round(151 * u) + 0.5);
    ctx.stroke();

    const specs = [
      ['LENGTH', ': 24.8 m'],
      ['WEIGHT', ': 142 t'],
      ['RANGE', ': 8,000 km'],
      ['DEPTH', ': 3,500 m'],
    ];
    ctx.font = `500 ${Math.round(13.5 * u)}px ${MONO}`;
    specs.forEach(([k, v], i) => {
      const sy = Math.round((186 + i * 21) * u);
      ctx.fillStyle = '#555A62';
      ctx.fillText(k, leftX, sy);
      ctx.fillStyle = '#23252A';
      ctx.fillText(v, leftX + Math.round(64 * u), sy);
    });

    drawScaleSilhouette(ctx, leftX, Math.round(284 * u), Math.round(295 * u), Math.round(92 * u), u);

    const oscX = Math.round(W * 0.438);
    const oscY = Math.round(52 * u);
    const oscW = Math.round(256 * u);
    const oscH = Math.round(84 * u);

    ctx.fillStyle = '#2B2E34';
    ctx.font = `700 ${Math.round(13 * u)}px ${SANS}`;
    ctx.fillText('ACOUSTIC SIGNAL', oscX, oscY);

    const midOscY = oscY + Math.round(48 * u);
    ctx.strokeStyle = 'rgba(130, 126, 118, 0.36)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(oscX, midOscY);
    ctx.lineTo(oscX + oscW, midOscY);
    for (let g = 0; g <= 8; g++) {
      const gx = oscX + (oscW * g) / 8;
      ctx.moveTo(gx, oscY + 14 * u);
      ctx.lineTo(gx, oscY + oscH);
    }
    ctx.stroke();

    ctx.strokeStyle = '#E05A2B';
    ctx.lineWidth = 1.65 * u;
    ctx.beginPath();
    const samples = 130;
    for (let i = 0; i <= samples; i++) {
      const f = i / samples;
      const px = oscX + f * oscW;
      const env1 = Math.exp(-Math.pow((f - 0.24) / 0.14, 2));
      const env2 = 0.55 * Math.exp(-Math.pow((f - 0.52) / 0.18, 2));
      const carrier =
        Math.sin(f * 92 - t * 14.0) * 0.65 +
        Math.cos(f * 148 + t * 9.5) * 0.35;
      const py = midOscY - carrier * (env1 + env2) * 34 * u;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();

    const arX = oscX + oscW + Math.round(18 * u);
    const freqVal = (12.4 + Math.sin(t * 3.1) * 0.1).toFixed(1);
    const amplVal = (87.6 + Math.cos(t * 4.3) * 0.4).toFixed(1);
    ctx.font = `500 ${Math.round(11.5 * u)}px ${MONO}`;
    ctx.fillStyle = '#555A62';
    ctx.fillText(`FREQ  : ${freqVal} kHz`, arX, oscY + Math.round(34 * u));
    ctx.fillText(`AMPL  : ${amplVal} dB`, arX, oscY + Math.round(52 * u));
    ctx.fillText(`RANGE : 12.5 km`, arX, oscY + Math.round(70 * u));

    const rightX = Math.round(W * 0.865);
    ctx.font = `500 ${Math.round(11.5 * u)}px ${MONO}`;
    ctx.fillStyle = '#4A4E55';
    ctx.fillText('AQUATIC BIOMECHATRONICS LAB', rightX, Math.round(48 * u));
    ctx.fillText('TYPE : LEVIATHAN-CLASS', rightX, Math.round(66 * u));
    ctx.fillText(`REV  : 3.7.4`, rightX, Math.round(84 * u));

    if (anchors) {
      const pSonar = projectToScreen(anchors.sonar, W, H);
      const pSpine = projectToScreen(anchors.spine, W, H);
      const pPectoral = projectToScreen(anchors.pectoral, W, H);
      const pTail = projectToScreen(anchors.tail, W, H);

      const callouts = [
        {
          pt: { x: clamp(pSonar.x, W * 0.22, W * 0.29), y: clamp(pSonar.y, H * 0.34, H * 0.46) },
          elbow: { x: clamp(pSonar.x, W * 0.22, W * 0.29), y: H * 0.205 },
          labelPos: { x: W * 0.272, y: H * 0.205 },
          title: 'PHASED-ARRAY',
          title2: 'SONAR CORE',
          sub: 'Multi-directional',
          sub2: 'acoustic sensing.',
        },
        {
          pt: { x: clamp(pSpine.x, W * 0.45, W * 0.53), y: clamp(pSpine.y, H * 0.28, H * 0.40) },
          elbow: { x: clamp(pSpine.x, W * 0.45, W * 0.53), y: H * 0.205 },
          labelPos: { x: W * 0.495, y: H * 0.205 },
          title: 'SPINAL LINKAGE',
          title2: '',
          sub: 'Adaptive flex system.',
          sub2: '',
        },
        {
          pt: { x: clamp(pPectoral.x, W * 0.52, W * 0.64), y: clamp(pPectoral.y, H * 0.60, H * 0.68) },
          elbow: { x: W * 0.720, y: clamp(pPectoral.y, H * 0.60, H * 0.68) },
          labelPos: { x: W * 0.730, y: clamp(pPectoral.y, H * 0.60, H * 0.68) },
          title: 'PECTORAL FIN THRUSTER',
          title2: '',
          sub: 'Multi-axis movement.',
          sub2: '',
        },
        {
          pt: { x: clamp(pTail.x, W * 0.80, W * 0.87), y: clamp(pTail.y, H * 0.16, H * 0.28) },
          elbow: { x: clamp(pTail.x, W * 0.80, W * 0.87), y: H * 0.318 },
          labelPos: { x: W * 0.885, y: H * 0.318 },
          title: 'TAIL ACTUATORS',
          title2: '',
          sub: 'Vectorized propulsion',
          sub2: 'control.',
        },
      ];

      for (const c of callouts) {
        ctx.strokeStyle = 'rgba(65, 68, 74, 0.76)';
        ctx.lineWidth = 1.15 * u;
        ctx.beginPath();
        ctx.moveTo(c.pt.x, c.pt.y);
        ctx.lineTo(c.elbow.x, c.elbow.y);
        ctx.lineTo(c.labelPos.x - 6 * u, c.labelPos.y);
        ctx.stroke();

        ctx.fillStyle = '#E05A2B';
        ctx.fillRect(c.pt.x - 2.5 * u, c.pt.y - 2.5 * u, 5 * u, 5 * u);

        const tx = c.labelPos.x;
        let ty = c.labelPos.y - 2 * u;
        ctx.fillStyle = '#23252A';
        ctx.font = `700 ${Math.round(13 * u)}px ${SANS}`;
        ctx.fillText(c.title, tx, ty);
        if (c.title2) {
          ty += Math.round(16 * u);
          ctx.fillText(c.title2, tx, ty);
        }
        ctx.fillStyle = '#555A62';
        ctx.font = `400 ${Math.round(12 * u)}px ${SANS}`;
        if (c.sub) {
          ty += Math.round(16 * u);
          ctx.fillText(c.sub, tx, ty);
        }
        if (c.sub2) {
          ty += Math.round(15 * u);
          ctx.fillText(c.sub2, tx, ty);
        }
      }
    }

    const botY = footerTopY + Math.round(16 * u);
    drawSonarDetailInset(ctx, Math.round(42 * u), botY, Math.round(148 * u), t, u);
    drawSideOrthographic(ctx, Math.round(W * 0.285), botY + Math.round(8 * u), Math.round(W * 0.305), Math.round(136 * u), t, u);
    drawStructuralOverview(ctx, Math.round(W * 0.622), botY + Math.round(6 * u), Math.round(W * 0.35), Math.round(140 * u), u);

    // Interactive State-Machine Teardown Console Strip & Operator Pointer (`teardown` standard)
    const stageLabels = ['01 · NOMINAL CRUISE', '02 · MANTLE OPEN', '03 · FULL TEARDOWN', '04 · BLUEPRINT LOCK'];
    const sIdx = clamp(state.sceneIndex ?? 0, 0, 3);
    const localT = state.localT ?? 0;
    const cellW = Math.round(156 * u);
    const cellH = Math.round(24 * u);
    const stripW = cellW * stageLabels.length;
    const sx0 = Math.round((W - stripW) * 0.5);
    const sy0 = footerTopY - cellH - Math.round(10 * u);

    ctx.fillStyle = 'rgba(244, 241, 234, 0.92)';
    ctx.fillRect(sx0 - 4 * u, sy0 - 4 * u, stripW + 8 * u, cellH + 8 * u);
    ctx.strokeStyle = 'rgba(95, 90, 82, 0.45)';
    ctx.lineWidth = 1;
    ctx.strokeRect(sx0 - 4 * u + 0.5, sy0 - 4 * u + 0.5, stripW + 8 * u - 1, cellH + 8 * u - 1);

    stageLabels.forEach((lbl, i) => {
      const bx = sx0 + i * cellW;
      const active = i === sIdx;
      ctx.fillStyle = active ? '#E05A2B' : 'rgba(35, 38, 43, 0.06)';
      ctx.fillRect(bx + 1, sy0, cellW - 2, cellH);
      ctx.fillStyle = active ? '#FFFFFF' : '#4A4E55';
      ctx.font = `600 ${Math.round(10.5 * u)}px ${MONO}`;
      ctx.textAlign = 'center';
      ctx.fillText(lbl, bx + cellW * 0.5, sy0 + cellH * 0.67);
      ctx.textAlign = 'left';
    });

    // Operator pointer & click ripple ring during stage transition (`localT < 1.8s`)
    const cursorAlpha = 1 - smootherstep(1.25, 1.85, localT);
    if (cursorAlpha > 0.02) {
      const fromIdx = sIdx > 0 ? sIdx - 1 : 0;
      const moveK = smootherstep(0.0, 0.28, localT);
      const fromX = sx0 + fromIdx * cellW + cellW * 0.52;
      const toX = sx0 + sIdx * cellW + cellW * 0.52;
      const cx = lerp(fromX, toX, moveK);
      const cy = sy0 + cellH * 0.58;
      const clickDt = localT - 0.26;
      const ringK = clickDt >= 0 && clickDt < 0.55 ? clamp(clickDt / 0.55, 0, 1) : 0;
      const pressK = clickDt >= 0 && clickDt < 0.22 ? Math.sin((clickDt / 0.22) * Math.PI) : 0;

      ctx.save();
      ctx.globalAlpha = cursorAlpha;
      if (ringK > 0.01) {
        ctx.strokeStyle = '#E05A2B';
        ctx.globalAlpha = cursorAlpha * (1 - ringK) * 0.85;
        ctx.lineWidth = Math.max(1.4, 2.0 * u);
        ctx.beginPath();
        ctx.arc(toX, cy, (5 + ringK * 20) * u, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = cursorAlpha;
      }
      const sc = (1 - pressK * 0.16) * Math.max(0.75, u);
      ctx.translate(cx, cy);
      ctx.scale(sc, sc);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(0, 18);
      ctx.lineTo(5, 14);
      ctx.lineTo(8.5, 21);
      ctx.lineTo(11, 19.5);
      ctx.lineTo(7.5, 12.5);
      ctx.lineTo(13.5, 12.5);
      ctx.closePath();
      ctx.fillStyle = '#181C22';
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.4;
      ctx.stroke();
      ctx.restore();
    }

    tex.needsUpdate = true;
  }

  return { plane, canvas, texture: tex, draw, fit };
}

// ============================================================================
// 5. WORLD ENTRYPOINT (`createWorld`)
// ============================================================================

export default async function createWorld({ width, height, scenes = [], style = {} }) {
  const whaleStyle = {
    ...style,
    look: {
      ...(style.look || {}),
      color: { output: 'srgb', toneMapping: 'aces', exposure: 1.05 },
      backdrop: { color: '#ECE8DF', fog: 0.002 },
      env: { enabled: true, share: 0.80, softbox: 3.8, studioStrips: true },
      light: {
        illuminance: 2.40,
        keyRatio: 3.15,
        key: {
          color: '#FFFFFF',
          pos: [-7, 17, 11],
          shadow: { mapSize: 2048, extent: [6, 6], near: 1, far: 40, bias: -0.0005, normalBias: 0.01 },
        },
        sky: '#FFFFFF',
        ground: '#ADA89E',
        bounce: { color: '#FFF6E8', pos: [8, -4, 9], share: 0.20 },
      },
      contact: {
        enabled: true,
        opacity: 0.34,
        blur: 2.6,
        size: [7.8, 4.8],
        center: [0, 0],
        height: 1.8,
        resolution: 512,
        updateInterval: 1,
      },
      ao: {
        enabled: true,
        intensity: 0.74,
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
        inkStrength: 0.38,
        inkColor: '#181C22',
      },
    },
  };

  const studio = createCalLabStudio({ width, height, scenes, style: whaleStyle });
  const { scene, camera, bench } = studio;

  if (bench) bench.visible = false;

  const M = createMaterials();
  const whale = buildMechanicalWhale(M);
  scene.add(whale.root);

  scene.add(camera);
  const hud = createWhaleBlueprintHud({ camera, width, height });
  hud.fit();

  const POSTER_HERO = { center: [-0.04, 1.36, 0.06], size: [3.55, 2.04, 1.92] };
  const SONAR_CLOSE = { center: [-0.38, 1.32, 0.14], size: [2.55, 1.56, 1.52] };
  const SPINE_PECTORAL = { center: [-0.06, 1.30, 0.10], size: [2.98, 1.82, 1.74] };
  const EXPLODED_HERO = { center: [-0.02, 1.40, 0.10], size: [3.85, 2.32, 2.24] };

  const director = studio.director({
    subjects: {
      whale: whale.root,
      sonar: whale.parts.sonarAnchor,
      spine: whale.parts.spineGroup,
      pectoral: whale.parts.pectoralNear,
    },
    shots: {
      // Scene 01: Normal Closed Motion State + 3D Camera Orbit Showcase (-36° -> -12°)
      'whale-cruise': [
        { dur: 1.9, size: 'full', fill: 0.93, subject: POSTER_HERO, angle: -34, height: 12, move: 'orbit', amount: 0.55 },
        { dur: 2.1, size: 'wide', fill: 0.93, subject: POSTER_HERO, angle: -12, height: 10, move: 'orbit', amount: -0.48 },
      ],
      // Scene 02: Staged Shroud Deployment & Close-Up Subsystem Inspection
      'whale-cutaway': [
        { dur: 2.0, size: 'close', fill: 0.94, subject: SONAR_CLOSE, angle: -26, height: 9, move: 'push', amount: 0.16 },
        { dur: 2.0, size: 'medium', fill: 0.93, subject: SPINE_PECTORAL, angle: -14, height: 11, move: 'orbit', amount: 0.36 },
      ],
      // Scene 03: Full Multi-Axis Subsystem Teardown + 3D Orbit Rotation Showcase (-32° -> -10°)
      'whale-exploded': [
        { dur: 1.8, size: 'full', fill: 0.92, subject: { from: SPINE_PECTORAL, to: EXPLODED_HERO }, angle: -32, height: 14, move: 'orbit', amount: 0.58 },
        { dur: 2.2, size: 'wide', fill: 0.92, subject: EXPLODED_HERO, angle: -12, height: 12, move: 'orbit', amount: -0.52 },
      ],
      // Scene 04: Re-Assembly to Classic `reference.jpg` Blueprint Telemetry Lock
      'whale-blueprint': [
        { dur: 1.8, size: 'full', fill: 0.93, subject: { from: EXPLODED_HERO, to: POSTER_HERO }, angle: -22, height: 10, move: 'pull', amount: 0.10 },
        { dur: 2.2, size: 'wide', fill: 0.93, subject: POSTER_HERO, angle: -19, height: 9, move: 'push', amount: 0.05 },
      ],
    },
  });

  function render(frame = {}) {
    const t = frame.t ?? 0;
    const localT = frame.localT ?? t;
    const sceneIndex = clamp(frame.sceneIndex ?? 0, 0, 3);

    let cutaway = 0.0;
    let explode = 0.0;
    if (sceneIndex === 0) {
      // Scene 1: 100% closed streamlined hull swimming + camera orbit
      cutaway = 0.0;
      explode = 0.0;
    } else if (sceneIndex === 1) {
      // Scene 2: Gull-wing sonar & thoracic mantle doors smoothly hinge open
      cutaway = smootherstep(0.08, 1.75, localT);
      explode = smootherstep(1.2, 3.6, localT) * 0.18;
    } else if (sceneIndex === 2) {
      // Scene 3: Full multi-axis subsystem teardown + orbit showcase
      cutaway = 1.0;
      explode = lerp(0.18, 1.0, smootherstep(0.08, 1.95, localT));
    } else {
      // Scene 4: Smoothly retract from full teardown to classic cutaway blueprint lock
      cutaway = 1.0;
      explode = lerp(1.0, 0.34, smootherstep(0.08, 1.85, localT));
    }

    whale.update(t, { cutaway, explode, swimSpeed: 2.45 });
    director.update({ ...frame, t, localT, sceneIndex });
    hud.fit();
    hud.draw({
      t,
      localT,
      sceneIndex,
      anchors: whale.anchors,
    });
    studio.render(frame);
  }

  render({ t: 0, localT: 0, sceneIndex: 0 });

  return {
    canvas: studio.canvas,
    scene,
    camera,
    renderer: studio.renderer,
    render,
    storyboard: director.storyboard,
  };
}
