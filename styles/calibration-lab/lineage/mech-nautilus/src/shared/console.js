// The Mechanical Nautilus (Archive / 007) console overlay at 1600 x 900.
// Laid out directly from the reference sheet (`refs/nautilus.png`):
//   - Top-Left: ARCHIVE / 007 title block & physical specification table (12.0 m / 18.5 m / 420 t / 6,000 m+)
//   - Top-Center: Live 18.5 m × 12.0 m Blueprint Side Schematic (logarithmic spiral septa + animated tentacles)
//   - Top-Right: 01 INTERNAL SECTION live circular cross-section + 01..05 subsystem readout
//   - Right-Lower: Sequence (CRUISE / DIVE), Camera Views (6), and Display Modes (5)
//   - Bottom-Left: 02 FRONT VIEW radial schematic & live propulsion/ballast gauges
//   - Bottom-Center: 03 ENVIRONMENTAL DATA (MPa, °C, PSU, multi-harmonic wave chart) & timeline scrubber
//   - Bottom-Right: 04 STRUCTURAL OVERVIEW (live 8-segment spiral shell breakdown)

import {P} from './palette.js';

export const C = P.ui; // tokens come from palette.js (scheme A/B/C)

export const VIEWS = ['hero', 'core', 'septa', 'tentacles', 'jets', 'front'];
export const VIEW_LABEL = {
  hero: 'HERO ¾',
  core: '01 CORE',
  septa: '02 SEPTA',
  tentacles: '04 TENTACLES',
  jets: '05 JETS',
  front: 'FRONT',
};

export const DISPLAY = ['labels', 'section', 'xray', 'exploded', 'orbit'];
export const DISPLAY_LABEL = {
  labels: 'LABELS',
  section: 'SECTION',
  xray: 'X-RAY HULL',
  exploded: 'EXPLODED',
  orbit: 'ORBIT',
};

const CSS = `
#app{font-family:Inter,system-ui,sans-serif;color:${C.ink};-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.ui{position:absolute;inset:0;pointer-events:none}
.mo{font-family:'JetBrains Mono',ui-monospace,monospace}
.cp{position:absolute;background:${C.panel};border:1px solid ${C.line};border-radius:4px;box-shadow:0 2px 10px ${C.panelShadow}}
.ph{position:absolute;display:flex;align-items:center;gap:8px;font:700 10px 'JetBrains Mono',monospace;letter-spacing:1.6px;color:${C.ink}}
.ph i{display:block;width:3px;height:12px;background:${C.or}}
.pn{position:absolute;font:500 9px 'JetBrains Mono',monospace;color:${C.mute};letter-spacing:1px}
.sm{font:500 8.8px 'JetBrains Mono',monospace;letter-spacing:1.5px;color:${C.mute};text-transform:uppercase;white-space:nowrap}
.bt{position:absolute;height:21px;padding:0 9px;display:flex;align-items:center;justify-content:center;border:1px solid ${C.faint};border-radius:3px;background:${C.btn};font:700 9px 'JetBrains Mono',monospace;letter-spacing:1.2px;color:${C.ink};white-space:nowrap}
.call{position:absolute;white-space:nowrap}
.call b{display:flex;align-items:center;gap:6px;font:700 9.4px 'JetBrains Mono',monospace;letter-spacing:1.2px;color:${C.ink}}
.call b i{display:block;width:6px;height:6px;background:${C.or}}
.call span{display:block;font:500 7.8px 'JetBrains Mono',monospace;letter-spacing:1.1px;color:${C.mute};margin-top:2px}
.cur{position:absolute;left:0;top:0;z-index:50;filter:drop-shadow(0 1px 2px rgba(0,0,0,.3))}
.ring{position:absolute;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;border:1.5px solid ${C.or};opacity:0;z-index:49}
`;

const el = (h) => {
  const d = document.createElement('div');
  d.innerHTML = h.trim();
  return d.firstElementChild;
};

