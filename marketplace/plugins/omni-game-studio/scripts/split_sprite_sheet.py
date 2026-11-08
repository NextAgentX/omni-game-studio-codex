#!/usr/bin/env python3
"""Split an existing generated sprite sheet into equally sized animation frames."""
import argparse
import json
import math
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow: python -m pip install pillow", file=sys.stderr)
    sys.exit(2)


def main(argv=None):
    ap = argparse.ArgumentParser(description="将等网格精灵表切分为动画帧")
    ap.add_argument("--input", required=True, help="已有的 AI 生成或人工制作的精灵表")
    ap.add_argument("--out-dir", required=True, help="新建输出目录，避免覆盖")
    ap.add_argument("--cols", type=int, required=True)
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--frames", type=int, help="使用前 N 帧，默认全部")
    ap.add_argument("--fps", type=float, default=12)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--backup-dir", help="图片先写入此新建备份目录，再复制到输出目录")
    args = ap.parse_args(argv)
    count = args.frames if args.frames is not None else args.cols * args.rows
    if args.cols <= 0 or args.rows <= 0 or count <= 0 or count > args.cols * args.rows or not math.isfinite(args.fps) or args.fps <= 0:
        ap.error("网格、帧数和 FPS 必须为正，帧数不能超过网格容量")
    src = Path(args.input)
    output = Path(args.out_dir)
    if output.exists():
        print(f"输出目录已存在，不覆盖: {output}", file=sys.stderr)
        return 1
    backup = Path(args.backup_dir) if args.backup_dir else None
    if backup and (backup.exists() or backup.resolve() == output.resolve()
                   or backup.resolve() in output.resolve().parents
                   or output.resolve() in backup.resolve().parents):
        print("备份目录和输出目录必须是互不包含的新目录", file=sys.stderr)
        return 1
    try:
        with Image.open(src) as image:
            width, height = image.size
            if width % args.cols or height % args.rows:
                raise ValueError("图片宽高不能被网格整除")
            fw, fh = width // args.cols, height // args.rows
            if backup:
                backup.mkdir(parents=True, exist_ok=False)
            output.mkdir(parents=True, exist_ok=False)
            frames, blank = [], []
            for index in range(count):
                x, y = (index % args.cols) * fw, (index // args.cols) * fh
                frame = image.crop((x, y, x + fw, y + fh)).convert("RGBA")
                name = f"frame_{index:03d}.png"
                if backup:
                    frame.save(backup / name)
                    shutil.copyfile(backup / name, output / name)
                else:
                    frame.save(output / name)
                if frame.getchannel("A").getbbox() is None:
                    blank.append(index)
                frames.append(name)
            metadata = {"version": 1, "source": str(src), "frame_size": [fw, fh],
                        "fps": args.fps, "loop": args.loop, "frames": frames,
                        "transparent_frames": blank}
            (output / "animation.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"切分失败: {exc}", file=sys.stderr)
        return 1
    print(f"已生成 {count} 帧，尺寸 {fw}x{fh}: {output}")
    if blank:
        print(f"注意：透明空帧 {blank}，请检查是否符合动画设计")
    return 0


if __name__ == "__main__":
    sys.exit(main())
