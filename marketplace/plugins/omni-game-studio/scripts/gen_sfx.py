#!/usr/bin/env python3
"""gen_sfx.py — 合成占位音效（无第三方依赖，仅标准库）

用法:
  python gen_sfx.py --list
  python gen_sfx.py --preset click --out assets/audio/sfx_click.wav
  python gen_sfx.py --preset hit --out assets/audio/sfx_hit.wav --gain 0.8

输出: 44100Hz / 16bit / 单声道 WAV。
说明: 占位音效，用于验证音频管线与手感节奏，不是生产级音效。
"""

import argparse
import math
import random
import struct
import sys
import wave
from pathlib import Path

SR = 44100

PRESETS = {
    # name: (duration_s, builder)
    "click":   (0.06, "tick"),
    "hit":     (0.14, "punch"),
    "pickup":  (0.18, "chirp_up"),
    "coin":    (0.22, "two_tone"),
    "fail":    (0.32, "chirp_down"),
    "jump":    (0.16, "chirp_up_soft"),
    "whoosh":  (0.30, "noise_sweep"),
    "explosion": (0.55, "boom"),
    "ui_open": (0.10, "tick_soft"),
    "ui_close": (0.10, "tick_down"),
}


def env(i, n, attack=0.01, release=0.5):
    a = int(n * attack) or 1
    r = int(n * release) or 1
    if i < a:
        return i / a
    if i > n - r:
        return max(0.0, (n - i) / r)
    return 1.0


def synth(kind, dur):
    n = int(SR * dur)
    buf = [0.0] * n
    rng = random.Random(hash(kind) & 0xFFFF)

    for i in range(n):
        t = i / SR
        e = env(i, n, 0.005, 0.6)

        if kind == "tick":
            v = math.sin(2 * math.pi * 1800 * t) * math.exp(-t * 60)
        elif kind == "tick_soft":
            v = math.sin(2 * math.pi * 1200 * t) * math.exp(-t * 45)
        elif kind == "tick_down":
            v = math.sin(2 * math.pi * 900 * t) * math.exp(-t * 50)
        elif kind == "punch":
            v = (math.sin(2 * math.pi * (140 - 60 * t / dur) * t) * 0.7
                 + rng.uniform(-1, 1) * 0.35) * math.exp(-t * 22)
        elif kind == "chirp_up":
            f = 500 + 1400 * (t / dur)
            v = math.sin(2 * math.pi * f * t) * math.exp(-t * 9)
        elif kind == "chirp_up_soft":
            f = 380 + 620 * (t / dur)
            v = math.sin(2 * math.pi * f * t) * math.exp(-t * 14)
        elif kind == "chirp_down":
            f = 900 - 650 * (t / dur)
            v = math.sin(2 * math.pi * f * t) * math.exp(-t * 7)
        elif kind == "two_tone":
            f = 1320 if t < dur * 0.4 else 1760
            v = math.sin(2 * math.pi * f * t) * math.exp(-t * 8)
        elif kind == "noise_sweep":
            lp = 0.15 + 0.85 * (1 - t / dur)
            v = rng.uniform(-1, 1) * lp * math.sin(math.pi * t / dur)
        elif kind == "boom":
            v = (math.sin(2 * math.pi * (70 - 40 * t / dur) * t) * 0.6
                 + rng.uniform(-1, 1) * 0.5) * math.exp(-t * 6)
        else:
            v = math.sin(2 * math.pi * 440 * t) * math.exp(-t * 10)
        buf[i] = v * e
    return buf


def write_wav(path: Path, samples, gain=0.7):
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = 32767 * gain / peak
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for s in samples:
            v = int(max(-32768, min(32767, s * scale)))
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))
    return path.stat().st_size


def main():
    ap = argparse.ArgumentParser(description="合成占位音效")
    ap.add_argument("--preset")
    ap.add_argument("--out")
    ap.add_argument("--gain", type=float, default=0.7)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list or not args.preset:
        print("可用预设:")
        for k, (d, kind) in PRESETS.items():
            print(f"  {k:<12} {d*1000:>4.0f} ms")
        return 0 if args.list else 1

    if args.preset not in PRESETS:
        print(f"未知预设: {args.preset}（用 --list 查看）", file=sys.stderr)
        return 1
    if not args.out:
        print("需要 --out", file=sys.stderr)
        return 1

    dur, kind = PRESETS[args.preset]
    samples = synth(kind, dur)
    size = write_wav(Path(args.out), samples, args.gain)
    print(f"已生成: {args.out}  {dur*1000:.0f} ms  {size/1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
