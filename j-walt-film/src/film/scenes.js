// Scenes. Each scene is draw(ctx, t, A, S) where t is absolute film time;
// scenes overlap to build transitions. Timings sit on the 120 BPM grid
// (beat = 0.5s, bar = 2s) -- see PRODUCTION.md for the beat map.
//
// One line runs through the film: it is drawn, becomes a joint of a real
// wall, the drawing becomes the photographed room, plates slide and close into
// their edges, an edge becomes the services spine, the spine becomes a seam,
// a plate closes into the horizon, a base line carries the gallery, a rule
// carries the numbers, and finally the wordmark rises out of the same line.

import { clamp, ease, seg, track, lerp } from '../engine/math.js';
import { frame, drawPhoto } from '../engine/camera.js';
import {
  lineDraw, pathDraw, ellipseDraw, smooth, maskedText, measure, logoPlace, drawLogo,
} from '../engine/draw.js';
import { W, H, C, G, T as TYPE, L, WEIGHT } from './theme.js';

const RIGHT = G.x(7);                    // left edge of the right-hand text column
const edgeLine = (ctx, a, b, alpha) => alpha > 0 && lineDraw(ctx, a, b, 1, { ...L.edge, alpha: L.edge.alpha * alpha });
const hline = (ctx, x0, x1, y, style = L.draw) => x1 - x0 > 0.5 && lineDraw(ctx, [x0, y], [x1, y], 1, style);
// a mask edge is visible only while it moves
const edgeAlpha = (p) => clamp(p / 0.08) * clamp((1 - p) / 0.25);

// Grid lines drawn top-down with a stagger (opening, and again before the end)
function grid(ctx, t, t0, fadeFrom, fadeTo, stagger = 0.05, dur = 0.9) {
  const fade = 1 - seg(t, fadeFrom, fadeTo);
  if (fade <= 0) return;
  G.lines().forEach((x, i) => {
    const p = seg(t, t0 + i * stagger, t0 + dur + i * stagger, ease.arch);
    lineDraw(ctx, [x + 0.5, 0], [x + 0.5, H], p, { ...L.grid, alpha: L.grid.alpha * fade });
  });
}

// Title block: name lines rise out of a rule (drawn by the caller), facts
// follow on eighth-notes below it. Every value is quoted from the source pack.
function titleBlock(ctx, t, b) {
  const { x, y, t0, t1 } = b;
  if (t < t0 || t > t1 + 0.1) return;
  const out = seg(t, t1 - 0.35, t1, ease.exit);
  (b.name ?? []).forEach((line, k, all) => {
    const ti = t0 + k * 0.1;
    maskedText(ctx, line, x, y - 28 - (all.length - 1 - k) * 62, TYPE.statement,
      seg(t, ti, ti + 0.7, ease.reveal) * (1 - out));
  });
  b.rows.forEach(([label, value], i) => {
    const ti = t0 + (b.name ? 0.25 : 0) + i * 0.125;
    const p = seg(t, ti, ti + 0.6, ease.reveal) * (1 - out);
    const yy = y + 62 + i * 42;
    maskedText(ctx, label, x, yy, TYPE.label, p, { rise: 16 });
    maskedText(ctx, value, x + 170, yy, TYPE.value, p, { rise: 24 });
  });
}

// ================================================================ 0-8  IDEA -> SPACE
// A line is drawn; FROM AN IDEA rises out of it; the line runs on into a panel
// joint of the real Heidelberg reception, which draws itself in construction
// lines; at 4.0s the photograph unfolds from the wall's corner line, under
// the drawing, registered; HEIDELBERG then rises out of the same line.

const RECEPTION = { x: G.x(5), y: 0, w: W - G.x(5), h: H };   // plate bleeds top/right/bottom
const recCam = {
  zoom: track([[4.0, 1.0], [8.4, 1.035]]),
  focus: track([[4.0, [0.5, 0.5]], [8.4, [0.54, 0.5]]]),   // horizontal only: joint-h2 stays on the rule
};

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

