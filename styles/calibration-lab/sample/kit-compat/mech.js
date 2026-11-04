// Machine feel: the parts that make a sculpted body read as assembled hardware instead of a sculpture with lines
// painted on it. docs/form.md, step 5, says when each one is required; this file is how.
//
//   import {cutWindow, windowRim, ridgeLine, seamHardware, ringStack, radialFins, curveSleeve, wearMaps, metalReport}
//     from 'teardown-kit/mech.js';
//
// Nothing here is specific to one machine: no names, no palette, no model constants. Every colour comes in as a
// material, every size as an argument. What it encodes is the machine feel found in a build whose form was wrong but
// which read as hardware at first glance: every seam carried a sunk groove, a liner and clasps; a hub was seven
// lugged rings turning against each other; the cutaway showed rows of vanes at an exact pitch; the metals were
// metals. Units are the caller's (the defaults suit a model a few metres across).
import {THREE} from '/styles/calibration-lab/kernel.js';
import {swept} from './parts.js';

const V3 = THREE.Vector3;

// ------------------------------------------------------------------------------------------------ windows

/**
 * Cut a window out of a mesh. `keep(x, y, z)` is a signed function: the surface stays where it is ≥ 0. Triangles
 * that straddle the boundary are clipped exactly (position, normal and uv interpolated), so the edge is as clean as
 * the function, not as coarse as the mesh. Returns the clipped geometry and the boundary as polylines
 * ({points, normals}[]), ready for windowRim().
 *
 *   // open the camera side of the shell between the hub and r = 3.2
 *   const {geometry, edges} = cutWindow(plate.geometry, (x, y, z) => Math.max(Math.hypot(x - hx, y - hy) - 3.2, 0.2 - z));
 */
