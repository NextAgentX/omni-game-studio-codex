"""Structural self-tests for the skill files themselves.

The product of this plugin is prompts, so the prompts get linted.
Run with: python -m unittest discover -s tests -v
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_lint  # noqa: E402

GOOD = """---
name: demo
description: Do demo tasks end to end. Use when the user asks for a demo of the pipeline.
---

# Demo

Read `references/notes.md` and run `scripts/ok.py`.
"""


def make_plugin(tmp, name="demo", body=GOOD, extra_files=None):
    root = Path(tmp)
    skill = root / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    (skill / "references").mkdir(exist_ok=True)
    (skill / "references" / "notes.md").write_text("# notes\n", encoding="utf-8")
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts" / "ok.py").write_text("print('ok')\n", encoding="utf-8")
    for rel, text in (extra_files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def verdict(checks, code):
    return next(c["verdict"] for c in checks if c["code"] == code)


class SkillLintRules(unittest.TestCase):
    def test_good_skill_passes_every_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_plugin(tmp)
            checks = skill_lint.lint_skill(root / "skills" / "demo", root)
            self.assertEqual([c["code"] for c in checks],
                             ["FM1", "FM2", "FM3", "LNK1", "LNK2", "TXT1", "SZ1"])
            self.assertEqual([c["verdict"] for c in checks], ["PASS"] * 7, checks)

    def test_name_must_match_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD.replace("name: demo", "name: other")
            root = make_plugin(tmp, body=body)
            self.assertEqual(verdict(skill_lint.lint_skill(root / "skills" / "demo", root), "FM2"), "FAIL")

    def test_missing_frontmatter_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_plugin(tmp, body="# Demo\n\nno frontmatter\n")
            checks = skill_lint.lint_skill(root / "skills" / "demo", root)
            self.assertEqual(verdict(checks, "FM1"), "FAIL")
            self.assertEqual(verdict(checks, "FM2"), "NOT ASSESSED")

    def test_description_without_trigger_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD.replace(
                "description: Do demo tasks end to end. Use when the user asks for a demo of the pipeline.",
                "description: A pile of demo utilities for the demo pipeline and its helpers.")
            root = make_plugin(tmp, body=body)
            self.assertEqual(verdict(skill_lint.lint_skill(root / "skills" / "demo", root), "FM3"), "WARN")

    def test_broken_reference_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD + "\nAlso see `references/missing.md`.\n"
            root = make_plugin(tmp, body=body)
            checks = skill_lint.lint_skill(root / "skills" / "demo", root)
            self.assertEqual(verdict(checks, "LNK1"), "FAIL")

    def test_reference_into_sibling_skill_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_plugin(tmp, extra_files={"skills/other/references/shared.md": "# s\n"})
            body = GOOD + "\nSee `references/shared.md`.\n"
            (root / "skills" / "demo" / "SKILL.md").write_text(body, encoding="utf-8")
            checks = skill_lint.lint_skill(root / "skills" / "demo", root)
            self.assertEqual(verdict(checks, "LNK1"), "WARN")

    def test_quoted_todo_is_not_a_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD + "\nThe template's `[TODO]` must be filled before the gate passes.\n"
            root = make_plugin(tmp, body=body)
            self.assertEqual(verdict(skill_lint.lint_skill(root / "skills" / "demo", root), "TXT1"), "PASS")
            body = GOOD + "\n[TODO] write the rest\n"
            (root / "skills" / "demo" / "SKILL.md").write_text(body, encoding="utf-8")
            self.assertEqual(verdict(skill_lint.lint_skill(root / "skills" / "demo", root), "TXT1"), "FAIL")

    def test_broken_script_reference_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_plugin(tmp)
            (root / "scripts" / "ok.py").write_text("def broken(:\n", encoding="utf-8")
            checks = skill_lint.lint_skill(root / "skills" / "demo", root)
            self.assertEqual(verdict(checks, "LNK2"), "FAIL")

    def test_oversized_skill_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_plugin(tmp, body=GOOD + "\n" + "line\n" * 520)
            self.assertEqual(verdict(skill_lint.lint_skill(root / "skills" / "demo", root), "SZ1"), "FAIL")

    def test_shipped_skills_pass(self):
        """Shipped skills must stay structurally clean."""
        if not (ROOT / "skills").is_dir():
            self.skipTest("no skills directory")
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "skill_lint.py"),
                                 "--root", str(ROOT), "--json"],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        import json
        report = json.loads(result.stdout)
        bad = [(s["skill"], c) for s in report["skills"] for c in s["checks"] if c["verdict"] == "FAIL"]
        self.assertEqual(bad, [], f"skill lint failures: {bad}")


if __name__ == "__main__":
    unittest.main()
