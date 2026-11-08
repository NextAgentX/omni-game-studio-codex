#!/usr/bin/env python3
"""Static validation for the Omni Game Studio marketplace repository.

Dependency-free (stdlib only) so CI and contributors can run the same gate:
    python tools/validate_repo.py

Exit codes: 0 = pass (warnings allowed), 1 = validation errors found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    tomllib = None

PLUGIN_DIR = Path("marketplace/plugins/omni-game-studio")
MANIFEST_ROOTS = (
    Path(".agents/plugins/marketplace.json"),
    Path("marketplace/.agents/plugins/marketplace.json"),
)
REQUIRED_ROOT_FILES = (
    "README.md",
    "README.zh-CN.md",
    "INSTALL.md",
    "OPTIMIZATION.md",
)
REQUIRED_PLUGIN_KEYS = ("name", "version", "description", "author", "license", "skills")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}
HARDCODED_KEY = re.compile(r"(sk-[A-Za-z0-9_\-]{20,}|AIza[0-9A-Za-z_\-]{30,})")
REF_TOKEN = re.compile(
    r"^(?:(?:references|scripts|templates)/[\w./-]+\.(?:md|py|json|tscn|gd|ts|cs)|\w+/SKILL\.md)$"
)


class Reporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checked = 0

    def ok(self, msg: str) -> None:
        self.checked += 1
        print(f"ok   {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"warn {msg}")

    def fail(self, msg: str) -> None:
        self.errors.append(msg)
        print(f"FAIL {msg}")

    def section(self, title: str) -> None:
        print(f"\n## {title}")


def load_json(path: Path, rep: Reporter) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        rep.fail(f"{path}: missing")
        return None
    except json.JSONDecodeError as exc:
        rep.fail(f"{path}: invalid JSON ({exc})")
        return None
    if not isinstance(data, dict):
        rep.fail(f"{path}: expected a JSON object")
        return None
    return data


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Parse the small YAML subset used by SKILL.md (flat key: value pairs)."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    data: dict[str, str] = {}
    key = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) and key:
            data[key] += " " + raw.strip()
            continue
        if ":" not in raw:
            return None
        key, _, value = raw.partition(":")
        key = key.strip()
        data[key] = value.strip().strip("'\"")
    return data


def check_root(root: Path, rep: Reporter) -> None:
    rep.section("repository root")
    for name in REQUIRED_ROOT_FILES:
        if (root / name).is_file():
            rep.ok(name)
        else:
            rep.fail(f"{name}: missing")
    if (root / PLUGIN_DIR).is_dir():
        rep.ok(f"{PLUGIN_DIR.as_posix()} present")
    else:
        rep.fail(f"{PLUGIN_DIR.as_posix()}: missing")
    if not (root / "tools" / "validate_repo.py").is_file():
        rep.warn("tools/validate_repo.py not found (running from a copy?)")


def check_manifests(root: Path, rep: Reporter) -> None:
    rep.section("marketplace manifests")
    docs = []
    for rel in MANIFEST_ROOTS:
        doc = load_json(root / rel, rep)
        if doc is None:
            continue
        docs.append((rel, doc))
        if not str(doc.get("name", "")).strip():
            rep.fail(f"{rel}: missing marketplace name")
        plugins = doc.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            rep.fail(f"{rel}: 'plugins' must be a non-empty list")
            continue
        for entry in plugins:
            source = (entry or {}).get("source") or {}
            if source.get("source") != "local":
                rep.warn(f"{rel}: plugin source is not 'local' ({source.get('source')!r})")
            target = None
            raw_path = str(source.get("path", ""))
            # Codex resolves source paths against the directory holding .agents/,
            # but accept the manifest directory and repo root too.
            base_dirs = (rel.parent, rel.parent.parent, rel.parent.parent.parent, root)
            target = None
            for base in base_dirs:
                candidate = (root / base / raw_path).resolve()
                if candidate.is_dir():
                    target = candidate
                    break
            if target is None:
                rep.fail(f"{rel}: source path {raw_path!r} does not resolve")
            else:
                rep.ok(f"{rel}: plugin path resolves")
            if not str(entry.get("name", "")).strip():
                rep.fail(f"{rel}: plugin entry missing name")
    if len(docs) == 2:
        (n1, d1), (n2, d2) = docs
        if d1.get("name") != d2.get("name"):
            rep.fail(f"{n1} and {n2} declare different marketplace names")
        else:
            rep.ok("root and nested marketplaces agree on marketplace name")
        names1 = {p.get("name") for p in d1.get("plugins", [])}
        names2 = {p.get("name") for p in d2.get("plugins", [])}
        if names1 != names2:
            rep.fail(f"plugin name mismatch between manifests: {names1} vs {names2}")
        else:
            rep.ok("root and nested marketplaces list the same plugins")


def check_plugin(plugin: Path, rep: Reporter) -> str | None:
    rep.section("plugin manifest")
    manifest = load_json(plugin / ".codex-plugin" / "plugin.json", rep)
    if manifest is None:
        return None
    for key in REQUIRED_PLUGIN_KEYS:
        if key not in manifest:
            rep.fail(f"plugin.json: missing key {key!r}")
    version = str(manifest.get("version", ""))
    if SEMVER.match(version):
        rep.ok(f"plugin.json version {version}")
    else:
        rep.fail(f"plugin.json: version {version!r} is not semver (MAJOR.MINOR.PATCH)")
    if manifest.get("name") != plugin.name:
        rep.fail(f"plugin.json name {manifest.get('name')!r} != directory {plugin.name!r}")
    else:
        rep.ok("plugin name matches directory")
    if not isinstance(manifest.get("author"), dict) or not manifest["author"].get("name"):
        rep.fail("plugin.json: author.name is required")
    interface = manifest.get("interface") or {}
    for key in ("displayName", "shortDescription"):
        if not str(interface.get(key, "")).strip():
            rep.fail(f"plugin.json: interface.{key} is required")
    prompts = interface.get("defaultPrompt") or []
    if not isinstance(prompts, list) or not all(isinstance(p, str) and p.strip() for p in prompts):
        rep.fail("plugin.json: interface.defaultPrompt must be a list of strings")
    for asset_key in ("composerIcon", "logo"):
        asset = interface.get(asset_key)
        if asset and not (plugin / asset).is_file():
            rep.fail(f"plugin.json: interface.{asset_key} -> {asset} not found")
        elif asset:
            rep.ok(f"interface.{asset_key} exists")
    skills_ref = str(manifest.get("skills", "./skills/"))
    if not (plugin / skills_ref).is_dir():
        rep.fail(f"plugin.json: skills path {skills_ref!r} not found")
    return version


def check_skills(plugin: Path, root: Path, rep: Reporter) -> None:
    rep.section("skills")
    skills_dir = plugin / "skills"
    dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []
    if not dirs:
        rep.fail("skills/: no skill directories found")
        return
    rep.ok(f"{len(dirs)} skill directories")
    seen: dict[str, Path] = {}
    for skill_dir in dirs:
        rel = skill_dir.relative_to(root).as_posix()
        doc = skill_dir / "SKILL.md"
        if not doc.is_file():
            rep.fail(f"{rel}: missing SKILL.md")
            continue
        text = doc.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if meta is None:
            rep.fail(f"{rel}/SKILL.md: missing or malformed YAML frontmatter")
            continue
        name = meta.get("name", "")
        if not name:
            rep.fail(f"{rel}/SKILL.md: frontmatter missing 'name'")
        elif name != skill_dir.name:
            rep.fail(f"{rel}/SKILL.md: name {name!r} != directory {skill_dir.name!r}")
        elif not KEBAB.match(name):
            rep.fail(f"{rel}/SKILL.md: name {name!r} is not lower-kebab-case")
        else:
            seen[name] = doc
        desc = meta.get("description", "")
        if len(desc) < 40:
            rep.fail(f"{rel}/SKILL.md: description too short ({len(desc)} chars, need >= 40)")
        elif len(desc) > 1024:
            rep.fail(f"{rel}/SKILL.md: description too long ({len(desc)} chars, max 1024)")
        body = text.split("---", 2)[-1].strip()
        if len(body) < 200:
            rep.warn(f"{rel}/SKILL.md: body is only {len(body)} chars")
        # Stale local references: skills legitimately point at sibling skills,
        # so resolve against every skill dir plus the plugin and repo roots.
        bases = (skill_dir, plugin, root, *dirs)
        for token in set(re.findall(r"`([^`\s]+)`", body)):
            if not REF_TOKEN.match(token):
                continue
            if token.startswith(f"{skill_dir.name}/"):
                token = token.split("/", 1)[1]
            if not any((base / token).exists() for base in bases):
                rep.fail(f"{rel}/SKILL.md: dangling reference `{token}`")
        rep.ok(f"{skill_dir.name}")
    if len(seen) != len(dirs):
        rep.fail("some skills failed basic validation")


def check_subagents(root: Path, rep: Reporter) -> None:
    rep.section("subagents")
    agent_dir = root / "subagents"
    files = sorted(agent_dir.glob("*.toml")) if agent_dir.is_dir() else []
    if not files:
        rep.warn("subagents/: no .toml profiles found")
        return
    if tomllib is None:
        rep.warn(f"subagents/: tomllib unavailable, parsed {len(files)} files as text only")
        return
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report parser message verbatim
            rep.fail(f"{rel}: invalid TOML ({exc})")
            continue
        if data.get("name") != path.stem:
            rep.fail(f"{rel}: name {data.get('name')!r} != file name {path.stem!r}")
        for key in ("description", "developer_instructions"):
            if not str(data.get(key, "")).strip():
                rep.fail(f"{rel}: missing {key!r}")
        mode = data.get("sandbox_mode")
        if mode is not None and mode not in SANDBOX_MODES:
            rep.fail(f"{rel}: sandbox_mode {mode!r} not in {sorted(SANDBOX_MODES)}")
        if not str(data.get("description", "")).strip():
            pass
        rep.ok(path.stem)


def check_scripts(plugin: Path, root: Path, rep: Reporter) -> None:
    rep.section("scripts")
    scripts_dir = plugin / "scripts"
    files = sorted(scripts_dir.glob("*.py")) if scripts_dir.is_dir() else []
    if not files:
        rep.fail("scripts/: no Python scripts found")
        return
    for path in files:
        rel = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:
            rep.fail(f"{rel}: SyntaxError line {exc.lineno}: {exc.msg}")
            continue
        if HARDCODED_KEY.search(source):
            rep.fail(f"{rel}: looks like a hardcoded API key")
        rep.ok(path.name)
    if not (scripts_dir / "README.md").is_file():
        rep.warn("scripts/README.md missing")


def check_tests(plugin: Path, root: Path, rep: Reporter) -> None:
    rep.section("tests")
    tests_dir = plugin / "tests"
    files = sorted(tests_dir.glob("test_*.py")) if tests_dir.is_dir() else []
    if not files:
        rep.fail("tests/: no test_*.py files found")
        return
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if "unittest" not in text and "pytest" not in text:
            rep.warn(f"{rel}: no unittest/pytest import detected")
        try:
            compile(text, str(path), "exec")
        except SyntaxError as exc:
            rep.fail(f"{rel}: SyntaxError line {exc.lineno}: {exc.msg}")
            continue
        rep.ok(path.name)


def check_version_docs(root: Path, version: str | None, rep: Reporter) -> None:
    rep.section("version consistency")
    if not version:
        return
    docs = {
        "INSTALL.md": (root / "INSTALL.md"),
        "OPTIMIZATION.md": (root / "OPTIMIZATION.md"),
    }
    found = False
    for label, path in docs.items():
        if path.is_file() and version in path.read_text(encoding="utf-8"):
            rep.ok(f"{label} mentions v{version}")
            found = True
    if not found:
        rep.warn(f"no doc mentions the current version {version}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    rep = Reporter()

    print(f"validating {root}")
    check_root(root, rep)
    check_manifests(root, rep)
    plugin = root / PLUGIN_DIR
    version = check_plugin(plugin, rep) if plugin.is_dir() else None
    if plugin.is_dir():
        check_skills(plugin, root, rep)
        check_scripts(plugin, root, rep)
        check_tests(plugin, root, rep)
    check_subagents(root, rep)
    check_version_docs(root, version, rep)

    print(f"\n{rep.checked} checks passed, {len(rep.warnings)} warnings, {len(rep.errors)} errors")
    for err in rep.errors:
        print(f"  ERROR {err}")
    for warn in rep.warnings:
        print(f"  WARN  {warn}")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
