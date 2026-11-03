/**
 * Three.js Look Profile & Light Energy Budget (`engine/look.js`).
 *
 * One declarative `look` object owns everything that decides how a 3D style *reads*:
 * colour pipeline, light rig, image-based lighting, backdrop/fog and contact shadows.
 * Styles declare it once (kernel default, optionally overridden in `style.js -> look`),
 * worlds never touch renderer/light settings directly.
 *
 * Energy budget — why adding an effect does not swing the whole image:
 *   `light.illuminance` is the fixed total. `light.keyRatio` splits it into key vs ambient
 *   (key : ambient = ratio : 1). The ambient part is then *shared* between the hemisphere
 *   fill, the bounce light and the IBL environment (`bounce.share`, `env.share`). Turning
 *   the environment on, or raising its share, takes energy away from the hemisphere fill
 *   instead of adding on top, so exposure and light ratio stay put and only the *quality*
 *   of the light changes (softbox highlights, directional occlusion).
 *   Verify any change with `python3 tools/lookcheck.py --style <id>`.
 *
 * ref.json drives defaults (ADR-021 colour/light gate work): `lookFromRefPalette(palette)` turns a product's declared
 *   palette (background / shell / mechanism / accent / glow / warm_metal / light.kelvin) into a look layer that sits
 *   BETWEEN the style defaults and the product's own `style.look` (product overrides still win). No palette -> `{}`,
 *   so products that do not declare one render exactly as before.
 * Role studio (ADR-021): when a world uses `glaze` / `metal` material roles, `augmentLookForRoles` gives the studio a
 *   softbox environment (`env.softboxRig`: bright panels in a darker surround, so metal has something bright to reflect),
 *   `keyRatio >= 3` (key >= 3x the sum of fills) and a rim light (`light.rim`). Opt out per item or wholesale with
 *   `look.studio = { auto: false }` / `{ softbox: false, keyRatio: false, rim: false }`. Looks without those roles are untouched.
 *
 * Usage: styles normally go through `engine/studio3d.js -> createStudio3D`, which creates the
 * rig, the per-scene look timeline and the director. Direct use:
 *   const look = createLookRig(THREE, { renderer, scene, look: resolveLook(DEFAULTS, style.look) });
 *   ...build world...
 *   look.render(camera);   // contact shadow + material sync + main render
 */

import { createGTAORig } from './gtao.js';

export const LOOK_DEFAULTS = {
  color: {
    output: 'srgb', // 'srgb' (correct) | 'legacy' (pre-r152 linear output, washed out)
    toneMapping: 'aces', // 'aces' | 'cineon' | 'reinhard' | 'linear' | 'none'
    exposure: 1.0,
  },
  light: {
    illuminance: 2.0, // total key + ambient budget
    keyRatio: 2.5, // key : ambient
    key: {
      color: '#FFF5E0',
      pos: [-10, 22, 16],
      shadow: {
        type: 'pcf-soft', // 'pcf-soft' | 'vsm' | 'pcf' | 'basic'
        mapSize: 2048,
        extent: [16, 14],
        near: 2,
        far: 65,
        bias: -0.0005,
        normalBias: 0.02,
        radius: 1,
        blurSamples: 8,
      },
    },
    sky: '#FFF8EB',
    ground: '#D9A796',
    bounce: { color: '#FFC6B0', pos: [12, -6, 10], share: 0.2 }, // share of the ambient budget
  },
  env: {
    enabled: true,
    share: 0.5, // share of the ambient budget served by IBL (taken from the hemisphere fill)
    softbox: 4.0, // softbox radiance relative to the gradient dome (specular highlight strength)
  },
  backdrop: { color: '#F6E9D7', fog: 0.012 },
  contact: {
    enabled: true,
    opacity: 0.5,
    blur: 2.0,
    size: [26, 18], // ground area covered (world units), centred on `center`
    center: [0, 0],
    height: 2.5, // only geometry within this height above the ground darkens it
    resolution: 256,
    updateInterval: 2,
  },
  ao: {
    enabled: false,
    intensity: 0.70,
    radius: 0.16,
    thickness: 0.60,
    distanceExponent: 1.4,
    distanceFallOff: 1.0,
    scale: 1.0,
    samples: 16,
    denoiseRadius: 6.0,
    lumaPhi: 10.0,
    depthPhi: 2.0,
    normalPhi: 3.0,
    resolutionScale: 1.0,
    inkStrength: 0.0,
    inkColor: '#181C22',
  },
};

/**
 * Time-of-day / mood presets selected per scene with `data-look="<name>"` (merged over the
 * style's resolved base look). Each is a complete light design inside the same energy
 * budget, tuned on warm pastel sets and checked with `lookcheck` readability floors.
 * Styles override or extend them (kernel `*_LOOK_PRESETS`, then per video `style.looks`).
 */