// The opening line ends exactly where joint-h2 begins on the rest frame; its
// height is the film's horizon, reused by every title block.
function openingLine(A) {
  const img = A.photos['heid-reception'];
  const T0 = frame(img, RECEPTION, { zoom: 1 });
  const j = A.lines.elements.find((e) => e.id === 'joint-h2');
  const end = T0.pt(...j.p0);
  const wall = A.lines.elements.find((e) => e.id === 'wall-left');
  const seam = (T0.pt(...wall.p0)[0] + T0.pt(...wall.p1)[0]) / 2;
  return { y: end[1], x1: end[0], seam };
}
const horizon = (A) => (A._open ??= openingLine(A)).y;

export function ideaToSpace(ctx, t, A, S) {
  const img = A.photos['heid-reception'];
  const O = (A._open ??= openingLine(A));
  const els = (A._els ??= schedule(A.lines.elements));
  const Y = O.y;

  grid(ctx, t, 0.9, 4.0, 4.8);

  // datum: a small red survey mark where the first line starts
  if (t < 4.3) {
    const s = 7 * seg(t, 0.3, 0.6, ease.reveal);
    ctx.save();
    ctx.globalAlpha = 1 - seg(t, 3.9, 4.3);
    ctx.fillStyle = C.red;
    ctx.fillRect(G.margin - s / 2, Y - s / 2, s, s);
    ctx.restore();
  }

  // photograph: unfolds from the wall's corner line at the 4.0s downbeat,
  // then slides out to the right (7.6-8.4) with window parallax
  const [cx, cy] = recCam.focus(t);
  const cam = { zoom: recCam.zoom(t), cx, cy };
  const Tn = frame(img, RECEPTION, cam);
  const open = seg(t, 4.0, 5.0, ease.arch);
  const mL = lerp(O.seam, RECEPTION.x, open);
  const mR = lerp(O.seam, W, open);
  const ghost = 1 - seg(t, 4.5, 5.7, ease.arch);
  // from 7.6s the craft plate covers it from the right; the old image drifts
  // left at 30% of the cover speed underneath (parallax push)
  const cover = coverEdge(t);
  if (open > 0 && cover > RECEPTION.x) {
    const push = -0.3 * (W - cover);
    drawPhoto(ctx, img, RECEPTION, { ...cam, px: push, free: cover < W },
      { clip: { x: mL, y: 0, w: Math.min(mR, cover) - mL, h: H }, stats: S });
    const ea = (1 - seg(t, 4.75, 5.0)) * (open < 1 ? 1 : 0);
    edgeLine(ctx, [mL, 0], [mL, H], ea);
    edgeLine(ctx, [mR, 0], [mR, H], ea);
  }

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

  // the first line: drawn 0.5-2.0s; from 7.6s the craft scene carries it
  const lineP = seg(t, 0.5, 2.0, ease.arch);
  const firstLine = (st) => t < 7.5 && lineDraw(ctx, [G.margin, Y], [O.x1, Y], lineP, st);

  const inP = seg(t, 0.95, 1.75, ease.reveal);
  const outP = seg(t, 3.55, 4.0, ease.exit);
  maskedText(ctx, 'FROM AN IDEA', G.margin, Y - 26, TYPE.statement, inP * (1 - outP));

  onPaper(firstLine);
  onPhoto(firstLine);
  if (t < 5.8) {
    for (const e of els) {
      const p = seg(t, e.t0, e.t1, ease.arch);
      if (p <= 0) continue;
      const w = WEIGHT[e.group];
      onPaper((st) => drawElement(ctx, e, Tn, p, { ...st, width: w.width, alpha: w.alpha }), RECEPTION.x);
      onPhoto((st) => drawElement(ctx, e, Tn, p, { ...st, width: w.width, alpha: st.alpha * (w.alpha / L.draw.alpha) }));
    }
  }

  titleBlock(ctx, t, {
    x: G.margin, y: Y, t0: 5.5, t1: 7.45, name: ['HEIDELBERG'],
    rows: [['LOCATION', 'DUBAI PRODUCTION CITY'], ['AREA', '5,600 SQ FT'], ['DURATION', '70 DAYS']],
  });
}

