// Industrial part generators: the secondary and tertiary forms that make a machine read as engineered rather than
// assembled from primitives. Every function returns a BufferGeometry (or {group}) in your model units, centred on
// the origin, with box-projected UVs so the micro-normal maps from look.js keep one grain size.
//
//   import {machinedPlate, ribbedLink, counterboreBoss, bolt, swept, flangedRing, instanced} from 'teardown-kit/parts.js';
//
// Ported from the calibration-lab kernel (stardino-stylehop). Defaults are in millimetres.
import {THREE} from '/styles/calibration-lab/kernel.js';
import {boxUVs, createMaterials, governMaterial} from './look.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const V2 = (r, y) => new THREE.Vector2(r, y);

/** Merge geometries (indexed or not) keeping position, normal, uv. */
export function mergeGeometries(list) {
  let vc = 0;
  let ic = 0;
  for (const g of list) {
    vc += g.attributes.position.count;
    ic += g.index ? g.index.count : g.attributes.position.count;
  }
  const pos = new Float32Array(vc * 3);
  const uv = new Float32Array(vc * 2);
  const idx = new Uint32Array(ic);
  let vo = 0;
  let io = 0;
  for (const g of list) {
    pos.set(g.attributes.position.array, vo * 3);
    if (g.attributes.uv) uv.set(g.attributes.uv.array, vo * 2);
    const c = g.attributes.position.count;
    if (g.index) for (const k of g.index.array) idx[io++] = k + vo;
    else for (let k = 0; k < c; k++) idx[io++] = k + vo;
    vo += c;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  out.setIndex(new THREE.BufferAttribute(idx, 1));
  out.computeVertexNormals();
  return out;
}

function roundedRect(w, d, r = 4) {
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
  return s;
}

function slotPath(cx, cz, w, d, r) {
  const rr = Math.max(0.01, Math.min(r, Math.min(w, d) / 2 - 0.01));
  const hw = w / 2;
  const hd = d / 2;
  const p = new THREE.Path();
  p.moveTo(cx - hw + rr, cz - hd);
  p.quadraticCurveTo(cx - hw, cz - hd, cx - hw, cz - hd + rr);
  p.lineTo(cx - hw, cz + hd - rr);
  p.quadraticCurveTo(cx - hw, cz + hd, cx - hw + rr, cz + hd);
  p.lineTo(cx + hw - rr, cz + hd);
  p.quadraticCurveTo(cx + hw, cz + hd, cx + hw, cz + hd - rr);
  p.lineTo(cx + hw, cz - hd + rr);
  p.quadraticCurveTo(cx + hw, cz - hd, cx + hw - rr, cz - hd);
  return p;
}

const extrudeY = (shape, h, bevel, curveSegments = 12) => {
  const bv = Math.min(bevel, h * 0.2);
  const g = new THREE.ExtrudeGeometry(shape, {depth: Math.max(0.2, h - bv * 2), bevelEnabled: bv > 0.01, bevelThickness: bv, bevelSize: bv, bevelSegments: 2, curveSegments});
  g.rotateX(-Math.PI / 2);
  g.translate(0, -h / 2 + bv, 0);
  return g;
};

/** Rounded, bevelled block: w x d footprint, h tall. */
export function block({w, h, d, r = 4, bevel = 1.2, uvScale}) {
  return boxUVs(extrudeY(roundedRect(w, d, r), h, Math.min(bevel, Math.min(w, d) * 0.22)), uvScale);
}

/**
 * Machined plate / bulkhead / flange: a rounded rect (w x d, h thick) with bores `holes: [{x, z, r}]` and
 * lightening pockets `slots: [{x, z, w, d, r}]` cut through before the bevel.
 */
export function machinedPlate({w, h, d, r = 5, bevel = 1, holes = [], slots = [], uvScale}) {
  const s = roundedRect(w, d, r);
  for (const o of holes) {
    const p = new THREE.Path();
    p.absarc(o.x || 0, -(o.z || 0), o.r, 0, Math.PI * 2, true);
    s.holes.push(p);
  }
  for (const o of slots) s.holes.push(slotPath(o.x || 0, -(o.z || 0), o.w, o.d, o.r ?? Math.min(o.w, o.d) * 0.45));
  return boxUVs(extrudeY(s, h, Math.min(bevel, Math.min(w, d) * 0.2), 24), uvScale);
}

/** Boss with a through bore and a stepped counterbore: fasteners sit in a recess, never on a flat face. Axis y. */
export function counterboreBoss({rOuter = 11, rBore = 3.2, rCounter = 6.8, hTotal = 9, hCounter = 3.8, bevel = 0.8, seg = 32, uvScale} = {}) {
  const y0 = -hTotal / 2;
  const y1 = hTotal / 2;
  const yc = y1 - clamp(hCounter, 0.5, hTotal - 1);
  const b = Math.min(bevel, (rOuter - rCounter) * 0.4, hTotal * 0.2);
  const prof = [[rBore, y0], [rOuter - b, y0], [rOuter, y0 + b], [rOuter, y1 - b], [rOuter - b, y1], [rCounter, y1], [rCounter, yc], [rBore, yc], [rBore, y0]];
  return boxUVs(new THREE.LatheGeometry(prof.map(([r, y]) => V2(r, y)), seg), uvScale);
}

/**
 * Forged I-beam link between two bores at y = -length/2 (big end) and +length/2 (small end), lying in the xy plane,
 * `thickness` along z, with a recessed web pocket on both faces.
 */
export function ribbedLink({length = 143, rBig = 23, rSmall = 13.5, rBoreBig = 15, rBoreSmall = 8.5, beamW = 19, thickness = 16, webThickness = 5.5, bevel = 0.9, uvScale} = {}) {
  const hl = length / 2;
  const w0 = beamW * 0.56;
  const w1 = beamW * 0.42;
  const aB = Math.acos(clamp(w0 / rBig, -0.95, 0.95));
  const aS = Math.acos(clamp(w1 / rSmall, -0.95, 0.95));
  const outline = () => {
    const s = new THREE.Shape();
    s.absarc(0, -hl, rBig, aB, Math.PI - aB, true);
    s.lineTo(-w1, hl - rSmall * Math.sin(aS));
    s.absarc(0, hl, rSmall, Math.PI + aS, -aS, true);
    s.closePath();
    for (const [y, r] of [[-hl, rBoreBig], [hl, rBoreSmall]]) {
      if (r <= 0) continue;
      const p = new THREE.Path();
      p.absarc(0, y, r, 0, Math.PI * 2, false);
      s.holes.push(p);
    }
    return s;
  };
  const web = new THREE.ExtrudeGeometry(outline(), {depth: webThickness, bevelEnabled: false, curveSegments: 28});
  web.translate(0, 0, -webThickness / 2);
  const rim = outline();
  const sb = -hl + rBig + 4;
  const st = hl - rSmall - 4;
  const sw = Math.max(3, w0 + w1 - 7);
  if (st - sb > 8) rim.holes.push(slotPath(0, (sb + st) / 2, sw, st - sb, Math.min(sw * 0.42, 4)));
  const rd = Math.max(1, thickness - bevel * 2);
  const rimG = new THREE.ExtrudeGeometry(rim, {depth: rd, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 2, curveSegments: 28});
  rimG.translate(0, 0, -rd / 2);
  return boxUVs(mergeGeometries([web, rimG]), uvScale);
}

/** Spur or helical gear from a tooth count, axis z, with optional bore and lightening holes. */
export function gear({teeth, rOut, rRoot, width, helix = 0, holeR = 0, lighteningHoles = 0, lighteningR = 0, bevel = 0.8, uvScale}) {
  const s = new THREE.Shape();
  const da = (Math.PI * 2) / teeth;
  for (let i = 0; i < teeth; i++) {
    const a0 = i * da;
    [[rRoot, 0], [rRoot, 0.2], [rOut, 0.33], [rOut, 0.62], [rRoot, 0.75]].forEach(([r, f], k) => {
      const x = r * Math.cos(a0 + da * f);
      const y = r * Math.sin(a0 + da * f);
      i === 0 && k === 0 ? s.moveTo(x, y) : s.lineTo(x, y);
    });
  }
  s.closePath();
  if (holeR > 0) {
    const p = new THREE.Path();
    p.absarc(0, 0, holeR, 0, Math.PI * 2, true);
    s.holes.push(p);
  }
  if (lighteningHoles > 0) {
    const pr = (rRoot + Math.max(holeR, rRoot * 0.25)) * 0.52;
    const lr = lighteningR || Math.min((rRoot - holeR) * 0.24, (pr * Math.PI) / (lighteningHoles * 1.8));
    for (let i = 0; lr > 1e-3 && i < lighteningHoles; i++) {
      const a = (i / lighteningHoles) * Math.PI * 2;
      const p = new THREE.Path();
      p.absarc(Math.cos(a) * pr, Math.sin(a) * pr, lr, 0, Math.PI * 2, true);
      s.holes.push(p);
    }
  }
  const g = new THREE.ExtrudeGeometry(s, {depth: width, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 1, curveSegments: 4});
  g.translate(0, 0, -width / 2);
  if (helix) {
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const a = (p.getZ(i) / width) * helix;
      const x = p.getX(i);
      const y = p.getY(i);
      p.setXY(i, x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a));
    }
  }
  g.computeVertexNormals();
  return boxUVs(g, uvScale);
}

