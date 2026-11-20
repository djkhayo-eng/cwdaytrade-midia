import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
SR = 44100
rng = np.random.default_rng(11)

def filt(x, fc, kind="low", order=2):
    b, a = butter(order, fc / (SR / 2), kind); return lfilter(b, a, x)

def env(n, a=0.005, d=0.3):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)

def kick(depth=110, dec=0.14):
    n = int(0.4 * SR); t = np.arange(n) / SR
    f = 45 + depth * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)

def b808(freq, dur, drive=2.5):
    n = int(dur * SR); t = np.arange(n) / SR
    f = freq * (1 + 1.2 * np.exp(-t / 0.015))
    s = np.tanh(drive * np.sin(2 * np.pi * np.cumsum(f) / SR))
    return s * np.minimum(t / 0.004, 1) * np.minimum((dur - t) / 0.03, 1).clip(0, 1)

def clap():
    n = int(0.25 * SR)
    x = filt(rng.standard_normal(n), 1100, "high") * env(n, 0.001, 0.08)
    return x

def snare():
    n = int(0.25 * SR); t = np.arange(n) / SR
    return 0.6 * filt(rng.standard_normal(n), 1800, "high") * np.exp(-t / 0.09) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)

def hat(d=0.03):
    n = int(0.08 * SR)
    return filt(rng.standard_normal(n), 7500, "high") * env(n, 0.001, d)

def cowbell(f=560, d=0.18):
    n = int(0.35 * SR); t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * f * t)) + np.sign(np.sin(2 * np.pi * f * 1.48 * t))
    return filt(s, 2500) * np.exp(-t / d) * 0.4

def pad(freqs, dur, cut=900, a=0.4):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in freqs:
        for det in (-0.006, 0, 0.006):
            ph = 2 * np.pi * f * (1 + det) * t
            s += sum(np.sin(k * ph) / k for k in (1, 2, 3, 4, 5))
    s = filt(s, cut)
    return s * np.minimum(t / a, 1) * np.minimum((dur - t) / 0.3, 1).clip(0, 1) / (len(freqs) * 3)

def epiano(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in freqs:
        s += (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.3)) * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t))
    return filt(s, 2500) * np.exp(-t / (dur * 0.7)) * np.minimum(t / 0.01, 1) / len(freqs)

def pluck(f, dur=0.35, d=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t)
    return s * env(n, 0.002, d)

def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n); y = np.zeros(n); step = 2048
    for i in range(0, n, step):
        fc = 300 + 7000 * (i / n) ** 2
        y[i:i + step] = filt(x[i:i + step + 200], fc)[: len(x[i:i + step])]
    return y * (t / dur) ** 2

def impact():
    n = int(2.2 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.6)
            + 0.5 * filt(rng.standard_normal(n), 2500) * np.exp(-t / 0.4))

# ---------- SFX ----------
def sfx_whoosh(d=0.45):
    n = int(d * SR); t = np.arange(n) / SR; x = rng.standard_normal(n); y = np.zeros(n); step = 512
    for i in range(0, n, step):
        p = i / n; fc = 400 + 5000 * np.sin(np.pi * p) ** 2
        y[i:i + step] = filt(x[i:i + step + 100], fc)[: len(x[i:i + step])]
    return y * np.sin(np.pi * t / d) ** 2 * 0.8

def sfx_pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 900 * np.exp(-t / 0.02) + 250
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04)

def sfx_tick():
    n = int(0.05 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.008) * 0.6

def sfx_ding():
    n = int(0.8 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318.5 * t) + 0.6 * np.sin(2 * np.pi * 1975.5 * t)) * np.exp(-t / 0.25) * 0.45

def sfx_buzz():
    n = int(0.25 * SR); t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 110 * t)) + 0.5 * np.sign(np.sin(2 * np.pi * 116 * t))
    return filt(s, 1200) * np.exp(-t / 0.12) * 0.35

def sfx_hit():
    n = int(1.0 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.3)
            + 0.4 * filt(rng.standard_normal(n), 3000) * np.exp(-t / 0.12))

def sfx_cash():
    a = np.zeros(int(0.9 * SR)); tk = sfx_tick(); a[:len(tk)] += tk; i = int(0.06 * SR); a[i:i + len(tk)] += tk
    d = sfx_ding(); j = int(0.1 * SR); a[j:j + len(d)] += d[: len(a) - j]
    return a

def sfx_rewind():
    n = int(0.8 * SR); t = np.arange(n) / SR
    f = 300 + 2500 * (t / 0.8) ** 1.5
    s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25 + 0.4 * filt(rng.standard_normal(n), 3000)
    return s * np.minimum(t / 0.05, 1) * np.minimum((0.8 - t) / 0.1, 1).clip(0, 1) * 0.6

def sfx_shutter():
    n = int(0.18 * SR); t = np.arange(n) / SR
    a = filt(rng.standard_normal(n), 2500, "high") * (np.exp(-t / 0.012) + 0.7 * np.exp(-np.maximum(t - 0.07, 0) / 0.015) * (t > 0.07))
    return a * 0.8

def sfx_type():
    n = int(0.04 * SR); t = np.arange(n) / SR
    return filt(rng.standard_normal(n), 1800, "high") * np.exp(-t / 0.006) * 0.5

def sfx_beep():
    n = int(0.12 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1000 * t) * np.minimum((0.12 - t) / 0.02, 1) * 0.3

SFX = dict(rewind=sfx_rewind, shutter=sfx_shutter, type=sfx_type, beep=sfx_beep, whoosh=sfx_whoosh, pop=sfx_pop, tick=sfx_tick, ding=sfx_ding, buzz=sfx_buzz, hit=sfx_hit, cash=sfx_cash)

