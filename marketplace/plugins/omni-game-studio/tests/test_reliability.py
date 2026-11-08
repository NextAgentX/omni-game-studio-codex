"""Regression tests for the release checks. Run with python -m unittest discover -s tests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import build_check
import pack_atlas


def run(script, *args, isolated=False):
    cmd = [sys.executable, "-X", "utf8"]
    if isolated:
        cmd.append("-S")
    return subprocess.run(cmd + [str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})


class ReleaseChecks(unittest.TestCase):
    def test_assets_release_rejects_bad_metadata_and_accepts_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sound.wav").write_bytes(b"fake audio for manifest validation")
            manifest = root / "manifest.json"
            entry = {"path": "sound.wav", "kind": "audio", "tier": "final",
                     "license": "test", "commercial_ok": "false", "placeholder": True}
            manifest.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
            result = run("validate_assets.py", "--root", root, "--manifest", manifest, "--final", "--strict-license")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("commercial_ok", result.stdout)
            self.assertIn("占位", result.stdout)
            entry.update(commercial_ok=True, placeholder=False)
            manifest.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
            result = run("validate_assets.py", "--root", root, "--manifest", manifest, "--final", "--strict-license")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = run("validate_assets.py", "--root", root, "--manifest", manifest, "--final", isolated=True)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            result = run("validate_assets.py", "--root", root, "--manifest", manifest, "--strict-license")
            self.assertEqual(result.returncode, 1)

    def test_invalid_manifest_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            for data in ([], {"entries": [{"path": [], "kind": []}]},
                         {"entries": [{"path": "x", "kind": []}]}):
                manifest.write_text(json.dumps(data), encoding="utf-8")
                result = run("validate_assets.py", "--manifest", manifest)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_sprite_cannot_bypass_image_checks_with_unknown_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sprite.bin").write_bytes(b"not an image")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"entries": [{"path": "sprite.bin", "kind": "sprite",
                                "tier": "final", "license": "test"}]}), encoding="utf-8")
            result = run("validate_assets.py", "--root", root, "--manifest", manifest, "--final")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_state_cannot_skip_or_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            init = ("init", "--root", tmp, "--engine", "godot")
            self.assertEqual(run("omni_state.py", *init).returncode, 0)
            state = Path(tmp) / ".omni" / "state.json"
            original = state.read_bytes()
            for args in (init, ("set", "--root", tmp, "--key", "stage", "--value", "done"),
                         ("advance", "--root", tmp, "--to", "done")):
                self.assertEqual(run("omni_state.py", *args).returncode, 1)
                self.assertEqual(state.read_bytes(), original)

    def test_build_verifies_files_and_nonempty_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "game.bin"
            output.touch()
            self.assertFalse(build_check.verify(output)[0])
            self.assertFalse(build_check.verify(root)[0])
            output.write_bytes(b"x")
            self.assertTrue(build_check.verify(output)[0])
            self.assertTrue(build_check.verify(root)[0])

    def test_atlas_rejects_overflow(self):
        class Img:
            def __init__(self, width, height):
                self.width, self.height = width, height
                self.size = (width, height)
        with self.assertRaises(ValueError):
            pack_atlas.pack([(Path("tall.png"), Img(2, 20))], 16, 1)
        with self.assertRaises(ValueError):
            pack_atlas.pack([(Path("a.png"), Img(8, 8)),
                             (Path("b.png"), Img(8, 8))], 16, 1)
        _, width, height = pack_atlas.pack([(Path("a.png"), Img(4, 4))], 16, 1)
        self.assertLessEqual(max(width, height), 16)


if __name__ == "__main__":
    unittest.main()
