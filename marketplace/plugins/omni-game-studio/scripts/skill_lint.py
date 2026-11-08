#!/usr/bin/env python3
"""skill_lint.py — 技能结构自测

产品是提示词，就得有测提示词的东西。本脚本只检查技能文件本身的结构合规，
不评估内容好坏，也不测用户的游戏。

用法:
  python skill_lint.py                       # 全量检查
  python skill_lint.py --skill cocos-engineering
  python skill_lint.py --json                # 机器可读
  python skill_lint.py --strict              # WARN 也算失败，用于发版前

判分四值（沿用 studio 惯例，宁可说"没评估"也不假装评过）:
  PASS          明确满足
  WARN          部分满足或不影响使用，建议改
  FAIL          明确不满足
  NOT ASSESSED  无法评估（文件读不到、检查项不适用）

退出码: 0 全过（允许 WARN）/ 1 有 FAIL / 2 无法评估
"""

import argparse
import json
import re
import sys
from pathlib import Path

ORDER = {"PASS": 0, "WARN": 1, "NOT ASSESSED": 2, "FAIL": 3}

# 插件内可校验的相对引用：只认这几类前缀，避免把项目里的 assets/xxx.json 当成死链
PLUGIN_REF = re.compile(
    r"(?:<plugin>/)?((?:references|templates|scripts|subagents|skills)/[\w./*\-]+\.(?:md|py|json|cfg|tscn|gd|cs|ts))"
)
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
FENCED = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
TRIGGER_HINTS = ("use when", "use for", "use whenever", "when the user",
                 "当", "用于", "适合", "需要")


def body_after_frontmatter(text):
    m = FRONTMATTER.match(text)
    return text[m.end():] if m else text


def parse_frontmatter(text):
    m = FRONTMATTER.match(text)
    if not m:
        return None
    data = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def resolve_ref(ref, skill_dir, root):
    """返回 (resolved, kind)。kind: file / glob / sibling / missing。

    sibling = 只在本技能目录之外的同级技能里找到。这种写法对人可读，但代理按自身
    目录解析会扑空，所以判 WARN 而不是 PASS。
    """
    ref = ref.replace("<plugin>/", "")
    bases = [skill_dir, root]
    if "*" in ref:
        for b in bases:
            if list(b.glob(ref)):
                return True, "glob"
        return False, "missing"
    for b in bases:
        p = b / ref
        if p.exists():
            return p, "file"
    if ref.startswith("references/"):
        for other in sorted((root / "skills").glob("*/" + ref)):
            if other.exists():
                return other, "sibling"
    return False, "missing"