export function cutWindow(geometry, keep) {
  const src = geometry.index ? geometry.toNonIndexed() : geometry;
  if (!src.attributes.normal) src.computeVertexNormals();
  const P = src.attributes.position;
  const N = src.attributes.normal;
  const U = src.attributes.uv;
  const outP = [];
  const outN = [];
  const outU = [];
  const segs = [];
  const vert = (i) => ({
    p: new V3(P.getX(i), P.getY(i), P.getZ(i)),
    n: new V3(N.getX(i), N.getY(i), N.getZ(i)),
    u: U ? [U.getX(i), U.getY(i)] : null,
  });
  const lerp = (a, b, fa, fb) => {
    // always interpolate from the lexically smaller end, so both triangles sharing an edge get the same point
    const swap = a.p.x > b.p.x || (a.p.x === b.p.x && (a.p.y > b.p.y || (a.p.y === b.p.y && a.p.z > b.p.z)));
    if (swap) [a, b, fa, fb] = [b, a, fb, fa];
    const t = fa / (fa - fb);
    return {
      p: a.p.clone().lerp(b.p, t),
      n: a.n.clone().lerp(b.n, t).normalize(),
      u: a.u ? [a.u[0] + (b.u[0] - a.u[0]) * t, a.u[1] + (b.u[1] - a.u[1]) * t] : null,
    };
  };
  const emit = (v) => {
    outP.push(v.p.x, v.p.y, v.p.z);
    outN.push(v.n.x, v.n.y, v.n.z);
    if (v.u) outU.push(v.u[0], v.u[1]);
  };
  for (let i = 0; i < P.count; i += 3) {
    const vs = [vert(i), vert(i + 1), vert(i + 2)];
    const f = vs.map((v) => keep(v.p.x, v.p.y, v.p.z));
    if (f[0] >= 0 && f[1] >= 0 && f[2] >= 0) {
      vs.forEach(emit);
      continue;
    }
    if (f[0] < 0 && f[1] < 0 && f[2] < 0) continue;
    const poly = [];
    const cut = [];
    for (let k = 0; k < 3; k++) {
      const a = vs[k];
      const b = vs[(k + 1) % 3];
      const fa = f[k];
      const fb = f[(k + 1) % 3];
      if (fa >= 0) poly.push(a);
      if ((fa >= 0) !== (fb >= 0)) {
        const x = lerp(a, b, fa, fb);
        poly.push(x);
        cut.push(x);
      }
    }
    for (let k = 1; k + 1 < poly.length; k++) [poly[0], poly[k], poly[k + 1]].forEach(emit);
    if (cut.length === 2) segs.push(cut);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(outP, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(outN, 3));
  if (U) g.setAttribute('uv', new THREE.Float32BufferAttribute(outU, 2));
  return {geometry: g, edges: chain(segs)};
}

// join cut segments that share end points into polylines
function chain(segs) {
  const key = (v) => `${Math.round(v.p.x * 1e4)},${Math.round(v.p.y * 1e4)},${Math.round(v.p.z * 1e4)}`;
  const at = new Map();
  segs.forEach((s, i) => {
    for (const e of [0, 1]) {
      const k = key(s[e]);
      if (!at.has(k)) at.set(k, []);
      at.get(k).push([i, e]);
    }
  });
  const used = new Uint8Array(segs.length);
  const lines = [];
  const walk = (line, i, e) => {
    // extend `line` from the free end `e` of segment i
    for (;;) {
      const next = (at.get(key(segs[i][e])) || []).find(([j]) => !used[j]);
      if (!next) return;
      const [j, ej] = next;
      used[j] = 1;
      const far = segs[j][1 - ej];
      line.push(far);
      i = j;
      e = 1 - ej;
    }
  };
  for (let i = 0; i < segs.length; i++) {
    if (used[i]) continue;
    used[i] = 1;
    const fwd = [segs[i][0], segs[i][1]];
    walk(fwd, i, 1);
    const back = [];
    walk(back, i, 0);
    const pts = [...back.reverse(), ...fwd];
    if (pts.length >= 3) lines.push({points: pts.map((v) => v.p), normals: pts.map((v) => v.n)});
  }
  return lines;
}

/**
 * The rim of a window: a side wall sunk `depth` along -normal (the panel's thickness, so the opening reads as cut
 * through something solid) and a lip tube on the edge. One polyline from cutWindow().edges in, one Group out.
 */
export function windowRim(edge, {depth = 0.12, lip = 0.03, wallMat, lipMat, minLength = 0.25} = {}) {
  const grp = new THREE.Group();
  const {points, normals} = edge;
  let len = 0;
  for (let i = 1; i < points.length; i++) len += points[i].distanceTo(points[i - 1]);
  if (len < minLength) return grp;
  if (wallMat) {
    const pos = [];
    const nor = [];
    const idx = [];
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const n = normals[i];
      pos.push(p.x, p.y, p.z, p.x - n.x * depth, p.y - n.y * depth, p.z - n.z * depth);
      nor.push(0, 0, 0, 0, 0, 0);
      if (i) idx.push((i - 1) * 2, i * 2, (i - 1) * 2 + 1, i * 2, i * 2 + 1, (i - 1) * 2 + 1);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    const m = wallMat.side === THREE.DoubleSide ? wallMat : wallMat.clone();
    m.side = THREE.DoubleSide;
    grp.add(new THREE.Mesh(g, m));
  }
  if (lipMat && lip > 0) {
    const pts = resample(points, Math.max(8, Math.round(len / 0.06)));
    grp.add(new THREE.Mesh(swept({points: pts, radiusAt: lip, tubularSeg: pts.length * 2, radialSeg: 8}), lipMat));
  }
  return grp;
}

function resample(points, n) {
  const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
  return curve.getSpacedPoints(n);
}

// ------------------------------------------------------------------------------------------------ seams

/**
 * The visible ridge of a strip-shaped mesh (a seam groove, a rib, a rail): its vertices binned by `along(p)` and,
 * in each bin, the mean of those within `flat` of the one furthest toward `up`. Returns {points, normals} on the surface, in mesh space. `range`
 * ([lo, hi] in `along` units) keeps only part of it, e.g. the part of a seam outside a window.
 *
 *   // a radial seam on the camera side of a shell centred on (hx, hy)
 *   const ridge = ridgeLine(seam.geometry, {along: (p) => Math.hypot(p.x - hx, p.y - hy), up: new V3(0, 0, 1)});
 */
export function ridgeLine(geometry, {along, up = new V3(0, 0, 1), bins = 18, trim = 0.04, range = null, flat = 0.03} = {}) {
  const P = geometry.attributes.position;
  if (!geometry.attributes.normal) geometry.computeVertexNormals();
  const N = geometry.attributes.normal;
  let lo = Infinity;
  let hi = -Infinity;
  const p = new V3();
  const s = new Float32Array(P.count);
  for (let i = 0; i < P.count; i++) {
    p.fromBufferAttribute(P, i);
    s[i] = along(p);
    lo = Math.min(lo, s[i]);
    hi = Math.max(hi, s[i]);
  }
  const span = hi - lo;
  lo += span * trim;
  hi -= span * trim;
  if (range) {
    lo = Math.max(lo, range[0]);
    hi = Math.min(hi, range[1]);
  }
  // per bin: the top height, then the mean of every vertex within `flat` of it. On a rounded strip that is the
  // crest; on a flat-topped one (a groove under flattened plates) it is the middle of the flat, where a single
  // highest vertex would jump from edge to edge and turn the liner into a twisted rope
  const top = new Array(bins).fill(-Infinity);
  for (let i = 0; i < P.count; i++) {
    const b = Math.floor(((s[i] - lo) / (hi - lo)) * bins);
    if (b < 0 || b >= bins) continue;
    p.fromBufferAttribute(P, i);
    top[b] = Math.max(top[b], p.dot(up));
  }
  const sumP = Array.from({length: bins}, () => new V3());
  const sumN = Array.from({length: bins}, () => new V3());
  const cnt = new Array(bins).fill(0);
  const n = new V3();
  for (let i = 0; i < P.count; i++) {
    const b = Math.floor(((s[i] - lo) / (hi - lo)) * bins);
    if (b < 0 || b >= bins) continue;
    p.fromBufferAttribute(P, i);
    if (p.dot(up) < top[b] - flat) continue;
    n.fromBufferAttribute(N, i);
    sumP[b].add(p);
    sumN[b].add(n.dot(up) < 0 ? n.negate() : n);
    cnt[b]++;
  }
  const points = [];
  const normals = [];
  for (let b = 0; b < bins; b++) {
    if (!cnt[b]) continue;
    points.push(sumP[b].divideScalar(cnt[b]));
    normals.push(sumN[b].normalize());
  }
  return {points, normals};
}

/**
 * Hardware along a seam, so it reads as a joint and not a drawn line: a liner (tube sunk into the gap) and clasps
 * bridging the gap at a fixed pitch, alternating two materials. `points`/`normals` from ridgeLine() or your own
 * curve; `normals` point out of the surface. `surfaces` (meshes, e.g. the two plates either side) seats every clasp
 * on them: a ray each side of the gap, the clasp at the mean of the two hits, dropped when either side misses or the
 * hits disagree (the plate turns away there, or a window cut it). Without it a clasp sits on the groove's ridge,
 * which floats wherever the groove stands proud of the plates. `space` is the object the group will be added to
 * (its matrixWorld converts the hits); omit it when everything is at identity.
 */
export function seamHardware({points, normals, linerMat, linerR = 0.035, sink = 0.02, claspMat, claspAlt, pitch = 0.6, clasp = [0.07, 0.05, 0.2], skipEnds = 0.08, surfaces = null, space = null}) {
  const grp = new THREE.Group();
  if (points.length < 2) return grp;
  const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
  const nCurve = new THREE.CatmullRomCurve3(normals.map((n) => n.clone()), false, 'centripetal');
  const len = curve.getLength();
  if (linerMat) {
    const pts = curve.getSpacedPoints(Math.max(8, Math.round(len / 0.08))).map((q, i, arr) => {
      const n = nCurve.getPoint(i / (arr.length - 1)).normalize();
      return q.clone().addScaledVector(n, -sink);
    });
    grp.add(new THREE.Mesh(swept({points: pts, radiusAt: linerR, tubularSeg: pts.length * 2, radialSeg: 8}), linerMat));
  }
  if (claspMat) {
    const count = Math.max(1, Math.floor((len * (1 - 2 * skipEnds)) / pitch));
    const box = new THREE.BoxGeometry(...clasp);
    const T = new V3();
    const B = new V3();
    const m = new THREE.Matrix4();
    const ray = surfaces ? new THREE.Raycaster() : null;
    const inv = space ? new THREE.Matrix4().copy(space.matrixWorld).invert() : null;
    const toWorld = (v) => (space ? v.clone().applyMatrix4(space.matrixWorld) : v.clone());
    const seat = (q, n) => {
      const hits = [];
      for (const side of [-1, 1]) {
        const o = q.clone().addScaledVector(B, side * clasp[2] * 0.42).addScaledVector(n, 0.6);
        const ow = toWorld(o);
        const dw = toWorld(o.clone().sub(n)).sub(ow).normalize();
        ray.set(ow, dw);
        ray.far = 1.2;
        const h = ray.intersectObjects(surfaces, false)[0];
        if (!h || !h.face) return null;
        hits.push(inv ? h.point.clone().applyMatrix4(inv) : h.point.clone());
        // the face normal, into the group's space: clasps lie on the plates, not on the groove's ridge
        const fn = h.face.normal.clone().transformDirection(h.object.matrixWorld);
        if (inv) fn.transformDirection(inv);
        if (fn.dot(n) < 0) fn.negate();
        seatN.add(fn);
      }
      if (hits[0].distanceTo(hits[1]) > clasp[2] * 1.6) return null;
      const mid = hits[0].add(hits[1]).multiplyScalar(0.5);
      return mid.distanceTo(q) < 0.35 ? mid : null;
    };
    const seatN = new V3();
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
        T.addScaledVector(n, -T.dot(n)).normalize(); // keep x along the seam, in the plate's plane
        B.crossVectors(T, n).normalize();
      }
      const mesh = new THREE.Mesh(box, k % 3 === 2 && claspAlt ? claspAlt : claspMat);
      // x along the seam, y out of the surface, z across the gap
      m.makeBasis(T, n, B);
      mesh.quaternion.setFromRotationMatrix(m);
      mesh.position.copy(q).addScaledVector(n, clasp[1] * 0.2);
      grp.add(mesh);
    }
  }
  return grp;
}

