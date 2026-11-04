// MECHANICAL NAUTILUS (Archive / 007) film & tour script.
// Pure function of film time `t`: poses the Blender hull + 3-tier interior (`nautilus.js`),
// steps the studio & seabed (`stage.js`), and updates the archive console (`console.js`).
import * as THREE from 'three';
import {runSim} from '../kit/runtime.js';
import {createConsole, DISPLAY} from './console.js';
import {G, mechAt, phaseAt, SEQ, uToX, vToY} from './kin.js';
import {createNautilusStage} from './stage.js';
import {FOCUS} from './palette.js';

export const SCRIPT = [
  {t: 0.0, seq: 'cruise', view: 'hero'},
  {t: 2.2, display: 'labels'},
  {t: 3.8, view: 'core'},
  {t: 7.8, seq: 'dive', view: 'septa'},
  {t: 11.0, display: 'labels'},
  {t: 11.6, view: 'tentacles'},
  {t: 14.5, view: 'jets'},
  {t: 15.6, seq: 'cruise'},
  {t: 17.3, view: 'hero'},
  {t: 18.0, display: 'exploded'},
  {t: 18.6, display: 'orbit'},
  {t: 21.8, display: 'exploded'},
  {t: 23.2, display: 'orbit'},
];

export const DURATION = 26.0;
export const DEFAULTS = {
  duration: DURATION,
  fps: 60,
  theme: 'light',
  hud: {enabled: false, title: 'nautilus', subtitle: ''},
  director: {enabled: false},
  watermark: '',
};

const D2R = Math.PI / 180;
const smoother = (x) => {
  const u = Math.min(1, Math.max(0, x));
  return u * u * u * (u * (u * 6 - 15) + 10);
};
const ss = (a, b, t) => smoother((t - a) / Math.max(1e-6, b - a));
const pulseWindow = (t0, t1, t2, t3, t) => ss(t0, t1, t) * (1 - ss(t2, t3, t));

// Stage 1: Per-subsystem localized close-up teardowns during each close-up camera beat
export const focusExplodeAt = (t) => ({
  core: pulseWindow(4.2, 5.4, 6.4, 7.5, t),
  septa: pulseWindow(8.2, 9.4, 10.3, 11.4, t),
  tentacles: pulseWindow(11.9, 13.0, 13.5, 14.4, t),
  jets: pulseWindow(14.9, 16.0, 16.4, 17.2, t),
});

export const seqAt = (t) => {
  const e = SCRIPT.filter((x) => x.seq && x.t <= t).pop();
  return {seq: e.seq, tau: (t - e.t) % SEQ[e.seq].dur};
};

export const displayAt = (t) => {
  const out = Object.fromEntries(DISPLAY.map((k) => [k, 0]));
  for (const e of SCRIPT) if (e.display && e.t <= t) out[e.display] = out[e.display] ? 0 : 1;
  return out;
};

const lastFlip = (key, t) => SCRIPT.filter((e) => e.display === key && e.t <= t).pop()?.t ?? -9;

export const easedDisplay = (key, t, dur = 0.75) => {
  const on = displayAt(t)[key];
  const k = ss(lastFlip(key, t), lastFlip(key, t) + dur, t);
  return on ? k : 1 - k;
};

// Pre-integrate distance swum over the film so render(t) is 100% pure and deterministic
const DT = 1 / 240;
const DIST = [0];
{
  for (let i = 1; i * DT <= DURATION + 1; i++) {
    const t = (i - 0.5) * DT;
    const {seq, tau} = seqAt(t);
    const m = mechAt(seq, tau);
    DIST.push(DIST[i - 1] + m.speed * DT * 0.45);
  }
}
export const distAt = (t) => {
  const u = Math.max(0, Math.min(DIST.length - 2, t / DT));
  const i = Math.floor(u);
  return DIST[i] + (DIST[i + 1] - DIST[i]) * (u - i);
};

