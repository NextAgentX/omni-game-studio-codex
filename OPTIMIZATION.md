# 未发布：证据闭环、会话检查点与技能自测

- `build_check.py` 新增 `--capture` / `--capture-only`：构建后无人值守启动引擎并截图，证据落在 `docs/qa/evidence/<名字>/`，同目录 `receipt.json` 记录所覆盖改动文件的 sha256。Godot 用 `--write-movie --quit-after` 原生支持；Unity 与 Cocos 无内置无人值守截图，返回 `NOT ASSESSED` 并给可用命令，不假装成功。
- `omni_state.py` 新增 `evidence list|check`：按 sha256 判断证据是否仍代表当前代码，被覆盖文件改过即判定过期；`advance` 离开 `qa` 阶段时默认校验证据，`--no-evidence` 可显式跳过。
- `omni_state.py` 新增 `checkpoint` 与会话检查点 `.omni/active.md`：`STATUS` 供工具读、`CHECKPOINT` 覆盖写、叙述区追加，超过 200 行自动归档到 `.omni/session-logs/`。两个编排技能在开工前先读它。
- 编排与流水线技能新增两条铁律：产物优先于叙述（声称写了文件就校验路径存在，缺失即阶段失败）、qa 之后必须有截图（`NOT ASSESSED` 不是通过）。
- 新增 `scripts/skill_lint.py` 与 `tests/test_skill_lint.py`：7 条结构检查、四值判分，发版前跑一次；首跑即查出两个技能缺触发条件、两处跨技能引用会扑空，均已修。
- 新增 `templates/active.md`；QA 文档模板增加「截图证据」小节。

# 未发布：CI 门禁与仓库自检

- 新增 GitHub Actions CI（`.github/workflows/ci.yml`）：仓库清单校验、技能结构检查、Python 3.9 / 3.12 / 3.13 三版本回归测试，另设 `CI gate` 汇总状态，供分支保护只勾一个检查项。
- 新增 `tools/validate_repo.py`（零第三方依赖）：校验市场清单能解析到真实插件目录、`plugin.json` 必填字段与 semver、界面图资源存在性、`SKILL.md` frontmatter 与目录一致、`references/` 死链、子代理 TOML 字段、脚本语法及误提交的 API 密钥。
- 新增 `v*.*.*` 标签触发的发布流程（`.github/workflows/release.yml`）：先重跑全部检查，标签与 `plugin.json` 版本不一致即失败；通过后产出 `omni-game-studio-<版本>.zip` 与 `SHA256SUMS.txt` 并附到 Release。
- 新增 `requirements-ci.txt`（仅测试依赖 Pillow）、Dependabot 配置、Issue 表单（Bug / 功能请求）与 PR 模板。
- 双语 README 补充 CI 徽章、仓库自检命令与目录说明。
- 边界：CI 只验证仓库结构、引用完整性与脚本回归，不构建游戏、不跑真机、不评估技能内容质量；跨技能引用仍由 `skill_lint.py` 记为 WARN，不强制失败。

# v3.5.0 GitHub 在线安装与升级

- 在仓库根目录增加 `.agents/plugins/marketplace.json`，使 Codex 可通过 GitHub 仓库根路径发现嵌套的 `marketplace/plugins/omni-game-studio` 插件。
- 在双语 README 与安装指南中补充在线安装、刷新 Git 市场、重新安装升级，以及从旧本地市场迁移的命令。
- 保留本地市场安装方式作为备用，并将插件版本更新到 3.5.0。

# v3.4.3 Marketplace 命名统一

- 将本地插件市场 ID 统一为 `omni-game-studio-plugins`，并更新安装命令、README 和缓存路径示例。
- 将市场显示名改为 Omni Game Studio Plugins；AgentX 开发者署名保持不变。

## v3.4.2 README 国际化与项目介绍

- 重写仓库根 README，以英文作为默认显示语言并提供完整简体中文对应内容。
- 详细说明本项目的技能组成、引擎支持、制作生命周期、AI 图片/动效/音频流程、模板、脚本、验证边界和贡献方式。
- 保留中英文支付宝/微信赞助码、Star 引导及贡献入口。

