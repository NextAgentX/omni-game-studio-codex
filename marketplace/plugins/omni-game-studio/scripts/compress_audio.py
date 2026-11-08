#!/usr/bin/env python3
"""compress_audio.py — 音频压缩与包体核算

用法:
  python compress_audio.py --in assets/audio/bgm_main.wav --bitrate 96k
  python compress_audio.py --dir assets/audio --bitrate 96k --ext .ogg
  python compress_audio.py --dir assets/audio --check     # 只核算体积，不转码

依赖 ffmpeg。没有 ffmpeg 时不会静默失败，而是打印各引擎的导入期压缩方案。

为什么必须压: 44.1kHz/16bit/单声道 WAV 约 88 KB/秒，15 秒 BGM 就 1.3 MB，
小游戏首包通常只有几 MB 量级，不压必爆。
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

NO_FFMPEG_HINT = """
未检测到 ffmpeg，无法转码。三条替代路径：

1) 装 ffmpeg（推荐，一次装好长期可用）
   Windows: winget install Gyan.FFmpeg   或   choco install ffmpeg
   macOS:   brew install ffmpeg

2) 用引擎导入期压缩（不装任何工具）
   Godot 4 : 选中 .wav → Import 面板 → Compress Mode 选 QOA / IMA-ADPCM，或直接改用 .ogg
   Unity   : 选中音频 → Inspector → Compression Format 选 Vorbis，调 Quality
   Cocos   : 音频资源属性里选压缩格式（mp3/ogg），或导入前自行转码
   Unreal  : 选中 SoundWave → 平台压缩设置（Vorbis / ADPCM / PCM）与 Streaming 选项

3) 用在线/本地工具批量转 ogg（Vorbis, 96-128kbps 对 BGM 足够）
"""


def human(n):
    return f"{n/1024/1024:.2f} MB" if n > 1024 * 1024 else f"{n/1024:.1f} KB"


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None


def collect(target: Path, ext):
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*") if p.suffix.lower() in {".wav", ".mp3", ".ogg"})


def main():
    ap = argparse.ArgumentParser(description="音频压缩与体积核算")
    ap.add_argument("--in", dest="src")
    ap.add_argument("--dir")
    ap.add_argument("--out")
    ap.add_argument("--ext", default=".ogg", choices=[".ogg", ".mp3"])
    ap.add_argument("--bitrate", default="96k")
    ap.add_argument("--check", action="store_true", help="只核算体积")
    args = ap.parse_args()

    if args.src:
        target = Path(args.src)
    elif args.dir:
        target = Path(args.dir)
    else:
        print("需要 --in 或 --dir", file=sys.stderr)
        return 1

    files = collect(target, args.ext)
    if not files:
        print(f"没有找到音频文件: {target}", file=sys.stderr)
        return 1

    total_before = sum(f.stat().st_size for f in files)
    print(f"待处理 {len(files)} 个文件，合计 {human(total_before)}")
    for f in files:
        print(f"  {f.name:<28} {human(f.stat().st_size)}")

    if args.check:
        # 粗估压缩后体积：bitrate / 8 * 时长
        est = 0
        for f in files:
            if f.suffix.lower() != ".wav":
                est += f.stat().st_size
                continue
            import wave
            try:
                with wave.open(str(f), "rb") as w:
                    dur = w.getnframes() / w.getframerate()
                kbps = int(args.bitrate.rstrip("k"))
                est += int(dur * kbps * 1000 / 8)
            except Exception:
                est += f.stat().st_size
        print(f"\n按 {args.bitrate} 压缩后预估: {human(est)}（省 {(1-est/total_before)*100:.0f}%）")
        return 0

    if not has_ffmpeg():
        print(NO_FFMPEG_HINT)
        return 1

    total_after = 0
    for f in files:
        if f.suffix.lower() == args.ext:
            total_after += f.stat().st_size
            continue
        out = Path(args.out) if (args.out and len(files) == 1) else f.with_suffix(args.ext)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(f),
               "-c:a", "libvorbis" if args.ext == ".ogg" else "libmp3lame",
               "-b:a", args.bitrate, str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  失败 {f.name}: {r.stderr.strip()[:200]}")
            total_after += f.stat().st_size
            continue
        total_after += out.stat().st_size
        print(f"  {f.name} → {out.name}  {human(f.stat().st_size)} → {human(out.stat().st_size)}")

    print(f"\n合计 {human(total_before)} → {human(total_after)}"
          f"（省 {(1 - total_after/total_before)*100:.0f}%）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
