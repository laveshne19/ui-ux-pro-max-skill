#!/usr/bin/env python3
"""
synth.py  —  Generate an original D-major backing track (WAV, no copyrighted music).

The track is entirely synthesized from sine waves, noise transients and a chime.
No samples, no copyrighted content, no external audio files required.

Usage:
    python synth.py                          # → out/backing.wav  (30s default)
    python synth.py --duration 15 --out out/bg15.wav
    python synth.py --duration 60 --bpm 90 --out out/slow.wav
"""
import argparse
import math
import struct
import sys
import wave
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# D-major chord tones (Hz)
D4   = 293.66
Fsh4 = 369.99
A4   = 440.00
D5   = 587.33
Fsh5 = 739.99
A5   = 880.00
B4   = 493.88   # added for colour

SAMPLE_RATE = 44100


def sine(freq: float, t_arr, amp: float = 1.0):
    return [amp * math.sin(2 * math.pi * freq * t) for t in t_arr]


def adsr_env(n: int, sr: int, attack=0.01, decay=0.05, sustain=0.7, release=0.15):
    env = []
    a = int(attack  * sr)
    d = int(decay   * sr)
    r = int(release * sr)
    s = max(0, n - a - d - r)
    for i in range(a):
        env.append(i / max(a, 1))
    for i in range(d):
        env.append(1.0 - (1.0 - sustain) * i / max(d, 1))
    for _ in range(s):
        env.append(sustain)
    for i in range(r):
        env.append(sustain * (1.0 - i / max(r, 1)))
    return env[:n] + [0.0] * max(0, n - len(env))


def make_tone(freq: float, duration: float, amp: float = 0.25,
              attack=0.02, decay=0.05, sustain=0.75, release=0.15) -> list:
    n = int(duration * SAMPLE_RATE)
    t = [i / SAMPLE_RATE for i in range(n)]
    wave_s = sine(freq, t, amp)
    # Add slight 2nd harmonic
    wave_s2 = sine(freq * 2, t, amp * 0.15)
    env = adsr_env(n, SAMPLE_RATE, attack, decay, sustain, release)
    return [(wave_s[i] + wave_s2[i]) * env[i] for i in range(n)]


def make_chime(freq: float, duration: float = 0.4, amp: float = 0.18) -> list:
    n = int(duration * SAMPLE_RATE)
    t = [i / SAMPLE_RATE for i in range(n)]
    # Fast attack, long exponential decay
    env = [math.exp(-5 * ti) for ti in t]
    return [amp * math.sin(2 * math.pi * freq * t[i]) * env[i] for i in range(n)]


def make_kick(duration: float = 0.25, amp: float = 0.4) -> list:
    n = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 150 * math.exp(-30 * t)
        env  = math.exp(-8  * t)
        samples.append(amp * math.sin(2 * math.pi * freq * t) * env)
    return samples


def make_hihat(duration: float = 0.08, amp: float = 0.08) -> list:
    import random
    n = int(duration * SAMPLE_RATE)
    env = [math.exp(-40 * i / SAMPLE_RATE) for i in range(n)]
    return [amp * (random.random() * 2 - 1) * env[i] for i in range(n)]


def mix(base: list, overlay: list, offset: int) -> list:
    end = offset + len(overlay)
    if end > len(base):
        base.extend([0.0] * (end - len(base)))
    for i, s in enumerate(overlay):
        base[offset + i] += s
    return base


