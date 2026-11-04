// Studio stage for the Mechanical Nautilus (Archive / 007):
// Warm archive studio backdrop (#EFECE6), bathymetric seabed grid shader that drifts with distance swum,
// VSM soft shadows, GTAOPass + InkPass (hidden on the floor via CallPass), section clipping plane synced
// to gtao.normalMaterial, and installSilhouette(scene) for the form gate (`capture.mjs --mask`).
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {GTAOPass} from 'three/addons/postprocessing/GTAOPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {CallPass, InkPass, installSilhouette, studioEnvironment} from '../kit/look.js';
import {buildNautilus} from './nautilus.js';
import {P} from './palette.js';

const V3 = THREE.Vector3;
export const COL = P.stage; // bg, ground, mark, shadow (docs: palette.js)

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
  // Bathymetric archive grid: x along swimming axis (drifts by +uSwim as nautilus swims left), z across
  float x = vW.x - uSwim;
  float z = vW.z;
  float gx = step(abs(mod(x + 1.5, 3.0) - 1.5), 0.025);
  float gz = step(abs(mod(z + 1.5, 3.0) - 1.5), 0.025);
  float tick = step(abs(mod(x + 0.3, 0.6) - 0.3), 0.015) * step(abs(z), 0.25);
  float m = max(max(gx, gz) * 0.55, tick * 0.85);
  float n = fract(sin(dot(floor(vW.xz * 28.0), vec2(12.9898, 78.233))) * 43758.5453);
  vec3 col = mix(uG, uM, m) * (0.99 + 0.02 * n);
  float d = length(vW.xz - uC.xz);
  gl_FragColor = vec4(mix(col, uBg, smoothstep(10.0, 28.0, d)), 1.0);
}`;

export async function createNautilusStage({canvas}) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    preserveDrawingBuffer: true,
    powerPreference: 'high-performance',
  });
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.VSMShadowMap;
  renderer.localClippingEnabled = true;

  const gl = renderer.getContext();
  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  const isSwift = Boolean(dbg && /SwiftShader/i.test(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)));

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(COL.bg);
  scene.fog = new THREE.Fog(COL.bg, 28, 68);

  const camera = new THREE.PerspectiveCamera(28, 16 / 9, 0.2, 120);
  const clipPlane = new THREE.Plane(new V3(0, 0, -1), 0.08);

  // Studio for metals (kit/look.js): bright softboxes against a dark surround. A pale #DCD9D2 surround leaves
  // every metal reflecting grey and read as plastic; a near-black one reads as metal. Dark parts stay readable
  // because they are now metal too: the boxes draw their bevels.
  scene.environment = studioEnvironment(renderer, {surround: COL.surround, floor: COL.envFloor});
  scene.environmentIntensity = COL.envIntensity;

  const SUN_DIR = new V3(-0.28, 0.84, 0.46).normalize();
  // One strong key and little fill (fill + rim + hemi outweighing the key makes every form read flat and soft)
  const sun = new THREE.DirectionalLight(COL.sun, COL.sunIntensity);
  sun.castShadow = true;
  const EXT = 14.5;
  Object.assign(sun.shadow.camera, {left: -EXT, right: EXT, top: EXT, bottom: -EXT, near: 2, far: 54});
  sun.shadow.mapSize.set(isSwift ? 1024 : 2048, isSwift ? 1024 : 2048);
  sun.shadow.radius = 7;
  sun.shadow.blurSamples = isSwift ? 4 : 16;
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.006;
  scene.add(sun, sun.target);

  const sideFill = new THREE.DirectionalLight(COL.fill, 0.3);
  sideFill.position.set(-14, 5, 22);
  scene.add(sideFill);

  const rim = new THREE.DirectionalLight(COL.rim, 0.9);
  rim.position.set(-14, 14, -12);
  scene.add(rim);

  scene.add(new THREE.HemisphereLight(COL.hemiSky, COL.hemiGround, 0.48));

  const floorY = -4.48;
  const groundMat = new THREE.ShaderMaterial({
    vertexShader: FLOOR_VERT,
    fragmentShader: FLOOR_FRAG,
    uniforms: {
      uG: {value: new THREE.Color(COL.ground)},
      uM: {value: new THREE.Color(COL.mark)},
      uBg: {value: new THREE.Color(COL.bg)},
      uSwim: {value: 0},
      uC: {value: new V3()},
    },
    toneMapped: false,
    side: THREE.DoubleSide,
  });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(240, 240), groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = floorY;
  ground.userData.noSilhouette = true;
  scene.add(ground);

  const shade = new THREE.Mesh(
    new THREE.PlaneGeometry(240, 240),
    new THREE.ShadowMaterial({
      color: COL.shadow,
      opacity: COL.shadowOpacity,
      polygonOffset: true,
      polygonOffsetFactor: -4,
      polygonOffsetUnits: -8,
    }),
  );
  shade.rotation.x = -Math.PI / 2;
  shade.position.y = floorY + 0.002;
  shade.receiveShadow = true;
  shade.userData.noSilhouette = true;
  scene.add(shade);

  const nautilus = await buildNautilus({clipPlane});
  scene.add(nautilus.root);

  // Post-processing: RenderPass -> CallPass(hide floor) -> GTAOPass -> InkPass -> CallPass(show floor) -> OutputPass
  const composer = new EffectComposer(
    renderer,
    new THREE.WebGLRenderTarget(4, 4, {type: THREE.HalfFloatType, samples: isSwift ? 0 : 4}),
  );
  composer.addPass(new RenderPass(scene, camera));
  const gtao = new GTAOPass(scene, camera, 4, 4);
  gtao.output = GTAOPass.OUTPUT.Default;
  gtao.blendIntensity = 0.7;
  gtao.updateGtaoMaterial({
    radius: 0.8,
    distanceExponent: 1.5,
    thickness: 1.25,
    scale: 0.85,
    samples: isSwift ? 6 : 16,
    distanceFallOff: 1.0,
    screenSpaceRadius: false,
  });
  gtao.updatePdMaterial({
    lumaPhi: 10,
    depthPhi: 2,
    normalPhi: 3,
    radius: isSwift ? 4 : 6,
    rings: isSwift ? 1 : 2,
    samples: isSwift ? 6 : 16,
  });
  const ink = new InkPass(gtao, camera, {strength: 0.26, normalWeight: 0.56, color: COL.ink});

  composer.addPass(
    new CallPass(() => {
      ground.visible = false;
      shade.visible = false;
    }),
  );
  composer.addPass(gtao);
  composer.addPass(ink);
  composer.addPass(
    new CallPass(() => {
      ground.visible = true;
      shade.visible = true;
    }),
  );
  composer.addPass(new OutputPass());

  // Silhouette mode for `capture.mjs --mask`
  installSilhouette(scene);
  const baseSil = window.__SILHOUETTE;
  window.__SILHOUETTE = (on) => {
    window.__SILHOUETTE_ACTIVE = !!on;
    baseSil?.(on);
  };

  const size = {w: 1600, h: 900};
  const resize = (w, h, pr) => {
    size.w = w;
    size.h = h;
    renderer.setPixelRatio(pr);
    renderer.setSize(w, h, false);
    composer.setPixelRatio(pr);
    composer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };

  const frame = (st, cam) => {
    nautilus.update({...st, camDist: cam.d}); // camDist: the detail level (kit/lod.js) follows the camera
    if (gtao.normalMaterial) {
      gtao.normalMaterial.clippingPlanes = st.section ? [clipPlane] : [];
    }
    groundMat.uniforms.uSwim.value = st.dist ?? 0;

    const tx = cam.tx ?? 0;
    const ty = cam.ty ?? 0;
    const tz = cam.tz ?? 0;
    camera.position.set(
      tx + cam.d * Math.cos(cam.el) * Math.sin(cam.az),
      ty + cam.d * Math.sin(cam.el),
      tz + cam.d * Math.cos(cam.el) * Math.cos(cam.az),
    );
    camera.lookAt(tx, ty, tz);
    // fog starts behind the subject, wherever the camera is: a fixed 28 m start greyed the whole machine once the
    // explode shot pulled back to 44 m (it read as ghosts)
    if (scene.fog) {
      // (null in silhouette mode)
      scene.fog.near = cam.d - 2;
      scene.fog.far = cam.d + 40;
    }
    camera.setViewOffset(size.w, size.h, -(cam.sx ?? 0), -(cam.sy ?? 0), size.w, size.h);
    camera.updateMatrixWorld();

    groundMat.uniforms.uC.value.set(tx, floorY, tz);
    sun.target.position.set(tx * 0.5, 0, tz * 0.5);
    sun.position.copy(sun.target.position).addScaledVector(SUN_DIR, 24);
    sun.target.updateMatrixWorld();

    if (window.__SILHOUETTE_ACTIVE) {
      renderer.render(scene, camera);
    } else {
      composer.render();
    }
  };

  const pv = new V3();
  const project = (x, y, z) => {
    pv.set(x, y, z).project(camera);
    if (pv.z > 1) return null;
    return [(pv.x * 0.5 + 0.5) * size.w, (-pv.y * 0.5 + 0.5) * size.h];
  };

  const setQuality = ({samples, ao, shadow}) => {
    if (samples !== undefined) {
      for (const t of [composer.renderTarget1, composer.renderTarget2]) {
        t.samples = samples;
        t.dispose();
      }
    }
    if (ao !== undefined) {
      gtao.enabled = ao;
      ink.enabled = ao;
    }
    if (shadow !== undefined) {
      sun.shadow.mapSize.set(shadow, shadow);
      sun.shadow.map?.dispose();
      sun.shadow.map = null;
    }
  };

  return {
    renderer,
    scene,
    camera,
    nautilus,
    composer,
    gtao,
    ink,
    sun,
    resize,
    frame,
    project,
    size,
    setQuality,
  };
}
