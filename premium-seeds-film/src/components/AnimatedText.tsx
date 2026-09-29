import React, {type CSSProperties} from 'react';
import {ease, progress} from '../utils/easing';
import {useSceneFrame} from '../utils/scene';
import {textStyles} from '../styles/typography';

type Variant = keyof typeof textStyles;
type Mode =
  /** Words rise out of a soft blur, staggered. Default for headlines. */
  | 'words'
  /** Each line slides up from behind a mask. */
  | 'mask'
  /** Whole block fades with a slight blur. */
  | 'fade'
  /** Letter-spacing settles from wide to target (wordmarks, caps). */
  | 'track';

export type AnimatedTextProps = {
  text: string;
  /** Scene-local frame at which the entrance starts. */
  start: number;
  /** Scene-local frame at which the exit starts. Omit to stay on. */
  exit?: number;
  variant?: Variant;
  mode?: Mode;
  size: number;
  /** Frames for the entrance. */
  duration?: number;
  exitDuration?: number;
  /** Frames between words for 'words' mode. */
  stagger?: number;
  align?: 'left' | 'center' | 'right';
  maxWidth?: number;
  color?: string;
  style?: CSSProperties;
  /** Override the scene clock (e.g. when the parent computes its own time). */
  frame?: number;
};

/**
 * Premium, restrained type animation. No bounces, no per-letter spins: words
 * surface from a soft focus pull, lines rise from masks, wordmarks settle.
 */
export const AnimatedText: React.FC<AnimatedTextProps> = ({
  text,
  start,
  exit,
  variant = 'headline',
  mode = 'words',
  size,
  duration = 26,
  exitDuration = 16,
  stagger = 3,
  align = 'left',
  maxWidth,
  color,
  style,
  frame: frameOverride,
}) => {
  const sceneFrame = useSceneFrame();
  const frame = frameOverride ?? sceneFrame;
  if (!text) {
    return null;
  }

  const exitP = exit === undefined ? 0 : progress(frame, exit, exitDuration, ease.in);
  const base: CSSProperties = {
    ...textStyles[variant],
    fontSize: size,
    textAlign: align,
    maxWidth,
    ...(color ? {color} : {}),
    ...style,
  };
  const exitStyle: CSSProperties = {
    opacity: 1 - exitP,
    filter: exitP > 0.001 ? `blur(${exitP * 10}px)` : undefined,
    transform: `translateY(${-exitP * 0.12}em)`,
  };

  if (mode === 'fade' || mode === 'track') {
    const p = progress(frame, start, duration, ease.out);
    const trackFrom = mode === 'track' ? 0.9 : 0;
    const targetLs = typeof base.letterSpacing === 'string' ? parseFloat(base.letterSpacing) : 0;
    return (
      <div
        style={{
          ...base,
          opacity: p * (1 - exitP),
          filter: `blur(${(1 - p) * 8 + exitP * 10}px)`,
          letterSpacing: mode === 'track' ? `${targetLs + trackFrom * (1 - p)}em` : base.letterSpacing,
          transform: `translateY(${(1 - p) * 0.15 - exitP * 0.12}em)`,
        }}
      >
        {text}
      </div>
    );
  }

  if (mode === 'mask') {
    const lines = text.split('\n');
    return (
      <div style={{...base, ...exitStyle}}>
        {lines.map((line, i) => {
          const p = progress(frame, start + i * 5, duration, ease.out);
          return (
            <div key={i} style={{overflow: 'hidden', paddingBottom: '0.12em', marginBottom: '-0.12em'}}>
              <div style={{transform: `translateY(${(1 - p) * 110}%)`, opacity: Math.min(1, p * 1.6)}}>{line}</div>
            </div>
          );
        })}
      </div>
    );
  }

  // 'words'
  const words = text.split(' ');
  return (
    <div style={{...base, ...exitStyle}}>
      {words.map((w, i) => {
        const p = progress(frame, start + i * stagger, duration, ease.out);
        return (
          <React.Fragment key={i}>
            <span
              style={{
                display: 'inline-block',
                opacity: p,
                filter: p < 0.999 ? `blur(${(1 - p) * 9}px)` : undefined,
                transform: `translateY(${(1 - p) * 0.32}em)`,
              }}
            >
              {w}
            </span>
            {i < words.length - 1 ? ' ' : null}
          </React.Fragment>
        );
      })}
    </div>
  );
};
