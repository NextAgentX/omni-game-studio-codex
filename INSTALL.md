# Omni Game Studio v3.4.3 安装与 AI 素材使用

本包包含本地市场、14 个技能、12 个脚本、10 份制作文档模板、游戏引擎模板，以及 8 个可选角色配置。插件不会自带 API 凭证或保证模型调用额度。

制作流程模板新增 `07-production-roadmap.md`、`08-sprint-review.md` 和 `09-milestones.md`，用于路线图、可玩 Sprint 复盘及 G1–G5/运营评审记录。它们补充制作生命周期；文档检查本身不会替代真实构建、测试或签核。

## 安装插件

将 `marketplace/` 完整复制到本机本地市场目录，例如 `~/.codex/local-marketplaces/omni-game-studio-plugins/`（目标目录下应直接有 `.agents/` 和 `plugins/`）。按当前 Codex 版本注册该市场并安装：

```bash
codex plugin marketplace add ~/.codex/local-marketplaces/omni-game-studio-plugins
codex plugin add omni-game-studio@omni-game-studio-plugins
codex plugin list
python -m pip install pillow
```

如果已注册同名市场，更新其源目录后按本机插件管理方式升级或重新安装，然后新开会话确认版本。`subagents/*.toml` 可选安装到 `~/.codex/agents/`；没有子代理时插件仍可工作。Windows 用户按本机终端语法调整路径。

## AI 图片和动效

Codex 会话内置的图像生成工具由宿主提供，可直接生成或编辑图像；工具是否可用取决于当前会话。插件还提供 OpenAI Images API 直接调用脚本，需单独设置 `OPENAI_API_KEY`；Codex 对话凭据不会自动充当 API 密钥。

```bash
# 根据实际插件缓存路径调整 PL
PL="$HOME/.codex/plugins/cache/omni-game-studio-plugins/omni-game-studio/3.4.3"
python "$PL/scripts/split_sprite_sheet.py" --input raw/run_sheet.png --cols 4 --rows 2 --frames 8 --fps 12 --loop --out-dir assets/animation/run --backup-dir doc/temp/run-frames
python "$PL/scripts/gen_ai_image.py" --prompt "small astronaut waves, 8-frame animation" --format gif --frames 8 --out assets/animation/wave.gif --backup-dir doc/temp
```

示例假定项目在仓库根目录有 `doc/temp/` 备份目录；新项目需先创建它。OpenAI Images API 脚本要求 `--backup-dir` 且会先写原始图片备份，再复制到运行目录。GIF 依赖模型预览权限，按[官方 Images API](https://developers.openai.com/api/reference/resources/images/methods/generate)的支持模型和画面限制选择帧数。切帧脚本只处理已有图片，不调用生成模型。动画还需检查一致性并导入引擎验证。

## AI 音效和音乐

优先使用会话中已有的音频生成工具，也可用插件的 ElevenLabs HTTP 适配器。接口可能产生费用，账户需开通相关权限；设置环境变量 `ELEVENLABS_API_KEY`，不要将密钥写入项目或聊天。脚本默认不会覆盖已有文件。

```bash
# 先预览，不联网、不计费、不需要密钥
PL="$HOME/.codex/plugins/cache/omni-game-studio-plugins/omni-game-studio/3.4.3"
python "$PL/scripts/gen_ai_audio.py" sfx --prompt "short bright pickup chime" --duration 1 --out assets/audio/pickup.mp3 --dry-run
# 去掉 --dry-run 后才实际请求生成
python "$PL/scripts/gen_ai_audio.py" music --prompt "gentle space exploration" --duration 30 --instrumental --out assets/audio/main.mp3
```

参见 [音效 API](https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert) 和 [音乐 API](https://elevenlabs.io/docs/api-reference/music/compose)。生成后须试听并确认实际授权；`gen_sfx.py` 和 `gen_music.py` 则是程序合成，不属于 AI 生成。

## 验证与边界

在插件目录可执行 `python -m unittest discover -s tests -v`。状态脚本只检查文档；资源终检、构建和设备验证需分别执行。生成工具、模型、服务费用和权限因环境而异，生成结果需要实际验收。
