# v3.6.1

本补丁收紧 G2 截图证据校验：`build_check.py` 在采集阶段验证 PNG 签名、图片可解码性与尺寸，拒绝伪造或空白截图；`omni_state.py` 在 receipt 中登记截图 SHA-256 与尺寸，并在证据门禁中核对摘要、尺寸与文件新鲜度，防止截图被篡改后仍被当作有效证据。回归测试新增可解码 PNG 夹具、伪 PNG 拒绝、路径逃逸防护和截图摘要变更用例。发布前校验：validate_repo 69 checks / 0 warnings / 0 errors、skill_lint 20/20 PASS、unittest 38 tests OK。`plugin.json` 版本 3.6.1 与 tag `v3.6.1` 一致，INSTALL 标题与缓存路径示例同步。

# v3.6.0

本版把此前累积的未发布能力线一次性定版：`plugin.json` 版本 3.6.0 与 tag `v3.6.0` 一致，INSTALL 标题与缓存路径示例同步。发布前校验：validate_repo 69 checks / 0 warnings / 0 errors、skill_lint 20/20 PASS、unittest 31 tests OK。

## Unreal Engine 5 工程师与配套链路

- 新增 `subagents/unreal-engineer.toml` 与 `skills/unreal-engineering/SKILL.md`：按「UE 大版本 + 目标平台」锁定结论，覆盖模块与目录划分、蓝图/C++ 职责分层、Gameplay Framework 落位、BuildCookRun 打包排障、包体与性能实测，以及设计确认项的 @trace 覆盖率门禁。
- 总编排与端到端流水线接入 `unreal-engineer` 派发（角色表、Workflow S/A/E、tech 阶段与 G2 派单）；`unreal-engineering` 进入引擎技能分组。Unreal 暂未提供起步模板，平台支持结论不套用三引擎矩阵，由角色按 Epic 官方文档单独核实。
- `omni_state.py` 与 `build_check.py` 引擎枚举加入 `unreal`：支持 .uproject 自动识别、RunUAT BuildCookRun 说明、截图能力如实返回 NOT ASSESSED，不谎称通过；`plugin.json` 描述与关键词同步。
- 双语 README、INSTALL、插件说明、文档模板与各角色/技能的引擎边界描述同步为四引擎；技能数 14→15、可选角色数 8→9。
- 边界：`multiplatform-release` 的 engine-matrix 仍为 Cocos / Unity / Godot 三引擎事实矩阵，未凭记忆补 Unreal 的平台支持结论。本条随 v3.6.0 发布。

## 软著申报能力线

- 新增 5 个软著申报技能：`copyright-filing`（主理人总编排，含 W1–W7 工作流与单角色直调路由）、`software-name-checker`（13 项命名规则 / 六渠道核查 / 三档结论 / Phase 0.5 名称锁死）、`copyright-material-kit`（60 页 × 每页 50 行源程序文档、说明书、申请表、材料清单）、`copyright-risk-audit`（12 项风险分级 + 提交前自评表 + 红线）、`copyright-filing-guide`（单文件 HTML 小白指导报告 + FAQ）。
- 新增 4 个可选角色 TOML：主理人 `copyright-filing-lead`、材料 `copyright-material-smith`、风控 `copyright-risk-auditor`、指导 `copyright-guide-designer`，与现有 9 个游戏角色（含 Unreal）并列。
- 新增 3 个零第三方依赖脚本（仅标准库，兼容 Python 3.9+）：`copyright_name_check.py`（名称静态预检）、`copyright_source_doc.py`（源程序分页文本，明确需转 PDF）、`copyright_audit.py`（三处名称一致 / 页数行数 / 密钥与版权头扫描 / 自评表判定）。
- 新增 4 份模板：`templates/copyright/material-templates.md`、`pre-submit-checklist.md`、`guide-report.html`（单文件内联 CSS）、`faq.md`。
- 编排沿用专家团 SOP：Phase 0 确认 → 0.5 名称锁死 → 1 材料串行 → 2 风险 / 指导双线并行 → 3 汇编交付（能交了吗 / 交什么 / 怎么交 / 红线原文不省略）。
- 宿主差异如实写明：Codex 无 WorkBuddy 团队运行时工具，协作以流程契约表达而非工具调用；可移植的是机制思想，不是宿主专有文件。
- 全仓计数统一校准：技能 15→20、可选角色 9→13、脚本 13→16、文档模板 10→14（另新增 4 份软著模板）；双语 README、INSTALL、插件说明与 `scripts/README.md` 同步。`ADOPTION.md` 的 v3.5.0 基线快照按其文件内注记保持不动。
- 边界：软著登记是形式审查，查名称不是为过审而是避免商标与应用商店冲突；脚本只做静态检查，不替代六渠道人工核查与官方审查；不承诺过审、不替用户做法律判断。
- 本版本定版为 v3.6.0：tag 与 `plugin.json` 版本一致，INSTALL 标题与缓存路径示例已同步。

## 证据闭环、会话检查点与技能自测

- `build_check.py` 新增 `--capture` / `--capture-only`：构建后无人值守启动引擎并截图，证据落在 `docs/qa/evidence/<名字>/`，同目录 `receipt.json` 记录所覆盖改动文件的 sha256。Godot 用 `--write-movie --quit-after` 原生支持；Unity 与 Cocos 无内置无人值守截图，返回 `NOT ASSESSED` 并给可用命令，不假装成功。
- `omni_state.py` 新增 `evidence list|check`：按 sha256 判断证据是否仍代表当前代码，被覆盖文件改过即判定过期；`advance` 离开 `qa` 阶段时默认校验证据，`--no-evidence` 可显式跳过。
- `omni_state.py` 新增 `checkpoint` 与会话检查点 `.omni/active.md`：`STATUS` 供工具读、`CHECKPOINT` 覆盖写、叙述区追加，超过 200 行自动归档到 `.omni/session-logs/`。两个编排技能在开工前先读它。
- 编排与流水线技能新增两条铁律：产物优先于叙述（声称写了文件就校验路径存在，缺失即阶段失败）、qa 之后必须有截图（`NOT ASSESSED` 不是通过）。
- 新增 `scripts/skill_lint.py` 与 `tests/test_skill_lint.py`：7 条结构检查、四值判分，发版前跑一次；首跑即查出两个技能缺触发条件、两处跨技能引用会扑空，均已修。
- 新增 `templates/active.md`；QA 文档模板增加「截图证据」小节。

## CI 门禁与仓库自检

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
