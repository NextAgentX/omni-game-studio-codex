"""Evidence capture, evidence freshness and session checkpoint tests.

Run with: python -m unittest discover -s tests -v
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import build_check  # noqa: E402
import omni_state  # noqa: E402


def run(script, *args):
    return subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})


class CaptureCommands(unittest.TestCase):
    def test_godot_capture_never_uses_headless(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd, notes, state = build_check.capture_command(
                "godot", Path(tmp), Path(tmp) / "ev", None, 60, None)
            self.assertEqual(state, "READY")
            joined = " ".join(cmd)
            self.assertIn("--write-movie", joined)
            self.assertIn("--windowed", joined)
            self.assertIn("--quit-after", joined)
            self.assertNotIn("--headless", joined, "headless 跳过渲染，截出来会是空白")

    def test_unity_without_command_is_not_assessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd, notes, state = build_check.capture_command(
                "unity", Path(tmp), Path(tmp) / "ev", None, 60, None)
            self.assertIsNone(cmd)
            self.assertEqual(state, "NOT_ASSESSED")
            self.assertTrue(any("ScreenCapture" in n for n in notes))

    def test_cocos_without_command_is_not_assessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, notes, state = build_check.capture_command(
                "cocos", Path(tmp), Path(tmp) / "ev", None, 60, None)
            self.assertEqual(state, "NOT_ASSESSED")
            self.assertTrue(any("浏览" in n or "playwright" in n for n in notes))


class CaptureRun(unittest.TestCase):
    def _helper(self, root: Path):
        helper = root / "shot.py"
        helper.write_text(
            "import struct, sys, zlib\nfrom pathlib import Path\n"
            "def chunk(kind, data):\n"
            "    crc = zlib.crc32(kind + data) & 0xffffffff\n"
            "    return (struct.pack('>I', len(data)) + kind + data\n"
            "            + struct.pack('>I', crc))\n"
            "ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)\n"
            "png = (b'\\x89PNG\\r\\n\\x1a\\n' + chunk(b'IHDR', ihdr)\n"
            "       + chunk(b'IDAT', zlib.compress(b'\\x00' * 5))\n"
            "       + chunk(b'IEND', b''))\n"
            "Path(sys.argv[1]).write_bytes(png)\n",
            encoding="utf-8")
        return helper

    def test_dry_run_creates_no_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            verdict, msgs = build_check.run_capture(
                root, "godot", "g2", capture_cmd=None, dry_run=True)
            self.assertEqual(verdict, "READY")
            self.assertFalse((root / build_check.EVIDENCE_ROOT).exists())
            self.assertTrue(any("未执行" in m for m in msgs))

    def test_capture_writes_screenshot_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = self._helper(root)
            shot = root / build_check.EVIDENCE_ROOT / "g2" / "shot.png"
            cmd = f'"{sys.executable}" "{helper}" "{shot}"'
            verdict, msgs = build_check.run_capture(root, "godot", "g2", capture_cmd=cmd)
            self.assertEqual(verdict, "CAPTURED", msgs)
            self.assertTrue(shot.exists())
            receipt = json.loads((shot.parent / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], 1)
            self.assertEqual(receipt["evidence_dir"], "docs/qa/evidence/g2")
            self.assertEqual(receipt["screenshot"]["path"], "shot.png")
            self.assertTrue(receipt["screenshot"]["sha256"])

    def test_capture_without_png_is_not_assessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = root / "noop.py"
            helper.write_text("print('ran, captured nothing')\n", encoding="utf-8")
            cmd = f'"{sys.executable}" "{helper}"'
            verdict, msgs = build_check.run_capture(root, "godot", "g2", capture_cmd=cmd)
            self.assertEqual(verdict, "NOT_ASSESSED", msgs)
            self.assertTrue(any("没有有效截图" in m for m in msgs), msgs)

    def test_capture_rejects_non_png_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = root / "bad_png.py"
            helper.write_text(
                "from pathlib import Path\n"
                "p = Path('docs/qa/evidence/g2/shot.png')\n"
                "p.parent.mkdir(parents=True, exist_ok=True)\n"
                "p.write_bytes(b'not a png')\n",
                encoding="utf-8")
            cmd = f'"{sys.executable}" "{helper}"'
            result = run("build_check.py", "--project", root, "--engine", "godot",
                         "--capture-only", "g2", "--capture-cmd", cmd)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("不是可解码的 PNG", result.stdout + result.stderr)
            receipt_path = root / build_check.EVIDENCE_ROOT / "g2" / "receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertIsNone(receipt["screenshot"], "伪 PNG 不能被登记为截图")

    def test_capture_name_cannot_escape_evidence_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = root / "escape.py"
            helper.write_text(
                "from pathlib import Path\n"
                "p = Path('docs/qa/escape/shot.png')\n"
                "p.parent.mkdir(parents=True, exist_ok=True)\n"
                "p.write_bytes(b'\x89PNG\r\n\x1a\nfake')\n",
                encoding="utf-8")
            cmd = f'"{sys.executable}" "{helper}"'
            result = run("build_check.py", "--project", root, "--engine", "godot",
                         "--capture-only", "../escape", "--capture-cmd", cmd)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("证据名", result.stdout + result.stderr)
            self.assertFalse((root / "docs" / "qa" / "escape").exists())


def _png(width=1, height=1):
    """Build a minimal, decodable PNG for evidence fixtures."""
    def chunk(kind, data):
        crc = zlib.crc32(kind + data) & 0xffffffff
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    row = b"\x00" + b"\x00\x00\x00\x00" * width
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(row * height))
            + chunk(b"IEND", b""))


class EvidenceFreshness(unittest.TestCase):
    def _bundle(self, root: Path, sources):
        d = root / omni_state.EVIDENCE_ROOT / "g2"
        d.mkdir(parents=True)
        shot = d / "shot.png"
        shot.write_bytes(_png(2, 3))
        (d / "receipt.json").write_text(json.dumps({
            "schema": 1, "at": "2026-11-08T19:00:00+08:00", "engine": "godot",
            "exit_code": 0,
            "screenshot": {"path": "shot.png", "sha256": omni_state.sha256_file(shot)},
            "sources": sources,
        }), encoding="utf-8")
        return d

    def test_no_evidence_fails_with_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok, msgs = omni_state.check_evidence(Path(tmp))
            self.assertFalse(ok)
            self.assertTrue(any("build_check.py" in m for m in msgs))

    def test_receipt_without_screenshot_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / omni_state.EVIDENCE_ROOT / "g2"
            d.mkdir(parents=True)
            (d / "receipt.json").write_text(json.dumps({"at": "x", "sources": []}), encoding="utf-8")
            ok, msgs = omni_state.check_evidence(root)
            self.assertFalse(ok)
            self.assertTrue(any("没有截图" in m or "没有任何截图" in m for m in msgs))

    def test_fresh_and_stale_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src" / "a.gd"
            src.parent.mkdir(parents=True)
            src.write_text("var a = 1\n", encoding="utf-8")
            digest = omni_state.sha256_file(src)
            self._bundle(root, [{"path": "src/a.gd", "sha256": digest, "bytes": src.stat().st_size}])

            ok, msgs = omni_state.check_evidence(root)
            self.assertTrue(ok, msgs)
            self.assertTrue(any("未过期" in m for m in msgs))

            src.write_text("var a = 2\n", encoding="utf-8")
            ok, msgs = omni_state.check_evidence(root)
            self.assertFalse(ok, msgs)
            self.assertTrue(any("过期" in m for m in msgs))

    def test_modified_screenshot_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._bundle(root, [])
            ok, msgs = omni_state.check_evidence(root)
            self.assertTrue(ok, msgs)
            (bundle / "shot.png").write_bytes(b"\x89PNG\r\n\x1a\ntampered")
            ok, msgs = omni_state.check_evidence(root)
            self.assertFalse(ok, msgs)
            self.assertTrue(any("截图已改动" in m for m in msgs), msgs)

    def test_invalid_receipt_screenshot_size_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._bundle(root, [])
            receipt_path = bundle / "receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["screenshot"]["size"] = [0, -1]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            ok, msgs = omni_state.check_evidence(root)
            self.assertFalse(ok, msgs)
            self.assertTrue(any("截图尺寸" in m for m in msgs), msgs)

    def test_receipt_cannot_whitelist_non_png_as_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._bundle(root, [])
            shot = bundle / "shot.png"
            shot.write_bytes(b"not a png")
            receipt_path = bundle / "receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["screenshot"]["sha256"] = omni_state.sha256_file(shot)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            ok, msgs = omni_state.check_evidence(root)
            self.assertFalse(ok, msgs)
            self.assertTrue(any("不是有效 PNG" in m for m in msgs), msgs)

    def test_receipt_size_must_match_actual_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._bundle(root, [])
            receipt_path = bundle / "receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["screenshot"]["size"] = [99, 99]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            ok, msgs = omni_state.check_evidence(root)
            self.assertFalse(ok, msgs)
            self.assertTrue(any("截图尺寸不符" in m for m in msgs), msgs)

    def test_receipt_screenshot_path_cannot_escape_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._bundle(root, [])
            outside = bundle.parent / "outside.png"
            outside.write_bytes(b"\x89PNG\r\n\x1a\noutside")
            receipt_path = bundle / "receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["screenshot"] = {
                "path": "../outside.png",
                "sha256": omni_state.sha256_file(outside),
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            ok, msgs = omni_state.check_evidence(root)
            self.assertFalse(ok, msgs)
            self.assertTrue(any("截图路径" in m for m in msgs), msgs)

    def test_evidence_cli_and_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run("omni_state.py", "init", "--root", root, "--engine", "godot").returncode, 0)
            self.assertEqual(run("omni_state.py", "evidence", "check", "--root", root).returncode, 1)
            # 无证据时 qa → release 必须被拦
            (root / "docs").mkdir()
            (root / "docs" / "05-qa.md").write_text(
                "# QA\n\n## 测试范围\n\n## 核心用例\n\n## 兼容矩阵\n\n## 性能基线\n\n## 回归\n\n## 准入结论\n",
                encoding="utf-8")
            state = json.loads((root / ".omni" / "state.json").read_text(encoding="utf-8"))
            state["stage"] = "qa"
            (root / ".omni" / "state.json").write_text(json.dumps(state), encoding="utf-8")
            blocked = run("omni_state.py", "advance", "--root", root, "--to", "release")
            self.assertEqual(blocked.returncode, 1, blocked.stdout)
            self.assertIn("证据", blocked.stdout)
            skipped = run("omni_state.py", "advance", "--root", root, "--to", "release", "--no-evidence")
            self.assertEqual(skipped.returncode, 0, skipped.stdout)


class Checkpoint(unittest.TestCase):
    def test_checkpoint_overwrites_block_and_keeps_narrative(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run("omni_state.py", "init", "--root", root, "--engine", "godot")
            self.assertEqual(run("omni_state.py", "checkpoint", "--root", root,
                                 "--task", "写 GDD", "--next", "派策划").returncode, 0)
            active = root / ".omni" / "active.md"
            text = active.read_text(encoding="utf-8")
            self.assertIn("<!-- CHECKPOINT -->", text)
            self.assertIn("写 GDD", text)

            run("omni_state.py", "checkpoint", "--root", root,
                "--task", "写技术方案", "--next", "派引擎", "--note", "完成 GDD 初稿")
            text = active.read_text(encoding="utf-8")
            self.assertEqual(text.count("<!-- CHECKPOINT -->"), 1, "检查点是覆盖写，不是追加")
            self.assertIn("写技术方案", text)
            self.assertNotIn("- 当前任务: 写 GDD", text)
            self.assertIn("完成 GDD 初稿", text)

            shown = run("omni_state.py", "checkpoint", "--root", root, "--show")
            self.assertEqual(shown.returncode, 0)
            self.assertIn("写技术方案", shown.stdout)

    def test_long_narrative_rotates_to_session_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".omni").mkdir()
            active = root / ".omni" / "active.md"
            active.write_text("## 记录\n" + "- 旧记录\n" * 260, encoding="utf-8")
            self.assertEqual(run("omni_state.py", "checkpoint", "--root", root,
                                 "--task", "T", "--next", "N").returncode, 0)
            logs = list((root / ".omni" / "session-logs").glob("*.md"))
            self.assertEqual(len(logs), 1)
            self.assertLess(len(active.read_text(encoding="utf-8").splitlines()), 60)
            self.assertIn("<!-- CHECKPOINT -->", active.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
