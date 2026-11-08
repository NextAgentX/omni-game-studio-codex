#!/usr/bin/env python3
"""validate_assets.py — 校验资源清单与文件（支持 draft / final 两档）

用法:
  python validate_assets.py --manifest assets/manifest.json                  # 基础校验
  python validate_assets.py --manifest assets/manifest.json --final          # 发布前终检
  python validate_assets.py --manifest assets/manifest.json --final --strict-license

--final 额外要求:
  1. 每条 tier 必须是 "final"（draft 视为未完成）
  2. 每条必须有 license 字段；--strict-license 时 commercial_ok 必须为 true
  3. sprite/ui/nine/icon 类图片必须有 alpha 通道且存在透明像素（不能是实底方块）
  4. 图片尺寸必须与声明一致
  5. WAV 超过 500KB 报警（应压缩为 ogg/mp3）

退出码: 0 通过 / 1 失败
"""

import argparse
import json
import sys
from pathlib import Path

VALID_KINDS = {"sprite", "ui", "icon", "bg", "nine", "animation", "vfx", "audio", "font", "other"}
VALID_TIERS = {"draft", "final"}
ALPHA_REQUIRED_KINDS = {"sprite", "ui", "icon", "nine", "animation", "vfx"}
VALID_SOURCES = {"ai", "commissioned", "purchased", "ofl", "self", "unknown"}

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def main():
    ap = argparse.ArgumentParser(description="校验资源清单")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--final", action="store_true", help="发布前终检")
    ap.add_argument("--strict-license", action="store_true", help="要求 commercial_ok=true")
    ap.add_argument("--max-wav-kb", type=int, default=500)
    args = ap.parse_args()

    if args.strict_license and not args.final:
        print("FAIL --strict-license 必须与 --final 一起使用", file=sys.stderr)
        return 1
    if args.final and not HAS_PIL:
        print("FAIL 发布终检需要 Pillow；请运行 python -m pip install pillow", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    mp = Path(args.manifest)
    if not mp.is_absolute():
        mp = root / mp
    if not mp.exists():
        print(f"FAIL manifest 不存在: {mp}", file=sys.stderr)
        return 1

    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"FAIL manifest JSON 解析失败: {e}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print("FAIL manifest 顶层必须是对象", file=sys.stderr)
        return 1
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        print("FAIL manifest.entries 缺失或为空", file=sys.stderr)
        return 1

    errors, warnings = [], []
    seen = set()
    drafts = finals = 0

    for i, e in enumerate(entries):
        tag = f"entries[{i}]"
        if not isinstance(e, dict):
            errors.append(f"{tag}: 不是对象")
            continue
        rel = e.get("path")
        if not isinstance(rel, str) or not rel.strip():
            errors.append(f"{tag}: path 必须是非空字符串")
            continue
        if rel in seen:
            errors.append(f"{tag}: path 重复 {rel}")
        seen.add(rel)

        p = Path(rel)
        if p.is_absolute():
            errors.append(f"{tag}: path 必须是相对路径 {rel}")
            continue
        target = (root / p).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"{tag}: path 越出项目根 {rel}")
            continue

        kind = e.get("kind", "sprite")
        if not isinstance(kind, str) or kind not in VALID_KINDS:
            errors.append(f"{tag}: kind 非法 '{kind}'")
            continue

        tier = e.get("tier", "draft")
        if not isinstance(tier, str) or tier not in VALID_TIERS:
            errors.append(f"{tag}: tier 非法 '{tier}'（draft / final）")
        elif tier == "final":
            finals += 1
        else:
            drafts += 1
            if args.final:
                errors.append(f"{tag}: 仍是 draft，不能发布 {rel}")

        if args.final:
            lic = e.get("license")
            if not isinstance(lic, str) or not lic.strip():
                errors.append(f"{tag}: 缺少 license（授权台账）{rel}")
            if args.strict_license and e.get("commercial_ok") is not True:
                errors.append(f"{tag}: commercial_ok 不为 true，不可商用 {rel}")
            if e.get("placeholder") is True:
                errors.append(f"{tag}: 仍是占位资源，不能发布 {rel}")
            elif "placeholder" in e and e["placeholder"] is not False:
                errors.append(f"{tag}: placeholder 必须是布尔值 {rel}")
            src = e.get("source")
            if src and (not isinstance(src, str) or src not in VALID_SOURCES):
                errors.append(f"{tag}: source 非法 '{src}'（{', '.join(sorted(VALID_SOURCES))}）")
            if src == "ai" and not e.get("ai_generated"):
                warnings.append(f"{tag}: source=ai 但未标 ai_generated，审核时容易漏报 {rel}")

        if not target.is_file():
            errors.append(f"{tag}: 文件不存在 {rel}")
            continue
        size_bytes = target.stat().st_size
        if size_bytes == 0:
            errors.append(f"{tag}: 文件为空 {rel}")
            continue

        suffix = target.suffix.lower()
        if args.final and kind in ALPHA_REQUIRED_KINDS and suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            errors.append(f"{tag}: {kind} 需要可检查的 PNG/JPEG/WebP/GIF 图片 {rel}")
            continue
        if kind == "audio" and suffix == ".wav" and size_bytes > args.max_wav_kb * 1024:
            warnings.append(f"{tag}: WAV {size_bytes/1024:.0f}KB 超过 {args.max_wav_kb}KB，建议压缩为 ogg/mp3 {rel}")

        declared = e.get("size")
        if HAS_PIL and suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            try:
                with Image.open(target) as im:
                    if declared is not None and declared != list(im.size):
                        errors.append(f"{tag}: size 声明 {declared} 与实际 {list(im.size)} 不一致 {rel}")
                    if args.final and kind in ALPHA_REQUIRED_KINDS:
                        if "A" not in im.getbands() and "transparency" not in im.info:
                            errors.append(f"{tag}: {kind} 必须有 alpha 通道，当前 {im.mode} {rel}")
                        else:
                            a = im.convert("RGBA").split()[-1]
                            if a.getextrema() == (255, 255):
                                errors.append(f"{tag}: {kind} 全不透明，像实底方块，抠图没做干净 {rel}")
            except Exception as ex:
                errors.append(f"{tag}: 图片无法读取 {rel} ({ex})")

    for w in warnings:
        print("  WARN " + w)
    for m in errors:
        print("  FAIL " + m)

    mode = "终检" if args.final else "基础校验"
    if errors:
        print(f"\n{mode}失败: {len(errors)} 个错误 / {len(warnings)} 个警告"
              f"（共 {len(entries)} 条，final {finals} / draft {drafts}）")
        return 1

    print(f"{mode}通过: {len(entries)} 条资源（final {finals} / draft {drafts}），{len(warnings)} 个警告")
    if not HAS_PIL:
        print("提示: 未安装 Pillow，已跳过尺寸与 alpha 检查（终检强烈建议安装）")
    if args.final and warnings:
        print("注意: 有警告项，发布前应逐条确认")
    return 0


if __name__ == "__main__":
    sys.exit(main())
