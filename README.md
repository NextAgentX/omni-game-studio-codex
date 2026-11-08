# Omni Game Studio for Codex

**A practical game-development studio toolkit for Codex.** Plan, build, art-direct, produce assets, engineer, test, and ship games with workflows that adapt to your project and engine.

[English](README.md) | [简体中文](README.zh-CN.md)

[![GitHub stars](https://img.shields.io/github/stars/NextAgentX/omni-game-studio-codex?style=social)](https://github.com/NextAgentX/omni-game-studio-codex/stargazers) [![Issues](https://img.shields.io/github/issues/NextAgentX/omni-game-studio-codex)](https://github.com/NextAgentX/omni-game-studio-codex/issues) [![CI](https://github.com/NextAgentX/omni-game-studio-codex/actions/workflows/ci.yml/badge.svg)](https://github.com/NextAgentX/omni-game-studio-codex/actions/workflows/ci.yml)

Omni Game Studio gives Codex an engine-aware toolkit for game production. It brings together focused skills, optional specialist role prompts, starter projects, document templates, and production scripts for **Cocos Creator, Unity, and Godot**.

Use it for one focused task in an existing game or for a project that is still an idea. The workflow follows your chosen engine and project stage; it does not force an existing project through a from-scratch setup.

### Contents

- [Why this project](#why-this-project)
- [What is included](#what-is-included)
- [Production workflow](#production-workflow)
- [Getting started](#getting-started)
- [AI art, animation, and audio](#ai-art-animation-and-audio)
- [Templates, scripts, and checks](#templates-scripts-and-checks)
- [Repository checks](#repository-checks)
- [Limits and verification](#limits-and-verification)
- [Contributing](#contributing)
- [Support the project](#support-the-project)

### Why this project

Game work crosses design, engineering, art, audio, QA, and release. A general-purpose coding assistant can help with each area, but teams still need clear handoffs, engine-specific guidance, and a way to distinguish a written plan from a working build.

Omni Game Studio provides focused workflows for those jobs. It helps turn requirements into reviewable artifacts and real project changes while keeping the developer in control of scope, tools, and release decisions. For an existing project, start with its current engine and codebase instead of replacing them with a template.

### What is included

| Area | Included |
|---|---|
| Skills | 14 Codex skills for orchestration, design, engine engineering, assets, QA, release, and live operations |
| Optional role prompts | 8 specialist TOML profiles: Cocos, Unity, Godot, art, audio, narrative, QA, and release |
| Production scripts | 13 Python tools for AI media adapters, asset processing, manifests, builds, run evidence, audio, and pipeline state |
| Document templates | 10 project documents, including a production roadmap, Sprint review, and G1–G5 milestone record |
| Engine starters | Small starter projects for Godot 4, Unity, and Cocos Creator 3.x |

#### Skill map

| Focus | Skills |
|---|---|
| Orchestration and production pipeline | `omni-game-studio`, `game-production-pipeline` |
| Design | `game-narrative-design`, `game-art-direction`, `game-audio-design` |
| Engine engineering | `cocos-engineering`, `unity-engineering`, `godot-engineering` |
| Art, animation, and audio production | `game-art-production`, `game-animation-production`, `game-audio-production` |
| QA, platforms, and release | `game-qa-testing`, `multiplatform-release`, `game-release-liveops` |

The specialist profiles in `subagents/` are optional. Skills remain usable when those role profiles are not installed; Codex can do the work directly.

### Production workflow

The production pipeline follows project milestones, with evidence at each review:

1. **G1 — Concept and go/no-go:** define the player, core experience, scope, risks, and assumptions.
2. **G2 — Prototype and vertical slice:** validate the core loop and integrate a small playable slice in the target engine.
3. **Production Sprints:** plan a testable goal, integrate design/code/art/audio, review a playable build, and record feedback and follow-up work.
4. **G3 — Alpha:** reach feature completeness and track remaining blockers.
5. **G4 — Beta:** lock content, focus on fixes and verification, and explicitly review any proposed feature additions.
6. **G5 — Gold and release:** review the release candidate, platform checks, build evidence, and launch plan.
7. **Live operations:** feed player reports, stability, and product metrics into the next backlog and release cycle.

The seven document gates (`brief`, `gdd`, `tech`, `art`, `audio`, `qa`, and `release`) organize project artifacts; they are not substitutes for G1–G5 reviews. `omni_state.py` checks document structure and TODOs. It cannot verify a playable build, test results, device compatibility, or release approval.

### Getting started

#### Requirements

- Codex CLI with Git plugin-marketplace support.
- Python 3.9+ for the bundled scripts.
- Pillow for image processing, sprite-sheet splitting, atlas packing, and some asset checks.
- `OPENAI_API_KEY` or `ELEVENLABS_API_KEY` only when you choose the corresponding direct API adapter. Native tools available in a Codex session may have different setup requirements.

#### Install

Follow [INSTALL.md](INSTALL.md) to install `omni-game-studio` directly from the GitHub marketplace, upgrade it from the latest repository version, or use a local checkout. The guide includes Windows and Unix-like shell examples, migration from the local marketplace, optional specialist profiles, media-generation setup, and the distinction between session tools and API credentials.

#### Use it in a game project

1. Open the game project root in Codex so it can inspect the actual engine version, files, and build setup.
2. Describe the task and target platform. For an existing project, state the engine if it is not obvious.
3. For a full project flow, ask Codex to use `omni-game-studio` or `game-production-pipeline`. For a focused task, use the matching engine or design skill.
4. Review generated files and evidence. Run the project in its engine and validate target-platform builds before treating them as complete.

Example requests:

- “Review this Godot project and fix the input bug without changing its scene architecture.”
- “Plan a vertical slice for this Unity game and list the build evidence needed for G2.”
- “Create an art and audio production plan for the next playable Sprint.”

### AI art, animation, and audio

The plugin describes workflows for Codex-hosted tools and provides optional API adapters. Which native generators are available depends on the current Codex session and account.

| Asset | Workflow |
|---|---|
| Images | Use an available Codex image-generation/editing tool, or opt into `gen_ai_image.py` with an OpenAI API key. The script supports image formats and model-qualified GIF generation; check its help and current API model limits. |
| Animation | Use `game-animation-production` to generate or prepare GIFs and sprite sheets. `split_sprite_sheet.py` cuts a regular sprite sheet into frames and writes timing metadata. A GIF is not a video export. |
| Sound and music | Use an available audio-generation tool or opt into `gen_ai_audio.py` with an ElevenLabs API key. `gen_sfx.py` and `gen_music.py` make procedural audio offline; they are synthesis tools, not AI generation. |
| Integration | Process and validate assets against the engine, target platform, file-size budget, loops, and manifest. Confirm source, license, and commercial-use terms for each service and output. |

Example commands (run them from a game project and adjust paths to its asset layout):

```bash
# Generate an image; the original is backed up before the runtime copy is written.
python scripts/gen_ai_image.py --prompt "small blue potion icon, transparent background" --format png --background transparent --out assets/art/potion.png --backup-dir doc/temp

# Prepare an existing sprite sheet as animation frames.
python scripts/split_sprite_sheet.py --input raw/run_sheet.png --cols 4 --rows 2 --fps 12 --loop --out-dir assets/animation/run --backup-dir doc/temp/run-frames

# Preview the audio request without sending it to the service.
python scripts/gen_ai_audio.py sfx --prompt "short bright pickup chime" --duration 1 --out assets/audio/pickup.mp3 --dry-run
```

Direct API requests may require separate credentials, service permissions, and paid usage. Keep keys out of the repository. Review generated media before shipping it. Preserve original and intermediate images under the project’s configured backup directory (the bundled examples use `doc/temp/`).

### Templates, scripts, and checks

The `templates/docs/` directory contains the seven stage documents and three lifecycle templates: a production roadmap, Sprint review, and milestone review. Engine starters are intentionally small: the Godot 4 starter is runnable, the Unity starter needs its scene-generation step, and the Cocos starter needs a scene created in the editor.

The `scripts/` directory includes:

- `omni_state.py` for document-stage tracking and gates, screenshot-evidence checks, and the session checkpoint.
- `gen_ai_image.py`, `gen_ai_audio.py`, `gen_music.py`, and `gen_sfx.py` for image/audio workflows.
- `process_art.py`, `split_sprite_sheet.py`, `pack_atlas.py`, and `compress_audio.py` for asset preparation.
- `validate_assets.py` and `build_check.py` for asset and build checks; `--capture` runs the game and keeps a screenshot with a hash receipt.
- `gen_placeholder_art.py` for pipeline-only placeholders; placeholders are not final game art.
- `skill_lint.py` for structural self-tests of the skills themselves.

Run the script-specific `--help` for parameters. Some image tools require Pillow; audio compression can use ffmpeg. See [scripts/README.md](marketplace/plugins/omni-game-studio/scripts/README.md), [templates/README.md](marketplace/plugins/omni-game-studio/templates/README.md), and [OPTIMIZATION.md](OPTIMIZATION.md) for more detail.

### Repository checks

CI validates the repository itself, not your game. The same three commands run locally and on every push:

```bash
python tools/validate_repo.py                  # manifests, plugin manifest, links, script syntax
cd marketplace/plugins/omni-game-studio
python scripts/skill_lint.py                   # SKILL.md structure and reference resolution
python -m unittest discover -s tests -v        # script regression tests
```

`validate_repo.py` is dependency-free and checks what breaks marketplace installs: JSON manifests resolving to real plugin directories, `plugin.json` required fields and semver, view assets that exist, `SKILL.md` frontmatter names matching their directories, dangling `references/` paths, subagent TOML fields, and accidentally committed API keys. `skill_lint.py` scores each skill as `PASS` / `WARN` / `FAIL` / `NOT ASSESSED` instead of pretending an unassessed skill passed.

Tagging `vX.Y.Z` runs the release workflow: it re-runs all checks, refuses to publish when the tag disagrees with `plugin.json`, and attaches a `omni-game-studio-X.Y.Z.zip` plus `SHA256SUMS.txt` to the GitHub release.

### Limits and verification

- Codex executes work in the project context; this plugin is not a one-click game generator or a hosted game engine.
- A completed document or a passing script check does not prove the game is fun, playable, performant, or accepted by a platform.
- Run actual builds and tests, inspect generated media in-game, and verify target-device and platform behavior before release.
- AI model access, API features, pricing, and usage terms depend on the provider and account. Verify current terms before commercial use.
- The included 2D-oriented animation flow does not replace a full 3D modeling, rigging, or video-production pipeline.

### Contributing

Contributions are welcome across engine skills, documentation, production scripts, asset validation, and platform guidance.

1. Search [existing Issues](https://github.com/NextAgentX/omni-game-studio-codex/issues) or open one with the engine/version, target platform, expected behavior, and reproduction steps.
2. Fork the repository and keep each pull request focused. Explain the problem, the change, and any engine/platform compatibility impact.
3. Run `python tools/validate_repo.py` and the plugin test command above for script changes. For skill or documentation changes, run `python scripts/skill_lint.py` to catch broken references and frontmatter drift.
4. In your pull request, list the checks you actually ran and anything still unverified. For generated media, include its source and license information.

### Support the project

If Omni Game Studio saves you time, you can support its maintenance and future development:

#### Buy me a coffee

Scan with Alipay or WeChat Pay. Support is voluntary and appreciated.

<p align="center">
  <img src="donate-alipay.jpg" alt="Alipay support QR code" width="240" />
  &nbsp;&nbsp;&nbsp;
  <img src="donate-wechat.png" alt="WeChat Pay support QR code" width="240" />
</p>
<p align="center">Alipay　　　　　　　　　WeChat Pay</p>

#### Star and share

If this project is useful to you, please [star it on GitHub](https://github.com/NextAgentX/omni-game-studio-codex/stargazers) and share it with other game developers.

### Repository layout

```text
marketplace/   Codex plugin marketplace and Omni Game Studio plugin
subagents/     Optional specialist role profiles
tools/         Repository validation (used by CI and by hand)
.github/       CI workflows, release workflow, issue and pull request templates
requirements-ci.txt  Test-only dependencies (Pillow)
donate-alipay.jpg / donate-wechat.png  Project-support QR images
INSTALL.md     Installation and AI-asset guide
OPTIMIZATION.md  Version history
```
