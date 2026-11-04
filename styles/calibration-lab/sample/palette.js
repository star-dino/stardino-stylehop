// The nautilus palette, in one place. Everything colour-like in nautilus.js, stage.js, console.js and live.js reads
// from `P`; nothing else in the nautilus carries a colour literal that belongs to a scheme.
//
// Pick a scheme: ?palette=A|B|C on the page URL, or `capture.mjs ... --palette B` (sets window.__PALETTE before the
// page loads). Default A.  Specs: docs/improvements.md, section 配色.
//
//   Layers (the same in every scheme):  shell ~60% · mechanism ~25% · accent (seams, joints) ~10% · glow ~5%.
//   Rule 1: the glow colour goes only on things that glow (eye, jets, lights), never on structure.
//   Rule 2: one warm metal. A keeps copper + brass (as built, the early cut.1-the final cut); B and C map brass and bronze onto the seam
//           metal so there is a single warm colour.
//
// Shape: shell (armour colour), seam (the accent metal and where it is drawn), mech (the mechanism's metals), glow,
// stage (backdrop, light, ink), ui (console panel tokens).

const shellA = {
  plain: ['#F7F6F2', '#F9F8F5', '#F3F1EC', '#ECE9E2'], // gradient stops at 0, .4, .8, 1
  ceramic: ['#F0EDE7', '#F4F2EC', '#ECE9E2', '#E4E1D9'],
  tentPlain: ['#F8F7F4', '#FAF9F7', '#F2F0EB'], // gradient stops at 0, .5, 1
  tentCeramic: ['#F0EDE7', '#F4F1EB', '#E9E6DF'],
  chamferDark: 'rgba(70, 64, 58, 0.42)', // the bevel turned away from the key
  chamferLight: 'rgba(255, 255, 255, 0.95)', // the bevel catching it
  facetLine: 'rgba(120, 125, 134, 0.14)',
  stencil: 'rgba(30, 34, 40, 0.85)',
  ghost: '#ECEAE4',
  // fine detail painted into the colour map (panel lines, hatches, screws, vents, rivets, wear hairlines)
  panelLine: 'rgba(96, 100, 108, 0.32)',
  panelHi: 'rgba(255, 255, 255, 0.85)',
  hatchLine: 'rgba(88, 92, 100, 0.55)',
  hatchHi: 'rgba(255, 255, 255, 0.9)',
  hatchDot: 'rgba(70, 74, 82, 0.7)',
  slot: 'rgba(60, 62, 68, 0.55)',
  rivet: 'rgba(92, 96, 104, 0.5)',
  cheekLine: 'rgba(115, 120, 128, 0.16)',
  wearInk: 'rgba(64,58,52,0.6)',
  tentWearInk: 'rgba(58,52,46,0.75)',
  // roughness / clearcoat stay in nautilus.js: they are the same for every scheme (the hard-not-soft rule)
};

const A = {
  name: 'A 深海档案',
  shell: shellA,
  seam: {
    chamfer: '#C27A44', // copper trim along plate edges (colour map)
    tentEdge: '#B86A34', // copper lines on the tentacle ribbons
    copper: '#D88E58',
    copperDark: '#A8653A',
    ribTint: '#E0A070', // instance tints on the dark rib / slit blocks
    slitTint: '#F2B27A',
    copperMetalness: 0.96,
  },
  mech: {
    alu: '#C9CED5', aluDark: '#59606A', titanium: '#A4ABB5', steel: '#D8DDE3', chrome: '#EEF2F6',
    structure: '#4A5059', liner: '#1C1F24', hose: '#262B33', darkGunmetal: '#434952', cavity: '#6A7078',
    brass: '#D2A85C', bronze: '#B8864E', white: '#F3F1EC', ceramic: '#ECE8E0',
  },
  glow: {
    accent: '#FF6A1F', stencilBar: '#F05822', eyeBase: '#3A2006', eyeEmissive: '#FF8A1E',
    eyeLight: '#FF6A22', hubLight: '#FF7A28', lens: '#0A0B0D',
  },
  stage: {
    bg: '#EFECE6', ground: '#ECE8E0', mark: '#D5CEC2', shadow: '#5D564C',
    surround: '#46494f', envFloor: '#8a867e', envIntensity: 0.8,
    sun: '#FFF8EE', sunIntensity: 2.7, fill: '#FAF8F3', rim: '#E2EAF5',
    hemiSky: '#FFFFFF', hemiGround: '#8E887E', ink: '#242830', shadowOpacity: 0.24,
    page: '#EFECE4',
  },
  ui: {
    ink: '#24211D', mute: '#7E766B', faint: '#D6CEC0', line: '#E2DBD0', panel: 'rgba(247,244,238,0.92)',
    or: '#D97224', brass: '#B88938', green: '#2E8B57', blue: '#386FA4',
    btn: '#FCFBF8', seg: '#F7F5F0', onBtn: '#fff', text1: '#5C554B', text2: '#6E675C', text3: '#5E574D', off: '#7E766B',
    well: '#E8E2D7', track: '#E5DFD3', trackSoft: '#E5DECFE0', knob: '#fff',
    chipBorder: '#DFD9CD', chipBg: 'rgba(251,249,244,.94)', chipInk: '#26231F', chipDot: '#DC6424', hint: '#8E877B',
    panelShadow: 'rgba(80,65,45,.06)',
  },
};