/** Coil spring along +y from 0 to len. Scale y to compress it. */
export function helix({r, wire, turns, len, seg = 160, uvScale}) {
  const pts = [];
  for (let i = 0; i <= seg; i++) {
    const u = i / seg;
    const a = u * turns * Math.PI * 2;
    pts.push(new THREE.Vector3(Math.cos(a) * r, u * len, Math.sin(a) * r));
  }
  return boxUVs(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), seg, wire, 10, false), uvScale);
}

/** Socket-head bolt with a washer, axis y, head up. */
export function bolt({r = 4, h = 6, washer = true, uvScale} = {}) {
  const prof = [[r * 0.46, h * 0.12], [r * 0.46, h * 0.5], [r * 0.92, h * 0.5], [r, h * 0.38], [r, -h * 0.5], [0, -h * 0.5], [0, h * 0.12], [r * 0.46, h * 0.12]];
  const head = new THREE.LatheGeometry(prof.map(([x, y]) => V2(x, y)), 6);
  if (!washer) return boxUVs(head, uvScale);
  const w = new THREE.CylinderGeometry(r * 1.62, r * 1.68, h * 0.28, 20);
  w.translate(0, -h / 2 + h * 0.14, 0);
  return boxUVs(mergeGeometries([head, w]), uvScale);
}

