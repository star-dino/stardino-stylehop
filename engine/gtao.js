/**
 * Ground-Truth Ambient Occlusion + Bilateral Poisson Denoiser (`engine/gtao.js`).
 *
 * Adapted from Three.js `GTAOPass` / `GTAOShader` / `PoissonDenoiseShader` (`teardown` pipeline)
 * for zero-build Three.js r147+ compatibility:
 *   1. Renders a view-space normal + hardware depth G-Buffer (`normalRenderTarget` + `depthTexture`),
 *      automatically skipping floor shadow catchers (`skipContactShadow`), stencil section caps
 *      (`isSectionCap`), HUD overlays (`isHudOverlay`), and syncing active `clippingPlanes` so
 *      section-cut geometry never leaves a pale ghost.
 *   2. Evaluates horizon-based Ground-Truth Ambient Occlusion (`GTAO_FS`) with a 5×5 magic-square
 *      interleaved gradient noise pattern and NaN-safe clamped inverse trig/power operations.
 *   3. Filters the raw AO through a depth-, normal-, and luma-aware 16-tap Poisson disc bilateral
 *      denoiser (`PD_FS`).
 *   4. Composites the denoised occlusion directly over the rendered MSAA framebuffer via hardware
 *      multiplicative blending (`DstColorFactor`), preserving native MSAA, sRGB output encoding,
 *      and tone mapping without requiring an `EffectComposer` copy chain.
 */

function generateMagicSquare(size) {
  const noiseSize = Math.floor(size) % 2 === 0 ? Math.floor(size) + 1 : Math.floor(size);
  const noiseSquareSize = noiseSize * noiseSize;
  const magicSquare = Array(noiseSquareSize).fill(0);
  let i = Math.floor(noiseSize / 2);
  let j = noiseSize - 1;

  for (let num = 1; num <= noiseSquareSize; ) {
    if (i === -1 && j === noiseSize) {
      j = noiseSize - 2;
      i = 0;
    } else {
      if (j === noiseSize) j = 0;
      if (i < 0) i = noiseSize - 1;
    }
    if (magicSquare[i * noiseSize + j] !== 0) {
      j -= 2;
      i++;
      continue;
    } else {
      magicSquare[i * noiseSize + j] = num++;
    }
    j++;
    i--;
  }
  return magicSquare;
}

function createMagicSquareNoiseTexture(THREE, size = 5) {
  const noiseSize = Math.floor(size) % 2 === 0 ? Math.floor(size) + 1 : Math.floor(size);
  const magicSquare = generateMagicSquare(noiseSize);
  const nSq = magicSquare.length;
  const data = new Uint8Array(nSq * 4);
  for (let inx = 0; inx < nSq; ++inx) {
    const iAng = magicSquare[inx];
    const angle = (2 * Math.PI * iAng) / nSq;
    const rx = Math.cos(angle);
    const ry = Math.sin(angle);
    data[inx * 4] = Math.round((rx * 0.5 + 0.5) * 255);
    data[inx * 4 + 1] = Math.round((ry * 0.5 + 0.5) * 255);
    data[inx * 4 + 2] = 127;
    data[inx * 4 + 3] = 255;
  }
  const tex = new THREE.DataTexture(data, noiseSize, noiseSize, THREE.RGBAFormat, THREE.UnsignedByteType);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.minFilter = THREE.NearestFilter;
  tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
}

function createBlueNoiseTexture(THREE, size = 64) {
  const data = new Uint8Array(size * size * 4);
  let seed = 0x9E3779B9;
  const nextRand = () => {
    seed |= 0;
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  for (let i = 0; i < data.length; i++) {
    data[i] = Math.floor(nextRand() * 256);
  }
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat, THREE.UnsignedByteType);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.minFilter = THREE.NearestFilter;
  tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
}

function buildPoissonSampleInitializer(samples = 16, rings = 2, radiusExponent = 2) {
  const parts = [];
  for (let i = 0; i < samples; i++) {
    const angle = (2 * Math.PI * rings * i) / samples;
    const r = Math.pow(i / Math.max(1, samples - 1), radiusExponent);
    const x = (Math.cos(angle) * r).toFixed(6);
    const y = (Math.sin(angle) * r).toFixed(6);
    const z = r.toFixed(6);
    parts.push(`vec3(${x}, ${y}, ${z})`);
  }
  return parts;
}

