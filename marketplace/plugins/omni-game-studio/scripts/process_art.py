#!/usr/bin/env python3
"""process_art.py — 把生成的原始图处理成符合规格的正式游戏资源

典型用法（AI 生成 1024x1024 → 256x64 的九宫格按钮）:
  python process_art.py --in raw/btn.png --out assets/art/ui/ui_btn_primary.png \
      --size 256x64 --mode fit --key-color "#FFFFFF" --key-tolerance 14 --nine-slice 24 --check-nine

参数说明:
  --mode fit      等比缩放到目标框内，四周补透明（默认，推荐）
  --mode stretch  直接拉伸到目标尺寸（会变形，仅用于纯色块/渐变）
  --mode trim     只裁掉透明边，不缩放（用于已符合尺寸的图）
  --key-color     抠掉指定背景色（AI 出图常见纯色底），配合 --key-tolerance
  --nine-slice    声明九宫格边距，配合 --check-nine 检查边框是否可九宫格拉伸
  --check-nine    检查外圈 N 像素是否足够均匀（九宫格拉伸不变形的前提）

退出码: 0 成功 / 1 失败 / 2 缺依赖
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:
    print("需要 Pillow: python -m pip install pillow", file=sys.stderr)
    sys.exit(2)


def hex_rgb(s: str):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def key_out(img: Image.Image, color: str, tol: int) -> Image.Image:
    """把接近 color 的像素设为全透明。"""
    rgb = hex_rgb(color)
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if abs(r - rgb[0]) <= tol and abs(g - rgb[1]) <= tol and abs(b - rgb[2]) <= tol:
                px[x, y] = (0, 0, 0, 0)
    return img


def trim_alpha(img: Image.Image) -> Image.Image:
    bbox = img.split()[-1].getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def fit_to(img: Image.Image, size, pad: int) -> Image.Image:
    tw, th = size
    inner_w, inner_h = max(1, tw - 2 * pad), max(1, th - 2 * pad)
    w, h = img.size
    scale = min(inner_w / w, inner_h / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2), resized)
    return canvas


def check_nine(img: Image.Image, n: int):
    """检查九宫格可行性：四条边带在拉伸方向上的像素应基本一致。"""
    w, h = img.size
    if n * 2 >= min(w, h):
        return False, [f"九宫格边距 {n}px 过大（图 {w}x{h}），边距之和需小于短边"]
    issues = []

    def row_uniform(y):
        px = img.load()
        vals = [px[x, y] for x in range(n, w - n)]
        if not vals:
            return True
        # 忽略全透明
        vals = [v for v in vals if v[3] > 8]
        if len(vals) < 2:
            return True
        r0, g0, b0, a0 = vals[0]
        for r, g, b, a in vals:
            if abs(r - r0) + abs(g - g0) + abs(b - b0) > 60:
                return False
        return True

    def col_uniform(x):
        px = img.load()
        vals = [px[x, y] for y in range(n, h - n)]
        vals = [v for v in vals if v[3] > 8]
        if len(vals) < 2:
            return True
        r0, g0, b0, a0 = vals[0]
        for r, g, b, a in vals:
            if abs(r - r0) + abs(g - g0) + abs(b - b0) > 60:
                return False
        return True

    for y in (0, n - 1, h - n, h - 1):
        if not row_uniform(y):
            issues.append(f"第 {y} 行在中段有颜色跳变，横向拉伸会撕裂")
            break
    for x in (0, n - 1, w - n, w - 1):
        if not col_uniform(x):
            issues.append(f"第 {x} 列在中段有颜色跳变，纵向拉伸会撕裂")
            break
    return (len(issues) == 0), issues


def main():
    ap = argparse.ArgumentParser(description="把原始图处理成符合规格的正式资源")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", help="目标尺寸 WxH，如 256x64")
    ap.add_argument("--mode", choices=["fit", "stretch", "trim"], default="fit")
    ap.add_argument("--key-color", help="要抠掉的背景色，如 #FFFFFF")
    ap.add_argument("--key-tolerance", type=int, default=10)
    ap.add_argument("--pad", type=int, default=0, help="fit 模式四周留白")
    ap.add_argument("--nine-slice", type=int, default=0)
    ap.add_argument("--check-nine", action="store_true")
    ap.add_argument("--report", help="把处理结果写成 JSON")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"源文件不存在: {src}", file=sys.stderr)
        return 1

    img = Image.open(src).convert("RGBA")
    orig = img.size
    steps = [f"读入 {orig[0]}x{orig[1]}"]

    if args.key_color:
        img = key_out(img, args.key_color, args.key_tolerance)
        steps.append(f"抠色 {args.key_color} ±{args.key_tolerance}")

    if args.mode in ("fit", "trim"):
        before = img.size
        img = trim_alpha(img)
        if img.size != before:
            steps.append(f"裁透明边 {before[0]}x{before[1]} → {img.size[0]}x{img.size[1]}")

    if args.size:
        tw, th = (int(v) for v in args.size.lower().split("x"))
        if args.mode == "fit":
            img = fit_to(img, (tw, th), args.pad)
            steps.append(f"等比缩放并居中到 {tw}x{th}")
        elif args.mode == "stretch":
            img = img.resize((tw, th), Image.LANCZOS)
            steps.append(f"拉伸到 {tw}x{th}")

    issues = []
    nine_ok = None
    if args.check_nine and args.nine_slice:
        nine_ok, issues = check_nine(img, args.nine_slice)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)

    # 透明像素占比（判断是否真的抠干净了）
    alpha = img.split()[-1]
    hist = alpha.histogram()
    total = img.size[0] * img.size[1]
    transparent_ratio = sum(hist[:9]) / total if total else 0

    print(f"输出: {out}  {img.size[0]}x{img.size[1]}  {out.stat().st_size/1024:.1f} KB")
    for s in steps:
        print(f"  · {s}")
    print(f"  · 全透明像素占比 {transparent_ratio*100:.1f}%")
    if nine_ok is True:
        print(f"  · 九宫格检查通过（边距 {args.nine_slice}px）")
    elif nine_ok is False:
        for i in issues:
            print(f"  · 九宫格检查失败: {i}")

    if args.report:
        Path(args.report).write_text(json.dumps({
            "src": str(src),
            "out": str(out),
            "source_size": list(orig),
            "final_size": list(img.size),
            "transparent_ratio": round(transparent_ratio, 4),
            "nine_slice": args.nine_slice or None,
            "nine_slice_ok": nine_ok,
            "steps": steps,
            "issues": issues,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  · 报告: {args.report}")

    return 0 if nine_ok is not False else 1


if __name__ == "__main__":
    sys.exit(main())
