#!/usr/bin/env python3
"""gen_music.py — 程序化 chiptune BGM（8-bit / 芯片音乐风格）

用法:
  python gen_music.py --style upbeat --out assets/audio/bgm_main.wav --tempo 132 --bars 16
  python gen_music.py --list

输出: 44.1kHz / 16bit / 单声道 WAV + 同名 .loop.json（循环点与元数据）。

定位: 这是「能用的成品」，不是占位。风格限于 8-bit / 芯片音乐（方波+三角波+噪声）。
      需要管弦、真实乐器、人声的风格，请用音频 MCP（ElevenLabs / RaoMusic 等）生成。
"""

import argparse
import json
import math
import random
import struct
import sys
import wave
from pathlib import Path

SR = 44100

STYLES = {
    # name: (scale, progression(级数,0-based), lead_density, mood)
    "upbeat":  ([0, 2, 4, 5, 7, 9, 11], [0, 4, 5, 3], 0.62, "bright"),
    "calm":    ([0, 2, 4, 5, 7, 9, 11], [0, 5, 3, 4], 0.32, "soft"),
    "tense":   ([0, 2, 3, 5, 7, 8, 10], [0, 5, 2, 6], 0.55, "dark"),
    "menu":    ([0, 2, 4, 7, 9],        [0, 3, 4, 0], 0.40, "loop"),
    "boss":    ([0, 1, 3, 5, 6, 8, 10], [0, 1, 5, 4], 0.72, "aggressive"),
}

NOTE_BASE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
             "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def midi_to_freq(m):
    return 440.0 * (2 ** ((m - 69) / 12))


def square(t, f, duty=0.5):
    if f <= 0:
        return 0.0
    ph = (t * f) % 1.0
    return 1.0 if ph < duty else -1.0


def triangle(t, f):
    if f <= 0:
        return 0.0
    ph = (t * f) % 1.0
    return 4 * abs(ph - 0.5) - 1


def render_note(buf, start, dur, freq, kind, gain, sr=SR):
    n = int(dur * sr)
    if n <= 0:
        return
    for i in range(n):
        idx = start + i
        if idx >= len(buf):
            break
        t = i / sr
        # 简单 ADSR：快起、指数衰减
        env = min(1.0, i / max(1, int(0.006 * sr))) * math.exp(-t * (3.0 if kind == "lead" else 1.2))
        if kind == "lead":
            v = square(t, freq, 0.5) * 0.5 + square(t, freq * 2, 0.25) * 0.12
        elif kind == "bass":
            v = triangle(t, freq) * 0.9
        else:
            v = square(t, freq, 0.125)
        buf[idx] += v * env * gain


def render_drum(buf, start, kind, gain, sr=SR):
    dur = {"kick": 0.13, "snare": 0.11, "hat": 0.035}[kind]
    n = int(dur * sr)
    rng = random.Random(start)
    for i in range(n):
        idx = start + i
        if idx >= len(buf):
            break
        t = i / sr
        if kind == "kick":
            f = 130 * math.exp(-t * 26) + 42
            v = math.sin(2 * math.pi * f * t) * math.exp(-t * 26)
        elif kind == "snare":
            v = (rng.uniform(-1, 1) * 0.75 + math.sin(2 * math.pi * 190 * t) * 0.25) * math.exp(-t * 34)
        else:
            v = rng.uniform(-1, 1) * math.exp(-t * 90)
        buf[idx] += v * gain


