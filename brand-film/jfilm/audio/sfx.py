"""Sound design library. Each generator returns (stereo clip, pre_roll_s):
the clip is placed so that its designed 'moment' lands exactly on the cue
time (pre_roll = how much of the clip precedes that moment).

Palette: precise clicks, metal and glass modes, soft air, low weight.
Nothing cartoonish, no stock 'whoosh' presets."""
from __future__ import annotations

import numpy as np

from . import dsp as D


def _modal(freqs, decays, amps, n, seed=0, strike=0.0015):
    t = np.arange(n) / D.SR
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    for f, d, a in zip(freqs, decays, amps):
        y += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    y *= np.clip(t / strike, 0, 1)
    return y


def click(seed=0, bright=1.0, dur=0.05):
    n = D.n_samples(dur)
    nz = D.noise(n, seed) * D.env_exp(n, 0.0012 + 0.001 * (1 - bright), 0.0002)
    y = D.butter(nz, "highpass", 2200 + 2500 * bright, 2)
    ping = _modal([2600 * (0.9 + 0.2 * bright), 5300], [0.012, 0.006], [0.35, 0.15], n, seed)
    return y * 0.9 + ping


def first_line(gain=1.0, params=None):
    """The opening: a precise tick, then a thin pure tone that opens outward
    in stereo as the line extends from the centre."""
    dur = 1.6
    n = D.n_samples(dur)
    t = np.arange(n) / D.SR
    tick = np.zeros(n)
    c = click(3, 0.8, 0.06)
    tick[:len(c)] = c
    tone_env = np.clip(t / 0.08, 0, 1) * np.exp(-np.maximum(t - 0.55, 0) / 0.35)
    tone = (np.sin(2 * np.pi * 1318.5 * t) * 0.5 + np.sin(2 * np.pi * 2637 * t) * 0.12) * tone_env * 0.11
    air = D.butter(D.noise(n, 5), "bandpass", (5000, 12000), 2) * tone_env * 0.03
    spread = np.clip(t / 0.62, 0, 1)
    L = tick * 0.9 + (tone + air) * (1.0 - 0.0 * spread)
    left = D.pan(tone * 1.0 + air, -0.7 * spread) + D.pan(tick, 0.0)
    right = D.pan(tone * 1.0 + air, 0.7 * spread)
    out = left + right
    out = D.reverb(out, 0.35, 2.6, 0.03, 0.7)
    return out * gain * 0.9, 0.0


def tick(gain=1.0, params=None, seed=None):
    s = int(np.random.default_rng(seed).integers(0, 10000)) if seed is None else seed
    c = click(s, 0.6 + 0.4 * np.random.default_rng(s).random(), 0.04) * 0.5
    p = np.random.default_rng(s + 1).uniform(-0.45, 0.45)
    out = D.reverb(D.pan(c, p), 0.3, 1.8, 0.02, 0.6)
    return out * gain, 0.0


def draw_texture(gain=1.0, params=None):
    """Graphite-on-vellum / electric drawing: sparse micro-grains."""
    dur = (params or {}).get("dur", 1.2)
    n = D.n_samples(dur + 0.3)
    rng = np.random.default_rng(11)
    y = np.zeros((n, 2))
    k = int(dur * 55)
    for i in range(k):
        t0 = rng.uniform(0, dur)
        c = click(int(rng.integers(0, 1e6)), rng.uniform(0.7, 1.0), 0.012) * rng.uniform(0.05, 0.16)
        D.place(y, D.pan(c, rng.uniform(-0.7, 0.7)), t0)
    hiss = D.butter(D.noise(n, 12), "bandpass", (3500, 9000), 2) * 0.012
    e = D.env_adsr(n, 0.2, 0.1, 1.0, 0.3)
    y += D.pan(hiss * e, 0.0)
    return D.reverb(y, 0.25, 1.6, 0.02, 0.7) * gain, 0.0


