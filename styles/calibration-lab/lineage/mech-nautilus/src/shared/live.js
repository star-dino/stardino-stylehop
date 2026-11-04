// Interactive real-time Mechanical Nautilus (Archive / 007) simulator.
// Drives the Blender hull + 3-tier interior (`nautilus.js`), studio stage (`stage.js`), and archive console (`console.js`).
// Left alone it runs the auto tour with the operator's cursor; any click, drag, wheel, or key hands control to the user.
import {warmComposer} from '../kit/warm.js';
import {createConsole, DISPLAY, VIEWS} from './console.js';
import {
  camAt,
  displayAt,
  DURATION,
  focusExplodeAt,
  makeConsoleFrame,
  makeCursor,
  SCRIPT,
  seqAt,
  viewAt,
  VIEW_FN,
} from './film.js';
import {mechAt, SEQ} from './kin.js';
import {P} from './palette.js';
import {createNautilusStage} from './stage.js';

const W = 1600;
const H = 900;
const IDLE = 25;
const D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const smoother = (x) => {
  const u = clamp(x, 0, 1);
  return u * u * u * (u * (u * 6 - 15) + 10);
};
const ss = (a, b, t) => smoother((t - a) / Math.max(1e-6, b - a));
const wrap = (d) => ((((d + 180) % 360) + 360) % 360) - 180;
const SPEED = [0.1, 2.0];
const speedK = (v) => (v - SPEED[0]) / (SPEED[1] - SPEED[0]);

const CSS = (top) => `
html,body{background:${P.stage.page};overflow:hidden;margin:0}
#app{position:absolute!important;inset:auto!important;left:0;top:0;width:${W}px;height:${H}px;transform-origin:0 0}
#gl{touch-action:none;cursor:grab}
#gl.drag{cursor:grabbing}
.bt{pointer-events:auto;cursor:pointer}
.bt:hover{filter:brightness(.96)}
.hit{position:absolute;pointer-events:auto;cursor:ew-resize}
.tourchip{position:absolute;left:800px;top:22px;transform:translateX(-50%);display:flex;align-items:center;gap:7px;height:22px;padding:0 12px;border:1px solid ${P.ui.chipBorder};border-radius:4px;background:${P.ui.chipBg};color:${P.ui.chipInk};font:700 9px 'JetBrains Mono',monospace;letter-spacing:1.3px;white-space:nowrap;cursor:pointer;pointer-events:auto}
.tourchip i{display:block;width:6px;height:6px;border-radius:50%;background:${P.ui.chipDot}}
.tourchip.on i{animation:blink 1.2s steps(2) infinite}
@keyframes blink{50%{opacity:.15}}
.turn{position:fixed;left:0;right:0;bottom:18px;text-align:center;font:600 12px/1.4 'JetBrains Mono',monospace;letter-spacing:1px;color:${P.ui.hint};text-transform:uppercase;display:none}
@media (orientation:portrait) and (max-width:820px){.turn{display:block}}
`;

