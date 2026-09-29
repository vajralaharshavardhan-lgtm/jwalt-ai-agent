import React, {type CSSProperties} from 'react';
import {palette} from '../styles/brand';

export type SeedProps = {
  /** Unique id prefix (SVG gradients/filters are document-global). */
  id: string;
  /** Rendered height in px. Width is 0.625 × height. */
  size: number;
  /** Key light position in seed-local space, 0..1 (x across, y down). */
  lightX?: number;
  lightY?: number;
  /** 0 = only the rim is lit (seed in darkness), 1 = fully lit. */
  keyLight?: number;
  /** Back/rim light intensity 0..1. */
  rimLight?: number;
  /** Hairline split at the tip, 0..1. */
  crack?: number;
  /** Warm light escaping from the split, 0..1. */
  glow?: number;
  /** Depth-of-field blur in px. */
  blur?: number;
  /** Multiplies the whole seed's brightness (for seeds sitting in soil). */
  exposure?: number;
  style?: CSSProperties;
};

// Cucurbit-type seed (cucumber / melon / pumpkin family): flat, egg-shaped,
// with a raised margin and a pointed hilum end. Drawn in a 100 × 160 box.
export const SEED_PATH =
  'M49,6 C58,7 70,20 78,40 C88,62 90,92 84,118 C78,140 64,154 50,155 C36,154 22,140 16,118 C10,92 12,62 21,40 C29,21 40,6.5 49,6 Z';

const CRACK_PATH = 'M49,7.5 C49.8,12 48.7,16.5 49.5,21 C50.3,25.5 49.1,29.5 49.8,34 C50.4,38 49.5,41 50,45';

// Filter regions in user space so blurs never clip into hard-edged strips.
const REGION = {x: -60, y: -60, width: 220, height: 280, filterUnits: 'userSpaceOnUse' as const};

/**
 * Macro seed, lit like a product shot: moving key light, directional rim
 * light, two-scale micro relief (SVG lighting on turbulence), raised margin,
 * specular sheen, and a hairline split at the tip that leaks warm light.
 * The recurring visual metaphor of the film.
 */