// ------------------------------------------------------------------------------------------------ rhythm

/** A flat ring with `lugs` rounded teeth on the outside: the hub / rotor / race look. Axis is +z. */
export function lugRing({rOuter, rInner, thick, lugs = 24, lugDepth = 0.25, bevel = 0.014}) {
  const sh = new THREE.Shape();
  const seg = Math.max(96, lugs * 10);
  for (let i = 0; i <= seg; i++) {
    const a = (i / seg) * Math.PI * 2;
    const r = rOuter + Math.pow(Math.max(0, Math.cos(a * lugs)), 6) * (rOuter - rInner) * lugDepth;
    if (i === 0) sh.moveTo(Math.cos(a) * r, Math.sin(a) * r);
    else sh.lineTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  const hole = new THREE.Path();
  hole.absarc(0, 0, rInner, 0, Math.PI * 2, true);
  sh.holes.push(hole);
  const g = new THREE.ExtrudeGeometry(sh, {
    depth: thick,
    bevelEnabled: bevel > 0,
    bevelThickness: Math.min(bevel, thick * 0.2),
    bevelSize: bevel,
    bevelSegments: 1,
    curveSegments: 48,
  });
  g.translate(0, 0, -thick / 2);
  return g;
}

/**
 * Concentric lugged rings stepping down into a well, counter-rotating: the precise repetition that reads as
 * machine at any distance. rings: [{rOut, rIn, z, thick, lugs, mat, spin, race}] (z > 0 faces the camera; with
 * `mirror` every ring is repeated at -z turning the other way). update(t, open) turns them and, with open 0..1,
 * lifts each ring out of the well by `spread * (index + 1)`.
 */
export function ringStack({rings, mirror = true, spread = 0.18}) {
  const group = new THREE.Group();
  const live = [];
  rings.forEach((rc, i) => {
    for (const sz of mirror ? [1, -1] : [1]) {
      const mesh = new THREE.Mesh(lugRing({rOuter: rc.rOut, rInner: rc.rIn, thick: rc.thick, lugs: rc.lugs}), rc.mat);
      mesh.position.z = sz * rc.z;
      group.add(mesh);
      live.push({mesh, spin: (rc.spin ?? 0.3) * sz, z: sz * rc.z, lift: sz * spread * (i + 1)});
      if (rc.race) {
        const race = new THREE.Mesh(new THREE.TorusGeometry((rc.rOut + rc.rIn) * 0.5, Math.min(0.03, (rc.rOut - rc.rIn) * 0.12), 8, 64), rc.race);
        race.position.z = sz * (rc.z + rc.thick * 0.5);
        group.add(race);
        live.push({mesh: race, spin: 0, z: race.position.z, lift: sz * spread * (i + 1)});
      }
    }
  });
  return {
    group,
    update(t, open = 0) {
      for (const r of live) {
        r.mesh.rotation.z = r.spin * t;
        r.mesh.position.z = r.z + r.lift * open;
      }
    },
  };
}

/**
 * Vanes at an exact angular pitch between radii r0 and r1, around +z through the origin: every `major`-th one full
 * length and thicker, the rest shorter. The exact pitch is the point: identical small parts in a row are what
 * machined hardware looks like. (The "no more than five identical parts at one pitch" rule in docs/form.md is for
 * big parts, not this.) Returns a Group of two InstancedMeshes.
 */
export function radialFins({r0, r1, a0, a1, pitch, depth = 0.4, thick = 0.035, z = 0, mat, minorMat, major = 3, minorLength = 0.62}) {
  const grp = new THREE.Group();
  const n = Math.floor((a1 - a0) / pitch) + 1;
  const len = r1 - r0;
  const mk = (l, t) => {
    const g = new THREE.BoxGeometry(l, t, depth, 1, 1, 1);
    g.translate(l / 2, 0, 0);
    return g;
  };
  const big = [];
  const small = [];
  for (let i = 0; i < n; i++) {
    const a = a0 + i * pitch;
    const o = new THREE.Object3D();
    const isMajor = i % major === 0;
    const start = isMajor ? r0 : r0 + len * (1 - minorLength);
    o.position.set(Math.cos(a) * start, Math.sin(a) * start, z);
    o.rotation.z = a;
    o.updateMatrix();
    (isMajor ? big : small).push(o.matrix.clone());
  }
  const inst = (geo, material, list) => {
    const m = new THREE.InstancedMesh(geo, material, list.length);
    list.forEach((mx, i) => m.setMatrixAt(i, mx));
    m.instanceMatrix.needsUpdate = true;
    if (m.computeBoundingSphere) m.computeBoundingSphere(); else m.frustumCulled = false; // r147: no InstancedMesh bounds
    return m;
  };
  if (big.length) grp.add(inst(mk(len, thick * 1.6), mat, big));
  if (small.length) grp.add(inst(mk(len * minorLength, thick), minorMat || mat, small));
  return grp;
}

// ------------------------------------------------------------------------------------------------ surface

const hash1 = (n) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453123;
  return x - Math.floor(x);
};

