#!/usr/bin/env python3
"""omni_state.py — 流水线状态与阶段门禁

用法:
  python omni_state.py init  --root . --engine godot --version 4.3 --platforms web,android
  python omni_state.py status --root .
  python omni_state.py advance --root . --to gdd
  python omni_state.py check  --root . --stage gdd
  python omni_state.py set    --root . --key engine --value unity

状态文件: <root>/.omni/state.json
退出码: 0 通过 / 1 失败（门禁未过）
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = ".omni"
STATE_FILE = "state.json"

# 阶段顺序（不可跳阶段推进）
STAGES = ["brief", "gdd", "tech", "art", "audio", "qa", "release", "done"]

# 每个阶段必须产出的工件（相对 root）
STAGE_OUTPUT = {
    "brief": "docs/00-brief.md",
    "gdd": "docs/01-gdd.md",
    "tech": "docs/02-tech.md",
    "art": "docs/03-art.md",
    "audio": "docs/04-audio.md",
    "qa": "docs/05-qa.md",
    "release": "docs/06-release.md",
}

# 每份文档必须包含的章节关键词（大小写不敏感，匹配任意标题）
REQUIRED_SECTIONS = {
    "brief": ["核心体验", "目标平台", "MVP", "变现", "验收标准"],
    "gdd": ["一句话核心体验", "核心循环", "系统清单", "数值", "关卡", "叙事", "留存", "待验证假设"],
    "tech": ["前提", "架构", "构建配置", "验收指标"],
    "art": ["视觉定调", "色彩", "关键画面", "资源规格", "UI 规范", "画质分级"],
    "audio": ["音频设计目标", "音乐清单", "音效清单", "交互音频", "预算", "平台适配", "验收"],
    "qa": ["测试范围", "核心用例", "兼容矩阵", "性能基线", "回归", "准入结论"],
    "release": ["发布目标", "平台规则卡", "包体", "资质", "排期", "上线检查", "运营"],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def state_path(root: Path) -> Path:
    return root / STATE_DIR / STATE_FILE


def load(root: Path) -> dict:
    p = state_path(root)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save(root: Path, data: dict) -> None:
    p = state_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def headings(md_text: str) -> list:
    return [m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+)$", md_text, re.M)]


def check_stage(root: Path, stage: str) -> tuple:
    """返回 (ok, messages)"""
    if stage not in STAGE_OUTPUT:
        return False, [f"未知阶段: {stage}（可选: {', '.join(STAGE_OUTPUT)}）"]

    rel = STAGE_OUTPUT[stage]
    f = root / rel
    msgs = []
    if not f.exists():
        return False, [f"缺少工件: {rel}（可先从 templates/docs/ 复制骨架）"]
    if f.stat().st_size < 80:
        return False, [f"工件过短（{f.stat().st_size} 字节）: {rel}"]

    text = f.read_text(encoding="utf-8", errors="replace")

    # 从 templates/docs 复制来的骨架必须填完才能过门禁，否则门禁形同虚设
    todo = text.count("[TODO]")
    if todo:
        return False, [f"{rel} 仍有 {todo} 处 [TODO] 未填（骨架未完成）"]

    hs = [h.lower() for h in headings(text)]
    missing = []
    for kw in REQUIRED_SECTIONS[stage]:
        if not any(kw.lower() in h for h in hs):
            missing.append(kw)
    if missing:
        msgs.append(f"{rel} 缺少章节: " + "、".join(missing))
        msgs.append("提示: 章节必须是 Markdown 标题（## xxx），正文里提到不算")
        return False, msgs
    msgs.append(f"{rel} 通过（{len(hs)} 个标题）")
    return True, msgs


def cmd_init(args):
    root = Path(args.root).resolve()
    if state_path(root).exists():
        print(f"状态文件已存在，未覆盖: {state_path(root)}")
        return 1
    data = {
        "version": 1,
        "project": args.name or root.name,
        "engine": args.engine,
        "engine_version": args.version or "",
        "platforms": [p.strip() for p in (args.platforms or "").split(",") if p.strip()],
        "stage": "brief",
        "created_at": now(),
        "updated_at": now(),
        "history": [{"stage": "brief", "at": now()}],
    }
    save(root, data)
    print(f"已初始化: {state_path(root)}")
    print(f"  引擎: {data['engine']} {data['engine_version']}".rstrip())
    print(f"  平台: {', '.join(data['platforms']) or '(未指定)'}")
    print(f"  当前阶段: brief → 需要产出 {STAGE_OUTPUT['brief']}")
    return 0


def cmd_status(args):
    root = Path(args.root).resolve()
    data = load(root)
    if not data:
        print("未初始化。先运行: python omni_state.py init --root . --engine <godot|unity|cocos>")
        return 1

    print(f"项目: {data.get('project')}   引擎: {data.get('engine')} {data.get('engine_version','')}".rstrip())
    print(f"平台: {', '.join(data.get('platforms') or []) or '(未指定)'}")
    print(f"当前阶段: {data.get('stage')}\n")

    print(f"{'阶段':<10}{'工件':<24}{'状态'}")
    print("-" * 56)
    for st in STAGES:
        if st == "done":
            continue
        rel = STAGE_OUTPUT[st]
        ok, _ = check_stage(root, st)
        mark = "OK" if ok else ("缺失" if not (root / rel).exists() else "不完整")
        cur = "  ← 当前" if data.get("stage") == st else ""
        print(f"{st:<10}{rel:<24}{mark}{cur}")
    return 0


def cmd_check(args):
    root = Path(args.root).resolve()
    ok, msgs = check_stage(root, args.stage)
    for m in msgs:
        print(("  OK  " if ok else "  FAIL ") + m)
    return 0 if ok else 1


def cmd_advance(args):
    root = Path(args.root).resolve()
    data = load(root)
    if not data:
        print("未初始化。先运行 init。")
        return 1

    cur = data.get("stage", "brief")
    if cur not in STAGES:
        print(f"状态文件里的阶段非法: {cur}")
        return 1
    idx = STAGES.index(cur)
    if cur == "done":
        print("已经处于 done 阶段，无需推进。")
        return 1

    target = args.to
    if target:
        if target not in STAGES:
            print(f"未知阶段: {target}")
            return 1
        if STAGES.index(target) <= idx:
            print(f"目标阶段 {target} 不晚于当前 {cur}，无需推进。")
            return 1
        # 逐阶段校验，不允许跳阶段
        span = STAGES[idx:STAGES.index(target)]
    else:
        span = [cur]
        target = STAGES[idx + 1] if idx + 1 < len(STAGES) else "done"

    for st in span:
        if st == "done":
            continue
        ok, msgs = check_stage(root, st)
        for m in msgs:
            print(("  OK  " if ok else "  FAIL ") + m)
        if not ok:
            print(f"\n门禁未过：无法离开阶段 {st}。补齐工件后重试。")
            return 1

    data["stage"] = target
    data["updated_at"] = now()
    data.setdefault("history", []).append({"stage": target, "at": now()})
    save(root, data)
    print(f"\n已推进: {cur} → {target}")
    if target in STAGE_OUTPUT:
        print(f"下一件工件: {STAGE_OUTPUT[target]}")
    return 0


def cmd_set(args):
    root = Path(args.root).resolve()
    data = load(root)
    if not data:
        print("未初始化。")
        return 1
    if args.key not in {"project", "engine", "engine_version", "platforms"}:
        print("不可修改该字段；允许: project, engine, engine_version, platforms")
        return 1
    if args.key == "engine" and args.value not in {"cocos", "unity", "godot"}:
        print("引擎必须是 cocos、unity 或 godot")
        return 1
    if args.key == "platforms":
        data[args.key] = [p.strip() for p in args.value.split(",") if p.strip()]
    else:
        data[args.key] = args.value
    data["updated_at"] = now()
    save(root, data)
    print(f"{args.key} = {data[args.key]}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="流水线状态与阶段门禁")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="初始化项目状态")
    p.add_argument("--root", default=".")
    p.add_argument("--name")
    p.add_argument("--engine", required=True, choices=["cocos", "unity", "godot"])
    p.add_argument("--version")
    p.add_argument("--platforms", help="逗号分隔，如 web,android,wechat")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status", help="查看各阶段状态")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("check", help="校验某阶段工件")
    p.add_argument("--root", default=".")
    p.add_argument("--stage", required=True, choices=list(STAGE_OUTPUT))
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("advance", help="推进阶段（带门禁）")
    p.add_argument("--root", default=".")
    p.add_argument("--to", help="目标阶段；省略则前进一步")
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("set", help="修改状态字段")
    p.add_argument("--root", default=".")
    p.add_argument("--key", required=True)
    p.add_argument("--value", required=True)
    p.set_defaults(func=cmd_set)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
