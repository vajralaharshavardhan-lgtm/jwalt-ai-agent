// Drawing primitives. Every function takes an explicit progress value `p`
// (0..1) computed from t by the caller, so there is no hidden animation state.

import { clamp, lerp } from './math.js';

// ------------------------------------------------------------------ strokes

function stroke(ctx, style, fn) {
  ctx.save();
  ctx.strokeStyle = style.color;
  ctx.globalAlpha = style.alpha ?? 1;
  ctx.lineWidth = style.width ?? 1.5;
  ctx.lineCap = style.cap ?? 'butt';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  fn();
  ctx.stroke();
  ctx.restore();
}

// Straight line drawn from a toward b.
export function lineDraw(ctx, a, b, p, style) {
  if (p <= 0) return;
  stroke(ctx, style, () => {
    ctx.moveTo(a[0], a[1]);
    ctx.lineTo(lerp(a[0], b[0], p), lerp(a[1], b[1], p));
  });
}

// Line that grows from its midpoint outward (used for rules and dimensions).
export function lineFromCentre(ctx, a, b, p, style) {
  if (p <= 0) return;
  const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  stroke(ctx, style, () => {
    ctx.moveTo(lerp(m[0], a[0], p), lerp(m[1], a[1], p));
    ctx.lineTo(lerp(m[0], b[0], p), lerp(m[1], b[1], p));
  });
}

// Centripetal Catmull-Rom resampling: authored polylines become fair curves.
export function smooth(points, perSeg = 14) {
  if (points.length < 3) return points;
  const P = [points[0], ...points, points[points.length - 1]];
  const out = [];
  for (let i = 1; i < P.length - 2; i++) {
    const [p0, p1, p2, p3] = [P[i - 1], P[i], P[i + 1], P[i + 2]];
    const d = (a, b) => Math.pow(Math.hypot(b[0] - a[0], b[1] - a[1]) || 1e-6, 0.5);
    const t0 = 0, t1 = t0 + d(p0, p1), t2 = t1 + d(p1, p2), t3 = t2 + d(p2, p3);
    for (let k = 0; k < perSeg; k++) {
      const t = lerp(t1, t2, k / perSeg);
      const A1 = p0.map((v, j) => ((t1 - t) * v + (t - t0) * p1[j]) / (t1 - t0));
      const A2 = p1.map((v, j) => ((t2 - t) * v + (t - t1) * p2[j]) / (t2 - t1));
      const A3 = p2.map((v, j) => ((t3 - t) * v + (t - t2) * p3[j]) / (t3 - t2));
      const B1 = A1.map((v, j) => ((t2 - t) * v + (t - t0) * A2[j]) / (t2 - t0));
      const B2 = A2.map((v, j) => ((t3 - t) * v + (t - t1) * A3[j]) / (t3 - t1));
      out.push(B1.map((v, j) => ((t2 - t) * v + (t - t1) * B2[j]) / (t2 - t1)));
    }
  }
  out.push(points[points.length - 1]);
  return out;
}

// Polyline drawn along its arc length.
export function pathDraw(ctx, pts, p, style) {
  if (p <= 0 || pts.length < 2) return;
  let total = 0;
  for (let i = 1; i < pts.length; i++) total += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  let remain = total * clamp(p);
  stroke(ctx, style, () => {
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length && remain > 0; i++) {
      const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      const f = Math.min(1, remain / l);
      ctx.lineTo(lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f));
      remain -= l;
    }
  });
}

// Ellipse drawn as a sweep from a start angle.
export function ellipseDraw(ctx, c, rx, ry, rotDeg, p, style, start = -Math.PI / 2) {
  if (p <= 0) return;
  stroke(ctx, style, () => {
    ctx.ellipse(c[0], c[1], rx, ry, (rotDeg * Math.PI) / 180, start, start + p * Math.PI * 2);
  });
}

// Rectangle outline drawn continuously from its bottom-left corner.
export function rectDraw(ctx, r, p, style) {
  const pts = [[r.x, r.y + r.h], [r.x, r.y], [r.x + r.w, r.y], [r.x + r.w, r.y + r.h], [r.x, r.y + r.h]];
  pathDraw(ctx, pts, p, style);
}

// Architectural dimension line: grows from the centre, then the end ticks
// (45° slashes) and extension lines land. Label sits above the line.
export function dimensionLine(ctx, x0, x1, y, p, style, label, labelStyle) {
  if (p <= 0) return;
  lineFromCentre(ctx, [x0, y], [x1, y], p, style);
  const tick = clamp((p - 0.85) / 0.15);
  if (tick > 0) {
    const s = { ...style, alpha: (style.alpha ?? 1) * tick };
    for (const x of [x0, x1]) {
      lineDraw(ctx, [x - 4, y + 4], [x + 4, y - 4], 1, s);
      lineDraw(ctx, [x, y - 9], [x, y + 9], 1, { ...s, width: 1 });
    }
  }
  if (label && labelStyle) {
    const q = clamp((p - 0.5) / 0.5);
    maskedText(ctx, label, (x0 + x1) / 2, y - 12, labelStyle, q, { align: 'center' });
  }
}