// Camera views. Each close-up was solved with sims/frame.mjs (docs/form.md, "Camera and teardown") so its subject, at the
// teardown's widest, fills the free area between the console panels and sits centred in it; the angle is chosen,
// the target, distance and screen offset are solved. Each drifts slowly (az and a 6% push-in over the shot) so a
// held shot is never a still.
// PULL: every shot (close-ups included) this much further out than the solved fit, for breathing room
const PULL = 1.2;
const drift = (base, u, {daz = 0, push = 0.06, dur = 4} = {}) => {
  const k = Math.min(1, Math.max(0, u / dur));
  return {...base, az: base.az + daz * k, d: base.d * PULL * (1 - push * k), sx: base.sx / PULL, sy: base.sy / PULL};
};
export const VIEW_FN = {
  // whole machine, reference angle, centred in the free area
  hero: (u) => drift({tx: -0.18, ty: -0.34, tz: -0.07, az: 0, el: 0, d: 32.4 * (FOCUS ? 0.9 : 1), sx: 18, sy: 26}, u, {daz: 2.5, push: 0.04, dur: 3.8}),
  // umbilicus + eye: from the front-left so the ring stack lifts toward the lens
  core: (u) => drift(FOCUS ? {tx: 3.1, ty: 0.1, tz: 0.85, az: 20, el: 8, d: 19.6, sx: 135, sy: -3} : {tx: 2.72, ty: -0.06, tz: 0, az: 20, el: 8, d: 17.4, sx: 110, sy: 4}, u, {daz: 3, dur: 4}),
  // the open shell window from above: septa push out, vanes lift
  septa: (u) => drift({tx: 3.5, ty: 2.2, tz: 1.2, az: -10, el: 22, d: 26.1, sx: 11, sy: 7}, u, {daz: 3, push: 0.08, dur: 3.8}),
  // the tentacle bundle from the front-left and a little above
  tentacles: (u) => drift({tx: -4.19, ty: -1.34, tz: 0, az: -24, el: 10, d: 23.8, sx: 56, sy: 7}, u, {daz: 2.5, dur: 2.9}),
  // the rear of the whorl and its jet cluster from the rear quarter, the whole rear shell in frame (fitting the jets
  // alone put a wall of plates across the frame in front of them)
  jets: (u) => drift({tx: 8.6, ty: -1.9, tz: 0, az: 52, el: 2, d: 28.4, sx: 6, sy: 3}, u, {daz: 5, push: 0.1, dur: 2.8}),
  front: (u) => ({tx: -1.1, ty: -0.08, tz: 0, az: -68 + 2.2 * u, el: 5, d: 21.8, sx: -16, sy: -46}),
};

// solved like the close-ups, at the explode's widest (t 19.8), az 0
const EXPLODE_CAM = {tx: 0.11, ty: 1.65, tz: 0.04, az: 0, el: 10, d: 44.3 * PULL, sx: 17 / PULL, sy: 19 / PULL};

const VIEWS = SCRIPT.filter((e) => e.view).map((e) => [e.t, e.view]);
const blend = (a, b, k, bump = true) => {
  const o = {};
  for (const key in b) {
    o[key] =
      key === 'az'
        ? a.az + ((((b.az - a.az + 540) % 360) - 180) * k)
        : a[key] + (b[key] - a[key]) * k;
  }
  const swing = Math.min(1, Math.abs(((b.az - a.az + 540) % 360) - 180) / 90);
  // pull back mid-move only in proportion to how far the camera swings round (so a big swing clears the hull);
  // a push-in with a small swing is a straight dolly, not a hold-then-lunge
  if (bump) o.d += Math.max(0, Math.max(a.d, b.d) + 1.2 * swing - o.d) * Math.sin(Math.PI * k) * swing;
  return o;
};

