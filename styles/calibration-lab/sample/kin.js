// Kinematics, hydrostatics, logarithmic spiral geometry, and tentacle wave solver for the
// Mechanical Nautilus (Archive / 007). Real dimensions in metres, MPa, kN, and knots.
// One input (seq, tau) drives every part pose and every console readout. No three.js in here.

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const smooth = (x) => {
  const u = clamp(x, 0, 1);
  return u * u * (3 - 2 * u);
};
const ss = (a, b, t) => smooth((t - a) / Math.max(1e-6, b - a));

export const G = {
  length: 18.5,          // m overall length (tentacle tip to thruster nozzle)
  diameter: 12.0,        // m spiral shell structural diameter
  hullHeight: 8.6,       // m vertical span in hero frame
  hullWidth: 5.75,       // m maximum beam across umbilicus cheeks
  mass: 420,             // t displacement
  maxDepth: 6000,        // m rated hadal depth
  cruiseDepth: 600,      // m bathyal archive station depth (6.0 MPa on reference sheet)
  spiralB: 0.1763,       // Nautilus logarithmic spiral constant r = r0 * exp(b * theta)
  hubX: -9.25 + 18.5 * 0.735, // +4.3475 m umbilicus X center
  hubY: -4.30 + 8.60 * 0.485, // -0.1290 m umbilicus Y center
  eyeX: -9.25 + 18.5 * 0.538, // +0.7030 m optical sensor X center
  eyeY: -4.30 + 8.60 * 0.492, // -0.0688 m optical sensor Y center
  eyeZ: 1.68,            // m lateral offset of left/right optical sensors
  chamberCount: 9,       // 9 internal spiral septum chambers
  tentacleCount: 15,     // 15 plated tentacles, crossing and curling (traced off the reference)
  thrusterCount: 4,      // 4 omnidirectional aft water-jet drives
  maxThrust: 184,        // kN combined peak hydro-jet thrust
  maxJetVel: 18.4,       // m/s nozzle exhaust velocity
};

export const uToX = (u) => -9.95 + 19.20 * u;
export const vToY = (v) => -4.30 + 8.6 * v;

// 9 internal septum chambers arranged along the logarithmic spiral cavity
// Non-uniform angular spacing (varied rhythm, never a uniform for-loop)
export const SEPTA_ANGLES = [
  142, 124, 103, 79, 52, 22, -11, -46, -84,
].map((deg) => (deg * Math.PI) / 180);

