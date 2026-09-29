/**
 * Parametric vegetable library for the portfolio montage.
 *
 * Every crop outline is sampled to the same number of points, starting at
 * the stem end and running clockwise, so any crop can morph point-for-point
 * into any other. Coordinates are unit-scale (longest side ≈ 1), centred.
 */
import {produce} from '../styles/brand';
import {type Pt, add, linePath, perp, pt, quad, rand, resample, scale, smoothPath, sub, normalize} from '../utils/geometry';
import {smoothstep} from '../utils/easing';

export const OUTLINE_POINTS = 180;

export type CropDetail = {d: string; stroke?: string; fill?: string; width?: number; opacity?: number};

export type Crop = {
  id: string;
  name: string;
  slot: string;
  outline: Pt[];
  /** [highlight, body, shadow] */
  colors: readonly string[];
  /** Surface details, clipped to the outline. */
  details: CropDetail[];
  /** Calyx / stem drawn on top, not clipped. */
  cap: CropDetail[];
  /** Display rotation in degrees. */
  angle: number;
};

const signedArea = (pts: Pt[]) => {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    const q = pts[(i + 1) % pts.length];
    a += p.x * q.y - q.x * p.y;
  }
  return a / 2;
};

/** Normalise: clockwise (screen), N points, starting nearest `stem`. */
const finish = (raw: Pt[], stem: Pt): Pt[] => {
  let pts = resample(raw, OUTLINE_POINTS, true);
  if (signedArea(pts) < 0) {
    pts = pts.reverse();
  }
  let best = 0;
  let bd = Infinity;
  pts.forEach((p, i) => {
    const d = (p.x - stem.x) ** 2 + (p.y - stem.y) ** 2;
    if (d < bd) {
      bd = d;
      best = i;
    }
  });
  return [...pts.slice(best), ...pts.slice(0, best)];
};

type Spine = {a: Pt; c: Pt; b: Pt};
const spinePt = (s: Spine, t: number) => quad(s.a, s.c, s.b, t);
const spineNormal = (s: Spine, t: number) => {
  const e = 0.001;
  const d = normalize(sub(spinePt(s, Math.min(1, t + e)), spinePt(s, Math.max(0, t - e))));
  return perp(d);
};

/** Closed outline around a curved spine with half-width w(t). */
const podOutline = (s: Spine, w: (t: number) => number, n = 120): Pt[] => {
  const left: Pt[] = [];
  const right: Pt[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const p = spinePt(s, t);
    const nm = spineNormal(s, t);
    left.push(add(p, scale(nm, w(t))));
    right.push(add(p, scale(nm, -w(t))));
  }
  return [...left, ...right.reverse()];
};

/** A line running along the spine at lateral offset k (-1..1) of the half-width. */
const alongSpine = (s: Spine, w: (t: number) => number, k: number, t0 = 0.04, t1 = 0.96, wob = 0, seed = '') =>
  Array.from({length: 40}, (_, i) => {
    const t = t0 + ((t1 - t0) * i) / 39;
    const kk = k + (wob ? Math.sin(t * 22 + rand(seed) * 6) * wob : 0);
    return add(spinePt(s, t), scale(spineNormal(s, t), w(t) * kk));
  });

const polarOutline = (r: (a: number) => number, sx = 1, sy = 1, n = 160): Pt[] =>
  Array.from({length: n}, (_, i) => {
    const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
    const rr = r(a);
    return pt(Math.cos(a) * rr * sx, Math.sin(a) * rr * sy);
  });

const calyxStar = (c: Pt, R: number, lobes: number, rot = 0): string => {
  const pts: Pt[] = [];
  for (let i = 0; i < lobes * 2; i++) {
    const a = rot + (i / (lobes * 2)) * Math.PI * 2;
    const r = i % 2 === 0 ? R : R * 0.32;
    pts.push(pt(c.x + Math.cos(a) * r, c.y + Math.sin(a) * r * 0.7));
  }
  return smoothPath(pts, true, 0.35);
};

const GREEN_CAP = '#3E6B2A';
const STEM = '#5C7A34';

// ── Crops ──────────────────────────────────────────────────────────────────

const chilli = (): Crop => {
  const s: Spine = {a: pt(-0.04, -0.47), c: pt(0.2, 0.02), b: pt(0.08, 0.5)};
  const w = (t: number) => 0.078 * Math.pow(Math.max(0, 1 - Math.pow(t, 1.7)), 0.75) * (t < 0.07 ? 0.72 + 4 * t : 1);
  return {
    id: 'chilli',
    name: 'Chilli',
    slot: 'crop-chilli',
    outline: finish(podOutline(s, w), s.a),
    colors: produce.chilliRed,
    details: [
      {d: smoothPath(alongSpine(s, w, -0.45, 0.08, 0.85)), stroke: '#FFD6C8', width: 0.016, opacity: 0.55},
      {d: smoothPath(alongSpine(s, w, 0.55, 0.1, 0.8)), stroke: '#4A0906', width: 0.02, opacity: 0.35},
    ],
    cap: [
      {d: calyxStar(pt(-0.04, -0.47), 0.085, 5, 0.3), fill: GREEN_CAP},
      {d: `M-0.04,-0.49 Q-0.03,-0.6 -0.1,-0.66`, stroke: STEM, width: 0.022},
    ],
    angle: 26,
  };
};

