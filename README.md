# Omni Game Studio Codex · v3.4.1

面向 Codex 的多引擎游戏制作插件，覆盖从立项、玩法与技术设计，到美术/音频资源、工程实现、测试、发布和持续运营。支持 Cocos Creator、Unity 与 Godot，并按项目所用引擎提供独立工程技能。

**English:** A game production plugin for Codex, covering Cocos Creator, Unity, and Godot from concept through production, QA, release, and live operations.

[![GitHub stars](https://img.shields.io/github/stars/NextAgentX/omni-game-studio-codex?style=social)](https://github.com/NextAgentX/omni-game-studio-codex/stargazers)

## 能做什么

- **游戏全流程**：立项与 G1–G5 里程碑、预制作与垂直切片、迭代 Sprint、Beta 内容锁定、发布及上线后运营。
- **独立引擎工程技能**：Cocos Creator、Unity、Godot 各自独立处理架构、代码、性能和平台构建/导出。
- **AI 资源制作**：在当前 Codex 会话支持时使用图像生成工具；制作 GIF/精灵表动效；通过可用音频工具或可选 API 生成音效与音乐。具体能力依赖会话工具、模型和账户权限。
- **交付与质量**：提供工程模板、资源校验、构建检查和阶段文档。文档检查不会冒充真实构建、QA 或设备验证。

## 安装

请按 [安装与 AI 资源指南](INSTALL.md) 将 `marketplace/` 注册为本地插件市场并安装。指南包含 Windows/类 Unix 路径提示、AI 图片与 GIF、AI 音效/音乐的配置方式和授权注意事项。

## 支持项目

如果这个项目对你有帮助，欢迎用以下方式支持持续维护：

### 请我喝杯咖啡

支付宝或微信扫码，自愿支持项目维护与后续开发。感谢每一份支持！

<p align="center">
  <img src="donate-alipay.jpg" alt="支付宝赞助二维码" width="240" />
  &nbsp;&nbsp;&nbsp;
  <img src="donate-wechat.png" alt="微信支付赞赏二维码" width="240" />
</p>
<p align="center">支付宝　　　　　　　　微信支付</p>

### 给项目点个 Star

如果你觉得插件有用，请到 GitHub [点亮 Star](https://github.com/NextAgentX/omni-game-studio-codex/stargazers)，也欢迎把项目分享给正在做游戏的朋友。

### 参与贡献

欢迎提交 Bug 反馈、文档改进、引擎适配、工程技能和资源流水线优化：

1. 先在 [Issues](https://github.com/NextAgentX/omni-game-studio-codex/issues) 搜索已有讨论；新问题请说明 Codex、引擎及版本、目标平台和复现步骤。
2. Fork 仓库并创建一个聚焦单一主题的分支，完成修改后说明动机、改动范围和兼容影响。
3. 对插件脚本改动，运行 `python -m unittest discover -s marketplace/plugins/omni-game-studio/tests -v`；对文档或技能改动，检查引用路径、阶段门禁和引擎边界是否同步。
4. 提交 Pull Request，并写明实际运行过的检查与未验证部分。涉及 AI 生成资源时，请同时注明来源、许可和所需备份。

也可以从 [现有 Issues](https://github.com/NextAgentX/omni-game-studio-codex/issues) 认领适合自己的任务。所有贡献都欢迎，感谢一起把游戏制作流程做得更可靠。

## 项目结构

```text
marketplace/   Codex 插件市场与 Omni Game Studio 插件
subagents/     可选的专业角色配置
INSTALL.md     安装、AI 资源生成与验证说明
OPTIMIZATION.md  版本更新记录
```
