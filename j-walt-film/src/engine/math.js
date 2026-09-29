// Deterministic math + easing. Nothing here reads the clock or Math.random:
// every frame is a pure function of t.

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const mix = (a, b, t) => (Array.isArray(a) ? a.map((v, i) => lerp(v, b[i], t)) : lerp(a, b, t));
export const progress = (t, t0, t1) => clamp((t - t0) / (t1 - t0));

// CSS-identical cubic-bezier easing (Newton-Raphson with bisection fallback).
export function cubicBezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = (u) => ((ax * u + bx) * u + cx) * u;
  const sy = (u) => ((ay * u + by) * u + cy) * u;
  const dx = (u) => (3 * ax * u + 2 * bx) * u + cx;
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let u = x;
    for (let i = 0; i < 8; i++) {
      const e = sx(u) - x;
      if (Math.abs(e) < 1e-7) return sy(u);
      const d = dx(u);
      if (Math.abs(d) < 1e-6) break;
      u -= e / d;
    }
    let lo = 0, hi = 1;
    u = x;
    while (hi - lo > 1e-7) {
      if (sx(u) < x) lo = u; else hi = u;
      u = (lo + hi) / 2;
    }
    return sy(u);
  };
}

// A small, deliberate set of curves. No overshoot, no bounce.
export const ease = {
  linear: (t) => t,
  arch: cubicBezier(0.65, 0, 0.35, 1),    // measured in-out: lines, masks, panels
  reveal: cubicBezier(0.16, 1, 0.3, 1),   // decisive start, long settle: type, reveals
  camera: cubicBezier(0.37, 0, 0.25, 1),  // camera moves: soft start, no hard stop
  exit: cubicBezier(0.5, 0, 0.75, 0),     // things leaving
  drift: (t) => t,                         // constant-velocity drift (reads as a real dolly)
};

// Eased 0..1 progress of t through [t0, t1].
export const seg = (t, t0, t1, e = ease.arch) => e(progress(t, t0, t1));

// Keyframe track: keys = [[t, value, easeToNext], ...]; values may be numbers or arrays.
export function track(keys) {
  return (t) => {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 0; i < keys.length - 1; i++) {
      const [t0, v0, e = ease.camera] = keys[i];
      const [t1, v1] = keys[i + 1];
      if (t < t1) return mix(v0, v1, e(progress(t, t0, t1)));
    }
    return keys[keys.length - 1][1];
  };
}

// Seeded PRNG (mulberry32) -- only for things like grain, always seeded by frame.
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
