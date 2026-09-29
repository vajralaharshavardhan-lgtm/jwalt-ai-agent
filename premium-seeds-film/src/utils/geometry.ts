/** Small 2-D geometry kit used by the procedural botanical visuals. */
import {random} from 'remotion';

export type Pt = {x: number; y: number};

export const pt = (x: number, y: number): Pt => ({x, y});
export const add = (a: Pt, b: Pt): Pt => ({x: a.x + b.x, y: a.y + b.y});
export const sub = (a: Pt, b: Pt): Pt => ({x: a.x - b.x, y: a.y - b.y});
export const scale = (a: Pt, s: number): Pt => ({x: a.x * s, y: a.y * s});
export const len = (a: Pt) => Math.hypot(a.x, a.y);
export const normalize = (a: Pt): Pt => {
  const l = len(a) || 1;
  return {x: a.x / l, y: a.y / l};
};
export const perp = (a: Pt): Pt => ({x: -a.y, y: a.x});
export const lerpPt = (a: Pt, b: Pt, t: number): Pt => ({x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t});
export const rotate = (p: Pt, angle: number, c: Pt = {x: 0, y: 0}): Pt => {
  const s = Math.sin(angle);
  const co = Math.cos(angle);
  const dx = p.x - c.x;
  const dy = p.y - c.y;
  return {x: c.x + dx * co - dy * s, y: c.y + dx * s + dy * co};
};

/** Deterministic random in [min, max). */
export const rand = (seed: string | number, min = 0, max = 1) => min + random(seed) * (max - min);

export const quad = (p0: Pt, p1: Pt, p2: Pt, t: number): Pt => {
  const m = 1 - t;
  return {
    x: m * m * p0.x + 2 * m * t * p1.x + t * t * p2.x,
    y: m * m * p0.y + 2 * m * t * p1.y + t * t * p2.y,
  };
};

export const cubic = (p0: Pt, p1: Pt, p2: Pt, p3: Pt, t: number): Pt => {
  const m = 1 - t;
  const a = m * m * m;
  const b = 3 * m * m * t;
  const c = 3 * m * t * t;
  const d = t * t * t;
  return {x: a * p0.x + b * p1.x + c * p2.x + d * p3.x, y: a * p0.y + b * p1.y + c * p2.y + d * p3.y};
};

/** Sample any parametric curve into n+1 points. */
export const sampleCurve = (f: (t: number) => Pt, n: number): Pt[] =>
  Array.from({length: n + 1}, (_, i) => f(i / n));

export const polylineLength = (pts: Pt[]) => {
  let l = 0;
  for (let i = 1; i < pts.length; i++) {
    l += len(sub(pts[i], pts[i - 1]));
  }
  return l;
};

/** Resample a polyline to n points evenly spaced by arc length. */
export const resample = (pts: Pt[], n: number, closed = false): Pt[] => {
  const src = closed ? [...pts, pts[0]] : pts;
  const cum = [0];
  for (let i = 1; i < src.length; i++) {
    cum.push(cum[i - 1] + len(sub(src[i], src[i - 1])));
  }
  const total = cum[cum.length - 1];
  const out: Pt[] = [];
  const count = closed ? n : n - 1;
  let j = 1;
  for (let i = 0; i < n; i++) {
    const d = (i / count) * total;
    while (j < cum.length - 1 && cum[j] < d) {
      j++;
    }
    const seg = cum[j] - cum[j - 1] || 1;
    out.push(lerpPt(src[j - 1], src[j], (d - cum[j - 1]) / seg));
  }
  return out;
};

/** Truncate a polyline to fraction t (0..1) of its length. */
export const trimPolyline = (pts: Pt[], t: number): Pt[] => {
  if (t >= 1) {
    return pts;
  }
  if (t <= 0 || pts.length < 2) {
    return [pts[0]];
  }
  const total = polylineLength(pts);
  const target = total * t;
  const out: Pt[] = [pts[0]];
  let acc = 0;
  for (let i = 1; i < pts.length; i++) {
    const l = len(sub(pts[i], pts[i - 1]));
    if (acc + l >= target) {
      out.push(lerpPt(pts[i - 1], pts[i], (target - acc) / (l || 1)));
      return out;
    }
    acc += l;
    out.push(pts[i]);
  }
  return out;
};

// 4 decimals: some shapes are built in unit space and scaled up hundreds of times.
const f = (n: number) => n.toFixed(4);

export const linePath = (pts: Pt[], closed = false) =>
  pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${f(p.x)},${f(p.y)}`).join('') + (closed ? 'Z' : '');

/** Catmull-Rom spline through the points, emitted as cubic Béziers. */
export const smoothPath = (pts: Pt[], closed = false, tension = 0.5) => {
  if (pts.length < 3) {
    return linePath(pts, closed);
  }
  const n = pts.length;
  const get = (i: number) => (closed ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))]);
  let d = `M${f(pts[0].x)},${f(pts[0].y)}`;
  const segs = closed ? n : n - 1;
  const k = tension / 3;
  for (let i = 0; i < segs; i++) {
    const p0 = get(i - 1);
    const p1 = get(i);
    const p2 = get(i + 1);
    const p3 = get(i + 2);
    const c1 = {x: p1.x + (p2.x - p0.x) * k, y: p1.y + (p2.y - p0.y) * k};
    const c2 = {x: p2.x - (p3.x - p1.x) * k, y: p2.y - (p3.y - p1.y) * k};
    d += `C${f(c1.x)},${f(c1.y)} ${f(c2.x)},${f(c2.y)} ${f(p2.x)},${f(p2.y)}`;
  }
  return d + (closed ? 'Z' : '');
};

/** Unit tangent at index i of a polyline. */
export const tangentAt = (pts: Pt[], i: number): Pt => {
  const a = pts[Math.max(0, i - 1)];
  const b = pts[Math.min(pts.length - 1, i + 1)];
  return normalize(sub(b, a));
};

/**
 * Turn a centre line into a closed outline whose half-width at arc position
 * s (0..1) is width(s). Used for roots, stems, pods and leaves.
 */
export const ribbon = (center: Pt[], width: (s: number) => number): Pt[] => {
  const left: Pt[] = [];
  const right: Pt[] = [];
  const last = center.length - 1;
  center.forEach((p, i) => {
    const n = perp(tangentAt(center, i));
    const w = width(last === 0 ? 0 : i / last);
    left.push(add(p, scale(n, w)));
    right.push(sub(p, scale(n, w)));
  });
  return [...left, ...right.reverse()];
};

/** Linear interpolation between two point lists of equal length. */
export const lerpPts = (a: Pt[], b: Pt[], t: number): Pt[] => a.map((p, i) => lerpPt(p, b[i], t));

export const centroid = (pts: Pt[]): Pt => {
  const s = pts.reduce((acc, p) => add(acc, p), {x: 0, y: 0});
  return scale(s, 1 / pts.length);
};