export const camAt = (t, orbit = 0, explode = 0) => {
  let i = 0;
  while (i < VIEWS.length - 1 && VIEWS[i + 1][0] <= t) i++;
  const cur = VIEW_FN[VIEWS[i][1]](t - VIEWS[i][0]);
  let o = {...cur};
  if (i > 0) {
    const k = ss(VIEWS[i][0], VIEWS[i][0] + 1.5, t);
    if (k < 1) o = blend(VIEW_FN[VIEWS[i - 1][1]](t - VIEWS[i - 1][0]), cur, k);
  }
  // full explode: blend to the solved explode camera (the whole exploded assembly in the free area, from a little
  // above). Orbit is a swing out and back over its window, so the machine closes at the angle it opened at.
  if (explode > 0.001) o = blend(o, EXPLODE_CAM, explode, false);
  if (orbit > 0) {
    const t0 = lastFlip('orbit', t);
    const t1 = SCRIPT.find((e) => e.display === 'orbit' && e.t > t0)?.t ?? DURATION;
    const k = Math.min(1, Math.max(0, (t - t0) / (t1 - t0)));
    o.az += 30 * Math.sin(Math.PI * smoother(k)) * orbit;
    o.el += 4 * Math.sin(Math.PI * smoother(k)) * orbit;
  }
  return o;
};

export const viewAt = (t) => VIEWS.filter(([a]) => a <= t).pop();

// Operator cursor waypoints
const REST = [
  [820, 480],
  [740, 430],
  [900, 510],
  [780, 390],
];
export function makeCursor(ui) {
  const EV = SCRIPT.filter((e) => e.t > 0).flatMap((e) => {
    const out = [];
    if (e.seq && ui.spots[e.seq]) out.push({t: e.t, spot: ui.spots[e.seq]});
    if (e.view && ui.spots[e.view]) out.push({t: e.t + (e.seq ? 0.35 : 0), spot: ui.spots[e.view]});
    if (e.display && ui.spots[e.display]) out.push({t: e.t, spot: ui.spots[e.display]});
    return out;
  });
  const WP = [[0, 880, 560]];
  EV.forEach((e, i) => {
    WP.push([e.t - 0.16, ...e.spot], [e.t + 0.22, ...e.spot]);
    WP.push([e.t + 1.3, ...REST[i % REST.length]]);
  });
  WP.sort((a, b) => a[0] - b[0]);
  return (t) => {
    if (t < 0.05) return {x: -99, y: -99, press: false, ring: 0, ringX: 0, ringY: 0};
    let i = 0;
    while (i < WP.length - 2 && t > WP[i + 1][0]) i++;
    const [t0, x0, y0] = WP[i];
    const [t1, x1, y1] = WP[i + 1];
    const k = ss(t0, t1, t);
    const len = Math.hypot(x1 - x0, y1 - y0);
    const bow = Math.sin(Math.PI * k) * Math.min(22, len * 0.07);
    let press = false;
    let ring = 0;
    let rx = 0;
    let ry = 0;
    for (const e of EV) {
      if (t >= e.t - 0.07 && t < e.t + 0.09) press = true;
      if (t >= e.t && t < e.t + 0.55) {
        ring = 1 - (t - e.t) / 0.55;
        [rx, ry] = e.spot;
      }
    }
    return {
      x: x0 + (x1 - x0) * k + (len ? (-(y1 - y0) / len) * bow : 0),
      y: y0 + (y1 - y0) * k + (len ? ((x1 - x0) / len) * bow : 0),
      press,
      ring,
      ringX: rx,
      ringY: ry,
    };
  };
}

// 3D Callout anchors in the Nautilus frame
const V3 = THREE.Vector3;
const PARTS = [
  {name: 'SPIRAL SHELL ARMOR', sub: 'LAYERED CERAMIC COMPOSITE · 07', at: () => new V3(uToX(0.76), vToY(0.88), 0.8)},
  {name: 'DORSAL REACTOR CUTAWAY', sub: 'MHD TURBINE & HELICAL COILS', at: () => new V3(uToX(0.62), vToY(0.82), 0.6)},
  {name: 'CEPHALIC VISOR HOOD', sub: 'ARTICULATED BROW SHIELD', at: () => new V3(uToX(0.46), vToY(0.62), 0.7)},
  {name: 'OPTICAL SENSOR MODULE', sub: 'CONCENTRIC IRIS GIMBAL', at: () => new V3(G.eyeX, G.eyeY, G.eyeZ)},
  {name: 'UMBILICUS COMMAND CORE', sub: 'GYROSCOPIC PRESSURE HUB', at: () => new V3(G.hubX, G.hubY, 1.45)},
  {name: 'VENTRAL CHEEK LOBE', sub: 'APERTURE FLANGE SHIELD', at: () => new V3(uToX(0.62), vToY(0.24), 1.6)},
  {name: 'TENTACLE ARRAY', sub: '9 PROGRESSIVE APPENDAGES', at: () => new V3(uToX(0.26), vToY(0.32), 0.7)},
  {name: 'PROPULSION SYSTEM', sub: '4× OMNIDIRECTIONAL WATER-JETS', at: () => new V3(uToX(0.94), vToY(0.36), 0.3)},
];