const PASS_VS = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

const GTAO_FS = /* glsl */ `
varying vec2 vUv;
uniform highp sampler2D tNormal;
uniform highp sampler2D tDepth;
uniform sampler2D tNoise;
uniform vec2 resolution;
uniform float noiseSize;
uniform float cameraNear;
uniform float cameraFar;
uniform mat4 cameraProjectionMatrix;
uniform mat4 cameraProjectionMatrixInverse;
uniform float radius;
uniform float distanceExponent;
uniform float thickness;
uniform float distanceFallOff;
uniform float scale;

#include <common>
#include <packing>

vec3 getViewPosition(const in vec2 screenPosition, const in float depth) {
  vec4 clipSpacePosition = vec4(vec3(screenPosition, depth) * 2.0 - 1.0, 1.0);
  vec4 viewSpacePosition = cameraProjectionMatrixInverse * clipSpacePosition;
  return viewSpacePosition.xyz / max(1e-6, viewSpacePosition.w);
}

float getDepth(const vec2 uv) {
  return texture2D(tDepth, uv).x;
}

vec3 getViewNormal(const vec2 uv) {
  return unpackRGBToNormal(texture2D(tNormal, uv).rgb);
}

vec3 getSceneUvAndDepth(vec3 sampleViewPos) {
  vec4 sampleClipPos = cameraProjectionMatrix * vec4(sampleViewPos, 1.0);
  vec2 sampleUv = (sampleClipPos.xy / max(1e-6, sampleClipPos.w)) * 0.5 + 0.5;
  float sampleSceneDepth = getDepth(sampleUv);
  return vec3(sampleUv, sampleSceneDepth);
}

void main() {
  float depth = getDepth(vUv);
  if (depth >= 0.9999) {
    gl_FragColor = vec4(1.0);
    return;
  }

  vec3 viewPos = getViewPosition(vUv, depth);
  vec3 viewNormal = getViewNormal(vUv);

  vec2 noiseUv = vUv * resolution / noiseSize;
  vec4 noiseTexel = texture2D(tNoise, noiseUv);
  vec3 randomVec = noiseTexel.xyz * 2.0 - 1.0;
  vec3 tangent = normalize(vec3(randomVec.xy, 0.0) + vec3(1e-5, 0.0, 0.0));
  vec3 bitangent = vec3(-tangent.y, tangent.x, 0.0);
  mat3 kernelMatrix = mat3(tangent, bitangent, vec3(0.0, 0.0, 1.0));

  const int DIRECTIONS = 3;
  const int STEPS = 6;
  float ao = 0.0;

  for (int i = 0; i < DIRECTIONS; ++i) {
    float angle = float(i) / float(DIRECTIONS) * PI;
    vec4 sampleDir = vec4(cos(angle), sin(angle), 0.0, 0.5 + 0.5 * noiseTexel.w);
    sampleDir.xyz = normalize(kernelMatrix * sampleDir.xyz);

    vec3 viewDir = normalize(-viewPos.xyz);
    vec3 sliceBitangent = normalize(cross(sampleDir.xyz, viewDir) + vec3(0.0, 0.0, 1e-5));
    vec3 sliceTangent = cross(sliceBitangent, viewDir);
    vec3 normalInSlice = normalize(viewNormal - sliceBitangent * dot(viewNormal, sliceBitangent));

    vec3 tangentToNormalInSlice = cross(normalInSlice, sliceBitangent);
    vec2 cosHorizons = clamp(
      vec2(dot(viewDir, tangentToNormalInSlice), dot(viewDir, -tangentToNormalInSlice)),
      -1.0,
      1.0
    );

    for (int j = 0; j < STEPS; ++j) {
      float stepFrac = float(j + 1) / float(STEPS);
      vec3 sampleViewOffset = sampleDir.xyz * radius * sampleDir.w * pow(max(stepFrac, 1e-4), distanceExponent);

      vec3 sampleSceneUvDepth = getSceneUvAndDepth(viewPos + sampleViewOffset);
      if (sampleSceneUvDepth.z < 0.9999) {
        vec3 sampleSceneViewPos = getViewPosition(sampleSceneUvDepth.xy, sampleSceneUvDepth.z);
        vec3 viewDelta = sampleSceneViewPos - viewPos;
        float deltaLen = length(viewDelta);
        if (deltaLen > 1e-5 && abs(viewDelta.z) < thickness) {
          float sampleCosHorizon = dot(viewDir, viewDelta / deltaLen);
          cosHorizons.x += max(0.0, (sampleCosHorizon - cosHorizons.x) * mix(1.0, 2.0 / float(j + 2), distanceFallOff));
        }
      }

      sampleSceneUvDepth = getSceneUvAndDepth(viewPos - sampleViewOffset);
      if (sampleSceneUvDepth.z < 0.9999) {
        vec3 sampleSceneViewPos = getViewPosition(sampleSceneUvDepth.xy, sampleSceneUvDepth.z);
        vec3 viewDelta = sampleSceneViewPos - viewPos;
        float deltaLen = length(viewDelta);
        if (deltaLen > 1e-5 && abs(viewDelta.z) < thickness) {
          float sampleCosHorizon = dot(viewDir, viewDelta / deltaLen);
          cosHorizons.y += max(0.0, (sampleCosHorizon - cosHorizons.y) * mix(1.0, 2.0 / float(j + 2), distanceFallOff));
        }
      }
    }

    cosHorizons = clamp(cosHorizons, -1.0, 1.0);
    vec2 sinHorizons = sqrt(max(vec2(0.0), 1.0 - cosHorizons * cosHorizons));
    float nx = dot(normalInSlice, sliceTangent);
    float ny = dot(normalInSlice, viewDir);
    float nxb = 0.5 * (acos(cosHorizons.y) - acos(cosHorizons.x) + sinHorizons.x * cosHorizons.x - sinHorizons.y * cosHorizons.y);
    float nyb = 0.5 * (2.0 - cosHorizons.x * cosHorizons.x - cosHorizons.y * cosHorizons.y);
    float occlusion = nx * nxb + ny * nyb;
    ao += occlusion;
  }

  ao = clamp(ao / float(DIRECTIONS), 0.0, 1.0);
  ao = pow(max(ao, 1e-4), max(0.1, scale));
  gl_FragColor = vec4(vec3(ao), 1.0);
}
`;

