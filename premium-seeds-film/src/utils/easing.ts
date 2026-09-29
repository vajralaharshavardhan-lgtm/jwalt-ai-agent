import {Easing, interpolate} from 'remotion';

type EaseFn = (t: number) => number;

/** The film's motion vocabulary. Everything eases; nothing bounces. */
export const ease = {
  /** Long, patient settle. Camera moves, big reveals. */
  cinematic: Easing.bezier(0.45, 0, 0.12, 1) as EaseFn,
  /** Fast start, soft landing. Text entrances. */
  out: Easing.bezier(0.16, 1, 0.3, 1) as EaseFn,
  /** Symmetric. Morphs, crossfades. */
  inOut: Easing.bezier(0.65, 0, 0.35, 1) as EaseFn,
  /** Slow start. Exits. */
  in: Easing.bezier(0.55, 0, 0.85, 0.35) as EaseFn,
  /** Very soft in-out for continuous drifts. */
  gentle: Easing.bezier(0.37, 0, 0.63, 1) as EaseFn,
  linear: ((t: number) => t) as EaseFn,
};

const clampOpts = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** Interpolate `frame` from [f0, f1] to [v0, v1] with easing, clamped. */
export const tween = (
  frame: number,
  [f0, f1]: [number, number],
  [v0, v1]: [number, number],
  easing: EaseFn = ease.inOut,
) => interpolate(frame, [f0, f1], [v0, v1], {...clampOpts, easing});

/** 0 → 1 progress over [start, start + duration]. */
export const progress = (frame: number, start: number, duration: number, easing: EaseFn = ease.inOut) =>
  tween(frame, [start, start + duration], [0, 1], easing);

/** Rise over [inStart, inStart+inDur], hold, fall over [outStart, outStart+outDur]. */
export const envelope = (
  frame: number,
  inStart: number,
  inDur: number,
  outStart: number,
  outDur: number,
  easeIn: EaseFn = ease.out,
  easeOut: EaseFn = ease.in,
) => Math.min(progress(frame, inStart, inDur, easeIn), 1 - progress(frame, outStart, outDur, easeOut));

export const clamp = (v: number, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
/** Map v from [a, b] to 0..1, clamped. */
export const norm = (v: number, a: number, b: number) => clamp((v - a) / (b - a));
export const smoothstep = (a: number, b: number, v: number) => {
  const t = norm(v, a, b);
  return t * t * (3 - 2 * t);
};
