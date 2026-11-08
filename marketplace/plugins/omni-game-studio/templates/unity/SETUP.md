# Unity 模板使用说明

## 打开

1. Unity Hub → Add → 选择本目录（含 `Assets/`、`Packages/`、`ProjectSettings/`）
2. 若提示版本不一致，允许 Unity 升级工程（模板基于 2022.3 LTS 记录，2021.3+ / Unity 6 一般可直接打开）
3. 首次导入会生成 `Library/`，耗时较长属正常

## 生成场景（必须做一次）

菜单栏 **Tools ▸ Omni ▸ Create Main Scene**

会创建 `Assets/Scenes/Main.unity`，其中 `GameRoot` 挂着原型脚本，并自动加入 Build Settings。

> 之所以做成菜单而不是自动执行：避免在你的编辑器里擅自新建场景、覆盖未保存的改动。

## 运行

点 Play。点击/拖动鼠标，方块会跟随；吃金币 +10；30 秒结束后按 R 重开。

## 批处理构建

1. 按目标平台修改 `Assets/Editor/BuildScript.cs` 里的 `OutputDir` 与 `Target`
2. 运行：

```bash
Unity.exe -quit -batchmode -nographics -projectPath "<项目>" -executeMethod BuildScript.PerformBuild -logFile -
```

或用插件的脚本自动识别：

```bash
python scripts/build_check.py --project . --run
```

## 换成正式工程时

- 删掉 `GameRoot.cs` 与 `OmniSceneBuilder.cs`，换成正式场景与架构
- `BuildScript.cs` 建议保留，作为 CI 构建入口
- 纹理压缩、代码裁剪（`link.xml`）、Addressables 分组按技术方案配置
