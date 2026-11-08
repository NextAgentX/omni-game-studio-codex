# 对标分析：Claude Code Game Studios → Omni Game Studio

分析对象：[Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)（MIT，638 文件 / 49 agents / 74 skills / 15 hooks / 14 rules / 62 templates / framework 1.2.0）
本地基线：Omni Game Studio v3.5.0（14 skills / 8 subagents / 12 scripts / 10 templates / 3 engine starters）

> 注：以上是本文件撰写时 v3.5.0 的历史基线快照，分析结论不随工作树改写。工作树后续加入的 Unreal 工程师与技能（15 skills / 9 subagents）已随 v3.6.0 发布，见 OPTIMIZATION.md 的 v3.6.0 区块。

定位差异先说清：CCGS 是**给单个游戏项目用的模板**（克隆到你自己的游戏仓库里，跟着游戏一起演进）；本项目是**分发的插件**（装到任意仓库，不能假设项目结构）。因此 CCGS 里大量"改宿主配置"的机制（hooks / settings.json / statusline / permissions）**不可移植**；真正值钱的是它的**流程设计与质量闭环**。

---

## 一、值得借鉴的 12 个点（按投入产出排序）

| # | 借鉴点 | CCGS 出处 | 本项目落点 | 成本 | 收益 |
|---|---|---|---|---|---|
| 1 | `modes.rigor` 档位：一个开关控制 6 个旋钮 | `project.yaml` + `.claude/docs/effects-map.md` | `omni_state.py` + `game-production-pipeline` | 中 | ★★★★★ |
| 2 | 证据闭环：改到玩家可见的东西就必须"跑起来看一眼" | `.claude/docs/run-and-observe.md` | `build_check.py` + `validate_assets.py` + 门禁 | 中 | ★★★★★ |
| 3 | 文件即记忆：`session-state/active.md` 检查点 | `.claude/docs/context-management.md` | 每个 SKILL 的 Phase 0 | 低 | ★★★★☆ |
| 4 | 框架自测：`studio-tests/` 给 skill/agent 本身写测试 | `studio-tests/` + `.claude/scripts/skill-lint.sh` | `tests/` 新增 skill 结构校验 | 中 | ★★★★☆ |
| 5 | 错误恢复：**看产物，不看叙述** | `.claude/docs/error-recovery-protocol.md` | `omni-game-studio/SKILL.md` 铁律 | 极低 | ★★★★☆ |
| 6 | 单一配置源 + 优先级链 + `project.local.yaml` 个人覆盖 | `project.yaml` / `config-resolution.md` | `.omni-state.json` 升级为 `project.yaml` | 中 | ★★★☆☆ |
| 7 | 门禁写成"数据"而非散文：每个门一个小文件 + 固定裁决词 | `.claude/docs/director-gates/*.md`（27 个） | `templates/docs/09-milestones.md` 拆分 | 低 | ★★★☆☆ |
| 8 | 先探测阶段再开方（`/project-stage-detect`） | `.claude/skills/project-stage-detect/` | Phase 0 的第 0 问 | 低 | ★★★☆☆ |
| 9 | 路径域规则：按目录加载的编码标准 + 正反例 | `.claude/rules/*.md`（14 个，带 `paths:` frontmatter） | 新增 `rules/` 参考库 | 低 | ★★★☆☆ |
| 10 | 「读取分节，永不整读」的上下文经济 | `effects-map.md` 头注、`validate-read.sh` | 各 SKILL 的 references 加载说明 | 极低 | ★★★☆☆ |
| 11 | 单特性编排（`/team-combat` 这类），区别于全流水线 | `.claude/skills/team-*`（9 个） | Workflow E 之外补一条 F | 中 | ★★☆☆☆ |
| 12 | 诚实的度量：公布"重流程没有让游戏更好"的数据 | README `Does it produce games, or documents?` | README 定位段落 | 低 | ★★☆☆☆ |

---

## 二、重点四条的展开

### 1. rigor 档位（最大的流程问题）

CCGS 自测四个游戏、同一份 brief、不同 rigor：

| `modes.rigor` | 写第一行游戏代码前的文档数 | 耗时 |
|---|---:|---:|
| `minimal` | 1（一页 brief） | 0 分钟 |
| `standard` | 30 | 58 分钟 |

结果：两位盲评 + 一次真人试玩，把 `standard` 判为**最后一名**——多出的 29 份文档买到的是可追溯性，不是更好的游戏。

对应到本项目：`omni_state.py` 的 `STAGES` 是硬性 7 段（brief→gdd→tech→art→audio→qa→release），`advance` 逐段门禁，没有"轻量模式"。结果是一个 20 分钟的玩法原型和一款要上线的游戏走完全相同的文书流程。这是我们与 CCGS 最大的流程差距，也是最该先补的。

CCGS 的三个设计细节值得一并抄：
- **唯一前门**：`rigor` 一个字段展开成 6 个旋钮，`/start` 只问一次；
- **禁止预置**：那 6 个被展开的键**不允许**出现在 `project.yaml` 里，否则钉死取值、遮蔽 rigor 展开（他们在 `project.yaml` 里写了 14 行注释专门警告这件事）；
- **两个逃生口**：`system_overrides`（单个系统单独提级）+ `project.local.yaml`（个人偏好，gitignore）。

### 2. 证据闭环（我们已知的漏洞，但没堵）

他们对此的表述是最狠的一句：**"A parse check is not a run."**

