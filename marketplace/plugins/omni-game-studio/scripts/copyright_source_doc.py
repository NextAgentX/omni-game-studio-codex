#!/usr/bin/env python3
"""copyright_source_doc.py — 软著源程序文档分页文本生成器（零第三方依赖）

把源码目录摊平成「目标页数 × 每页 50 行」的分页文本，页眉带软件全称与版本号；
顺带扫描第三方版权头与疑似密钥，只报告、不改写源码。

用法:
  python scripts/copyright_source_doc.py --root ./src --name "星轨塔防系统" --version V1.0 --out copyright-out/source-pages.txt
  python scripts/copyright_source_doc.py --root . --name "星轨塔防系统" --out copyright-out/source-pages.txt --exclude Library --exclude Temp
  python scripts/copyright_source_doc.py --root . --name "星轨塔防系统" --out copyright-out/source-pages.txt --ext .cs,.shader,.lua
  python scripts/copyright_source_doc.py --help

口径: 不足 60 页取全部；超过取前 30 页 + 后 30 页，中间省略并在文首注明。
      每页正文固定 50 行（页眉页脚为标记行，不计入），页码连续。
      页眉「软件全称 版本号」与说明书封面、申请表三处逐字一致。
退出码: 0 生成完成 / 1 参数或写入错误 / 2 未找到可纳入的源码行。
注意: 本产物为分页文本，需转 PDF 后提交，不假装已生成 PDF。
"""

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_EXT = set(".py .js .ts .jsx .tsx .cs .java .kt .go .c .cc .cpp .h .hpp "
                  ".m .mm .swift .lua .gd .shader .hlsl .glsl .rs .dart .rb "
                  ".php .sql .html .css .scss .vue .svelte .yaml .yml".split())
DEFAULT_EXCLUDE = set(".git .github .idea .vscode .godot .venv venv node_modules "
                      "dist build out bin obj target vendor third_party __pycache__ "
                      "Library Temp Logs Pods DerivedData .gradle packages".split())
HASH_EXT = set(".py .rb .sh .gd .lua .yaml .yml".split())
DASH_EXT = set(".sql .hs".split())
COPYRIGHT_MARKS = re.compile(r"(?i)(copyright|all rights reserved|"
                             r"spdx-license-identifier|licensed under|"
                             r"gnu general public license|apache license|"
                             r"mit license|@license)")