class Mix:
    def __init__(s, dur): s.dur = dur; s.N = int(SR * dur); s.out = np.zeros((s.N, 2))
    def add(s, sig, t0, pan=0.0, g=1.0):
        i = int(t0 * SR)
        if i >= s.N: return
        sig = np.asarray(sig)[: s.N - i]
        s.out[i:i + len(sig), 0] += sig * g * (1 - max(0, pan))
        s.out[i:i + len(sig), 1] += sig * g * (1 + min(0, pan))

def hz(note):  # 'A2'
    names = {'C': -9, 'C#': -8, 'Db': -8, 'D': -7, 'D#': -6, 'Eb': -6, 'E': -5, 'F': -4, 'F#': -3, 'Gb': -3, 'G': -2, 'G#': -1, 'Ab': -1, 'A': 0, 'A#': 1, 'Bb': 1, 'B': 2}
    n, o = note[:-1], int(note[-1])
    return 440 * 2 ** ((names[n] + 12 * (o - 4)) / 12)

def chord(root, kind="m", oct=3):
    r = hz(root + str(oct)); iv = {"m": [0, 3, 7], "M": [0, 4, 7], "m7": [0, 3, 7, 10], "M7": [0, 4, 7, 11]}[kind]
    return [r * 2 ** (i / 12) for i in iv]

def track(path, dur, bpm, prog, style, drop_at=None, outro=3.5):
    """prog: list of (root, kind); style: dark|bright|chill|phonk"""
    B = 60 / bpm; bar = 4 * B; m = Mix(dur); nb = int(np.ceil(dur / bar))
    for b in range(nb):
        t0 = b * bar; root, kind = prog[b % len(prog)]; ch = chord(root, kind)
        intro = t0 < (drop_at if drop_at is not None else bar * 0.5)
        end = t0 >= dur - outro
        rootf = hz(root + "1")
        if style == "piano":
            m.add(pad([f * 2 for f in ch], bar, 1300, a=1.0), t0, g=0.35)
            for k, f in enumerate([ch[0] * 2, ch[2] * 2, ch[1] * 4, ch[2] * 2]):
                m.add(epiano([f], 2.2 * B), t0 + k * B, pan=0.2 * (-1) ** k, g=0.5)
            m.add(epiano([hz(root + "2")], bar), t0, g=0.4)
            if not intro and not end and b % 2 == 1:
                m.add(kick(60, 0.2), t0, g=0.35)
            continue
        if style == "chill":
            m.add(epiano(ch, bar), t0, g=0.55)
            m.add(pad([f * 2 for f in ch], bar, 1500), t0, g=0.25)
            if not intro and not end:
                for k in (0, 2.5): m.add(kick(80, 0.12), t0 + k * B, g=0.8)
                m.add(snare(), t0 + B, g=0.35); m.add(snare(), t0 + 3 * B, g=0.35)
                for i in range(8): m.add(hat(0.025), t0 + i * B / 2 + (0.03 if i % 2 else 0), pan=0.2, g=0.12)
                m.add(b808(rootf * 2, 1.5 * B, 1.5), t0, g=0.35)
        else:
            m.add(pad([f * (2 if style == "bright" else 1) for f in ch], bar, 1100 if style != "dark" else 700), t0, g=0.5)
            arp = [ch[0] * 2, ch[1] * 2, ch[2] * 2, ch[1] * 2]
            if style in ("bright", "dark"):
                for i in range(8): m.add(pluck(arp[i % 4] * (1 if style == "dark" else 2) / (1 if style == "bright" else 1)), t0 + i * B / 2, pan=0.3 * (-1) ** i, g=0.16)
            if intro or end:
                continue
            if style == "phonk":
                for k in (0, 1.5, 2.5): m.add(kick(120, 0.16), t0 + k * B, g=0.9)
                m.add(b808(rootf, 1.4 * B), t0, g=0.55); m.add(b808(rootf * 1.5, 0.9 * B), t0 + 2.5 * B, g=0.45)
                m.add(clap(), t0 + B, g=0.5); m.add(clap(), t0 + 3 * B, g=0.5)
                for i in range(8): m.add(cowbell(560 if i % 3 else 750), t0 + i * B / 2, pan=0.25, g=0.13)
                for i in range(16): m.add(hat(0.015), t0 + i * B / 4, pan=-0.2, g=0.08)
            else:
                for k in (0, 0.75, 2.5): m.add(kick(), t0 + k * B, g=0.9)
                m.add(b808(rootf, 1.3 * B, 2.0), t0, g=0.45); m.add(b808(rootf, 0.6 * B, 2.0), t0 + 2.5 * B, g=0.4)
                m.add(clap(), t0 + 2 * B, g=0.5)
                for i in range(8): m.add(hat(), t0 + i * B / 2, pan=0.25, g=0.15 if i % 2 else 0.22)
                if b % 2:
                    for i in range(4): m.add(hat(0.02), t0 + 3.5 * B + i * B / 8, pan=-0.25, g=0.12)
    if drop_at:
        m.add(riser(min(1.5, drop_at)), max(0, drop_at - 1.5), g=0.25); m.add(impact(), drop_at, g=0.7)
    m.add(impact(), max(0, dur - outro), g=0.6)
    return m

def finish(m, sfx, path, music_gain=0.8):
    t = np.arange(m.N) / SR
    m.out *= music_gain
    for (t0, name, g) in sfx: m.add(SFX[name](), t0, g=g)
    m.out *= (np.minimum(t / 0.03, 1) * np.minimum((m.dur - t) / 0.6, 1))[:, None]
    o = np.tanh(m.out * 1.2); o /= np.abs(o).max() / 0.89
    wavfile.write(path, SR, (o * 32767).astype(np.int16))