// ================================================================ 8-12  CRAFT (SNOC)
// The craft plate slides in over the reception from the right, inside the same
// window (it is shorter: the SNOC photo cannot fill 1080 lines under 1.25x).
// The only project whose source text describes its joinery ("Custom-built
// joinery elements were incorporated across workspaces, meeting tables, wall
// panels, shelving, and storage units", p11), so the craft title sits here.

const CRAFT = { x: RECEPTION.x, y: 0, w: RECEPTION.w, h: 900 };
const SHELF = { x: G.margin, y: 0, w: 466, h: 360 };
const coverEdge = (t) => lerp(W, CRAFT.x, seg(t, 7.5, 8.5, ease.arch));

export function craft(ctx, t, A, S) {
  const Y = horizon(A);
  const e = coverEdge(t);
  const close = seg(t, 11.7, 12.2, ease.arch);
  if (e < W && close < 1) {
    const rect = { ...CRAFT, x: e };
    const cam = { zoom: lerp(1, 1.03, seg(t, 8.4, 12.2, ease.drift)), cx: 0.5, cy: 0.5,
      px: -0.4 * (e - CRAFT.x), free: e > CRAFT.x };
    const x1 = e + CRAFT.w - close * CRAFT.w;
    drawPhoto(ctx, A.photos['snoc-boardroom'], rect, cam, { clip: { x: e, y: 0, w: x1 - e, h: CRAFT.h }, stats: S });
    edgeLine(ctx, [e, 0], [e, H], e > CRAFT.x + 0.5 ? 1 : 0);
    edgeLine(ctx, [x1, 0], [x1, CRAFT.h], clamp(close / 0.08));
  } else if (close >= 1 && t < 12.25) {
    edgeLine(ctx, [CRAFT.x, 0], [CRAFT.x, CRAFT.h], 1);   // handed to the services spine
  }

  // the horizon rule carries over from HEIDELBERG; at the end it runs into the plate edge
  if (t >= 7.5) hline(ctx, lerp(G.margin, CRAFT.x, seg(t, 11.45, 11.85, ease.arch)), CRAFT.x, Y);
  titleBlock(ctx, t, { x: G.margin, y: Y, t0: 8.55, t1: 11.7, name: ['CARPENTRY &', 'JOINERY'], rows: [] });
  titleBlock(ctx, t, {
    x: G.margin, y: Y, t0: 9.9, t1: 11.7,
    rows: [['PROJECT', 'SNOC'], ['LOCATION', 'SHARJAH'], ['AREA', '2,500 SQ FT'], ['DURATION', '50 DAYS']],
  });

  // shelving detail: base line, then built upward from it
  const base = seg(t, 9.3, 9.8, ease.arch) * (1 - seg(t, 11.4, 11.8, ease.arch));
  const bx = SHELF.x + SHELF.w / 2;
  if (base > 0) hline(ctx, bx - (SHELF.w / 2) * base, bx + (SHELF.w / 2) * base, SHELF.h);
  const up = seg(t, 9.6, 10.3, ease.reveal) * (1 - seg(t, 11.3, 11.7, ease.exit));
  if (up > 0) {
    const top = SHELF.h * (1 - up);
    drawPhoto(ctx, A.photos['snoc-shelving'], SHELF, { zoom: 1.0, cx: 0.5, cy: lerp(0.5, 0.44, seg(t, 9.6, 11.8, ease.drift)) },
      { clip: { x: SHELF.x, y: top, w: SHELF.w, h: SHELF.h - top }, stats: S });
    edgeLine(ctx, [SHELF.x, top], [SHELF.x + SHELF.w, top], up < 1 ? 1 - up : 0);
  }
}

// ================================================================ 12-16  SERVICES
// A standalone schedule, deliberately not attached to any photograph: the
// source lists the services but does not say which project used which.