/** Accordion bellows / boot along y. */
export function bellows({rInner = 9, rOuter = 14, rBore = 0, ribs = 7, len = 36, seg = 36, uvScale} = {}) {
  const y0 = -len / 2;
  const st = len / ribs;
  const prof = [[rBore, y0], [rInner, y0]];
  for (let i = 0; i < ribs; i++) {
    const ya = y0 + i * st;
    prof.push([rInner, ya + st * 0.12], [rOuter, ya + st * 0.42], [rOuter, ya + st * 0.58], [rInner, ya + st * 0.88]);
  }
  prof.push([rInner, y0 + len], [rBore, y0 + len]);
  return boxUVs(new THREE.LatheGeometry(prof.map(([r, y]) => V2(r, y)), seg), uvScale);
}

/** Ball joint: {ballGeo (ball + neck down -y), socketGeo (cup opening up)}. */
export function ballJoint({rBall = 10, rSocket = 12.6, neckR = 4.6, neckLen = 14, cupAngle = Math.PI * 0.62, seg = 32, uvScale} = {}) {
  const ball = new THREE.SphereGeometry(rBall, seg, Math.round(seg * 0.65));
  const neck = new THREE.CylinderGeometry(neckR, neckR * 1.12, neckLen, Math.round(seg * 0.75));
  neck.translate(0, -rBall * 0.7 - neckLen / 2, 0);
  const prof = [];
  const n = 16;
  for (let i = 0; i <= n; i++) {
    const a = -Math.PI / 2 + (i / n) * cupAngle;
    prof.push(V2(Math.max(0, Math.cos(a) * rSocket), Math.sin(a) * rSocket));
  }
  for (let i = n; i >= 0; i--) {
    const a = -Math.PI / 2 + (i / n) * cupAngle;
    prof.push(V2(Math.max(0, Math.cos(a) * (rBall + 0.35)), Math.sin(a) * (rBall + 0.35)));
  }
  prof.push(prof[0].clone());
  return {ballGeo: boxUVs(mergeGeometries([ball, neck]), uvScale), socketGeo: boxUVs(new THREE.LatheGeometry(prof, seg), uvScale)};
}

/**
 * Tube swept along points with a parallel-transport frame (no twist flips), radius and z-scale as functions of
 * u in 0..1: tapered tentacles, hoses, manifolds, cable runs. Re-pose with updateSwept(geo, points) every frame.
 */
