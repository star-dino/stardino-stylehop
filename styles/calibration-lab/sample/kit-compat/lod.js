// Distance LOD: wraps the calibration-lab kernel primitives (same maths: smoothstep k, same setter protocol) and
// restores the teardown kit's optional-argument signatures (the kernel demands every parameter explicitly).
import {createLod as kCreateLod, lodAt as kLodAt, lodScaleIn, lodLerpMaterial} from '/styles/calibration-lab/kernel.js';

export const lodAt = kLodAt;
export const createLod = ({near, far}) => kCreateLod({near, far});
export const scaleIn = (meshes, {from = 0, to = 1} = {}) => lodScaleIn(meshes, {from, to});
export const lerpMaterial = (mat, spec = {}, objects = []) => lodLerpMaterial(mat, spec, objects);