export function createConsole(app) {
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);
  const ui = el(`<div class="ui"></div>`);
  app.appendChild(ui);
  const add = (h) => {
    const n = el(h);
    ui.appendChild(n);
    return n;
  };
  const panel = (x, y, w, h, title, n) => {
    add(`<div class="cp" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px"></div>`);
    add(`<div class="ph" style="left:${x + 12}px;top:${y + 10}px"><i></i>${title}</div>`);
    add(`<div class="pn" style="right:${1600 - x - w + 12}px;top:${y + 11}px">${n}</div>`);
  };

  // ------------------------------------------------------------ Top-Left: Archive Header & Spec Sheet
  panel(24, 18, 286, 214, 'ARCHIVE / 007', 'SPEC');
  add(`<div style="position:absolute;left:36px;top:40px;font-size:23px;font-weight:700;letter-spacing:0.6px;line-height:1.08">MECHANICAL<br>NAUTILUS</div>`);
  add(`<div class="sm" style="position:absolute;left:37px;top:94px;letter-spacing:1.7px;color:${C.text1}">ARTIFICIAL MARINE LIFEFORM</div>`);
  add(`<div style="position:absolute;left:37px;top:112px;width:54px;height:3px;background:${C.or}"></div>`);
  [
    ['DIAMETER', '12.0 m'],
    ['LENGTH', '18.5 m'],
    ['WEIGHT', '420 t'],
    ['DEPTH', '6,000 m+'],
  ].forEach(([k, v], i) => {
    const y = 124 + i * 16;
    add(`<div class="sm" style="position:absolute;left:37px;top:${y}px;color:${C.text2}">${k}</div>`);
    add(`<div class="mo" style="position:absolute;left:118px;top:${y - 1}px;font-size:9.6px;font-weight:600;color:${C.ink}">: &nbsp;${v}</div>`);
  });
  const stChip = add(`<div style="position:absolute;left:37px;top:196px;width:9px;height:22px;border-radius:2px;background:${C.green}"></div>`);
  const stTitle = add(`<div class="mo" style="position:absolute;left:53px;top:194px;font-size:10.5px;font-weight:700;letter-spacing:1px"></div>`);
  const stSub = add(`<div class="sm" style="position:absolute;left:53px;top:209px;font-size:8px"></div>`);

  // ------------------------------------------------------------ Top-Center: Orthographic Dimension Blueprint (18.5 m x 12.0 m)
  panel(322, 18, 326, 178, 'ORTHOGRAPHIC PROFILE · 18.5 M', '00');
  const bpSvg = add(`<svg style="position:absolute;left:332px;top:42px" width="306" height="146"></svg>`);

  // ------------------------------------------------------------ Top-Right: 01 INTERNAL SECTION & Subsystem Index
  panel(1316, 18, 260, 224, 'INTERNAL SECTION', '01');
  const secSvg = add(`<svg style="position:absolute;left:1324px;top:44px" width="118" height="118"></svg>`);
  const subRows = [
    ['01', 'Command Core'],
    ['02', 'Pressure Chamber'],
    ['03', 'Power Unit'],
    ['04', 'Motion Control'],
    ['05', 'Water-Jet Drive'],
  ].map(([num, label], i) => {
    const y = 50 + i * 22;
    const dot = add(`<div style="position:absolute;left:1448px;top:${y + 3}px;width:5px;height:5px;border-radius:50%;background:${C.faint}"></div>`);
    add(`<div class="mo" style="position:absolute;left:1458px;top:${y}px;font-size:8.8px;color:${C.mute}">${num}</div>`);
    const txt = add(`<div class="mo" style="position:absolute;left:1476px;top:${y}px;font-size:9px;font-weight:600;color:${C.ink}">${label}</div>`);
    return {dot, txt};
  });
  add(`<div style="position:absolute;left:1328px;top:168px;width:236px;height:1px;background:${C.line}"></div>`);
  const coreReadout = add(`<div class="mo" style="position:absolute;left:1328px;top:176px;width:236px;font-size:8.8px;line-height:1.55;color:${C.text3}"></div>`);

  // ------------------------------------------------------------ Controls: Sequence (Left-Upper), Views & Display (Right-Lower below thrusters)
  const btn = {};
  panel(24, 240, 224, 68, 'SEQUENCE', '02');
  add(`<div style="position:absolute;left:34px;top:270px;width:204px;height:26px;border-radius:4px;background:${C.well}"></div>`);
  btn.cruise = add(`<div class="bt" style="left:37px;top:273px;width:99px;height:20px;border:none;background:transparent">JET CRUISE</div>`);
  btn.dive = add(`<div class="bt" style="left:136px;top:273px;width:99px;height:20px;border:none;background:transparent">HADAL DIVE</div>`);

  const btnRow = (keys, labels, x0, y, wmax = 224) => {
    let x = x0;
    let yy = y;
    for (const k of keys) {
      const w = Math.round(labels[k].length * 6.5 + 16);
      if (x + w > x0 + wmax) {
        x = x0;
        yy += 26;
      }
      btn[k] = add(`<div class="bt" style="left:${x}px;top:${yy}px;width:${w}px;height:20px">${labels[k]}</div>`);
      x += w + 4;
    }
  };
  panel(1332, 536, 244, 88, 'CAMERA VIEWS', '03');
  btnRow(VIEWS, VIEW_LABEL, 1342, 566, 224);

  panel(1332, 634, 244, 88, 'DISPLAY MODES', '04');
  btnRow(DISPLAY, DISPLAY_LABEL, 1342, 664, 224);

  // ------------------------------------------------------------ Bottom-Left: FRONT VIEW & Propulsion Telemetry
  panel(24, 738, 286, 144, 'FRONT VIEW & TELEMETRY', '05');
  const frontSvg = add(`<svg style="position:absolute;left:34px;top:764px" width="112" height="110"></svg>`);
  const bars = ['THRUST', 'BALLAST', 'RIGIDITY'].map((n, i) => {
    const y = 772 + i * 32;
    add(`<div class="sm" style="position:absolute;left:154px;top:${y}px;font-size:8px">${n}</div>`);
    add(`<div style="position:absolute;left:154px;top:${y + 14}px;width:92px;height:4px;background:${C.trackSoft};border-radius:2px"></div>`);
    const f = add(`<div style="position:absolute;left:154px;top:${y + 14}px;height:4px;background:${C.or};border-radius:2px"></div>`);
    const v = add(`<div class="mo" style="position:absolute;right:${1600 - 298}px;top:${y - 1}px;font-size:9.8px;font-weight:700"></div>`);
    return {f, v};
  });

  // ------------------------------------------------------------ Bottom-Center: ENVIRONMENTAL DATA & Operation Scrubber
  panel(322, 738, 676, 144, 'ENVIRONMENTAL DATA & OPERATION TIMELINE', '06');
  const envLabels = ['PRESSURE', 'TEMPERATURE', 'SALINITY', 'SIGNAL'].map((k, i) => {
    const y = 768 + i * 16;
    add(`<div class="sm" style="position:absolute;left:336px;top:${y}px;font-size:8.2px">${k}</div>`);
    const val = add(`<div class="mo" style="position:absolute;left:420px;top:${y - 1}px;font-size:9.4px;font-weight:600;color:${C.ink}"></div>`);
    return val;
  });
  const waveSvg = add(`<svg style="position:absolute;left:515px;top:758px" width="468" height="54"></svg>`);

  btn.play = add(`<div class="bt" style="left:336px;top:836px;width:36px;height:36px;border-radius:50%;border:none;background:${C.or};color:#fff;font-size:13px"></div>`);
  const opFrom = add(`<div class="sm" style="position:absolute;left:386px;top:832px;font-size:8px"></div>`);
  const opPhase = add(`<div class="mo" style="position:absolute;left:470px;width:320px;top:831px;text-align:center;font-size:8.8px;font-weight:700;letter-spacing:1.3px;color:${C.or}"></div>`);
  const opTo = add(`<div class="sm" style="position:absolute;left:792px;top:832px;font-size:8px"></div>`);

  const TL = {x: 386, w: 468};
  add(`<div style="position:absolute;left:${TL.x}px;top:854px;width:${TL.w}px;height:3px;background:${C.track};border-radius:2px"></div>`);
  const tlFill = add(`<div style="position:absolute;left:${TL.x}px;top:854px;height:3px;background:${C.or};border-radius:2px"></div>`);
  const tlKnob = add(`<div style="position:absolute;top:848px;width:14px;height:14px;margin-left:-7px;border-radius:50%;background:${C.knob};border:2px solid ${C.or};box-sizing:border-box"></div>`);
  const tlTime = add(`<div class="mo" style="position:absolute;left:386px;top:864px;font-size:8.6px;color:${C.mute};letter-spacing:1px"></div>`);

  add(`<div class="sm" style="position:absolute;left:872px;top:836px;font-size:8px">SPEED</div>`);
  const SP = {x: 872, w: 74};
  add(`<div style="position:absolute;left:${SP.x}px;top:854px;width:${SP.w}px;height:3px;background:${C.track};border-radius:2px"></div>`);
  const spFill = add(`<div style="position:absolute;left:${SP.x}px;top:854px;height:3px;background:${C.or};border-radius:2px"></div>`);
  const spKnob = add(`<div style="position:absolute;top:848px;width:14px;height:14px;margin-left:-7px;border-radius:50%;background:${C.knob};border:2px solid ${C.or};box-sizing:border-box"></div>`);
  const spVal = add(`<div class="mo" style="position:absolute;left:954px;top:848px;font-size:9.2px;font-weight:700"></div>`);

  // ------------------------------------------------------------ Bottom-Right: STRUCTURAL OVERVIEW (Exploded Spiral Shell)
  panel(1010, 738, 566, 144, 'STRUCTURAL OVERVIEW · SPIRAL SHELL SEPTA', '07');
  const structSvg = add(`<svg style="position:absolute;left:1022px;top:766px" width="542" height="106"></svg>`);

  // ------------------------------------------------------------ Callout Leaders & Operator Cursor
  const callSvg = add(`<svg data-callouts style="position:absolute;inset:0;overflow:visible" width="1600" height="900"></svg>`);
  const callG = add(`<div data-callouts style="position:absolute;inset:0"></div>`);
  const ring = add(`<div class="ring"></div>`);
  const cur = add(`<div class="cur"><svg width="22" height="22" viewBox="0 0 34 34"><path d="M4 3 L30 13.5 L17.5 17.5 L13.5 30 Z" fill="#111" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/></svg></div>`);

  const centre = (n) => {
    const r = n.getBoundingClientRect();
    return [r.left + r.width / 2, r.top + r.height / 2];
  };
  const spots = Object.fromEntries(Object.entries(btn).map(([k, n]) => [k, centre(n)]));
  const pointer = (c) => {
    if (!c) return;
    cur.style.display = c.x < 0 ? 'none' : 'block';
    cur.style.transform = `translate(${(c.x - 3).toFixed(2)}px, ${(c.y - 2).toFixed(2)}px) scale(${c.press ? 0.88 : 1})`;
    ring.style.left = `${c.ringX}px`;
    ring.style.top = `${c.ringY}px`;
    ring.style.opacity = String((c.ring || 0) * 0.85);
    ring.style.transform = `scale(${(0.35 + 0.9 * (1 - (c.ring || 0))).toFixed(3)})`;
  };
  const fmt = (s) => `00:${String(Math.floor(s)).padStart(2, '0')}`;

  return {
    spots,
    btn,
    root: ui,
    TL,
    SP,
    pointer,
    update(s) {
      const m = s.mech;
      const [title, sub, kind] = m.state;
      stChip.style.background = kind === 'ok' ? C.green : C.or;
      stTitle.textContent = title;
      stSub.textContent = sub;

      // 00 Orthographic Profile Schematic (18.5 m x 12.0 m)
      {
        const cx = 212;
        const cy = 78;
        let h = `<line x1="16" y1="12" x2="288" y2="12" stroke="${C.mute}" stroke-width="0.7"/>`;
        h += `<line x1="16" y1="8" x2="16" y2="16" stroke="${C.mute}" stroke-width="0.8"/><line x1="288" y1="8" x2="288" y2="16" stroke="${C.mute}" stroke-width="0.8"/>`;
        h += `<text x="142" y="9" font-size="7.5" fill="${C.ink}" font-family="JetBrains Mono">18.5 m</text>`;
        h += `<line x1="8" y1="22" x2="8" y2="132" stroke="${C.mute}" stroke-width="0.7"/>`;
        h += `<text x="3" y="80" font-size="7" fill="${C.ink}" font-family="JetBrains Mono" transform="rotate(-90 6 80)">12.0 m</text>`;
        // Spiral shell outline & radial septa lines
        let sp = '';
        for (let i = 0; i <= 48; i++) {
          const a = -2.6 + (i / 48) * 5.1;
          const r = 18 + 36 * Math.pow((a + 2.6) / 5.1, 0.72);
          const px = cx + r * Math.cos(a);
          const py = cy - r * Math.sin(a);
          sp += `${i ? 'L' : 'M'}${px.toFixed(1)} ${py.toFixed(1)}`;
        }
        h += `<path d="${sp}" fill="none" stroke="${C.ink}" stroke-width="1.1"/>`;
        for (let i = 0; i < 12; i++) {
          const a = -2.2 + (i / 11) * 4.4;
          const rOut = 20 + 34 * Math.pow((a + 2.6) / 5.1, 0.72);
          h += `<line x1="${(cx + 11 * Math.cos(a)).toFixed(1)}" y1="${(cy - 11 * Math.sin(a)).toFixed(1)}" x2="${(cx + rOut * Math.cos(a)).toFixed(1)}" y2="${(cy - rOut * Math.sin(a)).toFixed(1)}" stroke="${C.mute}" stroke-width="0.65"/>`;
        }
        h += `<circle cx="${cx}" cy="${cy}" r="11" fill="none" stroke="${C.or}" stroke-width="1.1"/>`;
        h += `<circle cx="${cx - 42}" cy="${cy - 4}" r="6" fill="none" stroke="${C.or}" stroke-width="1.2"/>`;
        // Animated tentacle lines sweeping left
        for (let t = 0; t < 7; t++) {
          const y0 = cy - 16 + t * 6.5;
          let tp = `M${cx - 48} ${y0.toFixed(1)}`;
          for (let k = 1; k <= 6; k++) {
            const u = k / 6;
            const tx = cx - 48 - u * 138;
            const ty = y0 + (t - 3) * u * 7 + Math.sin(m.wavePhase - u * 4 + t) * 4.5 * (0.3 + 0.7 * m.waveAmp);
            tp += ` L${tx.toFixed(1)} ${ty.toFixed(1)}`;
          }
          h += `<path d="${tp}" fill="none" stroke="${t === 3 ? C.or : C.ink}" stroke-width="${t === 3 ? 1.1 : 0.75}" opacity="0.82"/>`;
        }
        bpSvg.innerHTML = h;
      }

      // 01 Internal Section Circular Diagram & Active Subsystem Highlight
      {
        const cx = 59;
        const cy = 59;
        const rot = ((m.wavePhase * 28) % 360).toFixed(1);
        let h = `<circle cx="${cx}" cy="${cy}" r="50" fill="none" stroke="${C.ink}" stroke-width="1.1"/>`;
        h += `<circle cx="${cx}" cy="${cy}" r="36" fill="none" stroke="${C.mute}" stroke-width="0.7" stroke-dasharray="3 2"/>`;
        h += `<circle cx="${cx}" cy="${cy}" r="21" fill="none" stroke="${C.ink}" stroke-width="0.9"/>`;
        for (let i = 0; i < 9; i++) {
          const a = (i / 9) * Math.PI * 2;
          const fill = m.chamberFill[i] ?? 0.3;
          const rF = 21 + fill * 27;
          h += `<line x1="${(cx + 21 * Math.cos(a)).toFixed(1)}" y1="${(cy + 21 * Math.sin(a)).toFixed(1)}" x2="${(cx + 50 * Math.cos(a)).toFixed(1)}" y2="${(cy + 50 * Math.sin(a)).toFixed(1)}" stroke="${C.ink}" stroke-width="0.75"/>`;
          h += `<circle cx="${(cx + rF * Math.cos(a + 0.32)).toFixed(1)}" cy="${(cy + rF * Math.sin(a + 0.32)).toFixed(1)}" r="2.2" fill="${C.or}" opacity="0.8"/>`;
        }
        h += `<g transform="translate(${cx} ${cy}) rotate(${rot})"><circle r="10" fill="none" stroke="${C.or}" stroke-width="1.5"/><path d="M-14 0H14M0 -14V14" stroke="${C.or}" stroke-width="1"/></g>`;
        secSvg.innerHTML = h;

        const activeIdx = {core: 0, septa: 1, hero: 2, tentacles: 3, jets: 4, front: 3}[s.view] ?? 0;
        subRows.forEach((r, idx) => {
          const on = idx === activeIdx;
          r.dot.style.background = on ? C.or : C.faint;
          r.txt.style.color = on ? C.or : C.ink;
        });
        coreReadout.innerHTML = `TURBINE <b>${m.turbineRpm} RPM</b> &nbsp;·&nbsp; JET <b>${m.jetVel} M/S</b><br>CHAMBER TRIM <b>${Math.round(m.ballast * 100)}%</b> &nbsp;·&nbsp; SPEED <b>${m.knots} KT</b>`;
      }

      // 05 Front View Schematic & Gauges
      {
        const cx = 56;
        const cy = 54;
        let h = `<ellipse cx="${cx}" cy="${cy}" rx="28" ry="44" fill="none" stroke="${C.ink}" stroke-width="1.1"/>`;
        h += `<circle cx="${cx}" cy="${cy + 4}" r="14" fill="none" stroke="${C.or}" stroke-width="1.2"/>`;
        h += `<circle cx="${cx}" cy="${cy + 4}" r="6" fill="${C.or}" opacity="0.35"/>`;
        for (let i = 0; i < 14; i++) {
          const side = i < 7 ? -1 : 1;
          const row = (i % 7) - 3;
          const y0 = cy + 4 + row * 8;
          const x0 = cx + side * 16;
          const x1 = cx + side * (46 + Math.sin(m.wavePhase + i) * 5);
          const y1 = y0 + row * 3.5;
          h += `<path d="M${x0} ${y0} Q${cx + side * 32} ${y0 - 3} ${x1.toFixed(1)} ${y1.toFixed(1)}" fill="none" stroke="${C.ink}" stroke-width="0.85"/>`;
        }
        frontSvg.innerHTML = h;

        const vals = [
          [m.thrust / 184, `${m.thrust} kN`],
          [m.ballast, `${Math.round(m.ballast * 100)}%`],
          [(m.rigidity - 80) / 20, `${m.rigidity}%`],
        ];
        bars.forEach((b, i) => {
          b.f.style.width = `${(Math.min(1, Math.max(0.05, vals[i][0])) * 92).toFixed(1)}px`;
          b.v.textContent = vals[i][1];
        });
      }

      // 06 Environmental Data & Wave Chart
      {
        envLabels[0].textContent = `: ${m.pressure.toFixed(1)} MPa`;
        envLabels[1].textContent = `: ${m.temp.toFixed(1)} °C`;
        envLabels[2].textContent = `: ${m.salinity.toFixed(1)} PSU`;
        envLabels[3].textContent = `: Stable`;

        let wHtml = '';
        for (let c = 0; c < 5; c++) {
          let p = '';
          const amp = 8 + (c % 3) * 5 * (0.5 + 0.5 * m.stroke);
          const freq = 0.022 + c * 0.006;
          const ph = m.wavePhase * (0.8 + c * 0.25) + c * 1.1;
          for (let x = 0; x <= 460; x += 8) {
            const y = 27 + Math.sin(x * freq - ph) * amp * Math.sin((x / 460) * Math.PI);
            p += `${x === 0 ? 'M' : 'L'}${x} ${y.toFixed(1)}`;
          }
          wHtml += `<path d="${p}" fill="none" stroke="${c === 0 ? C.or : C.ink}" stroke-width="${c === 0 ? 1.2 : 0.65}" opacity="${c === 0 ? 0.9 : 0.38}"/>`;
        }
        waveSvg.innerHTML = wHtml;
      }

      // 07 Structural Overview (8 Exploded Spiral Shell Segments)
      {
        const ex = s.explode ?? 0;
        let sh = '';
        for (let i = 0; i < 8; i++) {
          const f = i / 7;
          const x = 38 + i * (58 + ex * 6.5);
          const y = 54;
          const r = 36 * (1 - 0.58 * f);
          const ri = r * 0.45;
          sh += `<g transform="translate(${x.toFixed(1)} ${y})">`;
          sh += `<path d="M0 ${-r.toFixed(1)} A${r.toFixed(1)} ${r.toFixed(1)} 0 0 1 ${(r * 0.85).toFixed(1)} ${r.toFixed(1)} L${(ri * 0.7).toFixed(1)} ${ri.toFixed(1)} A${ri.toFixed(1)} ${ri.toFixed(1)} 0 0 0 0 ${(-ri).toFixed(1)} Z" fill="${C.seg}" stroke="${C.ink}" stroke-width="1"/>`;
          sh += `<circle cx="2" cy="0" r="${(ri * 0.75).toFixed(1)}" fill="none" stroke="${i % 2 === 0 ? C.or : C.mute}" stroke-width="0.9"/>`;
          sh += `<text x="-6" y="${(r + 11).toFixed(1)}" font-size="7" fill="${C.mute}" font-family="JetBrains Mono">S0${i + 1}</text>`;
          sh += `</g>`;
        }
        structSvg.innerHTML = sh;
      }

      // Buttons & Timeline Scrubber
      const onBtn = (k, on) => {
        if (!btn[k]) return;
        btn[k].style.background = on ? C.or : C.btn;
        btn[k].style.color = on ? C.onBtn : C.ink;
        btn[k].style.borderColor = on ? C.or : C.faint;
      };
      for (const k of ['cruise', 'dive']) {
        const on = s.seq === k;
        btn[k].style.background = on ? C.or : 'transparent';
        btn[k].style.color = on ? C.onBtn : C.off;
        btn[k].style.borderRadius = '3px';
      }
      for (const k of VIEWS) onBtn(k, s.view === k);
      for (const k of DISPLAY) onBtn(k, !!s.display[k]);

      btn.play.innerHTML = s.paused ? '▶' : '❚❚';
      opFrom.textContent = s.from;
      opTo.textContent = s.to;
      opPhase.textContent = s.phase;
      const kx = TL.x + s.prog * TL.w;
      tlFill.style.width = `${(s.prog * TL.w).toFixed(1)}px`;
      tlKnob.style.left = `${kx.toFixed(1)}px`;
      tlTime.textContent = `${fmt(s.tau)} / ${fmt(s.dur)}`;

      const sk = SP.x + s.speedK * SP.w;
      spFill.style.width = `${(s.speedK * SP.w).toFixed(1)}px`;
      spKnob.style.left = `${sk.toFixed(1)}px`;
      spVal.textContent = `${s.speed.toFixed(1)}×`;

      // Callouts with leaders
      let lh = '';
      let ch = '';
      for (const c of s.callouts || []) {
        if (c.o < 0.02 || !c.at) continue;
        const [ax, ay] = c.at;
        const [lx, ly] = c.label;
        const right = lx > ax;
        const ex = right ? lx - 6 : lx + c.w + 6;
        lh += `<polyline points="${ax.toFixed(1)},${ay.toFixed(1)} ${ex.toFixed(1)},${(ly + 6).toFixed(1)}" fill="none" stroke="${C.or}" stroke-width="0.95" opacity="${c.o.toFixed(2)}"/><circle cx="${ax.toFixed(1)}" cy="${ay.toFixed(1)}" r="2.5" fill="${C.or}" opacity="${c.o.toFixed(2)}"/>`;
        ch += `<div class="call" style="left:${lx.toFixed(1)}px;top:${(ly - 1).toFixed(1)}px;opacity:${c.o.toFixed(2)}"><b><i></i>${c.name}</b><span>${c.sub}</span></div>`;
      }
      callSvg.innerHTML = lh;
      callG.innerHTML = ch;
      pointer(s.cursor);
    },
  };
}