const SPINE_X = G.x(2) - 24;
const ROWS = [330, 540, 750];
const SERVICES = ['MEP', 'CIVIL WORKS', 'TURN KEY INTERIOR FIT OUT SOLUTIONS'];
const SERVICE_TYPE = { size: 56, weight: 300, track: 0.1, color: C.ink };
const CORYS = { x: 0, y: 0, w: G.xr(5) - 12, h: H };        // 0..840
const SEAM = CORYS.w / 2;

export function services(ctx, t) {
  // spine: the craft plate's closing edge travels left and settles as the
  // schedule's vertical; at the end it becomes the next plate's seam
  const s = seg(t, 12.15, 12.55, ease.arch);
  const e = seg(t, 15.3, 15.85, ease.arch);
  const x = lerp(lerp(CRAFT.x, SPINE_X, s), SEAM, e);
  const y0 = lerp(lerp(0, 250, s), 0, e);
  const y1 = lerp(lerp(CRAFT.h, 830, s), H, e);
  if (t >= 12.2 && t < 15.85) lineDraw(ctx, [x, y0], [x, y1], 1, L.draw);

  maskedText(ctx, 'SERVICES', G.x(2), 214, TYPE.label, seg(t, 12.35, 12.95, ease.reveal) * (1 - seg(t, 14.95, 15.25, ease.exit)));

  ROWS.forEach((y, i) => {
    const tr = 12.4 + i * 0.5;
    const grow = seg(t, tr, tr + 0.6, ease.arch) * (1 - seg(t, 15.05 + i * 0.05, 15.4 + i * 0.05, ease.arch));
    const xEnd = lerp(SPINE_X, G.xr(11), grow);
    if (grow > 0) {
      hline(ctx, SPINE_X, xEnd, y);
      // scale-bar ticks on the grid lines the rule has passed
      for (const gx of G.lines()) {
        if (gx > SPINE_X + 40 && gx <= xEnd) lineDraw(ctx, [gx + 0.5, y], [gx + 0.5, y + 8], 1, { ...L.dim, alpha: 0.35 });
      }
    }
    const tp = seg(t, tr + 0.15, tr + 0.85, ease.reveal) * (1 - seg(t, 14.95 + i * 0.06, 15.25 + i * 0.06, ease.exit));
    maskedText(ctx, SERVICES[i], G.x(2), y - 26, SERVICE_TYPE, tp);
    maskedText(ctx, `0${i + 1}`, SPINE_X - 24, y - 28, TYPE.index, tp, { align: 'right', rise: 16 });
  });
}

// ================================================================ 16-20  PROJECTS
// CORYS opens from the seam; closes into the horizon; OMODA | JAECOO opens
// from the same horizon line; closes down into its base line.

const OMODA = { x: W - 1121, y: 180, w: 1121, h: 630 };

