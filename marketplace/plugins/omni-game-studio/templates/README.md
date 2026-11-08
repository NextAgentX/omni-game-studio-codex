# 模板目录

| 目录 | 内容 | 可用状态 |
|------|------|---------|
| `godot4/` | Godot 4 最小可玩工程（点击移动 + 吃金币 + 倒计时） | ✅ 可直接运行，已实测导入并跑通主场景 |
| `unity/` | Unity 工程（`GameRoot.cs` + 场景生成菜单 + 批处理构建脚本） | ⚠️ 可打开，场景需点一次菜单生成 |
| `cocos3/` | Cocos Creator 3.x（`GameRoot.ts` + package.json + tsconfig） | ⚠️ 代码就绪，场景需在编辑器手动创建 |
| `docs/` | 10 份文档骨架：00–06 阶段文档、07 制作路线图、08 Sprint 复盘、09 里程碑评审 | 复制到项目 `docs/` 后按团队规模填写 |
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
