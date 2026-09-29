/**
 * Tiny offline DSP kit for the generated soundtrack. No dependencies.
 * Everything is deterministic (seeded noise), so the score is identical on
 * every machine.
 */
export const SR = 48000;

export const makeBuffer = (seconds) => ({
  L: new Float32Array(Math.ceil(seconds * SR)),
  R: new Float32Array(Math.ceil(seconds * SR)),
});

// ── Random / noise ──────────────────────────────────────────────────────────
export const rng = (seed = 1) => {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return ((s >>> 0) / 4294967296) * 2 - 1;
  };
};

export const whiteNoise = (n, seed) => {
  const r = rng(seed);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = r();
  return out;
};

/** Paul Kellet's pink-noise filter. */
export const pinkNoise = (n, seed) => {
  const r = rng(seed);
  const out = new Float32Array(n);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < n; i++) {
    const w = r();
    b0 = 0.99886 * b0 + w * 0.0555179;
    b1 = 0.99332 * b1 + w * 0.0750759;
    b2 = 0.969 * b2 + w * 0.153852;
    b3 = 0.8665 * b3 + w * 0.3104856;
    b4 = 0.55 * b4 + w * 0.5329522;
    b5 = -0.7616 * b5 - w * 0.016898;
    out[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
    b6 = w * 0.115926;
  }
  return out;
};

// ── Filters (RBJ biquads), cutoff may be a function of sample index ────────
const biquadCoefs = (type, f, q) => {
  const w0 = (2 * Math.PI * Math.min(f, SR * 0.45)) / SR;
  const cos = Math.cos(w0);
  const alpha = Math.sin(w0) / (2 * q);
  let b0, b1, b2;
  const a0 = 1 + alpha;
  const a1 = -2 * cos;
  const a2 = 1 - alpha;
  if (type === 'lowpass') {
    b0 = (1 - cos) / 2; b1 = 1 - cos; b2 = (1 - cos) / 2;
  } else if (type === 'highpass') {
    b0 = (1 + cos) / 2; b1 = -(1 + cos); b2 = (1 + cos) / 2;
  } else {
    // bandpass, constant peak gain
    b0 = alpha; b1 = 0; b2 = -alpha;
  }
  return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
};

export const filter = (input, type, freq, q = 0.707) => {
  const out = new Float32Array(input.length);
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  const dynamic = typeof freq === 'function';
  let c = biquadCoefs(type, dynamic ? freq(0) : freq, q);
  for (let i = 0; i < input.length; i++) {
    if (dynamic && i % 64 === 0) c = biquadCoefs(type, freq(i), q);
    const x = input[i];
    const y = c[0] * x + c[1] * x1 + c[2] * x2 - c[3] * y1 - c[4] * y2;
    x2 = x1; x1 = x; y2 = y1; y1 = y;
    out[i] = y;
  }
  return out;
};

// ── Envelopes ───────────────────────────────────────────────────────────────
/** Attack/decay-to-zero envelope value at time t (s). */
export const ad = (t, attack, decay) => (t < 0 ? 0 : t < attack ? t / attack : Math.exp(-(t - attack) / decay));

/** Smooth fade 0→1 between a and b (seconds). */
export const ramp = (t, a, b) => {
  if (t <= a) return 0;
  if (t >= b) return 1;
  const x = (t - a) / (b - a);
  return x * x * (3 - 2 * x);
};

// ── Mixing ──────────────────────────────────────────────────────────────────
/** Add a mono signal into a stereo buffer at `start` seconds, equal-power pan (-1..1). */
export const mixIn = (buf, mono, start, gain = 1, pan = 0) => {
  const s0 = Math.round(start * SR);
  const gl = Math.cos(((pan + 1) * Math.PI) / 4) * gain;
  const gr = Math.sin(((pan + 1) * Math.PI) / 4) * gain;
  for (let i = 0; i < mono.length; i++) {
    const j = s0 + i;
    if (j < 0 || j >= buf.L.length) continue;
    buf.L[j] += mono[i] * gl;
    buf.R[j] += mono[i] * gr;
  }
};

