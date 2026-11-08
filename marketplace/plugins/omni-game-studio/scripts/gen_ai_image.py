#!/usr/bin/env python3
"""Generate one still image or short animated GIF using the OpenAI Images API."""
import argparse
import base64
import json
import re
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.openai.com/v1/images/generations"
SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "gif": (b"GIF87a", b"GIF89a"),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
}


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="使用 OpenAI Images API 生成 PNG/WebP/JPEG 或动画 GIF")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, help="目标图片文件；不覆盖已有文件")
    ap.add_argument("--backup-dir", required=True, help="生成原图的备份目录，例如 doc/temp")
    ap.add_argument("--model", default="gpt-image-2.6-flare")
    ap.add_argument("--size", default="auto")
    ap.add_argument("--quality", choices=["low", "medium", "high", "xhigh", "max", "auto"], default="auto")
    ap.add_argument("--format", choices=["png", "webp", "jpeg", "gif"], default="png")
    ap.add_argument("--background", choices=["auto", "opaque", "transparent"], default="auto")
    ap.add_argument("--frames", type=int, help="GIF 帧数 2–16；省略时服务采用默认值")
    ap.add_argument("--frame-duration-ms", type=int, help="GIF 每帧时长，最小 20ms")
    ap.add_argument("--dry-run", action="store_true", help="显示请求但不联网、不计费")
    return ap.parse_args(argv)


def validate(args):
    out = Path(args.out)
    backup_dir = Path(args.backup_dir)
    if not args.prompt.strip() or len(args.prompt) > 32000:
        raise ValueError("提示词不能为空或超过 32000 字符")
    if args.size != "auto":
        match = re.fullmatch(r"(\d+)x(\d+)", args.size)
        if not match:
            raise ValueError("size 必须是 auto 或 WIDTHxHEIGHT")
        width, height = map(int, match.groups())
        if min(width, height) <= 0 or width > 3840 or height > 3840:
            raise ValueError("图片尺寸必须大于 0，且每边不超过 3840px")
        if width % 16 or height % 16 or max(width, height) > 3 * min(width, height):
            raise ValueError("图片尺寸的宽高应为 16 的倍数，长宽比不能超过 3:1")
    if out.suffix.lower() != "." + args.format:
        raise ValueError("--out 文件扩展名必须与 --format 一致")
    if args.format == "jpeg" and args.background == "transparent":
        raise ValueError("JPEG 不支持透明背景")
    if args.format == "gif":
        if args.background == "transparent":
            raise ValueError("GIF 流程不支持透明背景；请用 PNG/WebP，或后续处理精灵表")
        if args.frames is not None and not 2 <= args.frames <= 16:
            raise ValueError("GIF 帧数必须为 2–16")
        if args.frame_duration_ms is not None and not 20 <= args.frame_duration_ms <= 2000:
            raise ValueError("GIF 每帧时间必须为 20–2000ms")
    elif args.frames is not None or args.frame_duration_ms is not None:
        raise ValueError("--frames 和 --frame-duration-ms 只能与 --format gif 一起使用")
    if out.exists():
        raise ValueError(f"输出文件已存在，不覆盖: {out}")
    backup_file = backup_dir / out.name
    if backup_file.exists() or backup_file.resolve() == out.resolve():
        raise ValueError(f"备份文件已存在或与输出路径相同: {backup_file}")
    body = {"model": args.model, "prompt": args.prompt, "size": args.size,
            "quality": args.quality, "output_format": args.format,
            "background": args.background, "n": 1}
    if args.format == "gif":
        if args.frames is not None:
            body["frame_count"] = args.frames
        if args.frame_duration_ms is not None:
            body["frame_duration_ms"] = args.frame_duration_ms
    return out, backup_dir, backup_file, body


def has_valid_signature(image, output_format):
    if not image or not any(image.startswith(sig) for sig in SIGNATURES[output_format]):
        return False
    return output_format != "webp" or image[8:12] == b"WEBP"


def main(argv=None):
    args = parse_args(argv)
    try:
        out, backup_dir, backup_file, body = validate(args)
    except ValueError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        safe_body = {**body, "prompt": body["prompt"][:240] + ("…" if len(body["prompt"]) > 240 else "")}
        print(json.dumps({"url": API, "body": safe_body, "output": str(out),
                          "backup": str(backup_file)}, ensure_ascii=False, indent=2))
        return 0
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        print("缺少 OPENAI_API_KEY；请配置环境变量或使用 --dry-run", file=sys.stderr)
        return 2
    request = urllib.request.Request(
        API, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read(120 * 1024 * 1024).decode("utf-8"))
        encoded = payload["data"][0]["b64_json"]
        image = base64.b64decode(encoded, validate=True)
        if not has_valid_signature(image, args.format):
            raise ValueError("响应图片格式与请求不符或文件为空")
        backup_dir.mkdir(parents=True, exist_ok=True)
        with backup_file.open("xb") as file:
            file.write(image)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("xb") as file:
            file.write(image)
    except urllib.error.HTTPError as exc:
        print(f"图片生成请求失败：HTTP {exc.code}；检查账户、模型权限、预览资格和额度", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError,
            UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"图片生成失败：{type(exc).__name__}；检查网络、响应和输出路径", file=sys.stderr)
        return 1
    print(f"已保存图片: {out}；原图备份: {backup_file} ({len(image)} 字节)")
    if args.format == "gif":
        print("这是 AI 生成的 GIF；检查每一帧、动作连贯性和游戏引擎的导入支持。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
