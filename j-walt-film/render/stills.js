// Render keyframe stills straight from the film engine (the same seek(t) the
// video renderer will use), as lossless PNGs read back from the canvas.
//
//   node render/stills.js                 -> the four Phase 1 keyframes
//   node render/stills.js 2.5 13.62 ...   -> any times, into render/frames/

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { serve } = require('./server');

const ROOT = path.resolve(__dirname, '..');
const KEYFRAMES = [
  { t: 3.55, name: 'kf1-opening-from-an-idea' },
  { t: 6.6, name: 'kf2-project-heidelberg' },
  { t: 14.6, name: 'kf3-services' },
  { t: 29.0, name: 'kf4-brand-end-frame' },
];

(async () => {
  const args = process.argv.slice(2).map(Number).filter((n) => !Number.isNaN(n));
  const shots = args.length ? args.map((t) => ({ t, name: `t${t.toFixed(3)}` })) : KEYFRAMES;
  const outDir = path.join(ROOT, args.length ? 'render/frames' : 'output/keyframes');
  fs.mkdirSync(outDir, { recursive: true });

  const server = await serve(ROOT);
  const url = `http://127.0.0.1:${server.address().port}/index.html`;
  // grayscale text antialiasing only: LCD subpixel AA colour-fringes type in video
  const browser = await chromium.launch({ args: ['--disable-lcd-text', '--force-color-profile=srgb'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto(url);
  await page.waitForFunction(() => window.film && window.film.ready);
  await page.evaluate(() => window.film.ready);

  for (const s of shots) {
    const res = await page.evaluate((t) => {
      const info = window.film.seek(t);
      return { info, png: window.film.canvas.toDataURL('image/png') };
    }, s.t);
    const file = path.join(outDir, `${s.name}.png`);
    fs.writeFileSync(file, Buffer.from(res.png.split(',')[1], 'base64'));
    const ups = res.info.photos.map((p) => `${p.id}@${p.upscale}x`).join(', ') || 'no photos';
    console.log(`${s.t.toFixed(3)}s  [${res.info.active.join(', ')}]  ${ups}  -> ${path.relative(ROOT, file)}`);
  }
  if (errors.length) console.error('PAGE ERRORS:\n' + errors.join('\n'));
  await browser.close();
  server.close();
  process.exit(errors.length ? 1 : 0);
})();
