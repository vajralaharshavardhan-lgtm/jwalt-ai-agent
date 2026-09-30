"""Assemble the soundtrack: sound-design cues from every shot, the score
and a continuous ambience bed -> separate stems + a mastered stereo mix
(-14 LUFS integrated, -1 dBTP), all 48 kHz / 24-bit."""
from __future__ import annotations

import json

import numpy as np
import soundfile as sf

from .. import config
from . import dsp as D
from . import score, sfx

STEM_GAIN_DB = {"drone": -7.0, "pad": -1.0, "keys": 1.5, "pulse": -2.0, "bass": -2.5, "glass": -3.0, "fx": -1.0}
# music intensity arc (dB) -- sparse opening, patient build, arrival, resolution
ARC = ([0.0, 3.6, 8.0, 12.0, 16.0, 21.5, 24.0, 26.9, 27.33, 27.5, 31.5, 33.05, 34.3, 35.0],
       [-10, -8.5, -7.5, -6.5, -4.5, -5.5, -3.0, 0.0, -16, -1.0, -2.5, 0.0, -3.0, -12])
SFX_GAIN_DB = -1.5
AMB_GAIN_DB = -4.0


def collect_cues():
    from ..shots import base
    cues = []
    for sh in base.all_shots():
        cues.extend(sh.cues())
    return sorted(cues, key=lambda c: c.t)


def ambience(total: float) -> np.ndarray:
    n = D.n_samples(total + 0.5)
    t = np.arange(n) / D.SR
    air = D.butter(D.pink(n, 401), "bandpass", (90, 1400), 2)
    room = D.butter(D.pink(n, 402), "bandpass", (120, 3800), 2)
    city = D.butter(D.pink(n, 403), "bandpass", (40, 220), 2)
    mod = 1 + 0.15 * np.sin(2 * np.pi * 0.07 * t) + 0.08 * np.sin(2 * np.pi * 0.19 * t + 1)
    k = [0, 1.2, 8.0, 8.1, 12.0, 12.05, 16.0, 16.05, 21.5, 27.5, 32.0, total]
    a_air = np.interp(t, k, [0, 1, 1, 0.3, 0.3, 1, 1, 0.2, 0.2, 0.1, 0.1, 0])
    a_room = np.interp(t, k, [0, 0, 0, 1, 1, 0.2, 0.2, 1.3, 1.1, 0.9, 0.8, 0])
    a_city = np.interp(t, k, [0, 0, 0, 0.6, 0.6, 0, 0, 0.9, 0.8, 0.7, 0.6, 0])
    L = (air * a_air * 0.010 + room * a_room * 0.006 + city * a_city * 0.008) * mod
    R = (D.butter(D.pink(n, 404), "bandpass", (90, 1400), 2) * a_air * 0.010 +
         D.butter(D.pink(n, 405), "bandpass", (120, 3800), 2) * a_room * 0.006 + city * a_city * 0.008) * mod
    return np.stack([L, R], -1)


def render_all(write: bool = True) -> dict:
    cfg = config.load()
    total = cfg.duration
    n = D.n_samples(total)
    # sound design
    fx = np.zeros((D.n_samples(total + 0.5), 2))
    for i, c in enumerate(collect_cues()):
        gen = sfx.REGISTRY.get(c.kind)
        if gen is None:
            continue
        try:
            clip, pre = gen(c.gain, c.params)
        except TypeError:
            clip, pre = gen(c.gain)
        D.place(fx, clip, c.t - pre)
    # score
    stems = score.compose(total)
    music = np.zeros_like(fx)
    for k, v in stems.items():
        music[:len(v)] += v[:len(music)] * D.db(STEM_GAIN_DB.get(k, 0.0))
    tt = np.arange(len(music)) / D.SR
    music *= (10 ** (np.interp(tt, *ARC) / 20))[:, None]
    amb = ambience(total)
    parts = {"music": music[:n], "sfx": fx[:n] * D.db(SFX_GAIN_DB), "ambience": amb[:n] * D.db(AMB_GAIN_DB)}
    # gentle bus processing
    parts["music"] = D.compress(parts["music"], -22, 1.8, 0.03, 0.3, 1.0)
    mixbus = parts["music"] + parts["sfx"] + parts["ambience"]
    mixbus = D.butter(mixbus, "highpass", 26, 2)
    mixbus = D.shelf(mixbus, 70, -2.0, "low")
    mixbus = D.shelf(mixbus, 9000, 0.8, "high")
    mixbus = D.compress(mixbus, -16, 1.6, 0.02, 0.25)
    # loudness to target, then true-peak limit, then verify
    target = float(cfg.audio["target_lufs"])
    cur = D.lufs(mixbus)
    g = D.db(target - cur)
    master = D.true_peak_limit(mixbus * g, cfg.audio["true_peak_db"])
    for _ in range(2):   # limiter shaves a little loudness: trim and re-limit
        cur2 = D.lufs(master)
        master = D.true_peak_limit(master * D.db(target - cur2), cfg.audio["true_peak_db"])
    fade_n = D.n_samples(0.35)
    master[-fade_n:] *= np.cos(np.linspace(0, np.pi / 2, fade_n))[:, None] ** 2
    stats = {"lufs": round(D.lufs(master), 2), "peak_dbfs": round(20 * np.log10(np.abs(master).max() + 1e-12), 2),
             "cues": len(collect_cues())}
    if write:
        out = config.AUDIO_OUT
        out.mkdir(parents=True, exist_ok=True)
        for k, v in parts.items():
            sf.write(out / f"stem_{k}.wav", (v * g).astype(np.float32), D.SR, subtype="PCM_24")
        sf.write(out / "master.wav", master.astype(np.float32), D.SR, subtype="PCM_24")
        (out / "master.json").write_text(json.dumps(stats, indent=1))
    print("audio:", stats)
    return stats
