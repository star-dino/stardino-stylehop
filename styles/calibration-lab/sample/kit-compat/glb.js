// Meshes made in Blender (or any DCC), dropped into a teardown page as named, separable parts.
//
//   import hullGlb from './hull.glb';                  // build.mjs inlines it (base64), or "url:hull.glb" with build.json external
//   import {loadGLB, partsOf, explodeRig, applyMaterials} from 'teardown-kit/glb.js';
//   const root = await loadGLB(hullGlb);               // THREE.Group
//   const parts = partsOf(root);                       // {byName, bySub: {jaw: [..], armour: [..]}, all}
//   applyMaterials(root, M);                           // Blender material "white" / "alu" / "liner" → M.white ...
//   const rig = explodeRig(parts);  rig.set('armour', k)   // k 0..1, pure function of k
//
// Naming contract with Blender (docs/form.md, "Blender stage"):
//   object name   <subsystem>__<part>         e.g. armour__dorsal_03, jaw__lower, core__sphere
//   custom props  explode = [x, y, z]         rail in model units for k = 1 (else away from the model's centre)
//                 pivot   = [x, y, z]         hinge point for `hinge` (optional)
//                 hinge   = [ax, ay, az, deg] rotate about axis through pivot at k = 1 (optional; armour flaps)
//   material name a key of createMaterials() (white, ceramic, alu, titanium, liner, steel, brass, ...); others keep
//                 their own material, governed as 'shell'
// glTF export from Blender: +Y up, apply transforms, "Custom Properties" on (they arrive as userData).
import {THREE} from '/styles/calibration-lab/kernel.js';
import {parseGlbBuffer} from '/engine/three_bridge.js';
import {governMaterial} from './look.js';

const b64ToBuffer = (s) => {
  const bin = atob(s);
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u.buffer;
};

// stylehop's zero-dependency parser drops node `extras` (Blender custom properties: explode / pivot / hinge) and
// there is no GLTFLoader in the r147 global build, so read the JSON chunk again and put extras on userData.
function glbJson(buf) {
  const dv = new DataView(buf);
  let off = 12;
  while (off + 8 <= buf.byteLength) {
    const len = dv.getUint32(off, true);
    const type = dv.getUint32(off + 4, true);
    if (type === 0x4e4f534a) return JSON.parse(new TextDecoder('utf-8').decode(new Uint8Array(buf, off + 8, len)));
    off += 8 + len;
  }
  return null;
}

/**
 * src: base64 string, "url:<url>", a plain URL / path (anything else with '/' or '.glb'), or an ArrayBuffer.
 * opts.studio (optional, calibration-lab studio): parsed with studio.parseModelBuffer. Never added to a scene.
 * Returns the THREE.Group (same as the teardown kit); the group is not added to anything.
 */
export async function loadGLB(src, {studio = null} = {}) {
  let data = src;
  if (typeof src === 'string') {
    if (src.startsWith('url:')) data = await (await fetch(src.slice(4))).arrayBuffer();
    else if (/^(\/|\.\/|\.\.\/|https?:|data:|blob:)/.test(src) || /\.glb(\?|#|$)/i.test(src)) data = await (await fetch(src)).arrayBuffer();
    else data = b64ToBuffer(src);
  }
  const res = studio?.parseModelBuffer ? studio.parseModelBuffer(data) : parseGlbBuffer(THREE, data);
  const json = glbJson(data);
  (json?.nodes || []).forEach((n, i) => {
    if (n.extras && res.nodes[i]) Object.assign(res.nodes[i].userData, JSON.parse(JSON.stringify(n.extras)));
  });
  const root = res.scene;
  root.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  return root;
}

/** Index the named parts. A part is any object whose name has `__`; its subsystem is the prefix. */
export function partsOf(root) {
  const byName = {};
  const bySub = {};
  const all = [];
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    const m = /^(.+?)__(.+)$/.exec(o.name);
    if (!m) return;
    // skip children of an already-indexed part (a part may be an Empty holding several meshes)
    for (let p = o.parent; p; p = p.parent) if (p.userData.__part) return;
    o.userData.__part = true;
    o.userData.subsystem = o.userData.subsystem ?? m[1];
    byName[o.name] = o;
    (bySub[o.userData.subsystem] ||= []).push(o);
    all.push(o);
  });
  return {byName, bySub, all, root};
}

/** Map Blender material names onto the kit's materials (look.js createMaterials). Unknown ones are governed. */
export function applyMaterials(root, M, rename = {}) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const swap = (m) => {
      const key = rename[m.name] ?? m.name.toLowerCase().replace(/\.\d+$/, '');
      return M[key] ?? governMaterial(m, 'shell');
    };
    o.material = Array.isArray(o.material) ? o.material.map(swap) : swap(o.material);
  });
}

/**
 * Exploded view and hinged flaps, a pure function of k per subsystem. Rails come from the part's `explode` property,
 * else from the model's centre through the part's centre, `distance` long. set(sub, k) / setAll(k).
 */
export function explodeRig(parts, {distance = 0.35, centre} = {}) {
  const box = new THREE.Box3().setFromObject(parts.root);
  const c = centre ? new THREE.Vector3(...centre) : box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  // world-space rails, pivots and axes are converted into each part's parent space, so the rig keeps working when
  // the whole model is moved, scaled or animated by a parent
  const rails = parts.all.map((o) => {
    const pc = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
    let world;
    if (Array.isArray(o.userData.explode)) world = new THREE.Vector3(...o.userData.explode);
    else {
      world = pc.clone().sub(c);
      if (world.lengthSq() < 1e-9) world.set(0, 1, 0);
      world.setLength(distance * size);
    }
    const toLocal = (v) => o.parent.worldToLocal(v.clone());
    const rail = toLocal(pc.clone().add(world)).sub(toLocal(pc));
    const h = o.userData.hinge;
    let hinge = null;
    if (Array.isArray(h)) {
      const pivotW = Array.isArray(o.userData.pivot) ? new THREE.Vector3(...o.userData.pivot) : pc;
      const axisW = new THREE.Vector3(h[0], h[1], h[2]).normalize();
      hinge = {axis: toLocal(pivotW.clone().add(axisW)).sub(toLocal(pivotW)).normalize(), deg: h[3], pivot: toLocal(pivotW)};
    }
    return {o, sub: o.userData.subsystem, base: o.position.clone(), baseQ: o.quaternion.clone(), rail, hinge};
  });
  const q = new THREE.Quaternion();
  const tmp = new THREE.Vector3();
  const apply = (r, k) => {
    r.o.position.copy(r.base);
    r.o.quaternion.copy(r.baseQ);
    if (r.hinge) {
      q.setFromAxisAngle(r.hinge.axis, ((r.hinge.deg * Math.PI) / 180) * k);
      tmp.copy(r.base).sub(r.hinge.pivot).applyQuaternion(q).add(r.hinge.pivot);
      r.o.position.copy(tmp);
      r.o.quaternion.premultiply(q);
    } else r.o.position.addScaledVector(r.rail, k);
  };
  return {
    rails,
    subsystems: [...new Set(rails.map((r) => r.sub))],
    set(sub, k) {
      for (const r of rails) if (r.sub === sub) apply(r, k);
    },
    setAll(k) {
      for (const r of rails) apply(r, k);
    },
  };
}