export function projects(ctx, t, A, S) {
  const Y = horizon(A);

  // CORYS: opens both ways from the seam, closes vertically into the horizon
  const o = seg(t, 15.8, 16.5, ease.arch);
  const c = seg(t, 17.75, 18.15, ease.arch);
  if (o > 0 && c < 1) {
    const a = SEAM - SEAM * o, b = SEAM + SEAM * o;
    const top = Y * c, bot = H - (H - Y) * c;
    drawPhoto(ctx, A.photos['corys-openplan'], CORYS, { zoom: lerp(1, 1.025, seg(t, 15.8, 18.2, ease.drift)) },
      { clip: { x: a, y: top, w: b - a, h: bot - top }, stats: S });
    edgeLine(ctx, [a, 0], [a, H], o < 1 ? edgeAlpha(o) : 0);
    edgeLine(ctx, [b, 0], [b, H], o < 1 ? edgeAlpha(o) : 0);
    edgeLine(ctx, [a, top], [b, top], clamp(c / 0.08));
    edgeLine(ctx, [a, bot], [b, bot], clamp(c / 0.08));
  }

  // OMODA | JAECOO: opens from the horizon, closes down into its base line
  const o2 = seg(t, 18.0, 18.6, ease.arch);
  const c2 = seg(t, 19.6, 20.0, ease.arch);
  if (o2 > 0 && c2 < 1) {
    const top = lerp(Y - (Y - OMODA.y) * o2, OMODA.y + OMODA.h, c2);
    const bot = Y + (OMODA.y + OMODA.h - Y) * o2;
    drawPhoto(ctx, A.photos['omoda-reception'], OMODA,
      { zoom: lerp(1, 1.03, seg(t, 18.0, 20.0, ease.drift)), cx: lerp(0.47, 0.53, seg(t, 18.0, 20.0, ease.drift)), cy: 0.5 },
      { clip: { x: OMODA.x, y: top, w: OMODA.w, h: bot - top }, stats: S });
    edgeLine(ctx, [OMODA.x, top], [W, top], o2 < 1 ? edgeAlpha(o2) : clamp(c2 / 0.08));
    edgeLine(ctx, [OMODA.x, bot], [W, bot], o2 < 1 ? edgeAlpha(o2) : 0);
  }

  // the horizon rule: CORYS block on the right, sweeps across the frame to
  // carry the change, settles under the OMODA block on the left
  const r1 = seg(t, 16.3, 16.8, ease.arch);
  const sweep = seg(t, 17.5, 17.85, ease.arch);
  const settle = seg(t, 18.1, 18.6, ease.arch);
  const exit = seg(t, 19.45, 19.85, ease.arch);
  let x0 = lerp(RIGHT, 0, sweep), x1 = lerp(RIGHT, G.xr(11), r1);
  x0 = lerp(x0, G.margin, settle);
  x1 = lerp(x1, OMODA.x - 24, settle);
  x1 = lerp(x1, G.margin, exit);
  if (t >= 16.3) hline(ctx, x0, x1, Y);

  titleBlock(ctx, t, {
    x: RIGHT, y: Y, t0: 16.45, t1: 17.6, name: ['CORYS'],
    rows: [['LOCATION', 'DUBAI INVESTMENT PARK'], ['AREA', '25,000 SQ FT'], ['DURATION', '80 DAYS']],
  });
  titleBlock(ctx, t, {
    x: G.margin, y: Y, t0: 18.35, t1: 19.55, name: ['OMODA | JAECOO'],
    rows: [['LOCATION', 'DUBAI MARINA'], ['AREA', '3,500 SQ FT'], ['DURATION', '60 DAYS']],
  });
}

// ================================================================ 20-22  GALLERY
// No words: three plates built up on one ground line, then taken down again.

const BASE = 800;
const GALLERY = [
  { img: 'heid-stained', cols: [0, 4], at: 20.15, cam: (t) => ({ zoom: 1.0, cx: lerp(0.44, 0.5, seg(t, 20.1, 22, ease.drift)), cy: 0.5 }) },
  { img: 'heid-curved', cols: [5, 7], at: 20.3, cam: () => ({ zoom: 1.0, cx: 0.5, cy: 0.5 }) },
  { img: 'heid-corridor', cols: [8, 11], at: 20.45, cam: (t) => ({ zoom: lerp(1.0, 1.03, seg(t, 20.4, 22, ease.drift)), cx: 0.44, cy: 0.5 }) },
];

export function gallery(ctx, t, A, S) {
  // OMODA's base line (y 810) widens into the ground line
  const m = seg(t, 19.95, 20.35, ease.arch);
  const toRule = seg(t, 21.95, 22.45, ease.arch);
  const y = lerp(lerp(OMODA.y + OMODA.h, BASE, m), 640, toRule);
  const x0 = lerp(OMODA.x, G.margin, m);
  const x1 = lerp(lerp(W, G.xr(11), m), RULE_END, toRule);
  if (t >= 19.95 && t < 22.5) hline(ctx, x0, x1, y);

  GALLERY.forEach((g, i) => {
    const r = { x: G.x(g.cols[0]), y: 0, w: G.xr(g.cols[1]) - G.x(g.cols[0]), h: BASE };
    const up = seg(t, g.at, g.at + 0.6, ease.reveal) * (1 - seg(t, 21.55 + i * 0.1, 21.95 + i * 0.1, ease.exit));
    if (up <= 0) return;
    const top = BASE * (1 - up);
    drawPhoto(ctx, A.photos[g.img], r, g.cam(t), { clip: { x: r.x, y: top, w: r.w, h: BASE - top }, stats: S });
    edgeLine(ctx, [r.x, top], [r.x + r.w, top], up < 1 ? 1 - up : 0);
  });
}