export const mixStereo = (buf, src, start, gain = 1) => {
  const s0 = Math.round(start * SR);
  for (let i = 0; i < src.L.length; i++) {
    const j = s0 + i;
    if (j < 0 || j >= buf.L.length) continue;
    buf.L[j] += src.L[i] * gain;
    buf.R[j] += src.R[i] * gain;
  }
};

// ── Voices ──────────────────────────────────────────────────────────────────
export const hz = (note) => {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(note);
  const base = {C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11}[m[1]];
  const acc = m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0;
  const midi = 12 * (Number(m[3]) + 1) + base + acc;
  return 440 * Math.pow(2, (midi - 69) / 12);
};

/**
 * Warm analogue-style pad: detuned saws through a lowpass, slow envelope.
 * `amp(t)` and `cutoff(t)` are functions of local time in seconds.
 */
export const pad = (freq, seconds, {amp, cutoff, detune = 0.006, voices = 5, seed = 1}) => {
  const n = Math.ceil(seconds * SR);
  const raw = new Float32Array(n);
  const r = rng(seed);
  const phases = Array.from({length: voices}, () => (r() + 1) / 2);
  const ratios = Array.from({length: voices}, (_, v) => 1 + (v - (voices - 1) / 2) * detune + r() * 0.0015);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let v = 0; v < voices; v++) {
      phases[v] += (freq * ratios[v]) / SR;
      if (phases[v] >= 1) phases[v] -= 1;
      s += phases[v] * 2 - 1;
    }
    raw[i] = s / voices;
  }
  const f = filter(filter(raw, 'lowpass', (i) => cutoff(i / SR), 0.6), 'lowpass', (i) => cutoff(i / SR) * 1.4, 0.5);
  for (let i = 0; i < n; i++) f[i] *= amp(i / SR);
  return f;
};

/** Pure sine with optional pitch glide and amplitude function. */
export const sine = (seconds, freq, amp) => {
  const n = Math.ceil(seconds * SR);
  const out = new Float32Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    ph += (typeof freq === 'function' ? freq(t) : freq) / SR;
    out[i] = Math.sin(2 * Math.PI * ph) * amp(t);
  }
  return out;
};

/** Soft felt-piano-like tone: decaying harmonics, gentle attack. */
export const felt = (freq, seconds = 3.5, velocity = 1) => {
  const n = Math.ceil(seconds * SR);
  const out = new Float32Array(n);
  const partials = [
    [1, 1, 1.6],
    [2, 0.42, 0.9],
    [3, 0.18, 0.55],
    [4, 0.08, 0.4],
    [5.02, 0.04, 0.3],
  ];
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    let s = 0;
    for (const [k, a, d] of partials) s += Math.sin(2 * Math.PI * freq * k * t) * a * Math.exp(-t / d);
    out[i] = s * Math.min(1, t / 0.012) * velocity * 0.5;
  }
  return filter(out, 'lowpass', 2600, 0.7);
};

/** Glass / bell: inharmonic partials, long ring. */
export const glass = (freq, seconds = 3, velocity = 1) => {
  const n = Math.ceil(seconds * SR);
  const out = new Float32Array(n);
  const partials = [
    [1, 1, 1.8],
    [2.76, 0.35, 0.9],
    [5.4, 0.16, 0.45],
    [8.93, 0.06, 0.25],
  ];
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    let s = 0;
    for (const [k, a, d] of partials) s += Math.sin(2 * Math.PI * freq * k * t) * a * Math.exp(-t / d);
    out[i] = s * Math.min(1, t / 0.004) * velocity * 0.35;
  }
  return out;
};