export async function runLive() {
  const top = Number(document.body.dataset.top || 0);
  const style = document.createElement('style');
  style.textContent = CSS(top);
  document.head.appendChild(style);

  const app = document.getElementById('app');
  const canvas = document.createElement('canvas');
  canvas.id = 'gl';
  app.appendChild(canvas);

  const st = await createNautilusStage({canvas});
  const ui = createConsole(app);
  const tourCursor = makeCursor(ui);
  const frameConsole = makeConsoleFrame(ui, st);

  // ------------------------------------------------------------ Quality Tiers
  const TIERS = [
    {samples: 4, ao: true, shadow: 2048, pr: 2},
    {samples: 2, ao: false, shadow: 1024, pr: 1.5},
    {samples: 0, ao: false, shadow: 1024, pr: 1},
  ];
  const light = matchMedia('(pointer: coarse)').matches || Math.min(innerWidth, innerHeight) < 700;
  let tier = light ? 2 : 0;
  let scale = 1;
  const fit = () => {
    const h = innerHeight - top;
    scale = Math.min(innerWidth / W, h / H);
    app.style.transform = `translate(${(innerWidth - W * scale) / 2}px, ${top + (h - H * scale) / 2}px) scale(${scale})`;
    st.resize(W, H, clamp((devicePixelRatio || 1) * scale, 0.75, TIERS[tier].pr));
  };
  const applyTier = () => {
    const {pr, ...q} = TIERS[tier];
    st.setQuality(q);
    fit();
  };
  applyTier();
  addEventListener('resize', fit);

  const toStage = (cx, cy) => {
    const r = app.getBoundingClientRect();
    return [(cx - r.left) / scale, (cy - r.top) / scale];
  };

  const tourChip = document.createElement('div');
  tourChip.className = 'tourchip';
  ui.root.appendChild(tourChip);

  const note = document.createElement('div');
  note.className = 'turn';
  note.textContent = 'Turn your phone sideways for the full archive console';
  document.body.appendChild(note);

  // ------------------------------------------------------------ Interactive State
  let T = 0;
  let seq = 'cruise';
  let tau = 0;
  let speed = 1;
  let paused = false;
  let view = 'hero';
  let viewAt0 = 0;
  const disp = Object.fromEntries(DISPLAY.map((k) => [k, {on: 0, t: -9}]));
  const off = {az: 0, el: 0, k: 1};
  const cam = {...VIEW_FN.hero(0)};
  let dist = 0;
  let ring = {t: -9, x: 0, y: 0};

  const eased = (k, dur = 0.7) => {
    const d = disp[k];
    const x = ss(d.t, d.t + dur, T);
    return d.on ? x : 1 - x;
  };
  const pulse = (k) => {
    if (ui.spots[k]) ring = {t: T, x: ui.spots[k][0], y: ui.spots[k][1]};
  };

  // ------------------------------------------------------------ Auto Tour vs Visitor Takeover
  const AP = {on: true, t0: 0, loop: 0};
  let lastInput = 0;
  const startTour = () => {
    AP.on = true;
    AP.t0 = T;
    AP.loop = 0;
    paused = false;
    speed = 1;
    Object.assign(off, {az: 0, el: 0, k: 1});
  };
  const takeOver = () => {
    lastInput = T;
    if (!AP.on) return;
    AP.on = false;
    const cyc = (T - AP.t0) % DURATION;
    const [t0, v] = viewAt(cyc);
    view = v;
    viewAt0 = T - (cyc - t0);
  };

  tourChip.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    lastInput = T;
    if (AP.on) takeOver();
    else startTour();
  });
  addEventListener('pointerdown', (e) => {
    if (e.target !== tourChip) takeOver();
  });

  const syncDisplay = (cyc) => {
    const want = displayAt(cyc);
    for (const k of DISPLAY) {
      if (disp[k].on !== want[k]) {
        disp[k].on = want[k];
        disp[k].t = T;
      }
    }
  };

  // ------------------------------------------------------------ Button & Scrubber Controls
  for (const s of ['cruise', 'dive']) {
    ui.btn[s].addEventListener('click', () => {
      takeOver();
      pulse(s);
      seq = s;
      tau = 0;
      paused = false;
    });
  }
  for (const v of VIEWS) {
    ui.btn[v].addEventListener('click', () => {
      takeOver();
      pulse(v);
      view = v;
      viewAt0 = T;
      Object.assign(off, {az: 0, el: 0, k: 1});
    });
  }
  for (const k of DISPLAY) {
    ui.btn[k].addEventListener('click', () => {
      takeOver();
      pulse(k);
      disp[k].on = disp[k].on ? 0 : 1;
      disp[k].t = T;
    });
  }
  ui.btn.play.addEventListener('click', () => {
    takeOver();
    pulse('play');
    if (tau >= SEQ[seq].dur - 1e-3) tau = 0;
    paused = !paused;
  });

  const slider = (x0, w, y, apply) => {
    const d = document.createElement('div');
    d.className = 'hit';
    Object.assign(d.style, {left: `${x0 - 8}px`, top: `${y - 11}px`, width: `${w + 16}px`, height: '22px'});
    const move = (e) => {
      const [x] = toStage(e.clientX, e.clientY);
      apply(clamp((x - x0) / w, 0, 1));
      lastInput = T;
    };
    d.addEventListener('pointerdown', (e) => {
      takeOver();
      d.setPointerCapture(e.pointerId);
      const up = () => {
        removeEventListener('pointermove', move);
        removeEventListener('pointerup', up);
      };
      addEventListener('pointermove', move);
      addEventListener('pointerup', up);
      move(e);
    });
    ui.root.appendChild(d);
  };
  slider(ui.TL.x, ui.TL.w, 854, (k) => {
    tau = k * SEQ[seq].dur;
    paused = true;
  });
  slider(ui.SP.x, ui.SP.w, 854, (k) => {
    speed = SPEED[0] + k * (SPEED[1] - SPEED[0]);
  });

  addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const key = e.key.toLowerCase();
    const v = {1: 'hero', 2: 'core', 3: 'septa', 4: 'tentacles', 5: 'jets', 6: 'front'}[key];
    if (v) ui.btn[v].click();
    else if (key === ' ') ui.btn.play.click();
    else if (key === 'c') ui.btn.cruise.click();
    else if (key === 'd') ui.btn.dive.click();
    else if (key === 'l') ui.btn.labels.click();
    else if (key === 's') ui.btn.section.click();
    else if (key === 'x') ui.btn.xray.click();
    else if (key === 'e') ui.btn.exploded.click();
    else if (key === 'o') ui.btn.orbit.click();
    else return;
    e.preventDefault();
  });

  let drag = null;
  canvas.addEventListener('pointerdown', (e) => {
    drag = {x: e.clientX, y: e.clientY};
    canvas.setPointerCapture(e.pointerId);
    canvas.classList.add('drag');
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!drag) return;
    off.az += ((e.clientX - drag.x) / scale) * 0.32;
    off.el = clamp(off.el + ((e.clientY - drag.y) / scale) * 0.22, -35, 65);
    drag = {x: e.clientX, y: e.clientY};
    lastInput = T;
  });
  const endDrag = () => {
    drag = null;
    canvas.classList.remove('drag');
  };
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault();
      takeOver();
      off.k = clamp(off.k * Math.exp(e.deltaY * 0.0012), 0.45, 2.2);
    },
    {passive: false},
  );

  // ------------------------------------------------------------ Render Loop
  startTour();
  let last = performance.now();
  const perf = {n: 0, sum: 0, slow: 0, age: 0};

  const frame = (now) => {
    const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
    last = now;
    T += dt;

    if (tier < TIERS.length - 1) {
      perf.age += dt;
      if (perf.age > 0.6) {
        perf.sum += dt;
        perf.n++;
        if (perf.sum >= 0.5 && perf.n >= 6) {
          perf.slow = perf.sum / perf.n > 0.025 ? perf.slow + 1 : 0;
          perf.sum = 0;
          perf.n = 0;
          if (perf.slow >= (perf.age < 6 ? 1 : 2)) {
            tier++;
            applyTier();
            Object.assign(perf, {age: 0, slow: 0});
          }
        }
      }
    }

    const explodeBtn = eased('exploded', 0.95);
    const xray = eased('xray', 0.7);
    let explode = 0;
    let focusExplode = {core: 0, septa: 0, tentacles: 0, jets: 0};

    let tgt;
    let cursor;
    let since;
    if (AP.on) {
      const c = T - AP.t0;
      const loop = Math.floor(c / DURATION);
      const cyc = c - loop * DURATION;
      if (loop > AP.loop) AP.loop = loop;
      const s = seqAt(cyc);
      seq = s.seq;
      tau = s.tau;
      syncDisplay(cyc);
      explode = explodeBtn;
      focusExplode = focusExplodeAt(cyc);
      tgt = camAt(cyc, displayAt(cyc).orbit, explode);
      const [t0, v] = viewAt(cyc);
      view = v;
      since = cyc - t0;
      cursor = tourCursor(cyc);
      if (AP.loop > 0 && cyc < 0.8) {
        const end = tourCursor(DURATION - 0.01);
        const k = ss(0, 0.8, cyc);
        cursor = {...cursor, x: end.x + (cursor.x - end.x) * k, y: end.y + (cursor.y - end.y) * k};
      }
    } else {
      if (T - lastInput > IDLE) startTour();
      if (!paused) tau = (tau + dt * speed) % SEQ[seq].dur;
      since = T - viewAt0;
      if (view === 'hero' || view === 'front') {
        explode = explodeBtn;
      } else if (view in focusExplode) {
        focusExplode[view] = explodeBtn;
      }
      tgt = {...VIEW_FN[view](since)};
      tgt.az += off.az + (disp.orbit.on ? 14 * (T - disp.orbit.t) : 0);
      tgt.el = clamp(tgt.el + off.el, -35, 80);
      tgt.d = (tgt.d + 6.4 * explode) * off.k;
      const rk = Math.max(0, 1 - (T - ring.t) / 0.55);
      cursor = {x: -99, y: -99, press: false, ring: rk, ringX: ring.x, ringY: ring.y};
    }

    const m = mechAt(seq, tau);
    const live = AP.on || !paused;
    dist += live ? m.speed * dt * (AP.on ? 1 : speed) * 0.45 : 0;

    const k = 1 - Math.exp(-dt / (AP.on ? 0.18 : 0.38));
    cam.az += wrap(tgt.az - cam.az) * k;
    for (const key of ['tx', 'ty', 'tz', 'el', 'd', 'sx', 'sy']) cam[key] += (tgt[key] - cam[key]) * k;

    st.frame(
      {
        time: T,
        mech: m,
        dist,
        explode,
        focusExplode,
        xray,
        section: !!disp.section.on,
      },
      {...cam, az: cam.az * D2R, el: cam.el * D2R},
    );

    const display = Object.fromEntries(DISPLAY.map((x) => [x, disp[x].on]));
    frameConsole(T, {
      seq,
      tau,
      mech: m,
      view,
      display,
      explode: Math.max(explode, focusExplode.core, focusExplode.septa, focusExplode.tentacles, focusExplode.jets),
      labels: eased('labels', 0.5) * ss(0.4, 1.0, since),
      cursor,
      paused: AP.on ? false : paused,
      speed: AP.on ? 1 : speed,
      speedK: speedK(AP.on ? 1 : speed),
    });

    if (tourChip.classList.contains('on') !== AP.on || !tourChip.firstChild) {
      tourChip.classList.toggle('on', AP.on);
      tourChip.innerHTML = AP.on ? '<i></i>AUTO TOUR · CLICK TO TAKE OVER' : '▶ RESUME TOUR';
    }
    if (!window.SIM_SHOWN) {
      window.SIM_SHOWN = true;
      dispatchEvent(new Event('simframe'));
    }
    requestAnimationFrame(frame);
  };

  warmComposer(st.renderer, st.composer, st.scene, st.camera).then(() => requestAnimationFrame(frame));
  window.LIVE = {
    st,
    cam,
    startTour,
    takeOver,
    get tier() {
      return tier;
    },
    get T() {
      return T;
    },
  };
  void SCRIPT;
}
