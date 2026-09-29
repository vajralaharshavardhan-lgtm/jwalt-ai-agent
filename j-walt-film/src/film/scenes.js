// Scenes. Each scene is draw(ctx, t, A, S) where t is absolute film time;
// scenes overlap to build transitions. Timings are on the 120 BPM grid
// (beat = 0.5s, bar = 2s) -- see analysis/beat-map.md.

import { clamp, ease, seg, track, lerp, progress } from '../engine/math.js';
import { frame, drawPhoto } from '../engine/camera.js';
import {
  lineDraw, lineFromCentre, pathDraw, ellipseDraw, dimensionLine, smooth,
  maskedText, measure, logoPlace, drawLogo,
} from '../engine/draw.js';
import { W, H, C, G, T as TYPE, L, WEIGHT } from './theme.js';

// ================================================================ 1-2  IDEA -> SPACE
// A line is drawn; FROM AN IDEA rises out of it; the line runs on into a panel
// joint of the real Heidelberg reception, which draws itself in construction
// lines; at 4.0s the photograph unfolds from the wall's corner line, under
// the drawing, perfectly registered; HEIDELBERG then rises out of the same line.

const RECEPTION = { x: G.x(5), y: 0, w: W - G.x(5), h: H };   // plate bleeds top/right/bottom
const recCam = {
  zoom: track([[4.0, 1.0], [8.4, 1.035]]),
  focus: track([[4.0, [0.5, 0.5]], [8.4, [0.54, 0.5]]]),   // horizontal only: joint-h2 stays on the rule
};
const receptionCamera = (t) => {
  const [cx, cy] = recCam.focus(t);
  return { zoom: recCam.zoom(t), cx, cy };
};

// Drawing schedule: groups start on half-beats after the 2.0s downbeat.
const GROUP_START = { structure: 2.0, panels: 2.3, desk: 2.65, rings: 3.0 };
const DUR = { line: 0.7, polyline: 0.9, ellipse: 1.0 };
function schedule(elements) {
  const count = {};
  return elements.map((e) => {
    const k = (count[e.group] = (count[e.group] ?? -1) + 1);
    const t0 = e.id === 'joint-h2' ? 2.0 : GROUP_START[e.group] + k * 0.07;
    return { ...e, t0, t1: t0 + (e.id === 'joint-h2' ? 0.6 : DUR[e.type]) };
  });
}

function drawElement(ctx, e, T, p, style) {
  if (e.type === 'line') {
    lineDraw(ctx, T.pt(...e.p0), T.pt(...e.p1), p, style);
  } else if (e.type === 'polyline') {
    e._smooth ??= smooth(e.points);
    pathDraw(ctx, e._smooth.map((q) => T.pt(...q)), p, style);
  } else if (e.type === 'ellipse') {
    ellipseDraw(ctx, T.pt(e.cx, e.cy), e.rx * T.s, e.ry * T.s, e.rot, p, style, Math.PI * 0.85);
  }
}

// The opening line ends exactly where joint-h2 begins on the rest frame.
function openingLine(A) {
  const img = A.photos['heid-reception'];
  const T0 = frame(img, RECEPTION, { zoom: 1 });
  const j = A.lines.elements.find((e) => e.id === 'joint-h2');
  const end = T0.pt(...j.p0);
  const wall = A.lines.elements.find((e) => e.id === 'wall-left');
  const seam = (T0.pt(...wall.p0)[0] + T0.pt(...wall.p1)[0]) / 2;
  return { y: end[1], x1: end[0], seam };
}