def illuminate(gain=1.0, params=None):
    n = D.n_samples(2.4)
    t = np.arange(n) / D.SR
    e = np.clip(t / 0.45, 0, 1) ** 2 * np.exp(-np.maximum(t - 0.45, 0) / 0.7)
    nz = D.svf(D.pink(n, 21), 700 + 2600 * np.clip(t / 0.5, 0, 1), 1.4, "bp") * 0.05
    chord = sum(np.sin(2 * np.pi * D.hz(nm) * t) for nm in ("D6", "A6", "E7")) * 0.012
    out = D.pan((nz + chord) * e, 0)
    out = D.stereo_width(D.reverb(out, 0.5, 3.0, 0.03, 0.8), 1.4)
    return out * gain, 0.3


def rise(gain=1.0, params=None):
    """Walls extruding: low air rising, fine mechanical ratchet accelerating."""
    dur = (params or {}).get("dur", 1.6)
    n = D.n_samples(dur + 0.8)
    t = np.arange(n) / D.SR
    u = np.clip(t / dur, 0, 1)
    e = np.sin(np.pi * np.clip(u, 0, 1)) ** 0.8 * (t < dur + 0.6)
    air = D.svf(D.pink(n, 31), 140 + 900 * u ** 1.5, 0.9, "lp") * 0.16
    sub = np.sin(2 * np.pi * (38 + 12 * u) * t) * 0.10 * e
    y = D.pan(air * e + sub, 0.0)
    rng = np.random.default_rng(32)
    tt = 0.0
    while tt < dur:
        rate = 14 + 50 * (tt / dur) ** 1.4
        c = click(int(rng.integers(0, 1e6)), 0.45, 0.02) * 0.06 * np.sin(np.pi * tt / dur)
        D.place(y, D.pan(c, rng.uniform(-0.5, 0.5)), tt)
        tt += 1 / rate
    return D.reverb(y, 0.3, 2.2, 0.02, 0.5) * gain, 0.0


def title_in(gain=1.0, params=None):
    n = D.n_samples(1.6)
    t = np.arange(n) / D.SR
    e = np.clip(t / 0.35, 0, 1) ** 2.2 * np.exp(-np.maximum(t - 0.35, 0) / 0.28)
    air = D.butter(D.noise(n, 41), "highpass", 5500, 2) * 0.035 * e
    shim = (np.sin(2 * np.pi * 2349 * t) * 0.02 + np.sin(2 * np.pi * 3520 * t) * 0.012) * np.exp(-np.maximum(t - 0.3, 0) / 0.5) * np.clip(t / 0.3, 0, 1)
    out = D.stereo_width(D.reverb(D.pan(air + shim, 0), 0.45, 2.5, 0.03, 0.8), 1.5)
    return out * gain, 0.3


def swell(gain=1.0, params=None):
    dur = (params or {}).get("dur", 1.4)
    n = D.n_samples(dur + 1.0)
    t = np.arange(n) / D.SR
    e = np.sin(np.pi * np.clip(t / (dur + 0.6), 0, 1)) ** 1.5
    lo = D.svf(D.pink(n, 51), 300 + 500 * np.clip(t / dur, 0, 1), 0.8, "lp") * 0.12
    return D.reverb(D.pan(lo * e, 0), 0.4, 2.8, 0.03, 0.4) * gain, 0.0


def sweep(gain=1.0, params=None):
    """Material sweep travelling toward camera: filtered air, far -> near."""
    dur = (params or {}).get("dur", 1.0)
    n = D.n_samples(dur + 0.9)
    t = np.arange(n) / D.SR
    u = np.clip(t / dur, 0, 1)
    e = np.sin(np.pi * u) ** 1.3 * (1 - 0.0 * u)
    x = D.svf(D.pink(n, 61), 500 + 5200 * u ** 1.6, 1.1, "bp") * 0.09 * e
    out = np.stack([x * (0.7 + 0.3 * u), x * (0.7 + 0.3 * u)], -1)
    out = D.stereo_width(out, 0.4 + 1.2 * u[:, None].mean())
    return D.reverb(out, 0.35, 2.4, 0.02, 0.7) * gain, 0.0


