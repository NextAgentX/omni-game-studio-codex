#!/usr/bin/env python3
"""build_check.py — 构建检查与验证

用法:
  python build_check.py --project .                       # 自动识别引擎，打印构建命令（不执行）
  python build_check.py --project . --preset Web --out build/web --run
  python build_check.py --project . --verify build/web    # 只校验已有产物

支持: Godot 4 / Unity / Cocos Creator 3.x
说明: 各引擎 CLI 参数随版本变化，执行前请核对官方文档；--run 失败会如实返回非零。
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

GODOT_BINS = ["godot", "godot4", "Godot"]
UNITY_HINTS = [
    r"C:\Program Files\Unity\Hub\Editor",
    "/Applications/Unity/Hub/Editor",
]
COCOS_HINTS = [
    r"C:\ProgramData\cocos\editors",
    "/Applications/Cocos/Creator",
]


def detect(project: Path):
    if (project / "project.godot").exists():
        return "godot"
    # Unity: 只认 ProjectSettings/ProjectVersion.txt。不要用 Assets 目录判断——
    # Windows 文件系统大小写不敏感，Cocos 的 assets/ 会被误判成 Unity 的 Assets/。
    if (project / "ProjectSettings" / "ProjectVersion.txt").exists():
        return "unity"
    pkg = project / "package.json"
    if (project / "assets").is_dir() and pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "creator" in data or str(data.get("name", "")).startswith("cocos"):
                return "cocos"
        except Exception:
            pass
    return None


def find_godot():
    for b in GODOT_BINS:
        p = shutil.which(b)
        if p:
            return p
    return None


def godot_presets(project: Path):
    cfg = project / "export_presets.cfg"
    if not cfg.exists():
        return []
    names = []
    for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith("name=") and '"' in s:
            names.append(s.split("=", 1)[1].strip().strip('"'))
    return names


def cmd_godot(project, preset, out):
    binary = find_godot() or "godot"
    presets = godot_presets(project)
    if not presets:
        return None, ["未找到 export_presets.cfg 或其中没有导出预设。",
                      "先在 Godot 编辑器 Project > Export 添加目标平台并保存预设。"]
    p = preset or presets[0]
    if p not in presets:
        return None, [f"预设 '{p}' 不存在。可用: {', '.join(presets)}"]
    target = out or f"build/{p}"
    return [binary, "--headless", "--export-release", p, str(target)], []


def cmd_unity(project, preset, out):
    return None, [
        "Unity 批处理构建必须依赖一个 Editor 构建脚本。",
        "把 templates/unity/Assets/Editor/BuildScript.cs 复制到项目 Assets/Editor/，然后：",
        '  Unity.exe -quit -batchmode -nographics -projectPath "<项目>" '
        "-executeMethod BuildScript.PerformBuild -logFile -",
        "首次使用前把 BuildScript.cs 里的 outputPath 与 buildTarget 改成你的目标。",
    ]


def cmd_cocos(project, preset, out):
    return None, [
        "Cocos Creator 构建需使用编辑器自带 CLI（路径随安装位置变化）：",
        '  CocosCreator.exe --project "<项目>" --build "platform=web-mobile;debug=false"',
        "平台取值示例: web-mobile / web-desktop / android / ios / wechatgame / bytedance-mini-game。",
        "小游戏构建后还需用对应开发者工具打开产出目录。",
        "建议先手动在编辑器里构建一次，确认配置无误后再脚本化。",
    ]


def verify(path: Path):
    if not path.exists():
        return False, [f"产物目录不存在: {path}"]
    if path.is_file():
        size = path.stat().st_size
        return (True, [f"产物文件: {path.name} ({size/1024:.1f} KB)"]) if size else (False, [f"产物文件为空: {path}"])
    files = [p for p in path.rglob("*") if p.is_file()]
    if not files:
        return False, [f"产物目录为空: {path}"]
    total = sum(p.stat().st_size for p in files)
    if total == 0:
        return False, [f"产物目录中的文件均为空: {path}"]
    biggest = max(files, key=lambda p: p.stat().st_size)
    return True, [
        f"产物 {len(files)} 个文件，合计 {total/1024/1024:.2f} MB",
        f"最大文件: {biggest.relative_to(path)} ({biggest.stat().st_size/1024:.1f} KB)",
    ]


def main():
    ap = argparse.ArgumentParser(description="构建检查与验证")
    ap.add_argument("--project", default=".")
    ap.add_argument("--engine", choices=["auto", "godot", "unity", "cocos"], default="auto")
    ap.add_argument("--preset")
    ap.add_argument("--out")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--verify", help="只校验已有产物目录")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"项目目录不存在: {project}", file=sys.stderr)
        return 1

    if args.verify:
        ok, msgs = verify((project / args.verify) if not Path(args.verify).is_absolute() else Path(args.verify))
        for m in msgs:
            print(("  OK  " if ok else "  FAIL ") + m)
        return 0 if ok else 1

    engine = args.engine if args.engine != "auto" else detect(project)
    if not engine:
        print("无法识别引擎。请显式指定 --engine godot|unity|cocos", file=sys.stderr)
        return 1
    print(f"引擎: {engine}   项目: {project}")

    if engine == "godot":
        cmd, notes = cmd_godot(project, args.preset, args.out)
    elif engine == "unity":
        cmd, notes = cmd_unity(project, args.preset, args.out)
    else:
        cmd, notes = cmd_cocos(project, args.preset, args.out)

    if notes:
        for n in notes:
            print("  · " + n)
    if cmd:
        print("\n构建命令:")
        print("  " + " ".join(cmd))

    if not args.run:
        if engine == "godot" and not cmd:
            return 1
        print("\n（未执行。加 --run 实际构建）")
        return 0

    if not cmd:
        print("\n没有可直接执行的命令，请按上面步骤手动构建。")
        return 1

    print("\n执行中…")
    try:
        proc = subprocess.run(cmd, cwd=str(project), timeout=1800)
    except FileNotFoundError:
        print(f"可执行文件未找到: {cmd[0]}（检查是否在 PATH）", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("构建超时（1800s）", file=sys.stderr)
        return 1
    if proc.returncode != 0:
        print(f"构建失败，退出码 {proc.returncode}", file=sys.stderr)
        return proc.returncode

    out_dir = Path(cmd[-1])
    ok, msgs = verify((project / out_dir) if not out_dir.is_absolute() else out_dir)
    for m in msgs:
        print(("  OK  " if ok else "  FAIL ") + m)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