def generate_track(duration: float = 30.0, bpm: float = 96.0) -> list:
    import random
    random.seed(42)

    total_samples = int(duration * SAMPLE_RATE)
    track = [0.0] * total_samples

    beat_dur   = 60.0 / bpm        # seconds per beat
    bar_dur    = beat_dur * 4
    beats_total = int(duration / beat_dur)

    # ── Chord progression: I - V - vi - IV in D-major ──
    # D  → D4 Fsh4 A4
    # A  → A4 Csh5 E5   (approximation: A4 Csh5=277.18 E5=659.25)
    # Bm → B4 D5 Fsh5
    # G  → G4=392 B4 D5
    CSHARP5 = 554.37
    E5      = 659.25
    G4      = 392.00

    progression = [
        [(D4, 0.20), (Fsh4, 0.18), (A4, 0.16)],   # I  — D
        [(A4, 0.20), (CSHARP5, 0.18), (E5, 0.16)], # V  — A
        [(B4, 0.20), (D5, 0.18), (Fsh5, 0.16)],    # vi — Bm
        [(G4, 0.20), (B4, 0.18), (D5, 0.16)],      # IV — G
    ]

    bars_total = int(duration / bar_dur)
    for bar in range(bars_total):
        chord = progression[bar % 4]
        bar_start = int(bar * bar_dur * SAMPLE_RATE)

        for freq, amp in chord:
            tone = make_tone(freq, bar_dur * 0.95, amp, attack=0.04, release=0.2)
            track = mix(track, tone, bar_start)

    # ── Chime melody (D pentatonic: D4 Fsh4 A4 B4 D5) ──
    melody_notes = [D4, Fsh4, A4, B4, D5, A4, Fsh4, D4]
    note_dur = beat_dur
    for i in range(min(beats_total, len(melody_notes) * 4)):
        note_freq = melody_notes[i % len(melody_notes)]
        offset = int(i * beat_dur * SAMPLE_RATE)
        chime = make_chime(note_freq, min(note_dur * 1.5, 0.6), amp=0.14)
        track = mix(track, chime, offset)

    # ── Kick drum on beats 1 and 3 ──
    for beat in range(beats_total):
        if beat % 4 in (0, 2):
            offset = int(beat * beat_dur * SAMPLE_RATE)
            kick = make_kick(0.22, 0.32)
            track = mix(track, kick, offset)

    # ── Hi-hat on every beat ──
    for beat in range(beats_total):
        offset = int(beat * beat_dur * SAMPLE_RATE)
        hh = make_hihat(0.06, 0.06)
        track = mix(track, hh, offset)

    # ── Off-beat hi-hats ──
    for beat in range(beats_total):
        half_offset = int((beat + 0.5) * beat_dur * SAMPLE_RATE)
        if half_offset < total_samples:
            hh = make_hihat(0.04, 0.04)
            track = mix(track, hh, half_offset)

    # Normalise to -6 dBFS
    peak = max(abs(s) for s in track) or 1.0
    target = 0.5
    scale = target / peak
    track = [s * scale for s in track]

    # Fade in / fade out  (0.5s each)
    fade_n = int(0.5 * SAMPLE_RATE)
    for i in range(min(fade_n, len(track))):
        track[i] *= i / fade_n
    for i in range(min(fade_n, len(track))):
        track[-(i+1)] *= i / fade_n

    return track[:total_samples]


def save_wav(samples: list, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        pcm = struct.pack(f"<{len(samples)}h",
                          *[max(-32768, min(32767, int(s * 32767))) for s in samples])
        wf.writeframes(pcm)


def main():
    parser = argparse.ArgumentParser(description="Generate original D-major backing track.")
    parser.add_argument("--duration", type=float, default=30.0, help="Track duration in seconds (default 30)")
    parser.add_argument("--bpm",      type=float, default=96.0, help="Tempo in BPM (default 96)")
    parser.add_argument("--out",      default="out/backing.wav", help="Output WAV file")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = SCRIPT_DIR / out_path

    print(f"[synth] Generating {args.duration}s track at {args.bpm} BPM ...")
    try:
        samples = generate_track(args.duration, args.bpm)
    except Exception as e:
        print(f"[synth] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    save_wav(samples, out_path)
    print(f"[synth] Saved: {out_path}  ({len(samples)/SAMPLE_RATE:.1f}s, {SAMPLE_RATE}Hz mono 16-bit)")


if __name__ == "__main__":
    main()