export const LOOK_PRESETS = {
  day: {},
  golden: {
    light: {
      illuminance: 2.0,
      keyRatio: 3.0,
      key: { color: '#FFD49C', pos: [-18, 11, 14] },
      sky: '#FFE9CF',
      ground: '#D99C84',
      bounce: { color: '#FFB894' },
    },
    backdrop: { color: '#F6DDC2', fog: 0.014 },
  },
  dusk: {
    light: {
      illuminance: 1.5,
      keyRatio: 2.2,
      key: { color: '#FFA877', pos: [-20, 6, 12] },
      sky: '#E7BCD2',
      ground: '#7A5F8A',
      bounce: { color: '#C9A6E0', share: 0.22 },
    },
    env: { softbox: 2.6 },
    backdrop: { color: '#D2AFC6', fog: 0.012 },
  },
  night: {
    light: {
      illuminance: 1.15,
      keyRatio: 2.0,
      key: { color: '#C9D8FF', pos: [12, 20, 9] },
      sky: '#7C8CC4',
      ground: '#4A4466',
      bounce: { color: '#8C7CC0', share: 0.18 },
    },
    env: { softbox: 1.6 },
    backdrop: { color: '#3E4770', fog: 0.02 },
    contact: { opacity: 0.38 },
  },
  indoor: {
    light: {
      illuminance: 1.6,
      keyRatio: 2.2,
      key: { color: '#FFC994', pos: [7, 15, 11] },
      sky: '#F4DBC0',
      ground: '#9A7766',
      bounce: { color: '#FFB98F' },
    },
    env: { softbox: 2.8 },
    backdrop: { color: '#E9CFB3', fog: 0.015 },
  },
};

const TONE_MAPPING = {
  aces: 'ACESFilmicToneMapping',
  cineon: 'CineonToneMapping',
  reinhard: 'ReinhardToneMapping',
  linear: 'LinearToneMapping',
  none: 'NoToneMapping',
};

function isPlainObject(v) {
  return v && typeof v === 'object' && !Array.isArray(v);
}