export function ideaToSpace(ctx, t, A, S) {
  if (t >= 8.6) return;
  const img = A.photos['heid-reception'];
  const O = (A._open ??= openingLine(A));
  const els = (A._els ??= schedule(A.lines.elements));
  const Y = O.y;

  // column grid: faint, drawn top-down, gone once the space is revealed
  const gridFade = 1 - seg(t, 4.0, 4.8);
  if (gridFade > 0) {
    G.lines().forEach((x, i) => {
      const p = seg(t, 0.9 + i * 0.05, 1.8 + i * 0.05, ease.arch);
      lineDraw(ctx, [x + 0.5, 0], [x + 0.5, H], p, { ...L.grid, alpha: L.grid.alpha * gridFade });
    });
  }

  // datum: a small red survey mark where the first line starts
  const datum = seg(t, 0.3, 0.6, ease.reveal) * (1 - seg(t, 3.9, 4.3));
  if (datum > 0) {
    const s = 7 * seg(t, 0.3, 0.6, ease.reveal);
    ctx.save();
    ctx.globalAlpha = 1 - seg(t, 3.9, 4.3);
    ctx.fillStyle = C.red;
    ctx.fillRect(G.margin - s / 2, Y - s / 2, s, s);
    ctx.restore();
  }

  // photograph: unfolds from the wall's corner line at the 4.0s downbeat
  const cam = receptionCamera(t);
  const Tn = frame(img, RECEPTION, cam);
  const open = seg(t, 4.0, 5.0, ease.arch);
  const mL = lerp(O.seam, RECEPTION.x, open);
  const mR = lerp(O.seam, W, open);
  const ghost = 1 - seg(t, 4.5, 5.7, ease.arch);
  const onPaper = (fn, minX = 0) => {
    ctx.save();
    ctx.beginPath();
    const a = open > 0 ? mL : O.seam, b = open > 0 ? mR : O.seam;
    if (a > minX) ctx.rect(minX, 0, a - minX, H);
    ctx.rect(b, 0, W - b, H);
    ctx.clip();
    fn(L.draw);
    ctx.restore();
  };
  const onPhoto = (fn) => {
    if (open <= 0 || ghost <= 0) return;
    ctx.save();
    ctx.beginPath();
    ctx.rect(mL, 0, mR - mL, H);
    ctx.clip();
    fn({ ...L.ghost, alpha: L.ghost.alpha * ghost });
    ctx.restore();
  };

  // the first line: 0.5 -> 2.0s, stays as the horizon of the opening
  const lineP = seg(t, 0.5, 2.0, ease.arch);
  const firstLine = (st) => lineDraw(ctx, [G.margin, Y], [O.x1, Y], lineP, st);

  // FROM AN IDEA rises out of the line, sinks back before the reveal
  const inP = seg(t, 0.95, 1.75, ease.reveal);
  const outP = seg(t, 3.55, 4.0, ease.exit);
  maskedText(ctx, 'FROM AN IDEA', G.margin, Y - 26, TYPE.statement, inP * (1 - outP));
  if (open > 0) {
    drawPhoto(ctx, img, RECEPTION, cam, { clip: { x: mL, y: 0, w: mR - mL, h: H }, stats: S });
    const edgeA = (1 - seg(t, 4.75, 5.0)) * L.edge.alpha;
    if (edgeA > 0) {
      lineDraw(ctx, [mL, 0], [mL, H], 1, { ...L.edge, alpha: edgeA });
      lineDraw(ctx, [mR, 0], [mR, H], 1, { ...L.edge, alpha: edgeA });
    }
  }

  // construction lines (and the first line): full strength on paper,
  // ghosting out over the photograph they have become
  onPaper(firstLine);
  onPhoto(firstLine);
  for (const e of els) {
    const p = seg(t, e.t0, e.t1, ease.arch);
    if (p <= 0) continue;
    const w = WEIGHT[e.group];
    onPaper((st) => drawElement(ctx, e, Tn, p, { ...st, width: w.width, alpha: w.alpha }), RECEPTION.x);
    onPhoto((st) => drawElement(ctx, e, Tn, p, { ...st, width: w.width, alpha: st.alpha * (w.alpha / L.draw.alpha) }));
  }

  // HEIDELBERG title block, built on the same line
  projectBlock(ctx, t, {
    x: G.margin, y: Y, t0: 5.5, t1: 7.7,
    name: 'HEIDELBERG',
    rows: [['LOCATION', 'DUBAI PRODUCTION CITY'], ['AREA', '5,600 SQ FT'], ['DURATION', '70 DAYS']],
  });
}

// Project title block: the name rises out of a rule, in the same voice as the
// opening statement; the facts follow on eighth-notes below the rule.
// Every value is quoted from the source pack (see analysis/catalogue.md).
export function projectBlock(ctx, t, b) {
  const { x, y, t0, t1 } = b;
  if (t < t0 || t > t1 + 0.5) return;
  const out = seg(t, t1 - 0.35, t1, ease.exit);
  maskedText(ctx, b.name, x, y - 28, TYPE.statement, seg(t, t0, t0 + 0.7, ease.reveal) * (1 - out));
  b.rows.forEach(([label, value], i) => {
    const ti = t0 + 0.25 + i * 0.125;
    const p = seg(t, ti, ti + 0.6, ease.reveal) * (1 - out);
    const yy = y + 62 + i * 42;
    maskedText(ctx, label, x, yy, TYPE.label, p, { rise: 16 });
    maskedText(ctx, value, x + 170, yy, TYPE.value, p, { rise: 24 });
  });
}

// ================================================================ 4  BUILD
// Three plates are drawn as outlines on the grid, then built up from their
// base lines on consecutive beats; each carries one verified service title.

const BASE = 800;   // plates bleed off the top edge and stand on this line
const BUILD = [
  { img: 'heid-corridor', cols: [0, 4], title: ['MEP'], idx: '01',
    cam: (t) => ({ zoom: lerp(1.0, 1.035, seg(t, 12.4, 16.2, ease.drift)), cx: 0.44, cy: 0.5 }) },
  { img: 'heid2-hall', cols: [5, 7], title: ['CIVIL WORKS'], idx: '02',
    cam: (t) => ({ zoom: 1.0, cx: lerp(0.36, 0.33, seg(t, 12.9, 16.2, ease.drift)), cy: 0.5 }) },
  { img: 'heid-curved', cols: [8, 11], title: ['TURN KEY INTERIOR', 'FIT OUT SOLUTIONS'], idx: '03',
    cam: (t) => ({ zoom: lerp(1.0, 1.02, seg(t, 13.4, 16.2, ease.drift)), cx: 0.5, cy: 0.5 }) },
];