// B 白瓷黑钢: pure white shell, black steel mechanism, signal orange as the single warm colour, in the seams and
// joints only (keep it under ~5% of the frame, or it turns into a toy).
const B = {
  name: 'B 白瓷黑钢',
  shell: {
    ...shellA,
    plain: ['#FBFBFA', '#FDFDFC', '#F7F7F6', '#EFEFEE'],
    ceramic: ['#F6F6F5', '#F9F9F8', '#F1F1F0', '#E8E8E7'],
    tentPlain: ['#FBFBFA', '#FDFDFC', '#F5F5F4'],
    tentCeramic: ['#F6F6F5', '#F9F9F8', '#EDEDEC'],
    chamferDark: 'rgba(30, 32, 36, 0.5)',
    ghost: '#EEEEED',
    wearInk: 'rgba(40,42,46,0.6)',
    tentWearInk: 'rgba(36,38,42,0.75)',
  },
  seam: {
    chamfer: '#2A2E34', tentEdge: '#2A2E34', copper: '#FF6A1F', copperDark: '#B8430F', ribTint: '#FF8A4F', slitTint: '#FF9A64',
    copperMetalness: 0.7,
  },
  mech: {
    alu: '#4A5058', aluDark: '#23272D', titanium: '#3A3F46', steel: '#8E959E', chrome: '#C5CBD2',
    structure: '#1F2328', liner: '#121417', hose: '#16181C', darkGunmetal: '#191C20', cavity: '#3A3E44',
    brass: '#FF6A1F', bronze: '#B8430F', white: '#FBFBFA', ceramic: '#F6F6F5',
  },
  glow: {
    accent: '#FF6A1F', stencilBar: '#FF5A1F', eyeBase: '#3A1606', eyeEmissive: '#FF6A1F',
    eyeLight: '#FF6A22', hubLight: '#FF6A22', lens: '#08090A',
  },
  stage: {
    bg: '#E7E9EB', ground: '#E3E5E8', mark: '#C9CDD2', shadow: '#454A52',
    surround: '#3c4046', envFloor: '#80858c', envIntensity: 0.8,
    sun: '#FFFFFF', sunIntensity: 2.7, fill: '#F4F6F8', rim: '#E6EEF8',
    hemiSky: '#FFFFFF', hemiGround: '#868A90', ink: '#1C1F24', shadowOpacity: 0.26,
    page: '#E7E9EB',
  },
  ui: {
    ink: '#1D2024', mute: '#6F757D', faint: '#CCD0D5', line: '#DBDEE2', panel: 'rgba(244,246,248,0.92)',
    or: '#F05A1C', brass: '#F05A1C', green: '#2E8B57', blue: '#386FA4',
    btn: '#FAFBFC', seg: '#F4F6F8', onBtn: '#fff', text1: '#4F555C', text2: '#60666D', text3: '#51575E', off: '#6F757D',
    well: '#E1E4E8', track: '#DDE0E4', trackSoft: '#DDE0E4E0', knob: '#fff',
    chipBorder: '#D5D9DE', chipBg: 'rgba(250,251,252,.94)', chipInk: '#1D2024', chipDot: '#F05A1C', hint: '#868C94',
    panelShadow: 'rgba(40,50,60,.06)',
  },
};

