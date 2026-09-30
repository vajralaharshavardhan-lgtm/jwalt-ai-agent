"""Original score, synthesised. Minimal and architectural: a low D drone, a
slow pad, a felt-piano motif, a precise pulse, glass arpeggios for the
build -- D minor throughout, lifting to D major when the finished space is
revealed. Sections follow the shot list in film.yaml."""
from __future__ import annotations

import numpy as np

from .. import config
from . import dsp as D

BPM = 90.0
BEAT = 60.0 / BPM


def felt_piano(freq, dur, vel=0.5, seed=0, ring=2.6):
    n = D.n_samples(dur + ring)
    t = np.arange(n) / D.SR
    rng = np.random.default_rng(seed)
    B = 0.00032
    base_decay = float(np.clip(3.2 - 0.9 * np.log2(freq / 261.6), 1.0, 5.0))
    y = np.zeros(n)
    for k in range(1, 16):
        fk = k * freq * np.sqrt(1 + B * k * k)
        if fk > 15000:
            break
        amp = (vel ** (0.75 + 0.12 * (k - 1))) / k ** 1.35 * (1 + 0.25 * np.sin(k * 1.7))
        dec = base_decay / (1 + 0.38 * (k - 1))
        for det in (-0.7, 0.7):
            f2 = fk * 2 ** (det / 1200)
            y += amp * 0.5 * np.sin(2 * np.pi * f2 * t + rng.uniform(0, 6.28)) * np.exp(-t / dec)
    att = np.clip(t / 0.005, 0, 1)
    damp = np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.28))
    y *= att * damp
    ham = D.butter(D.noise(n, seed + 7), "lowpass", 900 + 2500 * vel, 2) * np.exp(-t / 0.006) * 0.12 * vel
    y += ham
    cutoff = (1400 + 3200 * vel) * np.exp(-t / 1.6) + 900
    y = D.svf(y, cutoff, 0.6, "lp")
    return y * 0.35


def pad(notes, dur, attack=1.2, release=1.2, cutoff=(700, 1600), level=1.0, seed=0, detune=7.0):
    n = D.n_samples(dur + release)
    t = np.arange(n) / D.SR
    rng = np.random.default_rng(seed)
    L = np.zeros(n)
    R = np.zeros(n)
    for i, f in enumerate(notes):
        for j, c in enumerate((-detune, 0.0, detune)):
            drift = 1 + 0.0015 * np.sin(2 * np.pi * rng.uniform(0.05, 0.15) * t + rng.uniform(0, 6))
            v = D.saw(f * 2 ** (c / 1200) * drift, n) * (0.6 if c == 0 else 0.45)
            p = (j - 1) * 0.6 + rng.uniform(-0.2, 0.2)
            L += v * np.cos((p + 1) * np.pi / 4)
            R += v * np.sin((p + 1) * np.pi / 4)
    c0, c1 = cutoff
    cut = c0 + (c1 - c0) * np.clip(t / max(dur, 1e-3), 0, 1)
    x = np.stack([L, R], -1)
    x = D.svf(x, cut, 0.8, "lp")
    x = D.butter(x, "highpass", 90, 2)
    e = np.clip(t / attack, 0, 1) ** 1.6
    e *= np.where(t < dur, 1.0, np.cos(np.clip((t - dur) / release, 0, 1) * np.pi / 2) ** 2)
    return x * e[:, None] * level * 0.05 / max(len(notes), 1) ** 0.5


