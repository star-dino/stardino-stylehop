/**
 * Mechanical Nautilus (Archive / 007) · stylehop world.
 *
 * Port of the teardown stage + film (`src/stage.js`, `film.js`, `console.js`) onto the stylehop engine:
 *   - stage     : studio look (`CAL_LOOK` merged with the teardown stage palette + `ref.json` palette), warm backdrop,
 *                 drifting bathymetric floor grid + soft floor shadow, GTAO + ink lines from the look rig.
 *   - film      : the 26 s teardown script (SCRIPT / VIEW_FN / camAt / distAt) as 5 `data-scene`s. The camera is the
 *                 original `camAt` (az / el / d / target / screen offset) on 16:9 so renders match `ref/*.png`; on other
 *                 aspects the director (`studio.director`) frames the same subjects instead.
 *   - HUD       : `createGaugeHud` carries the console readings (title, pressure, subsystem strip = camera views, phase
 *                 caption, operator cursor, callout leaders).
 */
import { clamp, lerp } from '/engine/motion.js';
import { resolveLook } from '/engine/look.js';
import { THREE, createCalLabStudio, createGaugeHud } from '/styles/calibration-lab/kernel.js';
import { buildNautilus } from './sample/nautilus-model.js';
import { studioEnvironment } from './sample/kit-compat.js';
import { P as NP } from './sample/palette.js';
import { G, mechAt, phaseAt, SEQ, uToX, vToY } from './sample/kin.js';

const D2R = Math.PI / 180;

// ------------------------------------------------------------------------------------------------ stage constants
// teardown palette.js `A.stage` (bg is replaced by ref.json palette.background when present)
const STAGE = {
  bg: '#EFECE6', ground: '#ECE8E0', mark: '#D5CEC2', shadow: '#5D564C',
  surround: '#46494f', sun: '#FFF8EE', ink: '#242830', shadowOpacity: 0.2,
};
const FLOOR_Y = -4.48;
const SUN_DIR = new THREE.Vector3(-0.28, 0.84, 0.46).normalize();
const SUN_POS = SUN_DIR.clone().multiplyScalar(24).toArray();

// ------------------------------------------------------------------------------------------------ film script (film.js)
const smoother = (x) => {
  const u = Math.min(1, Math.max(0, x));
  return u * u * u * (u * (u * 6 - 15) + 10);
};
const ss = (a, b, t) => smoother((t - a) / Math.max(1e-6, b - a));
const pulseWindow = (t0, t1, t2, t3, t) => ss(t0, t1, t) * (1 - ss(t2, t3, t));

const DURATION = 26.0;
const SCRIPT = [
  { t: 0.0, seq: 'cruise', view: 'hero' },
  { t: 2.2, display: 'labels' },
  { t: 3.8, view: 'core' },
  { t: 7.8, seq: 'dive', view: 'septa' },
  { t: 11.0, display: 'labels' },
  { t: 11.6, view: 'tentacles' },
  { t: 14.5, view: 'jets' },
  { t: 15.6, seq: 'cruise' },
  { t: 17.3, view: 'hero' },
  { t: 18.0, display: 'exploded' },
  { t: 18.6, display: 'orbit' },
  { t: 21.8, display: 'exploded' },
  { t: 23.2, display: 'orbit' },
];
const DISPLAY = ['labels', 'section', 'xray', 'exploded', 'orbit'];

const focusExplodeAt = (t) => ({
  core: pulseWindow(4.2, 5.4, 6.4, 7.5, t),
  septa: pulseWindow(8.2, 9.4, 10.3, 11.4, t),
  tentacles: pulseWindow(11.9, 13.0, 13.5, 14.4, t),
  jets: pulseWindow(14.9, 16.0, 16.4, 17.2, t),
});
const seqAt = (t) => {
  const e = SCRIPT.filter((x) => x.seq && x.t <= t).pop();
  return { seq: e.seq, tau: (t - e.t) % SEQ[e.seq].dur };
};
const displayAt = (t) => {
  const out = Object.fromEntries(DISPLAY.map((k) => [k, 0]));
  for (const e of SCRIPT) if (e.display && e.t <= t) out[e.display] = out[e.display] ? 0 : 1;
  return out;
};
const lastFlip = (key, t) => SCRIPT.filter((e) => e.display === key && e.t <= t).pop()?.t ?? -9;
const easedDisplay = (key, t, dur = 0.75) => {
  const on = displayAt(t)[key];
  const k = ss(lastFlip(key, t), lastFlip(key, t) + dur, t);
  return on ? k : 1 - k;
};

