/**
 * Shared seedling geometry for Germination (photoreal-ish) and Research
 * (line-art). Both scenes build the SAME plant from these functions so the
 * cut between them is a true match cut.
 *
 * World space: origin = seed centre, 1 unit = 1 px at camera scale 1.
 */
import {noise2D} from '@remotion/noise';
import {type Pt, pt, rotate, sampleCurve} from '../utils/geometry';
import {ease, lerp, progress, tween} from '../utils/easing';

/** Seed resting angle in the soil (degrees). Tip points up-left. */
export const SEED_REST_ROT = -58;

/** Camera at the end of Germination (and start of Research). */
export const GERM_CAMERA_END = {scale: 0.36, offsetY: 0.2};

/** Germination timing (scene-local frames). */
export const GERM = {
  rootStart: 22,
  rootDur: 98,
  shootStart: 40,
  shootDur: 62,
  openStart: 92,
  openDur: 30,
};

/** Seed tip position in world space for a seed of height `size` at rotation `rot` (deg). */
export const seedTip = (size: number, rot: number): Pt => {
  const k = size / 160;
  // Tip (49,6) relative to the seed's visual centre (50,82).
  return rotate(pt(-1 * k, -76 * k), (rot * Math.PI) / 180);
};

/** Heading-integrated organic curve: starts along `angle0`, turns toward `target` angle. */
const growCurve = (start: Pt, angle0: number, target: number, length: number, turn: number, seed: string, wiggle: number) => {
  const steps = 120;
  const pts: Pt[] = [start];
  let a = angle0;
  let p = start;
  const ds = length / steps;
  for (let i = 1; i <= steps; i++) {
    const s = i / steps;
    a += (target - a) * turn + noise2D(seed, s * 3, 0) * wiggle;
    p = pt(p.x + Math.cos(a) * ds, p.y + Math.sin(a) * ds);
    pts.push(p);
  }
  return pts;
};

export const seedlingGeometry = (size: number) => {
  const k = size / 620;
  const tip = seedTip(size, SEED_REST_ROT);
  const tipAngle = ((SEED_REST_ROT - 90) * Math.PI) / 180;
  // Turn through the left (counter-clockwise) so the radicle bends down, not over the seed.
  const root = growCurve(tip, tipAngle, -Math.PI * 1.5, 2100 * k, 0.07, 'root', 0.03);
  // Shoot leaves near the tip, loops out and climbs to the surface.
  const shootStart = pt(tip.x + 10 * k, tip.y + 6 * k);
  const shoot = growCurve(shootStart, tipAngle + 0.5, -Math.PI / 2, 1380 * k, 0.06, 'shoot', 0.012);
  const surfaceY = shoot[shoot.length - 1].y + 220 * k;
  const hairs = Array.from({length: 46}, (_, i) => ({
    at: 0.1 + (i / 46) * 0.6,
    side: i % 2 === 0 ? 1 : -1,
    angle: (noise2D('hairA', i, 0) * 0.6 + 1) * 0.9,
    length: (30 + (noise2D('hairL', i, 0) + 1) * 26) * k,
  }));
  const laterals = [0.42, 0.55, 0.68].map((at, i) => ({
    at,
    side: i % 2 === 0 ? 1 : -1,
    pts: sampleCurve((t) => pt(Math.cos(0.5 + i * 0.2) * t * 260 * k, Math.sin(0.5 + i * 0.2) * t * 240 * k), 20),
  }));
  return {k, tip, root, shoot, surfaceY, hairs, laterals};
};

/** Growth state at scene-local frame f of Germination (also used by Research). */
export const seedlingState = (f: number) => ({
  root: progress(f, GERM.rootStart, GERM.rootDur, ease.gentle),
  shoot: progress(f, GERM.shootStart, GERM.shootDur, ease.inOut),
  open: progress(f, GERM.openStart, GERM.openDur, ease.out),
  hairs: tween(f, [GERM.rootStart + 20, GERM.rootStart + 90], [0, 1], ease.linear),
});

/** Cotyledon leaf outline (points), base at origin pointing along +y (down), length L. */
export const cotyledonShape = (L: number): Pt[] => {
  const w = L * 0.36;
  const pts: Pt[] = [];
  const n = 28;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const y = t * L;
    const x = Math.sin(Math.PI * Math.pow(t, 0.8)) * w;
    pts.push(pt(x, y));
  }
  for (let i = n - 1; i > 0; i--) {
    const t = i / n;
    const y = t * L;
    const x = -Math.sin(Math.PI * Math.pow(t, 0.8)) * w;
    pts.push(pt(x, y));
  }
  return pts;
};

/**
 * Rotation (radians) to apply to each cotyledonShape(): folded downward in
 * the hook while underground → spread up-left / up-right once above soil.
 */
export const cotyledonRotations = (open: number): [number, number] => {
  // Direction angles (0 = +x, π/2 = down in SVG space).
  const left = lerp(Math.PI / 2 + 0.1, Math.PI + 0.62, open);
  const right = lerp(Math.PI / 2 - 0.1, -0.62, open);
  // Shape points along +y (π/2), so subtract that.
  return [left - Math.PI / 2, right - Math.PI / 2];
};