/** Filtered noise event. `shape(t)` amplitude, `freq(t)` bandpass centre. */
export const noiseEvent = (seconds, {type = 'bandpass', freq, q = 1, shape, seed = 7, pink = false}) => {
  const n = Math.ceil(seconds * SR);
  const src = pink ? pinkNoise(n, seed) : whiteNoise(n, seed);
  const out = filter(src, type, typeof freq === 'function' ? (i) => freq(i / SR) : freq, q);
  for (let i = 0; i < n; i++) out[i] *= shape(i / SR);
  return out;
};

// ── Freeverb ────────────────────────────────────────────────────────────────
const COMBS = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617];
const ALLPASSES = [556, 441, 341, 225];

export const reverb = (buf, {room = 0.84, damp = 0.25, wet = 0.3, dry = 1, spread = 23} = {}) => {
  const k = SR / 44100;
  const run = (input, offset) => {
    const combs = COMBS.map((d) => ({b: new Float32Array(Math.round((d + offset) * k)), i: 0, f: 0}));
    const aps = ALLPASSES.map((d) => ({b: new Float32Array(Math.round((d + offset) * k)), i: 0}));
    const out = new Float32Array(input.length);
    for (let n = 0; n < input.length; n++) {
      const x = input[n] * 0.015;
      let s = 0;
      for (const c of combs) {
        const y = c.b[c.i];
        c.f = y * (1 - damp) + c.f * damp;
        c.b[c.i] = x + c.f * room;
        c.i = (c.i + 1) % c.b.length;
        s += y;
      }
      for (const a of aps) {
        const y = a.b[a.i];
        a.b[a.i] = s + y * 0.5;
        a.i = (a.i + 1) % a.b.length;
        s = y - s;
      }
      out[n] = s;
    }
    return out;
  };
  const mono = new Float32Array(buf.L.length);
  for (let i = 0; i < mono.length; i++) mono[i] = (buf.L[i] + buf.R[i]) * 0.5;
  const wl = run(mono, 0);
  const wr = run(mono, spread);
  const scaleWet = wet * 3;
  for (let i = 0; i < mono.length; i++) {
    buf.L[i] = buf.L[i] * dry + wl[i] * scaleWet;
    buf.R[i] = buf.R[i] * dry + wr[i] * scaleWet;
  }
  return buf;
};

// ── Output ──────────────────────────────────────────────────────────────────
/** Normalise to `peakDb` with a gentle tanh soft-clip. */
export const master = (buf, peakDb = -1.5) => {
  let peak = 0;
  for (let i = 0; i < buf.L.length; i++) peak = Math.max(peak, Math.abs(buf.L[i]), Math.abs(buf.R[i]));
  const target = Math.pow(10, peakDb / 20);
  const g = peak > 0 ? (target / peak) * 1.15 : 1;
  for (let i = 0; i < buf.L.length; i++) {
    buf.L[i] = Math.tanh(buf.L[i] * g) * target;
    buf.R[i] = Math.tanh(buf.R[i] * g) * target;
  }
  return buf;
};

export const encodeWav = (buf) => {
  const n = buf.L.length;
  const data = Buffer.alloc(44 + n * 4);
  data.write('RIFF', 0);
  data.writeUInt32LE(36 + n * 4, 4);
  data.write('WAVE', 8);
  data.write('fmt ', 12);
  data.writeUInt32LE(16, 16);
  data.writeUInt16LE(1, 20);
  data.writeUInt16LE(2, 22);
  data.writeUInt32LE(SR, 24);
  data.writeUInt32LE(SR * 4, 28);
  data.writeUInt16LE(4, 32);
  data.writeUInt16LE(16, 34);
  data.write('data', 36);
  data.writeUInt32LE(n * 4, 40);
  for (let i = 0; i < n; i++) {
    data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, buf.L[i])) * 32767), 44 + i * 4);
    data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, buf.R[i])) * 32767), 46 + i * 4);
  }
  return data;
};
