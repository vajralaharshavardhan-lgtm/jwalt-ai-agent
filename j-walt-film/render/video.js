// Render the film to H.264: every frame is film.seek(f / fps) read back from
// the canvas as a lossless PNG and piped straight into FFmpeg (no frames on
// disk). Several browser pages render in parallel; frames are written in order.
//
//   node render/video.js                         final: 1920x1080, 60 fps, CRF 12
//   node render/video.js --preview               quick check: 30 fps, CRF 20
//   node render/video.js --from 12 --to 16 --out output/clip.mp4
//
// FFmpeg with libx264 must be on PATH or given as $FFMPEG.

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { serve } = require('./server');

const ROOT = path.resolve(__dirname, '..');
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const preview = process.argv.includes('--preview');
const FPS = Number(arg('--fps', preview ? 30 : 60));
const FROM = Number(arg('--from', 0));
const TO = Number(arg('--to', 30));
const OUT = path.resolve(ROOT, arg('--out', preview ? 'output/preview.mp4' : 'output/j-walt-brand-film.mp4'));
const AUDIO = path.resolve(ROOT, arg('--audio', 'output/score.wav'));
const WORKERS = Number(arg('--workers', 4));
const FFMPEG = process.env.FFMPEG || 'ffmpeg';

(async () => {
  const frames = Math.round((TO - FROM) * FPS);
  const server = await serve(ROOT);
  const url = `http://127.0.0.1:${server.address().port}/index.html`;
  const browser = await chromium.launch({ args: ['--disable-lcd-text', '--force-color-profile=srgb'] });
  const pages = [];
  for (let i = 0; i < WORKERS; i++) {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
    page.on('pageerror', (e) => { console.error('PAGE ERROR', e); process.exit(1); });
    await page.goto(url);
    await page.waitForFunction(() => window.film && window.film.ready);
    await page.evaluate(() => window.film.ready);
    pages.push(page);
  }

  const withAudio = fs.existsSync(AUDIO);
  const ff = spawn(FFMPEG, [
    '-y', '-hide_banner', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    ...(withAudio ? ['-ss', String(FROM), '-t', String(TO - FROM), '-i', AUDIO] : []),
    '-map', '0:v', ...(withAudio ? ['-map', '1:a'] : []),
    '-vf', 'scale=in_range=full:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p',
    '-c:v', 'libx264', '-preset', preview ? 'medium' : 'slow', '-crf', preview ? '20' : '12',
    '-profile:v', 'high', '-level:v', '4.2', '-pix_fmt', 'yuv420p',
    '-x264-params', `keyint=${FPS * 2}:min-keyint=${FPS}:aq-mode=3`,
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
    ...(withAudio ? ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000'] : []),
    '-r', String(FPS), '-movflags', '+faststart', OUT,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const ffDone = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))));

  const log = [];
  const pending = new Map();
  let next = 0, issued = 0;
  const t0 = Date.now();
  const write = (buf) => new Promise((res) => (ff.stdin.write(buf) ? res() : ff.stdin.once('drain', res)));

  async function worker(page) {
    while (issued < frames) {
      const f = issued++;
      const t = FROM + f / FPS;
      const r = await page.evaluate((tt) => {
        const info = window.film.seek(tt);
        return { info, png: window.film.canvas.toDataURL('image/png') };
      }, t);
      pending.set(f, Buffer.from(r.png.slice(22), 'base64'));
      log[f] = { t: +t.toFixed(4), scenes: r.info.active, photos: r.info.photos };
      while (pending.has(next)) {
        const buf = pending.get(next);
        pending.delete(next);
        const done = ++next;
        await write(buf);
        if (done % (FPS * 5) === 0) process.stdout.write(`  ${(done / FPS).toFixed(0)}s/${(frames / FPS).toFixed(0)}s  ${((Date.now() - t0) / 1000).toFixed(0)}s elapsed\n`);
      }
    }
  }
  await Promise.all(pages.map(worker));
  ff.stdin.end();
  await ffDone;
  await browser.close();
  server.close();

  const maxUp = Math.max(...log.flatMap((l) => l.photos.map((p) => p.upscale)), 0);
  fs.writeFileSync(OUT.replace(/\.mp4$/, '.frames.json'), JSON.stringify({ fps: FPS, from: FROM, frames, maxUpscale: maxUp, log }));
  console.log(`done: ${path.relative(ROOT, OUT)}  ${frames} frames @ ${FPS}fps  max photo enlargement ${maxUp}x  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  if (maxUp > 1.25) { console.error('FAIL: a photo exceeds 1.25x enlargement'); process.exit(1); }
})();
