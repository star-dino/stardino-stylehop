// BufferGeometryUtils.mergeGeometries (three r186) for the r147 global build, which ships no BufferGeometryUtils.
// Semantics as upstream: every geometry must have the same attribute set and the same indexed-ness (else null +
// console.error); useGroups adds one group per input geometry; morph attributes are not supported (never used).
import {THREE} from '/styles/calibration-lab/kernel.js';

export function mergeGeometries(geometries, useGroups = false) {
  if (!geometries.length) return null;
  const isIndexed = geometries[0].index !== null;
  const names = new Set(Object.keys(geometries[0].attributes));
  const attributes = {};
  const merged = new THREE.BufferGeometry();
  let offset = 0;
  geometries.forEach((g, i) => {
    if (isIndexed !== (g.index !== null)) {
      console.error('mergeGeometries: all geometries must be indexed or all non-indexed (geometry ' + i + ')');
      return;
    }
    const keys = Object.keys(g.attributes);
    if (keys.length !== names.size || !keys.every((k) => names.has(k))) {
      console.error('mergeGeometries: attribute set differs at geometry ' + i + ': ' + keys.join(',') + ' vs ' + [...names].join(','));
    }
    for (const k of keys) (attributes[k] ||= []).push(g.attributes[k]);
  });
  if (geometries.some((g, i) => (g.index !== null) !== isIndexed)) return null;
  for (const k of names) if (!attributes[k] || attributes[k].length !== geometries.length) return null;
  if (isIndexed) {
    let indexOffset = 0;
    const idx = [];
    geometries.forEach((g, i) => {
      const ia = g.index;
      if (useGroups) merged.addGroup(offset, ia.count, i);
      for (let j = 0; j < ia.count; j++) idx.push(ia.getX(j) + indexOffset);
      indexOffset += g.attributes.position.count;
      offset += ia.count;
    });
    merged.setIndex(idx);
  } else if (useGroups) {
    geometries.forEach((g, i) => {
      const c = g.attributes.position.count;
      merged.addGroup(offset, c, i);
      offset += c;
    });
  }
  for (const k of names) {
    const list = attributes[k];
    const first = list[0];
    const Arr = first.array.constructor;
    const size = first.itemSize;
    let n = 0;
    for (const a of list) {
      if (a.itemSize !== size || a.array.constructor !== Arr) return null;
      n += a.count * size;
    }
    const arr = new Arr(n);
    let o = 0;
    for (const a of list) {
      if (a.isInterleavedBufferAttribute) {
        for (let j = 0; j < a.count; j++) for (let c = 0; c < size; c++) arr[o++] = a['get' + 'XYZW'[c]](j);
      } else {
        arr.set(a.array, o);
        o += a.array.length;
      }
    }
    merged.setAttribute(k, new THREE.BufferAttribute(arr, size, first.normalized));
  }
  return merged;
}