// ================================================================ 22-26  SCALE
// Only the two milestones whose labels are printed in the source (p3).

const RY = 640;
const NUMERAL = { size: 210, weight: 300, track: -0.01, color: C.ink };
const STAT_LABEL = { size: 26, weight: 400, track: 0.16, color: C.ink };
const RULE_END = 1320;

function brandGeom(A) {
  const w = 620;
  const axis = W / 2;
  const P = logoPlace(A.logo, axis - w / 2 + 0.05 * w, 430, w);   // italic: visual axis ~5% left of bbox centre
  return { w, axis, P, base: 430 + P.h, half: w * 0.62 };
}

export function scale(ctx, t, A) {
  grid(ctx, t, 22.1, 25.3, 26.0, 0.025, 0.6);   // complete before the first numeral lands
  const B = (A._brand ??= brandGeom(A));
  const travel = seg(t, 25.45, 26.3, ease.arch);
  const x0 = lerp(G.margin, B.axis - B.half, travel);
  const x1 = lerp(RULE_END, B.axis + B.half, travel);
  const y = lerp(RY, B.base + 0.75, travel);
  if (t >= 22.45 && t < 26.35) hline(ctx, x0, x1, y);

  const stat = (num, label, a, b) => {
    const p = seg(t, a, a + 0.75, ease.reveal) * (1 - seg(t, b, b + 0.35, ease.exit));
    maskedText(ctx, num, G.margin - 8, RY - 40, NUMERAL, p);
    const q = seg(t, a + 0.2, a + 0.8, ease.reveal) * (1 - seg(t, b, b + 0.35, ease.exit));
    maskedText(ctx, label, RULE_END, RY - 24, STAT_LABEL, q, { align: 'right', rise: 30 });
  };
  stat('310+', 'HAPPY CLIENTS', 22.45, 23.85);
  stat('500+', 'COMPLETED PROJECTS', 24.0, 25.2);
}

// ================================================================ 26-30  BRAND
// The rule arrives at the centre; the wordmark rises out of it; the descriptor
// and tagline follow; then nothing moves.

export function brand(ctx, t, A) {
  const B = (A._brand ??= brandGeom(A));
  const lineOut = seg(t, 27.05, 27.6, ease.arch);
  const half = B.half * (1 - lineOut);
  if (t >= 26.3 && half > 0.5) hline(ctx, B.axis - half, B.axis + half, B.base + 0.75);

  const rise = seg(t, 26.35, 27.15, ease.reveal);
  if (rise > 0) drawLogo(ctx, A.logo, B.P, C.red, { clip: { x: 0, y: 0, w: W, h: B.base }, rise: (1 - rise) * (B.P.h + 6) });

  descriptor(ctx, B.axis - 0.4275 * B.w, B.axis + 0.4275 * B.w, B.base + 46, seg(t, 27.15, 27.8, ease.reveal));
  maskedText(ctx, 'REDEFINING SPACES', B.axis, B.base + 128, TYPE.tagline, seg(t, 27.7, 28.35, ease.reveal), { align: 'center' });
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
      lineDraw(ctx, [sx, y + 2], [sx, y - st.size * 0.73 - 2], p, { color: C.graphite, width: 1, alpha: 0.9 });
      x += gap;
    }
  });
}

export const SCENES = [
  { name: 'idea-to-space', t0: 0, t1: 8.55, draw: ideaToSpace },
  { name: 'craft', t0: 7.5, t1: 12.3, draw: craft },
  { name: 'services', t0: 12.2, t1: 16.1, draw: services },
  { name: 'projects', t0: 15.75, t1: 20.1, draw: projects },
  { name: 'gallery', t0: 19.95, t1: 22.5, draw: gallery },
  { name: 'scale', t0: 22.2, t1: 26.4, draw: scale },
  { name: 'brand', t0: 26.3, t1: 30, draw: brand },
];
