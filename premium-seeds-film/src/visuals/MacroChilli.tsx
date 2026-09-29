import React from 'react';
import {interpolateColors} from 'remotion';
import {type Pt, add, normalize, perp, pt, quad, ribbon, scale, smoothPath, sub} from '../utils/geometry';
import {clamp, lerp} from '../utils/easing';

export type MacroChilliProps = {
  id: string;
  /** Calyx (stem) end and tip, in px. */
  a: Pt;
  b: Pt;
  /** Curvature: control-point offset along the normal, as a fraction of length. */
  bend: number;
  /** Max half-width in px. */
  width: number;
  /** 0 green → 1 fully ripe red (ripening travels from tip to calyx). */
  ripen: number;
  /** Specular band position across the pod (-1..1): animating it reads as rotation. */
  sheen: number;
  /** Overall light level 0..1 (for reveal). */
  light: number;
  /** Width squash (0.9..1) for the rotation illusion. */
  squash?: number;
};

const GREEN = ['#9ED36F', '#3F8E36', '#0F3514'];
const RED = ['#F0624C', '#B9261A', '#4E0905'];

/**
 * Photographic-style macro chilli: glossy pod with a travelling specular band,
 * environment reflection, rim light, a calyx and stem, and ripening that
 * spreads from the tip to the shoulder.
 */