/**
 * An armour sleeve that bends with the limb it sits on: a tube over [u0, u1] of a curve, rebuilt from the curve each
 * update. Straight instanced sleeves kink where a limb curls; this does not. Elliptic section (rx along the
 * frame's "up", rz across it) for ribbon-like limbs. `profile` is [[t, scale], ...] with t in [0, 1] along the
 * sleeve: rings sit at those t, so put two close together for a lip. Geometry group 1 is the first ring segment (the
 * lip, give it the seam material), group 0 the rest. uv: x along the sleeve 0..1, y around 0..1 starting at "up"
 * (0 and 0.5 are the two edges of a ribbon, 0.25 and 0.75 its faces). Frame: "up" = tangent x `axis`, so pass the
 * axis the limb mostly bends around (world z for a limb seen side-on). `arc: [a0, a1]` (radians, 0 = up, pi/2 = across
 * toward +tangent x up) makes an open shell instead of a closed tube: a slit where the limb shows its inside.
 *
 *   const sl = curveSleeve({profile: [[0, 1.09], [0.04, 1.09], [0.07, 1], [1, 0.93]]});
 *   const mesh = new THREE.Mesh(sl.geometry, [ceramic, copper]);
 *   sl.update(curve, 0.30, 0.36, (u) => radius(u), {rx: 1.12, rz: 0.62, offset});   // every frame the curve moves
 */
