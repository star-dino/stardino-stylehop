// kit-compat: the teardown kit (three r186 ESM, src/kit/*.js) on stylehop's three r147 global build.
// Same names, same signatures, same return shapes. THREE comes only from the calibration-lab kernel.
// See NOTES.md "B · kit-compat" for which exports wrap the kernel and which are ported.
export {THREE} from '/styles/calibration-lab/kernel.js';

// glb.js
export {loadGLB, partsOf, applyMaterials, explodeRig} from './kit-compat/glb.js';

// look.js
export {boxUVs, createMaterials, governMaterial, studioEnvironment, createSurfaceMaps, PALETTE, InkPass, CallPass, installSilhouette} from './kit-compat/look.js';

// mech.js (cutWindow is the teardown implementation, line-for-line identical to the kernel's)
export {curveSleeve, cutWindow, lugRing, metalReport, radialFins, ridgeLine, ringStack, seamHardware, wearMaps, windowRim} from './kit-compat/mech.js';

// parts.js (parts.mergeGeometries is internal; the exported mergeGeometries is the three/addons-compatible one)
export {block, machinedPlate, counterboreBoss, ribbedLink, gear, helix, bolt, bellows, ballJoint, swept, updateSwept, creviceRing, flangedRing, instanced, vary} from './kit-compat/parts.js';
export {mergeGeometries} from './kit-compat/merge.js';

// lod.js
export {createLod, lerpMaterial, scaleIn, lodAt} from './kit-compat/lod.js';

// util.js
export * from './kit-compat/util.js';