// 15 tentacles traced off the reference (refs/nautilus.png) in its crop's (u, v), read off a 0.025 grid. What makes
// the reference read as a mane and not a rake is crossing: one thick arm leaves the lowest root and climbs across
// the bundle to a hooked tip at the far upper left (6), two arms leave the upper roots and dive across it to the
// lower left (5, 14), the top arm arches and falls back down through the others (1), and the tips curl into hooks
// and loops (6, 7, 11). Depth runs along each arm (z0 at the root -> z1 at the tip) so crossing arms pass in front
// of or behind each other instead of through. r: base radius (m), measured at the root.
const T = (id, role, r, z0, z1, freq, phase, uv) => ({
  id, role, rBase: r, rTip: r * 0.25, zOff: z0, freq, phase,
  // the traced root is where the arm leaves the bundle; one more point carries it 0.055 u back into the head and toward
  // the midline (z0 * 0.3), so the end cap of a front arm hides behind the eye and cheek instead of floating in front
  pts: [
    [uv[0][0] + 0.055, uv[0][1] + (uv[0][1] - uv[1][1]) * 0.5, z0 * 0.3], // root, pulled toward the midline: inside the head
    ...uv.map(([u, v], i) => [u, v, z0 + ((z1 - z0) * i) / Math.max(1, uv.length - 1)]),
  ],
});
export const TENTACLE_DEFS = [
  // 1: top arch, rises over the hood line, falls back through the upper arms, tip hooks right
  T(1, 'mid', 0.16, 0.05, -0.35, 2.1, 0.0, [[0.470, 0.575], [0.420, 0.605], [0.360, 0.640], [0.300, 0.650], [0.250, 0.642],
    [0.215, 0.615], [0.185, 0.570], [0.165, 0.510], [0.145, 0.465], [0.130, 0.410], [0.124, 0.350], [0.128, 0.300], [0.140, 0.272]]),
  // 2: upper wave, crest at u 0.21
  T(2, 'mid', 0.24, -0.45, -0.25, 2.3, 0.7, [[0.470, 0.550], [0.420, 0.555], [0.370, 0.550], [0.320, 0.535], [0.280, 0.525],
    [0.245, 0.515], [0.210, 0.522], [0.175, 0.515], [0.152, 0.492], [0.140, 0.452]]),
  // 3: second upper wave
  T(3, 'mid', 0.28, 0.55, 0.35, 1.9, 1.2, [[0.480, 0.510], [0.430, 0.490], [0.370, 0.470], [0.310, 0.460], [0.270, 0.475],
    [0.235, 0.488], [0.200, 0.470], [0.172, 0.440], [0.152, 0.410]]),
  // 4: thin feeler, hangs down at u 0.23
  T(4, 'short', 0.15, -0.85, -0.7, 2.6, 2.1, [[0.460, 0.530], [0.400, 0.530], [0.330, 0.535], [0.280, 0.528], [0.250, 0.510],
    [0.235, 0.470], [0.226, 0.420]]),
  // 5: front diver, upper root down across the bundle to the lower left
  T(5, 'reach', 0.40, 1.35, 0.55, 1.5, 0.5, [[0.500, 0.450], [0.460, 0.420], [0.410, 0.355], [0.360, 0.290], [0.310, 0.235],
    [0.260, 0.190], [0.210, 0.165], [0.160, 0.150], [0.110, 0.140], [0.068, 0.130]]),
  // 6: the climber, lowest root up across everything to the hooked tip at the far upper left (dark-core arm)
  T(6, 'reach', 0.40, 1.75, 1.05, 1.45, 3.3, [[0.530, 0.240], [0.480, 0.215], [0.430, 0.205], [0.380, 0.205], [0.330, 0.220],
    [0.285, 0.255], [0.240, 0.295], [0.195, 0.340], [0.150, 0.385], [0.100, 0.405], [0.065, 0.395], [0.040, 0.365],
    [0.025, 0.325], [0.028, 0.295]]),
  // 7: loop tip at u 0.05
  T(7, 'reach', 0.30, -0.6, -0.4, 1.7, 0.9, [[0.490, 0.400], [0.440, 0.370], [0.380, 0.345], [0.320, 0.330], [0.260, 0.320],
    [0.200, 0.315], [0.150, 0.335], [0.100, 0.345], [0.065, 0.330], [0.050, 0.290], [0.058, 0.255], [0.085, 0.235], [0.115, 0.240]]),
  // 8: mid arm, rises then turns down
  T(8, 'mid', 0.30, 0.3, 0.15, 1.8, 4.2, [[0.490, 0.360], [0.440, 0.340], [0.380, 0.360], [0.320, 0.390], [0.260, 0.400],
    [0.210, 0.395], [0.170, 0.370], [0.140, 0.330], [0.130, 0.290]]),
  // 9: thick mid-lower
  T(9, 'reach', 0.34, 0.95, 0.75, 1.6, 4.9, [[0.510, 0.300], [0.450, 0.270], [0.390, 0.260], [0.330, 0.275], [0.270, 0.270],
    [0.220, 0.245], [0.180, 0.220], [0.140, 0.200], [0.100, 0.195], [0.070, 0.205]]),
  // 10: lower long arm to the bottom-left tip
  T(10, 'reach', 0.32, 0.4, 0.3, 1.6, 2.6, [[0.520, 0.200], [0.470, 0.160], [0.420, 0.130], [0.360, 0.110], [0.300, 0.115],
    [0.240, 0.115], [0.190, 0.100], [0.140, 0.085], [0.090, 0.080], [0.050, 0.065], [0.022, 0.040]]),
  // 11: bottom arm, tip loops back
  T(11, 'reach', 0.28, -0.7, -0.5, 1.75, 5.5, [[0.520, 0.170], [0.470, 0.125], [0.420, 0.095], [0.360, 0.075], [0.290, 0.060],
    [0.220, 0.050], [0.160, 0.045], [0.110, 0.045], [0.072, 0.045], [0.050, 0.062], [0.060, 0.090], [0.092, 0.100]]),
  // 12: lower wave, dips then rises across 9 and 10
  T(12, 'mid', 0.26, -1.1, -0.9, 1.9, 1.7, [[0.510, 0.260], [0.460, 0.220], [0.400, 0.170], [0.340, 0.155], [0.280, 0.170],
    [0.230, 0.200], [0.190, 0.225], [0.150, 0.235], [0.120, 0.220]]),
  // 13: short bottom sweep
  T(13, 'short', 0.26, 1.0, 0.9, 2.0, 3.8, [[0.535, 0.160], [0.500, 0.115], [0.460, 0.085], [0.410, 0.065], [0.360, 0.058],
    [0.320, 0.062]]),
  // 14: back diver, thin, upper root down to the lower left behind the bundle
  T(14, 'reach', 0.18, -1.45, -1.2, 2.2, 0.3, [[0.470, 0.500], [0.420, 0.460], [0.370, 0.400], [0.320, 0.330], [0.270, 0.270],
    [0.220, 0.220], [0.170, 0.180], [0.120, 0.150], [0.080, 0.140], [0.050, 0.150], [0.035, 0.170]]),
  // 15: short upper filler
  T(15, 'short', 0.22, -0.2, -0.15, 2.4, 2.9, [[0.480, 0.470], [0.440, 0.455], [0.400, 0.440], [0.360, 0.430], [0.330, 0.420]]),
];