// C 深海暗色: deep titanium-grey shell, bright steel mechanism, copper in the seams, cold cyan glow, dark backdrop.
const C = {
  name: 'C 深海暗色',
  shell: {
    plain: ['#5A636E', '#606A76', '#555E69', '#4B535D'],
    ceramic: ['#555E69', '#5C6671', '#505963', '#474F58'],
    tentPlain: ['#5C6671', '#626C78', '#565F6A'],
    tentCeramic: ['#555E69', '#5B6570', '#4F5862'],
    chamferDark: 'rgba(8, 12, 16, 0.55)',
    chamferLight: 'rgba(205, 225, 240, 0.7)',
    facetLine: 'rgba(160, 190, 210, 0.16)',
    stencil: 'rgba(210, 232, 245, 0.85)',
    ghost: '#5A636E',
    panelLine: 'rgba(8, 12, 16, 0.45)',
    panelHi: 'rgba(190, 215, 232, 0.35)',
    hatchLine: 'rgba(8, 12, 16, 0.6)',
    hatchHi: 'rgba(190, 215, 232, 0.4)',
    hatchDot: 'rgba(8, 12, 16, 0.7)',
    slot: 'rgba(6, 10, 14, 0.6)',
    rivet: 'rgba(8, 12, 16, 0.55)',
    cheekLine: 'rgba(8, 12, 16, 0.2)',
    wearInk: 'rgba(6,10,14,0.65)',
    tentWearInk: 'rgba(6,10,14,0.75)',
  },
  seam: {
    chamfer: '#C27A44', tentEdge: '#B86A34', copper: '#D88E58', copperDark: '#A8653A', ribTint: '#E0A070', slitTint: '#F2B27A',
    copperMetalness: 0.96,
  },
  mech: {
    alu: '#C9D1DA', aluDark: '#8C97A3', titanium: '#B6C0CB', steel: '#E1E7ED', chrome: '#F2F6FA',
    structure: '#7C8794', liner: '#0B0E12', hose: '#1A2028', darkGunmetal: '#6A7480', cavity: '#2C333B',
    brass: '#D88E58', bronze: '#A8653A', white: '#5E6772', ceramic: '#58616C',
  },
  glow: {
    accent: '#3FE0EC', stencilBar: '#3FE0EC', eyeBase: '#06242A', eyeEmissive: '#3FE0EC',
    eyeLight: '#38D8E8', hubLight: '#38D8E8', lens: '#030507',
  },
  stage: {
    bg: '#0B1218', ground: '#0E161D', mark: '#1D2A35', shadow: '#000000',
    surround: '#1c2229', envFloor: '#2a3138', envIntensity: 0.8,
    sun: '#EAF4FF', sunIntensity: 2.9, fill: '#C8D8EA', rim: '#7FB8E6',
    hemiSky: '#8FA6BD', hemiGround: '#10161C', ink: '#05080B', shadowOpacity: 0.4,
    page: '#0B1218',
  },
  ui: {
    ink: '#DCE6EE', mute: '#8696A4', faint: '#33414D', line: '#26323C', panel: 'rgba(16,24,31,0.88)',
    or: '#38C8D8', brass: '#D88E58', green: '#3FB87E', blue: '#5AA0D8',
    btn: '#141D25', seg: '#121A21', onBtn: '#06161A', text1: '#A9B8C5', text2: '#9AABB9', text3: '#A0B0BD', off: '#8696A4',
    well: '#1A252E', track: '#26323C', trackSoft: '#26323CE0', knob: '#DCE6EE',
    chipBorder: '#33414D', chipBg: 'rgba(16,24,31,.94)', chipInk: '#DCE6EE', chipDot: '#38C8D8', hint: '#6F7F8D',
    panelShadow: 'rgba(0,0,0,.3)',
  },
};

export const PALETTES = {A, B, C};

/** The scheme asked for: window.__PALETTE (capture --palette), else ?palette= in the URL, else A. */
export function paletteKey() {
  let k = null;
  try {
    k = (typeof window !== 'undefined' && window.__PALETTE) || new URLSearchParams(location.search).get('palette');
  } catch {}
  k = String(k || 'A').toUpperCase();
  return PALETTES[k] ? k : 'A';
}

export const PALETTE_KEY = paletteKey();
export const P = PALETTES[PALETTE_KEY];

/** Look variant (?look= on the page, `capture.mjs --look`, window.__LOOK).
 *  ''/'focus'/'the final cut' (default, the final cut): the final cut's 大疏大密 + detail by camera distance.
 *  'read'/'the final cut': the final cut's three-value read at hero distance (dark seams, copper only at core, eye, jets and joints,
 *  slimmer tentacles, less wear). 'the final cut': the previous default as built. */
export const LOOK = (() => {
  let k = '';
  try {
    k = (typeof window !== 'undefined' && window.__LOOK) || new URLSearchParams(location.search).get('look') || '';
  } catch {}
  k = String(k).toLowerCase();
  return (k || 'focus');
})();
// 'focus' (default): read + 大疏大密: clasps only on the seams at the window (the outer seams get theirs from
// the camera distance), darker wider outer seams, pure orange core, hero 10% closer.
export const FOCUS = LOOK === 'focus';
export const READ = LOOK === 'read' || FOCUS;