export function makeLabels(st) {
  return (m, o) => {
    if (o < 0.02) return [];
    const pts = PARTS.map((p) => {
      const q = p.at(m);
      return {p, at: st.project(q.x, q.y, q.z)};
    }).filter((x) => x.at && x.at[0] > 280 && x.at[0] < 1290 && x.at[1] > 180 && x.at[1] < 710);

    const L = pts.filter((x) => x.at[0] < 780).sort((a, b) => a.at[1] - b.at[1]);
    const R = pts.filter((x) => x.at[0] >= 780).sort((a, b) => a.at[1] - b.at[1]);
    const out = [];
    const stack = (col, x, w, y0 = 248) => {
      let y = y0;
      for (const c of col) {
        y = Math.max(y, Math.min(685, c.at[1] - 10));
        out.push({name: c.p.name, sub: c.p.sub, at: c.at, label: [x, y], w, o});
        y += 38;
      }
    };
    stack(L, 42, 185, 324);
    stack(R, 1110, 185, 248);
    return out;
  };
}

export function makeConsoleFrame(ui, st) {
  const labels = makeLabels(st);
  return (t, s) => {
    const S = SEQ[s.seq];
    ui.update({
      mech: s.mech,
      seq: s.seq,
      prog: s.tau / S.dur,
      tau: s.tau,
      dur: S.dur,
      from: S.from,
      to: S.to,
      phase: phaseAt(s.seq, s.tau),
      view: s.view,
      display: s.display,
      explode: s.explode,
      paused: s.paused ?? false,
      speed: s.speed ?? 1,
      speedK: s.speedK ?? 0.5,
      callouts: labels(s.mech, s.labels),
      cursor: s.cursor,
    });
  };
}

export function makeFilm() {
  return async ({canvas, capture}) => {
    const st = await createNautilusStage({canvas});
    const resize = () =>
      st.resize(1600, 900, capture ? devicePixelRatio || 1 : Math.min(devicePixelRatio || 1, 2));
    resize();
    const ui = createConsole(document.getElementById('app'));
    const cursorAt = makeCursor(ui);
    const frameConsole = makeConsoleFrame(ui, st);
    window.NS = st;
    window.__FRAME = {camera: st.camera, root: st.nautilus.root}; // sims/frame.mjs (framing solver)
    return {
      resize,
      render(t) {
        const {seq, tau} = seqAt(t);
        const m = mechAt(seq, tau);
        const disp = displayAt(t);
        // 1.6 s each way: long enough for the staggered order to read (opens 18.0-19.6, closes 21.8-23.4, the timeline's beats)
        const explode = easedDisplay('exploded', t, 1.6);
        const focusExplode = focusExplodeAt(t);
        const xray = easedDisplay('xray', t, 0.7);
        // window.__CAM: a camera override for sims/frame.mjs (tools only; never set in the film)
        const cam = {...camAt(t, disp.orbit, explode), ...(window.__CAM || {})};
        st.frame(
          {
            time: t,
            mech: m,
            dist: distAt(t),
            explode,
            focusExplode,
            xray,
            section: !!disp.section,
          },
          {...cam, az: cam.az * D2R, el: cam.el * D2R},
        );
        const [vt0, view] = viewAt(t);
        frameConsole(t, {
          seq,
          tau,
          mech: m,
          view,
          display: disp,
          explode: Math.max(explode, focusExplode.core, focusExplode.septa, focusExplode.tentacles, focusExplode.jets),
          labels: easedDisplay('labels', t, 0.5) * ss(vt0 + 0.5, vt0 + 1.1, t),
          cursor: cursorAt(t),
        });
        return {};
      },
    };
  };
}

export const run = () => runSim(DEFAULTS, makeFilm());