function buildPoissonDenoiseFs(samples = 16, rings = 2, radiusExponent = 2) {
  const sampleVecs = buildPoissonSampleInitializer(samples, rings, radiusExponent);
  const unrolled = sampleVecs
    .map(
      (vecStr) => `
    {
      vec3 sampleDir = ${vecStr};
      vec2 offset = rotationMatrix * (sampleDir.xy * (1.0 + sampleDir.z * (radius - 1.0)) / resolution);
      denoiseSample(center, viewNormal, viewPos, vUv + offset, denoised, totalWeight);
    }`,
    )
    .join('\n');

  return /* glsl */ `
varying vec2 vUv;
uniform sampler2D tDiffuse;
uniform highp sampler2D tNormal;
uniform highp sampler2D tDepth;
uniform sampler2D tNoise;
uniform vec2 resolution;
uniform float noiseSize;
uniform mat4 cameraProjectionMatrixInverse;
uniform float lumaPhi;
uniform float depthPhi;
uniform float normalPhi;
uniform float radius;

#include <common>
#include <packing>

float getLuminance(const in vec3 a) {
  return dot(vec3(0.2125, 0.7154, 0.0721), a);
}

vec3 getViewPosition(const in vec2 screenPosition, const in float depth) {
  vec4 clipSpacePosition = vec4(vec3(screenPosition, depth) * 2.0 - 1.0, 1.0);
  vec4 viewSpacePosition = cameraProjectionMatrixInverse * clipSpacePosition;
  return viewSpacePosition.xyz / max(1e-6, viewSpacePosition.w);
}

float getDepth(const vec2 uv) {
  return texture2D(tDepth, uv).x;
}

vec3 getViewNormal(const vec2 uv) {
  return unpackRGBToNormal(texture2D(tNormal, uv).rgb);
}

void denoiseSample(
  in vec3 center,
  in vec3 viewNormal,
  in vec3 viewPos,
  in vec2 sampleUv,
  inout vec3 denoised,
  inout float totalWeight
) {
  float sampleDepth = getDepth(sampleUv);
  if (sampleDepth >= 0.9999) return;
  vec4 sampleTexel = texture2D(tDiffuse, sampleUv);
  vec3 sampleNormal = getViewNormal(sampleUv);
  vec3 neighborColor = sampleTexel.rgb;
  vec3 viewPosSample = getViewPosition(sampleUv, sampleDepth);

  float normalDiff = max(dot(viewNormal, sampleNormal), 0.0);
  float normalSimilarity = pow(max(normalDiff, 1e-4), normalPhi);
  float lumaDiff = abs(getLuminance(neighborColor) - getLuminance(center));
  float lumaSimilarity = max(1.0 - lumaDiff / max(1e-4, lumaPhi), 0.0);
  float depthDiff = abs(dot(viewPos - viewPosSample, viewNormal));
  float depthSimilarity = max(1.0 - depthDiff / max(1e-4, depthPhi), 0.0);
  float w = lumaSimilarity * depthSimilarity * normalSimilarity;

  denoised += w * neighborColor;
  totalWeight += w;
}

void main() {
  float depth = getDepth(vUv);
  if (depth >= 0.9999) {
    gl_FragColor = vec4(1.0);
    return;
  }
  vec3 viewNormal = getViewNormal(vUv);
  if (dot(viewNormal, viewNormal) < 1e-4) {
    gl_FragColor = vec4(1.0);
    return;
  }

  vec4 texel = texture2D(tDiffuse, vUv);
  vec3 center = texel.rgb;
  vec3 viewPos = getViewPosition(vUv, depth);

  vec2 noiseUv = vUv * resolution / noiseSize;
  vec4 noiseTexel = texture2D(tNoise, noiseUv);
  float ang = noiseTexel.x * 2.0 * PI;
  vec2 noiseVec = vec2(sin(ang), cos(ang));
  mat2 rotationMatrix = mat2(noiseVec.x, -noiseVec.y, noiseVec.y, noiseVec.x);

  float totalWeight = 1.0;
  vec3 denoised = center;
  ${unrolled}

  if (totalWeight > 0.0) {
    denoised /= totalWeight;
  }
  gl_FragColor = vec4(clamp(denoised, 0.0, 1.0), 1.0);
}
`;
}