// distance swum, pre-integrated so render(t) stays a pure function of t
const DT = 1 / 120;
const DIST = [0];
for (let i = 1; i * DT <= DURATION + 1; i++) {
  const { seq, tau } = seqAt((i - 0.5) * DT);
  DIST.push(DIST[i - 1] + mechAt(seq, tau).speed * DT * 0.45);
}
const distAt = (t) => {
  const u = Math.max(0, Math.min(DIST.length - 2, t / DT));
  const i = Math.floor(u);
  return DIST[i] + (DIST[i + 1] - DIST[i]) * (u - i);
};

// camera views (film.js VIEW_FN, FOCUS look), each 1.2x pulled out with a slow drift
const PULL = 1.2;
const drift = (base, u, { daz = 0, push = 0.06, dur = 4 } = {}) => {
  const k = Math.min(1, Math.max(0, u / dur));
  return { ...base, az: base.az + daz * k, d: base.d * PULL * (1 - push * k), sx: base.sx / PULL, sy: base.sy / PULL };
};
const VIEW_FN = {
  hero: (u) => drift({ tx: -0.18, ty: -0.34, tz: -0.07, az: 0, el: 0, d: 32.4 * 0.9, sx: 18, sy: 26 }, u, { daz: 2.5, push: 0.04, dur: 3.8 }),
  core: (u) => drift({ tx: 3.1, ty: 0.1, tz: 0.85, az: 20, el: 8, d: 19.6, sx: 135, sy: -3 }, u, { daz: 3, dur: 4 }),
  septa: (u) => drift({ tx: 3.5, ty: 2.2, tz: 1.2, az: -10, el: 22, d: 26.1, sx: 11, sy: 7 }, u, { daz: 3, push: 0.08, dur: 3.8 }),
  tentacles: (u) => drift({ tx: -4.19, ty: -1.34, tz: 0, az: -24, el: 10, d: 23.8, sx: 56, sy: 7 }, u, { daz: 2.5, dur: 2.9 }),
  jets: (u) => drift({ tx: 8.6, ty: -1.9, tz: 0, az: 52, el: 2, d: 28.4, sx: 6, sy: 3 }, u, { daz: 5, push: 0.1, dur: 2.8 }),
  front: (u) => ({ tx: -1.1, ty: -0.08, tz: 0, az: -68 + 2.2 * u, el: 5, d: 21.8, sx: -16, sy: -46 }),
};
const EXPLODE_CAM = { tx: 0.11, ty: 1.65, tz: 0.04, az: 0, el: 10, d: 44.3 * PULL, sx: 17 / PULL, sy: 19 / PULL };
const VIEWS = SCRIPT.filter((e) => e.view).map((e) => [e.t, e.view]);

const blend = (a, b, k, bump = true) => {
  const o = {};
  for (const key in b) {
    o[key] = key === 'az' ? a.az + (((b.az - a.az + 540) % 360) - 180) * k : a[key] + (b[key] - a[key]) * k;
  }
  const swing = Math.min(1, Math.abs(((b.az - a.az + 540) % 360) - 180) / 90);
  if (bump) o.d += Math.max(0, Math.max(a.d, b.d) + 1.2 * swing - o.d) * Math.sin(Math.PI * k) * swing;
  return o;
};
const camAt = (t, orbit = 0, explode = 0) => {
  let i = 0;
  while (i < VIEWS.length - 1 && VIEWS[i + 1][0] <= t) i++;
  const cur = VIEW_FN[VIEWS[i][1]](t - VIEWS[i][0]);
  let o = { ...cur };
  if (i > 0) {
    const k = ss(VIEWS[i][0], VIEWS[i][0] + 1.5, t);
    if (k < 1) o = blend(VIEW_FN[VIEWS[i - 1][1]](t - VIEWS[i - 1][0]), cur, k);
  }
  if (explode > 0.001) o = blend(o, EXPLODE_CAM, explode, false);
  if (orbit > 0) {
    const t0 = lastFlip('orbit', t);
    const t1 = SCRIPT.find((e) => e.display === 'orbit' && e.t > t0)?.t ?? DURATION;
    const k = Math.min(1, Math.max(0, (t - t0) / (t1 - t0)));
    o.az += 30 * Math.sin(Math.PI * smoother(k)) * orbit;
    o.el += 4 * Math.sin(Math.PI * smoother(k)) * orbit;
  }
  return o;
};
const viewAt = (t) => VIEWS.filter(([a]) => a <= t).pop();

