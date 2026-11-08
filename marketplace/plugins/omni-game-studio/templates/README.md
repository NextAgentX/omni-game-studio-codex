# 模板目录

| 目录 | 内容 | 可用状态 |
|------|------|---------|
| `godot4/` | Godot 4 最小可玩工程（点击移动 + 吃金币 + 倒计时） | ✅ 可直接运行，已实测导入并跑通主场景 |
| `unity/` | Unity 工程（`GameRoot.cs` + 场景生成菜单 + 批处理构建脚本） | ⚠️ 可打开，场景需点一次菜单生成 |
| `cocos3/` | Cocos Creator 3.x（`GameRoot.ts` + package.json + tsconfig） | ⚠️ 代码就绪，场景需在编辑器手动创建 |
| `unreal5/` | **暂未提供起步模板** | 由 `unreal-engineer` 生成 .uproject、Source/、Build.cs 与两个 Target.cs |
| `docs/` | 10 份文档骨架：00–06 阶段文档、07 制作路线图、08 Sprint 复盘、09 里程碑评审 | 复制到项目 `docs/` 后按团队规模填写 |
| `copyright/` | 4 份软著申报模板：`material-templates.md`（说明书骨架 / 申请表字段 / 材料清单）、`pre-submit-checklist.md`（12 项自评表 + 红线清单）、`guide-report.html`（单文件内联 CSS 指导报告）、`faq.md` | 模板内 `[TODO]` 占位是给填表用的，落表后清零再交 |
| `assets-manifest.json` | 资源清单示例 | 复制到项目 `assets/manifest.json` |

## 为什么 Cocos 模板要手动一步

Cocos 的 `.scene` 是编辑器生成的复合格式，手写极易损坏工程。宁可让用户点两下建场景，也不给一个打不开的工程——这是刻意的取舍，不是偷懒。

## 用法

```bash
cp -r <plugin>/templates/godot4/* .
mkdir -p docs assets
cp <plugin>/templates/docs/*.md docs/
cp <plugin>/templates/assets-manifest.json assets/manifest.json
```

## 换成正式工程时

模板里的原型脚本（`main.gd` / `GameRoot.cs` / `GameRoot.ts`）只是用来验证"能跑"，正式实现按 `docs/02-tech.md` 的架构方案重写，保留 `BuildScript.cs` 这类构建入口。