// ------------------------------------------------------------------ type

export function setFont(ctx, st) {
  ctx.font = `${st.weight ?? 400} ${st.size}px "Inter Tight"`;
  ctx.letterSpacing = `${((st.track ?? 0) * st.size).toFixed(2)}px`;
  ctx.fontKerning = 'normal';
  ctx.textRendering = 'geometricPrecision';
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = st.color;
}

// Width of a string without the tracking canvas appends after the last glyph.
export function measure(ctx, str, st) {
  setFont(ctx, st);
  return ctx.measureText(str).width - (st.track ?? 0) * st.size;
}

function alignedX(ctx, str, x, st, align) {
  if (align === 'left') return x;
  const w = measure(ctx, str, st);
  return align === 'center' ? x - w / 2 : x - w;
}

export function text(ctx, str, x, y, st, { align = 'left', alpha = 1 } = {}) {
  if (alpha <= 0) return;
  const x0 = alignedX(ctx, str, x, st, align);
  setFont(ctx, st);
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillText(str, x0, y);
  ctx.restore();
}

// Canvas snaps glyphs to whole pixels, so slowly moving text would judder
// (moving only on some frames). Moving text is therefore rasterised once into
// a greyscale sprite and drawn at true sub-pixel positions; text at rest is
// snapped to the pixel grid so it stays razor-sharp.
const SPRITES = new Map();
function sprite(str, st) {
  const key = `${str}|${st.size}|${st.weight}|${st.track}|${st.color}`;
  let s = SPRITES.get(key);
  if (s) return s;
  const probe = document.createElement('canvas').getContext('2d');
  const w = measure(probe, str, st);
  const pad = Math.ceil(st.size * 0.25);
  const asc = Math.ceil(st.size * 1.05), desc = Math.ceil(st.size * 0.35);
  const c = document.createElement('canvas');
  c.width = Math.ceil(w + st.size + 2 * pad);
  c.height = asc + desc;
  const g = c.getContext('2d', { alpha: true });
  setFont(g, st);
  g.fillText(str, pad, asc);
  s = { c, pad, asc, w };
  SPRITES.set(key, s);
  return s;
}

// Text that rises out of its own baseline, as if emerging from a drawn line.
// p=0 hidden below the baseline, p=1 in place. Reverse p for an exit.
export function maskedText(ctx, str, x, y, st, p, { align = 'left', alpha = 1, rise } = {}) {
  if (p <= 0 || alpha <= 0) return;
  const x0 = Math.round(alignedX(ctx, str, x, st, align));
  const sp = sprite(str, st);
  const d = rise ?? st.size * 1.05;
  const offset = (1 - clamp(p)) * d;
  const yy = offset < 0.01 ? Math.round(y) : y + offset;
  ctx.save();
  ctx.beginPath();
  // the mask includes the descender zone: clipping at the baseline would cut
  // comma tails ("5,600" -> "5.600") and the tail of the Q
  ctx.rect(x0 - st.size, y - st.size * 1.3, sp.w + st.size * 2, st.size * 1.3 + (st.descend ?? st.size * 0.3));
  ctx.clip();
  ctx.globalAlpha = alpha;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(sp.c, x0 - sp.pad, yy - sp.asc);
  ctx.restore();
}

// ------------------------------------------------------------------ logo

// The vectorised J-WALT wordmark (assets/logo/jwalt-wordmark.json).
// Placed by its visual bounds: x,y = top-left, w = width in px.
export function logoPlace(logo, x, y, w) {
  const [bx0, by0, bx1, by1] = logo.bounds;
  const s = w / (bx1 - bx0);
  return { s, x, y, w, h: (by1 - by0) * s, tx: x - bx0 * s, ty: y - by0 * s };
}

export function drawLogo(ctx, logo, place, color, { clip, rise = 0, alpha = 1 } = {}) {
  if (alpha <= 0) return;
  ctx.save();
  if (clip) {
    ctx.beginPath();
    ctx.rect(clip.x, clip.y, clip.w, clip.h);
    ctx.clip();
  }
  ctx.globalAlpha = alpha;
  ctx.translate(place.tx, place.ty + rise);
  ctx.scale(place.s, place.s);
  ctx.fillStyle = color;
  ctx.fill(logo.path, 'evenodd');
  ctx.restore();
}