def light_on(gain=1.0, params=None, seed=None):
    s = 71 if seed is None else seed
    n = D.n_samples(1.4)
    t = np.arange(n) / D.SR
    rly = _modal([1180, 2710, 4400], [0.006, 0.004, 0.002], [0.35, 0.2, 0.1], n, s) * 0.6
    bloom_e = np.clip(t / 0.12, 0, 1) * np.exp(-t / 0.55)
    hum = (np.sin(2 * np.pi * 100 * t) * 0.3 + np.sin(2 * np.pi * 200 * t) * 0.12) * bloom_e * 0.03
    glow = D.butter(D.noise(n, s + 1), "bandpass", (2500, 7000), 2) * bloom_e * 0.012
    out = D.pan(rly + hum + glow, np.random.default_rng(s).uniform(-0.3, 0.3))
    return D.reverb(out, 0.3, 1.8, 0.015, 0.6) * gain, 0.0


def cut(gain=1.0, params=None):
    n = D.n_samples(0.6)
    t = np.arange(n) / D.SR
    puff = D.butter(D.noise(n, 81), "lowpass", 2400, 2) * np.clip(t / 0.01, 0, 1) * np.exp(-t / 0.08) * 0.05
    return D.reverb(D.pan(puff, 0), 0.25, 1.4, 0.01, 0.5) * gain, 0.0


def cut_hit(gain=1.0, params=None):
    n = D.n_samples(1.2)
    t = np.arange(n) / D.SR
    f = 62 * np.exp(-t / 0.08) + 40
    thud = np.sin(2 * np.pi * np.cumsum(f) / D.SR) * np.exp(-t / 0.13) * 0.55
    c = np.zeros(n)
    cc = click(91, 0.5, 0.04) * 0.35
    c[:len(cc)] = cc
    body = D.butter(D.noise(n, 92), "bandpass", (180, 900), 2) * np.exp(-t / 0.03) * 0.12
    return D.reverb(D.pan(thud + c + body, 0), 0.2, 1.6, 0.012, 0.4) * gain, 0.0


def lock(gain=1.0, params=None, seed=None):
    """A panel clipping home: bright metal modes over a small low thump."""
    s = 101 if seed is None else seed
    rng = np.random.default_rng(s)
    n = D.n_samples(0.9)
    t = np.arange(n) / D.SR
    f0 = 1700 * rng.uniform(0.92, 1.1)
    metal = _modal([f0, f0 * 2.76, f0 * 5.40, f0 * 8.93], [0.045, 0.025, 0.012, 0.007], [0.4, 0.25, 0.12, 0.06], n, s)
    thump = np.sin(2 * np.pi * np.cumsum(95 * np.exp(-t / 0.03) + 55) / D.SR) * np.exp(-t / 0.05) * 0.35
    snap = click(s + 3, 0.9, 0.03)
    y = metal * 0.5 + thump
    y[:len(snap)] += snap * 0.4
    return D.reverb(D.pan(y, rng.uniform(-0.35, 0.35)), 0.22, 1.5, 0.012, 0.6) * gain, 0.0


def electric(gain=1.0, params=None):
    n = D.n_samples(1.6)
    t = np.arange(n) / D.SR
    r = _modal([1450, 3300], [0.008, 0.004], [0.5, 0.25], n, 111)
    e = np.clip(t / 0.25, 0, 1) ** 1.5 * np.exp(-np.maximum(t - 0.25, 0) / 0.6)
    hum = (np.sin(2 * np.pi * 100 * t) * 0.25 + np.sin(2 * np.pi * 300 * t) * 0.06) * e * 0.05
    sparkle = D.butter(D.noise(n, 112), "bandpass", (4000, 10000), 2) * e * 0.02
    return D.reverb(D.pan(r * 0.6 + hum + sparkle, 0.1), 0.35, 2.2, 0.015, 0.7) * gain, 0.0


