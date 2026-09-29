#!/usr/bin/env node
/**
 * Generates the film's soundtrack as two stems, timed to src/utils/timeline.ts:
 *
 *   public/audio/generated/music.wav  minimal cinematic score (D major / open fifths)
 *   public/audio/generated/sfx.wav    sound design (seed, crack, growth, lab, wind,
 *                                     crop transitions, slice, dive, logo impact)
 *
 * Deterministic: same output every run. ~2–4 s to render.
 * Replace the score with a licensed track by dropping public/assets/music.mp3.
 *
 *   node scripts/audio/generate-soundtrack.mjs            # always regenerate
 *   node scripts/audio/generate-soundtrack.mjs --if-missing
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {
  SR, ad, encodeWav, felt, glass, hz, makeBuffer, master, mixIn, noiseEvent, pad, ramp, reverb, sine, whiteNoise, filter,
} from './dsp.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const outDir = path.join(root, 'public/audio/generated');
const musicPath = path.join(outDir, 'music.wav');
const sfxPath = path.join(outDir, 'sfx.wav');

if (process.argv.includes('--if-missing') && fs.existsSync(musicPath) && fs.existsSync(sfxPath)) {
  console.log('[audio] generated stems present, skipping (run `npm run audio` to rebuild)');
  process.exit(0);
}

const DUR = 45;
// Scene starts (seconds), mirrored from src/utils/timeline.ts.
const T = {seed: 0, germ: 4, research: 8, field: 13, crops: 18, topgun: 24, harvest: 29, ret: 35, reveal: 40, end: 45};
const LOGO_HIT = 40.95;

// ═════════════════════════════════════ MUSIC ════════════════════════════════
const music = makeBuffer(DUR);

/** Chord pad from t0 to t1 with soft attack/release and cutoff swell. */
const chord = (notes, t0, t1, {gain = 0.12, attack = 1.6, release = 1.8, c0 = 500, c1 = 1400, seed = 1, spread = 0.5} = {}) => {
  const len = t1 - t0 + release;
  notes.forEach((n, i) => {
    const sig = pad(hz(n), len, {
      amp: (t) => ramp(t, 0, attack) * (1 - ramp(t, t1 - t0, t1 - t0 + release)),
      cutoff: (t) => c0 + (c1 - c0) * ramp(t, 0, (t1 - t0) * 0.8),
      seed: seed * 17 + i,
    });
    const pan = notes.length > 1 ? -spread + (2 * spread * i) / (notes.length - 1) : 0;
    mixIn(music, sig, t0, gain, pan);
  });
};

// 1 · Opening drone: open fifth, emerging from silence.
chord(['D2', 'A2'], 0, 12.5, {gain: 0.16, attack: 3.5, release: 2.5, c0: 220, c1: 520, seed: 1, spread: 0.2});
mixIn(music, sine(12, hz('A5'), (t) => 0.012 * ramp(t, 1, 5) * (1 - ramp(t, 9, 12)) * (0.7 + 0.3 * Math.sin(t * 1.7))), 0, 1, 0.4);
mixIn(music, sine(12, hz('E6'), (t) => 0.007 * ramp(t, 2, 6) * (1 - ramp(t, 9, 12)) * (0.7 + 0.3 * Math.sin(t * 1.3))), 0, 1, -0.4);

// 2 · Germination: the fifth gains a third; gentle lift.
chord(['D3', 'F#3'], 4.2, 12.8, {gain: 0.06, attack: 2.5, release: 2, c0: 300, c1: 900, seed: 2});

// 3 · Research: sparse glass notes, like instruments in a quiet lab.
const glassSeq = [
  [8.15, 'A4'], [8.85, 'D5'], [9.55, 'E5'], [10.25, 'F#5'], [10.95, 'A5'], [11.65, 'E5'], [12.35, 'D5'],
];
glassSeq.forEach(([t, n], i) => mixIn(music, glass(hz(n), 3, 0.55 - i * 0.03), t, 0.5, i % 2 ? 0.35 : -0.35));