/** Deep-merge look layers (later wins); arrays are replaced, not merged. */
export function resolveLook(...layers) {
  const out = {};
  for (const layer of layers) {
    if (!isPlainObject(layer)) continue;
    for (const [k, v] of Object.entries(layer)) {
      out[k] = isPlainObject(v) && isPlainObject(out[k]) ? resolveLook(out[k], v) : isPlainObject(v) ? resolveLook(v) : v;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------------------------- ref.json palette -> look

function hexToRgb(h) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(h).trim());
  if (!m) throw new Error(`look: bad colour "${h}" (need #RRGGBB)`);
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function rgbToHex(rgb) {
  return '#' + rgb.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
}
function mixHex(a, b, t) {
  const A = hexToRgb(a), B = hexToRgb(b);
  return rgbToHex(A.map((v, i) => v + (B[i] - v) * t));
}

/** Black-body colour (Tanner Helland fit), Kelvin -> '#RRGGBB'. 6500 K ~ white. */
export function kelvinToHex(k) {
  const t = Math.max(1000, Math.min(12000, k)) / 100;
  const r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
  const g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
  const b = t >= 66 ? 255 : t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  return rgbToHex([r, g, b]);
}

/**
 * Normalised ref.json palette. Canonical keys: background, shell, mechanism, accent, glow (+ optional warm_metal,
 * light.kelvin). The older nested form `palette.sampled_hex` is accepted through a fixed alias table so existing
 * ref.json files keep working: studio_backdrop->background, shell_glaze_mid->shell, mechanism_dark_steel->mechanism,
 * focal_accent_orange->accent, eye_emissive_orange->glow, mechanism_muted_bronze->warm_metal.
 * Returns null when nothing usable is declared (-> nothing is derived).
 */
export function normalizeRefPalette(ref) {
  const p = ref && ref.palette;
  if (!p || typeof p !== 'object') return null;
  const hx = p.sampled_hex || {};
  const pick = (...c) => c.find((v) => typeof v === 'string' && /^#?[0-9a-f]{6}$/i.test(v));
  const out = {
    background: pick(p.background, hx.studio_backdrop),
    shell: pick(p.shell, hx.shell_glaze_mid),
    mechanism: pick(p.mechanism, hx.mechanism_dark_steel),
    accent: pick(p.accent, hx.focal_accent_orange),
    glow: pick(p.glow, hx.eye_emissive_orange),
    warm_metal: pick(p.warm_metal, hx.mechanism_muted_bronze),
    kelvin: typeof p.light?.kelvin === 'number' ? p.light.kelvin : undefined,
  };
  for (const k of ['background', 'shell', 'mechanism', 'accent', 'glow', 'warm_metal']) if (out[k] && out[k][0] !== '#') out[k] = '#' + out[k];
  return Object.values(out).some((v) => v !== undefined) ? out : null;
}

/**
 * Look layer derived from a declared palette (empty object if none). Only what the palette says is touched:
 *   background -> backdrop.color (fog takes the same colour), light.sky = background lifted 25% toward white,
 *   light.ground = background darkened 22% (so the bounce from floor/air carries the reference's temperature, not the
 *   style's cool grey);  light.kelvin -> key colour (a 6500 K key is neutral), bounce colour = background.
 * The style keeps structure (illuminance, keyRatio, shadow, AO, env); products still override any leaf via style.look.
 */
export function lookFromRefPalette(ref) {
  const p = normalizeRefPalette(ref);
  if (!p) return {};
  const out = {};
  if (p.background) {
    out.backdrop = { color: p.background };
    out.light = {
      sky: mixHex(p.background, '#ffffff', 0.25),
      ground: mixHex(p.background, '#000000', 0.22),
      bounce: { color: p.background },
    };
  }
  if (p.kelvin) {
    out.light = out.light || {};
    out.light.key = { color: kelvinToHex(p.kelvin) };
  }
  return out;
}

// ---------------------------------------------------------------------------------------------- role studio

/**
 * Give a look the studio that `glaze` / `metal` roles need (see header). `roles` = { glaze: bool, metal: bool }.
 * Pure: returns { look, applied } where `applied` lists what was added (empty when nothing was needed / opted out).
 */
export function augmentLookForRoles(look, roles) {
  const applied = [];
  if (!roles || !(roles.glaze || roles.metal) || look.studio?.auto === false) return { look, applied };
  const opt = look.studio || {};
  const L = { ...look, light: { ...look.light }, env: { ...look.env } };
  if (opt.softbox !== false && !L.env.softboxRig) {
    L.env.softboxRig = true;
    L.env.enabled = true;
    applied.push('softbox environment');
  }
  if (opt.keyRatio !== false && L.light.keyRatio < 3) {
    L.light.keyRatio = 3;
    applied.push('keyRatio>=3');
  }
  if (opt.rim !== false && !L.light.rim) {
    const k = L.light.key.pos;
    L.light.rim = { color: L.light.key.color, pos: [-k[0] * 0.9, Math.max(6, k[1] * 0.55), -Math.max(8, Math.abs(k[2]) * 1.4)], ratio: 0.32 };
    applied.push('rim light');
  }
  return { look: L, applied };
}

/** Key must carry >= 3x the summed fills (hemisphere + bounce + IBL); a rim light is an accent and not counted. */
export function lightRatioReport(look) {
  const b = computeLightBudget(look);
  return { key: b.key, fills: b.ambient, ratio: b.key / Math.max(b.ambient, 1e-9), rim: look.light.rim ? b.key * (look.light.rim.ratio ?? 0.3) : 0 };
}

/** Split the fixed illuminance budget into per-source intensities. */
export function computeLightBudget(look) {
  const { illuminance, keyRatio, bounce } = look.light;
  const ambient = illuminance / (keyRatio + 1);
  const key = illuminance - ambient;
  const bounceI = ambient * (bounce?.share ?? 0);
  const envI = look.env.enabled ? ambient * look.env.share : 0;
  const hemi = Math.max(0, ambient - bounceI - envI);
  return { key, ambient, hemi, bounce: bounceI, env: envI };
}

const BLUR_FS = `
uniform sampler2D tDiffuse;
uniform vec2 dir;
varying vec2 vUv;
void main() {
  vec4 sum = vec4(0.0);
  sum += texture2D(tDiffuse, vUv - 4.0 * dir) * 0.051;
  sum += texture2D(tDiffuse, vUv - 3.0 * dir) * 0.0918;
  sum += texture2D(tDiffuse, vUv - 2.0 * dir) * 0.12245;
  sum += texture2D(tDiffuse, vUv - 1.0 * dir) * 0.1531;
  sum += texture2D(tDiffuse, vUv) * 0.1633;
  sum += texture2D(tDiffuse, vUv + 1.0 * dir) * 0.1531;
  sum += texture2D(tDiffuse, vUv + 2.0 * dir) * 0.12245;
  sum += texture2D(tDiffuse, vUv + 3.0 * dir) * 0.0918;
  sum += texture2D(tDiffuse, vUv + 4.0 * dir) * 0.051;
  gl_FragColor = sum;
}`;
const BLUR_VS = `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;

function luminance(c) {
  return 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
}

/**
 * Studio environment for IBL: a sky→ground gradient dome plus a softbox aligned with the key
 * light. The dome alone lights a surface exactly like a HemisphereLight of intensity 1 (sky
 * above, ground below), so the returned `upGain` only accounts for the softbox's extra
 * irradiance on an up-facing surface. `envMapIntensity = budget.env / upGain` then keeps IBL in
 * the same unit as the hemisphere fill it replaces.
 */
function buildEnvironment(THREE, renderer, look, sharedPmrem = null) {
  const envScene = new THREE.Scene();
  const sky = new THREE.Color(look.light.sky);
  const ground = new THREE.Color(look.light.ground);

  const dome = new THREE.SphereGeometry(50, 32, 16);
  const colors = [];
  const pos = dome.attributes.position;
  const c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const t = THREE.MathUtils.smoothstep(pos.getY(i) / 50, -0.35, 0.35);
    c.copy(ground).lerp(sky, t);
    colors.push(c.r, c.g, c.b);
  }
  dome.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  envScene.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));

  // Softbox facing the origin from the key direction: mainly a broad specular highlight.
  const keyDir = new THREE.Vector3(...look.light.key.pos).normalize();
  const boxW = 18;
  const boxH = 12;
  const dist = 30;
  const softboxColor = new THREE.Color(look.light.key.color).multiplyScalar(look.env.softbox);
  const softbox = new THREE.Mesh(new THREE.PlaneGeometry(boxW, boxH), new THREE.MeshBasicMaterial({ color: softboxColor }));
  softbox.position.copy(keyDir).multiplyScalar(dist);
  softbox.lookAt(0, 0, 0);
  envScene.add(softbox);

  // Optional high-contrast industrial studio reflection rig (`look.env.studioStrips`):
  // alternates sharp specular light strips with dark negative-fill ribs so machined steel,
  // chrome shafts, and anodized bevels show crisp metallic reflection bands instead of flat grey.
  if (look.env.studioStrips) {
    const stripHot = new THREE.Color(look.light.key.color).multiplyScalar(look.env.softbox * 1.45);
    const stripWarm = new THREE.Color('#F5F8FC').multiplyScalar(look.env.softbox * 1.15);
    const darkFill = new THREE.Color('#14181F');
    const strips = [
      { pos: [24, 15, 16], w: 4.2, h: 26, col: stripHot },
      { pos: [-24, 10, -14], w: 3.6, h: 24, col: stripWarm },
      { pos: [4, 28, -12], w: 22, h: 3.4, col: stripHot },
      { pos: [-18, 18, 20], w: 2.8, h: 22, col: stripHot },
      // Negative-fill absorber cards to carve crisp dark bands across cylindrical/spherical metal
      { pos: [22, 4, -6], w: 9.5, h: 24, col: darkFill },
      { pos: [-22, 3, 4], w: 9.0, h: 22, col: darkFill },
      { pos: [0, 14, -27], w: 14, h: 16, col: darkFill },
    ];
    for (const s of strips) {
      const m = new THREE.Mesh(
        new THREE.PlaneGeometry(s.w, s.h),
        new THREE.MeshBasicMaterial({ color: s.col, side: THREE.DoubleSide }),
      );
      m.position.set(...s.pos);
      m.lookAt(0, 0, 0);
      envScene.add(m);
    }
  }

  let solidAngle = (boxW * boxH) / (dist * dist);
  let upGain = 1 + (luminance(softboxColor) * solidAngle * Math.max(keyDir.y, 0)) / (Math.PI * luminance(sky));

  if (look.env.softboxRig) {
    // Softbox rig (role studio, after teardown's studioEnvironment, written for this engine): bright panels against a
    // DARKER surround. A metal shows only what it reflects: a uniformly pale env makes grey plastic, a uniformly dark
    // one makes black holes; panels give the highlight bands, the dark between them the contrast. The generic softbox
    // and strips above are dropped, the dome is darkened to `env.surround` (default: 30% of sky) with a dim floor, and
    // `upGain` is recomputed so the diffuse IBL level stays what the energy budget says (only the quality changes).
    for (const o of envScene.children.slice()) envScene.remove(o);
    const surround = look.env.surround ? new THREE.Color(look.env.surround) : sky.clone().multiplyScalar(0.3);
    const floor = ground.clone().multiplyScalar(0.55);
    const dome2 = new THREE.SphereGeometry(50, 32, 16);
    const col2 = [];
    for (let i = 0; i < pos.count; i++) {
      const t = THREE.MathUtils.smoothstep(pos.getY(i) / 50, -0.35, 0.35);
      c.copy(floor).lerp(surround, t);
      col2.push(c.r, c.g, c.b);
    }
    dome2.setAttribute('color', new THREE.Float32BufferAttribute(col2, 3));
    envScene.add(new THREE.Mesh(dome2, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const kc = new THREE.Color(look.light.key.color);
    const rimC = new THREE.Color(look.light.rim?.color || look.light.key.color);
    const white = new THREE.Color('#ffffff');
    // [w, h, position, colour, radiance] : top, key side, rim side, thin front strip for edge glints, dim front card
    // (faces turned to the camera reflect the card instead of the dark surround, so they read as polished, not as holes)
    const kd = new THREE.Vector3(...look.light.key.pos).normalize().multiplyScalar(26);
    const rd = look.light.rim ? new THREE.Vector3(...look.light.rim.pos).normalize().multiplyScalar(26) : new THREE.Vector3(-kd.x, 12, -kd.z);
    const gain = look.env.softbox / 3.2;
    const boxes = [
      [28, 22, [2, 24, 6], white.clone().lerp(kc, 0.25), 3.4 * gain],
      [18, 22, kd.toArray(), kc.clone(), 2.8 * gain],
      [14, 24, rd.toArray(), rimC.clone(), 2.4 * gain],
      [26, 5, [0, 8, 24], white.clone(), 2.2 * gain],
      [26, 14, [-4, -1, 26], white.clone().lerp(kc, 0.3), 1.15 * gain],
    ];
    let boxIrr = 0;
    for (const [w, h, p3, col, k] of boxes) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: col.clone().multiplyScalar(k), side: THREE.DoubleSide }));
      m.position.set(...p3);
      m.lookAt(0, 0, 0);
      envScene.add(m);
      const d = Math.hypot(...p3);
      boxIrr += luminance(col) * k * ((w * h) / (d * d)) * Math.max(p3[1] / d, 0);
    }
    upGain = Math.max(0.25, (Math.PI * luminance(surround) + boxIrr) / (Math.PI * luminance(sky)));
  }

  const pmrem = sharedPmrem || new THREE.PMREMGenerator(renderer);
  const texture = pmrem.fromScene(envScene, 0.04).texture;
  if (!sharedPmrem) pmrem.dispose();
  envScene.traverse((o) => {
    o.geometry?.dispose();
    o.material?.dispose();
  });
  return { texture, upGain };
}

/**
 * Soft ambient-occlusion-like contact shadow: render geometry near the ground from below into a
 * depth-alpha target, blur it, and lay it on the ground plane (after three.js webgl_shadow_contact).
 */
function buildContactShadow(THREE, look) {
  const cfg = look.contact;
  const [w, h] = cfg.size;
  const res = cfg.resolution;
  const rt = new THREE.WebGLRenderTarget(res, res);
  const rtBlur = new THREE.WebGLRenderTarget(res, res);
  rt.texture.generateMipmaps = false;
  rtBlur.texture.generateMipmaps = false;

  const group = new THREE.Group();
  group.position.set(cfg.center[0], 0.004, cfg.center[1]);

  const planeGeometry = new THREE.PlaneGeometry(w, h).rotateX(Math.PI / 2);
  const plane = new THREE.Mesh(
    planeGeometry,
    new THREE.MeshBasicMaterial({ map: rt.texture, opacity: cfg.opacity, transparent: true, depthWrite: false, fog: false })
  );
  plane.renderOrder = 1;
  plane.scale.y = -1; // texture is captured from below
  group.add(plane);

  const blurPlane = new THREE.Mesh(planeGeometry); // must face the shadow camera like `plane`
  blurPlane.visible = false;
  group.add(blurPlane);

  const shadowCamera = new THREE.OrthographicCamera(-w / 2, w / 2, h / 2, -h / 2, 0, cfg.height);
  shadowCamera.rotation.x = Math.PI / 2;
  group.add(shadowCamera);

  const depthMaterial = new THREE.MeshDepthMaterial();
  depthMaterial.userData.darkness = { value: 1.0 };
  depthMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.darkness = depthMaterial.userData.darkness;
    shader.fragmentShader = `uniform float darkness;\n${shader.fragmentShader.replace(
      'gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );',
      'gl_FragColor = vec4( vec3( 0.0 ), ( 1.0 - fragCoordZ ) * darkness );'
    )}`;
  };
  depthMaterial.depthTest = false;
  depthMaterial.depthWrite = false;

  const blurMaterial = new THREE.ShaderMaterial({
    uniforms: { tDiffuse: { value: null }, dir: { value: new THREE.Vector2() } },
    vertexShader: BLUR_VS,
    fragmentShader: BLUR_FS,
    depthTest: false,
  });

  function blur(renderer, amount) {
    blurPlane.visible = true;
    blurPlane.material = blurMaterial;
    blurMaterial.uniforms.tDiffuse.value = rt.texture;
    blurMaterial.uniforms.dir.value.set(amount / res, 0);
    renderer.setRenderTarget(rtBlur);
    renderer.render(blurPlane, shadowCamera);
    blurMaterial.uniforms.tDiffuse.value = rtBlur.texture;
    blurMaterial.uniforms.dir.value.set(0, amount / res);
    renderer.setRenderTarget(rt);
    renderer.render(blurPlane, shadowCamera);
    blurPlane.visible = false;
  }

  let frameCount = 0;
  const prevClear = new THREE.Color();

  function update(renderer, scene, force = false) {
    const interval = Math.max(1, cfg.updateInterval || 2);
    const isCapture = typeof window !== 'undefined' && Boolean(window.__CAPTURE_MODE);
    if (!force && !isCapture && frameCount > 0 && frameCount % interval !== 0) {
      frameCount++;
      return;
    }
    frameCount++;

    const bg = scene.background;
    const fog = scene.fog;
    const prevClearAlpha = renderer.getClearAlpha();
    renderer.getClearColor(prevClear);
    scene.background = null;
    scene.fog = null;

    const hiddenForShadow = [];
    const maxShadowY = (cfg.height || 2.5) + 1.8;
    scene.traverse((o) => {
      if (!o.visible || o === plane || o === blurPlane || o === group) return;
      if (
        o.isLineSegments ||
        o.isLine ||
        o.userData?.skipContactShadow ||
        (o.isMesh && o.parent === scene && o.position.y > maxShadowY)
      ) {
        o.visible = false;
        hiddenForShadow.push(o);
      }
    });

    scene.overrideMaterial = depthMaterial;
    plane.visible = false;
    renderer.setClearColor(0x000000, 0);
    renderer.setRenderTarget(rt);
    renderer.clear();
    renderer.render(scene, shadowCamera);
    scene.overrideMaterial = null;

    for (let i = 0; i < hiddenForShadow.length; i++) {
      hiddenForShadow[i].visible = true;
    }

    blur(renderer, cfg.blur);
    renderer.setRenderTarget(null);
    renderer.setClearColor(prevClear, prevClearAlpha);
    scene.background = bg;
    scene.fog = fog;
    plane.visible = true;
  }

  return {
    group,
    update,
    setOpacity: (v) => {
      plane.material.opacity = v;
    },
  };
}

/** Interpolate two resolved looks: numbers, colours and number arrays blend; anything else switches at k = 0.5. */
export function blendLooks(THREE, a, b, k) {
  if (k <= 0) return a;
  if (k >= 1) return b;
  const ca = new THREE.Color();
  const cb = new THREE.Color();
  const mix = (x, y) => {
    if (typeof x === 'number' && typeof y === 'number') return x + (y - x) * k;
    if (typeof x === 'string' && typeof y === 'string' && x[0] === '#' && y[0] === '#') {
      return `#${ca.set(x).lerp(cb.set(y), k).getHexString()}`;
    }
    if (Array.isArray(x) && Array.isArray(y) && x.length === y.length && x.every((v) => typeof v === 'number')) {
      return x.map((v, i) => v + (y[i] - v) * k);
    }
    if (isPlainObject(x) && isPlainObject(y)) {
      const out = {};
      for (const key of new Set([...Object.keys(x), ...Object.keys(y)])) out[key] = key in x && key in y ? mix(x[key], y[key]) : key in y ? y[key] : x[key];
      return out;
    }
    return k < 0.5 ? x : y;
  };
  return mix(a, b);
}