def stone_tap(seed, level=1.0):
    n = D.n_samples(0.25)
    t = np.arange(n) / D.SR
    rng = np.random.default_rng(seed)
    body = _modal([rng.uniform(380, 520), rng.uniform(900, 1200), rng.uniform(2100, 2600)],
                  [0.018, 0.009, 0.004], [0.5, 0.3, 0.12], n, seed)
    nz = D.butter(D.noise(n, seed), "bandpass", (1200, 5000), 2) * np.exp(-t / 0.004) * 0.35
    return (body + nz) * level


def tile_wave(gain=1.0, params=None):
    dur = (params or {}).get("dur", 0.9)
    n = D.n_samples(dur + 1.0)
    y = np.zeros((n, 2))
    rng = np.random.default_rng(121)
    k = 26
    for i in range(k):
        u = i / (k - 1)
        tt = dur * (u ** 1.35)
        D.place(y, D.pan(stone_tap(int(rng.integers(0, 1e6)), rng.uniform(0.35, 0.7)), -0.7 + 1.4 * u + rng.uniform(-0.15, 0.15)), tt)
    return D.reverb(y, 0.25, 1.8, 0.015, 0.55) * gain * 0.7, 0.0


def glass_slide(gain=1.0, params=None):
    dur = (params or {}).get("dur", 0.6)
    n = D.n_samples(dur + 0.6)
    t = np.arange(n) / D.SR
    u = np.clip(t / dur, 0, 1)
    e = np.sin(np.pi * u) ** 0.9 * (t < dur)
    fr = D.svf(D.noise(n, 131), 2600 + 1400 * u, 3.0, "bp") * 0.05 * e
    ring = (np.sin(2 * np.pi * 3150 * t) * 0.006 + np.sin(2 * np.pi * 5120 * t) * 0.004) * e
    return D.reverb(D.pan(fr + ring, 0.6 - 0.8 * u), 0.3, 2.0, 0.015, 0.8) * gain, 0.0


def glass_lock(gain=1.0, params=None):
    n = D.n_samples(1.8)
    t = np.arange(n) / D.SR
    clink = _modal([2330, 5610, 9140, 12400], [0.35, 0.18, 0.08, 0.04], [0.25, 0.15, 0.08, 0.04], n, 141)
    thud = np.sin(2 * np.pi * np.cumsum(110 * np.exp(-t / 0.02) + 60) / D.SR) * np.exp(-t / 0.06) * 0.3
    return D.reverb(D.pan(clink * 0.6 + thud, -0.1), 0.35, 2.4, 0.015, 0.8) * gain, 0.0


def mech(gain=1.0, params=None, up=True):
    """Servo glide + fine gear ticks for the exploded view separating/joining."""
    dur = (params or {}).get("dur", 1.4)
    n = D.n_samples(dur + 0.8)
    t = np.arange(n) / D.SR
    u = np.clip(t / dur, 0, 1)
    shape = np.sin(np.pi * u) ** 0.7 * (t < dur + 0.05)
    f = (95 + 70 * u) if up else (165 - 70 * u)
    whir = D.svf(D.saw(f, n) + 0.5 * D.saw(f * 2.01, n), 900 + 700 * u, 2.0, "bp") * 0.035 * shape
    y = D.pan(whir, 0)
    rng = np.random.default_rng(151 if up else 152)
    tt = 0.0
    while tt < dur:
        rate = 20 + 25 * np.sin(np.pi * tt / dur)
        c = click(int(rng.integers(0, 1e6)), 0.6, 0.015) * 0.05
        D.place(y, D.pan(c, rng.uniform(-0.6, 0.6)), tt)
        tt += 1 / rate
    low = np.sin(2 * np.pi * 48 * t) * 0.06 * shape
    y += D.pan(low, 0)
    return D.reverb(y, 0.25, 1.8, 0.015, 0.5) * gain, 0.0


