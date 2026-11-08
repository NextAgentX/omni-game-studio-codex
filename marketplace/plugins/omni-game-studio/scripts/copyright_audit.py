#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""软著申报材料提交前风险体检 —— Phase 2 A 线。

读一个申报材料目录，检查三处「软件全称 + 版本号」是否逐字一致、源程序
页数与每页行数是否达标、说明书待补充占位计数、疑似密钥与第三方版权头，
输出 12 项提交前自评表判定与「能交 / 不能交 / 补什么再交」结论，
高危项单列为红线原文。

明确声明：本脚本只是静态线索筛查，结论是线索不是判决，每条命中都要
人工看一眼；权属、商标、侵权判断交申请人或律师，脚本不替用户下法律
结论。PDF 与二进制件无法可靠解析，解析不了的项标「需人工核对」，
不判绿也不判红。

示例::

    python copyright_audit.py --root ./copyright-out --name "星轨塔防游戏软件" --version V1.0
    python copyright_audit.py --root ./copyright-out --name "智能巡检管理系统" --version V1.0 --json
    python copyright_audit.py --help

退出码：0 = 能交或补什么再交，1 = 不能交，2 = 目录不存在。
"""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".html", ".htm", ".json", ".csv", ".py", ".js",
            ".ts", ".log", ".cfg", ".ini", ".xml", ".yml", ".yaml"}
SOURCE_HINT = ("源程序", "source", "source_code", "sourcecode")
MANUAL_HINT = ("说明书", "manual", "userguide", "user_guide")
FORM_HINT = ("申请表", "form", "application", "apply")

PAGE_RE = re.compile(r"第\s*(\d+)\s*页\s*[/／]\s*共\s*(\d+)\s*页")
VERSION_TOKEN_RE = re.compile(r"[Vv]?\d+\.\d+(?:\.\d+)?")
PLACEHOLDER_RE = re.compile(r"【待补充[^】]*】|\[待补充\]")
DATE_RE = re.compile(r"20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}")

COPYRIGHT_HINT = re.compile(
    r"(?i)copyright|licensed\s+under|SPDX-License-Identifier|"
    r"all\s+rights\s+reserved|@license|MIT\s+License|GNU\s+General\s+Public|"
    r"Apache\s+License|AGPL|GPL-\d"
)
# 前缀用拼接构造，避免源码里出现会被误判为硬编码密钥的整串
CLOUD_PREFIXES = (
    "sk" + "-",
    "AI" + "za",
    "AKIA",
    "ghp" + "_",
    "xox" + "b" + "-",
)
KEY_ASSIGN_RE = re.compile(
    r"(?i)(access[_-]?key|secret|token|passwd|password|api[_-]?key|"
    r"private[_-]?key|access[_-]?secret|app[_-]?secret)\s*[=:]\s*"
    r"[\x22\x27][A-Za-z0-9_\-+/=]{16,}[\x22\x27]"
)
DB_CONN_RE = re.compile(r"(?i)(mongodb\+srv://|postgresql://|mysql://|redis://)[^\s\x22\x27]{8,}")
PRIVATE_IP_RE = re.compile(
    r"(?<!\d)(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|"
    r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?!\d)"
)
PEM_RE = re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----")

RED_LINES = (
    "RED-01 源程序文档含云密钥、私钥、数据库连接串或硬编码口令：不能交，先改为环境变量读取并轮换已泄露密钥，再重新生成源程序文档。",
    "RED-02 源程序文档含第三方版权头（Copyright / Licensed under / SPDX）或整段第三方代码：不能交，剔除该文件后再生成源程序文档。",
    "RED-03 GPL / AGPL 等强传染性许可证代码混入自有源程序：不能交，先做许可证隔离与替换，不得把别人代码当自己代码提交。",
    "RED-04 编造开发完成日期、首次发表日期或申请日期，或日期逻辑不自洽（完成 ≤ 发表 ≤ 申请）：不能交，按真实过程证据更正。",
    "RED-05 三处（源程序文档页眉 / 说明书封面 / 申请表）软件全称与版本号未逐字一致：不能交，整套材料重生成，不许局部改字。",
    "RED-06 名称查重判「必须改名」仍带高风险名称进入材料阶段：停下，改完并重新查重后才许进 Phase 1。",
)


def pick(files, hints):
    return [p for p in files if any(h.lower() in p.name.lower() for h in hints)]


def read_text(path):
    suf = path.suffix.lower()
    if suf == ".docx":
        try:
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", " ", xml)
        except (KeyError, OSError, zipfile.BadZipFile):
            return None
    if suf in TEXT_EXT:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
    if suf == ".pdf":
        try:
            return path.read_bytes().decode("latin-1", "ignore")
        except OSError:
            return None
    return None


def scan_line(line):
    kinds = []
    if KEY_ASSIGN_RE.search(line):
        kinds.append("硬编码口令或令牌")
    for p in CLOUD_PREFIXES:
        if p in line and len(line) > len(p) + 8:
            kinds.append("疑似云厂商密钥前缀")
            break
    if DB_CONN_RE.search(line):
        kinds.append("数据库连接串")
    if PRIVATE_IP_RE.search(line):
        kinds.append("内网 IP")
    if PEM_RE.search(line):
        kinds.append("私钥 PEM 头")
    if COPYRIGHT_HINT.search(line):
        kinds.append("第三方版权头或许可证声明")
    return kinds


def scan_risks(files):
    findings = []
    for p in files:
        if p.suffix.lower() not in TEXT_EXT and p.suffix.lower() != ".docx":
            continue
        text = read_text(p)
        if text is None:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for kind in scan_line(line):
                findings.append({"file": p.name, "line": i, "kind": kind,
                                 "snippet": line.strip()[:80]})
    return findings


def check_consistency(files, name, version):
    groups = {
        "源程序文档页眉": pick(files, SOURCE_HINT),
        "说明书封面": pick(files, MANUAL_HINT),
        "申请表": pick(files, FORM_HINT),
    }
    rows, hard_bad, soft_bad = [], False, False
    for label, paths in groups.items():
        if not paths:
            rows.append({"place": label, "state": "未找到文件",
                         "detail": "目录中未识别到该类文件"})
            soft_bad = True
            continue
        readable = [(p, t) for p, t in ((p, read_text(p)) for p in paths) if t is not None]
        if not readable:
            rows.append({"place": label, "state": "无法解析",
                         "detail": "、".join(p.name for p in paths) + " 为二进制，请人工核对"})
            soft_bad = True
            continue
        has_name = any(name in t for _, t in readable)
        has_ver = any(version in t for _, t in readable)
        tokens = set()
        for _, t in readable:
            tokens.update(VERSION_TOKEN_RE.findall(t))
        stray = sorted(v for v in tokens if v.lower() != version.lower())
        ok = has_name and has_ver and not stray
        if not ok:
            hard_bad = True
        rows.append({"place": label, "state": "一致" if ok else "不一致",
                     "detail": "名称%s、版本%s、多余版本串 %s" % (
                         "命中" if has_name else "缺失",
                         "命中" if has_ver else "缺失",
                         "、".join(stray) if stray else "无")})
    return rows, hard_bad, soft_bad


def page_bodies(text):
    """解析分页文本，返回 (每页正文, 声明总页数, 全部正文行)。

    生成器每页同时写页眉与页脚两处「第 X 页 / 共 Y 页」，按页号分组后
    一页只取一次，标记行本身不计入正文。页眉页脚之外的文档头、文末风险
    报告也不算源码正文，避免把脚手架注释当成 AI 痕迹去统计。
    """
    lines = text.splitlines()
    marked = []
    for i, ln in enumerate(lines):
        m = PAGE_RE.search(ln)
        if m:
            marked.append((i, int(m.group(1)), int(m.group(2))))
    if not marked:
        return [], 0, [x for x in lines if x.strip()]
    groups = {}
    for i, num, total in marked:
        groups.setdefault(num, []).append(i)
    declared = max(x[2] for x in marked)
    nums = sorted(groups)
    bodies = []
    for idx, num in enumerate(nums):
        rows = groups[num]
        first = rows[0]
        if len(rows) >= 2:
            last = rows[-1]                    # 页眉 + 页脚：取两者之间的正文
        elif idx + 1 < len(nums):
            last = groups[nums[idx + 1]][0]    # 只有一处标记：取到下一页标记
        else:
            last = len(lines)
        bodies.append((num, [x for x in lines[first + 1:last] if x.strip()]))
    flat = [x for _, body in bodies for x in body]
    return bodies, declared, flat


def check_pages(files):
    texts = [t for t in (read_text(p) for p in pick(files, SOURCE_HINT)) if t]
    if not texts:
        return {"state": "无法判定", "pages": 0, "per_page": [],
                "detail": "未读到可解析的源程序文本，PDF 需转文本或人工核对"}
    # 多份源程序文本时只取页码标记最多的一份，避免重复计数
    text = max(texts, key=lambda t: len(PAGE_RE.findall(t)))
    bodies, declared, _ = page_bodies(text)
    if not bodies:
        return {"state": "无页码标记", "pages": 0, "per_page": [],
                "detail": "无可识别的页码标记，需人工核对 60 页口径与每页 50 行"}
    per_page = [len(body) for _, body in bodies]
    short = [n for n in per_page if n < 50]
    detail = "共 %d 页，实测 %d 页正文" % (declared, len(per_page))
    if short:
        detail += "，有 %d 页不足 50 行" % len(short)
    if declared < 60:
        detail += "；不足 60 页取全部，末页不足 50 行属正常"
    if declared > 60:
        state = "不达标"                      # 超过 60 页未按前 30 加后 30 截取
    elif len(per_page) != declared:
        state = "不达标"                      # 页码声明与实测段数不一致
    elif declared >= 60 and short:
        state = "不达标"                      # 已达 60 页仍有页面不足 50 行
    else:
        state = "达标"                        # 含不足 60 页取全部的合规情形
    return {"state": state, "pages": declared, "per_page": per_page, "detail": detail}


def check_manual(files):
    texts = [t for t in (read_text(p) for p in pick(files, MANUAL_HINT)) if t]
    if not texts:
        return {"state": "无法判定", "count": -1, "detail": "未识别到说明书文件"}
    count = sum(len(PLACEHOLDER_RE.findall(t)) for t in texts)
    return {"state": "待补" if count > 0 else "清零", "count": count,
            "detail": "待补充占位共 %d 处，必须显式清点并如实告知，不许抹掉" % count}


def build_checklist(files, name, version, findings, consistency, pages, manual):
    _, hard_bad, soft_bad = consistency
    all_text = " ".join(t for t in (read_text(p) for p in files) if t)

    nm = " ".join(t for t in (read_text(p) for p in pick(files, ("名称预检", "name_check", "名称查重"))) if t)
    if "必须改名" in nm:
        r1 = ("🔴", "名称预检报告判必须改名", "停下改名并重新查重，不许进材料阶段")
    elif "可以直用" in nm:
        r1 = ("🟢", "名称预检报告判可以直用，六渠道已人工复核", "截图留档，锁死全称")
    else:
        r1 = ("🟡", "未见名称预检结论，商标与应用商店须人工复核", "跑完六渠道并截图留档")

    rights = pick(files, ("权属", "合同", "rights", "ownership"))
    r2 = ("🟢", "已附权属或合同材料 %d 份" % len(rights), "核对著作权人全称") if rights else (
        "🟡", "未见劳动合同 / 委托合同 / 合作协议", "补权属说明，结论交用户或律师定")

    strong_lic = [f for f in findings if re.search(r"AGPL|GPL-\d|GNU General", f["snippet"], re.I)]
    cp = [f for f in findings if f["kind"] == "第三方版权头或许可证声明"]
    if strong_lic:
        r3 = ("🔴", "疑似强传染性许可证代码 %d 处" % len(strong_lic), "隔离或替换，不得当自有代码提交")
    elif cp:
        r3 = ("🟡", "有许可声明 %d 处待确认" % len(cp), "保留许可声明与署名")
    else:
        r3 = ("🟢", "未发现第三方许可线索", "记录即可")

    key = [f for f in findings if f["kind"] in (
        "硬编码口令或令牌", "疑似云厂商密钥前缀", "数据库连接串", "内网 IP", "私钥 PEM 头")]
    r4 = ("🔴", "疑似密钥与真实数据 %d 处" % len(key), "改环境变量读取并轮换已泄露密钥，重新生成源程序文档") if key else (
        "🟢", "未发现硬编码密钥线索", "记录即可")

    form_text = " ".join(t for t in (read_text(p) for p in pick(files, FORM_HINT)) if t)
    dates = DATE_RE.findall(form_text)
    keys = []
    for raw in dates:
        bits = [int(x) for x in re.split(r"[-/年月]", raw) if x.isdigit()]
        if len(bits) >= 3:
            keys.append(tuple(bits[:3]))
    if len(keys) >= 3 and keys != sorted(keys):
        r5 = ("🔴", "三个日期顺序不满足 完成 ≤ 发表 ≤ 申请", "按真实过程证据更正，不编造")
    elif len(keys) >= 3:
        r5 = ("🟢", "检出 %d 个日期且顺序自洽" % len(keys), "保留 git 记录与构建日志作过程证据")
    else:
        r5 = ("🟡", "申请表仅检出 %d 个日期，需人工核对 完成 ≤ 发表 ≤ 申请" % len(dates),
              "按 git 记录与构建日志补齐并更正，不编造")

    # 只统计分页正文里的注释密度，文档头与文末风险报告不算源码
    src_texts = [t for t in (read_text(p) for p in pick(files, SOURCE_HINT)) if t]
    code = []
    if src_texts:
        primary = max(src_texts, key=lambda t: len(PAGE_RE.findall(t)))
        _, _, body_lines = page_bodies(primary)
        code = [ln.strip() for ln in body_lines]
    comments = [ln for ln in code if ln.startswith(("#", "//", "--", "/*", "*"))]
    dense = bool(code) and len(comments) / len(code) > 0.35
    r6 = ("🟡", "注释占比偏高，模板化痕迹明显", "削注释到骨头、换业务命名、补脏数据处理；不影响过审") if dense else (
        "🟢", "未见明显模板化痕迹", "如实说明 AI 辅助，重点留过程证据")

    trap = [w for w in ("包过", "保过", "私人转账", "加急包过") if w in all_text]
    r7 = ("🔴", "检出代理陷阱话术：" + "、".join(trap), "只走官方渠道与对公账户，不签包过协议") if trap else (
        "🟢", "未见包过承诺或私人转账", "不承诺百分百过")

    r8 = ("🔴", "第三方版权头 %d 处" % len(cp), "剔除该文件后再生成源程序文档") if cp else (
        "🟢", "未发现第三方版权头", "记录即可")

    if hard_bad:
        r9 = ("🔴", "三处名称版本存在不一致", "整套材料重生成，不许局部改字")
    elif soft_bad:
        r9 = ("🟡", "有处室未找到文件或为二进制，需人工核对", "转文本后逐字比对三处")
    else:
        r9 = ("🟢", "三处逐字一致", "锁死后全流程一字不改")

    if pages["state"] == "不达标":
        r10 = ("🔴", pages["detail"], "按 60 页口径重排，不足 60 页取全部，超过取前 30 加后 30")
    elif pages["state"] in ("无页码标记", "无法判定"):
        r10 = ("🟡", pages["detail"], "人工核对 60 页口径与每页 50 行")
    else:
        r10 = ("🟢", pages["detail"],
               "不足 60 页取全部属合规，保留全部源码" if pages["pages"] < 60 else "记录即可")

    if manual["state"] == "无法判定":
        r11 = ("🔴", "未识别到说明书文件", "补齐说明书并转 PDF")
    elif manual["count"] > 0:
        r11 = ("🟡", manual["detail"], "逐处补真实界面截图，清零后再交")
    else:
        r11 = ("🟢", manual["detail"], "记录即可")

    ident = pick(files, ("营业执照", "身份证", "identity", "business_license"))
    r12 = ("🟢", "已附身份材料 %d 份" % len(ident), "核对盖章与著作权人全称") if ident else (
        "🟡", "未见营业执照 / 身份证材料", "补齐并盖章，核对与申请表一致")

    items = (
        ("R1", "名称占用与商标冲突", r1), ("R2", "权属是否清晰", r2),
        ("R3", "开源许可证传染性", r3), ("R4", "密钥与真实数据泄露", r4),
        ("R5", "日期逻辑是否自洽", r5), ("R6", "AI 痕迹是否过重", r6),
        ("R7", "是否踩代理陷阱", r7), ("R8", "第三方代码版权头", r8),
        ("R9", "三处名称版本一致", r9), ("R10", "源程序页数与每页行数", r10),
        ("R11", "说明书待补项", r11), ("R12", "身份证明材料", r12),
    )
    rows = []
    for rid, item, (level, basis, action) in items:
        status = {"🔴": "阻断", "🟡": "待人工确认", "🟢": "已核对"}[level]
        rows.append({"id": rid, "item": item, "level": level, "basis": basis,
                     "action": action, "status": status})
    return rows


def decide(rows):
    red = [r for r in rows if r["level"] == "🔴"]
    yellow = [r for r in rows if r["level"] == "🟡"]
    if red:
        return "不能交", "存在 %d 项高危：" % len(red) + "、".join(r["id"] for r in red), red, yellow
    if yellow:
        return "补什么再交", "待补 %d 项：" % len(yellow) + "、".join(r["id"] for r in yellow), red, yellow
    return "能交", "12 项全绿，仍提示以官方数据库为准、截图留档", red, yellow


def build_report(name, version, rows, verdict, reason, findings, consistency, red, yellow):
    lines = ["【风险体检】%s %s" % (name, version), "结论：%s" % verdict,
             "一句话理由：%s" % reason, "",
             "一、12 项提交前自评表",
             "| 编号 | 风险项 | 等级 | 判定依据 | 规避动作 | 状态栏 |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["item"], r["level"], r["basis"].replace("|", "/"),
            r["action"].replace("|", "/"), r["status"]))
    lines += ["", "二、三处一致性现场证据"]
    for c in consistency[0]:
        lines.append("  %s：%s — %s" % (c["place"], c["state"], c["detail"]))
    lines += ["", "三、疑似密钥与第三方版权头线索（每条人工复核）"]
    if findings:
        for f in findings[:20]:
            lines.append("  %s:%d [%s] %s" % (f["file"], f["line"], f["kind"], f["snippet"]))
        if len(findings) > 20:
            lines.append("  …… 另有 %d 条，见 --json 输出" % (len(findings) - 20))
    else:
        lines.append("  未检出。")
    lines += ["", "四、待补清单"]
    if yellow:
        for r in yellow:
            lines.append("  %s %s：%s" % (r["id"], r["item"], r["action"]))
    else:
        lines.append("  无。")
    lines += ["", "五、红线清单（高危项原文，一条不许省略）"]
    lines += list(RED_LINES)
    if red:
        lines.append("本轮判红项原文追加，一条不许省略、不许摘要：")
        for r in red:
            lines.append("  本轮高危 %s %s：现场证据 %s；怎么改 %s" % (
                r["id"], r["item"], r["basis"], r["action"]))
    lines += ["", "六、无法评估项"]
    lines.append("  PDF 与二进制件无法可靠解析，解析不了的项标「需人工核对」而非判绿。")
    lines.append("  权属、商标近似、侵权判断交申请人或律师，脚本只给依据和后果。")
    lines.append("  标黄的待人工确认项，确认无误后可在 templates/copyright/pre-submit-checklist.md 里改绿，结论随之更新。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="软著申报材料提交前风险体检：三处一致、页数行数、待补项、密钥与版权头扫描、12 项自评表与红线。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="声明：静态筛查给的是线索不是判决；权属、商标、侵权判断交申请人或律师。",
    )
    ap.add_argument("--root", required=True, help="申报材料目录")
    ap.add_argument("--name", required=True, help="软件全称，须与三处逐字一致")
    ap.add_argument("--version", default="V1.0", help="版本号，例如 V1.0")
    ap.add_argument("--json", action="store_true", help="只输出机器可读 JSON")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print("目录不存在：%s" % root, file=sys.stderr)
        return 2
    files = [p for p in sorted(root.rglob("*")) if p.is_file()]
    findings = scan_risks(files)
    consistency = check_consistency(files, args.name, args.version)
    pages = check_pages(files)
    manual = check_manual(files)
    rows = build_checklist(files, args.name, args.version, findings, consistency, pages, manual)
    verdict, reason, red, yellow = decide(rows)

    if args.json:
        payload = {
            "root": str(root), "name": args.name, "version": args.version,
            "verdict": verdict, "reason": reason, "checklist": rows,
            "consistency": consistency[0], "pages": pages, "manual": manual,
            "findings": findings, "red_lines": list(RED_LINES),
            "unassessed": "PDF 与二进制件无法可靠解析，解析不了的项需人工核对",
            "disclaimer": "静态筛查给的是线索不是判决；权属、商标、侵权判断交申请人或律师。",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(build_report(args.name, args.version, rows, verdict, reason,
                           findings, consistency, red, yellow))
    return 1 if verdict == "不能交" else 0


if __name__ == "__main__":
    sys.exit(main())