def strings(notes, dur, attack=1.5, release=1.5, level=1.0, seed=0, bright=2600):
    n = D.n_samples(dur + release)
    t = np.arange(n) / D.SR
    rng = np.random.default_rng(seed)
    L = np.zeros(n)
    R = np.zeros(n)
    vib = np.clip((t - 0.6) / 1.0, 0, 1)
    for f in notes:
        for k in range(5):
            c = rng.uniform(-9, 9)
            vr = 2 ** ((6 * vib * np.sin(2 * np.pi * rng.uniform(4.8, 5.6) * t + rng.uniform(0, 6))) / 1200)
            v = D.saw(f * 2 ** (c / 1200) * vr, n)
            p = rng.uniform(-0.8, 0.8)
            L += v * np.cos((p + 1) * np.pi / 4)
            R += v * np.sin((p + 1) * np.pi / 4)
    x = np.stack([L, R], -1)
    x = D.svf(x, bright, 0.7, "lp")
    x = D.butter(x, "highpass", 140, 2)
    e = np.clip(t / attack, 0, 1) ** 2
    e *= np.where(t < dur, 1.0, np.cos(np.clip((t - dur) / release, 0, 1) * np.pi / 2) ** 2)
    return x * e[:, None] * level * 0.03 / max(len(notes), 1) ** 0.5


def glass(freq, vel=0.5, seed=0):
    n = D.n_samples(1.4)
    t = np.arange(n) / D.SR
    idx = 2.2 * vel * np.exp(-t / 0.05)
    y = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * freq * 3.0 * t))
    y += 0.3 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t / 0.25)
    y *= np.exp(-t / 0.45) * np.clip(t / 0.002, 0, 1)
    return y * 0.08 * vel


def bass_pluck(freq, dur, vel=0.6, seed=0):
    n = D.n_samples(dur + 0.3)
    t = np.arange(n) / D.SR
    x = D.saw(freq, n) * 0.6 + np.sin(2 * np.pi * freq * t) * 0.8
    cut = 180 + (900 + 900 * vel) * np.exp(-t / 0.09)
    x = D.svf(x, cut, 1.1, "lp")
    e = np.clip(t / 0.004, 0, 1) * np.exp(-t / 0.32) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.05))
    return x * e * 0.22 * vel


def sub_kick(vel=0.6):
    n = D.n_samples(0.5)
    t = np.arange(n) / D.SR
    f = 44 + 48 * np.exp(-t / 0.035)
    y = np.sin(2 * np.pi * np.cumsum(f) / D.SR) * np.exp(-t / 0.2) * np.clip(t / 0.002, 0, 1)
    # upper body so the pulse still reads on small speakers
    body = np.sin(2 * np.pi * np.cumsum(2.6 * f) / D.SR) * np.exp(-t / 0.06) * 0.35
    knock = D.butter(D.noise(n, 7), "bandpass", (180, 1200), 2) * np.exp(-t / 0.012) * 0.12
    return (y * 0.55 + body + knock) * 0.6 * vel


def riser(dur):
    n = D.n_samples(dur)
    t = np.arange(n) / D.SR
    u = t / dur
    nz = D.svf(D.pink(n, 301), 400 + 7000 * u ** 2.2, 1.6, "bp") * 0.07 * u ** 2.4
    tones = sum(np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.35 * u ** 2)) / D.SR) for f0 in (293.7, 440.0, 587.3)) * 0.012 * u ** 3
    x = D.stereo_width(D.pan(nz + tones, 0), 1.5)
    return x


