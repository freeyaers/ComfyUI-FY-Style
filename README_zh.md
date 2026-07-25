# ComfyUI-FY-Style

> 简单实用的参考图懒人专属方案 — 1000+ 精选风格，并且每张图附带精准的简易提示词。

[English instructions](README.md)

---

## 简介

**FY Style** 是一款 ComfyUI 自定义节点插件，提供内置的风格参考图画廊。每张参考图都配有可直接使用的简化提示词。

- **1000+ 风格参考图**，精选自开源项目 [fal-Krea-2-Style-LoRA](https://huggingface.co/fal/krea-2-style-lora)
- **灵活的分类浏览与搜索**，支持标签筛选和全文检索
- **中英文双语支持**，语言偏好自动保存
- **一键注入提示词** — 选中的图片提示词自动追加到你的工作流中

---

## 快速上手

1. 将插件安装到 ComfyUI 的 `custom_nodes/` 目录
2. 重启 ComfyUI
3. 在工作流中添加 **FY Style** 节点
4. 打开节点内嵌的画廊面板
5. 浏览或搜索你想要的风格，点击选中
6. 节点自动输出选中的图片 + 对应提示词（可选），直接连接你的图像生成模型即可

---

## 工作流

### 基本工作流

![基本工作流](https://github.com/freeyaers/ComfyUI-FY-Style/blob/main/workflows/basic_workflow.jpg)

典型使用流程：

1. 在工作流画布中添加 **FY_Style** 节点
2. 打开节点内的画廊面板，选择一张风格参考图
3. 可选：在 `positive_prompt` / `negative_prompt` 输入框中添加你自己的提示词
4. 节点会自动将参考图提示词与你的自定义文本组合（参考图提示词在前，逗号分隔）
5. 将输出的 `IMAGE` 和组合后的提示词接入你的图像生成管线

下载完整工作流：[basic_workflow.json](https://github.com/freeyaers/ComfyUI-FY-Style/blob/main/workflows/basic_workflow.json)

### 参考图图像生成

![参考图图像生成](https://github.com/freeyaers/ComfyUI-FY-Style/blob/main/workflows/reference_image_generation.jpg)

---

## 参考生图效果展示

推荐使用 **Krea-2 模型** 结合 **[ComfyUI-Krea2-StyleTransfer](https://github.com/jieg9341-lab/ComfyUI-Krea2-StyleTransfer)** 插件来生成（感谢作者开源这么厉害的参考图插件）。

![输出示例 1](https://github.com/freeyaers/ComfyUI-FY-Style/blob/main/workflows/output/1.png)
![输出示例 2](https://github.com/freeyaers/ComfyUI-FY-Style/blob/main/workflows/output/2.png)
![输出示例 3](https://github.com/freeyaers/ComfyUI-FY-Style/blob/main/workflows/output/3.png)

> **注意：** 将生成的输出图片放入 `workflows/output/` 目录即可更新此处示例。

---

## 文件说明

| 路径 | 说明 |
|------|------|
| `__init__.py` | 插件入口 — 注册 `FY_Style` 节点和 HTTP 路由 |
| `nodes.py` | 核心节点实现 — 读取选中图片，返回提示词 + 图片张量 |
| `update.py` | HTML 生成器 — 解析 `img/` 目录文件名，生成 `index.html` 画廊页面 |
| `js/main.js` | ComfyUI 前端扩展 — 嵌入画廊 iframe，处理跨帧消息通信 |
| `lang/zh-cn.json` | 中文语言包（UI 字符串 + 分类翻译） |
| `lang/en.json` | 英文语言包 |
| `img/` | 风格参考图目录（命名规范：`[_tag]N-名称(提示词){URL}.ext`） |
| `index.html` | 生成的画廊页面（由 `update.py` 自动生成） |
| `selected_image.json` | 运行时状态 — 保存当前选中的图片及其提示词 |
| `workflows/basic_workflow.json` | 示例 ComfyUI 工作流 |
| `workflows/basic_workflow.png` | 工作流示意图 |
| `workflows/reference_image_generation.png` | 参考图图像生成示意图 |
| `workflows/output/` | 生成效果示例图 |
| `更新图像风格 (Update image style).bat` | Windows 批处理脚本，运行 `update.py` 刷新画廊 |

---

## 图片命名规范

`img/` 目录中的参考图遵循以下格式：

```
[_tag]N-中文名称(English prompt ---- negative prompt){URL}.ext
```

| 部分 | 示例 | 说明 |
|------|------|------|
| `[_tag]` | `[_3d_rendering]` | 分类标签（对应语言包 `classify` 的键） |
| `N-` | `1-` | 序号 |
| `中文名称` | `轻盈瓷蓝` | 中文显示名称（UI 中展示） |
| `(English prompt)` | `(airy porcelain blue style)` | 简化正向提示词 |
| `----` | — | 正负向提示词分隔符 |
| `{URL}` | `{https://hf-mirror.com/...}` | 来源链接（自动解码显示） |

添加新图片后，运行 `update.py`（或双击 `.bat` 文件）重新生成 `index.html`。

---

## 语言支持

画廊支持两种语言：**中文 (zh-cn)** 和 **英文 (en)**。

- 语言偏好保存在浏览器 Cookie 中，跨会话持久化
- 分类名称通过各语言包的 `classify` 字段进行翻译
- UI 字符串（按钮、占位符、提示）均已本地化
- 添加新语言：在 `lang/` 目录下新建对应的 `.json` 文件

---

## 推荐搭配

为获得最佳效果，推荐以下方案：

- **Krea-2 模型** — [krea2_turbo_bf16.safetensors](https://modelscope.cn/models/krea/Krea-2-Turbo)
- **[ComfyUI-Krea2-StyleTransfer](https://github.com/jieg9341-lab/ComfyUI-Krea2-StyleTransfer)** — 参考图风格迁移插件，由 [jieg9341-lab](https://github.com/jieg9341-lab) 开源

---

## 许可

本插件仅供个人及社区使用。风格参考图来源于开源 LoRA 项目。