export function swept({points, radiusAt = 6, scaleZAt = null, tubularSeg = 48, radialSeg = 20, capEnds = true}) {
  const stride = radialSeg + 1;
  const body = (tubularSeg + 1) * stride;
  const total = body + (capEnds ? 2 * (radialSeg + 2) : 0);
  const idx = [];
  for (let i = 0; i < tubularSeg; i++)
    for (let j = 0; j < radialSeg; j++) {
      const a = i * stride + j;
      const b = a + stride;
      // (a, a+1, b): T x B = +N, outward. The old (a, b, a+1) faced inward, so FrontSide showed the tube's far wall.
      idx.push(a, a + 1, b, b, a + 1, b + 1);
    }
  if (capEnds) {
    const s0 = body;
    const s1 = body + radialSeg + 2;
    for (let j = 0; j < radialSeg; j++) idx.push(s0, s0 + 1 + ((j + 1) % stride), s0 + 1 + j, s1, s1 + 1 + j, s1 + 1 + ((j + 1) % stride));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(total * 3), 3));
  g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(total * 3), 3));
  g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(total * 2), 2));
  g.setIndex(idx);
  g.userData.sweep = {tubularSeg, radialSeg, capEnds, radiusAt, scaleZAt};
  return updateSwept(g, points);
}

export function updateSwept(g, points) {
  const {tubularSeg, radialSeg, capEnds, radiusAt, scaleZAt} = g.userData.sweep;
  const stride = radialSeg + 1;
  const body = (tubularSeg + 1) * stride;
  const curve = new THREE.CatmullRomCurve3(points.map((p) => (p.isVector3 ? p : new THREE.Vector3(...p))));
  const rFn = typeof radiusAt === 'function' ? radiusAt : () => radiusAt;
  const zFn = typeof scaleZAt === 'function' ? scaleZAt : () => scaleZAt ?? 1;
  const pos = g.attributes.position.array;
  const uv = g.attributes.uv.array;
  const T = new THREE.Vector3();
  const pT = new THREE.Vector3();
  const N = new THREE.Vector3();
  const B = new THREE.Vector3();
  const ax = new THREE.Vector3();
  const q = new THREE.Quaternion();
  const P = new THREE.Vector3();
  for (let i = 0; i <= tubularSeg; i++) {
    const u = i / tubularSeg;
    curve.getPointAt(u, P);
    curve.getTangentAt(u, T).normalize();
    if (i === 0) {
      B.crossVectors(T, Math.abs(T.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0)).normalize();
      N.crossVectors(B, T).normalize();
    } else {
      ax.crossVectors(pT, T);
      const s = ax.length();
      if (s > 1e-5) N.applyQuaternion(q.setFromAxisAngle(ax.divideScalar(s), Math.atan2(s, clamp(pT.dot(T), -1, 1))));
      N.sub(T.clone().multiplyScalar(N.dot(T))).normalize();
      B.crossVectors(T, N).normalize();
    }
    pT.copy(T);
    const rx = rFn(u);
    const rz = rx * zFn(u);
    for (let j = 0; j <= radialSeg; j++) {
      const a = (j / radialSeg) * Math.PI * 2;
      const c = Math.cos(a);
      const s = Math.sin(a);
      const k = (i * stride + j) * 3;
      pos[k] = P.x + N.x * c * rx + B.x * s * rz;
      pos[k + 1] = P.y + N.y * c * rx + B.y * s * rz;
      pos[k + 2] = P.z + N.z * c * rx + B.z * s * rz;
      uv[(i * stride + j) * 2] = u * 6;
      uv[(i * stride + j) * 2 + 1] = (j / radialSeg) * 2;
    }
    if (capEnds && (i === 0 || i === tubularSeg)) {
      const cb = i === 0 ? body : body + radialSeg + 2;
      pos.set([P.x, P.y, P.z], cb * 3);
      for (let j = 0; j <= radialSeg; j++) pos.copyWithin((cb + 1 + j) * 3, (i * stride + j) * 3, (i * stride + j) * 3 + 3);
    }
  }
  g.attributes.position.needsUpdate = true;
  g.attributes.uv.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

/**
 * Soft contact shadow disc for where a boss, bolt or shaft meets a face: lay it on the face (it lies in xz) so
 * parts read as seated, not pasted. Hidden in silhouette mode.
 */
export function creviceRing({rIn = 4, rOut = 9, opacity = 0.46} = {}) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const k = rIn / rOut;
  const gr = g.createRadialGradient(64, 64, 62 * k * 0.9, 64, 64, 62);
  gr.addColorStop(0, 'rgba(255,255,255,0.95)');
  gr.addColorStop(0.45, 'rgba(255,255,255,0.65)');
  gr.addColorStop(0.8, 'rgba(255,255,255,0.18)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 128, 128);
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(rOut * 2.1, rOut * 2.1).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({color: '#0D1014', alphaMap: new THREE.CanvasTexture(c), transparent: true, opacity, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2, toneMapped: false}),
  );
  m.userData.noSilhouette = true;
  return m;
}