export const MacroChilli: React.FC<MacroChilliProps> = ({id, a, b, bend, width, ripen, sheen, light, squash = 1}) => {
  const L = Math.hypot(b.x - a.x, b.y - a.y);
  const dir = normalize(sub(b, a));
  const nrm = perp(dir);
  const c = add(pt((a.x + b.x) / 2, (a.y + b.y) / 2), scale(nrm, bend * L));
  const spine = Array.from({length: 80}, (_, i) => quad(a, c, b, i / 79));
  const w = (t: number) => width * squash * Math.pow(Math.max(0, 1 - Math.pow(t, 1.8)), 0.72) * (t < 0.06 ? 0.78 + 3.6 * t : 1);
  const body = ribbon(spine, w);
  const bodyD = smoothPath(body, true);

  // Specular band: a thin ribbon offset across the pod.
  const band = (offset: number, thick: number, t0: number, t1: number) => {
    const pts = spine.filter((_, i) => i / 79 >= t0 && i / 79 <= t1);
    const shifted = pts.map((p, i) => {
      const t = t0 + ((t1 - t0) * i) / Math.max(1, pts.length - 1);
      const tan = normalize(sub(spine[Math.min(79, Math.round(t * 79) + 1)], spine[Math.max(0, Math.round(t * 79) - 1)]));
      return add(p, scale(perp(tan), w(t) * offset));
    });
    return smoothPath(ribbon(shifted, (s) => thick * Math.sin(Math.PI * Math.min(1, Math.max(0, s))) * width), true);
  };

  const mid = quad(a, c, b, 0.45);
  const g1 = add(mid, scale(nrm, width * 1.1));
  const g2 = add(mid, scale(nrm, -width * 1.1));
  const col = (i: number) => interpolateColors(clamp(ripen), [0, 1], [GREEN[i], RED[i]]);
  // Ripening front travels from the tip (1) toward the calyx (0).
  const front = lerp(1.15, -0.2, clamp(ripen));
  const calyxDir = scale(dir, -1);
  const calyx = [
    add(a, scale(nrm, width * 1.05)),
    add(add(a, scale(dir, width * 0.55)), scale(nrm, width * 0.95)),
    add(a, scale(dir, width * 1.05)),
    add(add(a, scale(dir, width * 0.55)), scale(nrm, -width * 0.95)),
    add(a, scale(nrm, -width * 1.05)),
    add(a, scale(calyxDir, width * 0.35)),
  ];
  const stemEnd = add(add(a, scale(calyxDir, width * 3.6)), scale(nrm, width * 1.6));
  const stemCtrl = add(a, scale(calyxDir, width * 2.2));

  return (
    <g opacity={light}>
      <defs>
        <linearGradient id={`${id}-g`} gradientUnits="userSpaceOnUse" x1={g1.x} y1={g1.y} x2={g2.x} y2={g2.y}>
          <stop offset="0" stopColor={GREEN[2]} />
          <stop offset="0.3" stopColor={GREEN[1]} />
          <stop offset="0.55" stopColor={GREEN[0]} />
          <stop offset="0.8" stopColor={GREEN[1]} />
          <stop offset="1" stopColor={GREEN[2]} />
        </linearGradient>
        <linearGradient id={`${id}-r`} gradientUnits="userSpaceOnUse" x1={g1.x} y1={g1.y} x2={g2.x} y2={g2.y}>
          <stop offset="0" stopColor={RED[2]} />
          <stop offset="0.3" stopColor={RED[1]} />
          <stop offset="0.55" stopColor={RED[0]} />
          <stop offset="0.8" stopColor={RED[1]} />
          <stop offset="1" stopColor={RED[2]} />
        </linearGradient>
        <linearGradient id={`${id}-ripe`} gradientUnits="userSpaceOnUse" x1={a.x} y1={a.y} x2={b.x} y2={b.y}>
          <stop offset={Math.max(0, front - 0.14)} stopColor="#000" />
          <stop offset={Math.min(1, Math.max(0, front + 0.14))} stopColor="#fff" />
        </linearGradient>
        <mask id={`${id}-ripe-mask`}>
          <path d={bodyD} fill={`url(#${id}-ripe)`} />
        </mask>
        <linearGradient id={`${id}-stem`} gradientUnits="userSpaceOnUse" x1={a.x} y1={a.y} x2={stemEnd.x} y2={stemEnd.y}>
          <stop offset="0" stopColor="#35561F" />
          <stop offset="1" stopColor="#8BA656" />
        </linearGradient>
        <filter id={`${id}-b3`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation={width * 0.08} />
        </filter>
        <filter id={`${id}-b10`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation={width * 0.35} />
        </filter>
        <filter id={`${id}-shadow`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation={width * 0.9} />
        </filter>
        <clipPath id={`${id}-clip`}>
          <path d={bodyD} />
        </clipPath>
      </defs>

      {/* Ambient glow behind the pod, tinted by its colour */}
      <path d={bodyD} fill={col(1)} opacity={0.35} filter={`url(#${id}-shadow)`} />

      <path d={bodyD} fill={`url(#${id}-g)`} />
      <path d={bodyD} fill={`url(#${id}-r)`} mask={`url(#${id}-ripe-mask)`} />

      <g clipPath={`url(#${id}-clip)`}>
        {/* Environment reflection (soft, opposite side) */}
        <path d={band(-sheen * 0.8 - 0.2, 0.22, 0.05, 0.85)} fill="#FFFFFF" opacity={0.1} filter={`url(#${id}-b10)`} />
        {/* Key specular band + hot core */}
        <path d={band(sheen, 0.2, 0.04, 0.9)} fill="#FFFFFF" opacity={0.28} filter={`url(#${id}-b10)`} />
        <path d={band(sheen, 0.07, 0.06, 0.82)} fill="#FFFFFF" opacity={0.75} filter={`url(#${id}-b3)`} />
        {/* Shoulder wrinkles */}
        {[0.3, -0.1, -0.45].map((o, i) => (
          <path
            key={i}
            d={smoothPath([
              add(add(a, scale(dir, width * (1.2 + i * 0.3))), scale(nrm, width * o)),
              add(add(a, scale(dir, width * (2.4 + i * 0.4))), scale(nrm, width * (o + 0.12))),
              add(add(a, scale(dir, width * (3.8 + i * 0.5))), scale(nrm, width * (o + 0.05))),
            ])}
            stroke="#000"
            strokeOpacity={0.22}
            strokeWidth={width * 0.05}
            fill="none"
          />
        ))}
      </g>

      {/* Rim light on the lower edge */}
      <path d={bodyD} fill="none" stroke="#FFE6C8" strokeOpacity={0.35} strokeWidth={width * 0.05} filter={`url(#${id}-b3)`} />

      {/* Stem and calyx */}
      <path
        d={`M${a.x},${a.y} Q${stemCtrl.x},${stemCtrl.y} ${stemEnd.x},${stemEnd.y}`}
        stroke={`url(#${id}-stem)`}
        strokeWidth={width * 0.34}
        strokeLinecap="round"
        fill="none"
      />
      <path
        d={`M${a.x},${a.y} Q${stemCtrl.x},${stemCtrl.y} ${stemEnd.x},${stemEnd.y}`}
        stroke="#E9F2C8"
        strokeOpacity={0.35}
        strokeWidth={width * 0.07}
        strokeLinecap="round"
        fill="none"
        transform={`translate(${nrm.x * width * 0.08} ${nrm.y * width * 0.08})`}
      />
      <path d={smoothPath(calyx, true, 0.4)} fill="#3C6424" />
      <path d={smoothPath(calyx, true, 0.4)} fill="none" stroke="#9DBA66" strokeOpacity={0.45} strokeWidth={width * 0.04} />
    </g>
  );
};