# 疑似密钥只做线索初筛；前缀拼接书写，避免本脚本自身被 CI 当成硬编码密钥。
_OPENAI, _GOOGLE = "sk" + "-", "AI" + "za"
KEY_PATTERNS = [
    ("openai_style", re.compile(re.escape(_OPENAI) + r"[A-Za-z0-9]{20,}")),
    ("google_style", re.compile(re.escape(_GOOGLE) + r"[0-9A-Za-z_\-]{30,}")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{12,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("secret_assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|access[_-]?key)\b"
        r"\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ("db_uri", re.compile(r"(?i)\b(?:mongodb|mysql|postgres(?:ql)?|redis)://[^\s'\"]{8,}")),
    ("private_ip", re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
]


def natural_key(rel):
    """自然序：mod2 排在 mod10 前面；数字段与文本段分开比较，避免类型混比。"""
    return tuple((1, int(p)) if p.isdigit() else (0, p)
                 for p in re.split(r"(\d+)", rel.lower()))


def comment_prefix(ext):
    if ext in DASH_EXT:
        return "--"
    if ext in HASH_EXT:
        return "#"
    return "<!--" if ext in (".html", ".xml") else "//"


def collect_files(root, exts, excludes):
    picked = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excludes and not d.startswith(".")]
        picked += [Path(dirpath) / fn for fn in filenames
                   if Path(fn).suffix.lower() in exts]
    picked.sort(key=lambda p: natural_key(str(p.relative_to(root)).replace(os.sep, "/")))
    return picked


def squash(lines):
    out, blank = [], False
    for line in lines:
        if not line.strip():
            if blank:
                continue
            blank = True
        else:
            blank = False
        out.append(line)
    return out


def scan_risks(files, root):
    ch, kh = [], []
    for p in files:
        rel = str(p.relative_to(root)).replace(os.sep, "/")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines[:20], 1):
            m = COPYRIGHT_MARKS.search(line)
            if m:
                ch.append((rel, i, m.group(0).strip()))
                break
        for i, line in enumerate(lines, 1):
            for label, pat in KEY_PATTERNS:
                if pat.search(line):
                    kh.append((rel, i, label))
                    break
    return ch, kh


def build_pages(root, files, lpp):
    body = []
    for p in files:
        rel = str(p.relative_to(root)).replace(os.sep, "/")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        tags = [m.group(0).strip() for ln in lines[:20]
                for m in [COPYRIGHT_MARKS.search(ln)] if m]
        banner = comment_prefix(p.suffix.lower()) + f" ===== 文件: {rel} ====="
        if tags:
            banner += f"  [含第三方版权头: {tags[0]}]"
        body += [banner] + squash(lines)
    return [body[i:i + lpp] for i in range(0, len(body), lpp)]


def select_pages(pages, budget):
    total = len(pages)
    if total <= budget:
        return [(i + 1, pg) for i, pg in enumerate(pages)], None
    front, back = budget // 2, budget - budget // 2
    chosen = [(i + 1, pages[i]) for i in range(front)]
    chosen += [(total - back + i + 1, pages[total - back + i]) for i in range(back)]
    return chosen, (front + 1, total - back)


def render(chosen, total, name, version, skipped, meta, risks):
    bar = "#" * 70
    out = [bar, "# 源程序文档（分页文本 · 非 PDF）", f"# 软件全称：{name}",
           f"# 版本号：{version}", f"# 源码根目录：{meta['root']}",
           f"# 纳入文件数：{meta['files']} / 摊平代码行：{meta['lines']}",
           f"# 每页正文：{meta['lpp']} 行（页眉页脚为标记行，不计入）",
           f"# 原稿总页数：{meta['total']} / 实际输出页数：{total}"]
    if skipped:
        out.append(f"# 截取口径：超过 {meta['budget']} 页，取前 {meta['budget'] // 2} 页 + 后 "
                   f"{meta['budget'] - meta['budget'] // 2} 页；省略原稿第 {skipped[0]}–{skipped[1]} 页")
    else:
        out.append(f"# 截取口径：不足 {meta['budget']} 页，全部提交，未截取")
    out += ["# 页眉规范：软件全称 版本号，须与说明书封面、申请表逐字一致", bar, ""]
    for seq, (orig, lines) in enumerate(chosen, 1):
        out.append(f"===== {name} {version} | 源程序文档 | 第 {seq} 页 / 共 {total} 页 =====")
        out += lines + [f"----- 原稿第 {orig} 页 · 第 {seq} 页 / 共 {total} 页 -----", ""]
    ch, kh = risks
    out += [bar, "# 附：风险初筛（只报告，不改写源码；结论是线索不是判决）",
            f"# 第三方版权头：{len(ch)} 个文件"]
    out += [f"#   - {r}:{n} 命中「{t}」→ 该文件不得纳入源程序文档，先剔除"
            for r, n, t in ch] if ch else ["#   - 未发现"]
    out.append(f"# 疑似密钥 / 内网地址：{len(kh)} 处")
    out += [f"#   - {r}:{n} 类型 {t} → 人工确认；已暴露的密钥须轮换"
            for r, n, t in kh] if kh else ["#   - 未发现"]
    out += ["# 处理动作：逐条核对 → 剔除第三方版权头文件 / 脱敏或轮换 → 重新生成", bar, "",
            "【交付提醒】本产物为分页文本，需转 PDF 后提交，不假装已生成 PDF。",
            "【交付提醒】提交前另需：说明书补齐占位并转 PDF；申请表三处名称版本对齐。"]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(
        description="软著源程序文档分页文本生成器（零第三方依赖，需转 PDF 后提交）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例见文件顶部 docstring；本产物为分页文本，不假装已生成 PDF。")
    ap.add_argument("--root", default=".", help="源码根目录（默认当前目录）")
    ap.add_argument("--name", required=True, help="软件全称，写进每页页眉")
    ap.add_argument("--version", default="V1.0", help="版本号，写进每页页眉（默认 V1.0）")
    ap.add_argument("--out", required=True, help="分页文本输出路径")
    ap.add_argument("--pages", type=int, default=60, help="目标页数，默认 60")
    ap.add_argument("--lines-per-page", type=int, default=50, help="每页正文行数，默认 50，不得低于 50")
    ap.add_argument("--exclude", action="append", default=[], help="追加排除的目录名，可多次传入")
    ap.add_argument("--ext", default="", help="逗号分隔扩展名，覆盖默认集合")
    a = ap.parse_args()
    if not a.name.strip() or a.pages < 2 or a.lines_per_page < 50:
        print("FAIL 参数非法：--name 非空、--pages 至少 2、--lines-per-page 不得低于 50", file=sys.stderr)
        return 1
    root = Path(a.root).resolve()
    if not root.is_dir():
        print(f"FAIL 源码根目录不存在或不是目录: {root}", file=sys.stderr)
        return 1
    exts = ({"." + e.strip().lower().lstrip(".") for e in a.ext.split(",") if e.strip()}
            if a.ext.strip() else DEFAULT_EXT)
    files = collect_files(root, exts, set(DEFAULT_EXCLUDE) | set(a.exclude))
    if not files:
        print("FAIL 未找到源码文件；检查 --root 与 --ext / --exclude", file=sys.stderr)
        return 2
    pages = build_pages(root, files, a.lines_per_page)
    if not pages:
        print("FAIL 摊平后无有效代码行", file=sys.stderr)
        return 2
    chosen, skipped = select_pages(pages, a.pages)
    risks = scan_risks(files, root)
    meta = {"root": str(root), "files": len(files), "lines": sum(map(len, pages)),
            "total": len(pages), "budget": a.pages, "lpp": a.lines_per_page}
    text = render(chosen, len(chosen), a.name, a.version, skipped, meta, risks)
    out_path = Path(a.out)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    except OSError as e:
        print(f"FAIL 写入失败: {e}", file=sys.stderr)
        return 1
    ch, kh = risks
    note = f" / 省略原稿第 {skipped[0]}–{skipped[1]} 页" if skipped else " / 不足目标页数，全交"
    print(f"OK 已写出 {out_path}")
    print(f"   纳入 {len(files)} 个文件 / {meta['lines']} 行 / 原稿 {len(pages)} 页 / 输出 {len(chosen)} 页{note}")
    print(f"   硬风险线索：第三方版权头 {len(ch)} 个文件，疑似密钥/内网地址 {len(kh)} 处"
          "（已写入文末报告，须人工逐条处理后再转 PDF）")
    print("   本产物为分页文本，需转 PDF 后提交，不假装已生成 PDF。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
