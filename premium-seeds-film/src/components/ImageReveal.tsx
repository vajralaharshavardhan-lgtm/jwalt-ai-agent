import React from 'react';
import {AbsoluteFill} from 'remotion';
import {clamp} from '../utils/easing';

export type RevealType = 'soft-wipe-up' | 'soft-wipe-right' | 'iris' | 'split' | 'focus';

/**
 * Masked reveal for any layer (photo, illustration, scene). `progress` 0..1.
 * All reveals are feathered: hard-edged wipes read as templates.
 */
export const ImageReveal: React.FC<{
  progress: number;
  type?: RevealType;
  /** Feather width as a fraction of the frame. */
  feather?: number;
  /** Iris centre for type 'iris', 0..1. */
  cx?: number;
  cy?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({progress, type = 'soft-wipe-up', feather = 0.18, cx = 0.5, cy = 0.5, children, style}) => {
  const p = clamp(progress);
  if (p <= 0) {
    return null;
  }
  if (p >= 1 && type !== 'focus') {
    return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
  }
  let mask: string | undefined;
  let extra: React.CSSProperties = {};
  const f = feather * 100;
  if (type === 'soft-wipe-up') {
    const edge = -f + p * (100 + 2 * f);
    mask = `linear-gradient(to top, black ${edge - f}%, transparent ${edge + f}%)`;
  } else if (type === 'soft-wipe-right') {
    const edge = -f + p * (100 + 2 * f);
    mask = `linear-gradient(to right, black ${edge - f}%, transparent ${edge + f}%)`;
  } else if (type === 'iris') {
    const r = p * 150;
    mask = `radial-gradient(circle at ${cx * 100}% ${cy * 100}%, black ${Math.max(0, r - f)}%, transparent ${r + f * 0.5}%)`;
  } else if (type === 'split') {
    const half = p * 50 + f;
    mask = `linear-gradient(to bottom, transparent ${50 - half}%, black ${50 - half + f}%, black ${50 + half - f}%, transparent ${50 + half}%)`;
  } else if (type === 'focus') {
    extra = {opacity: p, filter: p < 0.999 ? `blur(${(1 - p) * 24}px)` : undefined, transform: `scale(${1.04 - 0.04 * p})`};
  }
  return (
    <AbsoluteFill style={{WebkitMaskImage: mask, maskImage: mask, ...extra, ...style}}>
      {children}
    </AbsoluteFill>
  );
};