const BLEND_FS = /* glsl */ `
varying vec2 vUv;
uniform float intensity;
uniform sampler2D tDiffuse;
uniform highp sampler2D tDepth;
uniform highp sampler2D tNormal;
uniform vec2 resolution;
uniform float cameraNear;
uniform float cameraFar;
uniform float inkStrength;
uniform vec3 inkColor;

#include <common>
#include <packing>

float linD(const in vec2 uv) {
  float z = texture2D(tDepth, uv).x * 2.0 - 1.0;
  return (2.0 * cameraNear * cameraFar) / max(1e-5, cameraFar + cameraNear - z * (cameraFar - cameraNear));
}

vec3 rdN(const in vec2 uv) {
  return unpackRGBToNormal(texture2D(tNormal, uv).rgb);
}

void main() {
  float d = texture2D(tDepth, vUv).x;
  if (d >= 0.9999) {
    gl_FragColor = vec4(1.0);
    return;
  }
  vec4 texel = texture2D(tDiffuse, vUv);
  vec3 ao = mix(vec3(1.0), clamp(texel.rgb, 0.0, 1.0), clamp(intensity, 0.0, 1.0));

  if (inkStrength > 0.001) {
    vec2 stepUv = 1.0 / max(resolution, vec2(1.0));
    float d0 = linD(vUv);
    float maxJump = d0 * 2.5;
    float dR = min(linD(vUv + vec2(stepUv.x, 0.0)), maxJump);
    float dL = min(linD(vUv - vec2(stepUv.x, 0.0)), maxJump);
    float dU = min(linD(vUv + vec2(0.0, stepUv.y)), maxJump);
    float dD = min(linD(vUv - vec2(0.0, stepUv.y)), maxJump);
    float lap = abs(dR + dL + dU + dD - 4.0 * d0) / max(d0, 0.5);
    float eD = smoothstep(0.004, 0.016, lap);

    vec3 n0 = rdN(vUv);
    float dRraw = texture2D(tDepth, vUv + vec2(stepUv.x, 0.0)).x;
    float dUraw = texture2D(tDepth, vUv + vec2(0.0, stepUv.y)).x;
    vec3 nR = dRraw < 0.9999 ? rdN(vUv + vec2(stepUv.x, 0.0)) : n0;
    vec3 nU = dUraw < 0.9999 ? rdN(vUv + vec2(0.0, stepUv.y)) : n0;
    float eN = smoothstep(0.32, 0.72, max(length(n0 - nR), length(n0 - nU)));

    float edge = clamp(max(eD, eN * 0.68) * inkStrength, 0.0, 1.0);
    ao *= mix(vec3(1.0), inkColor, edge);
  }

  gl_FragColor = vec4(ao, 1.0);
}
`;