// resting sway amplitude (m) by role; arms whose trace already hooks or loops (1, 6, 7, 11) keep most of their trace
const SWAY_AMP = {reach: 0.55, mid: 0.45, short: 0.25};
const SWAY = {1: 0.3, 6: 0.35, 7: 0.3, 11: 0.4};

// Evaluate 3D control points of tentacle `def` at (wavePhase, waveAmp) in model metres
export function sampleTentacle(def, wavePhase = 0, waveAmp = 0) {
  const n = def.pts.length;
  return def.pts.map(([u, v, z], i) => {
    const s = i / Math.max(1, n - 1); // 0 at root, 1 at tip
    const env = waveAmp * (s * s) * (0.35 + 0.65 * s);
    const w1 = Math.sin(wavePhase * def.freq - s * 4.2 + def.phase);
    const w2 = Math.cos(wavePhase * def.freq * 0.8 - s * 3.1 + def.phase * 1.3);
    // resting S-sway on top of the trace: grows toward the tip, its own phase per arm, so neighbours that leave the
    // head side by side drift across each other (the reference's lower arms cross in S-curves, not in parallel lines)
    const sway = (SWAY[def.id] ?? 1) * SWAY_AMP[def.role] * Math.pow(s, 1.2) * Math.sin(s * 6.0 + def.phase * 1.7);
    const x = uToX(u) + env * 0.18 * w2;
    const y = vToY(v) + env * 0.36 * w1 + sway;
    const zPos = z + env * 0.22 * w2;
    return [x, y, zPos];
  });
}

// Operational sequences (both 8.0 s, looped or scrubbed)
export const SEQ = {
  cruise: {
    dur: 8.0,
    from: 'INTAKE FILL',
    to: 'JET PULSE',
    stroke(tau) {
      // Intake expansion 0..2.2s, rapid power jet stroke 2.2..4.8s, recovery 4.8..8.0s
      const up = ss(0.3, 2.1, tau);
      const fire = ss(2.2, 4.4, tau);
      const rec = ss(5.2, 7.7, tau);
      return clamp(0.18 + 0.82 * fire - 0.72 * rec - 0.18 * up * (1 - fire), 0, 1);
    },
    ballast(tau) {
      return 0.32 + 0.04 * Math.sin((tau / 8.0) * Math.PI * 2);
    },
    depth(tau) {
      return 600 + 18 * Math.sin((tau / 8.0) * Math.PI * 2);
    },
    speed(tau) {
      // m/s forward velocity (peaks after jet pulse)
      const pulse = Math.sin(clamp((tau - 1.8) / 4.2, 0, 1) * Math.PI);
      return 4.2 + 3.1 * pulse * pulse;
    },
  },
  dive: {
    dur: 8.0,
    from: '600 M BATHYAL',
    to: '6,000 M HADAL',
    stroke(tau) {
      // Siphuncle ballast pump stroke
      return 0.25 + 0.65 * ss(0.4, 3.2, tau) - 0.55 * ss(5.2, 7.6, tau);
    },
    ballast(tau) {
      // Floods chambers to dive, purges to trim at bottom
      return clamp(0.24 + 0.52 * ss(0.2, 3.0, tau) - 0.42 * ss(5.0, 7.7, tau), 0.15, 0.85);
    },
    depth(tau) {
      // 600 m bathyal -> 6000 m hadal -> 600 m
      const d = ss(0.5, 4.2, tau) * (1 - 0.85 * ss(5.6, 7.9, tau));
      return 600 + 5400 * d;
    },
    speed(tau) {
      return 3.4 + 1.8 * Math.sin((tau / 8.0) * Math.PI);
    },
  },
};