export function curveSleeve({radial = 16, profile, axis = new V3(0, 0, 1), arc = null}) {
  const rings = profile.length;
  const stride = radial + 1;
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(rings * stride * 3);
  const uv = new Float32Array(rings * stride * 2);
  for (let i = 0; i < rings; i++)
    for (let j = 0; j <= radial; j++) {
      uv[(i * stride + j) * 2] = profile[i][0];
      uv[(i * stride + j) * 2 + 1] = j / radial;
    }
  const idx = [];
  for (let i = 0; i < rings - 1; i++)
    for (let j = 0; j < radial; j++) {
      const a = i * stride + j;
      const b = a + stride;
      idx.push(a, a + 1, b, b, a + 1, b + 1); // (Z x T) = +up at angle 0: outward
    }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.addGroup(radial * 6, (rings - 2) * radial * 6, 0);
  g.addGroup(0, radial * 6, 1);
  const P = new V3();
  const T = new V3();
  const Y = new V3();
  const Z = new V3();
  const [a0, a1] = arc ?? [0, Math.PI * 2];
  const cs = Array.from({length: stride}, (_, j) => {
    const a = a0 + (j / radial) * (a1 - a0);
    return [Math.cos(a), Math.sin(a)];
  });
  if (arc)
    for (let i = 0; i < rings; i++)
      for (let j = 0; j <= radial; j++) uv[(i * stride + j) * 2 + 1] = (a0 + (j / radial) * (a1 - a0)) / (Math.PI * 2);
  function update(curve, u0, u1, rFn, {rx = 1, rz = 1, offset = null} = {}) {
    for (let i = 0; i < rings; i++) {
      const [t, k] = profile[i];
      const u = Math.min(1, Math.max(0, u0 + (u1 - u0) * t));
      curve.getPointAt(u, P);
      curve.getTangentAt(u, T).normalize();
      Y.crossVectors(T, axis);
      if (Y.lengthSq() < 1e-8) Y.set(0, 1, 0);
      Y.normalize();
      Z.crossVectors(T, Y);
      if (offset) P.add(offset);
      const r = rFn(u) * k;
      for (let j = 0; j <= radial; j++) {
        const o = (i * stride + j) * 3;
        const [c, sn] = cs[j];
        pos[o] = P.x + (Y.x * c * rx + Z.x * sn * rz) * r;
        pos[o + 1] = P.y + (Y.y * c * rx + Z.y * sn * rz) * r;
        pos[o + 2] = P.z + (Y.z * c * rx + Z.z * sn * rz) * r;
      }
    }
    g.attributes.position.needsUpdate = true;
    g.computeVertexNormals();
    g.computeBoundingSphere();
  }
  return {geometry: g, update};
}

