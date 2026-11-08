#!/usr/bin/env python3
"""Generate MP3 sound effects or music through the ElevenLabs HTTP API."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io/v1/"
MAX_BYTES = 100 * 1024 * 1024


def arguments():
    parser = argparse.ArgumentParser(description="AI 音效与音乐生成（ElevenLabs，可能计费）")
    sub = parser.add_subparsers(dest="kind", required=True)
    for kind in ("sfx", "music"):
        p = sub.add_parser(kind)
        p.add_argument("--prompt", required=True)
        p.add_argument("--out", required=True, help="输出 MP3，禁止覆盖已有文件")
        p.add_argument("--duration", type=float, help="秒；省略时由服务决定")
        p.add_argument("--dry-run", action="store_true", help="只打印请求，不调用服务、不计费")
        if kind == "sfx":
            p.add_argument("--loop", action="store_true")
            p.add_argument("--model", default="eleven_text_to_sound_v3")
        else:
            p.add_argument("--instrumental", action="store_true")
            p.add_argument("--model", default="music_v2_5")
    return parser


def make_request(args):
    if not args.prompt.strip():
        raise ValueError("提示词不能为空")
    if Path(args.out).suffix.lower() != ".mp3":
        raise ValueError("输出文件必须以 .mp3 结尾")
    if args.kind == "sfx":
        if args.duration is not None and not 0.5 <= args.duration <= 30:
            raise ValueError("音效时长必须为 0.5–30 秒")
        body = {"text": args.prompt, "model_id": args.model, "loop": args.loop}
        if args.duration is not None:
            body["duration_seconds"] = args.duration
        endpoint = "sound-generation"
    else:
        if len(args.prompt) > 4100:
            raise ValueError("音乐提示词不能超过 4100 字符")
        if args.duration is not None and not 3 <= args.duration <= 600:
            raise ValueError("音乐时长必须为 3–600 秒")
        body = {"prompt": args.prompt, "model_id": args.model,
                "force_instrumental": args.instrumental}
        if args.duration is not None:
            body["music_length_ms"] = round(args.duration * 1000)
        endpoint = "music"
    return API + endpoint + "?output_format=mp3_44100_128", body


def main(argv=None):
    args = arguments().parse_args(argv)
    try:
        url, body = make_request(args)
    except ValueError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        return 1
    out = Path(args.out)
    if out.exists():
        print(f"输出已存在，不覆盖: {out}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(json.dumps({"url": url, "body": body, "output": str(out)}, ensure_ascii=False, indent=2))
        return 0
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        print("缺少 ELEVENLABS_API_KEY；先配置环境变量，或使用 --dry-run", file=sys.stderr)
        return 2
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if content_type not in {"audio/mpeg", "audio/mp3", "application/octet-stream"}:
                raise ValueError(f"响应不是音频（Content-Type: {content_type or '缺失'}）")
            audio = response.read(MAX_BYTES + 1)
        if not audio or len(audio) > MAX_BYTES:
            raise ValueError("返回音频为空或超过 100 MiB")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("xb") as file:
            file.write(audio)
    except urllib.error.HTTPError as exc:
        print(f"服务请求失败: HTTP {exc.code}；检查账户权限、额度与请求参数", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"生成失败: {type(exc).__name__}；请检查网络或输出路径", file=sys.stderr)
        return 1
    print(f"已保存 AI 生成音频: {out} ({len(audio)} 字节)")
    print("请试听、检查循环和授权，再登记到资源清单；不要自动标记商用许可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