export function phaseAt(seq, tau) {
  if (seq === 'cruise') {
    if (tau < 2.2) return 'PHASE 1 · MANTLE INTAKE & PLENUM CHARGE';
    if (tau < 5.0) return 'PHASE 2 · OMNIDIRECTIONAL WATER-JET PULSE';
    return 'PHASE 3 · LAMINAR GLIDE & GYRO RECOVERY';
  }
  if (tau < 2.6) return 'PHASE 1 · SIPHUNCLE PERISTALTIC BALLAST FLOOD';
  if (tau < 5.4) return 'PHASE 2 · HADAL 60.4 MPA SHELL RIGIDITY LOCK';
  return 'PHASE 3 · HIGH-PRESSURE TURBOPUMP DEWATERING';
}

export function stateBadge(seq, stroke, depth) {
  if (seq === 'dive' && depth > 3500) {
    return ['HADAL ARMOR LOCK', `DEPTH ${Math.round(depth)} M · ${(depth * 0.01006).toFixed(1)} MPA`, 'warn'];
  }
  if (stroke > 0.55) {
    return ['HYDRO-JET VECTORS ACTIVE', `THRUST ${Math.round(42 + stroke * 142)} KN · JET ${(4.8 + stroke * 13.6).toFixed(1)} M/S`, 'warn'];
  }
  return ['BATHYAL ARCHIVE CRUISE', `DEPTH ${Math.round(depth)} M · SIGNAL STABLE`, 'ok'];
}

export function mechAt(seq, tau) {
  const S = SEQ[seq] || SEQ.cruise;
  const stroke = S.stroke(tau);
  const ballast = S.ballast(tau);
  const depth = S.depth(tau);
  const speed = S.speed(tau);
  const pressure = Number((depth * 0.01006).toFixed(2)); // MPa (6.04 MPa at 600 m, 60.36 MPa at 6000 m)
  const temp = Number((2.1 - ((depth - 600) / 5400) * 0.7).toFixed(2)); // 2.1 C at 600 m -> 1.4 C at 6000 m
  const salinity = Number((34.7 + ((depth - 600) / 5400) * 0.18).toFixed(2)); // 34.7 PSU
  const thrust = Math.round(28 + stroke * 156); // kN
  const jetVel = Number((3.6 + stroke * 14.8).toFixed(1)); // m/s
  const knots = Number((speed * 1.94384).toFixed(1));
  const turbineRpm = Math.round(1420 + stroke * 2860 + ballast * 420);
  const rigidity = Number((86.0 + (pressure / 60.4) * 13.4).toFixed(1)); // % composite shell lock
  // At tau = 0 (Frame 0, the hero shot), waveAmp is 0 so the silhouette matches the reference 100%;
  // ramps smoothly over 0.75 s into the live undulating wave!
  const waveAmp = ss(0.05, 0.85, tau) * (0.65 + 0.35 * stroke);
  const wavePhase = tau * 2.4;
  const eyeScan = Math.sin(tau * 1.57) * 0.14;
  const chamberFill = SEPTA_ANGLES.map((_, i) => {
    const f = i / (SEPTA_ANGLES.length - 1);
    return clamp(ballast * (0.55 + 0.75 * f) + 0.08 * Math.sin(tau * 2.2 - i * 0.6), 0.05, 0.95);
  });
  return {
    stroke,
    ballast,
    depth,
    speed,
    knots,
    pressure,
    temp,
    salinity,
    thrust,
    jetVel,
    turbineRpm,
    rigidity,
    waveAmp,
    wavePhase,
    eyeScan,
    chamberFill,
    state: stateBadge(seq, stroke, depth),
  };
}
