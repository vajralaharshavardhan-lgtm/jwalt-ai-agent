"""DSP primitives for the score and sound design (48 kHz, float, stereo
arrays shaped (n, 2)). Everything is synthesised here: no sample libraries,
so there is nothing to license."""
from __future__ import annotations

import math

import numpy as np
from numba import njit
from scipy import signal

SR = 48000


def n_samples(sec: float) -> int:
    return int(round(sec * SR))


def t_axis(sec: float) -> np.ndarray:
    return np.arange(n_samples(sec)) / SR


def db(x: float) -> float:
    return 10 ** (x / 20)


def midi(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
NOTE.update({"Db": 1, "Eb": 3, "Gb": 6, "Ab": 8, "Bb": 10})


def hz(name: str) -> float:
    """'D3', 'F#4', 'Bb2' -> Hz."""
    for L in (2, 1):
        if name[:L] in NOTE and name[L:].lstrip("-").isdigit():
            return midi(NOTE[name[:L]] + 12 * (int(name[L:]) + 1))
    raise ValueError(name)


# --- envelopes ------------------------------------------------------------------

def env_adsr(n, a, d, s, r, sustain_n=None):
    a_n, d_n, r_n = max(1, n_samples(a)), max(1, n_samples(d)), max(1, n_samples(r))
    sus = n - a_n - d_n - r_n if sustain_n is None else sustain_n
    sus = max(sus, 0)
    e = np.concatenate([np.linspace(0, 1, a_n, endpoint=False) ** 1.2,
                        1 - (1 - s) * (1 - np.exp(-np.linspace(0, 5, d_n))),
                        np.full(sus, s),
                        s * np.exp(-np.linspace(0, 6, r_n))])
    if len(e) < n:
        e = np.concatenate([e, np.zeros(n - len(e))])
    return e[:n]


def env_exp(n, tau: float, attack: float = 0.002):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-5), 0, 1)
    return a * np.exp(-t / max(tau, 1e-5))


def fade(x, fin=0.0, fout=0.0):
    n = len(x)
    e = np.ones(n)
    if fin > 0:
        k = min(n, n_samples(fin))
        e[:k] = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
    if fout > 0:
        k = min(n, n_samples(fout))
        e[n - k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return x * (e[:, None] if x.ndim == 2 else e)


# --- oscillators ------------------------------------------------------------------

@njit(cache=True)
def _polyblep_saw(phase_inc):
    n = phase_inc.shape[0]
    out = np.empty(n)
    ph = 0.0
    for i in range(n):
        dt = phase_inc[i]
        v = 2.0 * ph - 1.0
        if ph < dt:
            x = ph / dt
            v -= x + x - x * x - 1.0
        elif ph > 1.0 - dt:
            x = (ph - 1.0) / dt
            v -= x * x + x + x + 1.0
        out[i] = v
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
    return out


def saw(freq, n, rng=None):
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,)).copy()
    return _polyblep_saw(f / SR)


def sine(freq, n, phase=0.0):
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def pink(n, seed=0):
    w = np.fft.rfft(noise(n, seed))
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    w /= np.sqrt(f)
    x = np.fft.irfft(w, n)
    return x / (np.std(x) + 1e-12)


# --- filters -----------------------------------------------------------------------

def butter(x, kind, freq, order=2):
    sos = signal.butter(order, freq, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


@njit(cache=True)
def _svf(x, cutoff, q, mode):
    """TPT state-variable filter with per-sample cutoff (Hz). mode 0=LP 1=BP 2=HP."""
    n = x.shape[0]
    y = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    k = 1.0 / q
    for i in range(n):
        g = math.tan(math.pi * min(cutoff[i], 0.49 * 48000.0) / 48000.0)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2
        elif mode == 1:
            y[i] = v1
        else:
            y[i] = x[i] - k * v1 - v2
    return y


def svf(x, cutoff, q=0.707, mode="lp"):
    c = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), (x.shape[0],)).copy()
    m = {"lp": 0, "bp": 1, "hp": 2}[mode]
    if x.ndim == 2:
        return np.stack([_svf(np.ascontiguousarray(x[:, i]), c, q, m) for i in range(x.shape[1])], 1)
    return _svf(np.ascontiguousarray(x, dtype=np.float64), c, q, m)


