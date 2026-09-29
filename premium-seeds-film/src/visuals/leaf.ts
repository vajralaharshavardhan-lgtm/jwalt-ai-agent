/**
 * Procedural ovate-lanceolate leaf (chilli-like), base at the origin,
 * tip at (bend, -L). Returns outline, midrib and secondary veins, so the
 * same leaf can be drawn as line-art (Research) or backlit tissue (Field).
 */
import {type Pt, pt, quad} from '../utils/geometry';

export type LeafGeometry = {
  outline: Pt[];
  midrib: Pt[];
  veins: Pt[][];
  /** Point on the midrib at fraction t (0 base … 1 tip). */
  mid: (t: number) => Pt;
};

export const leafGeometry = (L: number, W: number, bend = 0.08, veinPairs = 6): LeafGeometry => {
  const mid = (t: number) => pt(bend * L * t * t, -L * t);
  const half = (t: number) => (W * Math.pow(t, 0.5) * Math.pow(1 - t, 1.05)) / 0.36;
  const n = 48;
  const right: Pt[] = [];
  const left: Pt[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const m = mid(t);
    // Slight asymmetry reads as a real leaf.
    right.push(pt(m.x + half(t) * 1.04, m.y));
    left.push(pt(m.x - half(t) * 0.96, m.y));
  }
  const outline = [...right, ...left.reverse().slice(1, -1)];
  const midrib = Array.from({length: 25}, (_, i) => mid(i / 24));
  const veins: Pt[][] = [];
  for (let i = 0; i < veinPairs; i++) {
    const t0 = 0.1 + (i / veinPairs) * 0.72;
    const t1 = Math.min(0.97, t0 + 0.16);
    for (const side of [1, -1]) {
      const a = mid(t0);
      const edge = pt(mid(t1).x + side * half(t1) * 0.86, mid(t1).y);
      const ctrl = pt(a.x + side * half(t0) * 0.7, (a.y + edge.y) / 2 + L * 0.02);
      veins.push(Array.from({length: 13}, (_, j) => quad(a, ctrl, edge, j / 12)));
    }
  }
  return {outline, midrib, veins, mid};
};