## v3.4.1 AgentX 品牌与项目说明

- 将插件市场名、开发者显示名及安装说明统一为 AgentX 品牌。
- 新增项目根 README，介绍插件能力、安装入口、AI 资源流程、贡献方式和 Star 支持。
- 添加用户提供的支付宝与微信支付二维码，供自愿请咖啡支持项目维护。

## v3.4.0 Unity / Godot 工程技能拆分

- 将原 `unity-godot-engineering` 拆为独立的 `unity-engineering` 和 `godot-engineering` 技能，分别聚焦各自的架构、实现、性能剖析与构建/导出。
- 将可选工程子代理同步拆为 `unity-engineer` 与 `godot-engineer`，并更新 Cocos、流水线及总编排中的派发路由。
- 将跨引擎选型移至总编排，并按源引擎与目标引擎协调迁移评估，避免单一双栈工程角色承担不清晰的范围。

## v3.3.0 制作生命周期与交付门禁

- 按提供的游戏制作流程参考，补齐 G1 立项、G2 可玩原型/垂直切片、G3 Alpha、G4 Beta 内容锁定、G5 Gold 与上线后运营的评审框架。
- 增加可裁剪的 Sprint 集成、可玩构建评审、测试反馈和复盘；加入制作路线图、Sprint 复盘、里程碑证据模板。
- 明确现有七阶段状态脚本只检查文档工件，不能替代可玩构建、实际 QA、平台验证或人工门禁签署。
- 保留 Codex 会话内 AI 图像生成、GIF/精灵表动效和 AI 音频工作流；新增生命周期不要求团队采用特定项目管理工具。

## v3.2.0 AI 素材生成

- 补充 Codex 图像生成技能和 OpenAI Images API 工具说明，生成静态图与 2–16 帧 GIF；按要求先存档到备份目录。
- 保留静态精灵表及切帧流程；GIF 可直接生成动画，视频生成需其他明确可用的服务。
- 音效和音乐可经 ElevenLabs API 文字生成，继续支持现有会话中的音频工具。
- 发布资源校验现在识别 `animation`、`vfx` 类型及 GIF 图片。
- OpenAI 图片生成脚本使用模拟/预览流程说明，不使用真实 API 密钥或产生计费请求。

## v3.1.0

- 新增 AI 动画制作技能和等网格精灵表切帧工具，支持帧备份及 JSON 时间信息。
- 新增 ElevenLabs 音效和音乐 HTTP 适配器；密钥通过环境变量提供，`--dry-run` 不联网，实际调用可能产生费用。
- 图片生成优先调用当前可用的生成工具；音频也可使用其他已连接的生成工具。能力依赖运行环境及账户。
- 修复发布技能的无效 YAML frontmatter。
- 音频适配器经过模拟服务测试，未使用真实账户进行端到端生成；音质、授权及模型实际可用性需要用户环境确认。

## v3.0.1

- 发布资源终检缺少 Pillow 时返回退出码 2；严格授权要求 JSON 布尔值 true，并阻止占位资源通过。
- 对格式错误的清单给出失败结果；基础检查不再提前强制透明背景。
- 禁止重复初始化覆盖状态；禁止通过 set 修改阶段或历史，已完成阶段不会重复推进。
- 检查 Godot 实际导出目标，支持单个文件并拒绝零字节产物；这不验证文件内容或新鲜度。
- 图集放不下时明确失败；拒绝重复图名，避免递归收录自己的输出，并保留源图透明度。
- 批量生成占位图时限制清单路径在项目根目录内，不再改写未更改的清单。
- 技能允许在无子代理时由当前助手工作，并明确阶段文档检查不能替代资源、构建和设备验证。

v3.0.1 回归测试：进入 `marketplace/plugins/omni-game-studio/` 后执行 `python -m unittest discover -s tests -v`；测试需要 Pillow。
