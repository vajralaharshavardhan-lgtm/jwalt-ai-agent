// The film: a pure function of time. seek(t) repaints the frame at t seconds
// from nothing -- no state carries between frames, so any frame can be
// rendered in any order (and in parallel) with identical results.

import { W, H, C } from './theme.js';
import { loadAssets, loadFonts } from './assets.js';
import { SCENES } from './scenes.js';

export const DURATION = 30;
export const FPS = 60;

export function createFilm(canvas) {
  canvas.width = W;
  canvas.height = H;
  // alpha:true on purpose: Chromium uses LCD (RGB-subpixel) text antialiasing
  // on opaque canvases, which colour-fringes type in video. Every frame is
  // fully painted with paper, so the output is opaque anyway.
  const ctx = canvas.getContext('2d', { alpha: true });
  let A = null;
  let last = { t: -1, active: [], photos: [] };

  const ready = (async () => {
    await loadFonts();
    A = await loadAssets();
    return true;
  })();

  function seek(t) {
    if (!A) throw new Error('film not ready');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
    ctx.fillStyle = C.paper;
    ctx.fillRect(0, 0, W, H);
    const stats = [];
    const active = [];
    for (const sc of SCENES) {
      if (t >= sc.t0 && t < sc.t1) {
        active.push(sc.name);
        sc.draw(ctx, t, A, stats);
      }
    }
    last = { t, active, photos: stats };
    return last;
  }

  return { ready, seek, duration: DURATION, fps: FPS, info: () => last, canvas };
}
