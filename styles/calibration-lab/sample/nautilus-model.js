// The Mechanical Nautilus (Archive / 007): clasps seated on the plates (kit seamHardware `surfaces`), a
// staggered teardown order on every hull part, tentacle plate and septum, an orderly full explode that fits one
// frame and lifts the machine off the floor (camera and timing in film.js).
// the final cut: the hull re-shaped in Blender (shell plates pushed to a
// superellipse section: flat sides, square outer edge; hood flattened to a low visor), ridgeLine fixed for flat
// grooves, the JS plate widening dropped, a dielectric cavity floor.
// Made to read hard instead of soft (lighting in stage.js; here:
// glazed ceramic, chamfered and copper-trimmed plate edges, plates widened 7% so seams close to lines, hatches and
// rivets for scale, fewer cracks, glossy saturated copper, slim titanium probe tips, mostly dark root hoses).
// the final cut: the final cut's crossing tentacles with sleeves that bend:
//   1. 15 tentacles (kin.js) traced off the reference to cross: a climber, two divers, depth along each arm, a resting
//      S-sway, back arms in a greyer ceramic.
//   2. Each arm: gunmetal core, ceramic sleeves rebuilt along the curve every frame (kit/mech.js curveSleeve) on a
//      ribbon section (1.12 r x 0.6 r) with copper edge lines and a copper lip, steel tabs at every joint, a steel
//      probe tip. The three big arms (5, 6, 9) are split along the face toward the viewer: a narrow slit, mechanism
//      blocks at an exact pitch behind it, every third sleeve closed.
//   3. The first 12% of each arm bare mechanism: collars, a drive ram and two hoses back into the head.
//   4. Hood in chevron bands, the reference's eye, belly flanges facing the camera (the final cut).
// Kept from the final cut: the camera-side window, seam hardware on every seam, the seven-ring umbilicus, metals ≥ 0.8 under
// studioEnvironment, the reference's palette and wear.
import { THREE } from '/styles/calibration-lab/kernel.js';
const hullGlb = new URL('./hull.glb', import.meta.url).href;
import {applyMaterials, explodeRig, loadGLB, partsOf} from './kit-compat.js';
import {boxUVs, createMaterials, governMaterial} from './kit-compat.js';
import {curveSleeve, cutWindow, lugRing, metalReport, radialFins, ridgeLine, ringStack, seamHardware, wearMaps, windowRim} from './kit-compat.js';
import {
  bolt,
  counterboreBoss,
  creviceRing,
  flangedRing,
  gear,
  helix,
  instanced,
  machinedPlate,
  ribbedLink,
  swept,
  updateSwept,
  vary,
} from './kit-compat.js';
import { mergeGeometries } from './kit-compat.js';
import {rng} from './kit-compat.js';
import {createLod, lerpMaterial, scaleIn} from './kit-compat.js';
import {P, READ, FOCUS} from './palette.js';
import {G, sampleTentacle, SEPTA_ANGLES, TENTACLE_DEFS} from './kin.js';

const V3 = THREE.Vector3;

const hash1 = (n) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453123;
  return x - Math.floor(x);
};

// kit/parts.js swept() now winds outward itself; this used to flip it and is kept as a pass-through.

// ------------------------------------------------------------------ Ceramic armour colour (wear is in kit/mech.js wearMaps)
function makeShellArmorTexture(mode = 'plain', overlay = null) {
  const W = 1024;
  const H = 1024;
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const g = c.getContext('2d');

  // Pure, clean matte white / warm engineering porcelain (matching Mechanical Bee & Medusa JF-6 white armor)
  const isCeramic = mode === 'ceramic';
  const gr = g.createLinearGradient(0, 40, 0, H);
  const sg = isCeramic ? P.shell.ceramic : P.shell.plain;
  [0, 0.4, 0.8, 1].forEach((t, i) => gr.addColorStop(t, sg[i]));
  g.fillStyle = gr;
  g.fillRect(0, 0, W, H);

  // Hard edge: a chamfer along every plate edge, dark on the outer 9 px (the bevel turned away) and a bright line inside
  // it (the bevel catching the key). This is what reads a round panel as a hard plate instead of a cushion (the final cut).
  const chamfer = (x, y, w, h, horizontal) => {
    // the seam-side edges are trimmed in copper (reference: copper runs along the plate edges, not only in the gap)
    g.fillStyle = horizontal || READ ? P.shell.chamferDark : P.seam.chamfer;
    g.fillRect(x, y, w, h);
    g.fillStyle = P.shell.chamferLight;
    if (horizontal) g.fillRect(x, y + (y === 0 ? h : -3), w, 3);
    else g.fillRect(x + (x === 0 ? w : -3), y, 3, h);
  };
  chamfer(0, 0, 14, H, false);
  chamfer(W - 14, 0, 14, H, false);
  chamfer(0, 0, W, 7, true);
  chamfer(0, H - 7, W, 7, true);

  // Two transverse panel lines (fewer than the final cut's six: one or two per plate on the reference)
  for (const v of [Math.round(H * 0.38), Math.round(H * 0.71)]) {
    g.fillStyle = P.shell.panelLine;
    g.fillRect(0, v, W, 2);
    g.fillStyle = P.shell.panelHi;
    g.fillRect(0, v + 2, W, 1.5);
  }

  // Scale: inspection hatches with a screw at each corner and a short vent grille, a rivet row along both seams.
  // A 12 m hull needs parts a few centimetres across, or it reads as a toy.
  const hatch = (x, y, w, h, slots) => {
    g.strokeStyle = P.shell.hatchLine;
    g.lineWidth = 2;
    g.strokeRect(x, y, w, h);
    g.strokeStyle = P.shell.hatchHi;
    g.lineWidth = 1.2;
    g.strokeRect(x + 2, y + 2, w, h);
    g.fillStyle = P.shell.hatchDot;
    for (const [sx, sy] of [[x + 8, y + 8], [x + w - 8, y + 8], [x + 8, y + h - 8], [x + w - 8, y + h - 8]]) {
      g.beginPath();
      g.arc(sx, sy, 3.2, 0, Math.PI * 2);
      g.fill();
    }
    g.fillStyle = P.shell.slot;
    for (let k = 0; k < slots; k++) g.fillRect(x + 18, y + 18 + k * 9, w * 0.45, 3.5);
  };
  const alt = isCeramic || mode === '05';
  // canvas y = (1 - v) H and v runs collar -> outer whorl: the face seen in the hero view is y 0.2-0.6 H
  hatch(alt ? W * 0.56 : W * 0.22, H * 0.28, 150, 92, 3);
  hatch(alt ? W * 0.2 : W * 0.58, H * 0.5, 120, 70, 0);
  g.fillStyle = P.shell.rivet;
  for (let y = 30; y < H - 20; y += 34) {
    for (const x of [22, W - 22]) {
      g.beginPath();
      g.arc(x, y, 2.8, 0, Math.PI * 2);
      g.fill();
    }
  }

  if (mode === 'cheekLobe') {
    for (const xSub of [260, 520, 780]) {
      g.strokeStyle = P.shell.cheekLine;
      g.lineWidth = 1.6;
      g.beginPath();
      g.moveTo(xSub, 40);
      g.quadraticCurveTo(xSub + 42, H * 0.5, xSub - 18, H - 40);
      g.stroke();
    }
  }

  // wear hairlines (kit/mech.js wearMaps overlay): cracks, chips, panel lines, rivets, readable at hero distance
  if (overlay) g.drawImage(overlay, 0, 0, W, H);

  // Clean archival stencil numbers ("07" and "05") in deep charcoal with an industrial-orange index bar
  if (mode === '07' || mode === '05') {
    g.save();
    g.translate(mode === '05' ? W * 0.36 : W * 0.50, mode === '05' ? H * 0.62 : H * 0.58);
    g.scale(1.0, 0.42);
    g.rotate(0.12);
    // Small industrial signal-orange registration bar above stencil
    g.fillStyle = P.glow.stencilBar;
    g.fillRect(-92, -158, 184, 18);
    g.font = '700 245px "JetBrains Mono", "Courier New", monospace';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillStyle = P.shell.stencil;
    g.fillText(mode, 0, 0);
    g.restore();
  }

  const tex = new THREE.CanvasTexture(c);
  tex.encoding = THREE.sRGBEncoding; // r147: no colorSpace
  tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.anisotropy = 4;
  return tex;
}

function makeTentacleArmorTexture(isCeramic = false, overlay = null, edges = false) {
  const W = 512;
  const H = 512;
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const g = c.getContext('2d');

  const gr = g.createLinearGradient(0, 0, W, H);
  const tg = isCeramic ? P.shell.tentCeramic : P.shell.tentPlain;
  [0, 0.5, 1].forEach((t, i) => gr.addColorStop(t, tg[i]));
  g.fillStyle = gr;
  g.fillRect(0, 0, W, H);

  // Subtle machined chamfer line on each polygonal facet
  g.strokeStyle = P.shell.facetLine;
  g.lineWidth = 1.4;
  for (const v of [128, 256, 384]) {
    g.beginPath();
    g.moveTo(0, v);
    g.lineTo(W, v);
    g.stroke();
  }
  if (overlay) g.drawImage(overlay, 0, 0, W, H); // cracks and chips (wearMaps), the reference's level
  if (edges) {
    // curveSleeve uv: y = 0 / 0.5 / 1 are the two edges of the ribbon -> copper lines along both edges (reference)
    g.fillStyle = READ ? P.mech.aluDark : P.seam.tentEdge;
    for (const y of [0, H / 2 - 10, H - 20]) g.fillRect(0, y, W, 20);
  }

  const tex = new THREE.CanvasTexture(c);
  tex.encoding = THREE.sRGBEncoding; // r147: no colorSpace
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = 4;
  return tex;
}

// Map each Blender shell plate's UVs so u in [0,1] spans across its radial seam-to-seam angle
// and v in [0,1] spans radially from the umbilicus collar to the outer whorl perimeter.
function assignPolarShellUVs(geometry) {
  const pos = geometry.attributes.position;
  if (!geometry.attributes.normal) geometry.computeVertexNormals();
  const n = pos.count;
  const thArr = new Float32Array(n);
  const rArr = new Float32Array(n);

  // Compute mean angle first to avoid +/-PI branch cut jumps
  let sumCos = 0;
  let sumSin = 0;
  for (let i = 0; i < n; i++) {
    const dx = pos.getX(i) - G.hubX;
    const dy = pos.getY(i) - G.hubY;
    const r = Math.hypot(dx, dy) || 1e-5;
    sumCos += dx / r;
    sumSin += dy / r;
  }
  const refAng = Math.atan2(sumSin, sumCos);

  let thMin = Infinity;
  let thMax = -Infinity;
  let rMin = Infinity;
  let rMax = -Infinity;
  for (let i = 0; i < n; i++) {
    const dx = pos.getX(i) - G.hubX;
    const dy = pos.getY(i) - G.hubY;
    const r = Math.hypot(dx, dy);
    let dTh = Math.atan2(dy, dx) - refAng;
    while (dTh > Math.PI) dTh -= Math.PI * 2;
    while (dTh < -Math.PI) dTh += Math.PI * 2;
    thArr[i] = dTh;
    rArr[i] = r;
    if (dTh < thMin) thMin = dTh;
    if (dTh > thMax) thMax = dTh;
    if (r < rMin) rMin = r;
    if (r > rMax) rMax = r;
  }

  const thSpan = Math.max(1e-4, thMax - thMin);
  const rSpan = Math.max(1e-4, rMax - rMin);
  const uv = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {
    uv[i * 2] = 1.0 - (thArr[i] - thMin) / thSpan;
    uv[i * 2 + 1] = (rArr[i] - rMin) / rSpan;
  }
  geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
}

