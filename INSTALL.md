# Omni Game Studio v3.6.0 安装与 AI 素材使用

本仓库支持通过 GitHub 插件市场在线安装和升级，也保留本地市场安装方式；包含 20 个技能（15 个游戏制作 + 5 个软著申报）、16 个脚本、14 份文档模板（10 份制作文档 + 4 份软著模板）、三个游戏引擎起步模板，以及 13 个可选角色配置。Unreal Engine 5 有独立技能与角色，但暂未提供起步模板，需由 `unreal-engineer` 生成工程骨架。插件不会自带 API 凭证或保证模型调用额度。

v3.6.0 新增的「软著申报能力线」是可选的独立分支：游戏做完要确权、上架要资质时，用 `copyright-filing` 技能走名称锁死 → 材料生成 → 风险体检 / 小白指导双线并行 → 汇编交付。相关角色（`copyright-filing-lead`、`copyright-material-smith`、`copyright-risk-auditor`、`copyright-guide-designer`）与游戏角色并列，均为可选安装。三个软著脚本只用 Python 标准库，不需要 API key、也不联网；产物是分页文本与 HTML，需按提示转 PDF 后再提交。软著登记是形式审查，脚本只做静态检查，不替代人工核查与官方审查。

制作流程模板新增 `07-production-roadmap.md`、`08-sprint-review.md` 和 `09-milestones.md`，用于路线图、可玩 Sprint 复盘及 G1–G5/运营评审记录。它们补充制作生命周期；文档检查本身不会替代真实构建、测试或签核。

## 在线安装（推荐）

无需克隆仓库或手动复制文件。Codex CLI 可直接从 GitHub 跟踪插件市场：

```bash
codex plugin marketplace add NextAgentX/omni-game-studio-codex --ref main
codex plugin add omni-game-studio@omni-game-studio-plugins
codex plugin list
```

Windows PowerShell 使用相同命令。安装后重新打开 Codex 会话，让新技能生效。

### 在线升级

发布新版本后，先刷新 GitHub 市场，再移除并重新安装插件以刷新本地缓存（当前 Codex CLI 没有单独的 `plugin update` 子命令）：

```bash
codex plugin marketplace upgrade omni-game-studio-plugins
codex plugin remove omni-game-studio@omni-game-studio-plugins
codex plugin add omni-game-studio@omni-game-studio-plugins
codex plugin list
```

重新安装会读取 GitHub 上最新的插件版本。若 Codex 正在运行，请重启 Codex 或新开会话。也可在 Codex 插件目录中刷新 `Omni Game Studio Plugins` 市场后安装最新版本。

### 从旧本地市场迁移

如果此前通过本地文件夹安装，先移除旧的插件注册和市场注册，再添加 GitHub 市场。该操作不会删除你的本地市场源文件：

```bash
codex plugin remove omni-game-studio@omni-game-studio-plugins
codex plugin marketplace remove omni-game-studio-plugins
codex plugin marketplace add NextAgentX/omni-game-studio-codex --ref main
codex plugin add omni-game-studio@omni-game-studio-plugins
```

若当前 Codex 环境尚不支持 Git 市场，可继续使用下方本地安装方式。`subagents/*.toml` 可选安装到 `~/.codex/agents/`；没有子代理时插件仍可工作。

## 本地安装（备用）

将 `marketplace/` 完整复制到本机本地市场目录，例如 `~/.codex/local-marketplaces/omni-game-studio-plugins/`（目标目录下应直接有 `.agents/` 和 `plugins/`），然后注册并安装：

```bash
codex plugin marketplace add ~/.codex/local-marketplaces/omni-game-studio-plugins
codex plugin add omni-game-studio@omni-game-studio-plugins
codex plugin list
```

## AI 图片和动效

Codex 会话内置的图像生成工具由宿主提供，可直接生成或编辑图像；工具是否可用取决于当前会话。插件还提供 OpenAI Images API 直接调用脚本，需单独设置 `OPENAI_API_KEY`；Codex 对话凭据不会自动充当 API 密钥。

```bash
# 根据实际插件缓存路径调整 PL
PL="$HOME/.codex/plugins/cache/omni-game-studio-plugins/omni-game-studio/3.6.0"
python "$PL/scripts/split_sprite_sheet.py" --input raw/run_sheet.png --cols 4 --rows 2 --frames 8 --fps 12 --loop --out-dir assets/animation/run --backup-dir doc/temp/run-frames
python "$PL/scripts/gen_ai_image.py" --prompt "small astronaut waves, 8-frame animation" --format gif --frames 8 --out assets/animation/wave.gif --backup-dir doc/temp
```

示例假定项目在仓库根目录有 `doc/temp/` 备份目录；新项目需先创建它。OpenAI Images API 脚本要求 `--backup-dir` 且会先写原始图片备份，再复制到运行目录。GIF 依赖模型预览权限，按[官方 Images API](https://developers.openai.com/api/reference/resources/images/methods/generate)的支持模型和画面限制选择帧数。切帧脚本只处理已有图片，不调用生成模型。动画还需检查一致性并导入引擎验证。

## AI 音效和音乐

优先使用会话中已有的音频生成工具，也可用插件的 ElevenLabs HTTP 适配器。接口可能产生费用，账户需开通相关权限；设置环境变量 `ELEVENLABS_API_KEY`，不要将密钥写入项目或聊天。脚本默认不会覆盖已有文件。

```bash
# 先预览，不联网、不计费、不需要密钥
PL="$HOME/.codex/plugins/cache/omni-game-studio-plugins/omni-game-studio/3.6.0"
python "$PL/scripts/gen_ai_audio.py" sfx --prompt "short bright pickup chime" --duration 1 --out assets/audio/pickup.mp3 --dry-run
# 去掉 --dry-run 后才实际请求生成
python "$PL/scripts/gen_ai_audio.py" music --prompt "gentle space exploration" --duration 30 --instrumental --out assets/audio/main.mp3
```

参见 [音效 API](https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert) 和 [音乐 API](https://elevenlabs.io/docs/api-reference/music/compose)。生成后须试听并确认实际授权；`gen_sfx.py` 和 `gen_music.py` 则是程序合成，不属于 AI 生成。

## 验证与边界

在插件目录可执行 `python -m unittest discover -s tests -v`。状态脚本只检查文档；资源终检、构建和设备验证需分别执行。生成工具、模型、服务费用和权限因环境而异，生成结果需要实际验收。
