/**
 * Procedural perspective crop field at golden hour: rows converging on a low
 * sun, plants with warm rim light, aerial haze. Pure SVG, deterministic.
 */
import React from 'react';
import {interpolateColors} from 'remotion';
import {type Pt, pt, rand} from '../utils/geometry';
import {lerp} from '../utils/easing';

export type FieldSetup = {
  width: number;
  height: number;
  u: number;
  horizon: number;
  vpX: number;
  rows: number;
  /** Row bottom-x positions (screen) for rows 0..rows-1. */
  rowBottomX: number[];
  bottomY: number;
};

export const fieldSetup = (width: number, height: number, u: number, portrait: boolean, rows = 13): FieldSetup => {
  const horizon = height * (portrait ? 0.42 : 0.4);
  const vpX = width * 0.5;
  const spacing = (portrait ? 0.62 : 0.34) * width;
  const mid = (rows - 1) / 2;
  return {
    width,
    height,
    u,
    horizon,
    vpX,
    rows,
    rowBottomX: Array.from({length: rows}, (_, i) => vpX + (i - mid) * spacing),
    bottomY: height + 60 * u,
  };
};

/** Row line i as n points from the bottom edge to the vanishing point. */
export const rowLine = (s: FieldSetup, i: number, n = 16): Pt[] =>
  Array.from({length: n}, (_, j) => {
    const t = j / (n - 1);
    return pt(lerp(s.rowBottomX[i], s.vpX, t), lerp(s.bottomY, s.horizon, t));
  });

/** Screen position of depth Z (1 = bottom edge) on row i (fractional rows allowed). */
const project = (s: FieldSetup, rowPos: number, Z: number) => {
  const dy = (s.bottomY - s.horizon) / Z;
  const i0 = Math.floor(rowPos);
  const frac = rowPos - i0;
  const xb = lerp(s.rowBottomX[Math.max(0, Math.min(s.rows - 1, i0))], s.rowBottomX[Math.max(0, Math.min(s.rows - 1, i0 + 1))], frac);
  const slope = (xb - s.vpX) / (s.bottomY - s.horizon);
  return pt(s.vpX + slope * dy, s.horizon + dy);
};

// Broad ovate leaf (vegetable crop), base at origin pointing up (-y).
const LEAF = (L: number, w: number) =>
  `M0,0 C${w * 0.9},${-L * 0.12} ${w},${-L * 0.68} 0,${-L} C${-w},${-L * 0.68} ${-w * 0.9},${-L * 0.12} 0,0Z`;

/** A bushy vegetable plant: broad leaves scattered over a low dome, rim-lit from the sun side. */
const Plant: React.FC<{x: number; y: number; h: number; seed: string; haze: number; sunSide: number; sway: number}> = ({
  x,
  y,
  h,
  seed,
  haze,
  sunSide,
  sway,
}) => {
  const shades = ['#132A15', '#1A361B', '#224423', '#2B5029'].map((c) => interpolateColors(haze, [0, 1], [c, '#A09F74']));
  const rim = interpolateColors(haze, [0, 1], ['#EFC47A', '#EAD3A2']);
  const leaves = h > 40 ? 13 : h > 14 ? 8 : 5;
  const off = Math.max(0.5, h * 0.018);
  const items = Array.from({length: leaves}, (_, i) => {
    const bx = (rand(`${seed}x${i}`) - 0.5) * h * 0.8;
    const dome = 1 - Math.pow(Math.abs(bx) / (h * 0.45), 2);
    const by = -Math.max(0, dome) * h * (0.25 + rand(`${seed}y${i}`) * 0.35);
    const a = Math.atan2(by - h * 0.2, bx) + Math.PI / 2 + (rand(`${seed}a${i}`) - 0.5) * 0.9 + sway;
    const L = h * (0.32 + rand(`${seed}l${i}`) * 0.2);
    return {bx, by, a, L, w: L * 0.44, shade: shades[i % shades.length]};
  }).sort((p, q) => p.by - q.by);
  return (
    <g transform={`translate(${x} ${y})`}>
      <ellipse cx={0} cy={-h * 0.08} rx={h * 0.42} ry={h * 0.2} fill={shades[0]} />
      {items.map((it, i) => {
        const d = LEAF(it.L, it.w);
        const deg = (it.a * 180) / Math.PI;
        return (
          <g key={i} transform={`translate(${it.bx} ${it.by}) rotate(${deg})`}>
            {haze < 0.85 ? <path d={d} fill={rim} opacity={0.9 * (1 - haze)} transform={`translate(${off * 0.6 * sunSide} ${-off})`} /> : null}
            <path d={d} fill={it.shade} />
          </g>
        );
      })}
    </g>
  );
};