export async function buildNautilus({clipPlane, studio} = {}) {
  const r = rng(7007);
  // Palette from the reference sheet (refs/nautilus.png), not from other builds: ceramic white armour with cracks
  // and chipped edges; copper in every seam; steel, titanium and gunmetal mechanism; brass fittings. Signal orange
  // (accent) only where something glows (eye, jets). Every metal is metal: metalness ≥ 0.8 (docs/form.md step 5).
  const M = createMaterials(
    {
      white: P.mech.white,
      ceramic: P.mech.ceramic,
      alu: P.mech.alu,
      aluDark: P.mech.aluDark,
      titanium: P.mech.titanium,
      steel: P.mech.steel,
      chrome: P.mech.chrome,
      structure: P.mech.structure,
      liner: P.mech.liner,
      hose: P.mech.hose,
      brass: P.mech.brass,
      bronze: P.mech.bronze,
      accent: P.glow.accent,
    },
    {normalScale: 0.48},
  );

  // gunmetal structure: a metal, so the softboxes draw its bevels as bright edges instead of a plastic sheen
  M.structure.metalness = 0.86;
  M.structure.roughness = 0.38;
  M.structure.clearcoat = 0;
  M.structure.envMapIntensity = 1.0;

  // the cavity behind windows: dark, rough, not metal; it is the "inside" the windows look into
  M.liner.metalness = 0.2;
  M.liner.roughness = 0.7;

  M.aluDark.metalness = 0.86;
  M.aluDark.roughness = 0.4;
  M.aluDark.envMapIntensity = 1.0;

  const cavityMat = governMaterial(new THREE.MeshStandardMaterial({color: P.mech.cavity, metalness: 0.25, roughness: 0.62}), 'precision');
  M.darkGunmetal = M.aluDark.clone();
  M.darkGunmetal.color.set(P.mech.darkGunmetal);

  // copper: the seam colour of the reference. (Name kept: every former orange part is now copper.)
  M.copper = governMaterial(
    // saturated like the reference's copper; it reads as metal (not orange paint, the final cut) by sharp reflections:
    // low roughness so the softboxes draw bright streaks on it against the dark surround
    new THREE.MeshStandardMaterial({color: P.seam.copper, metalness: P.seam.copperMetalness, roughness: 0.16, envMapIntensity: 1.25}),
    'precision',
  );
  if (FOCUS) {
    // the final cut: the warm accent only sits at the core, eye and jets now; pure signal orange (matches the console), not brown
    M.copper.color.set(P.glow.accent);
    M.copper.metalness = 0.55;
    M.copper.roughness = 0.3;
  }
  M.orangeMetal = M.copper;
  M.copperDark = governMaterial(
    new THREE.MeshStandardMaterial({color: P.seam.copperDark, metalness: 0.92, roughness: 0.36, envMapIntensity: 1.1}),
    'precision',
  );

  M.titanium.metalness = 0.86;
  M.titanium.roughness = 0.36;
  M.titanium.envMapIntensity = 1.0;

  M.steel.metalness = 0.95;
  M.steel.roughness = 0.24;

  M.bronze.metalness = 0.92;
  M.brass.metalness = 0.92;

  // Ceramic armour: clean colour, wear in the relief. Levels counted off the reference: hairline cracks on most
  // plates, chipped edges, a rivet row along each seam, two or three panel lines per plate.
  const {bumpMap, roughnessMap, overlay} = wearMaps({seed: 7, grain: 0.45, edges: 0.55, chips: 0.45, panels: 0.25, cracks: READ ? 0.05 : 0.16, rivets: 0.7, lineScale: 1.7, ink: P.shell.wearInk});
  const makeShellMat = (mode) =>
    governMaterial(
      new THREE.MeshPhysicalMaterial({
        map: makeShellArmorTexture(mode, overlay),
        bumpMap,
        bumpScale: 0.022,
        roughnessMap,
        roughness: 0.46,
        metalness: 0.04,
        // glazed ceramic: a crisp clearcoat draws the softboxes as sharp highlights, which is what makes a round
        // panel read as hard (the final cut's matte 0.08 coat let every plate read as a soft cushion)
        clearcoat: 0.7,
        clearcoatRoughness: 0.1,
      }),
      'shell',
    );

  const shellMatWhite = makeShellMat('plain');
  const shellMatCeramic = makeShellMat('ceramic');
  const shellMat07 = makeShellMat('07');
  const shellMat05 = makeShellMat('05');
  const shellMatCheek = makeShellMat('cheekLobe');

  // flat-shaded metals for the tentacle cores, tabs and tips
  const polyGunmetal = M.darkGunmetal.clone();
  polyGunmetal.flatShading = true;
  const polyTitanium = M.titanium.clone();
  polyTitanium.flatShading = true;
  const polySteel = M.steel.clone();
  polySteel.flatShading = true;

  // Ghost material for X-Ray / Hull Shell mode
  const ghostMat = governMaterial(
    new THREE.MeshPhysicalMaterial({
      color: P.shell.ghost,
      roughness: 0.48,
      metalness: 0.05,
      transparent: true,
      opacity: 0.18,
      depthWrite: false,
      side: THREE.DoubleSide,
    }),
    'shell',
  );

  const root = new THREE.Group();

  // Soft localized internal amber point lights
  const eyeGlowMat = new THREE.MeshStandardMaterial({color: P.glow.eyeBase, emissive: P.glow.eyeEmissive, emissiveIntensity: 1.25, roughness: 0.35, metalness: 0});
  const eyeLensMat = new THREE.MeshPhysicalMaterial({color: P.glow.lens, roughness: 0.06, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.04});
  const eyeCowls = [];
  const eyeLightL = new THREE.PointLight(P.glow.eyeLight, 3.0, 1.3, 2.2);
  eyeLightL.position.set(G.eyeX + 0.05, G.eyeY + 0.15, 1.75);
  const eyeLightR = new THREE.PointLight(P.glow.eyeLight, 3.0, 1.3, 2.2);
  eyeLightR.position.set(G.eyeX + 0.05, G.eyeY + 0.15, -1.75);
  const hubLight = new THREE.PointLight(P.glow.hubLight, 4.5, 3.2, 2.0);
  hubLight.position.set(G.hubX - 0.4, G.hubY + 0.5, 0.0);
  root.add(eyeLightL, eyeLightR, hubLight);

  // ------------------------------------------------------------------ 1. Blender Sculpted Hull (hull.glb)
  const hullRoot = await loadGLB(hullGlb, {studio});
  applyMaterials(hullRoot, M);

  // The window (reference: the upper-front shell is open between the umbilicus and the outer whorl, the septa and
  // drive showing through). Plates 01-04 and their seams lose their camera-side skin inside WINDOW_R; the outer
  // band stays, so the silhouette does not change. Cut in mesh space (the hull is exported with transforms applied).
  const WINDOW_R = 3.15;
  const WINDOW_Z = 0.25;
  const hubR = (x, y) => Math.hypot(x - G.hubX, y - G.hubY);
  const windowKeep = (x, y, z) => Math.max(hubR(x, y) - WINDOW_R, WINDOW_Z - z);
  const inWindow = (name) => /^shell__(plate|seam_groove|seam)_0[1-4]$/.test(name);
  const rimJobs = [];
  const seamJobs = [];
  const widenAboutHub = (geo, k) => {
    const pos = geo.attributes.position;
    let sc = 0;
    let ss = 0;
    for (let i = 0; i < pos.count; i++) {
      const a = Math.atan2(pos.getY(i) - G.hubY, pos.getX(i) - G.hubX);
      sc += Math.cos(a);
      ss += Math.sin(a);
    }
    const ac = Math.atan2(ss, sc);
    for (let i = 0; i < pos.count; i++) {
      const dx = pos.getX(i) - G.hubX;
      const dy = pos.getY(i) - G.hubY;
      const r = Math.hypot(dx, dy);
      let d = Math.atan2(dy, dx) - ac;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      const a = ac + d * k;
      pos.setXY(i, G.hubX + r * Math.cos(a), G.hubY + r * Math.sin(a));
    }
    pos.needsUpdate = true;
    geo.computeVertexNormals();
  };
  const hoodJobs = [];

  const jetDegMap = {1: -8, 2: -22, 3: -36, 4: -50};
  hullRoot.traverse((m) => {
    if (!m.isMesh) return;
    // Plates 7% wider in angle about their own centre: the rounded ends of neighbours close up, so a seam reads as a
    // line between two hard plates, not a deep V between two cushions (the final cut). The seam groove and its hardware stay.
    if (/^shell__plate_\d\d$/.test(m.name)) widenAboutHub(m.geometry, 1.0);
    if (inWindow(m.name)) {
      const {geometry, edges} = cutWindow(m.geometry, windowKeep);
      m.geometry.dispose();
      m.geometry = geometry;
      if (m.name.startsWith('shell__plate_')) rimJobs.push({mesh: m, edges});
    }
    if (m.name.startsWith('shell__seam_groove_')) seamJobs.push(m);
    boxUVs(m.geometry, 2.2);

    if (m.name.startsWith('shell__plate_')) {
      assignPolarShellUVs(m.geometry);
      const idx = Number(m.name.slice(-2));
      if (idx === 6) m.material = shellMat07;
      else if (idx === 7) m.material = shellMat05;
      else m.material = idx % 2 === 1 ? shellMatWhite : shellMatCeramic;
    } else if (m.name.startsWith('hood__cheek_posterior') || m.name.startsWith('hood__cheek_anterior')) {
      assignPolarShellUVs(m.geometry);
      m.material = m.name.includes('anterior') ? shellMatCheek : shellMatCeramic;
    } else if (m.name.startsWith('hood__visor_fore') || m.name.startsWith('hood__visor_aft')) {
      assignPolarShellUVs(m.geometry);
      m.material = m.name.includes('fore') ? shellMatWhite : shellMatCheek;
      hoodJobs.push(m);
    } else if (m.name.startsWith('shell__seam_groove_') || m.name === 'hood__visor_seam' || m.name === 'hood__cheek_seam_01') {
      // the gap between plates is copper in the reference: dark copper groove, bright copper liner on top
      m.material = READ ? M.liner : M.copperDark; // the final cut: dark gaps carry the spiral's rhythm (the final cut)
    } else if (m.name.startsWith('shell__seam_')) {
      const idx = Number(m.name.slice(-2));
      m.material = idx % 2 === 0 ? M.darkGunmetal : M.steel;
    } else if (m.name.startsWith('shell__collar_')) {
      const idx = Number(m.name.slice(-2));
      // Segmented umbilicus crown collar: deep charcoal-black, bright steel, and industrial signal-orange accents (like Medusa JF-6)
      m.material = idx % 4 === 1 ? M.orangeMetal : idx % 2 === 0 ? M.structure : M.steel;
    } else if (m.name.startsWith('core__umbilicus_')) {
      // Iconic deep charcoal-black central hub with dark gunmetal outer rim (matching Medusa JF-6 crown disc)
      m.material = m.name.includes('rim') ? M.darkGunmetal : M.structure;
    }

    if (
      m.name.includes('inner_liner') ||
      m.name.includes('cephalic_cranium') ||
      m.name.includes('underbelly_liner')
    ) {
      m.scale.z = 0.14;
      m.position.z = -0.34;
      // cavity floors: a mid-grey liner (dielectric, docs/form.md step 5), so the parts in front of them read as
      // silhouettes against a floor, not a hole; as metal they mirrored the dark surround and went black
      m.material = cavityMat;
    }
    if (m.name.includes('underbelly_rib')) {
      m.visible = false;
      m.userData.noSilhouette = true;
    }
    if (m.name.startsWith('eye__')) {
      const g = m.geometry;
      g.translate(-G.eyeX, -G.eyeY, 0);
      g.scale(0.76, 0.76, 0.88);
      g.translate(G.eyeX + 0.08, G.eyeY + 0.16, 0);
      // reference eye: steel housing and bezel, a brass ring, a glowing amber iris, a black glass lens with a glint
      if (m.name.includes('outer_cowl')) m.material = M.titanium;
      else if (m.name.includes('bezel')) m.material = M.steel;
      else if (m.name.includes('brass_ring')) m.material = M.brass;
      else if (m.name.includes('iris_glow')) m.material = eyeGlowMat;
      else if (m.name.includes('pupil_lens')) m.material = eyeLensMat;
      else m.material = M.structure;
      if (m.name.includes('outer_cowl')) eyeCowls.push(m);
    }
    if (m.name.startsWith('jet__')) {
      const match = /thruster_0(\d)/.exec(m.name);
      const tNum = match ? Number(match[1]) : 2;
      const deg = jetDegMap[tNum] ?? -22;
      const a = (deg * Math.PI) / 180;
      m.geometry.translate(Math.cos(a) * 0.44, Math.sin(a) * 0.44, 0);
      // Deep charcoal-black thruster shrouds + signal-orange/brass collars + bright silver-steel nozzles
      if (m.name.includes('collar')) m.material = tNum % 2 === 1 ? M.orangeMetal : M.bronze;
      else if (m.name.includes('nozzle')) m.material = M.steel;
      else m.material = M.titanium;
    }
  });

  // Hood armour: the reference's hood is a stack of angular cracked plates, not one smooth cowl. Each visor piece is
  // cut into chevron bands (cutWindow with two planes), a gap between bands, every band edge rimmed in copper, and
  // each band stepped out a little more than the one before it so they overlap like scales. Flat-shaded: facets.
  const HOOD_GAP = 0.05;
  for (const m of hoodJobs) {
    const fore = m.name.includes('fore');
    const cuts = fore ? [-99, -0.55, 0.3, 99] : [-99, 1.05, 2.15, 99];
    const src = m.geometry;
    const coord = (x, y, z) => x + 0.35 * y + 0.12 * Math.abs(z); // chevron: bands sweep back toward the flanks
    const mat = m.material.clone();
    mat.flatShading = true;
    for (let k = 0; k < cuts.length - 1; k++) {
      const a = cuts[k] + HOOD_GAP;
      const b = cuts[k + 1] - HOOD_GAP;
      const {geometry, edges} = cutWindow(src, (x, y, z) => Math.min(coord(x, y, z) - a, b - coord(x, y, z)));
      geometry.computeBoundingBox();
      const c = geometry.boundingBox.getCenter(new V3());
      const step = 1 + 0.018 * (fore ? cuts.length - 2 - k : k); // the band nearer the shell sits under the next
      geometry.translate(-c.x, -c.y, -c.z).scale(step, step, step).translate(c.x, c.y, c.z);
      const band = k === 0 ? m : new THREE.Mesh(geometry, mat);
      if (k === 0) m.geometry = geometry;
      m.material = mat;
      if (k > 0) m.add(band);
      for (const e of edges) {
        for (const p of e.points) p.sub(c).multiplyScalar(step).add(c);
        band.add(windowRim(e, {depth: 0.05, lip: 0.018, wallMat: M.aluDark, lipMat: READ ? M.aluDark : M.copper, minLength: 0.3}));
      }
    }
    src.dispose();
  }

  // Eye bezel: a lugged steel ring with 24 lugs around each housing (the reference's bolt ring round the iris)
  for (const cowl of eyeCowls) {
    cowl.geometry.computeBoundingBox();
    const bb = cowl.geometry.boundingBox;
    const c = bb.getCenter(new V3());
    const rr = Math.max(bb.max.x - bb.min.x, bb.max.y - bb.min.y) / 2;
    const front = c.z > 0 ? bb.max.z : bb.min.z;
    const ring = new THREE.Mesh(lugRing({rOuter: rr * 1.08, rInner: rr * 0.92, thick: 0.08, lugs: 24, lugDepth: 0.35}), M.steel);
    ring.position.set(c.x, c.y, front - Math.sign(c.z) * 0.12);
    if (c.z < 0) ring.rotation.y = Math.PI;
    cowl.add(ring);
  }

  // Window rims: the panel's side wall (dark, so the opening reads as cut through something solid) + a copper lip.
  // Children of their plate, so they travel with it in every teardown.
  for (const {mesh, edges} of rimJobs)
    for (const e of edges) mesh.add(windowRim(e, {depth: 0.16, lip: 0.05, wallMat: M.liner, lipMat: READ ? M.aluDark : M.copper, minLength: 0.4}));

  // Seam hardware on both faces of every seam: a copper liner sunk in the groove and clasps across it.
  // Seams crossing the window only get it on their remaining outer part.
  const claspMat = M.steel;
  const LOD_NEAR = 30.5;
  const LOD_FAR = 33.5;
  const claspAlt = READ ? M.steel : M.brass;
  // clasps sit on the plates either side of a seam, not on the groove's ridge (kit seamHardware `surfaces`)
  hullRoot.updateMatrixWorld(true);
  const plateMeshes = [];
  hullRoot.traverse((o) => o.isMesh && /^shell__plate_\d\d$/.test(o.name) && plateMeshes.push(o));
  // the final cut (focus look): detail by camera distance. Full at the close-up distances, none at the hero's.
  const lateDetail = [];
  const seamLod = createLod({near: LOD_NEAR, far: LOD_FAR});
  const seamAccent = M.liner.clone();
  seamLod.add(lerpMaterial(seamAccent, {color: ['#1C1F24', P.mech.alu], metalness: [0.2, 0.9], roughness: [0.7, 0.3]}));
  for (const m of seamJobs) {
    const windowed = inWindow(m.name);
    for (const zSign of [1, -1]) {
      const range = windowed && zSign > 0 ? [WINDOW_R + 0.12, 99] : null;
      const ridge = ridgeLine(m.geometry, {along: (p) => hubR(p.x, p.y), up: new V3(0, 0, zSign), bins: 16, range});
      if (ridge.points.length < 3) continue;
      // the final cut: one dense area (window + its neighbour seam), the outer shell quiet like the final cut: no clasps, a dark liner
      const quiet = FOCUS && Number(m.name.slice(-2)) > 5;
      m.add(seamHardware({...ridge, linerMat: FOCUS ? M.liner : READ ? M.darkGunmetal : M.copper, linerR: quiet ? 0.085 : 0.06, sink: 0.015, claspMat: quiet ? null : claspMat, claspAlt, pitch: FOCUS ? 0.84 : READ ? 1.26 : 0.42, clasp: [0.1, 0.07, 0.32], surfaces: plateMeshes, space: m}));
      if (quiet) {
        // the final cut: the quiet seams earn their small parts as the camera closes in (kit/lod.js): steel clasps grow in and a
        // thin bright steel line rises on the dark liner. Steel/aluminium, never the accent orange.
        const detail = seamHardware({...ridge, linerMat: seamAccent, linerR: 0.03, sink: -0.045, claspMat, claspAlt, pitch: 0.6, clasp: [0.1, 0.07, 0.32], surfaces: plateMeshes, space: m});
        const [accent, ...clasps] = detail.children;
        seamLod.add(scaleIn(clasps));
        seamLod.add((k) => (accent.visible = k > 0.002));
        lateDetail.push([m, detail]); // attached after the teardown vectors are measured (their bounds would shift them)
      }
    }
  }

  // Two-stage teardown metadata on every Blender hull part:
  //   - `fullVec`: large-amplitude 3D explosion vector for the Grand Wide-Shot Full-Part Teardown
  //   - `focusKey` + `focusVec`: targeted close-up teardown vector when inspecting Core/Eye, Septa, or Jets
  const hullParts = partsOf(hullRoot);
  const hullCustomExplode = [];
  for (const o of hullParts.all) {
    delete o.userData.hinge;
    delete o.userData.pivot;
    const nm = o.name;
    const basePos = o.position.clone();
    if (
      nm.includes('inner_liner') ||
      nm.includes('cephalic_cranium') ||
      nm.includes('underbelly_liner')
    ) {
      o.userData.explode = [0, 0, 0];
      hullCustomExplode.push({obj: o, basePos, fullVec: new V3(0, 0, 0), focusKey: null, focusVec: new V3(0, 0, 0)});
      continue;
    }
    const pc = new THREE.Box3().setFromObject(o).getCenter(new V3());
    const dx = pc.x - G.hubX;
    const dy = pc.y - G.hubY;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len;
    const uy = dy / len;

    // full explode (the final cut): an orderly exploded assembly that fits one wide frame and never goes below the floor;
    // vertical push is damped (EX_V) and the whole machine lifts (update: root.position.y)
    const EX_V = 0.75;
    let fullVec = new V3(ux * 1.5, uy * 1.5 * EX_V, 0);
    let focusKey = null;
    let focusVec = new V3(0, 0, 0);

    if (nm.startsWith('shell__plate') || nm.startsWith('shell__seam')) {
      const m = /_(\d+)$/.exec(nm);
      const idx = m ? Number(m[1]) : 5;
      // plate and its seam move together (the seam carries the clasps), alternate plates a step further
      const rDist = 1.45 + (idx % 2) * 0.45;
      const zStagger = (idx % 2 === 0 ? 1 : -1) * 0.3;
      fullVec = new V3(ux * rDist, uy * rDist * EX_V, zStagger);
      if (idx <= 7) {
        focusKey = 'septa';
        focusVec = new V3(ux * (2.15 + (idx % 2) * 0.35), uy * (2.15 + (idx % 2) * 0.35), (idx % 2 === 0 ? 0.45 : -0.45));
      } else if (idx >= 8 && idx <= 13) {
        focusKey = 'jets';
        // jets close-up: plates near the jets open a little, radially only (the final cut pushed them 1.65 m and they filled the
        // frame in front of the nozzles)
        focusVec = new V3(ux * 0.8, uy * 0.8, 0);
      }
    } else if (nm.startsWith('shell__collar')) {
      const m = /_(\d+)$/.exec(nm);
      const idx = m ? Number(m[1]) : 5;
      fullVec = new V3(ux * 0.9, uy * 0.9 * EX_V, (idx % 2 === 0 ? 1 : -1) * 0.9);
      focusKey = 'core';
      focusVec = new V3(ux * 0.85, uy * 0.85, (idx % 2 === 0 ? 1 : -1) * 0.65);
    } else if (nm.startsWith('hood__visor')) {
      const isFore = nm.includes('fore');
      fullVec = new V3(isFore ? -1.9 : -1.3, isFore ? 1.5 : 1.15, 0);
      focusKey = 'core';
      focusVec = new V3(isFore ? -1.55 : -1.05, isFore ? 1.45 : 1.05, 0);
    } else if (nm.startsWith('hood__cheek')) {
      const sz = nm.endsWith('_L') ? 1 : nm.endsWith('_R') ? -1 : 0;
      const isAnt = nm.includes('anterior');
      fullVec = new V3(isAnt ? -1.3 : -0.9, isAnt ? -1.2 : -1.4, sz * 1.6);
      focusKey = isAnt ? 'core' : 'jets';
      focusVec = new V3(isAnt ? -0.95 : -0.65, -1.25, sz * 1.15);
    } else if (nm.startsWith('eye__')) {
      const sz = nm.endsWith('_L') ? 1 : -1;
      const layer = nm.includes('outer_cowl')
        ? 1.95
        : nm.includes('brass_ring')
          ? 1.55
          : nm.includes('aperture_ring')
            ? 1.15
            : nm.includes('iris_core')
              ? 0.75
              : 0.40;
      fullVec = new V3(-0.9, 0.3, sz * (layer * 0.8 + 0.6));
      focusKey = 'core';
      focusVec = new V3(-0.45, 0.22, sz * layer);
    } else if (nm.startsWith('core__umbilicus')) {
      const sz = nm.includes('_L') ? 1 : -1;
      const isRim = nm.includes('rim');
      fullVec = new V3(0, 0, sz * (isRim ? 2.2 : 1.5));
      focusKey = 'core';
      focusVec = new V3(0, 0, sz * (isRim ? 1.65 : 1.05));
    } else if (nm.startsWith('jet__')) {
      const match = /thruster_0(\d)/.exec(nm);
      const deg = match ? jetDegMap[Number(match[1])] ?? -22 : -22;
      const a = (deg * Math.PI) / 180;
      const jx = Math.cos(a);
      const jy = Math.sin(a);
      const stageDist = nm.includes('nozzle')
        ? 2.2
        : nm.includes('collar')
          ? 1.7
          : nm.includes('shroud')
            ? 1.3
            : 0.9;
      fullVec = new V3(jx * stageDist, jy * stageDist, (nm.includes('02') ? 0.6 : nm.includes('03') ? -0.6 : 0));
      focusKey = 'jets';
      focusVec = new V3(jx * (stageDist * 0.72), jy * (stageDist * 0.72), 0);
    }

    o.userData.explode = [fullVec.x, fullVec.y, fullVec.z];
    // order in the teardown sequence, 0..1: a part with order 1 leaves last and comes back first (kit-style stagger)
    let order = 0.5;
    const num = Number((/_(\d+)$/.exec(nm) || [])[1] ?? 7);
    if (nm.startsWith('shell__')) order = 0.15 + 0.7 * ((num - 1) / 13); // plates peel round the whorl, 01 first
    else if (nm.startsWith('hood__')) order = nm.includes('visor_fore') ? 0 : nm.includes('visor') ? 0.1 : 0.25;
    else if (nm.startsWith('eye__')) order = nm.includes('outer_cowl') ? 0 : nm.includes('bezel') ? 0.2 : nm.includes('brass') ? 0.4 : nm.includes('iris') ? 0.6 : 0.8;
    else if (nm.startsWith('core__umbilicus')) order = 0.2 + 0.12 * (num % 7);
    else if (nm.startsWith('jet__')) order = (nm.includes('nozzle') ? 0 : nm.includes('collar') ? 0.35 : 0.7) + 0.08 * (Number((/thruster_0(\d)/.exec(nm) || [])[1] ?? 1) - 1);
    hullCustomExplode.push({obj: o, basePos, fullVec, focusKey, focusVec, order: Math.min(1, order)});
  }
  const hullRig = explodeRig(hullParts, {distance: 1.0, centre: [G.hubX, G.hubY, 0]});
  root.add(hullRoot);

  // Save original materials on outer shell & cheek plates for X-Ray mode
  const shellMeshes = [];
  for (const sub of ['shell', 'hood']) {
    for (const o of hullParts.bySub[sub] || []) {
      o.traverse((m) => {
        if (m.isMesh && !m.name.includes('liner')) {
          shellMeshes.push({mesh: m, baseMat: m.material, wasGhost: false});
        }
      });
    }
  }

  // ------------------------------------------------------------------ 2. Tier 1: 01 Command Core, Clockwork Umbilicus & Bridge Arm
  const coreGroup = new THREE.Group();
  coreGroup.name = 'core'; // framing probe (sims/frame-probe) and subsystem lookups
  coreGroup.position.set(G.hubX, G.hubY, 0);
  root.add(coreGroup);

  const coreSphere = new THREE.Mesh(new THREE.SphereGeometry(0.66, 32, 24), M.structure);
  const coreBand = new THREE.Mesh(new THREE.CylinderGeometry(0.70, 0.70, 0.22, 36), M.orangeMetal);
  coreBand.rotation.x = Math.PI / 2;
  coreGroup.add(coreSphere, coreBand);

  const gyroOuter = flangedRing({
    rOuter: 118,
    rInner: 94,
    thickness: 16,
    webThickness: 6,
    flangeRim: 5,
    lighteningHoles: 12,
    boltCount: 16,
    bevel: 1.5,
    mat: M.steel,
    boltMat: M.orangeMetal,
    uvScale: 0.012,
  }).group;
  gyroOuter.scale.setScalar(0.01);

  const gyroInner = flangedRing({
    rOuter: 90,
    rInner: 72,
    thickness: 14,
    webThickness: 5,
    flangeRim: 4,
    lighteningHoles: 10,
    boltCount: 12,
    bevel: 1.2,
    mat: M.darkGunmetal,
    boltMat: M.steel,
    uvScale: 0.012,
  }).group;
  gyroInner.scale.setScalar(0.01);

  const coreGearL = new THREE.Mesh(
    gear({teeth: 36, rOut: 0.66, rRoot: 0.56, width: 0.14, helix: 0.2, holeR: 0.26, lighteningHoles: 8, bevel: 0.01, uvScale: 1}),
    M.steel,
  );
  coreGearL.position.z = 1.44;
  const coreGearR = coreGearL.clone();
  coreGearR.position.z = -1.44;

  // Inner counter-rotating signal-orange & brass pinion ring inside the deep-black umbilicus well
  const innerPinionL = new THREE.Mesh(
    gear({teeth: 24, rOut: 0.42, rRoot: 0.34, width: 0.16, helix: -0.2, holeR: 0.16, lighteningHoles: 6, bevel: 0.008, uvScale: 1}),
    M.orangeMetal,
  );
  innerPinionL.position.z = 1.50;
  const innerPinionR = innerPinionL.clone();
  innerPinionR.position.z = -1.50;

  const coreShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.20, 0.20, 3.25, 24).rotateX(Math.PI / 2), M.chrome);
  coreGroup.add(gyroOuter, gyroInner, coreGearL, coreGearR, innerPinionL, innerPinionR, coreShaft);

  // The umbilicus stack (out/the early cut.1's best detail): seven lugged rings stepping out of the well, counter-rotating,
  // tooth counts 20..48, steel / gunmetal / brass with races between. Sits in front of the Blender well discs.
  const umbilicus = ringStack({
    spread: 0.16,
    rings: [
      {rOut: 0.25, rIn: 0.15, z: 2.0, thick: 0.08, lugs: 20, mat: M.steel, spin: 1.25},
      {rOut: 0.36, rIn: 0.27, z: 1.95, thick: 0.09, lugs: 26, mat: M.darkGunmetal, spin: -0.9, race: M.brass},
      {rOut: 0.48, rIn: 0.38, z: 1.9, thick: 0.1, lugs: 32, mat: M.copper, spin: 0.68},
      {rOut: 0.61, rIn: 0.5, z: 1.85, thick: 0.1, lugs: 36, mat: M.steel, spin: -0.52, race: M.darkGunmetal},
      {rOut: 0.74, rIn: 0.63, z: 1.8, thick: 0.11, lugs: 40, mat: M.brass, spin: 0.38},
      {rOut: 0.88, rIn: 0.76, z: 1.74, thick: 0.11, lugs: 44, mat: M.darkGunmetal, spin: -0.28, race: M.steel},
      {rOut: 1.02, rIn: 0.9, z: 1.68, thick: 0.12, lugs: 48, mat: M.structure, spin: 0.18},
    ],
  });
  const hubCap = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, 0.16, 24).rotateX(Math.PI / 2), M.chrome);
  hubCap.position.z = 2.06;
  const hubCapR = hubCap.clone();
  hubCapR.position.z = -2.06;
  coreGroup.add(umbilicus.group, hubCap, hubCapR);

  // Segmented Umbilicus Mechanical Bridge Arm (clean white, deep charcoal-black, and signal-orange index plate)
  const bridgePlates = [];
  for (const sy of [-1, 1]) {
    for (let b = 0; b < 6; b++) {
      const rBridge = 0.52 + b * 0.22;
      const aBridge = ((164 - b * 3.5) * Math.PI) / 180;
      const bx = rBridge * Math.cos(aBridge);
      const by = rBridge * Math.sin(aBridge);
      const bz = sy * (1.46 - b * 0.03);
      const segPlate = new THREE.Mesh(
        new THREE.BoxGeometry(0.20, 0.34 - b * 0.02, 0.16),
        b === 0 ? M.orangeMetal : b % 2 === 1 ? M.structure : shellMatWhite,
      );
      segPlate.position.set(bx, by, bz);
      segPlate.rotation.z = aBridge - Math.PI;
      coreGroup.add(segPlate);
      bridgePlates.push({mesh: segPlate, basePos: new V3(bx, by, bz), sy, idx: b, aBridge});
    }
  }

  // ------------------------------------------------------------------ 3. Tier 1: 02 Spiral Septa Pressure Chambers & Siphuncle
  const septaGroup = new THREE.Group();
  septaGroup.name = 'septa'; // framing probe (sims/frame-probe) and subsystem lookups
  root.add(septaGroup);

  const septaBulkheads = [];
  const siphunclePts = [];
  const holeCounts = [8, 9, 7, 10, 8, 6, 8, 7, 6];
  const thickFactors = vary(r, SEPTA_ANGLES.length, 0.14, 0.22);

  SEPTA_ANGLES.forEach((ang, i) => {
    const f = i / (SEPTA_ANGLES.length - 1);
    const rMid = 3.12 - 0.44 * f;
    const rTube = 1.22 - 0.26 * f;
    const cx = G.hubX + rMid * Math.cos(ang);
    const cy = G.hubY + rMid * Math.sin(ang);

    const ring = flangedRing({
      rOuter: rTube * 100,
      rInner: rTube * 62,
      thickness: thickFactors[i] * 100,
      webThickness: thickFactors[i] * 42,
      flangeRim: rTube * 9,
      lighteningHoles: holeCounts[i],
      boltCount: 8 + (i % 3) * 2,
      bevel: 1.4,
      mat: i % 2 === 0 ? M.structure : M.steel,
      boltMat: i % 3 === 0 ? M.orangeMetal : M.bronze,
      uvScale: 0.015,
    });
    ring.group.scale.setScalar(0.01);
    const g = new THREE.Group();
    g.add(ring.group);
    g.position.set(cx, cy, 0.36);
    g.rotation.y = Math.PI / 2;
    g.rotation.x = -(ang - Math.PI / 2);

    const piston = new THREE.Mesh(
      new THREE.CylinderGeometry(rTube * 0.54, rTube * 0.54, 0.18, 24).rotateX(Math.PI / 2),
      i % 3 === 0 ? M.orangeMetal : M.bronze,
    );
    g.add(piston);

    const strutLen = Math.max(0.5, rMid - 1.15);
    const strut = new THREE.Mesh(
      ribbedLink({
        length: strutLen * 100,
        rBig: 18,
        rSmall: 13,
        rBoreBig: 9,
        rBoreSmall: 6.5,
        beamW: 16,
        thickness: 12,
        webThickness: 4.5,
        bevel: 0.8,
        uvScale: 0.012,
      }).scale(0.01, 0.01, 0.01),
      i % 2 === 0 ? M.steel : M.darkGunmetal,
    );
    const rStrut = 1.15 + strutLen * 0.5;
    strut.position.set(G.hubX + rStrut * Math.cos(ang), G.hubY + rStrut * Math.sin(ang), 0.52 + (i % 2) * 0.24);
    strut.rotation.z = ang - Math.PI / 2;

    septaGroup.add(g, strut);
    septaBulkheads.push({
      group: g,
      piston,
      strut,
      basePos: g.position.clone(),
      strutBasePos: strut.position.clone(),
      ang,
      rTube,
      idx: i,
    });
    siphunclePts.push(new V3(cx, cy, 0.42));
  });

  // Siphuncle peristaltic tube running through all 9 chambers
  const siphuncleGeo = swept({
      points: siphunclePts,
      radiusAt: (u) => 0.22 * (1 - 0.28 * u) * (1 + 0.14 * Math.sin(u * Math.PI * 16)),
      tubularSeg: 64,
      radialSeg: 12,
    });
  const siphuncleMesh = new THREE.Mesh(siphuncleGeo, M.structure);
  septaGroup.add(siphuncleMesh);

  // Vanes behind the window at an exact pitch (2.2°, every third one long): the machined rhythm the reference
  // shows through its opening. Two layers at different depths and pitches so they never read as one comb.
  const vanes = new THREE.Group();
  vanes.position.set(G.hubX, G.hubY, 0);
  const vaneA = radialFins({r0: 1.62, r1: WINDOW_R - 0.08, a0: 92 * (Math.PI / 180), a1: 146 * (Math.PI / 180), pitch: 2.2 * (Math.PI / 180), depth: 0.7, thick: 0.03, z: 1.15, mat: M.steel, minorMat: M.darkGunmetal, major: 3, minorLength: 0.55});
  const vaneB = radialFins({r0: 1.75, r1: WINDOW_R - 0.3, a0: 93.5 * (Math.PI / 180), a1: 145 * (Math.PI / 180), pitch: 4.5 * (Math.PI / 180), depth: 0.5, thick: 0.05, z: 0.55, mat: M.titanium, major: 2, minorLength: 0.7});
  vanes.add(vaneA, vaneB);
  // circumferential stiffening rings across the vanes, copper and steel
  for (const [rr, zz, mat] of [[2.05, 1.5, M.copper], [2.62, 1.5, M.steel], [2.9, 1.2, M.copper]]) {
    const arc = new THREE.Mesh(new THREE.TorusGeometry(rr, 0.028, 8, 64, 54 * (Math.PI / 180)), mat);
    arc.rotation.z = 92 * (Math.PI / 180);
    arc.position.z = zz;
    vanes.add(arc);
  }
  septaGroup.add(vanes);

  // The head bay between the eye and the umbilicus (reference: dense silver mechanism, not a dark hole): a second
  // vane row, coarser, with copper and steel tie rods across it.
  const headBay = new THREE.Group();
  headBay.position.set(G.hubX, G.hubY, 0);
  headBay.add(radialFins({r0: 1.25, r1: 3.1, a0: 170 * (Math.PI / 180), a1: 191 * (Math.PI / 180), pitch: 3 * (Math.PI / 180), depth: 0.6, thick: 0.04, z: 1.0, mat: M.steel, minorMat: M.titanium, major: 2, minorLength: 0.6}));
  for (const [rr, zz, mat] of [[1.6, 1.3, M.copper], [2.2, 1.25, M.steel], [2.75, 1.2, M.brass]]) {
    const arc = new THREE.Mesh(new THREE.TorusGeometry(rr, 0.03, 8, 32, 22 * (Math.PI / 180)), mat);
    arc.rotation.z = 169.5 * (Math.PI / 180);
    arc.position.z = zz;
    headBay.add(arc);
  }
  root.add(headBay);

  // ------------------------------------------------------------------ 3B. Large-Radius Circular Ventral Rib Cage & Keel Arch
  const ventralGroup = new THREE.Group();
  root.add(ventralGroup);

  const X_VC = 3.10;
  const Y_VC = 2.05;
  const R_VC = 6.38;
  const ventralCircleRadiusAt = (ang) => {
    const dx = G.hubX - X_VC;
    const dy = G.hubY - Y_VC;
    const ct = Math.cos(ang);
    const st = Math.sin(ang);
    const b = 2.0 * (dx * ct + dy * st);
    const c = dx * dx + dy * dy - R_VC * R_VC;
    return 0.5 * (-b + Math.sqrt(Math.max(0, b * b - 4.0 * c)));
  };

  const bellyAngles = [-116, -123, -130, -137, -144, -150, -156].map((d) => (d * Math.PI) / 180);
  bellyAngles.forEach((ang, idx) => {
    const rOut = ventralCircleRadiusAt(ang);
    const rMid = rOut - 0.92;
    const cx = G.hubX + rMid * Math.cos(ang);
    const cy = G.hubY + rMid * Math.sin(ang);
    const bRing = flangedRing({
      rOuter: 96 - idx * 3,
      rInner: 58 - idx * 2,
      thickness: 14,
      webThickness: 5,
      flangeRim: 8,
      lighteningHoles: 8,
      boltCount: 10,
      bevel: 1.2,
      mat: idx % 2 === 0 ? M.darkGunmetal : M.steel,
      boltMat: M.brass,
      uvScale: 0.015,
    }).group;
    // face the camera (edge-on, the final cut showed them as a row of black and white slats): a row of bolted flanges
    bRing.scale.setScalar(0.0062);
    bRing.position.set(cx, cy, 0.62);
    bRing.rotation.z = ang;
    ventralGroup.add(bRing);
  });

  for (const [rOffset, zOff, rad, mat] of [
    [-0.08, 0.0, 0.095, shellMatWhite],
    [-0.26, 0.32, 0.065, M.steel],
    [-0.26, -0.32, 0.065, M.steel],
    [-0.48, 0.56, 0.055, M.orangeMetal],
    [-0.48, -0.56, 0.055, M.orangeMetal],
  ]) {
    const arcPts = [];
    for (let k = 0; k <= 18; k++) {
      const deg = -106 - (k / 18) * 50;
      const a = (deg * Math.PI) / 180;
      const r = ventralCircleRadiusAt(a) + rOffset;
      arcPts.push([G.hubX + r * Math.cos(a), G.hubY + r * Math.sin(a), zOff]);
    }
    const arcGeo = swept({
        points: arcPts,
        radiusAt: (u) => rad * (1 - 0.18 * u),
        tubularSeg: 36,
        radialSeg: 8,
      });
    const arcMesh = new THREE.Mesh(arcGeo, mat);
    ventralGroup.add(arcMesh);
  }

  for (const deg of [-114, -122, -130, -138, -146, -153]) {
    const a = (deg * Math.PI) / 180;
    const r0 = ventralCircleRadiusAt(a) - 0.65;
    const r1 = ventralCircleRadiusAt(a) - 0.08;
    const pMid = new V3(G.hubX + 0.5 * (r0 + r1) * Math.cos(a), G.hubY + 0.5 * (r0 + r1) * Math.sin(a), 0);
    const strut = new THREE.Mesh(new THREE.BoxGeometry(r1 - r0, 0.09, 0.24), M.structure);
    strut.position.copy(pMid);
    strut.rotation.z = a;
    ventralGroup.add(strut);
  }

  const cheekRibDefs = [
    {pts: [[-0.55, -0.72, 1.12], [0.42, -0.58, 1.32], [1.48, -0.32, 1.46], [2.38, -0.05, 1.50]], r: 0.085, mat: M.steel},
    {pts: [[-0.45, -1.28, 1.08], [0.52, -1.06, 1.28], [1.58, -0.72, 1.42], [2.45, -0.35, 1.48]], r: 0.078, mat: M.orangeMetal},
    {pts: [[1.15, 0.36, 1.22], [1.95, 0.38, 1.34], [2.85, 0.24, 1.42]], r: 0.085, mat: M.steel},
    {pts: [[1.12, -0.10, 1.26], [1.98, -0.04, 1.36], [2.88, -0.06, 1.44]], r: 0.080, mat: M.structure},
  ];
  for (const cr of cheekRibDefs) {
    for (const sy of [-1, 1]) {
      const ptsSigned = cr.pts.map(([x, y, z]) => [x, y, z * sy]);
      const m = new THREE.Mesh(
        swept({points: ptsSigned, radiusAt: (u) => cr.r * (0.85 + 0.25 * Math.sin(u * Math.PI)), scaleZAt: () => 0.65, tubularSeg: 24, radialSeg: 8}),
        cr.mat,
      );
      ventralGroup.add(m);
    }
  }

  // ------------------------------------------------------------------ 4. Tier 1: 03 MHD Power Unit & Dorsal Reactor
  const powerGroup = new THREE.Group();
  const pAng = (122 * Math.PI) / 180;
  const pRad = 3.08;
  powerGroup.position.set(G.hubX + pRad * Math.cos(pAng), G.hubY + pRad * Math.sin(pAng), 0.45);
  powerGroup.rotation.z = pAng - Math.PI / 2;
  root.add(powerGroup);

  const mhdRotorA = new THREE.Mesh(
    gear({teeth: 32, rOut: 0.65, rRoot: 0.54, width: 0.24, helix: 0.35, holeR: 0.28, lighteningHoles: 8, bevel: 0.015, uvScale: 1.2}),
    M.steel,
  );
  mhdRotorA.rotation.y = Math.PI / 2;
  mhdRotorA.position.y = -0.28;

  const mhdRotorB = new THREE.Mesh(
    gear({teeth: 32, rOut: 0.62, rRoot: 0.51, width: 0.22, helix: -0.35, holeR: 0.26, lighteningHoles: 8, bevel: 0.015, uvScale: 1.2}),
    M.orangeMetal,
  );
  mhdRotorB.rotation.y = Math.PI / 2;
  mhdRotorB.position.y = 0.28;

  const reactorCoilL = new THREE.Mesh(
    helix({r: 0.44, wire: 0.042, turns: 7, len: 1.15, seg: 120, uvScale: 1}),
    M.bronze,
  );
  reactorCoilL.position.set(0, -0.58, 0.42);
  const reactorCoilR = reactorCoilL.clone();
  reactorCoilR.position.set(0, -0.58, -0.42);

  const manifoldPlate = new THREE.Mesh(
    machinedPlate({
      w: 145,
      h: 11,
      d: 125,
      r: 12,
      bevel: 1.5,
      holes: [{x: -40, z: 0, r: 20}, {x: 40, z: 0, r: 20}],
      slots: [{x: 0, z: 36, w: 58, d: 16}, {x: 0, z: -36, w: 58, d: 16}],
      uvScale: 0.015,
    }).scale(0.01, 0.01, 0.01),
    M.structure,
  );
  powerGroup.add(mhdRotorA, mhdRotorB, reactorCoilL, reactorCoilR, manifoldPlate);

  // Intertwined Deep-Black & Industrial Signal-Orange Ribbons / Hydraulic Conduits (matching Medusa JF-6)
  const hoseDefs = [
    {pts: [[G.hubX - 0.6, G.hubY + 0.8, 0.95], [G.hubX - 1.5, G.hubY + 1.9, 1.15], [G.eyeX + 0.8, G.eyeY + 1.1, 1.05], [G.eyeX - 0.3, G.eyeY + 0.25, 0.85]], mat: M.hose, r: 0.072},
    {pts: [[G.hubX - 0.6, G.hubY + 0.8, -0.95], [G.hubX - 1.5, G.hubY + 1.9, -1.15], [G.eyeX + 0.8, G.eyeY + 1.1, -1.05], [G.eyeX - 0.3, G.eyeY + 0.25, -0.85]], mat: M.hose, r: 0.072},
    {pts: [[G.hubX - 0.8, G.hubY - 0.5, 0.98], [G.hubX - 2.0, G.hubY - 1.5, 1.06], [G.eyeX - 0.2, G.eyeY - 1.2, 0.82]], mat: M.orangeMetal, r: 0.058},
    {pts: [[G.hubX - 0.8, G.hubY - 0.5, -0.98], [G.hubX - 2.0, G.hubY - 1.5, -1.06], [G.eyeX - 0.2, G.eyeY - 1.2, -0.82]], mat: M.orangeMetal, r: 0.058},
    {pts: [[G.hubX - 0.4, G.hubY - 0.9, 0.82], [G.hubX - 1.8, G.hubY - 2.2, 0.88], [G.eyeX - 0.8, G.eyeY - 2.0, 0.62]], mat: M.hose, r: 0.064},
  ];
  for (const h of hoseDefs) {
    const hMesh = new THREE.Mesh(
      swept({points: h.pts, radiusAt: (u) => h.r - 0.012 * u, tubularSeg: 32, radialSeg: 8}),
      h.mat,
    );
    root.add(hMesh);
  }

  // ------------------------------------------------------------------ 5. Tentacles: 15 plated arms (reference-traced, kin.js)
  // Each arm: a dark gunmetal core (shows in the joints), ceramic sleeves that bend with the arm (kit curveSleeve) on
  // a flattened, ribbon-like section with copper along both edges and a copper lip at every joint, a steel tab at each
  // joint top and bottom (the "barbs" along every arm in the reference), a steel probe tip. The first 12% is bare
  // mechanism: collars on the core, two hoses per arm back into the head, a drive ram.
  const tentacleGroup = new THREE.Group();
  tentacleGroup.name = 'tentacles'; // framing probe (sims/frame-probe) and subsystem lookups
  root.add(tentacleGroup);

  const lathe = (pts) => {
    const g = new THREE.LatheGeometry(pts, 18);
    g.rotateZ(-Math.PI / 2); // lathe axis +Y -> +X
    return g;
  };
  // ribbon section: 1.12 r edge to edge-ish height, 0.6 r deep (reference: flat bands, broad face to the viewer)
  const SEC_RX = 1.12;
  const SEC_RZ = 0.6;
  // sleeve profile along t: copper lip ring (group 1), shoulder, slow taper, rolled distal edge
  const SLEEVE_PROFILE = [[0, 1.09], [0.085, 1.09], [0.11, 1.0], [0.25, 0.995], [0.5, 0.98], [0.75, 0.965], [0.93, 0.95], [1, 0.9]];
  const tabGeo = new THREE.BoxGeometry(0.22, 0.26, 0.2).translate(0, SEC_RX * 1.02, 0); // on the +Y edge of the joint
  const ribGeo = lathe([[0.78, -0.06], [0.96, -0.05], [0.98, 0], [0.96, 0.05], [0.78, 0.06]].map(([r, x]) => new THREE.Vector2(r, x)));
  // split arms: which, how wide the slit (radians each side of the face toward the viewer), the blocks inside
  const SPLIT_ARMS = [5, 6, 9];
  const SLIT = 0.2;
  const slitBlockGeo = new THREE.BoxGeometry(0.45, 0.26, 0.3).translate(0, 0, -SEC_RZ * 0.62); // toward the viewer (-Z)
  const tipGeo = new THREE.ConeGeometry(0.8, 3.2, 10).rotateZ(-Math.PI / 2).translate(1.6, 0, 0); // a slim probe, not a plug

  const tentWear = wearMaps({seed: 23, grain: 0.4, edges: 0.5, chips: 0.6, panels: 0.3, cracks: READ ? 0.06 : 0.28, rivets: 0.0, lineScale: 3.0, ink: P.shell.tentWearInk});
  const tentPlateMat = governMaterial(
    new THREE.MeshPhysicalMaterial({
      map: makeTentacleArmorTexture(false, tentWear.overlay, true),
      bumpMap: tentWear.bumpMap,
      bumpScale: 0.02,
      roughnessMap: tentWear.roughnessMap,
      roughness: 0.5,
      metalness: 0.04,
      clearcoat: 0.1,
      clearcoatRoughness: 0.45,
    }),
    'shell',
  );


  // ram parts along +X, unit length: body (x 0.45..1, anchor end), rod (0..0.55), copper gland band at 0.45
  const ramBodyGeo = new THREE.CylinderGeometry(1, 1, 0.55, 12).rotateZ(-Math.PI / 2).translate(0.725, 0, 0);
  const ramRodGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.6, 10).rotateZ(-Math.PI / 2).translate(0.3, 0, 0);
  const ramBandGeo = new THREE.CylinderGeometry(1.12, 1.12, 0.05, 14).rotateZ(-Math.PI / 2).translate(0.47, 0, 0);
  const RAM_ANCHOR = new V3(G.eyeX + 0.9, G.eyeY - 0.75, 0);
  const PLATE_LEN = 5.2; // plate length in local radii (reference: long sleeves, joints far apart)
  // hose path: from beside the ram anchor, bowing out, to the end of an arm's bare root zone
  const hosePoints = (rootP, endP, side, rb) => {
    const a = new V3(RAM_ANCHOR.x - 0.3, RAM_ANCHOR.y + side * 0.35, rootP[2] * 0.35);
    const e = endP.isVector3 ? endP.clone() : new V3(...endP);
    e.y += side * rb * 0.75;
    const m1 = a.clone().lerp(e, 0.35);
    m1.y += side * 0.45;
    const m2 = a.clone().lerp(e, 0.7);
    m2.y += side * 0.3;
    return [a, m1, m2, e];
  };
  const tentacles = TENTACLE_DEFS.map((def, idx) => {
    const pts0 = sampleTentacle(def, 0, 0);
    // thick at the root, thinning steadily (reference: girth at the head bay, slim outer half, whip tips); the
    // root swell (+25% fading over the first ~15%) packs the roots into one bundle instead of a comb of separate stems
    const rAtCurve = (u) => (READ ? 0.84 : 1) * (def.rTip + (def.rBase - def.rTip) * (1 - u)) * (1 + 0.25 * Math.exp(-u / 0.07));
    const curve0 = new THREE.CatmullRomCurve3(pts0.map((p) => new V3(...p)));
    const L0 = curve0.getLength();

    const coreGeo = swept({points: pts0, radiusAt: (u) => rAtCurve(u) * 0.86, scaleZAt: () => SEC_RZ / SEC_RX, tubularSeg: 80, radialSeg: 12});
    const coreMesh = new THREE.Mesh(coreGeo, polyGunmetal);

    // root zone (first 12%): no armour, the reference shows the arms' mechanism where they leave the head. The core
    // carries collars at an exact pitch there instead, steel with every third one copper.
    const ROOT = 0.12;
    const ribs = [];
    for (let sArc = 0.08; sArc < L0 * ROOT; sArc += 0.2) ribs.push({u: sArc / L0, k: ribs.length});
    // plate stations by arc length: each plate PLATE_LEN radii long, a 5% joint gap, stop short of the tip cone
    const plates = [];
    for (let sArc = L0 * ROOT; sArc < L0 * 0.975; ) {
      const r = rAtCurve(sArc / L0);
      const len = PLATE_LEN * r;
      plates.push({u0: sArc / L0, u1: Math.min(0.995, (sArc + len) / L0), k: plates.length});
      sArc += len * 1.05;
    }
    const depth = THREE.MathUtils.clamp((def.zOff + 1.5) / 3.2, 0, 1); // 0 = back of the bundle, 1 = front
    const plateMat = tentPlateMat.clone();
    plateMat.color.setScalar(READ ? 0.5 + 0.5 * depth : 0.74 + 0.26 * depth); // the final cut: back arms recede
    const plateHolder = new THREE.Group();
    // the big arms (reference: the climber, the diver and two more) are split along the face toward the viewer: an
    // open C-shell with the mechanism showing in the slit, a block at an exact pitch inside each plate
    const split = SPLIT_ARMS.includes(def.id);
    for (const pl of plates) {
      pl.open = split && pl.k % 3 !== 2; // every third plate closed: a major/minor rhythm, not a continuous slot
      pl.sleeve = curveSleeve({radial: 16, profile: SLEEVE_PROFILE, arc: pl.open ? [-Math.PI / 2 + SLIT, (3 * Math.PI) / 2 - SLIT] : null});
      pl.mesh = new THREE.Mesh(pl.sleeve.geometry, [plateMat, READ ? M.alu : M.copper]);
      pl.mesh.frustumCulled = false;
      plateHolder.add(pl.mesh);
    }
    const tabMesh = new THREE.InstancedMesh(tabGeo, polySteel, plates.length * 2);
    const slitMesh = split ? new THREE.InstancedMesh(slitBlockGeo, polyGunmetal, plates.length * 3) : null;
    if (slitMesh) {
      slitMesh.frustumCulled = false;
      const cuTint = new THREE.Color(P.seam.slitTint); // on gunmetal, so the copper block reads warm
      for (let k = 0; k < plates.length * 3; k++) slitMesh.setColorAt(k, k % 3 === 1 ? cuTint : new THREE.Color(1, 1, 1));
    }
    const ribMesh = new THREE.InstancedMesh(ribGeo, polySteel, ribs.length);
    const ribCopper = new THREE.Color(P.seam.ribTint);
    for (const rb of ribs) ribMesh.setColorAt(rb.k, rb.k % 3 === 2 ? ribCopper : new THREE.Color(1, 1, 1));
    for (const o of [tabMesh, ribMesh]) o.frustumCulled = false;
    // two hoses per arm from the head anchor to the end of the bare root zone, one dark, one copper
    const hoses = [-1, 1].map((side) => {
      const hp = hosePoints(pts0[0], curve0.getPointAt(ROOT), side, def.rBase);
      const geo = swept({points: hp, radiusAt: () => 0.05 + 0.012 * side, tubularSeg: 18, radialSeg: 6});
      // dark hoses, a copper one on every third arm only: fifteen copper hoses read as a tangle of orange sticks
      return {side, geo, mesh: new THREE.Mesh(geo, !READ && side > 0 && idx % 3 === 0 ? M.copper : M.hose)};
    });
    const tipMesh = new THREE.Mesh(tipGeo, M.titanium); // titanium: steel reflected the dark surround and read as a black plug

    // drive ram: each arm is pushed by a hydraulic ram anchored deep in the head bay. 14 rams converging on one
    // anchor fill the root zone with mechanism (reference: arms vanish into a dense silver mass, not a ring of roots)
    const ram = new THREE.Group();
    const ramBody = new THREE.Mesh(ramBodyGeo, idx % 2 ? M.steel : M.titanium);
    const ramRod = new THREE.Mesh(ramRodGeo, polySteel);
    const ramBand = new THREE.Mesh(ramBandGeo, M.copper);
    ram.add(ramBody, ramRod, ramBand);
    tentacleGroup.add(coreMesh, plateHolder, tabMesh, ribMesh, tipMesh, ram, ...hoses.map((h) => h.mesh));
    if (slitMesh) plateHolder.add(slitMesh);
    return {def, idx, coreGeo, plates, ribs, plateHolder, tabMesh, ribMesh, slitMesh, tipMesh, hoses, ROOT, rAtCurve, ram, ramBody, ramRod, ramBand};
  });

  // ------------------------------------------------------------------ 6. Tier 1: 05 Omnidirectional Water-Jet Impellers & Plenums
  const jetGroup = new THREE.Group();
  jetGroup.name = 'jets'; // framing probe (sims/frame-probe) and subsystem lookups
  root.add(jetGroup);

  const jetRigs = [
    {deg: -8, rBase: 4.15, z: 0.0, r: 0.34},
    {deg: -22, rBase: 4.22, z: 0.42, r: 0.38},
    {deg: -36, rBase: 4.15, z: -0.42, r: 0.34},
    {deg: -50, rBase: 3.96, z: 0.0, r: 0.28},
  ].map((j) => {
    const a = (j.deg * Math.PI) / 180;
    const dir = new V3(Math.cos(a), Math.sin(a), 0);
    const g = new THREE.Group();
    g.position.set(G.hubX + (j.rBase + 0.32) * Math.cos(a), G.hubY + (j.rBase + 0.32) * Math.sin(a), j.z);
    g.quaternion.setFromUnitVectors(new V3(0, 0, 1), dir);

    const impeller = new THREE.Mesh(
      gear({teeth: 18, rOut: j.r * 0.82, rRoot: j.r * 0.45, width: 0.22, helix: 0.45, holeR: 0.08, bevel: 0.01, uvScale: 1}),
      M.steel,
    );
    const pintle = new THREE.Mesh(
      new THREE.ConeGeometry(j.r * 0.48, 0.42, 12).rotateX(Math.PI / 2),
      M.structure,
    );
    pintle.position.z = 0.18;
    const glowRing = new THREE.Mesh(
      new THREE.TorusGeometry(j.r * 0.62, 0.032, 12, 24),
      M.accent,
    );
    glowRing.position.z = 0.24;
    g.add(impeller, pintle, glowRing);
    jetGroup.add(g);
    return {group: g, impeller, pintle, glowRing, basePos: g.position.clone(), dir};
  });

  // ------------------------------------------------------------------ 7. Tier 3: Instanced Socket Bolts, Counterbore Bosses & Crevice Discs
  const fastenerGroupL = new THREE.Group();
  const fastenerGroupR = new THREE.Group();
  root.add(fastenerGroupL, fastenerGroupR);

  const boltTransformsL = [];
  const boltTransformsR = [];
  const bossTransformsL = [];
  const bossTransformsR = [];
  for (let i = 0; i < 112; i++) {
    const ang = ((140 - (i / 112) * 250) * Math.PI) / 180;
    const rad = 1.18 + (i % 4) * 0.34;
    const isLeft = i % 2 === 0;
    const zSide = (isLeft ? 1 : -1) * (1.58 - (i % 4) * 0.08);
    const o = new THREE.Object3D();
    o.position.set(G.hubX + rad * Math.cos(ang), G.hubY + rad * Math.sin(ang), zSide);
    o.rotation.x = zSide > 0 ? Math.PI / 2 : -Math.PI / 2;
    if (isLeft) {
      boltTransformsL.push(o);
      if (i % 3 === 0) bossTransformsL.push(o);
    } else {
      boltTransformsR.push(o);
      if (i % 3 === 0) bossTransformsR.push(o);
    }
  }
  const boltGeo = bolt({r: 4.5, h: 6.5, washer: true, uvScale: 0.01}).scale(0.01, 0.01, 0.01);
  const bossGeo = counterboreBoss({rOuter: 9.5, rBore: 3.5, rCounter: 6.0, hTotal: 6.0, hCounter: 2.5, bevel: 0.8, uvScale: 0.01}).scale(0.01, 0.01, 0.01);
  fastenerGroupL.add(instanced(boltGeo, M.steel, boltTransformsL), instanced(bossGeo, M.titanium, bossTransformsL));
  fastenerGroupR.add(instanced(boltGeo, M.steel, boltTransformsR), instanced(bossGeo, M.titanium, bossTransformsR));

  // Soft contact crevice rings under the umbilicus hubs & optical eyes
  for (const sy of [-1, 1]) {
    const crHub = creviceRing({rIn: 1.15, rOut: 1.55, opacity: 0.34});
    crHub.position.set(G.hubX, G.hubY, sy * 1.42);
    crHub.rotation.x = sy > 0 ? Math.PI / 2 : -Math.PI / 2;
    const crEye = creviceRing({rIn: 0.55, rOut: 0.85, opacity: 0.36});
    crEye.position.set(G.eyeX, G.eyeY, sy * 1.50);
    crEye.rotation.x = sy > 0 ? Math.PI / 2 : -Math.PI / 2;
    root.add(crHub, crEye);
  }

  root.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });

  // tentacle frame: X along the arm, Y "up" (perpendicular to the arm in the arm's own plane against world Z)
  const tmpP = new V3();
  const tmpPos = new V3();
  const tmpX = new V3();
  const tmpY = new V3();
  const tmpZ = new V3();
  const tmpS = new V3();
  const tmpQ = new THREE.Quaternion();
  const tmpQ2 = new THREE.Quaternion();
  const tmpM = new THREE.Matrix4();
  const tmpB = new THREE.Matrix4();
  const zeroM = new THREE.Matrix4().makeScale(0, 0, 0);
  const flipX = new THREE.Quaternion().setFromAxisAngle(new V3(1, 0, 0), Math.PI);
  const worldZ = new V3(0, 0, 1);
  const unitX = new V3(1, 0, 0);
  const tentFrame = (curve, u) => {
    curve.getPointAt(u, tmpP);
    curve.getTangentAt(u, tmpX).normalize();
    tmpY.crossVectors(tmpX, worldZ);
    if (tmpY.lengthSq() < 1e-6) tmpY.set(0, 1, 0);
    tmpY.normalize();
    tmpZ.crossVectors(tmpX, tmpY);
    tmpQ.setFromRotationMatrix(tmpB.makeBasis(tmpX, tmpY, tmpZ));
  };

  // Teardown stagger: a part with order o (0..1) starts its move once k passes o * SPREAD and finishes at 1, eased.
  // Opening runs in order, closing in reverse (last off, first back on), which is how an assembly comes apart.
  const SPREAD = 0.55;
  const stagger = (k, o) => {
    const u = Math.min(1, Math.max(0, (k - o * SPREAD) / (1 - SPREAD)));
    return u * u * (3 - 2 * u);
  };

  function update(st) {
    if (FOCUS && st.camDist != null) seamLod.update(st.camDist);
    const m = st.mech;
    const ex = st.explode ?? 0; // Full-machine grand wide-shot explosion (0..1)
    const focus = st.focusExplode || {}; // Per-subsystem close-up teardown {core, septa, tentacles, jets}
    const exCore = Math.max(ex, focus.core ?? 0);
    const exSepta = Math.max(ex, focus.septa ?? 0);
    const exTent = Math.max(ex, focus.tentacles ?? 0);
    const exJets = Math.max(ex, focus.jets ?? 0);

    const xray = st.xray ?? 0;
    // the full explode lifts the machine so the lower half's parts stay above the floor (the final cut: they sank through it
    // and read as ghosts)
    root.position.y = 1.7 * ex;
    const section = !!st.section;

    // 1. Two-Stage Hull Explode: combines full-body wide explosion (`ex`) with focused subsystem close-up teardowns (`focus`)
    const hideLiners = ex > 0.06 || exSepta > 0.06 || xray > 0.15;
    for (const item of hullCustomExplode) {
      if (!item.focusKey && item.fullVec.lengthSq() === 0) {
        // Internal backing liners: hide during shell teardowns or X-Ray so the open spiral septa are 100% see-through
        item.obj.visible = !hideLiners;
        continue;
      }
      const fAmt = item.focusKey ? (focus[item.focusKey] ?? 0) : 0;
      item.obj.position.copy(item.basePos);
      if (ex > 0.0005) item.obj.position.addScaledVector(item.fullVec, stagger(ex, item.order));
      if (fAmt > 0.0005) item.obj.position.addScaledVector(item.focusVec, stagger(fAmt, item.order) * (1 - ex * 0.65));
    }

    // 2. X-Ray / Cutaway shell transparency (only swap when state changes so --mask silhouette material is preserved)
    const useGhost = xray > 0.15;
    for (const item of shellMeshes) {
      if (item.wasGhost !== useGhost) {
        item.mesh.material = useGhost ? ghostMat : item.baseMat;
        item.wasGhost = useGhost;
      }
    }
    if (useGhost) {
      ghostMat.opacity = Math.max(0.12, 1 - xray * 0.84);
    }

    // 3. Section clipping plane
    const planes = section && clipPlane ? [clipPlane] : [];
    root.traverse((o) => {
      if (o.isMesh && o.material) {
        if (Array.isArray(o.material)) o.material.forEach((mat) => (mat.clippingPlanes = planes));
        else o.material.clippingPlanes = planes;
      }
    });

    // 4. Pose 01 Command Core, Gyro & Bridge Arm (responds to `exCore` in close-up AND `ex` in grand finale)
    const spin = (st.time ?? 0) * 1.8 + m.stroke * 2.4;
    gyroOuter.rotation.z = spin * 0.7;
    gyroOuter.rotation.x = Math.sin(spin * 0.5) * 0.22;
    gyroOuter.position.z = exCore * 0.75;
    gyroInner.rotation.y = -spin * 1.1;
    gyroInner.position.z = -exCore * 0.75;

    coreGearL.rotation.z = spin * 2.2;
    coreGearL.position.z = 1.44 + exCore * 1.45;
    coreGearR.rotation.z = -spin * 2.2;
    coreGearR.position.z = -1.44 - exCore * 1.45;

    umbilicus.update(spin, exCore);
    hubCap.position.z = 2.06 + exCore * 1.3;
    headBay.position.z = exCore * 0.9 + ex * 1.1;
    hubCapR.position.z = -2.06 - exCore * 1.3;

    innerPinionL.rotation.z = -spin * 3.4;
    innerPinionL.position.z = 1.50 + exCore * 2.05;
    innerPinionR.rotation.z = spin * 3.4;
    innerPinionR.position.z = -1.50 - exCore * 2.05;

    for (const bp of bridgePlates) {
      bp.mesh.position.copy(bp.basePos);
      if (exCore > 0.001) {
        bp.mesh.position.x += Math.cos(bp.aBridge) * exCore * (0.45 + bp.idx * 0.14);
        bp.mesh.position.y += Math.sin(bp.aBridge) * exCore * (0.45 + bp.idx * 0.14);
        bp.mesh.position.z += bp.sy * exCore * (0.85 + bp.idx * 0.12);
      }
    }

    fastenerGroupL.position.z = exCore * 1.85 + ex * 0.95;
    fastenerGroupR.position.z = -(exCore * 1.85 + ex * 0.95);

    // 5. Pose 02 Spiral Septa, Ballast Pistons & Ventral Keel (responds to `exSepta` and `ex`)
    septaBulkheads.forEach((b, i) => {
      const fill = m.chamberFill[i] ?? 0.3;
      b.piston.position.z = (fill - 0.5) * 0.45 + exSepta * 0.85;
      b.group.position.copy(b.basePos);
      b.strut.position.copy(b.strutBasePos);
      if (exSepta > 0.001) {
        const kS = stagger(exSepta, i / Math.max(1, septaBulkheads.length - 1));
        const rPush = (1.55 + ex * 1.25) * kS;
        const zOff = ((i % 2 === 0 ? 1 : -1) * 0.65) * kS;
        b.group.position.x += Math.cos(b.ang) * rPush;
        b.group.position.y += Math.sin(b.ang) * rPush;
        b.group.position.z += zOff;
        b.strut.position.x += Math.cos(b.ang) * rPush * 0.65;
        b.strut.position.y += Math.sin(b.ang) * rPush * 0.65;
        b.strut.position.z += zOff * 1.2;
      }
    });
    siphuncleMesh.position.z = exSepta * 0.55;
    vanes.position.z = exSepta * 0.9 + ex * 1.2;
    ventralGroup.position.set(-ex * 0.6, -ex * 1.0, 0);

    // 6. Pose 03 MHD Power Unit (responds to `exSepta` and `ex`)
    mhdRotorA.rotation.x = spin * 3.2;
    mhdRotorA.position.y = -0.28 - exSepta * 0.65;
    mhdRotorB.rotation.x = -spin * 3.2;
    mhdRotorB.position.y = 0.28 + exSepta * 0.65;
    reactorCoilL.position.z = 0.42 + exSepta * 0.75;
    reactorCoilR.position.z = -0.42 - exSepta * 0.75;
    const pPush = exSepta * 1.65 + ex * 1.15;
    powerGroup.position.set(
      G.hubX + (pRad + pPush) * Math.cos(pAng),
      G.hubY + (pRad + pPush) * Math.sin(pAng),
      0.45 + exSepta * 0.45,
    );

    // 7. Tentacles (wave from kin.js; exTent spreads the bundle and lifts the plates off the core)
    const lift = (focus.tentacles ?? 0) * 0.5 + ex * 0.9;
    for (const t of tentacles) {
      const pts = sampleTentacle(t.def, m.wavePhase, m.waveAmp);
      if (exTent > 0.001) {
        const spreadY = (7.5 - t.idx) * 0.16 * (exTent * 0.65 + ex * 0.85);
        for (const p of pts) {
          p[0] -= ex * 1.5 + (focus.tentacles ?? 0) * 0.85;
          p[1] += spreadY;
          p[2] += Math.sign(t.def.zOff || 0.1) * (ex * 0.9 + (focus.tentacles ?? 0) * 0.65);
        }
      }
      updateSwept(t.coreGeo, pts);
      const curve = new THREE.CatmullRomCurve3(pts.map((p) => new V3(...p)));
      const L = curve.getLength();
      for (const pl of t.plates) {
        tmpPos.set(0, 0, 0);
        if (lift > 0.001) {
          tentFrame(curve, 0.5 * (pl.u0 + pl.u1));
          const sgn = pl.k % 2 === 0 ? 1 : -1;
          // plates come off root to tip, a wave down the arm (lift is up to ~1.4: stagger on its 0..1 part)
          const lk = Math.min(1, lift) > 0 ? stagger(Math.min(1, lift), pl.u0) * Math.max(1, lift) : 0;
          tmpPos.addScaledVector(tmpY, sgn * lk * (1 - 0.35 * pl.u0)).addScaledVector(tmpZ, ((pl.k % 3) - 1) * lk * 0.5);
        }
        pl.sleeve.update(curve, pl.u0, pl.u1, t.rAtCurve, {rx: SEC_RX, rz: SEC_RZ, offset: tmpPos});
        if (t.slitMesh)
          for (let q = 0; q < 3; q++) {
            if (!pl.open) {
              t.slitMesh.setMatrixAt(pl.k * 3 + q, zeroM);
              continue;
            }
            const offs = tmpPos.clone();
            tentFrame(curve, pl.u0 + (pl.u1 - pl.u0) * (0.22 + 0.28 * q));
            const rq = t.rAtCurve(pl.u0);
            tmpS.set(rq, rq, rq);
            tmpM.compose(tmpP.add(offs), tmpQ, tmpS);
            t.slitMesh.setMatrixAt(pl.k * 3 + q, tmpM);
          }
        // tabs at the plate's proximal joint, on both edges
        tentFrame(curve, pl.u0 + 0.01 * (pl.u1 - pl.u0));
        const r = t.rAtCurve(pl.u0);
        tmpS.set(r, r, r);
        for (const side of [0, 1]) {
          tmpQ2.copy(tmpQ);
          if (side) tmpQ2.multiply(flipX);
          tmpM.compose(tmpP, tmpQ2, tmpS);
          t.tabMesh.setMatrixAt(pl.k * 2 + side, tmpM);
        }
      }
      for (const rb of t.ribs) {
        tentFrame(curve, rb.u);
        const rr = t.rAtCurve(rb.u);
        tmpS.set(rr, rr * SEC_RX * 0.95, rr * SEC_RZ);
        tmpM.compose(tmpP, tmpQ, tmpS);
        t.ribMesh.setMatrixAt(rb.k, tmpM);
      }
      t.ribMesh.instanceMatrix.needsUpdate = true;
      t.tabMesh.instanceMatrix.needsUpdate = true;
      if (t.slitMesh) t.slitMesh.instanceMatrix.needsUpdate = true;
      t.plateHolder.visible = xray < 0.75;
      for (const h of t.hoses) updateSwept(h.geo, hosePoints(pts[0], curve.getPointAt(t.ROOT), h.side, t.def.rBase));
      tentFrame(curve, 0.99);
      t.tipMesh.position.copy(tmpP);
      t.tipMesh.quaternion.copy(tmpQ);
      t.tipMesh.scale.setScalar(t.rAtCurve(0.99) * 0.9);
      // ram from the arm root (rod end) to a point 80% of the way to the anchor (body end)
      tmpPos.set(...pts[0]);
      tmpX.copy(RAM_ANCHOR).sub(tmpPos);
      tmpX.z *= 0.4; // rams keep most of their arm's depth: a layered bundle, not a single cone
      const ramLen = tmpX.length() * 0.8;
      tmpX.normalize();
      t.ram.position.copy(tmpPos);
      t.ram.quaternion.setFromUnitVectors(unitX, tmpX);
      t.ram.scale.set(ramLen, t.def.rBase * 0.62, t.def.rBase * 0.62);
    }

    // 8. Pose 05 Water-Jet Thrusters (responds to `exJets` and `ex`)
    for (const j of jetRigs) {
      j.impeller.rotation.z = spin * 4.5;
      j.impeller.position.z = exJets * 0.65;
      j.pintle.position.z = 0.22 + m.stroke * 0.24 + exJets * 1.35;
      j.glowRing.position.z = 0.24 + exJets * 1.02;
      j.group.position.copy(j.basePos).addScaledVector(j.dir, exJets * 1.55 + ex * 0.8 + m.stroke * 0.12);
    }
  }

  for (const [m, g] of lateDetail) m.add(g);
  metalReport(root);

  return {
    root,
    hullRoot,
    hullParts,
    hullRig,
    materials: M,
    update,
  };
}