// 4 · Field: the harmony opens (Dmaj9) with a felt-piano motif.
chord(['D2', 'A2'], 12.8, 24, {gain: 0.12, attack: 1.5, release: 1.5, c0: 260, c1: 600, seed: 3, spread: 0.1});
chord(['D3', 'A3', 'E4', 'F#4'], 13, 21, {gain: 0.07, attack: 2.2, release: 1.2, c0: 600, c1: 1900, seed: 4});
[
  [13.4, 'F#4'], [14.1, 'A4'], [14.8, 'E5'], [15.9, 'D5'], [16.6, 'A4'], [17.3, 'F#4'],
].forEach(([t, n], i) => mixIn(music, felt(hz(n), 3.5, 0.9 - i * 0.05), t, 0.55, i % 2 ? 0.25 : -0.25));

// 5 · Crops: a soft pulse gives momentum; chord moves to Bm7.
chord(['B2', 'F#3', 'A3', 'D4'], 21, 24, {gain: 0.07, attack: 0.8, release: 1.4, c0: 700, c1: 1800, seed: 5});
for (let k = 0; k < 20; k++) {
  const t = 18 + k * 0.3;
  const note = t < 21 ? (k % 2 ? 'A3' : 'D3') : k % 2 ? 'F#3' : 'B2';
  const v = 0.35 + 0.25 * (k / 20);
  mixIn(music, filter(felt(hz(note), 0.6, v), 'lowpass', 900, 0.7), t, 0.6, k % 2 ? 0.2 : -0.2);
}

// 6 · Top Gun: a held breath on Gmaj7, a sub hit on the reveal, shimmer as it ripens.
chord(['G2', 'D3', 'F#3', 'B3'], 24, 29, {gain: 0.08, attack: 0.6, release: 1.2, c0: 400, c1: 1300, seed: 6});
mixIn(music, sine(2.5, (t) => 58 - 18 * Math.min(1, t / 0.6), (t) => 0.35 * ad(t, 0.01, 0.55)), 24.02, 1, 0);
mixIn(music, sine(3, hz('B5'), (t) => 0.03 * ramp(t, 0, 1.4) * (1 - ramp(t, 1.8, 3))), 25.9, 1, 0.3);
mixIn(music, sine(3, hz('F#6'), (t) => 0.02 * ramp(t, 0.2, 1.5) * (1 - ramp(t, 1.8, 3))), 26.0, 1, -0.3);

// 7 · Harvest: warm and open. G → D/F# → A → D, melody above.
chord(['G2', 'D3', 'G3', 'B3'], 29, 30.6, {gain: 0.085, attack: 0.9, release: 0.9, c0: 700, c1: 1800, seed: 7});
chord(['F#2', 'D3', 'A3', 'D4'], 30.5, 32.1, {gain: 0.085, attack: 0.6, release: 0.9, c0: 800, c1: 1900, seed: 8});
chord(['A2', 'E3', 'A3', 'C#4'], 32.0, 33.6, {gain: 0.085, attack: 0.6, release: 0.9, c0: 900, c1: 2100, seed: 9});
chord(['D2', 'D3', 'A3', 'F#4'], 33.5, 35.6, {gain: 0.09, attack: 0.6, release: 1.6, c0: 900, c1: 2200, seed: 10});
[
  [29.2, 'D5'], [29.9, 'B4'], [30.6, 'A4'], [31.5, 'F#5'], [32.1, 'E5'], [33.0, 'C#5'], [33.6, 'D5'], [34.4, 'A5'],
].forEach(([t, n], i) => mixIn(music, felt(hz(n), 3.2, 0.8), t, 0.6, i % 2 ? 0.3 : -0.3));

// 8 · Return to seed: everything recedes to the open fifth; a swell gathers.
chord(['D3', 'A3'], 35.2, 40.4, {gain: 0.08, attack: 1.2, release: 0.6, c0: 900, c1: 350, seed: 11, spread: 0.3});
mixIn(music, noiseEvent(3.2, {type: 'lowpass', freq: (t) => 300 + 2200 * Math.pow(t / 3.2, 2), q: 0.8, shape: (t) => 0.22 * Math.pow(t / 3.2, 2.2) * (1 - ramp(t, 3.05, 3.2)), seed: 31, pink: true}), 37.75, 1, 0);

