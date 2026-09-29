"""Original score + sound design for the J-WALT film, synthesised in code.

No samples, no loops, no library music: every sound is generated here from
oscillators and seeded noise, so the result is deterministic and its rights
are unambiguous. 120 BPM (beat 0.5s), 30.0s, 48 kHz stereo, 24-bit.

Structure (bar = 2s):
  b1      room tone, datum tick, graphite drag of the first line
  b2      pad enters on the 2.0 downbeat; pencil ticks as the room draws
  b3-4    felt impact on the 4.0 reveal; half-time sub pulse; pluck motif
  b5-6    craft: motif continues, warmer chord
  b7-8    services: pulse on quarters, rule ticks, hats on the off-beat
  b9-11   projects + gallery: fullest texture, wood knocks on the plates
  b12-13  scale: break -- pulse drops, pad + two measured accents
  b14-15  brand: reversed swell into the rise, mallet chord at 26.5,
          decay to silence by 29.8

Every cue time below is taken from src/film/scenes.js.

Usage: python audio/score.py [out.wav]
"""
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
DUR = 30.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(20260929)          # fixed seed: identical every run


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def at(t):
    return int(round(t * SR))


def db(x):
    return 10 ** (x / 20)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x)


def place(bus, x, t, gain=1.0, pan=0.0):
    """Add a mono or stereo event to a stereo bus at time t (equal-power pan)."""
    i = at(t)
    if i >= N:
        return
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l, x * r], 1)
    n = min(len(x), N - i)
    bus[i:i + n] += x[:n] * gain


# ------------------------------------------------------------------ voices