def transform_bed(gain=1.0, params=None):
    dur = (params or {}).get("dur", 5.0)
    n = D.n_samples(dur + 1.5)
    t = np.arange(n) / D.SR
    u = np.clip(t / dur, 0, 1)
    shape = np.clip(t / 0.8, 0, 1) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.4))
    tex = D.svf(D.pink(n, 161), 600 + 3000 * u ** 1.5, 1.2, "bp") * 0.05 * shape
    shim = D.butter(D.noise(n, 162), "bandpass", (6000, 12000), 2) * 0.012 * shape * u
    y = D.stereo_width(D.pan(tex + shim, 0), 1.6)
    return D.reverb(y, 0.4, 2.6, 0.02, 0.7) * gain, 0.0


def niche_glow(gain=1.0, params=None):
    n = D.n_samples(2.6)
    t = np.arange(n) / D.SR
    e = np.clip(t / 0.5, 0, 1) ** 2 * np.exp(-np.maximum(t - 0.5, 0) / 1.0)
    tones = sum(a * np.sin(2 * np.pi * D.hz(nm) * t) for nm, a in (("D5", 0.03), ("A5", 0.02), ("F#6", 0.012)))
    return D.stereo_width(D.reverb(D.pan(tones * e, 0), 0.55, 3.0, 0.03, 0.8), 1.5) * gain, 0.2


def logo_hit(gain=1.0, params=None):
    n = D.n_samples(4.5)
    t = np.arange(n) / D.SR
    f = 50 * np.exp(-t / 0.35) + 30
    boom = np.sin(2 * np.pi * np.cumsum(f) / D.SR) * np.exp(-t / 1.1) * 0.55 * np.clip(t / 0.004, 0, 1)
    cc = click(171, 0.4, 0.05) * 0.25
    body = D.butter(D.noise(n, 172), "lowpass", 700, 2) * np.exp(-t / 0.08) * 0.12
    y = boom + body
    y[:len(cc)] += cc
    bells = np.zeros(n)
    for nm, a, d in (("D6", 0.03, 1.6), ("A6", 0.02, 1.3), ("F#7", 0.012, 1.0), ("E7", 0.008, 0.9)):
        fr = D.hz(nm)
        bells += a * np.sin(2 * np.pi * fr * t + 2.2 * np.sin(2 * np.pi * fr * 3.5 * t) * np.exp(-t / 0.4)) * np.exp(-t / d)
    out = D.pan(y, 0) + D.stereo_width(D.pan(bells, 0), 1.6)
    return D.reverb(out, 0.35, 4.0, 0.03, 0.6) * gain, 0.0


def shimmer(gain=1.0, params=None):
    n = D.n_samples(3.0)
    t = np.arange(n) / D.SR
    e = np.clip(t / 0.3, 0, 1) * np.exp(-t / 1.1)
    s = D.butter(D.noise(n, 181), "bandpass", (7000, 14000), 2) * 0.012 * e
    return D.stereo_width(D.reverb(D.pan(s, 0), 0.6, 3.2, 0.03, 0.9), 1.6) * gain, 0.0


def ambience_in(gain=1.0, params=None):
    return np.zeros((1, 2)), 0.0   # handled by the continuous ambience bed


REGISTRY = {
    "first_line": first_line, "tick": tick, "draw_texture": draw_texture, "illuminate": illuminate, "rise": rise,
    "title_in": title_in, "swell": swell, "sweep": sweep, "light_on": light_on, "cut": cut, "cut_hit": cut_hit,
    "lock": lock, "electric": electric, "tile_wave": tile_wave, "glass_slide": glass_slide, "glass_lock": glass_lock,
    "mech_rise": lambda g=1.0, p=None: mech(g, p, True), "mech_fall": lambda g=1.0, p=None: mech(g, p, False),
    "transform_bed": transform_bed, "niche_glow": niche_glow, "logo_hit": logo_hit, "shimmer": shimmer,
    "ambience_in": ambience_in,
}