def build(style, tempo, bars, root, seed):
    scale, prog, density, mood = STYLES[style]
    rng = random.Random(seed)

    beat = 60.0 / tempo
    bar = beat * 4
    total = int(bar * bars * SR) + SR // 2
    buf = [0.0] * total

    root_midi = 48 + NOTE_BASE.get(root.upper(), 0)  # C3 附近

    sixteenth = beat / 4
    steps_per_bar = 16

    for b in range(bars):
        chord_deg = prog[b % len(prog)]
        chord_root = root_midi + scale[chord_deg % len(scale)] + 12 * (chord_deg // len(scale))

        # 低音：每拍一个根音，第 3 拍加八度跳
        for beat_i in range(4):
            start = int((b * bar + beat_i * beat) * SR)
            m = chord_root - 12 + (12 if beat_i == 2 and rng.random() < 0.5 else 0)
            render_note(buf, start, beat * 0.9, midi_to_freq(m), "bass", 0.34)

        # 鼓：底鼓 1/3 拍，军鼓 2/4 拍，踩镲 8 分
        for beat_i in range(4):
            s = int((b * bar + beat_i * beat) * SR)
            if beat_i in (0, 2):
                render_drum(buf, s, "kick", 0.42)
            else:
                render_drum(buf, s, "snare", 0.22)
        for e in range(8):
            if e % 2 == 0 or mood in ("aggressive", "bright"):
                render_drum(buf, int((b * bar + e * beat / 2) * SR), "hat", 0.09 if e % 2 else 0.13)

        # 主旋律：按密度在 16 分网格上取音，音高落在和弦音 + 经过音
        chord_tones = [(chord_root + 12 * k + scale[(chord_deg + o) % len(scale)])
                       for k in (0, 1) for o in (0, 2, 4)]
        for s16 in range(steps_per_bar):
            if rng.random() > density:
                continue
            start = int((b * bar + s16 * sixteenth) * SR)
            dur = sixteenth * rng.choice([1, 1, 1, 2, 3])
            m = rng.choice(chord_tones) + (12 if rng.random() < 0.25 else 0)
            render_note(buf, start, dur * 0.92, midi_to_freq(m), "lead", 0.26)

        # 装饰：每 4 小节加一个上行琶音
        if b % 4 == 3:
            for k in range(4):
                start = int((b * bar + (12 + k) * sixteenth) * SR)
                m = chord_root + 12 + scale[(chord_deg + k * 2) % len(scale)]
                render_note(buf, start, sixteenth * 0.9, midi_to_freq(m), "lead", 0.2)

    # 尾部淡出，避免循环接缝爆音
    fade = int(0.05 * SR)
    for i in range(min(fade, total)):
        buf[total - 1 - i] *= i / fade

    return buf, bar * bars


def write_wav(path: Path, samples, gain=0.62):
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
    ap = argparse.ArgumentParser(description="程序化 chiptune BGM")
    ap.add_argument("--style", choices=list(STYLES), default="upbeat")
    ap.add_argument("--out")
    ap.add_argument("--tempo", type=int, default=128)
    ap.add_argument("--bars", type=int, default=16)
    ap.add_argument("--root", default="C")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--gain", type=float, default=0.62)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list or not args.out:
        print("可用风格:")
        for k, (_, prog, dens, mood) in STYLES.items():
            print(f"  {k:<8} 情绪={mood:<11} 主旋律密度={dens}")
        return 0 if args.list else 1

    samples, loop_sec = build(args.style, args.tempo, args.bars, args.root, args.seed)
    out = Path(args.out)
    size = write_wav(out, samples, args.gain)

    loop_meta = {
        "file": out.name,
        "style": args.style,
        "tempo": args.tempo,
        "bars": args.bars,
        "root": args.root,
        "sample_rate": SR,
        "duration_sec": round(len(samples) / SR, 3),
        "loop_start_sample": 0,
        "loop_end_sample": len(samples),
        "loop_sec": round(loop_sec, 3),
        "seamless": True,
        "generator": "omni-game-studio/gen_music.py",
    }
    meta_path = out.with_suffix(".loop.json")
    meta_path.write_text(json.dumps(loop_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已生成: {out}  {loop_meta['duration_sec']}s  {size/1024:.1f} KB")
    print(f"循环元数据: {meta_path}")
    print(f"  风格={args.style}  速度={args.tempo}BPM  小节={args.bars}  调={args.root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