机制：改了玩家可见东西的故事，**不关闭**，直到游戏被启动、被观察、截图留在 `production/qa/evidence/<story-slug>/`，并用 `review-receipts.sh hash` 给改过的文件打 `stamp.txt`——之后任何一次改动都会让证据显示"比代码旧"。每个引擎有具体的无人值守截图命令（Godot `--write-movie`、Unity `ScreenCapture`、Unreal `HighResShot`），并明确写了**绝不能用的 flag**（`--headless`、`-batchmode`、`-nullrhi`——它们的存在就是为了跳过渲染）。

本项目现状：README 的 Limits 段已经诚实声明"文档完成或脚本通过不能证明游戏可玩"，但**只停留在声明**。`build_check.py --run` 能构建，`validate_assets.py` 能校验清单，却没有任何一步产出"我看见了"的产物。补法：`--capture` 参数 + 证据目录约定 + 门禁校验证据是否比代码新。

### 3. 文件即记忆（Context 是稀缺资源）

> **The file is the memory, not the conversation.**

`production/session-state/active.md` 分两个区，职责分离是关键设计：
- `<!-- STATUS -->`（Statusline 读，仅 Production+ 阶段）
- `<!-- CHECKPOINT -->`（每次会话启动读，**覆盖写、不追加**，~25 行以内，原文展示）
- 之后是自由叙述区（给人看，无 hook 注入）；超过 200 行就 rotate 到 `session-logs/`

为什么值得抄：本项目 SKILL 里"全文传递，不要摘要"（Workflow A Phase 1→2）在长会话里会被压缩吃掉。一个检查点文件能让冷启动的下一会话（或压缩后）直接续上。

### 4. 框架自测（我们的产品就是提示词，却没有测提示词的测试）

`studio-tests/` 分四层：
1. `catalog.yaml` —— 74 skills / 49 agents 全量目录
2. `quality-rubric.md` —— 按类别（gate / review / sprint / team …）定义 4–5 条二元 PASS/FAIL 指标
3. `skill-lint.sh` —— 7 条结构合规检查（静态）
4. `skill-test static|category|spec|audit` —— 缺省值、行为断言、覆盖率报告；`skill-improve` 做"测-改-再测，分数不掉才留"的闭环

判分哲学也值得抄：**PASS / FAIL / WARN / NOT ASSESSED 四值**。强制评估不到时输出 `NOT ASSESSED` 而不是 0 分或 PASS——这直接杀掉了"看起来评过了"的幻觉。本项目目前只有 `test_ai_audio.py` / `test_reliability.py` 两个脚本测试，14 个 SKILL 零覆盖。

---

## 三、另外三条低成本高价值的文本级改动

- **错误恢复协议**："A fluent response is not evidence that a phase ran. The artifact is — observe the artifact, not the transcript." 子代理返回一段流畅的"我将要…"却没写文件，是最隐蔽的失败形态。规则：返回契约里点了路径，就 `ls` 它；没有 = FAILED PHASE，不推进、不总结为完成。本项目已规定"写操作串行"，但没有"校验产物存在"这条。
- **先探测再开方**：`/start` 第一问是"你现在在哪"（没想法 / 模糊概念 / 设计清楚 / 已有工作），四选一，不做任何假设。本项目 Phase 0 是 5 个变量的固定清单——对存量工程容易问错问题。
- **门禁写成数据**：每个门一个小 md，字段固定为 触发时机 / 传给代理的上下文 / 提示词 / 裁决词（`REALISTIC` / `CONCERNS` / `UNREALISTIC`）。固定裁决词让"评审通过了吗"变成可解析的字符串，而不是一段散文。访问约定也值得抄：**"父会话不该读这个文件，由被派的 agent 读"**——省父上下文。

---

## 四、明确不要抄的

| 反面项 | 原因 |
|---|---|
| 74 skills / 49 agents 的规模 | 维护成本压倒收益；他们自己的数据证明更重的流程不产出更好的游戏。我们 14 个 skill 是优势，不是欠账 |
| hooks / settings.json / permissions / statusline | Claude Code 专有能力，Codex 无对应扩展点。要的是机制思想，不是这些文件 |
| 15 个 hook 挂在每次工具调用上 | 他们得在 README 里专门解释"这不是性能问题"，说明已经是个包袱 |
| 92 KB CHANGELOG + 87 KB UPGRADING | 模板类项目的维护税。插件靠语义化版本 + 迁移说明即可 |

---

## 五、实际落地（已完成）

原计划的 P0 里 **rigor 档位已撤销**：本项目的编排已有 `Workflow D`（玩法原型 go/no-go）和 `Workflow E`（单点直调）两条轻量路径，`game-production-pipeline` 的"不许跳阶段"只作用于用户明确要端到端时。给已解决的问题再加一层档位配置，是净增维护成本。CCGS 需要 rigor 是因为它只有一条流水线，那是因为它只有一个入口。

| 项 | 状态 | 落点 |
|---|---|---|
| 产物优先于叙述 | 已完成 | 两个编排技能的铁律 + 子代理产物校验 |
| 证据闭环（截图留证） | 已完成 | `build_check.py --capture`、`docs/qa/evidence/<名字>/`、`receipt.json` 哈希绑定、`omni_state.py evidence check`、`advance` 离开 qa 时拦截 |
| 会话检查点 | 已完成 | `omni_state.py checkpoint`、`.omni/active.md`（STATUS / CHECKPOINT / 叙述三区）、超 200 行归档 |
| skill 结构自测 | 已完成 | `scripts/skill_lint.py`（7 条检查、四值判分）+ `tests/test_skill_lint.py`；首跑即查出 2 个技能缺触发条件、2 处跨技能引用会扑空 |
| rigor 档位 | 撤销 | 见上 |
| `project.yaml` 重构 / rules/ / Workflow F | 未做 | 判断为负收益，不做 |

