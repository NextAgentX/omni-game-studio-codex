#!/usr/bin/env python3
"""gen_placeholder_art.py — 生成占位美术资源

单文件模式:
  python gen_placeholder_art.py --out assets/art/ui_btn_attack.png --size 256x64 --kind ui --label btn_attack --color "#7C3AED" --nine-slice 24

批量模式（按 assets/manifest.json 里 placeholder=true 且文件缺失的条目生成）:
  python gen_placeholder_art.py --manifest assets/manifest.json

说明: 产出的是占位图，用于打通管线与布局验证，不是生产级美术。
"""

import argparse
import json
import random
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("需要 Pillow: python -m pip install pillow", file=sys.stderr)
    sys.exit(2)

PALETTE = ["#7C3AED", "#2563EB", "#059669", "#D97706", "#DC2626", "#0891B2", "#DB2777", "#4B5563"]

# 批量模式只处理图片条目：音频、字体等由各自的工具生成
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
NON_IMAGE_KINDS = {"audio", "font"}


def parse_size(s: str):
    w, _, h = s.lower().partition("x")
    return int(w), int(h or w)


def ascii_label(label: str, limit: int = 22) -> str:
    out = "".join(c if 32 <= ord(c) < 127 else "?" for c in (label or ""))
    return out[:limit]


def draw_placeholder(w: int, h: int, kind: str, label: str, color: str, nine: int):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

    radius = 0 if kind in ("bg", "nine") else max(4, min(w, h) // 12)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=rgb + (235,))

    # 网格：帮助判断缩放与拉伸
    step = max(8, min(w, h) // 8)
    grid = tuple(min(255, c + 28) for c in rgb) + (140,)
    for x in range(step, w, step):
        d.line([(x, 0), (x, h - 1)], fill=grid, width=1)
    for y in range(step, h, step):
        d.line([(0, y), (w - 1, y)], fill=grid, width=1)

    # 边框
    d.rectangle([0, 0, w - 1, h - 1], outline=(255, 255, 255, 200), width=max(1, min(w, h) // 64))

    # 九宫格安全线
    if nine > 0:
        g = (255, 255, 255, 120)
        for v in (nine, w - nine):
            d.line([(v, 0), (v, h - 1)], fill=g, width=1)
        for v in (nine, h - nine):
            d.line([(0, v), (w - 1, v)], fill=g, width=1)

    # 标签
    txt = ascii_label(label)
    if txt:
        d.text((6, 4), txt, fill=(255, 255, 255, 255))
    d.text((6, h - 14), f"{w}x{h}", fill=(255, 255, 255, 180))
    if kind:
        d.text((w - 8 - 6 * len(kind), h - 14), kind, fill=(255, 255, 255, 180))
    return img


def gen_one(out: Path, size: str, kind: str, label: str, color: str, nine: int):
    w, h = parse_size(size)
    img = draw_placeholder(w, h, kind, label, color, nine)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out, (w, h)


def load_manifest(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(p: Path, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="生成占位美术资源")
    ap.add_argument("--out")
    ap.add_argument("--size", default="256x256")
    ap.add_argument("--kind", default="sprite", choices=["sprite", "ui", "icon", "bg", "nine"])
    ap.add_argument("--label", default="")
    ap.add_argument("--color")
    ap.add_argument("--nine-slice", type=int, default=0)
    ap.add_argument("--manifest", help="批量模式：读取 manifest 并补齐缺失的占位图")
    ap.add_argument("--root", default=".", help="批量模式下 manifest 路径的基准目录")
    args = ap.parse_args()

    if args.manifest:
        root = Path(args.root).resolve()
        mp = (root / args.manifest) if not Path(args.manifest).is_absolute() else Path(args.manifest)
        if not mp.exists():
            print(f"manifest 不存在: {mp}", file=sys.stderr)
            return 1
        data = load_manifest(mp)
        entries = data.get("entries", [])
        made = skipped = 0
        rng = random.Random(42)
        for e in entries:
            if not e.get("placeholder"):
                continue
            rel = e.get("path")
            if not rel:
                continue
            # 音频/字体等非图片条目交给 gen_sfx.py 或人工处理，不要在这里生成图片
            if e.get("kind") in NON_IMAGE_KINDS or Path(rel).suffix.lower() not in IMAGE_EXTS:
                skipped += 1
                continue
            if Path(rel).is_absolute():
                print(f"路径必须在项目根目录内: {rel}", file=sys.stderr)
                return 1
            out = (root / rel).resolve()
            try:
                out.relative_to(root)
            except ValueError:
                print(f"路径必须在项目根目录内: {rel}", file=sys.stderr)
                return 1
            if out.exists():
                skipped += 1
                continue
            color = e.get("color") or rng.choice(PALETTE)
            gen_one(out, e.get("size_str") or "x".join(str(v) for v in e.get("size", [256, 256])),
                    e.get("kind", "sprite"), e.get("label") or Path(rel).stem, color,
                    int(e.get("nine_slice") or 0))
            made += 1
            print(f"  + {rel}")
        print(f"批量生成完成: 新建 {made}，已存在跳过 {skipped}")
        return 0

    if not args.out:
        print("单文件模式需要 --out；批量模式需要 --manifest", file=sys.stderr)
        return 1
    color = args.color or PALETTE[hash(args.label or args.out) % len(PALETTE)]
    out, size = gen_one(Path(args.out), args.size, args.kind, args.label or Path(args.out).stem, color, args.nine_slice)
    print(f"已生成: {out}  {size[0]}x{size[1]}  kind={args.kind}  color={color}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