/**
 * Scene-driven look changes. Each `<section>` in scenes.html may declare:
 *   data-look="dusk"            preset name (from `presets`) or inline JSON, merged over `base`;
 *                               scenes without it keep the previous scene's look
 *   data-look-blend="2.5"       seconds to blend from the previous scene's look (0 = switch at the cut)
 *   data-look-at="0.5"          scene-local start of that blend (default 0)
 * Every resolved look goes through the same energy budget, so a "night" scene is darker only
 * because its preset says so (lower `illuminance`, cooler key), never because effects stack up.
 */
export function createLookTimeline(THREE, { base, presets = {}, scenes = [] }) {
  const targets = [];
  const blends = [];
  scenes.forEach((scene, i) => {
    const ds = scene.el?.dataset || scene;
    const spec = ds.look;
    let target = i ? targets[i - 1] : base;
    if (spec) {
      let layer;
      if (spec.trim().startsWith('{')) layer = JSON.parse(spec);
      else if (presets[spec]) layer = presets[spec];
      else throw new Error(`look: unknown preset "${spec}" in scene ${scene.id ?? i} (known: ${Object.keys(presets).join(', ')})`);
      target = resolveLook(base, layer);
    }
    targets.push(target);
    blends.push({ dur: parseFloat(ds.lookBlend) || 0, at: parseFloat(ds.lookAt) || 0 });
  });
  const animated = scenes.some((s) => (s.el?.dataset || s).look);

  /** Resolved look at scene `index`, scene-local time `localT`; `envLook` switches between cached preset endpoints (`from` / `to`) so transitions never trigger synchronous PMREM baking stalls. */
  function at(index, localT) {
    if (!targets.length) return { look: base, envLook: base };
    const i = Math.max(0, Math.min(targets.length - 1, index));
    const to = targets[i];
    const from = i ? targets[i - 1] : to;
    const { dur, at: t0 } = blends[i];
    let k = localT >= t0 ? 1 : 0;
    if (dur > 0) {
      const x = Math.max(0, Math.min(1, (localT - t0) / dur));
      k = x * x * x * (x * (x * 6 - 15) + 10);
    }
    if (from === to) return { look: to, envLook: to };
    return { look: blendLooks(THREE, from, to, k), envLook: k < 0.5 ? from : to };
  }

  return { at, animated, targets };
}