def shelf(x, freq, gain_db, kind="high"):
    """RBJ shelving EQ."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * freq / SR
    cw, sw = np.cos(w), np.sin(w)
    al = sw / 2 * np.sqrt(2)
    sq = 2 * np.sqrt(A) * al
    if kind == "high":
        b = [A * ((A + 1) + (A - 1) * cw + sq), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sq)]
        a = [(A + 1) - (A - 1) * cw + sq, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sq]
    else:
        b = [A * ((A + 1) - (A - 1) * cw + sq), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sq)]
        a = [(A + 1) + (A - 1) * cw + sq, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sq]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


# --- space ---------------------------------------------------------------------------

def pan(mono, p):
    """Constant-power pan, p in [-1, 1] (scalar or per-sample)."""
    p = np.clip(np.asarray(p, dtype=np.float64), -1, 1)
    a = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], -1)


def stereo_width(x, w):
    m = (x[:, 0] + x[:, 1]) / 2
    s = (x[:, 0] - x[:, 1]) / 2 * w
    return np.stack([m + s, m - s], -1)


_IR_CACHE = {}


def impulse_response(seconds=3.2, predelay=0.018, bright=0.5, seed=3, early=True):
    key = (seconds, predelay, bright, seed, early)
    if key in _IR_CACHE:
        return _IR_CACHE[key]
    n = n_samples(seconds)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    # frequency-dependent decay: split into bands, highs die faster
    bands = [(20, 250, 1.15), (250, 1200, 1.0), (1200, 5000, 0.72), (5000, 16000, 0.42 + 0.3 * bright)]
    for ch in range(2):
        nz = noise(n, seed + ch * 17)
        acc = np.zeros(n)
        for lo, hi, k in bands:
            b = butter(nz, "bandpass", (lo, min(hi, SR / 2 - 100)), 2)
            rt = seconds * 0.55 * k
            acc += b * np.exp(-6.9 * t / rt)
        out[:, ch] = acc
    pd = n_samples(predelay)
    out = np.concatenate([np.zeros((pd, 2)), out])[:n]
    if early:
        rng = np.random.default_rng(seed)
        for _ in range(14):
            d = n_samples(rng.uniform(0.004, 0.06))
            out[d, rng.integers(0, 2)] += rng.uniform(0.2, 0.6) * (1 if rng.random() > 0.5 else -1)
    out /= np.sqrt((out ** 2).sum(0, keepdims=True)).max() + 1e-12
    _IR_CACHE[key] = out
    return out


def reverb(x, mix=0.25, seconds=3.2, predelay=0.02, bright=0.5, width=1.0):
    ir = impulse_response(seconds, predelay, bright)
    if x.ndim == 1:
        x = np.stack([x, x], -1)
    wet = np.stack([signal.oaconvolve(x[:, 0], ir[:, 0])[:len(x)], signal.oaconvolve(x[:, 1], ir[:, 1])[:len(x)]], -1)
    wet = stereo_width(wet, width)
    return x * (1 - mix) + wet * mix * 2.2


def place(buf, clip, t0, gain=1.0):
    """Mix `clip` into `buf` starting at time t0 (seconds). Both (n, 2)."""
    i = n_samples(t0)
    if i >= len(buf):
        return
    if i < 0:
        clip = clip[-i:]
        i = 0
    k = min(len(clip), len(buf) - i)
    buf[i:i + k] += clip[:k] * gain


# --- dynamics / loudness -----------------------------------------------------------------

@njit(cache=True)
def _env_follow(x, att, rel):
    n = x.shape[0]
    y = np.empty(n)
    e = 0.0
    for i in range(n):
        v = x[i]
        c = att if v > e else rel
        e = c * e + (1.0 - c) * v
        y[i] = e
    return y


def compress(x, threshold_db=-18.0, ratio=2.0, attack=0.01, release=0.18, makeup_db=0.0):
    lvl = np.abs(x).max(axis=1) if x.ndim == 2 else np.abs(x)
    att = math.exp(-1 / (attack * SR))
    rel = math.exp(-1 / (release * SR))
    env = _env_follow(lvl, att, rel)
    env_db = 20 * np.log10(env + 1e-9)
    over = np.maximum(env_db - threshold_db, 0)
    gain = db(-over * (1 - 1 / ratio) + makeup_db)
    return x * (gain[:, None] if x.ndim == 2 else gain)


def true_peak_limit(x, ceiling_db=-1.0, lookahead=0.004, release=0.08):
    """Look-ahead limiter on 4x-oversampled peaks (catches inter-sample overs)."""
    ceiling = db(ceiling_db)
    up = signal.resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(axis=1).reshape(-1, 4).max(axis=1)[:len(x)]
    need = np.minimum(1.0, ceiling / np.maximum(pk, 1e-9))
    la = n_samples(lookahead)
    # windowed minimum over the look-ahead, then smooth release
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, size=2 * la + 1, mode="nearest")
    g = np.concatenate([g[la:], np.full(la, g[-1])])
    rel = math.exp(-1 / (release * SR))
    sm = 1 - _env_follow(1 - g, 0.0, rel)
    sm = np.minimum(sm, g)
    return x * sm[:, None]


def k_weight(x):
    # ITU-R BS.1770 pre-filter (48 kHz coefficients)
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x) -> float:
    """Integrated loudness (BS.1770-4 gating)."""
    y = k_weight(x)
    blk, hop = n_samples(0.4), n_samples(0.1)
    ms = []
    for s in range(0, len(y) - blk, hop):
        ms.append((y[s:s + blk] ** 2).mean(axis=0).sum())
    ms = np.array(ms)
    L = -0.691 + 10 * np.log10(ms + 1e-12)
    g1 = ms[L > -70]
    if len(g1) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(g1.mean()) - 10
    g2 = ms[(L > -70) & (L > rel)]
    return float(-0.691 + 10 * np.log10(g2.mean()))
