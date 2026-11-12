#!/usr/bin/env python3
"""omni_state.py — 流水线状态、阶段门禁、证据校验与会话检查点

用法:
  python omni_state.py init  --root . --engine godot --version 4.3 --platforms web,android
  python omni_state.py init  --root . --engine unreal --version 5.4 --platforms windows
  python omni_state.py status --root .
  python omni_state.py advance --root . --to gdd
  python omni_state.py check  --root . --stage gdd
  python omni_state.py set    --root . --key engine --value unity

  python omni_state.py evidence list  --root .
  python omni_state.py evidence check --root .          # 截图证据是否存在且未过期
  python omni_state.py checkpoint --root . --task "..." --next "..." [--blocked ...] [--note ...]
  python omni_state.py checkpoint --root . --show

状态文件: <root>/.omni/state.json
检查点:   <root>/.omni/active.md
退出码: 0 通过 / 1 失败（门禁未过）/ 2 无法评估（NOT ASSESSED）
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = ".omni"
STATE_FILE = "state.json"
ACTIVE_FILE = "active.md"
SESSION_LOGS = "session-logs"
EVIDENCE_ROOT = "docs/qa/evidence"

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


# ---------------------------------------------------------------------------
# 证据：截图留证是否存在、是否还覆盖当前代码
# ---------------------------------------------------------------------------

def sha256_file(path: Path):
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def evidence_bundles(root: Path):
    base = root / EVIDENCE_ROOT
    if not base.is_dir():
        return []
    bundles = []
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        receipt = None
        rec_path = d / "receipt.json"
        if rec_path.exists():
            try:
                receipt = json.loads(rec_path.read_text(encoding="utf-8"))
            except Exception:
                receipt = None
        shots = sorted(d.glob("*.png"))
        sort_key = (receipt or {}).get("at") or ""
        bundles.append({"dir": d, "receipt": receipt, "shots": shots, "at": sort_key})
    return bundles


def png_size(path: Path):
    """Read PNG IHDR dimensions without Pillow; reject truncated or non-PNG files."""
    try:
        with path.open("rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if (len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n"
            or head[12:16] != b"IHDR"):
        return None
    width = int.from_bytes(head[16:20], "big")
    height = int.from_bytes(head[20:24], "big")
    if width <= 0 or height <= 0:
        return None
    return [width, height]


def check_evidence(root: Path) -> tuple:
    """返回 (ok, messages)。ok=False 表示不能拿这份证据当"看过"。

    三值语义与 skill_lint 一致：通过 / 过期（仍存在但绑定的文件已变）/ 没有证据。
    """
    bundles = evidence_bundles(root)
    if not bundles:
        return False, [
            f"没有证据: {EVIDENCE_ROOT}/ 下没有任何记录。",
            "→ 先跑一次留证: python scripts/build_check.py --project . --run --capture <名字>",
            "→ 解析通过不等于跑起来，跑起来不等于看得对——这一步不能由文档替代。",
        ]

    latest = max(bundles, key=lambda b: b["at"] or b["dir"].name)
    name = latest["dir"].name
    msgs = [f"· 最新证据: {EVIDENCE_ROOT}/{name}"]

    if not latest["shots"]:
        return False, msgs + [f"（没有截图）: {name}/ 里有回执但没有任何截图，画面未被捕获。"]
    msgs.append("· 截图: " + ", ".join(p.name for p in latest["shots"]))

    receipt = latest["receipt"]
    if not receipt:
        return False, msgs + [f"（没有回执）: {name}/receipt.json 缺失或无法解析，无法判断证据覆盖范围。"]

    shot_meta = receipt.get("screenshot")
    if not isinstance(shot_meta, dict) or not isinstance(shot_meta.get("path"), str):
        return False, msgs + [
            "（回执缺少截图信息）: receipt.json 没有 screenshot.path，无法确认是哪张图。"]
    rel_shot = Path(shot_meta["path"])
    bundle_dir = latest["dir"].resolve()
    shot_path = (bundle_dir / rel_shot).resolve()
    try:
        shot_path.relative_to(bundle_dir)
    except ValueError:
        return False, msgs + [
            f"（截图路径非法）: {shot_meta['path']!r} 逃出了证据目录 {name}/。"]
    if not shot_path.is_file():
        return False, msgs + [
            f"（截图缺失）: 回执指向 {shot_meta['path']!r}，但该文件不存在。"]
    actual_digest = sha256_file(shot_path)
    if not shot_meta.get("sha256"):
        return False, msgs + [
            "（截图没有指纹）: 旧版回执未记录 screenshot.sha256，无法判断图片是否被替换；请重新留证。"]
    if actual_digest != shot_meta["sha256"]:
        return False, msgs + [
            "（截图已改动）: 回执记录的 screenshot.sha256 与当前图片不一致，画面不再可信；请重新留证。"]
    actual_size = png_size(shot_path)
    if actual_size is None:
        return False, msgs + [
            "（截图不是有效 PNG）: 文件头或 IHDR 无效，不能作为画面证据。"]
    shot_size = shot_meta.get("size")
    if shot_size is not None and (not isinstance(shot_size, list)
                                  or len(shot_size) != 2
                                  or not all(isinstance(v, int) and v > 0 for v in shot_size)):
        return False, msgs + [
            "（截图尺寸无效）: receipt.json 里的 screenshot.size 必须是两个正整数。"]
    if shot_size is not None and shot_size != actual_size:
        return False, msgs + [
            "（截图尺寸不符）: 回执记录 %dx%d，实际 PNG 为 %dx%d，证据不可信。"
            % (shot_size[0], shot_size[1], actual_size[0], actual_size[1])]

    if receipt.get("exit_code") not in (0, None):
        msgs.append(f"注意: 捕获时进程退出码 {receipt.get('exit_code')}，画面可用但进程非正常退出。")

    sources = receipt.get("sources") or []
    if not sources:
        msgs.append("WARN: 这份证据没有绑定任何源文件（捕获时目录不是 git 仓库），无法判断新鲜度。")
        return True, msgs

    changed, missing = [], []
    for s in sources:
        p = root / s.get("path", "")
        if not p.exists():
            missing.append(s.get("path"))
            continue
        if s.get("sha256") is None:
            continue
        if sha256_file(p) != s.get("sha256"):
            changed.append(s.get("path"))

    if missing:
        msgs.append("被覆盖的文件已不存在: " + "、".join(missing[:5]))
    if changed:
        msgs.append("（过期）: 证据之后这些文件又改过，画面不再代表当前代码: "
                    + "、".join(changed[:5]) + (" …" if len(changed) > 5 else ""))
        msgs.append("→ 重新留证: python scripts/build_check.py --project . --capture-only <名字>")
        return False, msgs

    msgs.append(f"· 证据覆盖 {len(sources)} 个改动文件，均未被改动 → 未过期")
    return True, msgs


# ---------------------------------------------------------------------------
# 会话检查点：文件是记忆，不是对话
# ---------------------------------------------------------------------------

CP_BLOCK = re.compile(r"<!-- CHECKPOINT -->.*?<!-- /CHECKPOINT -->", re.S)
NARRATIVE_MARK = "## 记录"


def active_path(root: Path) -> Path:
    return root / STATE_DIR / ACTIVE_FILE


def cmd_checkpoint(args):
    root = Path(args.root).resolve()
    p = active_path(root)

    if args.show:
        if not p.exists():
            print(f"没有检查点: {p}")
            return 1
        print(p.read_text(encoding="utf-8"))
        return 0

    data = load(root)
    stage = data.get("stage", "unknown") if data else "unknown"
    existing = p.read_text(encoding="utf-8") if p.exists() else ""

    files = [f.strip() for f in (args.files or "").split(",") if f.strip()]
    block = "\n".join([
        "<!-- CHECKPOINT -->",
        f"- 当前任务: {args.task or '(未填)'}",
        f"- 下一步: {args.next or '(未填)'}",
        f"- 卡在: {args.blocked or '无'}",
        f"- 进行中的文件: {', '.join(files) or '无'}",
        f"- 待定问题: {args.question or '无'}",
        f"- 更新于: {now()}",
        "<!-- /CHECKPOINT -->",
    ])

    header = f"# 会话检查点\n\n阶段: {stage}\n\n<!-- STATUS -->\nStage: {stage}\n<!-- /STATUS -->\n\n"
    if existing and CP_BLOCK.search(existing):
        text = CP_BLOCK.sub(block, existing, count=1)
        if "<!-- STATUS -->" not in text:
            text = header + text
    else:
        body = existing.split(NARRATIVE_MARK, 1)[1] if NARRATIVE_MARK in existing else ""
        text = header + block + "\n\n" + NARRATIVE_MARK + body

    if args.note:
        entry = f"- {now()[:19]} {args.note}\n"
        if NARRATIVE_MARK in text:
            head, tail = text.split(NARRATIVE_MARK, 1)
            text = head + NARRATIVE_MARK + tail.rstrip("\n") + "\n" + entry
        else:
            text = text.rstrip("\n") + "\n\n" + NARRATIVE_MARK + "\n" + entry

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

    # 叙述区太长就切到 session-logs，检查点本身保留
    if NARRATIVE_MARK in text:
        narrative = text.split(NARRATIVE_MARK, 1)[1]
        if len(narrative.splitlines()) > 200:
            log_dir = root / STATE_DIR / SESSION_LOGS
            log_dir.mkdir(parents=True, exist_ok=True)
            log = log_dir / f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"
            log.write_text("# 会话记录\n" + narrative, encoding="utf-8")
            head = text.split(NARRATIVE_MARK, 1)[0]
            p.write_text(head + NARRATIVE_MARK + "\n- （已归档到 "
                         f"{log.relative_to(root).as_posix()}）\n", encoding="utf-8")
            print(f"叙述区超过 200 行，已归档: {log.relative_to(root)}")

    print(f"检查点已写入: {p.relative_to(root)}")
    return 0


def print_evidence(msgs, ok=True):
    """打印证据校验结果。

    → 开头是补救提示、· 开头是信息、WARN/注意/被覆盖 是警告，都按中性打印；
    其余消息按整体结论套 OK / FAIL，免得出错时把"最新证据是哪个"也标成失败。
    """
    for m in msgs:
        if m.startswith(("→", "·", "WARN", "注意", "被覆盖")):
            print("  " + m)
        else:
            print(("  OK  " if ok else "  FAIL ") + m)


def cmd_evidence(args):
    root = Path(args.root).resolve()
    if args.action == "list":
        bundles = evidence_bundles(root)
        if not bundles:
            print(f"{EVIDENCE_ROOT}/ 下没有任何证据。")
            return 1
        print(f"{'证据':<24}{'截图':<8}{'覆盖文件':<10}{'时间'}")
        print("-" * 60)
        for b in bundles:
            n = len((b["receipt"] or {}).get("sources") or [])
            print(f"{b['dir'].name:<24}{len(b['shots']):<8}{n:<10}{b['at'] or '-'}")
        return 0

    ok, msgs = check_evidence(root)
    print_evidence(msgs, ok)
    return 0 if ok else 1


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
        print("未初始化。先运行: python omni_state.py init --root . --engine <godot|unity|cocos|unreal>")
        return 1

    print(f"项目: {data.get('project')}   引擎: {data.get('engine')} {data.get('engine_version','')}".rstrip())
    print(f"平台: {', '.join(data.get('platforms') or []) or '(未指定)'}")
    print(f"当前阶段: {data.get('stage')}")
    bundles = evidence_bundles(root)
    if bundles:
        latest = max(bundles, key=lambda b: b["at"] or b["dir"].name)
        print(f"截图证据: {len(bundles)} 份，最新 {latest['dir'].name}"
              f"（{', '.join(p.name for p in latest['shots']) or '无截图'}）")
    else:
        print("截图证据: 无（qa 之后必须先留证一次）")
    print("")

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
    if args.evidence:
        eok, emsgs = check_evidence(root)
        print("")
        print_evidence(emsgs, eok)
        ok = ok and eok
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

    # 离开 qa 之后就是"能不能发"的判断，必须有截图证据，文档不能代替
    if STAGES.index(target) > STAGES.index("qa") and not args.no_evidence:
        print("\n证据校验（qa → 之后）：")
        eok, emsgs = check_evidence(root)
        print_evidence(emsgs, eok)
        if not eok:
            print(f"\n门禁未过：没有可用的截图证据，不能进 {target}。")
            print("确实要先推进可加 --no-evidence，但交付时必须说明没看过画面。")
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
    if args.key == "engine" and args.value not in {"cocos", "unity", "godot", "unreal"}:
        print("引擎必须是 cocos、unity、godot 或 unreal")
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
    p.add_argument("--engine", required=True, choices=["cocos", "unity", "godot", "unreal"])
    p.add_argument("--version")
    p.add_argument("--platforms", help="逗号分隔，如 web,android,wechat")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status", help="查看各阶段状态")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("check", help="校验某阶段工件")
    p.add_argument("--root", default=".")
    p.add_argument("--stage", required=True, choices=list(STAGE_OUTPUT))
    p.add_argument("--evidence", action="store_true", help="同时校验截图证据")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("advance", help="推进阶段（带门禁）")
    p.add_argument("--root", default=".")
    p.add_argument("--to", help="目标阶段；省略则前进一步")
    p.add_argument("--no-evidence", action="store_true",
                   help="跳过 qa 之后的截图证据校验（交付时必须说明没看过画面）")
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("evidence", help="截图证据列表与新鲜度校验")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="check", choices=["check", "list"])
    p.set_defaults(func=cmd_evidence)

    p = sub.add_parser("checkpoint", help="写入/查看会话检查点")
    p.add_argument("--root", default=".")
    p.add_argument("--show", action="store_true")
    p.add_argument("--task", help="当前任务")
    p.add_argument("--next", help="下一步")
    p.add_argument("--blocked", help="卡在哪")
    p.add_argument("--files", help="进行中的文件，逗号分隔")
    p.add_argument("--question", help="待定问题")
    p.add_argument("--note", help="追加一条叙述记录")
    p.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser("set", help="修改状态字段")
    p.add_argument("--root", default=".")
    p.add_argument("--key", required=True)
    p.add_argument("--value", required=True)
    p.set_defaults(func=cmd_set)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
