import React from 'react';
import {interpolateColors} from 'remotion';
import {type Crop, outlinePath} from '../visuals/crops';
import {lerpPts, rotate, type Pt} from '../utils/geometry';
import {clamp, lerp} from '../utils/easing';

const lerpAngle = (a: number, b: number, t: number) => a + (b - a) * t;

/**
 * Renders one vegetable, or a point-for-point morph between two (t 0..1).
 * Shape, colour and orientation interpolate; surface details cross-dissolve.
 * `draw` (0..1) traces the outline before the flesh fills in.
 */
export const CropMorph: React.FC<{
  id: string;
  from: Crop;
  to: Crop;
  t: number;
  x: number;
  y: number;
  /** Pixel size of one unit (crops are ~1 unit on their long side). */
  size: number;
  draw?: number;
  opacity?: number;
}> = ({id, from, to, t, x, y, size, draw = 1, opacity = 1}) => {
  const angle = lerpAngle(from.angle, to.angle, t);
  const rad = (angle * Math.PI) / 180;
  const local: Pt[] = t <= 0 ? from.outline : t >= 1 ? to.outline : lerpPts(from.outline, to.outline, t);
  const rotated = local.map((p) => rotate(p, rad));
  const c = (i: number) => interpolateColors(t, [0, 1], [from.colors[i], to.colors[i]]);
  const fill = clamp((draw - 0.55) / 0.45);
  const fromDetail = clamp(1 - t * 2.5);
  const toDetail = clamp((t - 0.6) / 0.4);
  const renderDetails = (crop: Crop, o: number, keyPrefix: string) =>
    o <= 0.001
      ? null
      : crop.details.map((d, i) => (
          <path
            key={`${keyPrefix}${i}`}
            d={d.d}
            fill={d.fill ?? 'none'}
            stroke={d.stroke ?? 'none'}
            strokeWidth={d.width ?? 0.01}
            strokeLinecap="round"
            opacity={(d.opacity ?? 1) * o}
          />
        ));
  const renderCap = (crop: Crop, o: number, keyPrefix: string) =>
    o <= 0.001
      ? null
      : crop.cap.map((d, i) => (
          <path
            key={`${keyPrefix}${i}`}
            d={d.d}
            fill={d.fill ?? 'none'}
            stroke={d.stroke ?? 'none'}
            strokeWidth={d.width ?? 0.01}
            strokeLinecap="round"
            opacity={o}
          />
        ));
  const outlineD = outlinePath(rotated);
  const localD = outlinePath(local);
  return (
    <g transform={`translate(${x} ${y}) scale(${size})`} opacity={opacity}>
      <defs>
        <radialGradient id={`${id}-body`} cx="0.36" cy="0.3" r="0.85">
          <stop offset="0" stopColor={c(0)} />
          <stop offset="0.5" stopColor={c(1)} />
          <stop offset="1" stopColor={c(2)} />
        </radialGradient>
        <radialGradient id={`${id}-light`} cx="0.34" cy="0.26" r="0.6">
          <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.42" />
          <stop offset="0.35" stopColor="#FFFFFF" stopOpacity="0.08" />
          <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}-shade`} x1="0.2" y1="0.1" x2="0.85" y2="0.95">
          <stop offset="0.45" stopColor="#000000" stopOpacity="0" />
          <stop offset="1" stopColor="#000000" stopOpacity="0.45" />
        </linearGradient>
        <clipPath id={`${id}-clip`}>
          <path d={localD} />
        </clipPath>
        <filter id={`${id}-glow`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="0.06" />
        </filter>
      </defs>
      {/* Soft warm bounce behind the fruit */}
      <path d={outlineD} fill={c(1)} opacity={0.35 * fill} filter={`url(#${id}-glow)`} transform="translate(0 0.03)" />
      <g opacity={fill}>
        <path d={outlineD} fill={`url(#${id}-body)`} />
        <g transform={`rotate(${angle})`} clipPath={`url(#${id}-clip)`}>
          {renderDetails(from, fromDetail, 'fd')}
          {renderDetails(to, toDetail, 'td')}
        </g>
        <path d={outlineD} fill={`url(#${id}-shade)`} />
        <path d={outlineD} fill={`url(#${id}-light)`} />
      </g>
      {/* Hairline outline: traces on first, then stays as a fine edge */}
      <path
        d={outlineD}
        fill="none"
        stroke="#F4EFE3"
        strokeOpacity={lerp(0.9, 0.18, fill)}
        strokeWidth={1.3 / size}
        pathLength={1}
        strokeDasharray="1 1"
        strokeDashoffset={1 - clamp(draw / 0.6)}
      />
      <g transform={`rotate(${angle})`} opacity={fill}>
        {renderCap(from, fromDetail, 'fc')}
        {renderCap(to, toDetail, 'tc')}
      </g>
    </g>
  );
};