def lint_skill(skill_dir: Path, root: Path):
    path = skill_dir / "SKILL.md"
    checks = []

    def add(code, verdict, msg):
        checks.append({"code": code, "verdict": verdict, "msg": msg})

    if not path.exists():
        for code in ("FM1", "FM2", "FM3", "LNK1", "LNK2", "TXT1", "SZ1"):
            add(code, "NOT ASSESSED", "SKILL.md 不存在")
        return checks

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        for code in ("FM1", "FM2", "FM3", "LNK1", "LNK2", "TXT1", "SZ1"):
            add(code, "NOT ASSESSED", f"读不到: {e}")
        return checks

    fm = parse_frontmatter(text)
    add("FM1", "PASS" if fm is not None else "FAIL",
        "frontmatter 存在" if fm else "缺少 --- 包裹的 frontmatter 首块")

    name = (fm or {}).get("name", "")
    if fm is None:
        add("FM2", "NOT ASSESSED", "无 frontmatter")
    elif not name:
        add("FM2", "FAIL", "frontmatter 缺 name")
    elif name != skill_dir.name:
        add("FM2", "FAIL", f"name '{name}' 与目录名 '{skill_dir.name}' 不一致")
    else:
        add("FM2", "PASS", f"name 与目录一致: {name}")

    desc = (fm or {}).get("description", "")
    if not desc:
        add("FM3", "FAIL", "缺 description" if fm is not None else "无 frontmatter")
    elif len(desc) < 20:
        add("FM3", "FAIL", f"description 过短（{len(desc)} 字符），无法判断何时该用")
    elif not any(h in desc.lower() for h in TRIGGER_HINTS):
        add("FM3", "WARN", "description 没有触发条件（Use when / 当…时 / 用于）")
    else:
        add("FM3", "PASS", f"description 有触发条件（{len(desc)} 字符）")

    body = body_after_frontmatter(text)
    refs = sorted(set(PLUGIN_REF.findall(body)))
    missing, siblings, resolved = [], [], []
    for ref in refs:
        got, kind = resolve_ref(ref, skill_dir, root)
        if kind == "missing":
            missing.append(ref)
        elif kind == "sibling":
            siblings.append(ref)
            resolved.append(got)
        elif kind == "file":
            resolved.append(got)
    if not refs:
        add("LNK1", "PASS", "无插件内相对引用（不适用）")
    elif missing:
        add("LNK1", "FAIL", "引用不存在: " + "、".join(missing))
    elif siblings:
        add("LNK1", "WARN",
            "引用落在同级技能里，按自身目录解析会扑空，建议写全 skills/<技能>/…: "
            + "、".join(siblings))
    else:
        add("LNK1", "PASS", f"{len(refs)} 处引用均存在")

    scripts = [p for p in resolved if p.suffix == ".py"]
    if not scripts:
        add("LNK2", "PASS", "无脚本引用（不适用）")
    else:
        bad = []
        for p in scripts:
            try:
                compile(p.read_text(encoding="utf-8"), str(p), "exec")
            except (SyntaxError, OSError, UnicodeDecodeError) as e:
                bad.append(f"{p.name}({type(e).__name__})")
        add("LNK2", "FAIL" if bad else "PASS",
            ("语法错误/读不到: " + "、".join(bad)) if bad else f"{len(scripts)} 个引用脚本可编译")

    # 只查正文里真正的遗留占位；提到这个标记本身的说明（写在反引号里）不算
    prose = INLINE_CODE.sub("", FENCED.sub("", body))
    marks = [m for m in ("[TODO]", "TODO:", "FIXME") if m in prose]
    add("TXT1", "PASS" if not marks else "FAIL",
        "无遗留占位标记" if not marks else "遗留占位: " + "、".join(marks))

    lines = len(text.splitlines())
    if lines <= 300:
        add("SZ1", "PASS", f"{lines} 行")
    elif lines <= 500:
        add("SZ1", "WARN", f"{lines} 行，超过 300；考虑把细节挪进 references/")
    else:
        add("SZ1", "FAIL", f"{lines} 行，超过 500；技能文件过重，必须拆分")

    return checks


def worst(verdicts):
    return max(verdicts, key=lambda v: ORDER[v]) if verdicts else "NOT ASSESSED"


def main():
    ap = argparse.ArgumentParser(description="技能结构自测")
    ap.add_argument("--root", help="插件根目录；默认取脚本所在位置的上两级")
    ap.add_argument("--skill", help="只检查一个技能")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN 也算失败")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print(f"找不到 skills/ 目录: {skills_dir}", file=sys.stderr)
        return 2

    dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    if args.skill:
        dirs = [p for p in dirs if p.name == args.skill]
        if not dirs:
            print(f"没有这个技能: {args.skill}", file=sys.stderr)
            return 2
    if not dirs:
        print("skills/ 下没有技能", file=sys.stderr)
        return 2

    report = []
    for d in dirs:
        checks = lint_skill(d, root)
        verdict = worst([c["verdict"] for c in checks])
        report.append({"skill": d.name, "verdict": verdict, "checks": checks})

    if args.json:
        print(json.dumps({"root": str(root), "skills": report}, ensure_ascii=False, indent=2))
    else:
        for item in report:
            print(f"\n{item['skill']}  →  {item['verdict']}")
            for c in item["checks"]:
                if c["verdict"] == "PASS":
                    continue
                print(f"  [{c['verdict']:<12}] {c['code']} {c['msg']}")
            fails = [c for c in item["checks"] if c["verdict"] == "FAIL"]
            warns = [c for c in item["checks"] if c["verdict"] == "WARN"]
            if not fails and not warns:
                print("  [PASS        ] 7/7 通过")
        print()
        tally = {}
        for item in report:
            tally[item["verdict"]] = tally.get(item["verdict"], 0) + 1
        print("合计: " + "  ".join(f"{k}={v}" for k, v in sorted(tally.items())) + f"  共 {len(report)} 个技能")

    verdicts = [i["verdict"] for i in report]
    if "FAIL" in verdicts:
        return 1
    if args.strict and "WARN" in verdicts:
        return 1
    if "NOT ASSESSED" in verdicts:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