// ------------------------------------------------------------------------------------------------ HUD content
const VIEW_STRIP = [
  ['hero', 'HERO ¾'],
  ['core', '01 CORE'],
  ['septa', '02 SEPTA'],
  ['tentacles', '04 TENTACLES'],
  ['jets', '05 JETS'],
];
const STRIP_LABELS = [...VIEW_STRIP.map((v) => v[1]), 'EXPLODED'];
// operator cursor presses a strip cell at each view change and when the explode starts
const CLICKS = [
  ...SCRIPT.filter((e) => e.view && e.t > 0).map((e) => ({ t: e.t, idx: VIEW_STRIP.findIndex((v) => v[0] === e.view) })),
  { t: 18.0, idx: 5 },
  { t: 21.8, idx: 0 },
].sort((a, b) => a.t - b.t);

const PARTS = [
  { name: 'SPIRAL SHELL ARMOR', sub: 'LAYERED CERAMIC COMPOSITE · 07', at: [uToX(0.76), vToY(0.88), 0.8] },
  { name: 'DORSAL REACTOR CUTAWAY', sub: 'MHD TURBINE & HELICAL COILS', at: [uToX(0.62), vToY(0.82), 0.6] },
  { name: 'OPTICAL SENSOR MODULE', sub: 'CONCENTRIC IRIS GIMBAL', at: [G.eyeX, G.eyeY, G.eyeZ] },
  { name: 'UMBILICUS COMMAND CORE', sub: 'GYROSCOPIC PRESSURE HUB', at: [G.hubX, G.hubY, 1.45] },
  { name: 'VENTRAL CHEEK LOBE', sub: 'APERTURE FLANGE SHIELD', at: [uToX(0.62), vToY(0.24), 1.6] },
  { name: 'TENTACLE ARRAY', sub: '15 PLATED APPENDAGES', at: [uToX(0.26), vToY(0.32), 0.7] },
  { name: 'PROPULSION SYSTEM', sub: '4× OMNIDIRECTIONAL WATER-JETS', at: [uToX(0.94), vToY(0.36), 0.3] },
];

// ------------------------------------------------------------------------------------------------ floor
const FLOOR_VERT = /* glsl */ `
varying vec3 vW;
void main() {
  vec4 w = modelMatrix * vec4(position, 1.0);
  vW = w.xyz;
  gl_Position = projectionMatrix * viewMatrix * w;
}`;
const FLOOR_FRAG = /* glsl */ `
uniform vec3 uG;
uniform vec3 uM;
uniform vec3 uBg;
uniform float uSwim;
uniform vec3 uC;
varying vec3 vW;
void main() {
  float x = vW.x - uSwim;
  float z = vW.z;
  float gx = step(abs(mod(x + 1.5, 3.0) - 1.5), 0.025);
  float gz = step(abs(mod(z + 1.5, 3.0) - 1.5), 0.025);
  float tick = step(abs(mod(x + 0.3, 0.6) - 0.3), 0.015) * step(abs(z), 0.25);
  float m = max(max(gx, gz) * 0.55, tick * 0.85);
  float n = fract(sin(dot(floor(vW.xz * 28.0), vec2(12.9898, 78.233))) * 43758.5453);
  vec3 col = mix(uG, uM, m) * (0.99 + 0.02 * n);
  float d = length(vW.xz - uC.xz);
  vec3 outc = mix(col, uBg, smoothstep(10.0, 28.0, d));
  gl_FragColor = linearToOutputTexel(vec4(outc, 1.0));
}`;

