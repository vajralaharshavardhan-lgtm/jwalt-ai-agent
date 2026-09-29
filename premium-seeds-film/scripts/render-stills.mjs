#!/usr/bin/env node
/**
 * Render review stills (bundles once, renders many frames).
 *
 *   npm run stills                                  # key frames of the 16:9 film
 *   npm run stills -- --comp=PremiumSeedsFilmVertical
 *   npm run stills -- --frames=0,60,120 --out=out/stills --scale=0.5
 */
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v ?? 'true'];
  }),
);

const compId = args.comp ?? 'PremiumSeedsFilm';
// Default: two frames per scene: a mid-scene hero frame and a transition frame.
const DEFAULT_FRAMES = [20, 75, 112, 150, 215, 262, 330, 400, 470, 520, 575, 640, 700, 760, 840, 900, 990, 1040, 1080, 1150, 1225, 1290, 1330];
const frames = args.frames ? args.frames.split(',').map(Number) : DEFAULT_FRAMES;
const outDir = path.join(root, args.out ?? `out/stills/${compId}`);
const scale = Number(args.scale ?? 0.5);
fs.mkdirSync(outDir, {recursive: true});

const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts')});
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE ?? null;
const composition = await selectComposition({serveUrl, id: compId, browserExecutable});

for (const frame of frames) {
  const output = path.join(outDir, `${compId}-f${String(frame).padStart(4, '0')}.jpg`);
  await renderStill({
    serveUrl,
    composition,
    frame,
    output,
    imageFormat: 'jpeg',
    jpegQuality: 90,
    scale,
    browserExecutable,
    overwrite: true,
  });
  console.log(`[stills] ${path.relative(root, output)}`);
}