export function createGTAORig(THREE, { renderer, scene, options = {} }) {
  const scaleFactor = Math.max(0.25, Math.min(1.0, options.resolutionScale ?? 1.0));
  const sizeVec = new THREE.Vector2();
  renderer.getSize(sizeVec);
  let width = Math.max(64, Math.round(sizeVec.x * scaleFactor));
  let height = Math.max(64, Math.round(sizeVec.y * scaleFactor));

  const depthTexture = new THREE.DepthTexture(width, height);
  depthTexture.format = THREE.DepthStencilFormat;
  depthTexture.type = THREE.UnsignedInt248Type;
  depthTexture.minFilter = THREE.NearestFilter;
  depthTexture.magFilter = THREE.NearestFilter;

  const normalRenderTarget = new THREE.WebGLRenderTarget(width, height, {
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    type: THREE.HalfFloatType,
    depthTexture,
  });
  normalRenderTarget.texture.generateMipmaps = false;

  const gtaoRenderTarget = new THREE.WebGLRenderTarget(width, height, {
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
    type: THREE.HalfFloatType,
    depthBuffer: false,
  });
  gtaoRenderTarget.texture.generateMipmaps = false;

  const pdRenderTarget = gtaoRenderTarget.clone();
  pdRenderTarget.texture.generateMipmaps = false;

  const gtaoNoiseTexture = createMagicSquareNoiseTexture(THREE, 5);
  const pdNoiseTexture = createBlueNoiseTexture(THREE, 64);

  const normalMaterial = new THREE.MeshNormalMaterial({
    blending: THREE.NoBlending,
  });

  const gtaoMaterial = new THREE.ShaderMaterial({
    uniforms: {
      tNormal: { value: normalRenderTarget.texture },
      tDepth: { value: depthTexture },
      tNoise: { value: gtaoNoiseTexture },
      resolution: { value: new THREE.Vector2(width, height) },
      noiseSize: { value: 5.0 },
      cameraNear: { value: 0.1 },
      cameraFar: { value: 100.0 },
      cameraProjectionMatrix: { value: new THREE.Matrix4() },
      cameraProjectionMatrixInverse: { value: new THREE.Matrix4() },
      radius: { value: options.radius ?? 0.16 },
      distanceExponent: { value: options.distanceExponent ?? 1.4 },
      thickness: { value: options.thickness ?? 0.6 },
      distanceFallOff: { value: options.distanceFallOff ?? 1.0 },
      scale: { value: options.scale ?? 1.0 },
    },
    vertexShader: PASS_VS,
    fragmentShader: GTAO_FS,
    blending: THREE.NoBlending,
    depthTest: false,
    depthWrite: false,
  });

  const pdMaterial = new THREE.ShaderMaterial({
    uniforms: {
      tDiffuse: { value: gtaoRenderTarget.texture },
      tNormal: { value: normalRenderTarget.texture },
      tDepth: { value: depthTexture },
      tNoise: { value: pdNoiseTexture },
      resolution: { value: new THREE.Vector2(width, height) },
      noiseSize: { value: 64.0 },
      cameraProjectionMatrixInverse: { value: new THREE.Matrix4() },
      lumaPhi: { value: options.lumaPhi ?? 10.0 },
      depthPhi: { value: options.depthPhi ?? 2.0 },
      normalPhi: { value: options.normalPhi ?? 3.0 },
      radius: { value: options.denoiseRadius ?? 6.0 },
    },
    vertexShader: PASS_VS,
    fragmentShader: buildPoissonDenoiseFs(options.samples ?? 16, 2, 2),
    blending: THREE.NoBlending,
    depthTest: false,
    depthWrite: false,
  });

  const blendMaterial = new THREE.ShaderMaterial({
    uniforms: {
      tDiffuse: { value: pdRenderTarget.texture },
      tDepth: { value: depthTexture },
      tNormal: { value: normalRenderTarget.texture },
      resolution: { value: new THREE.Vector2(width, height) },
      cameraNear: { value: 0.1 },
      cameraFar: { value: 100.0 },
      intensity: { value: options.intensity ?? 0.72 },
      inkStrength: { value: options.inkStrength ?? 0.0 },
      inkColor: { value: new THREE.Color(options.inkColor ?? '#181C22') },
    },
    vertexShader: PASS_VS,
    fragmentShader: BLEND_FS,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.CustomBlending,
    blendSrc: THREE.DstColorFactor,
    blendDst: THREE.ZeroFactor,
    blendEquation: THREE.AddEquation,
    blendSrcAlpha: THREE.ZeroFactor,
    blendDstAlpha: THREE.OneFactor,
    blendEquationAlpha: THREE.AddEquation,
  });

  const quadScene = new THREE.Scene();
  const quadCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const quadMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), gtaoMaterial);
  quadMesh.frustumCulled = false;
  quadScene.add(quadMesh);

  const prevClearColor = new THREE.Color();
  const hiddenCache = [];

  function syncSize() {
    renderer.getSize(sizeVec);
    const pr = renderer.getPixelRatio ? renderer.getPixelRatio() : 1;
    const targetW = Math.max(64, Math.round(sizeVec.x * pr * scaleFactor));
    const targetH = Math.max(64, Math.round(sizeVec.y * pr * scaleFactor));
    if (targetW !== width || targetH !== height) {
      width = targetW;
      height = targetH;
      normalRenderTarget.setSize(width, height);
      gtaoRenderTarget.setSize(width, height);
      pdRenderTarget.setSize(width, height);
      gtaoMaterial.uniforms.resolution.value.set(width, height);
      pdMaterial.uniforms.resolution.value.set(width, height);
      blendMaterial.uniforms.resolution.value.set(width, height);
    }
  }

  function applyConfig(cfg = {}) {
    if (cfg.intensity !== undefined) blendMaterial.uniforms.intensity.value = cfg.intensity;
    if (cfg.inkStrength !== undefined) blendMaterial.uniforms.inkStrength.value = cfg.inkStrength;
    if (cfg.inkColor !== undefined) blendMaterial.uniforms.inkColor.value.set(cfg.inkColor);
    if (cfg.radius !== undefined) gtaoMaterial.uniforms.radius.value = cfg.radius;
    if (cfg.distanceExponent !== undefined) gtaoMaterial.uniforms.distanceExponent.value = cfg.distanceExponent;
    if (cfg.thickness !== undefined) gtaoMaterial.uniforms.thickness.value = cfg.thickness;
    if (cfg.distanceFallOff !== undefined) gtaoMaterial.uniforms.distanceFallOff.value = cfg.distanceFallOff;
    if (cfg.scale !== undefined) gtaoMaterial.uniforms.scale.value = cfg.scale;
    if (cfg.lumaPhi !== undefined) pdMaterial.uniforms.lumaPhi.value = cfg.lumaPhi;
    if (cfg.depthPhi !== undefined) pdMaterial.uniforms.depthPhi.value = cfg.depthPhi;
    if (cfg.normalPhi !== undefined) pdMaterial.uniforms.normalPhi.value = cfg.normalPhi;
    if (cfg.denoiseRadius !== undefined) pdMaterial.uniforms.denoiseRadius ? (pdMaterial.uniforms.denoiseRadius.value = cfg.denoiseRadius) : (pdMaterial.uniforms.radius.value = cfg.denoiseRadius);
  }

  function update(camera) {
    syncSize();

    // Sync active clipping planes onto `normalMaterial` so section cuts never leave a pale AO ghost (`teardown` rule)
    const activeClips = scene.userData?.activeClippingPlanes || null;
    if (normalMaterial.clippingPlanes !== activeClips) {
      normalMaterial.clippingPlanes = activeClips;
      normalMaterial.clipping = Boolean(activeClips && activeClips.length);
      normalMaterial.needsUpdate = true;
    }

    // Hide non-AO casters (lines, points, floor contact shadows, section caps, stencil helpers, HUD planes, transparent glass)
    hiddenCache.length = 0;
    scene.traverse((o) => {
      if (!o.visible) return;
      if (
        o.isPoints ||
        o.isLine ||
        o.isLineSegments ||
        o.userData?.skipAO ||
        o.userData?.skipContactShadow ||
        o.userData?.isStencilHelper ||
        o.userData?.isSectionCap ||
        o.userData?.isHudOverlay ||
        (o.isMesh && o.material && !Array.isArray(o.material) && o.material.transparent && o.material.opacity < 0.5)
      ) {
        o.visible = false;
        hiddenCache.push(o);
      }
    });

    const prevBg = scene.background;
    const prevFog = scene.fog;
    const prevAutoClear = renderer.autoClear;
    const prevClearAlpha = renderer.getClearAlpha();
    renderer.getClearColor(prevClearColor);

    scene.background = null;
    scene.fog = null;

    // 1. G-Buffer Pass (View Normals + Depth)
    renderer.setRenderTarget(normalRenderTarget);
    renderer.autoClear = false;
    renderer.setClearColor(0x7777ff, 1.0);
    renderer.clear(true, true, false);
    scene.overrideMaterial = normalMaterial;
    renderer.render(scene, camera);
    scene.overrideMaterial = null;

    // Restore visibility & scene background
    for (let i = 0; i < hiddenCache.length; i++) {
      hiddenCache[i].visible = true;
    }
    hiddenCache.length = 0;
    scene.background = prevBg;
    scene.fog = prevFog;

    // 2. GTAO Horizon Integral Pass
    gtaoMaterial.uniforms.cameraNear.value = camera.near;
    gtaoMaterial.uniforms.cameraFar.value = camera.far;
    gtaoMaterial.uniforms.cameraProjectionMatrix.value.copy(camera.projectionMatrix);
    gtaoMaterial.uniforms.cameraProjectionMatrixInverse.value.copy(camera.projectionMatrixInverse);
    blendMaterial.uniforms.cameraNear.value = camera.near;
    blendMaterial.uniforms.cameraFar.value = camera.far;

    renderer.setRenderTarget(gtaoRenderTarget);
    renderer.setClearColor(0xffffff, 1.0);
    renderer.clear(true, false, false);
    quadMesh.material = gtaoMaterial;
    renderer.render(quadScene, quadCamera);

    // 3. Poisson Bilateral Denoise Pass
    pdMaterial.uniforms.cameraProjectionMatrixInverse.value.copy(camera.projectionMatrixInverse);
    renderer.setRenderTarget(pdRenderTarget);
    renderer.setClearColor(0xffffff, 1.0);
    renderer.clear(true, false, false);
    quadMesh.material = pdMaterial;
    renderer.render(quadScene, quadCamera);

    // Restore renderer state
    renderer.setRenderTarget(null);
    renderer.autoClear = prevAutoClear;
    renderer.setClearColor(prevClearColor, prevClearAlpha);
  }

  function composite() {
    const prevAutoClear = renderer.autoClear;
    renderer.autoClear = false;
    quadMesh.material = blendMaterial;
    renderer.render(quadScene, quadCamera);
    renderer.autoClear = prevAutoClear;
  }

  return {
    normalMaterial,
    normalRenderTarget,
    gtaoRenderTarget,
    pdRenderTarget,
    applyConfig,
    setOptions: applyConfig,
    update,
    composite,
  };
}