// 9 · Logo: impact, bell, and a final Dadd9 that rings out.
mixIn(music, sine(3.5, (t) => 62 - 24 * Math.min(1, t / 0.9), (t) => 0.55 * ad(t, 0.005, 0.9)), LOGO_HIT, 1, 0);
mixIn(music, glass(hz('D6'), 4, 0.7), LOGO_HIT + 0.02, 0.45, -0.15);
mixIn(music, glass(hz('A6'), 4, 0.5), LOGO_HIT + 0.05, 0.35, 0.2);
chord(['D2', 'A2', 'D3', 'A3', 'E4', 'F#4'], LOGO_HIT, 45, {gain: 0.075, attack: 0.25, release: 0.3, c0: 1600, c1: 900, seed: 12, spread: 0.7});
mixIn(music, felt(hz('F#5'), 4, 0.5), LOGO_HIT + 1.1, 0.45, 0.2);

reverb(music, {room: 0.86, damp: 0.3, wet: 0.32});

// Final fade.
for (let i = 0; i < music.L.length; i++) {
  const t = i / SR;
  const g = (1 - ramp(t, 43.6, 45)) * ramp(t, 0, 0.4);
  music.L[i] *= g;
  music.R[i] *= g;
}
master(music, -2);

// ═════════════════════════════════════ SFX ══════════════════════════════════
const sfx = makeBuffer(DUR);

const click = (t, {freq = 3200, q = 4, gain = 0.3, len = 0.04, pan = 0, seed = 1} = {}) =>
  mixIn(sfx, noiseEvent(len, {freq, q, shape: (x) => ad(x, 0.001, len / 4), seed}), t, gain, pan);

const whoosh = (t, len, {f0 = 300, f1 = 2400, gain = 0.25, q = 1.2, pan = 0, seed = 5, curve = 1.6} = {}) =>
  mixIn(sfx, noiseEvent(len, {freq: (x) => f0 + (f1 - f0) * Math.pow(x / len, curve), q, shape: (x) => Math.sin(Math.PI * Math.min(1, x / len)) ** 2, seed, pink: true}), t, gain, pan);

// Seed appears: a soft organic "tock".
mixIn(sfx, sine(0.5, (t) => 95 - 30 * Math.min(1, t / 0.2), (t) => 0.35 * ad(t, 0.003, 0.09)), 0.55, 1, 0);
click(0.55, {freq: 1800, q: 3, gain: 0.12, len: 0.05, seed: 2});

// Crack: fine, accelerating crackle.
for (let k = 0; k < 28; k++) {
  const x = k / 27;
  const t = 2.9 + Math.pow(x, 0.7) * 1.0 + (Math.sin(k * 12.9898) * 0.5 + 0.5) * 0.02;
  click(t, {freq: 2600 + ((k * 733) % 3200), q: 5, gain: 0.05 + 0.12 * x, len: 0.02 + 0.02 * ((k * 37) % 3) / 3, pan: ((k * 0.37) % 1) - 0.5, seed: 100 + k});
}
// Light floods out: soft bloom.
whoosh(3.85, 1.4, {f0: 200, f1: 3500, gain: 0.18, seed: 9, curve: 0.8});

// Germination: slow organic growth texture + tiny soil creaks.
mixIn(sfx, noiseEvent(4.2, {freq: (t) => 250 + 900 * (t / 4.2), q: 2.5, shape: (t) => 0.09 * ramp(t, 0, 1.2) * (1 - ramp(t, 3.6, 4.2)), seed: 12, pink: true}), 4.2, 1, 0);
for (let k = 0; k < 9; k++) click(4.6 + k * 0.38 + ((k * 0.13) % 0.1), {freq: 700 + k * 60, q: 6, gain: 0.05, len: 0.05, pan: (k % 3) * 0.3 - 0.3, seed: 200 + k});

