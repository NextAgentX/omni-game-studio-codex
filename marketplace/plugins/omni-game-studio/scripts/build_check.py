#!/usr/bin/env python3
"""build_check.py — 构建检查、产物校验与运行留证

用法:
  python build_check.py --project .                        # 自动识别引擎，打印构建命令（不执行）
  python build_check.py --project . --preset Web --out build/web --run
  python build_check.py --project . --verify build/web     # 只校验已有产物
  python build_check.py --project . --run --capture g2-slice   # 构建后启动并截图留证
  python build_check.py --project . --capture-only quick-look   # 不构建，只跑起来看一眼

支持: Godot 4 / Unity / Cocos Creator 3.x
说明:
  - 各引擎 CLI 参数随版本变化，执行前请核对官方文档；--run 失败会如实返回非零退出码。
  - 解析通过不等于跑起来；跑起来不等于看得对。--capture 是唯一产出"我看过"这一步的路径。
  - 截图证据落在 docs/qa/evidence/<名字>/，同时写 receipt.json 记录所覆盖文件的 sha256。
    之后任何一次改动都会让这份证据显示为过期，而不是"通过"。
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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

EVIDENCE_ROOT = "docs/qa/evidence"
DEFAULT_FRAMES = 90          # 让引擎真的渲染若干帧再截图，60 是下限
DEFAULT_RESOLUTION = "1280x720"
MAX_HASH_BYTES = 20 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def detect(project: Path):
    if (project / "project.godot").exists():
        return "godot"
    # Unreal: .uproject 是工程根的标志文件，优先判定，避免与其它引擎的特征目录混淆。
    if any(project.glob("*.uproject")):
        return "unreal"
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
    # 构建可以且应当 headless；截图阶段绝不能用（那是为了跳过渲染而存在的开关）。
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


def cmd_unreal(project, preset, out):
    return None, [
        "Unreal Engine 打包需调用 RunUAT BuildCookRun（路径随 UE 安装位置变化）：",
        '  RunUAT.bat BuildCookRun -project="<项目>/<Name>.uproject" '
        "-platform=<平台> -clientconfig=Development -build -cook -stage -pak -archive "
        "-archivedirectory=<输出目录>",
        "先用编辑器手动打包一次确认 Cook 与打包配置；失败只从日志第一条错误开始定位，忽略连锁报错。",
        "Android / iOS 的 SDK、NDK 与签名版本区间以 Epic 官方文档当前版本为准，不要写死数字。",
        "本脚本不代跑 UE 打包；手动产出后用 --verify 校验产物目录。",
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


# ---------------------------------------------------------------------------
# 运行留证
# ---------------------------------------------------------------------------

def sha256_file(path: Path):
    """返回 (hash, bytes)，跳过大文件（返回 None）。"""
    try:
        size = path.stat().st_size
        if size > MAX_HASH_BYTES:
            return None, size
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest(), size
    except OSError:
        return None, 0


def png_size(path: Path):
    """只读 PNG 文件头与 IHDR，返回 (宽, 高)；不是合法 PNG 则返回 None。"""
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


def image_size(path: Path):
    """优先用 Pillow 完整解码；Pillow 不存在时仍校验 PNG 头，不把伪 PNG 当截图。"""
    try:
        from PIL import Image
    except ImportError:
        return png_size(path)
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            return list(im.size)
    except Exception:
        return None


def evidence_dir_for(project: Path, name: str):
    """证据名只能是单段目录名，禁止路径分隔符和 . / .. 逃出证据根。"""
    if (not name or name in {".", ".."} or "/" in name or "\\" in name
            or Path(name).is_absolute()):
        return None
    base = (project / EVIDENCE_ROOT).resolve()
    target = (base / name).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    return target


def _under(path: Path, parent: Path) -> bool:
    """path 是否在 parent 之下（Py3.9 兼容写法）。"""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def git_changed_sources(project: Path, exclude_dirs):
    """本份证据覆盖哪些文件：git 里已修改/未跟踪的文件。git 不可用则返回空并说明。"""
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=str(project),
                             capture_output=True, text=True, errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return [], "git 不可用，证据未绑定任何源文件（无法判断新鲜度）"
    if out.returncode != 0:
        return [], "当前目录不是 git 仓库，证据未绑定任何源文件"

    sources = []
    for line in out.stdout.splitlines():
        raw = line[3:] if len(line) > 3 else ""
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        raw = raw.strip().strip('"')
        if not raw:
            continue
        p = (project / raw).resolve()
        if not p.exists() or not p.is_file():
            continue
        if ".git" in p.parts:
            continue
        if any(_under(p, Path(d).resolve()) for d in exclude_dirs if d):
            continue
        digest, size = sha256_file(p)
        sources.append({"path": raw.replace("\\", "/"), "sha256": digest, "bytes": size})
    return sources, ""


def capture_command(engine, project, evidence_dir, scene, frames, capture_cmd):
    """返回 (cmd, notes, verdict)。

    verdict:
      READY        有可直接执行的启动+截图命令
      NOT_ASSESSED 该引擎没有内置的无人值守截图能力，且用户没给命令
    """
    if capture_cmd:
        return capture_cmd, ["使用 --capture-cmd 提供的命令；约定它把截图写进证据目录。"], "READY"

    if engine == "godot":
        binary = find_godot() or "godot"
        movie = str((evidence_dir / "shot.png").resolve())
        cmd = [binary, "--path", str(project), "--windowed",
               "--resolution", DEFAULT_RESOLUTION]
        if scene:
            cmd.append(scene)
        # --write-movie 传 .png 时写的是图片序列（shot00000000.png 起）。
        # 绝不能用 --headless：它跳过渲染，截出来会是空白。
        cmd += ["--write-movie", movie, "--quit-after", str(frames)]
        return cmd, [], "READY"

    if engine == "unity":
        return None, [
            "Unity 没有可用的内置无人值守截图 CLI，需要一层引导脚本：",
            "  1. 在项目里加一个 Bootstrap MonoBehaviour，启动后等若干帧再调 "
            "ScreenCapture.CaptureScreenshot(<绝对路径>)，然后 Application.Quit()；",
            "  2. 构建播放器后运行：",
            "     <Player>.exe -screen-width 1280 -screen-height 720 -screen-fullscreen 0 "
            "-scene <Name> --capture-shot <证据目录>/shot.png",
            "  3. 或直接把上面这条命令用 --capture-cmd 传进来。",
            "不能用的开关：-batchmode、-nographics（它们会跳过渲染）。",
        ], "NOT_ASSESSED"

    if engine == "cocos":
        return None, [
            "Cocos Creator 没有内置的无人值守截图 CLI（预览跑在浏览器/模拟器里）。",
            "两条可行路径：",
            "  a. 构建 web-mobile，用无头浏览器截图：",
            '     npx playwright screenshot --viewport-size=1280,720 <预览地址> <证据目录>/shot.png',
            "  b. 小游戏用对应开发者工具的真机预览手动截图，再把文件放进证据目录。",
            "把命令用 --capture-cmd 传进来即可自动留证；否则本步记为 NOT ASSESSED。",
        ], "NOT_ASSESSED"

    if engine == "unreal":
        return None, [
            "Unreal Engine 没有插件内置可用的无人值守截图 CLI。",
            "两条可行路径：",
            '  a. 打包后用 -ExecCmds="HighResShot 1280x720" 或 -game 启动时注入控制台命令截图；',
            "  b. 在关卡蓝图/代码里等若干帧后调 FScreenshotRequest::RequestScreenshot 再退出。",
            "把命令用 --capture-cmd 传进来即可自动留证；否则本步记为 NOT ASSESSED。",
        ], "NOT_ASSESSED"

    return None, [f"未知引擎: {engine}"], "NOT_ASSESSED"


def pick_screenshot(evidence_dir: Path):
    """取证据目录里最新的一张 png，并把 Godot 的帧序列收敛成 shot.png。

    Godot 的 --write-movie 会顺带写出同名 .wav（录制的音频），那不是画面证据，删掉。
    """
    pngs = sorted(evidence_dir.glob("*.png"), key=lambda p: p.stat().st_mtime)
    if not pngs:
        return None
    for wav in evidence_dir.glob("*.wav"):
        try:
            wav.unlink()
        except OSError:
            pass
    frames = [p for p in pngs if p.name.startswith("shot") and p.name.endswith(".png")]
    newest = pngs[-1]
    if len(frames) > 1:
        target = evidence_dir / "shot.png"
        if newest != target:
            newest.replace(target)
        for f in frames:
            if f != target and f.exists():
                f.unlink()
        return target
    return newest


def fmt_size(size):
    """image_size 返回 (w, h)；统一成 宽x高 以便阅读。"""
    if not size or len(size) < 2:
        return ""
    return f"{size[0]}x{size[1]}"


def run_capture(project: Path, engine, name, scene=None, frames=DEFAULT_FRAMES,
                capture_cmd=None, dry_run=False):
    """跑起来、截图、写回执。返回 (verdict, messages)。"""
    evidence_dir = evidence_dir_for(project, name)
    if evidence_dir is None:
        return "INVALID", [
            "FAIL: 证据名必须是一段目录名，不能为空、包含 / 或 \\，也不能是 . 或 ..",
            f"当前值: {name!r}",
        ]
    cmd, notes, state = capture_command(engine, project, evidence_dir, scene, frames, capture_cmd)
    msgs = list(notes)

    if state != "READY":
        msgs.append("VERDICT: NOT ASSESSED —— 这一步没有产出任何证据，不能当作已看过的画面。")
        return "NOT_ASSESSED", msgs

    shown = cmd if isinstance(cmd, str) else " ".join(cmd)
    msgs.append("启动命令: " + shown)
    if dry_run:
        msgs.append("（未执行。去掉 --dry-run 才真正启动并截图）")
        return "READY", msgs

    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = now()
    try:
        proc = subprocess.run(cmd, cwd=str(project), shell=isinstance(cmd, str),
                              timeout=300, capture_output=True, text=True,
                              errors="replace")
        rc = proc.returncode
        tail = (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]
    except FileNotFoundError:
        msgs.append(f"FAIL: 可执行文件未找到: {cmd[0] if isinstance(cmd, list) else cmd}")
        msgs.append("VERDICT: NOT ASSESSED —— 没有启动起来，就没有画面可看。")
        return "NOT_ASSESSED", msgs
    except subprocess.TimeoutExpired:
        rc = -9
        tail = "启动超时（300s 未退出）"
        msgs.append("FAIL: " + tail)

    shot = pick_screenshot(evidence_dir)
    sources, src_note = git_changed_sources(project, [evidence_dir])
    if src_note:
        msgs.append(src_note)

    receipt = {
        "schema": 1,
        "at": started,
        "engine": engine,
        "evidence_dir": str(evidence_dir.relative_to(project)).replace("\\", "/"),
        "command": cmd if isinstance(cmd, str) else cmd,
        "exit_code": rc,
        "output_tail": tail.strip()[-1200:],
        "screenshot": None,
        "sources": sources,
    }

    dims = image_size(shot) if shot else None
    if shot and dims is None:
        msgs.append(f"FAIL: 捕获到的 {shot.name} 不是可解码的 PNG，不能作为画面证据。")
        shot = None

    if shot:
        digest, size = sha256_file(shot)
        receipt["screenshot"] = {
            "path": shot.name, "sha256": digest, "bytes": size,
            "size": dims,
        }
        msgs.append(f"截图: {EVIDENCE_ROOT}/{name}/{shot.name} "
                    f"({size/1024:.1f} KB {fmt_size(dims)})".replace(" )", ")"))
        msgs.append("尺寸以项目自己的窗口设置为准；--resolution 只是请求，游戏是竖屏就截竖屏。")
    else:
        msgs.append("FAIL: 证据目录里没有出现可解码的 PNG，画面未被捕获。")

    (evidence_dir / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    msgs.append(f"回执: {EVIDENCE_ROOT}/{name}/receipt.json（绑定 {len(sources)} 个改动文件）")

    if not shot:
        msgs.append("VERDICT: NOT ASSESSED —— 没有有效截图，就不算看过。")
        return "NOT_ASSESSED", msgs
    if rc != 0:
        msgs.append(f"注意: 进程退出码 {rc}，但已拿到画面。画面是否为预期仍需人/代理判读。")
    msgs.append("VERDICT: CAPTURED —— 现在去看这张图，再和验收标准逐条对。")
    return "CAPTURED", msgs


def main():
    ap = argparse.ArgumentParser(description="构建检查、产物校验与运行留证")
    ap.add_argument("--project", default=".")
    ap.add_argument("--engine", choices=["auto", "godot", "unity", "cocos", "unreal"], default="auto")
    ap.add_argument("--preset")
    ap.add_argument("--out")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--verify", help="只校验已有产物目录")
    ap.add_argument("--capture", metavar="NAME",
                    help="构建后启动引擎并截图留证，证据落在 docs/qa/evidence/NAME/")
    ap.add_argument("--capture-only", metavar="NAME", help="跳过构建，只启动并截图")
    ap.add_argument("--scene", help="启动直接进入的场景/地图，避免靠菜单点进去")
    ap.add_argument("--frames", type=int, default=DEFAULT_FRAMES,
                    help=f"截图前让引擎渲染的帧数（默认 {DEFAULT_FRAMES}）")
    ap.add_argument("--capture-cmd", help="自定义启动+截图命令（Unity/Cocos/Unreal 需要）")
    ap.add_argument("--dry-run", action="store_true", help="只打印命令，不执行")
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
        print("无法识别引擎。请显式指定 --engine godot|unity|cocos|unreal", file=sys.stderr)
        return 1
    print(f"引擎: {engine}   项目: {project}")

    if args.capture_only:
        verdict, msgs = run_capture(project, engine, args.capture_only, args.scene,
                                    args.frames, args.capture_cmd, args.dry_run)
        for m in msgs:
            print("  · " + m)
        return {"CAPTURED": 0, "READY": 0}.get(verdict, 2)

    if engine == "godot":
        cmd, notes = cmd_godot(project, args.preset, args.out)
    elif engine == "unity":
        cmd, notes = cmd_unity(project, args.preset, args.out)
    elif engine == "unreal":
        cmd, notes = cmd_unreal(project, args.preset, args.out)
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
        if args.capture:
            print("\n（--capture 需要配合 --run，或使用 --capture-only）")
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
    if not ok:
        return 1

    if args.capture:
        print("\n运行留证…")
        verdict, cmsgs = run_capture(project, engine, args.capture, args.scene,
                                     args.frames, args.capture_cmd, args.dry_run)
        for m in cmsgs:
            print("  · " + m)
        if verdict == "NOT_ASSESSED":
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
