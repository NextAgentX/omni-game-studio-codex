# 工程结构与资源规范（三引擎）

> 第一至六节以 Cocos Creator 为例讲通用原则（依赖方向、图集、分包、性能预算），这些原则对 Unity、Godot 与 Unreal 同样成立。第七、八节给 Unity 与 Godot 的对应落法；Unreal 的模块与 Content 目录落法见 `unreal-engineering` 技能。

## 一、目录结构建议（Cocos Creator）

```
assets/
├── scenes/                 # 场景，按流程编号：00_Boot / 01_Main / 10_Game
├── scripts/
│   ├── core/               # 与业务无关的基础设施：事件、状态机、对象池、工具
│   ├── game/               # 玩法逻辑：战斗、关卡、数值
│   ├── ui/                 # 界面逻辑，按页面拆分
│   ├── platform/           # 平台适配层：登录、支付、广告、分享的抽象接口
│   └── config/             # 配置与常量，禁止硬编码散落各处
├── resources/              # ⚠️ 会被打进包体，只放必须动态加载的资源
├── bundles/                # 分包根目录，每个子目录一个 Asset Bundle
│   ├── lobby/              # 大厅
│   ├── battle/             # 战斗
│   └── common/             # 多包共用资源
├── art/
│   ├── ui/                 # UI 图，按图集划分
│   ├── character/
│   ├── environment/
│   └── vfx/
├── audio/
│   ├── bgm/
│   └── sfx/
└── configs/                # 数值表、关卡表等（json / csv 转成的 asset）
```

**关键原则**：
- `resources/` 是包体杀手。凡是能在场景里直接引用的，不要放 `resources/`。
- 分包按「玩法模块」切，不按「资源类型」切。按类型切会导致每个包都缺资源。
- `platform/` 层必须是一组接口 + 各平台实现，业务层只依赖接口。

## 二、依赖方向

```
ui / game  →  core  →  (无依赖)
     ↓
  platform（接口）
     ↑
platform/android | ios | harmony | minigame | web（实现）
```

**禁止**：`core` 反向依赖 `game`；`game` 直接调用平台原生 API（必须走 `platform` 接口）；`platform` 实现里写业务逻辑。

## 三、资源规范

### 图集划分
| 原则 | 说明 |
|------|------|
| 同屏同集 | 同一界面同时出现的图放同一图集，才能合批 |
| 按功能域切 | UI 通用件 / 单页面 / 角色 / 场景分别成集 |
| 控制单集尺寸 | 单张图集不超过 2048×2048（低端机 1024×1024 更稳） |
| 大图独立 | 全屏背景等大图不进图集，单独压缩 |

### 纹理压缩
| 平台 | 首选格式 | 备注 |
|------|---------|------|
| Android | ETC2（或 ASTC，视机型覆盖） | ASTC 质量更好但老机型不支持 |
| iOS | ASTC 或 PVRTC | 新设备优先 ASTC |
| 小游戏 | 平台支持的格式（多为 ASTC/ETC2） | 需核实目标平台支持度 |
| Web / Windows / Linux | 视 GPU 而定，可保留 PNG/JPG | Web 端注意解码耗时 |

### 命名规范
- 资源：`类型_模块_名称_状态`，如 `ui_battle_btn_attack_normal`
- 脚本：PascalCase 类名，文件名与类名一致
- 事件名：`模块:动作`，如 `battle:enemy_die`
- Bundle 名：全小写，无空格，语义化

## 四、分包策略

1. **首包只放"能玩的最小集"**：启动场景、登录、核心玩法第一关的资源、通用 UI
2. **按玩法阶段分包**：新手期之后的内容全部放分包
3. **公共资源单独成包**：避免多个分包重复打包同一份资源
4. **加载时机设计**：在玩家等待（加载页、结算页、过场）时预下载下一个分包，不要在操作中卡加载
5. **失败兜底**：分包下载失败要有重试与降级提示，不能白屏

## 五、性能预算模板

| 指标 | 低端机目标 | 中端机目标 | 高端机目标 |
|------|-----------|-----------|-----------|
| 帧率 | ≥30 FPS 稳定 | ≥45 FPS | 60 FPS |
| DrawCall | ≤80 | ≤120 | ≤200 |
| 内存峰值 | ≤200 MB | ≤350 MB | ≤500 MB |
| 首屏加载 | ≤5s | ≤3s | ≤2s |
| 同屏粒子数 | ≤50 | ≤150 | ≤300 |