// Research: quiet room tone + faint instrument ticks.
mixIn(sfx, noiseEvent(5, {type: 'lowpass', freq: 700, q: 0.7, shape: (t) => 0.05 * ramp(t, 0, 0.8) * (1 - ramp(t, 4.3, 5)), seed: 14, pink: true}), 8, 1, 0);
[8.4, 9.1, 9.3, 10.6, 11.2, 11.9].forEach((t, k) => mixIn(sfx, sine(0.05, 4200 + k * 150, (x) => 0.03 * ad(x, 0.001, 0.008)), t, 1, k % 2 ? 0.5 : -0.5));

// Push into the leaf.
whoosh(12.6, 1.3, {f0: 250, f1: 2600, gain: 0.22, seed: 15});

// Field: wind moving across crops (decorrelated stereo).
const wind = (t0, len, gain, seed) => {
  const mk = (s) => noiseEvent(len, {freq: (t) => 500 + 280 * Math.sin(t * 0.9 + s) + 150 * Math.sin(t * 2.3 + s * 2), q: 0.9, shape: (t) => gain * ramp(t, 0, 1.2) * (1 - ramp(t, len - 1.2, len)) * (0.7 + 0.3 * Math.sin(t * 0.7 + s)), seed: seed + s, pink: true});
  mixIn(sfx, mk(1), t0, 1, -0.6);
  mixIn(sfx, mk(2), t0, 1, 0.6);
};
wind(13.2, 5.2, 0.14, 40);

// Crop transitions: a soft air-swish at each morph (mirrors CropPortfolio timing).
for (let i = 1; i <= 7; i++) {
  const t = 18 + (30 + 18 * (i - 1)) / 30;
  whoosh(t, 0.28, {f0: 1200, f1: 4200, gain: 0.07, q: 1.5, pan: i % 2 ? 0.35 : -0.35, seed: 60 + i, curve: 1});
}

// Into Top Gun; ripening shimmer.
whoosh(23.55, 0.7, {f0: 300, f1: 1800, gain: 0.14, seed: 70});
whoosh(25.9, 1.8, {f0: 3000, f1: 7000, gain: 0.05, q: 2, seed: 71, curve: 1});

// Harvest: warm evening air.
wind(28.6, 6.6, 0.12, 80);

// The slice, then the dive into the seed.
whoosh(35.85, 0.5, {f0: 2500, f1: 9000, gain: 0.2, q: 2.5, seed: 90, curve: 0.7});
mixIn(sfx, noiseEvent(0.25, {type: 'highpass', freq: 3000, q: 0.7, shape: (x) => 0.1 * ad(x, 0.002, 0.05), seed: 91}), 36.1, 1, 0);
whoosh(36.7, 1.9, {f0: 120, f1: 900, gain: 0.2, q: 0.9, seed: 92, curve: 2.2});

// Seed condenses to light, then the logo lands.
mixIn(sfx, sine(1.2, (t) => 1800 + 1400 * t, (t) => 0.025 * ramp(t, 0, 0.9) * (1 - ramp(t, 0.95, 1.2))), 39.9, 1, 0);
mixIn(sfx, noiseEvent(1.6, {type: 'lowpass', freq: 500, q: 0.7, shape: (x) => 0.35 * ad(x, 0.004, 0.35), seed: 95, pink: true}), LOGO_HIT, 1, 0);
mixIn(sfx, noiseEvent(2.5, {type: 'highpass', freq: 6000, q: 0.7, shape: (x) => 0.04 * ad(x, 0.01, 0.8), seed: 96}), LOGO_HIT, 1, 0);

reverb(sfx, {room: 0.8, damp: 0.35, wet: 0.22});
for (let i = 0; i < sfx.L.length; i++) {
  const g = 1 - ramp(i / SR, 43.8, 45);
  sfx.L[i] *= g;
  sfx.R[i] *= g;
}
master(sfx, -3);

// Silence the unused-import linter for whiteNoise (kept for custom SFX).
void whiteNoise;

fs.mkdirSync(outDir, {recursive: true});
fs.writeFileSync(musicPath, encodeWav(music));
fs.writeFileSync(sfxPath, encodeWav(sfx));
console.log(`[audio] wrote ${path.relative(root, musicPath)} and ${path.relative(root, sfxPath)}`);