const cucumber = (): Crop => {
  const s: Spine = {a: pt(0, -0.5), c: pt(0.07, 0), b: pt(0.02, 0.5)};
  const w = (t: number) => 0.13 * Math.sqrt(Math.max(0, 1 - Math.pow(2 * t - 1, 6)));
  const stripes = [-0.6, -0.2, 0.2, 0.6].map((k) => ({
    d: smoothPath(alongSpine(s, w, k, 0.08, 0.92)),
    stroke: '#9BC476',
    width: 0.018,
    opacity: 0.45,
  }));
  const bumps = Array.from({length: 26}, (_, i) => {
    const t = 0.1 + rand(`cb${i}`) * 0.8;
    const k = (rand(`ck${i}`) - 0.5) * 1.5;
    const p = add(spinePt(s, t), scale(spineNormal(s, t), w(t) * k));
    return {d: `M${p.x},${p.y} m-0.008,0 a0.008,0.008 0 1,0 0.016,0 a0.008,0.008 0 1,0 -0.016,0`, fill: '#D8EBB4', opacity: 0.6};
  });
  return {
    id: 'cucumber',
    name: 'Cucumber',
    slot: 'crop-cucumber',
    outline: finish(podOutline(s, w), s.a),
    colors: produce.cucumber,
    details: [...stripes, ...bumps],
    cap: [{d: `M0,-0.5 Q0.01,-0.56 -0.02,-0.6`, stroke: STEM, width: 0.03}],
    angle: -24,
  };
};

const watermelon = (): Crop => {
  const rx = 0.46;
  const ry = 0.36;
  const outline = polarOutline(() => 1, rx, ry);
  const stripes: CropDetail[] = Array.from({length: 9}, (_, i) => {
    const u = -0.85 + (i / 8) * 1.7;
    const pts = Array.from({length: 40}, (_, j) => {
      const v = -1 + (j / 39) * 2;
      const x = u * Math.sqrt(Math.max(0, 1 - v * v)) * rx + Math.sin(v * 12 + i) * 0.012;
      return pt(x, v * ry);
    });
    return {d: smoothPath(pts), stroke: '#1C3D17', width: 0.045, opacity: 0.8};
  });
  return {
    id: 'watermelon',
    name: 'Watermelon',
    slot: 'crop-watermelon',
    outline: finish(outline, pt(0, -ry)),
    colors: produce.watermelon,
    details: stripes,
    cap: [{d: `M0,-0.36 Q0.02,-0.42 0.06,-0.44`, stroke: STEM, width: 0.022}],
    angle: -8,
  };
};

const bitterGourd = (): Crop => {
  const s: Spine = {a: pt(0, -0.5), c: pt(-0.05, 0), b: pt(0.02, 0.5)};
  const base = (t: number) => 0.125 * Math.pow(Math.sin(Math.PI * t), 0.85);
  const w = (t: number) => base(t) * (1 + 0.07 * Math.sin(t * 60));
  const warts: CropDetail[] = [];
  [-0.62, -0.2, 0.2, 0.62].forEach((k, r) => {
    for (let i = 0; i < 11; i++) {
      const t = 0.1 + (i / 10) * 0.8 + (r % 2) * 0.04;
      const p = add(spinePt(s, t), scale(spineNormal(s, t), base(t) * k));
      const rr = 0.008 + 0.007 * Math.sin(Math.PI * t);
      warts.push({d: `M${p.x - rr},${p.y} a${rr},${rr * 1.6} 0 1,0 ${rr * 2},0 a${rr},${rr * 1.6} 0 1,0 ${-rr * 2},0`, fill: '#CBE79A', opacity: 0.45});
    }
  });
  return {
    id: 'bitter-gourd',
    name: 'Bitter gourd',
    slot: 'crop-bitter-gourd',
    outline: finish(podOutline(s, w, 160), s.a),
    colors: produce.bitterGourd,
    details: warts,
    cap: [{d: `M0,-0.5 Q0.02,-0.58 -0.03,-0.64`, stroke: STEM, width: 0.02}],
    angle: 22,
  };
};

