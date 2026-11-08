# 脚本目录

全部为 Python 3.9+ 单文件脚本。图像裁切、切帧、占位图、图集打包及图片终检需要 Pillow。AI 图片与 GIF 通过 OpenAI Images API 生成；GIF 需要模型资格。

| 脚本 | 作用 | 依赖 |
|------|------|------|
| `omni_state.py` | 流水线状态与阶段门禁（init / status / check / advance / set） | 无 |
| `validate_assets.py` | 资源校验；`--final` 为发布终检（拦 draft、缺 license、无 alpha、实底图） | Pillow（终检必需） |
| `gen_placeholder_art.py` | 生成占位图（仅用于验证管线，**不是正式资源**） | Pillow |
| `process_art.py` | 正式图后处理：抠背景色、裁透明边、等比缩放到规格、九宫格可行性检查 | Pillow |
| `gen_music.py` | 程序化 chiptune BGM（5 种风格，输出 WAV + 循环元数据） | 无 |
| `gen_sfx.py` | 合成音效（10 个预设，44.1kHz/16bit/mono） | 无 |
| `gen_ai_audio.py` | AI 音效 / 音乐（ElevenLabs API，支持不联网预览） | 服务密钥和额度 |
| `gen_ai_image.py` | OpenAI API 图片与短动画 GIF 生成，先备份再复制 | API 密钥、权限和可能产生的费用 |
| `split_sprite_sheet.py` | 等网格精灵表切帧，输出序列和动画元数据 | Pillow |
| `compress_audio.py` | 音频压缩与体积核算；无 ffmpeg 时给引擎侧替代方案 | ffmpeg（可选） |
| `pack_atlas.py` | 图集打包（shelf packing，输出通用 JSON 索引） | Pillow |
| `build_check.py` | 引擎识别、构建命令生成、产物校验 | 无 |

## 装 Pillow

```bash
python -m pip install pillow
```

## 快速自检

```bash
python omni_state.py init --root /tmp/demo --engine godot
python gen_sfx.py --list
python gen_placeholder_art.py --out /tmp/demo/a.png --size 128x128 --label demo
python validate_assets.py --manifest /tmp/demo/assets/manifest.json --root /tmp/demo
python build_check.py --project /tmp/demo
```

批量占位生成只处理清单中标记 `"placeholder": true` 的图片条目；示例清单默认未标记，需要先按实际需要填写。

## 设计原则

- **退出码有意义**：0 通过 / 1 失败 / 2 缺依赖。CI 可直接用。
- **不猜**：引擎识别不出来就报错让你指定，不默认选一个。
- **不静默成功**：构建失败返回真实退出码，产物为空判失败。
- **占位可追溯**：`placeholder: true` 保留在 manifest 里，使用 `--final` 阻止发布。
- **门禁边界**：`omni_state.py` 只检查各阶段文档，不会自动验证资源、构建或真机表现。应分别运行资源终检和构建检查；产物存在也不证明内容正确或是本次生成。
- **状态保护**：初始化不会覆盖已有状态；`set` 仅允许修改 project、engine、engine_version 和 platforms。
