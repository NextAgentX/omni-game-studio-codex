# Cocos Creator 3.x 模板使用说明

> ⚠️ 与其他两个模板不同，**Cocos 必须做一步手动操作**（场景文件是编辑器生成的二进制/JSON 混合格式，手写容易损坏工程）。这是刻意选择：宁可让你点两下，也不给你一个打不开的工程。

## 打开

1. Cocos Dashboard → 项目 → 导入 → 选择本目录（含 `package.json`、`assets/`）
2. 用 **Cocos Creator 3.8.x** 打开（版本不一致会提示升级，允许即可）
3. 首次打开会生成 `settings/`、`temp/`、`library/`，耗时较长属正常

## 创建场景（手动，一次性）

1. 资源管理器右键 `assets` → 新建 → 场景，命名 `main`
2. 打开 `main.scene`，在层级管理器里：右键 → 创建 → UI → Canvas
3. 选中 **Canvas** 节点，属性检查器 → 添加组件 → 自定义脚本 → `GameRoot`
4. 保存场景（Ctrl+S）
5. 项目设置 → 项目数据 → 起始场景，设为 `main`

## 运行

点顶部预览按钮（浏览器预览）。点击/触摸移动方块，吃金币 +10，30 秒结束。

## 构建

编辑器内：项目 → 构建发布，选择平台（web-mobile / 微信小游戏 / Android …）后构建。

脚本化（路径随安装位置变化）：

```bash
CocosCreator.exe --project "<项目>" --build "platform=web-mobile;debug=false"
```

或让插件脚本识别并提示：

```bash
python scripts/build_check.py --project .
```

## 换成正式工程时

- `GameRoot.ts` 里的节点创建逻辑换成正式场景 + 预制体
- 目录按 `references/project-structure.md` 的 `core / game / ui / platform` 分层
- 图集、纹理压缩、分包、引擎模块裁剪按技术方案配置
- 小游戏平台记得先核对首包上限与分包规则