> 以上为通用参考区间，实际目标须结合项目类型与目标机型实测校准，不可直接当验收标准。

## 六、多平台构建配置差异

| 配置项 | 小游戏 | Android/iOS | Windows/Linux | Web |
|--------|--------|-------------|---------------|-----|
| 纹理压缩 | 平台指定格式 | ETC2 / ASTC | 视 GPU | 保持通用格式 |
| 引擎模块 | 极致裁剪 | 按需裁剪 | 按需裁剪 | 按需裁剪 |
| 分包 | 必须 | 可选 | 可选 | 可选（按需加载） |
| 远程资源 | 常用 | 少用 | 不用 | 常用 |
| 调试信息 | 关闭 | 关闭 | 关闭 | 可保留 sourcemap |
| 音频格式 | 平台支持优先 | mp3/aac + wav | ogg/mp3 | mp3/ogg |

## 七、Unity 工程结构

```
Assets/
├── Scenes/                # 按流程编号：Boot / Main / Level_01
├── Scripts/
│   ├── Core/              # 事件、状态机、对象池、工具（不依赖业务）
│   ├── Gameplay/          # 玩法逻辑
│   ├── UI/                # 界面逻辑
│   ├── Platform/          # 平台抽象接口（登录/支付/广告/分享）
│   └── Editor/            # 编辑器扩展，必须放 Editor 目录
├── ScriptableObjects/     # 数据配置（关卡、数值、掉落表）
├── Art/                   # 美术资源
├── Audio/
├── Settings/              # URP Asset、Addressables 配置、Quality 设置
└── Resources/             # ⚠️ 慎用：该目录内容会全量打进包体
```

**关键原则**：
- **必须用 Assembly Definition 拆模块**，不要把所有代码堆在 `Assembly-CSharp`。模块化才能控制编译时间与依赖方向。
- **资源加载统一走 Addressables**，不要手写 AssetBundle，也不要把动态资源塞 `Resources/`。Addressables 的 group 就是分包边界。
- **依赖方向与 Cocos 一致**：`Gameplay / UI → Core`，`Platform` 只暴露接口，平台实现按导出目标条件编译（`#if UNITY_ANDROID` 等）。
- **代码裁剪要防误伤**：IL2CPP + Managed Stripping 会裁掉仅通过反射/序列化访问的类型，需用 `link.xml` 显式保留，否则真机崩溃、编辑器正常。

## 八、Godot 4 工程结构

```
res://
├── scenes/                # .tscn，按功能域分子目录
├── scripts/               # .gd 或 .cs
├── resources/             # 自定义 Resource（.tres）作为数据配置
├── assets/
│   ├── art/
│   └── audio/
├── autoload/              # 全局单例，慎用
└── export_presets.cfg     # 各平台导出预设
```

**关键原则**：
- **场景树用组合不用继承**：把能力做成子场景（组件）挂上去，而不是靠继承链扩展。这是 Godot 与 Unity 思维差异最大的一点。
- **用 signal 解耦**：禁止在深层节点里写 `get_node("../../../Player")` 这类硬路径，节点一挪就断。
- **数据配置用自定义 Resource**：定义 `class_name ItemData extends Resource`，用 `@export` 暴露字段，比读 json 更类型安全，还能直接在检查器里编辑。
- **Autoload 只放真全局服务**：音频总线、存档管理、事件总线。业务单例塞进 Autoload 会让场景无法独立运行与测试。
- **导出模板要锁版本**：Godot 的导出依赖与编辑器版本匹配的 export templates，版本错配会直接构建失败，团队需统一编辑器版本。

## 九、三引擎结构映射速查

| 概念 | Cocos Creator | Unity | Godot |
|------|---------------|-------|-------|
| 场景文件 | `.scene` | `.unity` | `.tscn` |
| 脚本 | `.ts`（组件） | `.cs`（MonoBehaviour） | `.gd` / `.cs`（Node） |
| 数据配置 | json / asset | ScriptableObject | 自定义 Resource（.tres） |
| 资源分组/分包 | Asset Bundle | Addressables Group | 导出过滤 / PCK 分包（需自研） |
| 图集 | Sprite Atlas | Sprite Atlas | AtlasTexture |
| 全局单例 | 常驻节点 | Service Locator / DontDestroyOnLoad | Autoload |
| 事件解耦 | EventTarget | C# event / UnityEvent | signal |
| 平台条件编译 | `#if` 宏 | `#if UNITY_*` | Feature tag / 平台检测 |