def pad_voice(notes, dur, bright=3.2):
    """Warm, slightly detuned band-limited pad; stereo from detune spread."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for j, m in enumerate(notes):
        f0 = midi(m)
        for k, (cents, pan) in enumerate([(-7, -0.7), (0, 0.0), (6, 0.7)]):
            f = f0 * 2 ** (cents / 1200)
            ph = rng.uniform(0, 2 * np.pi)
            v = np.zeros(n)
            for h in range(1, 9):
                if f * h > 9000:
                    break
                v += np.sin(2 * np.pi * f * h * t + ph * h) * np.exp(-h / bright) / h
            l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
            out[:, 0] += v * l
            out[:, 1] += v * r
    return out / (len(notes) * 3)


def env_ar(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    e[n - nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def pluck(m, dur=1.2, decay=7.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi(m)
    v = np.sin(2 * np.pi * f * t) + 0.28 * np.sin(4 * np.pi * f * t) * np.exp(-t * 14) + 0.08 * np.sin(6 * np.pi * f * t) * np.exp(-t * 22)
    e = np.minimum(t / 0.003, 1) * np.exp(-t * decay)
    return lp(v * e, 3800)


def felt_kick(level=1.0):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 46 + 70 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.minimum(t / 0.004, 1) * np.exp(-t * 9.5)
    click = lp(rng.standard_normal(n) * np.exp(-t * 400), 2500) * 0.08
    return (body + click) * level


def tick(freq=3200, level=1.0, length=0.02):
    n = int(length * SR)
    t = np.arange(n) / SR
    v = bp(rng.standard_normal(n), freq * 0.6, min(freq * 1.8, 20000)) * np.exp(-t * 350)
    v += 0.3 * np.sin(2 * np.pi * freq * 0.7 * t) * np.exp(-t * 180)
    return v * level


def knock(freq=720, level=1.0):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    v = bp(rng.standard_normal(n), freq * 0.85, freq * 1.18, 2) * np.exp(-t * 45) * 2.2
    v += 0.5 * np.sin(2 * np.pi * freq * 0.25 * t) * np.exp(-t * 30)
    return v * level


def hat(level=1.0):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t * 90) * level


def air(t0, t1, lo=300, hi=2400, shape="bell", level=1.0):
    """Filtered-air move following an on-screen motion (not a cartoon whoosh)."""
    n = int((t1 - t0) * SR)
    x = rng.standard_normal(n)
    u = np.linspace(0, 1, n)
    if shape == "bell":
        e = np.sin(np.pi * u) ** 2
    elif shape == "rise":                       # reversed swell into a hit
        e = u ** 3
    else:
        e = (1 - u) ** 2
    y = bp(x, lo, hi, 2) * e
    return np.stack([y * (0.8 + 0.2 * u), y * (1.0 - 0.2 * u)], 1) * level


def mallet(notes, dur=3.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in notes:
        f = midi(m)
        for ratio, amp, dec in [(1, 1.0, 1.6), (2.0, 0.35, 3.0), (3.01, 0.12, 5.0), (4.2, 0.05, 8.0)]:
            out += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dec)
    out *= np.minimum(t / 0.004, 1)
    return lp(out / len(notes), 6000)


def reverb_ir(seconds=2.6, predelay=0.02):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n + int(predelay * SR), 2))
    for c in range(2):
        noise = rng.standard_normal(n) * np.exp(-t * 6.9 / seconds)
        # darker as it decays: blend of lowpassed and bright noise
        dark = lp(noise, 2200)
        mix = np.exp(-t * 3.0)
        ir[int(predelay * SR):, c] = noise * mix * 0.35 + dark * (1 - mix * 0.35)
    return ir / np.sqrt((ir ** 2).sum() / 2)


def convolve(x, ir):
    return np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1)


def delay_pingpong(x, time=0.375, fb=0.32, wet=0.28):
    d = int(time * SR)
    out = np.zeros_like(x)
    tap = x.copy()
    for k in range(1, 6):
        g = wet * fb ** (k - 1)
        shifted = np.zeros_like(x)
        shifted[d * k:] = tap[:-d * k] if d * k < N else 0
        side = 0 if k % 2 else 1
        out[:, side] += shifted[:, 0] * g + shifted[:, 1] * g * 0.3
    return x + lp(out, 3000)


# ------------------------------------------------------------------ loudness

def lufs(x):
    """Integrated loudness, ITU-R BS.1770-4 (48 kHz coefficients)."""
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    z = np.array([(y[i:i + blk] ** 2).mean(0).sum() for i in range(0, len(y) - blk, hop)])
    lk = -0.691 + 10 * np.log10(z + 1e-12)
    z = z[lk > -70]
    rel = -0.691 + 10 * np.log10(z.mean()) - 10
    z = z[-0.691 + 10 * np.log10(z) > rel]
    return -0.691 + 10 * np.log10(z.mean())


def true_peak(x):
    return np.abs(signal.resample_poly(x, 4, 1, axis=0)).max()


def limiter(x, ceiling_db=-1.2, release=0.08):
    """Look-ahead peak limiter on a 4x-oversampled envelope."""
    ceil = db(ceiling_db)
    over = np.abs(signal.resample_poly(x, 4, 1, axis=0)).max(1).reshape(-1, 4).max(1)[:len(x)]
    need = np.minimum(1.0, ceil / np.maximum(over, 1e-9))
    look = int(0.003 * SR)
    need = -np.maximum.accumulate(np.r_[-need[look:], -np.ones(look)][::-1])[::-1]   # min over look-ahead
    g = np.empty_like(need)
    cur, rel = 1.0, np.exp(-1 / (release * SR))
    for i, v in enumerate(need):
        cur = v if v < cur else v + (cur - v) * rel
        g[i] = cur
    return x * g[:, None]


# ------------------------------------------------------------------ score

CHORDS = [   # (start, end, midi notes)
    (0.6, 2.2, [57, 60, 64, 65]),              # Dm9 colour, no root (air)
    (2.0, 4.2, [50, 57, 60, 64, 65]),          # Dm9
    (4.0, 8.2, [46, 53, 57, 60, 62]),          # Bbmaj9
    (8.0, 12.2, [41, 48, 57, 64, 67]),         # Fmaj9
    (12.0, 16.2, [48, 55, 62, 64, 69]),        # C6/9
    (16.0, 20.2, [38, 45, 53, 60, 64]),        # Dm9
    (20.0, 22.2, [46, 53, 57, 60, 62]),        # Bbmaj9
    (22.0, 26.4, [43, 50, 58, 62, 65]),        # Gm9 (break)
    (26.2, 30.0, [41, 48, 55, 57, 64]),        # Fmaj9 resolve
]

# pluck motif: (start, end, chord tones to arpeggiate, pattern of 8th-note hits)
MOTIF = [
    (5.5, 8.0, [65, 69, 72, 74], [1, 0, 1, 0, 0, 1, 0, 0]),
    (8.0, 12.0, [69, 72, 76, 79], [1, 0, 1, 0, 0, 1, 0, 1]),
    (12.0, 16.0, [67, 72, 74, 76], [1, 0, 0, 1, 0, 1, 0, 0]),
    (16.0, 20.0, [65, 69, 72, 76], [1, 0, 1, 0, 0, 1, 0, 1]),
    (20.0, 22.0, [65, 70, 72, 74], [1, 0, 1, 0, 1, 0, 1, 0]),
]


def build():
    music = np.zeros((N, 2))
    fx = np.zeros((N, 2))
    send = np.zeros((N, 2))            # reverb send

    # room tone: barely-there filtered air for the whole film
    room = lp(rng.standard_normal((N, 2)), 900) * db(-58)
    music += room * np.minimum(T / 0.5, 1)[:, None] * np.minimum((29.9 - T) / 0.8, 1).clip(0)[:, None]

    # pad
    for t0, t1, notes in CHORDS:
        v = pad_voice(notes, t1 - t0, bright=2.6 if t0 >= 22 and t0 < 26 else 3.2)
        v *= env_ar(len(v), 0.9 if t0 > 0.5 else 1.4, 0.5 if t1 < 29 else 3.0)[:, None]
        g = db(-21) if t0 >= 2.0 else db(-26)
        place(music, v, t0, g)
        place(send, v, t0, g * 0.6)

    # felt pulse: half-time 4-12, quarters 12-22 (accent on bar downbeats), break 22-26
    beats = [4.0 + k for k in range(8)] + [12.0 + 0.5 * k for k in range(20)]
    for b in beats:
        acc = 1.0 if abs((b / 2) - round(b / 2)) < 1e-6 else 0.72
        place(music, felt_kick(acc), b, db(-19))
    place(music, felt_kick(1.0), 26.5, db(-18))

    # pluck motif through ping-pong delay
    motif = np.zeros((N, 2))
    for t0, t1, tones, pat in MOTIF:
        k = 0
        t = t0
        while t < t1 - 1e-6:
            step = int(round((t - t0) / 0.25)) % 8
            if pat[step]:
                m = tones[k % len(tones)]
                k += 1
                vel = 0.85 if step == 0 else 0.6
                place(motif, pluck(m), t, vel, pan=0.25 * np.sin(k * 1.7))
            t += 0.25
    motif = delay_pingpong(motif)
    music += motif * db(-25)
    send += motif * db(-28)

    # hats on the off-beat, 12-22
    for k in range(20):
        place(music, hat(1.0 if k % 2 else 0.7), 12.25 + 0.5 * k, db(-38), pan=0.3)

    # ---------------- sound design (follows the picture)
    place(fx, tick(3400, 1.0), 0.30, db(-24))                                   # datum mark
    drag_n = int(1.5 * SR)                                                      # the first line
    u = np.linspace(0, 1, drag_n)
    speed = np.sin(np.pi * u) ** 2                                              # arch-ease velocity
    drag = bp(rng.standard_normal(drag_n), 1800, 6000) * speed
    place(fx, np.stack([drag * (1 - 0.7 * u), drag * (0.3 + 0.7 * u)], 1), 0.5, db(-40))
    for i, tt in enumerate([2.0, 2.3, 2.65, 3.0, 3.35]):                        # the room drawing itself
        place(fx, tick(2600 + 300 * i, 0.8), tt, db(-33), pan=0.2 + 0.1 * i)
    place(fx, air(3.1, 4.0, 200, 1800, "rise"), 3.1, db(-31))                  # into the reveal
    imp = felt_kick(1.0) * 1.2 + lp(rng.standard_normal(int(0.9 * SR)) * np.exp(-np.arange(int(0.9 * SR)) / SR * 9), 400) * 0.25
    place(fx, imp, 4.0, db(-17))
    place(send, imp, 4.0, db(-21))

    for t0, t1, lo, hi, lvl in [(7.5, 8.5, 250, 2000, -32),     # cover slide
                                (11.7, 12.2, 300, 2200, -35),   # plate closes to its edge
                                (15.3, 16.5, 250, 1800, -34),   # spine -> seam -> open
                                (17.75, 18.6, 300, 2400, -34),  # close into horizon / open
                                (19.6, 20.0, 300, 2000, -36),   # close down
                                (21.55, 22.1, 300, 2000, -36)]: # gallery taken down
        a = air(t0, t1, lo, hi, "bell")
        place(fx, a, t0, db(lvl))
        place(send, a, t0, db(lvl - 4))

    for k, tt in enumerate([12.4, 12.9, 13.4]):                              # service rules
        place(fx, tick(2200, 0.9), tt, db(-31), pan=-0.2)
    for k, tt in enumerate([20.15, 20.3, 20.45]):                               # gallery plates
        place(fx, knock(680 + 60 * k, 1.0), tt, db(-24), pan=-0.4 + 0.4 * k)
    for tt, m in [(22.45, 74), (24.0, 77)]:                                     # the two milestones
        place(fx, tick(1800, 0.8), tt, db(-30))
        place(music, pluck(m, 2.0, 3.5), tt, db(-27))
        place(send, pluck(m, 2.0, 3.5), tt, db(-26))

    place(fx, air(25.45, 26.35, 200, 1600, "rise"), 25.45, db(-30))            # rule travels to centre
    bell = mallet([65, 69, 72, 76, 79])                                         # wordmark rises
    place(music, bell, 26.5, db(-20), pan=0.0)
    place(send, bell, 26.5, db(-18))
    place(fx, tick(1500, 0.6), 27.15, db(-36))                                  # descriptor lands
    place(fx, tick(1300, 0.5), 27.7, db(-38))                                   # tagline lands

    wet = convolve(send, reverb_ir())
    mix = music + fx + wet * db(-6)
    mix = hp(mix, 28)                                                           # clean subsonics

    # end: nothing after the picture settles; silence by 29.8s
    fade = np.clip((29.8 - T) / 1.3, 0, 1) ** 1.5
    mix *= fade[:, None]
    mix[:at(0.02)] *= np.linspace(0, 1, at(0.02))[:, None]

    # loudness to -16 LUFS (restrained brand film), true peak <= -1 dBTP
    mix *= db(-16 - lufs(mix))
    mix = limiter(mix, -1.2)
    return mix


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    q = np.round(x * (2 ** 23 - 1)).astype(np.int32)
    b = q.astype("<i4").tobytes()
    b = b"".join(b[i:i + 3] for i in range(0, len(b), 4))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "output" / "score.wav")
    mix = build()
    write_wav(out, mix)
    print(f"{out}  {len(mix) / SR:.3f}s  loudness {lufs(mix):.2f} LUFS  true peak {20 * np.log10(true_peak(mix)):.2f} dBTP")
