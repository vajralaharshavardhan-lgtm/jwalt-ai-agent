import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, useVideoConfig} from 'remotion';
import {ease, progress} from '../utils/easing';

export type Grade = 'natural' | 'warm' | 'cool' | 'night';

const GRADES: Record<Grade, {overlay: string; blend: React.CSSProperties['mixBlendMode']; filter: string}> = {
  natural: {overlay: 'rgba(14,42,28,0.18)', blend: 'soft-light', filter: 'contrast(1.06) saturate(0.95)'},
  warm: {overlay: 'rgba(246,176,96,0.28)', blend: 'soft-light', filter: 'contrast(1.08) saturate(1.02) sepia(0.08)'},
  cool: {overlay: 'rgba(40,80,70,0.25)', blend: 'soft-light', filter: 'contrast(1.05) saturate(0.85)'},
  night: {overlay: 'rgba(6,13,9,0.45)', blend: 'multiply', filter: 'contrast(1.1) saturate(0.8) brightness(0.85)'},
};

export type CinematicImageProps = {
  src: string;
  kind?: 'image' | 'video';
  /** Local frame for the move (0 = start of the move). */
  frame: number;
  /** Length of the Ken Burns move in frames. */
  duration: number;
  scaleFrom?: number;
  scaleTo?: number;
  /** Drift in % of frame over the move. */
  driftX?: number;
  driftY?: number;
  /** Focus point for the scale origin, 0..1. */
  focusX?: number;
  focusY?: number;
  grade?: Grade;
  /** Depth-of-field / defocus blur in px. */
  blur?: number;
  /** Darken toward the edges (0..1). */
  vignette?: number;
  style?: React.CSSProperties;
};

/**
 * Real photo or clip treated like graded footage: slow push, subtle drift,
 * colour grade toward the brand palette, optional defocus and vignette.
 * Used for every drop-in asset slot.
 */
export const CinematicImage: React.FC<CinematicImageProps> = ({
  src,
  kind = 'image',
  frame,
  duration,
  scaleFrom = 1.04,
  scaleTo = 1.12,
  driftX = -1.2,
  driftY = -0.6,
  focusX = 0.5,
  focusY = 0.5,
  grade = 'natural',
  blur = 0,
  vignette = 0.5,
  style,
}) => {
  const {width, height} = useVideoConfig();
  const p = progress(frame, 0, duration, ease.gentle);
  const s = scaleFrom + (scaleTo - scaleFrom) * p;
  const g = GRADES[grade];
  const media: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...style}}>
      <AbsoluteFill
        style={{
          transform: `translate(${driftX * p}%, ${driftY * p}%) scale(${s})`,
          transformOrigin: `${focusX * 100}% ${focusY * 100}%`,
          filter: `${g.filter}${blur > 0.3 ? ` blur(${blur}px)` : ''}`,
        }}
      >
        {kind === 'video' ? <OffthreadVideo src={src} muted style={media} /> : <Img src={src} style={media} />}
      </AbsoluteFill>
      <AbsoluteFill style={{background: g.overlay, mixBlendMode: g.blend}} />
      {vignette > 0 ? (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse ${width > height ? '80% 75%' : '90% 70%'} at 50% 50%, rgba(0,0,0,0) 40%, rgba(0,0,0,${vignette}) 100%)`,
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};
