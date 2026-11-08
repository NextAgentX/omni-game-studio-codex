# Omni Game Studio for Codex

**A practical game-development studio toolkit for Codex.** Plan, build, art-direct, produce assets, engineer, test, and ship games with workflows that adapt to your project and engine.

[English](#english) | [简体中文](#简体中文)

[![GitHub stars](https://img.shields.io/github/stars/NextAgentX/omni-game-studio-codex?style=social)](https://github.com/NextAgentX/omni-game-studio-codex/stargazers) [![Issues](https://img.shields.io/github/issues/NextAgentX/omni-game-studio-codex)](https://github.com/NextAgentX/omni-game-studio-codex/issues)

## English

Omni Game Studio gives Codex an engine-aware toolkit for game production. It brings together focused skills, optional specialist role prompts, starter projects, document templates, and production scripts for **Cocos Creator, Unity, and Godot**.

Use it for one focused task in an existing game or for a project that is still an idea. The workflow follows your chosen engine and project stage; it does not force an existing project through a from-scratch setup.

### Contents

- [Why this project](#why-this-project)
- [What is included](#what-is-included)
- [Production workflow](#production-workflow)
- [Getting started](#getting-started)
- [AI art, animation, and audio](#ai-art-animation-and-audio)
- [Templates, scripts, and checks](#templates-scripts-and-checks)
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
| Production scripts | 12 Python tools for AI media adapters, asset processing, manifests, builds, audio, and pipeline state |
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

- Codex with local plugin-marketplace support.
- Python 3.9+ for the bundled scripts.
- Pillow for image processing, sprite-sheet splitting, atlas packing, and some asset checks.
- `OPENAI_API_KEY` or `ELEVENLABS_API_KEY` only when you choose the corresponding direct API adapter. Native tools available in a Codex session may have different setup requirements.

#### Install

Clone the repository, then follow [INSTALL.md](INSTALL.md) to register the `marketplace/` directory and install `omni-game-studio` from the `agentx-plugins` marketplace. The guide includes Windows and Unix-like shell examples, optional specialist profiles, media-generation setup, and the distinction between session tools and API credentials.

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

- `omni_state.py` for document-stage tracking and gates.
- `gen_ai_image.py`, `gen_ai_audio.py`, `gen_music.py`, and `gen_sfx.py` for image/audio workflows.
- `process_art.py`, `split_sprite_sheet.py`, `pack_atlas.py`, and `compress_audio.py` for asset preparation.
- `validate_assets.py` and `build_check.py` for asset and build checks.
- `gen_placeholder_art.py` for pipeline-only placeholders; placeholders are not final game art.

Run the script-specific `--help` for parameters. For plugin development, the current regression command is:

```bash
python -m unittest discover -s marketplace/plugins/omni-game-studio/tests -v
```

Some image tools require Pillow; audio compression can use ffmpeg. See [scripts/README.md](marketplace/plugins/omni-game-studio/scripts/README.md), [templates/README.md](marketplace/plugins/omni-game-studio/templates/README.md), and [OPTIMIZATION.md](OPTIMIZATION.md) for more detail.

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
3. Run the plugin test command above for script changes. For skill or documentation changes, check linked paths, stage definitions, and engine ownership.
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
donate-alipay.jpg / donate-wechat.png  Project-support QR images
INSTALL.md     Installation and AI-asset guide
OPTIMIZATION.md  Version history
```

---

## 简体中文

**Omni Game Studio 是面向 Codex 的实用型游戏制作工具集。** 它把策划、工程、美术、音频、测试、发行等专业工作整理成可调用的技能、可选角色提示词、工程模板、文档模板和制作脚本，支持 **Cocos Creator、Unity 与 Godot**。

你可以让它处理现有游戏中的单项任务，也可以从一个想法开始推进完整制作流程。它会沿用项目当前引擎和阶段，不会要求已有项目从零建档。

### 项目目标

游戏制作跨越策划、程序、美术、音频、QA 和发行。通用编程助手可以处理其中许多工作，但团队仍需要清楚的交接方式、引擎专属建议，以及区分“计划写完”和“游戏实际可运行”的验证流程。

Omni Game Studio 为 Codex 提供这些分工明确的工作流，帮助把需求落实成可评审文档和真实项目改动，同时由开发者决定范围、工具和发行方案。对于已有项目，先从当前引擎和代码库出发，不强制替换成模板。

### 包含内容

- **14 个技能：** 覆盖编排、设计、引擎工程、资源制作、QA、发行和运营。
- **8 个可选角色：** Cocos、Unity、Godot、美术、音频、叙事、QA 和发行。
- **12 个 Python 脚本：** 处理 AI 媒体适配、资源制作、manifest、构建、音频和流程状态。
- **10 份文档模板：** 包含制作路线图、Sprint 复盘及 G1–G5 里程碑评审。
- **3 个引擎模板：** Godot 4、Unity、Cocos Creator 3.x 小型起步工程。

#### 技能分组

| 范围 | 技能 |
|---|---|
| 总编排与制作流水线 | `omni-game-studio`、`game-production-pipeline` |
| 设计 | `game-narrative-design`、`game-art-direction`、`game-audio-design` |
| 引擎工程 | `cocos-engineering`、`unity-engineering`、`godot-engineering` |
| 美术、动效与音频制作 | `game-art-production`、`game-animation-production`、`game-audio-production` |
| QA、平台与发行 | `game-qa-testing`、`multiplatform-release`、`game-release-liveops` |

### 制作流程

制作流水线围绕项目里程碑推进，每个门禁都应有对应证据：

1. **G1——立项与 Go/No-Go：** 明确目标玩家、核心体验、范围、风险和待验证假设。
2. **G2——原型与垂直切片：** 在目标引擎中验证核心循环，并集成一个范围小但可玩的切片。
3. **Production Sprint：** 设定可验收目标，集成策划、程序、美术和音频产出；评审可玩构建、测试、反馈和后续工作。
4. **G3——Alpha：** 功能完整，跟踪剩余问题和阻塞项。
5. **G4——Beta：** 内容锁定，集中修复和验证；增加功能时要明确记录影响并重新评审。
6. **G5——Gold 与发行：** 评审发行候选版本、平台检查、构建证据和发布方案。
7. **上线后运营：** 将玩家反馈、稳定性和业务指标回写到下一版本 backlog。

七个文档阶段（`brief`、`gdd`、`tech`、`art`、`audio`、`qa`、`release`）管理制作工件，不能代替 G1–G5 评审。`omni_state.py` 只检查文档结构和 TODO，不会验证真实可玩构建、测试结果、设备兼容性或发行审批。

### 快速开始

#### 环境要求

- 支持本地插件市场的 Codex。
- Python 3.9+，用于运行插件脚本。
- Pillow：图片处理、精灵表切帧、图集打包和部分资源检查需要。
- 只有选择直接 API 适配器时才需要 `OPENAI_API_KEY` 或 `ELEVENLABS_API_KEY`。Codex 会话原生工具的配置要求可能不同。

#### 安装

先克隆仓库，再按 [INSTALL.md](INSTALL.md) 注册 `marketplace/` 并从 `agentx-plugins` 市场安装 `omni-game-studio`。安装指南包含 Windows 和类 Unix 命令、可选专业角色、媒体生成配置，以及会话工具与 API 凭证的区别。

#### 在游戏项目中使用

1. 在 Codex 中打开游戏项目根目录，让它检查真实引擎版本、文件和构建方式。
2. 说明要解决的问题和目标平台；如果是已有项目且引擎不明显，主动注明引擎。
3. 从创意推进完整流程时使用 `omni-game-studio` 或 `game-production-pipeline`；处理单项任务时选择对应引擎或设计技能。
4. 审阅生成的文件和证据。在游戏引擎中实际运行并验证目标平台构建，再判断工作是否完成。

示例请求：

- “检查这个 Godot 项目并修复输入问题，不要改变场景架构。”
- “为这个 Unity 游戏规划垂直切片，并列出通过 G2 评审需要的构建证据。”
- “为下一个可玩 Sprint 制定美术和音频制作计划。”

### AI 美术、动效与音频

插件同时说明 Codex 宿主工具的使用方式，并提供可选 API 适配器。当前会话中是否有原生生成工具，取决于 Codex 环境和账户。

| 资源类型 | 工作流 |
|---|---|
| 图片 | 使用当前可用的 Codex 图像生成/编辑工具，或配置 OpenAI API 后运行 `gen_ai_image.py`。脚本支持图片格式以及特定模型有权限时的 GIF 生成；请查看脚本帮助和当前模型限制。 |
| 动效 | 使用 `game-animation-production` 生成或整理 GIF 和精灵表。`split_sprite_sheet.py` 可以把规则网格图集切成帧并写入时间信息。GIF 不能代替视频导出。 |
| 音效与音乐 | 使用可用的音频生成工具，或配置 ElevenLabs API 后运行 `gen_ai_audio.py`。`gen_sfx.py` 与 `gen_music.py` 可离线程序合成，它们不是 AI 生成。 |
| 资源集成 | 按引擎、平台、包体预算、循环效果和 manifest 处理并检查资源。发布前确认每项服务和生成结果的来源、授权与商用条款。 |

示例命令（在游戏项目目录执行，并按项目资源结构调整路径）：

```bash
# 生成图片：写入运行目录前先备份原始图。
python scripts/gen_ai_image.py --prompt "small blue potion icon, transparent background" --format png --background transparent --out assets/art/potion.png --backup-dir doc/temp

# 把已有精灵表切成动效帧。
python scripts/split_sprite_sheet.py --input raw/run_sheet.png --cols 4 --rows 2 --fps 12 --loop --out-dir assets/animation/run --backup-dir doc/temp/run-frames

# 预览音效请求；该模式不会把请求发送到服务。
python scripts/gen_ai_audio.py sfx --prompt "short bright pickup chime" --duration 1 --out assets/audio/pickup.mp3 --dry-run
```

实际 API 请求可能需要独立密钥、服务权限并产生费用。不要把密钥提交到仓库。生成结果需人工检查后再用于发布。请将原图和中间图保存在项目备份目录中（示例使用 `doc/temp/`）。

### 模板、脚本与检查

`templates/docs/` 包含七个阶段文档和三个生命周期模板：制作路线图、Sprint 复盘、里程碑评审。三个引擎模板都刻意保持小而清晰：Godot 4 模板可运行，Unity 模板需执行场景生成步骤，Cocos 模板需在编辑器中创建场景。

`scripts/` 包含：

- `omni_state.py`：阶段文档状态和门禁。
- `gen_ai_image.py`、`gen_ai_audio.py`、`gen_music.py`、`gen_sfx.py`：AI 图片/音频适配及程序音频生成。
- `process_art.py`、`split_sprite_sheet.py`、`pack_atlas.py`、`compress_audio.py`：资源处理。
- `validate_assets.py`、`build_check.py`：资源和构建检查。
- `gen_placeholder_art.py`：只用于验证资源流程的占位图，不是正式美术。

运行各脚本的 `--help` 查看参数。插件开发目前使用以下回归命令：

```bash
python -m unittest discover -s marketplace/plugins/omni-game-studio/tests -v
```

部分图片工具需要 Pillow，音频压缩可选使用 ffmpeg。更多细节见[脚本说明](marketplace/plugins/omni-game-studio/scripts/README.md)、[模板说明](marketplace/plugins/omni-game-studio/templates/README.md)和[版本记录](OPTIMIZATION.md)。

### 能力边界与验证

- Codex 会在项目上下文中执行工作；本插件不是一键游戏生成器，也不是托管游戏引擎。
- 文档完成或脚本检查通过，不证明游戏好玩、可运行、性能达标或通过平台审核。
- 发布前实际运行构建和测试，在游戏中检查生成资源，并验证目标设备与平台行为。
- AI 模型权限、API 功能、价格和使用条款取决于服务商与账户；商用前请核对当前条款。
- 当前动效流程侧重 2D，不能替代完整的 3D 建模、绑定或视频制作流水线。

### 参与贡献

欢迎贡献引擎技能、文档、制作脚本、资源校验和平台适配内容。

1. 先搜索[现有 Issues](https://github.com/NextAgentX/omni-game-studio-codex/issues)，或提交新问题并说明引擎/版本、目标平台、预期行为和复现步骤。
2. Fork 仓库并让每个 Pull Request 聚焦一个主题，写清问题、改动和引擎/平台兼容影响。
3. 脚本改动运行上述插件测试命令；技能和文档改动检查链接路径、阶段定义和引擎职责。
4. Pull Request 中列出实际执行过的检查和仍未验证的部分。若提交 AI 生成资源，请注明来源与授权信息。

### 支持项目

如果 Omni Game Studio 帮你节省了时间，欢迎支持项目维护和后续开发：

#### 请我喝杯咖啡

使用支付宝或微信扫码，自愿支持项目。每一份支持都非常感谢。

<p align="center">
  <img src="donate-alipay.jpg" alt="支付宝支持二维码" width="240" />
  &nbsp;&nbsp;&nbsp;
  <img src="donate-wechat.png" alt="微信支付支持二维码" width="240" />
</p>
<p align="center">支付宝　　　　　　　　微信支付</p>

#### 点亮 Star 并分享

如果你觉得项目有用，欢迎在 GitHub [点亮 Star](https://github.com/NextAgentX/omni-game-studio-codex/stargazers)，也可以分享给其他游戏开发者。

### 仓库结构

```text
marketplace/   Codex 插件市场和 Omni Game Studio 插件
subagents/     可选的专业角色配置
donate-alipay.jpg / donate-wechat.png  项目支持二维码
INSTALL.md     安装和 AI 资源指南
OPTIMIZATION.md 版本更新记录
```