/**
 * Wear on a panel, as bump + roughness maps (u across the panel, v along it; panel edges at u = 0 and 1). Every
 * knob is 0..1 and scales count and contrast: 1 is heavy (a cracked, chipped, riveted panel). Set them from the
 * reference, not from taste: count the cracks and chips you can see on one panel there. Grey 128 = flat.
 * Relief alone vanishes at viewing distance, so it also returns `overlay`: a transparent canvas with the same
 * cracks, chips and panel lines as dark hairlines, to draw over the panel's colour map. `lineScale` thickens every
 * line for panels seen from far away (2-3 for a body several metres long in a 1080p frame).
 */
export function wearMaps({size = 1024, seed = 1, grain = 0.5, edges = 0.5, chips = 0.4, panels = 0.5, cracks = 0.3, rivets = 0.6, lineScale = 1, ink = 'rgba(64,58,52,0.6)'} = {}) {
  const W = size;
  const mk = () => {
    const c = document.createElement('canvas');
    c.width = c.height = W;
    return c;
  };
  const bc = mk();
  const rc = mk();
  const oc = mk();
  const b = bc.getContext('2d');
  const r = rc.getContext('2d');
  const o = oc.getContext('2d');
  o.strokeStyle = ink;
  o.fillStyle = ink;
  b.fillStyle = 'rgb(140,140,140)';
  b.fillRect(0, 0, W, W);
  r.fillStyle = 'rgb(150,150,150)';
  r.fillRect(0, 0, W, W);
  const h = (i) => hash1(i * 1.37 + seed * 91.7);
  const s = W / 1024;
  for (let i = 0; i < Math.round(4200 * grain); i++) {
    const pit = i % 3 === 0;
    const a = 0.08 + 0.16 * grain;
    b.fillStyle = pit ? `rgba(60,60,60,${a})` : `rgba(215,215,215,${a * 0.7})`;
    r.fillStyle = pit ? `rgba(225,225,225,${a})` : `rgba(115,115,115,${a * 0.7})`;
    const x = h(i * 3.1) * W;
    const y = h(i * 5.3 + 7) * W;
    const w = (2 + h(i * 7.7) * 14) * s;
    const hh = (1 + h(i * 9.1) * 8) * s;
    b.fillRect(x, y, w, hh);
    r.fillRect(x, y, w, hh);
  }
  if (edges > 0) {
    const ew = 44 * s * (0.5 + edges * 0.5);
    for (const [x0, x1, flip] of [[0, ew, false], [W - ew, W, true]]) {
      const gr = b.createLinearGradient(x0, 0, x1, 0);
      const dark = `rgb(${Math.round(140 - 105 * edges)},${Math.round(140 - 105 * edges)},${Math.round(140 - 105 * edges)})`;
      const stops = [[0, dark], [0.55, 'rgb(110,110,110)'], [0.8, 'rgb(185,185,185)'], [1, 'rgba(140,140,140,0)']];
      for (const [t, c] of stops) gr.addColorStop(flip ? 1 - t : t, c);
      b.fillStyle = gr;
      b.fillRect(x0, 0, x1 - x0, W);
    }
  }
  b.fillStyle = 'rgb(28,28,28)';
  r.fillStyle = 'rgb(235,235,235)';
  for (let i = 0; i < Math.round(140 * chips); i++) {
    const y = h(i * 7.13 + 3) * W;
    const cw = (8 + h(i * 11.3) * 28) * s;
    const ch = (4 + h(i * 17.9) * 18) * s;
    const x = i % 2 ? W - cw : 0;
    b.fillRect(x, y, cw, ch);
    r.fillRect(x, y, cw, ch);
    o.fillRect(x, y, cw * 0.7, ch * 0.7);
  }
  const rows = Math.round(7 * panels);
  for (let k = 0; k < rows; k++) {
    const v = ((k + 1) / (rows + 1)) * W;
    b.strokeStyle = 'rgb(24,24,24)';
    b.lineWidth = 4.5 * s;
    b.beginPath();
    b.moveTo(0, v);
    b.lineTo(W, v);
    b.stroke();
    b.strokeStyle = 'rgb(230,230,230)';
    b.lineWidth = 2.5 * s;
    b.beginPath();
    b.moveTo(0, v + 4 * s);
    b.lineTo(W, v + 4 * s);
    b.stroke();
    r.strokeStyle = 'rgb(235,235,235)';
    r.lineWidth = 6 * s;
    r.beginPath();
    r.moveTo(0, v);
    r.lineTo(W, v);
    r.stroke();
    o.lineWidth = 2.2 * s * lineScale;
    o.beginPath();
    o.moveTo(0, v);
    o.lineTo(W, v);
    o.stroke();
  }
  for (let c = 0; c < Math.round(56 * cracks); c++) {
    let x = h(c * 19.7 + 3.1) * W;
    let y = h(c * 31.3 + 9.7) * W;
    let ang = (h(c * 43.1) - 0.5) * Math.PI * 1.6;
    b.strokeStyle = 'rgba(20,20,20,0.88)';
    b.lineWidth = (1.6 + (c % 3) * 0.7) * s;
    r.strokeStyle = 'rgba(235,235,235,0.85)';
    r.lineWidth = 2.4 * s;
    o.lineWidth = (1.2 + (c % 3) * 0.5) * s * lineScale;
    b.beginPath();
    r.beginPath();
    o.beginPath();
    b.moveTo(x, y);
    r.moveTo(x, y);
    o.moveTo(x, y);
    for (let k = 0, n = 6 + (c % 7); k < n; k++) {
      ang += (h(c * 100 + k * 17.3) - 0.5) * 1.15;
      const l = (12 + h(c * 50 + k * 9.1) * 26) * s * Math.sqrt(lineScale);
      x += Math.cos(ang) * l;
      y += Math.sin(ang) * l;
      b.lineTo(x, y);
      r.lineTo(x, y);
      o.lineTo(x, y);
    }
    b.stroke();
    r.stroke();
    o.stroke();
  }
  if (rivets > 0) {
    const step = 36 / rivets;
    b.fillStyle = 'rgb(22,22,22)';
    r.fillStyle = 'rgb(230,230,230)';
    for (let y = 28 * s; y < W - 20 * s; y += step * s) {
      for (const x of [36 * s, W - 36 * s]) {
        b.beginPath();
        b.arc(x, y, 5.2 * s, 0, Math.PI * 2);
        b.fill();
        r.beginPath();
        r.arc(x, y, 6 * s, 0, Math.PI * 2);
        r.fill();
        o.beginPath();
        o.arc(x, y, 3.2 * s * lineScale, 0, Math.PI * 2);
        o.fill();
      }
    }
  }
  const tex = (c) => {
    const t = new THREE.CanvasTexture(c);
    t.anisotropy = 4;
    return t;
  };
  return {bumpMap: tex(bc), roughnessMap: tex(rc), overlay: oc};
}