/**
 * Apply a resolved look to a renderer + scene. Must run before world materials are created so
 * colour management converts palette hexes correctly. `apply(look)` re-applies the light,
 * backdrop, exposure, IBL and contact-shadow strength later (per scene / per frame); colour
 * pipeline, tone-mapping operator and shadow-map quality stay as created.
 * @returns {{ look, budget, lights, apply(look, opts), render(camera), syncMaterials() }}
 */
const SHADOW_MAP_TYPE = {
  'pcf-soft': 'PCFSoftShadowMap',
  vsm: 'VSMShadowMap',
  pcf: 'PCFShadowMap',
  basic: 'BasicShadowMap',
};

export function createLookRig(THREE, { renderer, scene, look }) {
  const srgb = look.color.output === 'srgb';
  THREE.ColorManagement.legacyMode = !srgb;
  renderer.outputEncoding = srgb ? THREE.sRGBEncoding : THREE.LinearEncoding;
  renderer.toneMapping = THREE[TONE_MAPPING[look.color.toneMapping] || TONE_MAPPING.aces];
  const sh = look.light.key.shadow;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE[SHADOW_MAP_TYPE[sh.type] || 'PCFSoftShadowMap'];
  renderer.localClippingEnabled = true;

  const bgColor = new THREE.Color();
  scene.background = bgColor;
  const fog = new THREE.FogExp2(0xffffff, 0);
  scene.fog = fog;
  const gradCache = new Map();

  function gradientTextureFor(stops) {
    const k = JSON.stringify(stops);
    if (gradCache.has(k)) return gradCache.get(k);
    if (typeof document === 'undefined') return null;
    const c = document.createElement('canvas');
    c.width = 4;
    c.height = 512;
    const g = c.getContext('2d');
    const gr = g.createLinearGradient(0, 0, 0, 512);
    const n = stops.length;
    for (let i = 0; i < n; i++) {
      gr.addColorStop(i / Math.max(1, n - 1), stops[i]);
    }
    g.fillStyle = gr;
    g.fillRect(0, 0, 4, 512);
    const tex = new THREE.CanvasTexture(c);
    tex.encoding = srgb ? THREE.sRGBEncoding : THREE.LinearEncoding;
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.generateMipmaps = false;
    gradCache.set(k, tex);
    return tex;
  }

  const rig = new THREE.Group();
  rig.name = 'LookRig';
  const hemi = new THREE.HemisphereLight();
  const key = new THREE.DirectionalLight();
  key.castShadow = true;
  key.shadow.mapSize.set(sh.mapSize, sh.mapSize);
  Object.assign(key.shadow.camera, {
    near: sh.near,
    far: sh.far,
    left: -sh.extent[0],
    right: sh.extent[0],
    top: sh.extent[1],
    bottom: -sh.extent[1],
  });
  key.shadow.bias = sh.bias;
  key.shadow.normalBias = sh.normalBias ?? 0;
  if (sh.radius !== undefined) key.shadow.radius = sh.radius;
  if (sh.blurSamples !== undefined) key.shadow.blurSamples = sh.blurSamples;
  const bounce = new THREE.DirectionalLight();
  const rim = new THREE.DirectionalLight(); // role studio / look.light.rim; hidden (not counted by three) unless declared
  rim.castShadow = false;
  rim.visible = false;
  rig.add(hemi, key, bounce, rim);
  scene.add(rig);

  const contact = look.contact.enabled ? buildContactShadow(THREE, look) : null;
  if (contact) scene.add(contact.group);

  let gtao = look.ao?.enabled ? createGTAORig(THREE, { renderer, scene, options: look.ao }) : null;

  // IBL textures are cached by the inputs that shape them, reusing one persistent PMREMGenerator.
  const envCache = new Map();
  let sharedPmrem = null;
  function envFor(l) {
    const k = JSON.stringify([l.light.sky, l.light.ground, l.light.key.color, l.light.key.pos, l.env.softbox, Boolean(l.env.studioStrips), Boolean(l.env.softboxRig), l.env.surround || '', l.light.rim?.color || '', l.light.rim?.pos || '']);
    if (!envCache.has(k)) {
      if (envCache.size >= 24) {
        const [oldKey, old] = envCache.entries().next().value;
        old.texture.dispose();
        envCache.delete(oldKey);
      }
      if (!sharedPmrem) sharedPmrem = new THREE.PMREMGenerator(renderer);
      envCache.set(k, buildEnvironment(THREE, renderer, l, sharedPmrem));
    }
    return envCache.get(k);
  }

  function prewarm(looks = []) {
    if (!look.env.enabled) return;
    for (const l of looks) {
      if (l && l.env?.enabled !== false) envFor(l);
    }
  }

  const tracked = [];
  const seen = new WeakSet();
  let envIntensity = 0;
  let current = null;
  let fogBase = 0;
  let fogScale = 1; // director `cinema.fog`: density multiplier (1 = unchanged)
  let budget = null;
  let lastChildCount = -1;
  let syncFrames = 0;
  let materialsDirty = true;

  let roleDemand = null; // { glaze, metal } set by the style kernel when a world uses those material roles
  let studioApplied = [];
  let lastIn = null;
  // Softbox rig only: the energy budget keeps the DIFFUSE IBL level, but a metal has no diffuse term, its whole look is the
  // reflection, so it would sit at ~17% radiance. Metals / glaze take a role gain on the env intensity (env.roleGain, default
  // metal x4, glaze x2); matte materials are untouched. Without the rig the gain is 1 (nothing changes).
  let roleGain = { metal: 1, glaze: 1 };
  const envScaleOf = (m) => (m.userData?.envMapScale ?? 1.0) * (roleGain[m.userData?.role] ?? 1);
  function apply(next, { envLook = next } = {}) {
    lastIn = { next, envLook };
    if (roleDemand) {
      const a = augmentLookForRoles(next, roleDemand);
      const e = envLook === next ? a.look : augmentLookForRoles(envLook, roleDemand).look;
      studioApplied = a.applied;
      next = a.look;
      envLook = e;
    }
    current = next;
    roleGain = next.env.softboxRig ? { metal: 4, glaze: 2, ...(next.env.roleGain || {}) } : { metal: 1, glaze: 1 };
    budget = computeLightBudget(next);
    const L = next.light;
    renderer.toneMappingExposure = next.color.exposure;
    if (Array.isArray(next.backdrop?.gradient) && next.backdrop.gradient.length >= 2) {
      const gTex = gradientTextureFor(next.backdrop.gradient);
      scene.background = gTex || bgColor.set(next.backdrop.color);
      fog.color.set(next.backdrop.gradient[Math.floor(next.backdrop.gradient.length / 2)] || next.backdrop.color);
    } else {
      bgColor.set(next.backdrop.color);
      scene.background = bgColor;
      fog.color.set(next.backdrop.color);
    }
    fogBase = next.backdrop.fog;
    fog.density = fogBase * fogScale;

    hemi.color.set(L.sky);
    hemi.groundColor.set(L.ground);
    hemi.intensity = budget.hemi;
    key.color.set(L.key.color);
    key.intensity = budget.key;
    key.position.set(...L.key.pos);
    bounce.color.set(L.bounce?.color ?? '#ffffff');
    bounce.intensity = budget.bounce;
    if (L.bounce?.pos) bounce.position.set(...L.bounce.pos);
    bounce.visible = budget.bounce > 0;
    if (L.rim) {
      rim.visible = true;
      rim.color.set(L.rim.color || L.key.color);
      rim.intensity = budget.key * (L.rim.ratio ?? 0.3);
      rim.position.set(...L.rim.pos);
    } else {
      rim.visible = false;
    }

    if (look.env.enabled && budget.env > 0) {
      const env = envFor(envLook);
      scene.environment = env.texture;
      envIntensity = budget.env / env.upGain;
    } else {
      scene.environment = null;
      envIntensity = 0;
    }
    for (const m of tracked) m.envMapIntensity = envIntensity * envScaleOf(m);
    if (contact) contact.setOpacity(next.contact.opacity);
    if (next.ao?.enabled) {
      if (!gtao) gtao = createGTAORig(THREE, { renderer, scene, options: next.ao });
      else gtao.setOptions(next.ao);
    }
  }

  /** Give every standard material the budgeted IBL intensity and sRGB colour maps. */
  function syncMaterials(force = false) {
    if (!force && !materialsDirty && scene.children.length === lastChildCount && syncFrames >= 2) {
      return;
    }
    lastChildCount = scene.children.length;
    materialsDirty = false;
    syncFrames++;
    scene.traverse((o) => {
      const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const m of mats) {
        if (seen.has(m)) continue;
        seen.add(m);
        if (m.isMeshStandardMaterial && m.userData.lookEnv !== false) {
          m.envMapIntensity = envIntensity * envScaleOf(m);
          tracked.push(m);
        }
        for (const slot of ['map', 'emissiveMap']) {
          const tex = m[slot];
          if (srgb && tex && tex.encoding !== THREE.sRGBEncoding) {
            tex.encoding = THREE.sRGBEncoding;
            tex.needsUpdate = true;
            m.needsUpdate = true;
          }
        }
      }
    });
  }

  function render(camera) {
    syncMaterials(false);
    if (contact) contact.update(renderer, scene);
    const useAo = Boolean(gtao && current?.ao?.enabled && (current.ao.intensity ?? 0) > 0.01);
    if (!useAo) {
      renderer.render(scene, camera);
      return;
    }

    gtao.update(camera);

    const hudMeshes = [];
    scene.traverse((o) => {
      if (o.visible && o.userData?.isHudOverlay) {
        hudMeshes.push(o);
        o.visible = false;
      }
    });

    renderer.render(scene, camera);
    gtao.composite();

    if (hudMeshes.length > 0) {
      const hudAncestors = new Set();
      for (const h of hudMeshes) {
        h.visible = true;
        let p = h;
        while (p && p !== scene) {
          hudAncestors.add(p);
          p = p.parent;
        }
      }
      const hiddenTop = [];
      for (const child of scene.children) {
        if (child.visible && !hudAncestors.has(child)) {
          child.visible = false;
          hiddenTop.push(child);
        }
      }
      const prevAutoClear = renderer.autoClear;
      const prevBg = scene.background;
      const prevFog = scene.fog;
      renderer.autoClear = false;
      scene.background = null;
      scene.fog = null;
      renderer.render(scene, camera);
      scene.background = prevBg;
      scene.fog = prevFog;
      renderer.autoClear = prevAutoClear;
      for (const child of hiddenTop) child.visible = true;
    }
  }

  apply(look);

  return {
    look,
    get current() {
      return current;
    },
    get budget() {
      return budget;
    },
    get envIntensity() {
      return envIntensity;
    },
    lights: { hemi, key, bounce },
    gtao,
    apply,
    /** Style kernel reports which material roles the world uses; the role studio is (re)applied. */
    setRoleDemand(d) {
      const same = roleDemand && roleDemand.glaze === d.glaze && roleDemand.metal === d.metal;
      if (same) return;
      roleDemand = { glaze: Boolean(d.glaze), metal: Boolean(d.metal) };
      if (lastIn) apply(lastIn.next, { envLook: lastIn.envLook });
    },
    get studioApplied() {
      return studioApplied;
    },
    setFogScale(s) {
      fogScale = s;
      if (fogBase) fog.density = fogBase * s;
    },
    prewarm,
    render,
    syncMaterials,
  };
}