const bottleGourd = (): Crop => {
  const s: Spine = {a: pt(0, -0.5), c: pt(0.03, 0), b: pt(0, 0.5)};
  const w = (t: number) =>
    (0.058 + 0.165 * smoothstep(0.28, 0.72, t)) * Math.sqrt(Math.max(0, 1 - Math.pow(2 * t - 1, 14)));
  const specks = Array.from({length: 40}, (_, i) => {
    const t = 0.1 + rand(`bg${i}`) * 0.85;
    const p = add(spinePt(s, t), scale(spineNormal(s, t), w(t) * (rand(`bk${i}`) - 0.5) * 1.6));
    return {d: `M${p.x},${p.y} m-0.006,0 a0.006,0.006 0 1,0 0.012,0 a0.006,0.006 0 1,0 -0.012,0`, fill: '#F3F8DA', opacity: 0.5};
  });
  return {
    id: 'bottle-gourd',
    name: 'Bottle gourd',
    slot: 'crop-bottle-gourd',
    outline: finish(podOutline(s, w), s.a),
    colors: produce.bottleGourd,
    details: specks,
    cap: [{d: `M0,-0.5 Q-0.01,-0.57 0.03,-0.62`, stroke: STEM, width: 0.024}],
    angle: -10,
  };
};

const ridgeGourd = (): Crop => {
  const s: Spine = {a: pt(0, -0.5), c: pt(0.08, 0), b: pt(0.04, 0.5)};
  const w = (t: number) => (0.055 + 0.055 * t) * Math.sqrt(Math.max(0, 1 - Math.pow(2 * t - 1, 10)));
  const ridges = [-0.75, -0.45, -0.15, 0.15, 0.45, 0.75].map((k) => ({
    d: smoothPath(alongSpine(s, w, k, 0.05, 0.95)),
    stroke: '#1E3A14',
    width: 0.014,
    opacity: 0.75,
  }));
  return {
    id: 'ridge-gourd',
    name: 'Ridge gourd',
    slot: 'crop-ridge-gourd',
    outline: finish(podOutline(s, w), s.a),
    colors: produce.ridgeGourd,
    details: ridges,
    cap: [{d: `M0,-0.5 Q0.01,-0.57 -0.03,-0.62`, stroke: STEM, width: 0.02}],
    angle: 30,
  };
};

const tomato = (): Crop => {
  const outline = polarOutline((a) => 0.4 * (1 + 0.035 * Math.cos(5 * a)), 1.05, 0.88);
  return {
    id: 'tomato',
    name: 'Tomato',
    slot: 'crop-tomato',
    outline: finish(outline, pt(0, -0.35)),
    colors: produce.tomato,
    details: [
      {d: smoothPath([pt(-0.2, -0.22), pt(-0.26, -0.05), pt(-0.22, 0.12)]), stroke: '#FFD3C2', width: 0.02, opacity: 0.35},
    ],
    cap: [
      {d: calyxStar(pt(0, -0.33), 0.13, 6, 0.2), fill: GREEN_CAP},
      {d: `M0,-0.34 Q0.01,-0.42 0.04,-0.45`, stroke: STEM, width: 0.024},
    ],
    angle: 0,
  };
};

const okra = (): Crop => {
  const s: Spine = {a: pt(0, -0.47), c: pt(-0.07, 0.02), b: pt(0.05, 0.5)};
  const w = (t: number) => 0.082 * Math.pow(Math.max(0, 1 - Math.pow(t, 2.2)), 0.85) * (t < 0.06 ? 0.8 + 3.3 * t : 1);
  const ridges = [-0.55, -0.1, 0.35, 0.75].map((k) => ({
    d: smoothPath(alongSpine(s, w, k, 0.06, 0.94)),
    stroke: '#2B4F1C',
    width: 0.012,
    opacity: 0.7,
  }));
  return {
    id: 'okra',
    name: 'Okra',
    slot: 'crop-okra',
    outline: finish(podOutline(s, w), s.a),
    colors: produce.okra,
    details: [...ridges, {d: smoothPath(alongSpine(s, w, -0.3, 0.1, 0.8)), stroke: '#E6F5C4', width: 0.014, opacity: 0.4}],
    cap: [
      {d: `M-0.07,-0.44 Q0,-0.52 0.07,-0.44 L0.06,-0.4 Q0,-0.46 -0.06,-0.4Z`, fill: '#4F7A2E'},
      {d: `M0,-0.5 Q0.01,-0.58 -0.03,-0.63`, stroke: STEM, width: 0.022},
    ],
    angle: -24,
  };
};

/** Montage order (keep in sync with copy.crops.names). */
export const CROPS: Crop[] = [chilli(), cucumber(), watermelon(), bitterGourd(), bottleGourd(), ridgeGourd(), tomato(), okra()];

export const outlinePath = (pts: Pt[]) => smoothPath(pts, true, 0.5);
export {linePath};
