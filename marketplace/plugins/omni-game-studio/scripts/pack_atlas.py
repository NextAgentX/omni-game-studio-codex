#!/usr/bin/env python3
"""pack_atlas.py — 图集打包（shelf packing）

用法:
  python pack_atlas.py --input assets/art/ui --out-sheet assets/art/ui_atlas.png --out-data assets/art/ui_atlas.json --max-size 2048 --padding 2

输出 JSON 结构接近 TexturePacker 通用格式，主流引擎都可二次转换。
说明: 简化实现，不支持旋转与裁剪；同屏同集的划分仍需人工决定。
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow: python -m pip install pillow", file=sys.stderr)
    sys.exit(2)

EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def collect(input_dir: Path):
    files = [p for p in sorted(input_dir.rglob("*")) if p.suffix.lower() in EXTS and p.is_file()]
    imgs = []
    for p in files:
        try:
            im = Image.open(p)
        except Exception as e:
            print(f"  跳过（无法读取）: {p} ({e})")
            continue
        imgs.append((p, im.convert("RGBA")))
    return imgs


def pack(imgs, max_size, padding):
    order = sorted(imgs, key=lambda t: (-t[1].height, -t[1].width, t[0].name))
    placements = []
    x = y = row_h = 0
    for path, im in order:
        w, h = im.size
        if w + 2 * padding > max_size:
            raise ValueError(f"图片过宽，超过 max-size: {path.name} ({w}px)")
        if h + 2 * padding > max_size:
            raise ValueError(f"图片过高，超过 max-size: {path.name} ({h}px)")
        if x + w + 2 * padding > max_size:
            x = 0
            y += row_h + padding
            row_h = 0
        if y + h + 2 * padding > max_size:
            raise ValueError(f"图片无法全部装入 {max_size}x{max_size} 图集")
        placements.append((path, im, x + padding, y + padding))
        x += w + padding
        row_h = max(row_h, h)

    sheet_w = max((px + im.width + padding) for _, im, px, _ in placements)
    sheet_h = max((py + im.height + padding) for _, im, _, py in placements)
    sheet_w = min(max_size, ((sheet_w + 3) // 4) * 4)
    sheet_h = min(max_size, ((sheet_h + 3) // 4) * 4)
    return placements, sheet_w, sheet_h


def main():
    ap = argparse.ArgumentParser(description="图集打包")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-sheet", required=True)
    ap.add_argument("--out-data", required=True)
    ap.add_argument("--max-size", type=int, default=2048)
    ap.add_argument("--padding", type=int, default=2)
    args = ap.parse_args()

    if args.max_size <= 0 or args.padding < 0:
        print("max-size 必须大于 0，padding 不得为负数", file=sys.stderr)
        return 1
    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"目录不存在: {input_dir}", file=sys.stderr)
        return 1

    imgs = [(p, im) for p, im in collect(input_dir) if p.resolve() != Path(args.out_sheet).resolve()]
    if not imgs:
        print(f"没有可用图片: {input_dir}", file=sys.stderr)
        return 1
    names = [p.stem for p, _ in imgs]
    if len(names) != len(set(names)):
        print("图片文件名重复（忽略扩展名），无法生成唯一索引", file=sys.stderr)
        return 1

    try:
        placements, sw, sh = pack(imgs, args.max_size, args.padding)
    except ValueError as e:
        print(f"打包失败: {e}", file=sys.stderr)
        return 1

    sheet = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    frames = {}
    for path, im, px, py in placements:
        sheet.paste(im, (px, py))
        frames[path.stem] = {
            "frame": {"x": px, "y": py, "w": im.width, "h": im.height},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": im.width, "h": im.height},
            "sourceSize": {"w": im.width, "h": im.height},
        }

    out_sheet = Path(args.out_sheet)
    out_data = Path(args.out_data)
    out_sheet.parent.mkdir(parents=True, exist_ok=True)
    out_data.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_sheet)

    data = {
        "frames": frames,
        "meta": {
            "image": out_sheet.name,
            "format": "RGBA8888",
            "size": {"w": sw, "h": sh},
            "scale": "1",
            "generator": "omni-game-studio/pack_atlas.py",
        },
    }
    out_data.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已打包 {len(frames)} 张 → {out_sheet}  {sw}x{sh}")
    print(f"索引: {out_data}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