def compose(total: float) -> dict[str, np.ndarray]:
    cfg = config.load()
    S = {s.id: s for s in cfg.shots}
    n = D.n_samples(total + 0.5)
    stems = {k: np.zeros((n, 2)) for k in ("drone", "pad", "keys", "pulse", "bass", "glass", "fx")}

    def put(stem, clip, t0, gain=1.0):
        if clip.ndim == 1:
            clip = D.pan(clip, 0.0)
        D.place(stems[stem], clip, t0, gain)

    # --- drone -------------------------------------------------------------------
    t = np.arange(n) / D.SR
    drone = np.sin(2 * np.pi * 36.71 * t) * 0.55 + np.sin(2 * np.pi * 73.42 * t) * 0.35 + np.sin(2 * np.pi * 110.0 * t) * 0.07
    drone = D.butter(drone, "lowpass", 220, 2)
    lvl = np.interp(t, [0, 1.5, 3.6, 8.0, 16.0, 21.5, 26.8, 27.35, 27.5, 31.5, 33.05, 34.2, total],
                    [0, 0.35, 0.45, 0.55, 0.55, 0.6, 0.95, 0.4, 0.85, 0.75, 1.0, 0.6, 0.0])
    stems["drone"] += D.pan(drone * lvl * 0.10, 0.0)

    # --- pads / strings ------------------------------------------------------------
    h = D.hz
    s2, s3, s4, s5, s6, s7, s8 = (S[k].start for k in ("s02_design", "s03_craft", "s04_engineering", "s05_execution",
                                                       "s06_transformation", "s07_hero", "s08_brand"))
    put("pad", pad([h("D3"), h("A3"), h("E4"), h("F4")], s3 - s2 + 0.3, 1.6, 1.2, (450, 1500), 1.0, 1), s2)
    put("pad", pad([h("Bb2"), h("F3"), h("A3"), h("D4")], s4 - s3 + 0.2, 0.7, 1.0, (900, 1300), 0.9, 2), s3)
    put("pad", pad([h("G2"), h("D3"), h("Bb3"), h("A4")], 2.1, 0.5, 0.6, (800, 1500), 0.9, 3), s4)
    put("pad", pad([h("A2"), h("E3"), h("D4"), h("E4")], 1.3, 0.4, 0.4, (1000, 1700), 0.9, 4), s4 + 2.0)
    put("pad", pad([h("A2"), h("E3"), h("C#4"), h("E4")], 0.9, 0.2, 0.5, (1400, 1900), 0.9, 5), s4 + 3.2)
    put("pad", pad([h("D3"), h("A3"), h("F4")], 2.9, 0.3, 0.5, (700, 1100), 0.7, 6), s5)
    put("pad", pad([h("Bb2"), h("F3"), h("D4")], 1.5, 0.2, 0.5, (700, 1100), 0.7, 7), s5 + 2.8)
    put("pad", pad([h("C3"), h("G3"), h("E4")], 1.4, 0.2, 0.6, (800, 1300), 0.7, 8), s5 + 4.2)
    # the build
    put("pad", strings([h("D3"), h("A3"), h("D4"), h("F4")], 2.1, 1.0, 0.8, 0.8, 9, 2000), s6)
    put("pad", strings([h("Bb2"), h("F3"), h("D4"), h("F4")], 2.0, 0.5, 0.8, 1.0, 10, 2400), s6 + 2.0)
    put("pad", strings([h("C3"), h("G3"), h("E4"), h("G4")], 1.8, 0.5, 0.25, 1.3, 11, 3000), s6 + 4.0)
    # arrival: D major
    put("pad", pad([h("D3"), h("A3"), h("F#4"), h("A4"), h("D5")], s8 - s7 + 0.4, 0.25, 1.4, (1800, 2600), 1.2, 12), s7)
    put("pad", strings([h("D3"), h("A3"), h("F#4"), h("D5")], s8 - s7 + 0.3, 0.6, 1.5, 1.1, 13, 2600), s7)
    put("pad", pad([h("D3"), h("A3"), h("E4"), h("F#4"), h("C#5")], total - s8 - 0.4, 0.8, 1.6, (1500, 1100), 1.0, 14), s8)

    # --- felt piano motif ---------------------------------------------------------------
    motif = [("D5", 0.42), ("A4", 0.36), ("F5", 0.40), ("E5", 0.36), ("D5", 0.34), ("A4", 0.30)]
    for i, (nm, v) in enumerate(motif):
        put("keys", D.pan(felt_piano(h(nm), BEAT * 0.9, v, 20 + i), 0.15 * np.sin(i)), s3 + 0.3 + i * BEAT)
    hero = [("F#5", 0.40), ("E5", 0.36), ("D5", 0.36), ("A4", 0.33)]
    for i, (nm, v) in enumerate(hero):
        put("keys", D.pan(felt_piano(h(nm), BEAT * 1.4, v, 40 + i), 0.12 * np.cos(i)), s7 + 0.45 + i * BEAT * 1.25)
    for nm, v in (("D4", 0.3), ("A4", 0.28), ("F#5", 0.3)):
        put("keys", felt_piano(h(nm), 1.4, v, 50), s7 + 0.45 + 4 * BEAT * 1.25 + 0.5)
    for nm, v in (("D3", 0.34), ("A3", 0.3), ("F#4", 0.3), ("E5", 0.26)):
        put("keys", felt_piano(h(nm), 1.6, v, 60), 33.05)

    # --- pulse -------------------------------------------------------------------------
    k = 0
    tt = s2 + BEAT * 0.5
    while tt < s6 + 5.7:
        if tt < s3:
            v, every = 0.35, 2
        elif tt < s5:
            v, every = 0.42, 1
        else:
            v, every = 0.5 + 0.35 * float(np.clip((tt - s6) / 5.5, 0, 1)), 1
        if k % every == 0:
            put("pulse", sub_kick(v), tt)
        tt += BEAT
        k += 1
    # precise 'clockwork' ticks in ENGINEERING
    tt = s4
    while tt < s5 - 0.1:
        c = D.butter(D.noise(D.n_samples(0.02), int(tt * 1000)), "highpass", 6000, 2) * np.exp(-np.arange(D.n_samples(0.02)) / 40.0)
        put("pulse", D.pan(c * 0.04, 0.4 if int(tt / (BEAT / 2)) % 2 else -0.4), tt)
        tt += BEAT / 2

    # --- bass ostinato (EXECUTION) -------------------------------------------------------
    pat = ["D2", "D2", "F2", "D2", "A1", "D2", "C2", "D2"]
    tt = s5
    i = 0
    while tt < s6 - 0.05:
        nm = pat[i % len(pat)]
        if tt > s5 + 2.8:
            nm = {"D2": "Bb1", "F2": "D2", "A1": "F1", "C2": "C2"}.get(nm, nm)
        if tt > s5 + 4.2:
            nm = {"Bb1": "C2", "D2": "E2", "F1": "G1"}.get(nm, nm)
        put("bass", bass_pluck(h(nm), BEAT / 2 * 0.9, 0.55 + 0.1 * (i % 2 == 0), i), tt)
        tt += BEAT / 2
        i += 1

    # --- glass arpeggio (TRANSFORMATION build) ---------------------------------------------
    chords = [(s6, ["D5", "F5", "A5", "D6", "A5", "F5"]), (s6 + 2.0, ["Bb4", "D5", "F5", "Bb5", "F5", "D5"]),
              (s6 + 4.0, ["C5", "E5", "G5", "C6", "G5", "E5"])]
    tt = s6 + 1.2
    i = 0
    while tt < s7 - 0.2:
        notes = [c for c in chords if c[0] <= tt][-1][1]
        vel = 0.25 + 0.6 * float(np.clip((tt - s6 - 1.2) / 4.6, 0, 1))
        put("glass", D.pan(glass(h(notes[i % len(notes)]), vel, i), -0.6 if i % 2 else 0.6), tt)
        tt += BEAT / 4
        i += 1

    # --- riser, breath, arrival --------------------------------------------------------------
    put("fx", riser(1.5), s7 - 0.15 - 1.5)
    arrival = np.zeros(D.n_samples(3.0))
    ta = np.arange(len(arrival)) / D.SR
    arrival += np.sin(2 * np.pi * np.cumsum(38 + 30 * np.exp(-ta / 0.12)) / D.SR) * np.exp(-ta / 0.9) * 0.35
    put("fx", D.reverb(D.pan(arrival, 0), 0.25, 3.0, 0.02, 0.4), s7)

    # reverb per stem (keys/glass most, pulse least)
    stems["pad"] = D.reverb(stems["pad"], 0.35, 3.6, 0.03, 0.55)
    stems["keys"] = D.reverb(stems["keys"], 0.42, 3.8, 0.035, 0.6, 1.2)
    stems["glass"] = D.reverb(stems["glass"], 0.5, 3.2, 0.03, 0.8, 1.4)
    stems["pulse"] = D.reverb(stems["pulse"], 0.12, 1.4, 0.01, 0.4)
    stems["bass"] = D.reverb(stems["bass"], 0.12, 1.6, 0.01, 0.4)
    return stems