// ------------------------------------------------------------------------------------------------ audit

/**
 * How much of the model is actually metal. Counts triangles of visible meshes by metalness band and prints it, so
 * "dark parts painted like plastic" shows as a number. A machine reads as one when the parts that should be metal
 * (structure, gears, rings, links, fittings) sit at metalness ≥ 0.8; dark plastic-looking structure comes from 0.1-0.4.
 */
export function metalReport(root, {log = true} = {}) {
  const bands = {metal: 0, mid: 0, dielectric: 0};
  const byMat = new Map();
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!o.isMesh || !o.visible || !o.material) return;
    const g = o.geometry;
    const tris = ((g.index ? g.index.count : g.attributes.position.count) / 3) * (o.isInstancedMesh ? o.count : 1);
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (m.metalness === undefined || m.transparent) continue;
      const band = m.metalness >= 0.8 ? 'metal' : m.metalness >= 0.4 ? 'mid' : 'dielectric';
      bands[band] += tris;
      const k = `${m.name || m.uuid.slice(0, 6)} #${m.color?.getHexString()} m${m.metalness.toFixed(2)}`;
      byMat.set(k, (byMat.get(k) || 0) + tris);
    }
  });
  const total = bands.metal + bands.mid + bands.dielectric || 1;
  const pct = (v) => Math.round((v / total) * 100);
  const res = {metal: pct(bands.metal), mid: pct(bands.mid), dielectric: pct(bands.dielectric), byMat};
  if (log) console.log(`metalReport: metal ≥0.8 ${res.metal}%  mid ${res.mid}%  dielectric <0.4 ${res.dielectric}% (by triangles)`);
  return res;
}