export const Field: React.FC<{
  setup: FieldSetup;
  /** Seconds of dolly travel. */
  time: number;
  /** 0..1 fade for plants. */
  plantsIn: number;
  /** Row furrow line opacity. */
  furrows: number;
  sunX?: number;
}> = ({setup: s, time, plantsIn, furrows, sunX = 0.6}) => {
  const {width, height, u, horizon} = s;
  const sunPx = width * sunX;
  const plants: React.ReactNode[] = [];
  const zMin = 0.85;
  const zRange = 9;
  const dz = 0.38;
  const speed = 0.55;
  const perRow = Math.floor(zRange / dz);
  const items: {Z: number; node: (key: string) => React.ReactNode}[] = [];
  for (let r = 0; r < s.rows; r++) {
    for (let j = 0; j < perRow; j++) {
      const phase = rand(`ph${r}`) * dz;
      const zRaw = j * dz + phase - time * speed;
      const Z = zMin + (((zRaw % zRange) + zRange) % zRange);
      const jitter = (rand(`jx${r}-${j}`) - 0.5) * 0.18;
      const p = project(s, r + jitter, Z);
      if (p.x < -300 * u || p.x > width + 300 * u) {
        continue;
      }
      const h = (300 * u) / Z;
      const haze = Math.min(1, Math.max(0, (Z - 1.2) / 8));
      const sunSide = p.x < sunPx ? 1 : -1;
      const sway = Math.sin(time * 1.3 + r * 0.7 + j) * 0.03;
      items.push({Z, node: (key) => <Plant key={key} x={p.x} y={p.y} h={h} seed={`p${r}-${j}`} haze={haze} sunSide={sunSide} sway={sway} />});
    }
  }
  items.sort((a, b) => b.Z - a.Z);
  const far = items.filter((it) => it.Z > 4.5);
  const mid = items.filter((it) => it.Z <= 4.5 && it.Z > 1.45);
  const near = items.filter((it) => it.Z <= 1.45);
  plants.push(
    <g key="far" filter="url(#f-dof-far)">{far.map((it, i) => it.node(`f${i}`))}</g>,
    <g key="mid">{mid.map((it, i) => it.node(`m${i}`))}</g>,
    <g key="near" filter="url(#f-dof-near)">{near.map((it, i) => it.node(`n${i}`))}</g>,
  );

  return (
    <svg width={width} height={height} style={{position: 'absolute', inset: 0}}>
      <defs>
        <linearGradient id="f-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2C3F3A" />
          <stop offset="0.55" stopColor="#B07A4E" />
          <stop offset="0.85" stopColor="#F2C27E" />
          <stop offset="1" stopColor="#FBE3B0" />
        </linearGradient>
        <linearGradient id="f-ground" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#B3905F" />
          <stop offset="0.12" stopColor="#6A5236" />
          <stop offset="0.5" stopColor="#35271A" />
          <stop offset="1" stopColor="#1A120B" />
        </linearGradient>
        <radialGradient id="f-sun" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#FFF8E6" stopOpacity="1" />
          <stop offset="0.08" stopColor="#FFE9BC" stopOpacity="0.95" />
          <stop offset="0.3" stopColor="#F6C47C" stopOpacity="0.45" />
          <stop offset="1" stopColor="#F6C47C" stopOpacity="0" />
        </radialGradient>
        <filter id="f-dof-far" x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={1.1 * u} />
        </filter>
        <filter id="f-dof-near" x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={7 * u} />
        </filter>
        <linearGradient id="f-haze" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F7D69C" stopOpacity="0" />
          <stop offset="0.5" stopColor="#F7D69C" stopOpacity="0.55" />
          <stop offset="1" stopColor="#F7D69C" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width={width} height={horizon + 2} fill="url(#f-sky)" />
      <rect y={horizon} width={width} height={height - horizon} fill="url(#f-ground)" />
      {/* Distant tree line / far crop band */}
      <path
        d={`M0,${horizon} ${Array.from({length: 41}, (_, i) => {
          const x = (i / 40) * width;
          return `L${x},${horizon - (4 + rand(`tl${i}`) * 9) * u}`;
        }).join(' ')} L${width},${horizon} Z`}
        fill="#7A6C4C"
        opacity={0.4}
      />
      {/* Furrows */}
      {Array.from({length: s.rows}, (_, i) => (
        <path
          key={i}
          d={`M${s.rowBottomX[i]},${s.bottomY} L${s.vpX},${horizon}`}
          stroke="#1A120B"
          strokeOpacity={0.55 * furrows}
          strokeWidth={26 * u}
          strokeLinecap="butt"
        />
      ))}
      <g opacity={plantsIn}>{plants}</g>
      {/* Haze at the horizon and sun bloom */}
      <rect y={horizon - 90 * u} width={width} height={180 * u} fill="url(#f-haze)" />
      <circle cx={sunPx} cy={horizon - 26 * u} r={520 * u} fill="url(#f-sun)" style={{mixBlendMode: 'screen'}} />
      <rect x={0} y={horizon - 30 * u} width={width} height={4 * u} fill="#FFE7B8" opacity={0.18} />
    </svg>
  );
};
