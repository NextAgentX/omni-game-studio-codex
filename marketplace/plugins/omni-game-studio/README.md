# Omni Game Studio v3.5.0

面向 Cocos Creator、Unity、Godot 与 Unreal Engine 5 的游戏生产插件，包含设计、独立的 Unity/Godot/Unreal 工程技能、AI 图片、动效、音效、音乐、测试与发布技能。按用户任务选择流程；已有项目不必强制从头建档。Unreal 起步模板暂未提供，由 `unreal-engineer` 生成工程骨架。

另附一条可选的**软著申报能力线**，用于游戏做完后的确权与上架资质：见下文。

## 游戏制作流程

完整项目覆盖立项、预制作与垂直切片、迭代 Sprint、Alpha/Beta/Gold、发布和持续运营。七个文档阶段是制作流程中的工件门禁；里程碑必须由实际可玩构建、测试结果和负责人评审确认。新增路线图、Sprint 复盘和里程碑模板，供团队按规模裁剪。

## 软著申报能力线

游戏做完只是「能上线」，确权之后才是「能保护、能上架、能维权」。`copyright-filing` 技能按四段 SOP 编排：**Phase 0** 确认软件目录 / 全称与版本号 / 著作权人 → **Phase 0.5** 名称查重锁死（不可跳过，锁死后三处逐字一致）→ **Phase 1** 材料串行生成 → **Phase 2** 风险体检与小白指导双线并行 → **Phase 3** 汇编交付（能交了吗 / 交什么 / 怎么交 / 红线原文一条不省略）。按 W1–W7 工作流路由，也支持单角色直调。

配套 4 个技能：`software-name-checker`（13 项命名规则 + 六渠道核查 + 三档结论）、`copyright-material-kit`（60 页 × 每页 50 行源程序文档、说明书、申请表、材料清单）、`copyright-risk-audit`（12 项风险红黄绿分级 + 提交前自评表 + 红线）、`copyright-filing-guide`（单文件 HTML 小白指导报告 + FAQ）。

三个脚本均为零第三方依赖（只用标准库、不联网、不需要 API key）：

```bash
python scripts/copyright_name_check.py --name "星轨塔防游戏软件" --version V1.0 --industry 游戏 --json
python scripts/copyright_source_doc.py --root . --name "星轨塔防游戏软件" --version V1.0 --out copyright-out/源程序文档.txt
python scripts/copyright_audit.py --root copyright-out --name "星轨塔防游戏软件" --version V1.0
```

模板在 `templates/copyright/`：`material-templates.md`（说明书骨架 / 申请表字段 / 材料清单）、`pre-submit-checklist.md`（12 项自评表 + 红线清单）、`guide-report.html`（单文件内联 CSS 指导报告）、`faq.md`（常见问题）。

边界要如实说清：软著登记是**形式审查**，中国版权保护中心不比对名称是否已被他人登记，查名称不是为过审，而是避免「拿到证书后产品不能叫这个名字」，真正的墙在商标和应用商店。脚本只做静态检查，产物是分页文本与 HTML、需转 PDF 后提交，不替代六渠道人工核查与官方审查，不承诺过审、不替用户做法律判断。Codex 没有 WorkBuddy 的团队运行时工具，协作以流程契约表达而非工具调用。

## AI 素材

- **图片**：`game-art-production` 优先调用当前会话可用的图像生成或编辑工具，生成后检查规格并遵守项目图片备份规则。
- **OpenAI API 图片与 GIF**：`gen_ai_image.py` 用 `OPENAI_API_KEY` 直接请求 Images API；支持透明 PNG/WebP 和有资格时的 2–16 帧动画 GIF。脚本强制指定备份目录，先保存返回原图，再复制到游戏资源目录。
- **动画 / 特效**：`game-animation-production` 支持 AI GIF 和精灵表；`split_sprite_sheet.py` 将等网格精灵表切成 PNG 序列及通用 JSON，检查帧一致性后再导入引擎。
- **音效 / 音乐**：`game-audio-production` 优先调用现有生成工具；`gen_ai_audio.py` 可使用 ElevenLabs API 按提示词生成 MP3。密钥、服务权限和费用由账户决定，`--dry-run` 不联网。
- **程序音频**：`gen_sfx.py` / `gen_music.py` 可离线合成复古音色，属于程序合成。

图片、动画和音频的生成质量、循环效果与商用授权均需具体验收；插件不自动断言许可或把占位资源当成正式资源。

Codex 的图像生成技能默认使用内置 `image_gen` 工具，通过 GPT Image 生成或编辑图片，不用 API key；可用性由当前会话决定。[OpenAI 介绍 Codex 使用图像生成技能制作游戏素材](https://openai.com/index/introducing-the-codex-app/)。该工具的文件默认写入 `$CODEX_HOME/generated_images/`；项目素材需先复制原图到项目备份目录，再处理。直接 API 脚本仅在用户选择后调用，另需开发者 API key 和模型权限，可能计费。AI 声效与音乐使用已连接工具或 ElevenLabs API；Image API 的动画结果是 GIF，不是视频剪辑。

## 本地脚本

脚本位于 `scripts/`。图片工具需要 Pillow，音频压缩可选 ffmpeg；三个软著脚本只用标准库。详细用法参见各脚本的 `--help` 和对应技能；安装步骤见发行包的 `INSTALL.md`。

```bash
python scripts/gen_ai_audio.py sfx --prompt "soft sci-fi button click" --duration 1 --out assets/audio/click.mp3 --dry-run
python scripts/gen_ai_image.py --prompt "small blue potion icon, transparent background" --format png --background transparent --out assets/art/potion.png --backup-dir doc/temp --dry-run
python scripts/gen_ai_image.py --prompt "a cheerful robot waves" --format gif --frames 8 --out assets/animation/robot.gif --backup-dir doc/temp --dry-run
python scripts/split_sprite_sheet.py --input raw/run_sheet.png --cols 4 --rows 2 --fps 12 --loop --out-dir assets/animation/run --backup-dir doc/temp/run-frames
python scripts/validate_assets.py --manifest assets/manifest.json --final --strict-license
python -m unittest discover -s tests -v
```

仅当 AI 图片工具或用户选择的服务可用时才能生成图片；音频直接适配器需要 `ELEVENLABS_API_KEY`。阶段状态脚本检查文档，不会自动证明资源或构建通过。
