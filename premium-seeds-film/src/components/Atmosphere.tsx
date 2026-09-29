/**
 * Finishing layers that make generated imagery feel photographed:
 * film grain, lens vignette, drifting particles, bokeh and light leaks.
 */
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {noise2D} from '@remotion/noise';
import {rand} from '../utils/geometry';
import {useLayout} from '../utils/layout';

export const FilmGrain: React.FC<{opacity?: number}> = ({opacity = 0.085}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{mixBlendMode: 'overlay', opacity, pointerEvents: 'none'}}>
      <svg width={width} height={height}>
        <filter id="ps-grain" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={(frame * 7) % 97} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#ps-grain)" />
      </svg>
    </AbsoluteFill>
  );
};

export const Vignette: React.FC<{strength?: number; color?: string}> = ({strength = 0.6, color = '0,0,0'}) => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: `radial-gradient(ellipse 75% 70% at 50% 50%, rgba(${color},0) 45%, rgba(${color},${strength * 0.55}) 80%, rgba(${color},${strength}) 100%)`,
    }}
  />
);

type ParticleProps = {
  count?: number;
  seed?: string;
  /** CSS rgb triplet, e.g. '255,230,190'. */
  color?: string;
  /** Size range in layout units. */
  size?: [number, number];
  /** Drift in layout units per second. */
  drift?: {x: number; y: number};
  opacity?: number;
  /** Depth (0 near … 1 far) that is in focus. */
  focus?: number;
  maxBlur?: number;
  frame?: number;
};

/** Dust / pollen drifting through a shallow depth of field. */
export const Particles: React.FC<ParticleProps> = ({
  count = 40,
  seed = 'dust',
  color = '255,236,200',
  size = [2, 14],
  drift = {x: 6, y: -10},
  opacity = 0.6,
  focus = 0.55,
  maxBlur = 10,
  frame: frameOverride,
}) => {
  const current = useCurrentFrame();
  const frame = frameOverride ?? current;
  const {fps} = useVideoConfig();
  const {width, height, u} = useLayout();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {Array.from({length: count}, (_, i) => {
        const z = rand(`${seed}-z-${i}`);
        const s = (size[1] - (size[1] - size[0]) * z) * u;
        const speed = 1 - z * 0.6;
        const pad = 60 * u;
        const W = width + pad * 2;
        const H = height + pad * 2;
        const x0 = rand(`${seed}-x-${i}`) * W;
        const y0 = rand(`${seed}-y-${i}`) * H;
        const wob = 24 * u;
        let x = x0 + drift.x * u * t * speed + noise2D(`${seed}-nx`, i, t * 0.25) * wob;
        let y = y0 + drift.y * u * t * speed + noise2D(`${seed}-ny`, i, t * 0.25) * wob;
        x = (((x % W) + W) % W) - pad;
        y = (((y % H) + H) % H) - pad;
        const blur = Math.abs(z - focus) * maxBlur * u;
        const tw = 0.55 + 0.45 * noise2D(`${seed}-tw`, i, t * 0.6);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x - s / 2,
              top: y - s / 2,
              width: s,
              height: s,
              borderRadius: '50%',
              background: `radial-gradient(circle, rgba(${color},1) 0%, rgba(${color},0.5) 40%, rgba(${color},0) 70%)`,
              filter: blur > 0.4 ? `blur(${blur}px)` : undefined,
              opacity: opacity * tw * (0.5 + 0.5 * (1 - z)),
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

type BokehProps = {
  count?: number;
  seed?: string;
  colors?: string[];
  /** Radius range in layout units. */
  radius?: [number, number];
  opacity?: number;
  /** Horizontal parallax offset in px (move opposite to the subject for depth). */
  shiftX?: number;
  shiftY?: number;
  area?: {x: number; y: number; w: number; h: number};
};

/** Out-of-focus highlights for backgrounds. */
export const Bokeh: React.FC<BokehProps> = ({
  count = 14,
  seed = 'bokeh',
  colors = ['246,196,124'],
  radius = [30, 110],
  opacity = 0.35,
  shiftX = 0,
  shiftY = 0,
  area,
}) => {
  const {width, height, u} = useLayout();
  const A = area ?? {x: 0, y: 0, w: width, h: height};
  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen'}}>
      {Array.from({length: count}, (_, i) => {
        const r = (radius[0] + rand(`${seed}-r-${i}`) * (radius[1] - radius[0])) * u;
        const depth = rand(`${seed}-d-${i}`);
        const x = A.x + rand(`${seed}-x-${i}`) * A.w + shiftX * (0.4 + depth);
        const y = A.y + rand(`${seed}-y-${i}`) * A.h + shiftY * (0.4 + depth);
        const c = colors[i % colors.length];
        const o = opacity * (0.35 + 0.65 * rand(`${seed}-o-${i}`));
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x - r,
              top: y - r,
              width: r * 2,
              height: r * 2,
              borderRadius: '50%',
              background: `radial-gradient(circle, rgba(${c},${o * 0.55}) 0%, rgba(${c},${o * 0.7}) 58%, rgba(${c},${o}) 66%, rgba(${c},0) 71%)`,
              filter: `blur(${(1.5 + depth * 3) * u}px)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/** Soft warm light bloom drifting across the frame. Screen-blended, subtle. */
export const LightLeak: React.FC<{
  opacity: number;
  x?: number;
  y?: number;
  color?: string;
  size?: number;
}> = ({opacity, x = 0.8, y = 0.2, color = '255,190,120', size = 0.9}) => {
  const {width, height} = useVideoConfig();
  if (opacity <= 0.001) {
    return null;
  }
  const r = Math.max(width, height) * size;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', opacity}}>
      <div
        style={{
          position: 'absolute',
          left: x * width - r / 2,
          top: y * height - r / 2,
          width: r,
          height: r,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(${color},0.85) 0%, rgba(${color},0.35) 30%, rgba(${color},0) 65%)`,
        }}
      />
    </AbsoluteFill>
  );
};