/**
 * I-section ring frame (a bulkhead, a rib, a bearing ring) with lightening holes and bolts on both faces. Axis z.
 * Returns {group, body}. Pass `mat`/`boltMat` or it builds its own from createMaterials().
 */
export function flangedRing({rOuter = 68, rInner = 46, thickness = 10, webThickness = 4.2, flangeRim = 3.8, lighteningHoles = 8, boltCount = 8, bevel = 0.8, mat, boltMat, uvScale} = {}) {
  const M = mat && boltMat ? null : createMaterials();
  const rMid = (rOuter + rInner) / 2;
  const holeR = Math.min((rOuter - rInner) * 0.24, (rMid * Math.PI) / Math.max(4, lighteningHoles * 2.2));
  const ring = (rO, rI, depth, bv) => {
    const s = new THREE.Shape();
    s.absarc(0, 0, rO, 0, Math.PI * 2, false);
    const h = new THREE.Path();
    h.absarc(0, 0, rI, 0, Math.PI * 2, true);
    s.holes.push(h);
    return s;
  };
  const webS = ring(rOuter, rInner);
  for (let i = 0; holeR > 1e-3 && i < lighteningHoles; i++) {
    const a = (i / lighteningHoles) * Math.PI * 2;
    const p = new THREE.Path();
    p.absarc(Math.cos(a) * rMid, Math.sin(a) * rMid, holeR, 0, Math.PI * 2, true);
    webS.holes.push(p);
  }
  const web = new THREE.ExtrudeGeometry(webS, {depth: webThickness, bevelEnabled: false, curveSegments: 40});
  web.translate(0, 0, -webThickness / 2);
  const rd = Math.max(0.5, thickness - bevel * 2);
  const rim = (rO, rI) => {
    const g = new THREE.ExtrudeGeometry(ring(rO, rI), {depth: rd, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 2, curveSegments: 40});
    g.translate(0, 0, -rd / 2);
    return g;
  };
  const geo = boxUVs(mergeGeometries([web, rim(rOuter, Math.max(rInner + 0.5, rOuter - flangeRim)), rim(Math.min(rOuter - 0.5, rInner + flangeRim), rInner)]), uvScale);
  const group = new THREE.Group();
  const body = new THREE.Mesh(geo, governMaterial(mat || M.alu, 'shell'));
  group.add(body);
  if (boltCount > 0) {
    const bg = bolt({r: Math.min(2.6, flangeRim * 0.65), h: 3.6}).rotateX(Math.PI / 2);
    const xs = [];
    for (let i = 0; i < boltCount; i++) {
      const a = ((i + 0.5) / boltCount) * Math.PI * 2;
      for (const sz of [-1, 1]) {
        const o = new THREE.Object3D();
        o.position.set(Math.cos(a) * rMid, Math.sin(a) * rMid, sz * (thickness / 2 + 0.6));
        if (sz < 0) o.rotation.y = Math.PI;
        xs.push(o);
      }
    }
    group.add(instanced(bg, boltMat || M.steel, xs));
  }
  return {group, body};
}

/**
 * One InstancedMesh from a list of transforms (Object3D, or {position, quaternion|rotation, scale}). Use it for the
 * tertiary layer (bolts, rivets, clips): thousands of them cost one draw call.
 */
export function instanced(geometry, material, transforms) {
  const im = new THREE.InstancedMesh(geometry, material, transforms.length);
  const o = new THREE.Object3D();
  transforms.forEach((t, i) => {
    if (t.isObject3D) t.updateMatrix(), im.setMatrixAt(i, t.matrix);
    else {
      o.position.copy(t.position ?? new THREE.Vector3());
      if (t.quaternion) o.quaternion.copy(t.quaternion);
      else o.rotation.copy(t.rotation ?? new THREE.Euler());
      o.scale.copy(t.scale ?? new THREE.Vector3(1, 1, 1));
      o.updateMatrix();
      im.setMatrixAt(i, o.matrix);
    }
  });
  im.instanceMatrix.needsUpdate = true;
  return im;
}

/**
 * Break a uniform array. Returns n values from base, each varied by ±spread (a fraction), seeded: rib spacings,
 * ring sizes, bolt counts. A row of identical parts at identical pitch reads as a for-loop; the eye wants the
 * rhythm of a real assembly (docs/form.md, gate 4).
 */
export function vary(rand, n, base, spread = 0.18) {
  return Array.from({length: n}, () => base * (1 + (rand() * 2 - 1) * spread));
}