// ------------------------------------------------------------------------------------------------ world
export default async function createWorld({ width, height, scenes = [], style = {} } = {}) {
  const ref = style.ref && style.ref.palette ? style.ref.palette : {};
  const bg = ref.background || STAGE.bg;
  const mix = (a, b, t) => '#' + [1, 3, 5].map((i) => Math.round(parseInt(a.slice(i, i + 2), 16) * (1 - t) + parseInt(b.slice(i, i + 2), 16) * t).toString(16).padStart(2, '0')).join('');
  const groundCol = mix(bg, '#FFFFFF', 0.6); // ref floor reads lighter than the backdrop (teardown stage.js: ground #ECE8E0 vs bg, shown un-tonemapped); fades into bg at distance
  const markCol = mix(groundCol, '#000000', 0.07);

  // teardown stage.js -> look tokens (energy budget replaces the per-light intensities; r147 lights are in the
  // legacy unit, so r186 sun 2.7 ~ 0.86 here)
  const stageLook = {
    color: { output: 'srgb', toneMapping: 'linear', exposure: 1.0 },
    light: {
      illuminance: 1.75,
      keyRatio: 3.6,
      key: {
        color: STAGE.sun,
        pos: SUN_POS,
        shadow: { type: 'vsm', mapSize: 2048, extent: [15, 15], near: 2, far: 54, bias: -0.0004, normalBias: 0.006, radius: 7, blurSamples: 16 },
      },
      bounce: { color: '#FAF8F3', pos: [-6, 4, 24], share: 0.5 },
      rim: { color: '#E2EAF5', pos: [-14, 14, -12], ratio: 0.45 },
    },
    env: { enabled: true, share: 0.7, softbox: 3.2, studioStrips: false, surround: STAGE.surround },
    backdrop: { color: bg, fog: 0.0025 },
    contact: { enabled: false },
    ao: {
      enabled: true, intensity: 0.5, radius: 0.8, thickness: 1.25, distanceExponent: 1.5, distanceFallOff: 1.0, scale: 0.85,
      samples: 16, denoiseRadius: 6, lumaPhi: 10, depthPhi: 2, normalPhi: 3, inkStrength: 0.26, inkColor: STAGE.ink,
    },
  };
  const studio = createCalLabStudio({ width, height, scenes, style: { ...style, look: resolveLook(stageLook, style.look) }, maxDist: null });
  studio.bench.visible = false;
  studio.scene.add(studio.camera);
  const camera = studio.camera;
  const scene = studio.scene;

  const hud = createGaugeHud({ camera, width, height });

  // floor: grid that drifts with the distance swum + a shadow catcher on top
  const floorMat = new THREE.ShaderMaterial({
    vertexShader: FLOOR_VERT,
    fragmentShader: FLOOR_FRAG,
    uniforms: {
      uG: { value: new THREE.Color(groundCol) },
      uM: { value: new THREE.Color(markCol) },
      uBg: { value: new THREE.Color(bg) },
      uSwim: { value: 0 },
      uC: { value: new THREE.Vector3() },
    },
    side: THREE.DoubleSide,
    fog: false,
  });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(240, 240), floorMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = FLOOR_Y;
  ground.userData.skipContactShadow = true;
  ground.userData.noSilhouette = true;
  scene.add(ground);
  const shade = new THREE.Mesh(
    new THREE.PlaneGeometry(240, 240),
    new THREE.ShadowMaterial({ color: STAGE.shadow, opacity: STAGE.shadowOpacity, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -8 }),
  );
  shade.rotation.x = -Math.PI / 2;
  shade.position.y = FLOOR_Y + 0.002;
  shade.receiveShadow = true;
  shade.userData.skipContactShadow = true;
  shade.userData.noSilhouette = true;
  scene.add(shade);

  // the machine
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0.08);
  const nautilus = await buildNautilus({ clipPlane, studio });
  // Metal reads by what it reflects (teardown stage.js): bright softboxes on a dark surround. The engine's pale
  // gradient dome turns every metal into grey plastic, so the subject's materials opt out of the look rig's IBL
  // and carry teardown's studio environment at its own intensity.
  const tdEnv = studioEnvironment(studio.renderer, { surround: NP.stage.surround, floor: NP.stage.envFloor });
  nautilus.root.traverse((o) => {
    const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
    for (const m of mats) {
      if (!m.isMeshStandardMaterial || m.userData.tdEnv) continue;
      m.userData.tdEnv = true;
      m.userData.lookEnv = false;
      m.envMap = tdEnv;
      m.envMapIntensity = (m.envMapIntensity ?? 1) * NP.stage.envIntensity;
      m.needsUpdate = true;
    }
  });
  const subjectRoot = new THREE.Group();
  subjectRoot.name = 'MechNautilusRoot';
  subjectRoot.add(nautilus.root);
  scene.add(subjectRoot);
  let anyCast = false;
  nautilus.root.traverse((o) => { if (o.isMesh && o.castShadow) anyCast = true; });
  if (!anyCast) nautilus.root.traverse((o) => { if (o.isMesh) o.castShadow = true; });

  // director subjects (boxes in the nautilus frame) for non-16:9 aspects and the storyboard
  const subjects = {
    machine: { center: [-0.2, -0.3, 0], size: [19.2, 8.8, 5.2] },
    core: { center: [G.hubX, G.hubY, 0.6], size: [5.4, 5.4, 3.6] },
    septaWindow: { center: [3.5, 2.2, 1.0], size: [7.0, 5.0, 3.2] },
    tentacles: { center: [-4.6, -1.3, 0], size: [10.0, 6.2, 4.6] },
    jets: { center: [8.4, -1.6, 0], size: [4.6, 5.6, 4.6] },
    exploded: { center: [0.1, 1.65, 0], size: [24, 15, 9] },
  };
  const shots = {
    'hero-establish': [{ subject: 'machine', size: 'full', angle: 0, height: 2, move: 'push', amount: 0.3 }],
    'core-teardown': [{ subject: 'core', size: 'close', angle: 20, height: 8, move: 'push', amount: 0.4 }],
    'septa-teardown': [{ subject: 'septaWindow', size: 'close', angle: -10, height: 22, move: 'push', amount: 0.5 }],
    'tentacles-jets': [
      { dur: 2.9, subject: 'tentacles', size: 'medium', angle: -24, height: 10, move: 'push', amount: 0.4 },
      { subject: 'jets', size: 'medium', angle: 52, height: 2, move: 'push', amount: 0.6 },
    ],
    'full-explode': [
      { dur: 0.7, subject: 'machine', size: 'full', angle: 0, height: 2 },
      { subject: 'exploded', size: 'full', angle: 0, height: 10, move: 'orbit', amount: 1.5 },
    ],
  };
  const director = studio.director({ subjects, shots });

  const aspect = camera.aspect;
  const exact = aspect >= 1.6;
  const tmpCam = new THREE.Vector3();
  const tanV = Math.tan((camera.fov * D2R) / 2);

  function setExactCamera(cam, W, H) {
    const az = cam.az * D2R;
    const el = cam.el * D2R;
    camera.position.set(
      cam.tx + cam.d * Math.cos(el) * Math.sin(az),
      cam.ty + cam.d * Math.sin(el),
      cam.tz + cam.d * Math.cos(el) * Math.cos(az),
    );
    camera.up.set(0, 1, 0);
    camera.lookAt(cam.tx, cam.ty, cam.tz);
    // the original used a lens shift (setViewOffset, in 1600x900 px); a small yaw / pitch gives the same image shift
    // without moving the HUD plane that rides on the camera
    const k = W / 1600;
    const nx = ((cam.sx ?? 0) * k) / (W / 2);
    const ny = ((cam.sy ?? 0) * k) / (H / 2);
    camera.rotateY(Math.atan(nx * tanV * (W / H)));
    camera.rotateX(Math.atan(ny * tanV));
    camera.updateMatrixWorld(true);
  }

  function cursorAt(t, stripIdx) {
    if (t < 0.05) return null;
    let i = -1;
    while (i + 1 < CLICKS.length && CLICKS[i + 1].t <= t) i++;
    const next = CLICKS[i + 1];
    const prev = i >= 0 ? CLICKS[i] : { t: 0, idx: 0 };
    const fade = ss(0.05, 0.5, t);
    if (next && next.t - t < 0.55) {
      const mk = ss(next.t - 0.55, next.t - 0.06, t);
      return { fromIndex: prev.idx, toIndex: next.idx, moveK: mk, opacity: fade, press: 0, ring: 0 };
    }
    const dt = t - prev.t;
    const press = i >= 0 && dt < 0.12 ? 1 : 0;
    const ring = i >= 0 && dt < 0.55 ? 1 - dt / 0.55 : 0;
    return { fromIndex: prev.idx, toIndex: prev.idx, moveK: 1, opacity: fade, press, ring };
  }

  const tmpSun = new THREE.Vector3();

  function render(frame = { t: 0, sceneIndex: 0, localT: 0 }) {
    const t = frame.t ?? frame.globalT ?? 0;
    const { seq, tau } = seqAt(t);
    const m = mechAt(seq, tau);
    const disp = displayAt(t);
    const explode = easedDisplay('exploded', t, 1.6);
    const focusExplode = focusExplodeAt(t);
    const xray = easedDisplay('xray', t, 0.7);

    director.update(frame); // frames every aspect; on 16:9 the original camera below replaces it
    let camD;
    if (exact) {
      const cam = camAt(t, disp.orbit, explode);
      setExactCamera(cam, width, height);
      camD = cam.d;
    } else {
      camera.updateMatrixWorld(true);
      camD = camera.getWorldPosition(tmpCam).distanceTo(tmpSun.set(0, 0, 0));
    }

    nautilus.update({ time: t, mech: m, dist: distAt(t), explode, focusExplode, xray, section: !!disp.section, camDist: camD });
    floorMat.uniforms.uSwim.value = distAt(t);
    const tgt = camera.getWorldDirection(tmpSun).multiplyScalar(camD).add(camera.position);
    floorMat.uniforms.uC.value.set(tgt.x, FLOOR_Y, tgt.z);

    // HUD
    const [vt0, view] = viewAt(t);
    const labelsK = easedDisplay('labels', t, 0.5) * ss(vt0 + 0.5, vt0 + 1.1, t);
    const exAmt = Math.max(explode, focusExplode.core, focusExplode.septa, focusExplode.tentacles, focusExplode.jets);
    const stripIdx = explode > 0.5 || (t >= 18.0 && t < 23.4) ? 5 : Math.max(0, VIEW_STRIP.findIndex((v) => v[0] === view));
    const state = m.state; // [title, sub, kind]
    hud.fit();
    hud.draw({
      accent: studio.refPalette?.accent,
      title: 'MECHANICAL NAUTILUS',
      subtitle: 'ARCHIVE / 007 · ARTIFICIAL MARINE LIFEFORM',
      big: { label: state[0], value: m.pressure.toFixed(1), unit: 'MPa' },
      phase: {
        labels: STRIP_LABELS,
        index: stripIdx,
        caption: `${phaseAt(seq, tau)} · ${state[1]}${exAmt > 0.05 ? ' · TEARDOWN ' + Math.round(exAmt * 100) + '%' : ''}`,
      },
      callouts: PARTS.map((p, i) => ({
        worldPos: [p.at[0], p.at[1] + nautilus.root.position.y, p.at[2]],
        label: p.name,
        sub: p.sub,
        accent: i === 2 || i === 3,
        opacity: labelsK,
      })),
      cursor: cursorAt(t, stripIdx),
    });

    studio.render(frame);
  }

  render({ t: 0, sceneIndex: 0, localT: 0, scene: scenes[0] });

  return {
    canvas: studio.canvas,
    scene,
    camera,
    subjectRoot,
    render,
    storyboard: () => director.storyboard(),
  };
}