export const Seed: React.FC<SeedProps> = ({
  id,
  size,
  lightX = 0.35,
  lightY = 0.3,
  keyLight = 1,
  rimLight = 0.8,
  crack = 0,
  glow = 0,
  blur = 0,
  exposure = 1,
  style,
}) => {
  const w = size * 0.625;
  const pad = 0.35;
  const azimuth = (Math.atan2(lightY - 0.5, lightX - 0.5) * 180) / Math.PI;
  const k = keyLight;
  // Rim sits on the side facing away from the key light.
  const rx1 = lightX;
  const ry1 = lightY;
  const rx2 = 1 - lightX;
  const ry2 = 1 - lightY * 0.6;
  return (
    <svg
      width={w * (1 + pad * 2)}
      height={size * (1 + pad * 2 * 0.625)}
      viewBox={`${-100 * pad} ${-100 * pad} ${100 * (1 + pad * 2)} ${160 + 100 * pad * 2}`}
      style={{
        overflow: 'visible',
        filter: `${blur > 0.3 ? `blur(${blur}px)` : ''}${exposure !== 1 ? ` brightness(${exposure})` : ''}` || undefined,
        ...style,
      }}
    >
      <defs>
        <radialGradient id={`${id}-body`} cx={lightX} cy={lightY} r="0.9" fx={lightX} fy={lightY}>
          <stop offset="0" stopColor="#FFF7E4" />
          <stop offset="0.22" stopColor="#F1DDB0" />
          <stop offset="0.55" stopColor="#CFA869" />
          <stop offset="0.85" stopColor="#8A6334" />
          <stop offset="1" stopColor="#4B3117" />
        </radialGradient>
        <radialGradient id={`${id}-dark`} cx="0.5" cy="0.5" r="0.7">
          <stop offset="0" stopColor="#2E2111" />
          <stop offset="1" stopColor="#0E0904" />
        </radialGradient>
        <linearGradient id={`${id}-form`} x1={lightX} y1={lightY} x2={1 - lightX} y2={1 - lightY}>
          <stop offset="0" stopColor="#FFFFFF" stopOpacity="0" />
          <stop offset="0.55" stopColor="#2A1A0A" stopOpacity="0.05" />
          <stop offset="1" stopColor="#1A0F05" stopOpacity="0.75" />
        </linearGradient>
        <linearGradient id={`${id}-rim`} x1={rx1} y1={ry1} x2={rx2} y2={ry2}>
          <stop offset="0" stopColor="#FFE9C2" stopOpacity="0" />
          <stop offset="0.6" stopColor="#FFE9C2" stopOpacity="0" />
          <stop offset="1" stopColor="#FFF3DD" stopOpacity="1" />
        </linearGradient>
        <linearGradient id={`${id}-lip`} x1={lightX} y1={lightY} x2={1 - lightX} y2={1 - lightY}>
          <stop offset="0" stopColor="#FFF6E2" stopOpacity="0.9" />
          <stop offset="0.5" stopColor="#FFF6E2" stopOpacity="0.2" />
          <stop offset="1" stopColor="#FFF6E2" stopOpacity="0" />
        </linearGradient>
        <radialGradient id={`${id}-spec`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.9" />
          <stop offset="0.4" stopColor="#FFFBF0" stopOpacity="0.35" />
          <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`${id}-halo`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor={palette.sun} stopOpacity="0.5" />
          <stop offset="0.45" stopColor={palette.husk} stopOpacity="0.1" />
          <stop offset="1" stopColor={palette.husk} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`${id}-tipglow`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#FFF4DC" stopOpacity="1" />
          <stop offset="0.3" stopColor={palette.sun} stopOpacity="0.6" />
          <stop offset="1" stopColor={palette.sun} stopOpacity="0" />
        </radialGradient>
        <clipPath id={`${id}-clip`}>
          <path d={SEED_PATH} />
        </clipPath>
        {/* Coarse mottling of the seed coat. */}
        <filter id={`${id}-mottle`} x="0" y="0" width="100" height="160" filterUnits="userSpaceOnUse">
          <feTurbulence type="fractalNoise" baseFrequency="0.05 0.035" numOctaves={3} seed={3} result="n" />
          <feDiffuseLighting in="n" surfaceScale={3} diffuseConstant={1} lightingColor="#FFF3E0">
            <feDistantLight azimuth={azimuth} elevation={50} />
          </feDiffuseLighting>
        </filter>
        {/* Fine longitudinal striations. */}
        <filter id={`${id}-fibre`} x="0" y="0" width="100" height="160" filterUnits="userSpaceOnUse">
          <feTurbulence type="fractalNoise" baseFrequency="1.1 0.09" numOctaves={2} seed={11} result="n" />
          <feDiffuseLighting in="n" surfaceScale={0.9} diffuseConstant={1} lightingColor="#FFF6EA">
            <feDistantLight azimuth={azimuth} elevation={55} />
          </feDiffuseLighting>
        </filter>
        <filter id={`${id}-soft`} {...REGION}>
          <feGaussianBlur stdDeviation="1.6" />
        </filter>
        <filter id={`${id}-softer`} {...REGION}>
          <feGaussianBlur stdDeviation="5" />
        </filter>
      </defs>

      {/* Halo behind the seed separates it from the black. */}
      <ellipse cx="50" cy="82" rx="85" ry="110" fill={`url(#${id}-halo)`} opacity={0.3 * rimLight + 0.45 * glow} />

      <g clipPath={`url(#${id}-clip)`}>
        <path d={SEED_PATH} fill={`url(#${id}-dark)`} />
        <path d={SEED_PATH} fill={`url(#${id}-body)`} opacity={k} />
        <rect width="100" height="160" filter={`url(#${id}-mottle)`} style={{mixBlendMode: 'soft-light'}} opacity={0.55 * k} />
        <rect width="100" height="160" filter={`url(#${id}-fibre)`} style={{mixBlendMode: 'multiply'}} opacity={0.14 + 0.06 * k} />
        {/* Form shading: falls off to near-black on the far side. */}
        <path d={SEED_PATH} fill={`url(#${id}-form)`} />
        {/* Raised margin: dark groove inside the edge, lit lip on the key side. */}
        <path
          d={SEED_PATH}
          transform="translate(50 82) scale(0.83 0.875) translate(-50 -82)"
          fill="none"
          stroke="#3B2711"
          strokeOpacity={0.6}
          strokeWidth={3}
          filter={`url(#${id}-soft)`}
        />
        <path
          d={SEED_PATH}
          transform="translate(50 82) scale(0.9 0.93) translate(-50 -82)"
          fill="none"
          stroke={`url(#${id}-lip)`}
          strokeWidth={2.2}
          opacity={0.75 * k}
          filter={`url(#${id}-soft)`}
        />
        {/* Specular sheen: broad soft lobe plus a tight hotspot. */}
        <ellipse
          cx={100 * lightX + 4}
          cy={160 * lightY + 6}
          rx="22"
          ry="38"
          fill={`url(#${id}-spec)`}
          opacity={0.4 * k}
          transform={`rotate(-14 ${100 * lightX} ${160 * lightY})`}
        />
        <ellipse
          cx={100 * lightX + 6}
          cy={160 * lightY + 4}
          rx="6"
          ry="11"
          fill={`url(#${id}-spec)`}
          opacity={0.55 * k}
          transform={`rotate(-14 ${100 * lightX} ${160 * lightY})`}
        />
      </g>

      {/* Directional rim light along the silhouette. */}
      <path d={SEED_PATH} fill="none" stroke={`url(#${id}-rim)`} strokeWidth={2.2} opacity={rimLight} filter={`url(#${id}-soft)`} />
      <path d={SEED_PATH} fill="none" stroke={`url(#${id}-rim)`} strokeWidth={0.5} opacity={rimLight * 0.8} />

      {/* Hairline split at the tip, leaking warm light. */}
      {crack > 0 ? (
        <g>
          <ellipse cx="49.5" cy="12" rx={10 + 30 * glow} ry={12 + 34 * glow} fill={`url(#${id}-tipglow)`} opacity={glow * 0.9} />
          <path
            d={CRACK_PATH}
            fill="none"
            stroke={palette.sun}
            strokeWidth={3 + glow * 6}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray="1 1"
            strokeDashoffset={1 - crack}
            opacity={0.5 + 0.5 * glow}
            filter={`url(#${id}-softer)`}
          />
          <path
            d={CRACK_PATH}
            fill="none"
            stroke="#FFF8EA"
            strokeWidth={0.7 + glow * 0.6}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray="1 1"
            strokeDashoffset={1 - crack}
          />
        </g>
      ) : null}
    </svg>
  );
};