export function build(ctx, t, A, S) {
  if (t < 11.9 || t > 16.4) return;
  BUILD.forEach((b, i) => {
    const r = { x: G.x(b.cols[0]), y: 0, w: G.xr(b.cols[1]) - G.x(b.cols[0]), h: BASE };
    const beat = 12.0 + i * 0.5;
    // 1. base line from its centre, then the two sides rise
    const o = progress(t, beat - 0.1, beat + 0.6);
    const fade = 1 - seg(t, beat + 0.9, beat + 1.3);
    if (fade > 0) {
      const st = { ...L.draw, alpha: L.draw.alpha * fade };
      lineFromCentre(ctx, [r.x, BASE], [r.x + r.w, BASE], ease.arch(clamp(o / 0.45)), st);
      const up = ease.arch(clamp((o - 0.35) / 0.65));
      lineDraw(ctx, [r.x, BASE], [r.x, 0], up, st);
      lineDraw(ctx, [r.x + r.w, BASE], [r.x + r.w, 0], up, st);
    }
    // 2. the photograph is built up from the base line
    const up = seg(t, beat + 0.4, beat + 1.0, ease.reveal);
    if (up > 0) {
      const top = BASE * (1 - up);
      drawPhoto(ctx, A.photos[b.img], r, b.cam(t), { clip: { x: r.x, y: top, w: r.w, h: BASE - top }, stats: S });
      if (up < 1) lineDraw(ctx, [r.x, top], [r.x + r.w, top], 1, { ...L.edge, alpha: L.edge.alpha * (1 - up) });
    }
    // 3. service title (verified terminology, source pack p03)
    const tt = seg(t, beat + 0.7, beat + 1.3, ease.reveal);
    b.title.forEach((line, k) => maskedText(ctx, line, r.x, BASE + 112 + k * 40, TYPE.service, tt));
    // 4. dimension string just under the plates, one span each, labelled with its index
    dimensionLine(ctx, r.x, r.x + r.w, BASE + 44, seg(t, 12.1 + i * 0.12, 12.9 + i * 0.12, ease.arch),
      L.dim, b.idx, TYPE.index);
  });
}

// ================================================================ 7  BRAND
// Everything simplifies to one line; the J-WALT wordmark rises out of it;
// the descriptor and the tagline follow; then nothing moves.

export function brand(ctx, t, A) {
  if (t < 25.9) return;
  const logo = A.logo;
  const w = 620;
  const place = logoPlace(logo, 0, 0, w);
  // italic wordmark: its visual axis sits ~5% left of its bounding-box centre
  const axis = W / 2;
  const x = axis - w / 2 + 0.05 * w;
  const top = 430;
  const P = logoPlace(logo, x, top, w);
  const base = top + P.h;

  // the line: grows from the axis, carries the wordmark, then withdraws
  const lineIn = seg(t, 25.9, 26.45, ease.arch);
  const lineOut = seg(t, 27.05, 27.6, ease.arch);
  const half = (w * 0.62) * lineIn * (1 - lineOut);
  if (half > 0.5) lineDraw(ctx, [axis - half, base + 0.75], [axis + half, base + 0.75], 1, L.draw);

  // wordmark rises out of the line
  const rise = seg(t, 26.35, 27.15, ease.reveal);
  if (rise > 0) {
    drawLogo(ctx, logo, P, C.red, { clip: { x: 0, y: 0, w: W, h: base }, rise: (1 - rise) * (P.h + 6) });
  }

  // descriptor, locked to the wordmark like the source lockup (85% of its width)
  const dp = seg(t, 27.15, 27.8, ease.reveal);
  descriptor(ctx, axis - 0.4275 * w, axis + 0.4275 * w, base + 46, dp);

  // tagline
  maskedText(ctx, 'REDEFINING SPACES', axis, base + 128, TYPE.tagline, seg(t, 27.7, 28.35, ease.reveal), { align: 'center' });
}

function descriptor(ctx, x0, x1, y, p) {
  if (p <= 0) return;
  const st = TYPE.descriptor;
  const words = ['INTERIORS', 'MEP', 'CONTRACTING'];
  const ws = words.map((s) => measure(ctx, s, st));
  const gap = (x1 - x0 - ws.reduce((a, b) => a + b, 0)) / 2;
  let x = x0;
  words.forEach((s, i) => {
    maskedText(ctx, s, x, y, st, p, { rise: 18 });
    x += ws[i];
    if (i < 2) {
      const sx = Math.round(x + gap / 2) + 0.5;
      const cap = st.size * 0.73;
      lineDraw(ctx, [sx, y + 2], [sx, y - cap - 2], p, { color: C.graphite, width: 1, alpha: 0.9 });
      x += gap;
    }
  });
}

export const SCENES = [
  { name: 'idea-to-space', t0: 0, t1: 8.6, draw: ideaToSpace },
  { name: 'build', t0: 11.9, t1: 16.4, draw: build },
  { name: 'brand', t0: 25.9, t1: 30, draw: brand },
];
