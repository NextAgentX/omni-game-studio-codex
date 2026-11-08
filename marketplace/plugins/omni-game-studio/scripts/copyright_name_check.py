#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""软件名称合规静态预检 —— 软著申报 Phase 0.5 前置锁死环节。

离线跑 13 项命名规则 + 独创性启发式评分，给「可以直用 / 建议微调 /
必须改名」三档结论；需改时给 3-5 个备选名并推荐其中一个。

重要声明：静态预检不替代商标、应用商店、软著登记公告的人工核查。
六个渠道（软著登记公告 / 商标第 9 与 42 类 / 应用商店 / 备案 /
企业 / 官网）必须由人工用官方数据库逐一复核并截图留档。
脚本连不上登记库和商标库，两者都要登录加图形验证码。

示例::

    python copyright_name_check.py --name "星轨塔防游戏软件" --version V1.0 --industry 游戏 --owner "某某工作室" --app-store 计划上架
    python copyright_name_check.py --name "智能巡检管理系统" --version V1.0 --json
    python copyright_name_check.py --help

退出码：0 = 可以直用或建议微调，1 = 必须改名，2 = 参数错误。
"""

import argparse
import json
import re
import sys

CATEGORY_WORDS = (
    "系统", "平台", "软件", "游戏", "引擎", "工具", "框架", "组件", "小程序",
    "应用", "程序", "插件", "编辑器", "模拟器", "管理器", "助手", "中台",
    "客户端", "服务端", "数据库", "工具箱", "套件", "SDK", "APP",
)
SENSITIVE_WORDS = (
    "中国", "国家", "中华", "全国", "国际", "世界", "政府", "官方", "军用",
    "中央", "国务院", "国家级",
)
ABSOLUTE_WORDS = (
    "第一", "唯一", "最好", "最强", "最全", "顶级", "首创", "极品", "极致",
    "无敌", "最高级", "第一品牌",
)
BRAND_WORDS = (
    "腾讯", "网易", "米哈游", "原神", "王者荣耀", "和平精英", "微信", "支付宝",
    "阿里", "百度", "华为", "苹果", "微软", "谷歌", "任天堂", "索尼",
    "Steam", "Unity", "Unreal", "Cocos", "Godot", "Adobe",
    "Minecraft", "我的世界", "堡垒之夜", "塞尔达", "宝可梦", "磐石",
)
OSS_NAMES = (
    "Linux", "Android", "Kubernetes", "Docker", "Redis", "MySQL",
    "PostgreSQL", "TensorFlow", "PyTorch", "Vue", "React", "Angular",
    "Django", "Spring", "Blender", "Nginx",
)
RESIDUAL_WORDS = (
    "demo", "test", "temp", "tmp", "sample", "example", "untitled", "backup",
    "final", "draft", "新建", "副本", "示例", "测试", "占位", "草稿", "未命名",
)
GENERIC_WORDS = (
    "智能", "智慧", "云", "大数据", "数据", "管理", "信息", "综合", "通用",
    "新一代", "数字化", "一体化", "可视化", "在线", "网络", "企业",
)
PLACE_PERSON_WORDS = (
    "北京", "上海", "天津", "重庆", "深圳", "广州", "杭州", "成都", "南京",
    "武汉", "西安", "浙江", "广东", "江苏", "山东", "四川", "中国",
)
NAME_POOL = ("星轨", "折光", "拾光", "青岚", "栖梧", "远岚", "墨屿", "云枢", "砺行")

CATEGORY_RE = re.compile("|".join(re.escape(w) for w in CATEGORY_WORDS), re.I)
VERSION_RE = re.compile(r"^[Vv]?\d+(?:\.\d+){0,2}(?:[-.]?(?:alpha|beta|rc|release)\d*)?$", re.I)
VERSION_IN_NAME_RE = re.compile(r"[Vv]?\d+\.\d+(?:\.\d+)?")
ALLOWED_CHAR_RE = re.compile("^[一-龥A-Za-z0-9 .·\\-]+$")

CHANNELS = (
    "软著登记公告", "商标第 9 与 42 类", "应用商店", "备案", "企业", "官网与产品",
)


def _hits(text, words):
    low = text.lower()
    return sorted({w for w in words if w.lower() in low}, key=len, reverse=True)


def _core(name):
    return CATEGORY_RE.sub("", name).strip()


def _chinese_ratio(text):
    if not text:
        return 0.0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fa5")
    return cjk / len(text)


def _overlap(core, industry):
    if not industry or not core:
        return 0.0
    a, b = set(core), set(industry)
    return len(a & b) / max(1, len(a | b))


def run_checks(name, version, industry):
    checks = []

    def add(code, title, status, detail):
        checks.append({"id": code, "rule": title, "status": status, "detail": detail})

    n = len(name)
    add("N01", "全称长度", "PASS" if 4 <= n <= 30 else "WARN",
        "%d 字，要求 4-30 字" % n)

    cats = CATEGORY_RE.findall(name)
    add("N02", "品类词完整性", "PASS" if cats else "WARN",
        "命中品类词 " + "、".join(cats) if cats else "未命中品类词，建议补系统 / 平台 / 软件 / 游戏")

    hit = _hits(name, SENSITIVE_WORDS)
    add("N03", "敏感禁用字样", "FAIL" if hit else "PASS",
        "命中 " + "、".join(hit) + "，形审会补正或驳回" if hit else "未命中")

    hit = _hits(name, ABSOLUTE_WORDS)
    add("N04", "绝对化用语", "FAIL" if hit else "PASS",
        "命中 " + "、".join(hit) if hit else "未命中")

    hit = _hits(name, BRAND_WORDS)
    add("N05", "他人品牌词", "FAIL" if hit else "PASS",
        "命中 " + "、".join(hit) if hit else "未命中")

    hit = _hits(name, OSS_NAMES)
    add("N06", "开源项目名", "FAIL" if hit else "PASS",
        "命中 " + "、".join(hit) if hit else "未命中")

    hit = _hits(name, RESIDUAL_WORDS)
    add("N07", "开发残留词", "FAIL" if hit else "PASS",
        "命中 " + "、".join(hit) if hit else "未命中")

    generic = _hits(name, GENERIC_WORDS)
    core = _core(name)
    weak = bool(generic) and len(core) <= 4
    add("N08", "纯通用词堆叠", "WARN" if weak else "PASS",
        "通用词 " + "、".join(generic) + "，独创词偏短" if weak else "有足够独创成分")

    hit = _hits(name, PLACE_PERSON_WORDS)
    add("N09", "地名与人名", "WARN" if hit else "PASS",
        "命中 " + "、".join(hit) + "，易被误认地域官方项目" if hit else "未命中")

    ratio = _chinese_ratio(name)
    add("N10", "中文字符占比", "PASS" if ratio >= 0.30 else "WARN",
        "%.2f，要求不低于 0.30" % ratio)

    chars_ok = bool(ALLOWED_CHAR_RE.match(name))
    add("N11", "特殊字符规范", "PASS" if chars_ok else "FAIL",
        "字符合规" if chars_ok else "含 emoji、全角符号、引号或控制字符")

    vok = bool(VERSION_RE.match(version or ""))
    mixed = bool(VERSION_IN_NAME_RE.search(name))
    add("N12", "版本号格式", "PASS" if vok and not mixed else "WARN",
        "版本 %s，格式%s，%s" % (version, "规范" if vok else "不规范",
                              "版本串混进全称" if mixed else "全称未混版本串"))

    overlap = _overlap(core, industry)
    add("N13", "与行业通用名重合度", "PASS" if overlap < 0.60 else "WARN",
        "%.2f（独创词与行业词 %s 的字符重合度）" % (overlap, industry or "未指定"))

    return checks


def originality_score(name, industry):
    core = _core(name)
    score = 50
    score += 15 if len(core) >= 3 else (8 if len(core) >= 2 else 0)
    if not _hits(core, GENERIC_WORDS):
        score += 12
    if not _hits(name, BRAND_WORDS):
        score += 8
    if _hits(name, RESIDUAL_WORDS):
        score -= 30
    if _hits(name, BRAND_WORDS) or _hits(name, OSS_NAMES):
        score -= 20
    if _hits(name, GENERIC_WORDS) and len(core) <= 4:
        score -= 15
    if _overlap(core, industry) >= 0.60:
        score -= 15
    return max(0, min(100, score))


def conclude(checks, score):
    fails = [c["id"] for c in checks if c["status"] == "FAIL"]
    warns = [c["id"] for c in checks if c["status"] == "WARN"]
    if fails:
        return "必须改名", "命中禁用规则：" + "、".join(fails)
    if warns or score < 50:
        why = "存在可优化项：" + "、".join(warns) if warns else "无"
        if score < 50:
            why += "；独创性偏弱"
        return "建议微调", why
    return "可以直用", "13 项规则全通过且独创性达标（仍需人工复核六个渠道）"


def suggest(name, industry, count=5):
    cats = CATEGORY_RE.findall(name)
    suffix = cats[-1] if cats else "软件"
    topic = (industry or "").strip() or "智能"
    body = topic if topic not in suffix else ""
    picks = []
    for p in NAME_POOL:
        cand = p + body + suffix
        if cand not in picks:
            picks.append(cand)
        if len(picks) >= count:
            break
    return picks


def build_report(args, checks, score, verdict, reason):
    name, version = args.name, args.version
    lines = []
    lines.append("【名称查重·静态预检】%s %s" % (name, version))
    lines.append("结论：%s" % verdict)
    lines.append("理由：%s" % reason)
    lines.append("")
    lines.append("一、名称拆解")
    cats = CATEGORY_RE.findall(name)
    lines.append("  全称：%s" % name)
    lines.append("  版本号：%s" % version)
    lines.append("  品类词：%s" % ("、".join(cats) if cats else "无"))
    lines.append("  独创词：%s" % (_core(name) or "无"))
    lines.append("  著作权人：%s" % (args.owner or "未提供"))
    lines.append("  行业词：%s" % (args.industry or "未提供"))
    lines.append("")
    lines.append("二、13 项命名规则")
    icon = {"PASS": "通过", "WARN": "不通过（建议微调）", "FAIL": "不通过（必须改名）"}
    for c in checks:
        lines.append("  %s %s %s — %s" % (icon[c["status"]], c["id"], c["rule"], c["detail"]))
    lines.append("")
    lines.append("三、独创性启发式评分：%d 分（%s）" % (
        score, "强" if score >= 75 else ("中" if score >= 50 else "弱")))
    lines.append("  高分只代表结构好看，绝对不代表能注册；磐石类词在第 9 类早有多家注册。")
    lines.append("")
    lines.append("四、六个渠道人工复核清单（脚本不查，逐条做并截图留档）")
    for i, ch in enumerate(CHANNELS, 1):
        lines.append("  %d. %s" % (i, ch))
    if args.app_store:
        lines.append("  已声明：%s → 应用商店这一栏须重点复核，小程序名称唯一性校验更严" % args.app_store)
    lines.append("")
    lines.append("五、备选名")
    if verdict == "可以直用":
        lines.append("  无需给备选名。")
    else:
        picks = suggest(name, args.industry)
        for i, cand in enumerate(picks, 1):
            lines.append("  %d. %s%s" % (i, cand, "  ← 推荐" if i == 1 else ""))
        lines.append("  推荐理由：%s 为常见字组合，好读好传播，与业务贴合。" % picks[0])
        lines.append("  注意：备选名仅结构合规、还没查过商标，选定一个后回来重跑六个渠道。")
    lines.append("")
    lines.append("六、核查边界")
    lines.append("  静态预检不替代商标、应用商店、软著登记公告的人工核查；")
    lines.append("  中国版权保护中心登记库与商标库需登录加验证码，网页检索只是初筛。")
    lines.append("  正式提交前到 sbj.cnipa.gov.cn 与 ccopyright.com.cn 复核，截图留档。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="软件名称静态预检：13 项规则 + 独创性评分 + 三档结论。静态预检不替代六个渠道人工核查。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="声明：静态预检不替代商标、应用商店、软著登记公告的人工核查；六个渠道需人工复核并截图留档。",
    )
    ap.add_argument("--name", required=True, help="软件全称（不含版本号），例如 星轨塔防游戏软件")
    ap.add_argument("--version", default="V1.0", help="版本号，例如 V1.0")
    ap.add_argument("--industry", default="", help="行业词，用于行业通用名重合度判定，例如 游戏 / 巡检")
    ap.add_argument("--owner", default="", help="著作权人名称，写入报告便于核对字号")
    ap.add_argument("--app-store", default="", help="是否计划上架应用商店或小程序；非空时提示该渠道须重点复核")
    ap.add_argument("--json", action="store_true", help="只输出机器可读 JSON")
    args = ap.parse_args()

    args.name = (args.name or "").strip()
    if not args.name:
        ap.error("--name 不能为空")

    checks = run_checks(args.name, args.version, args.industry)
    score = originality_score(args.name, args.industry)
    verdict, reason = conclude(checks, score)

    if args.json:
        payload = {
            "name": args.name, "version": args.version, "industry": args.industry,
            "owner": args.owner, "app_store": args.app_store,
            "category_words": CATEGORY_RE.findall(args.name),
            "core": _core(args.name), "originality_score": score,
            "checks": checks, "verdict": verdict, "reason": reason,
            "alternatives": [] if verdict == "可以直用" else suggest(args.name, args.industry),
            "manual_channels": list(CHANNELS),
            "disclaimer": "静态预检不替代商标、应用商店、软著登记公告的人工核查，六个渠道需人工复核。",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(build_report(args, checks, score, verdict, reason))
    return 1 if verdict == "必须改名" else 0


if __name__ == "__main__":
    sys.exit(main())
