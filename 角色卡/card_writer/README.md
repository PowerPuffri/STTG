# 角色卡撰写器

本工具面向 `chara_card_v2`（spec_version 2.0）格式的角色卡，提供两种方式：

- 一键撰写：接入任何「OpenAI 兼容」的 Chat Completions API（`/v1/chat/completions`）。
- 精雕细琢：完整字段编辑与高级 JSON 编辑器，保证格式可控。
- 平台映射：按目标平台导出与校验（CharHub/Chub、SillyTavern、Legacy Tavern v1）。

## 使用方式

1. 打开 `card_writer/index.html`。
2. 如需导入现有角色卡，点击「导入 JSON」。
3. 在「一键撰写」中填写要点并点击「一键撰写」。
4. 在「精雕细琢」中细化字段。
5. 选择「目标平台」，再点击「导出 JSON」。

## 目标平台映射

- `CharHub / Chub (chara_card_v2)`
- 导出：原样 `chara_card_v2`（保留扩展字段）
- 校验重点：`extensions.chub` 结构

- `SillyTavern (chara_card_v2)`
- 导出：原样 `chara_card_v2`
- 校验重点：`extensions.depth_prompt` 与 `character_book`

- `Legacy Tavern v1`
- 导出：旧版平铺字段（`name/description/personality/scenario/first_mes/mes_example`）
- 说明：内部仍编辑 v2，导出时自动转换到 v1

## 角色卡格式要点（chara_card_v2）

顶层字段：

- `spec`: 固定为 `chara_card_v2`
- `spec_version`: 固定为 `2.0`
- `data`: 角色内容主对象

`data` 常用字段：

- `name`: 角色名
- `description`: 角色描述（推荐 Markdown 小节）
- `first_mes`: 首条消息
- `mes_example`: 对话示例
- `scenario`: 场景/世界观
- `personality`: 可选
- `tags`: 字符串数组
- `alternate_greetings`: 字符串数组
- `creator_notes`: 可含 HTML
- `system_prompt` / `post_history_instructions`: 可选
- `extensions`: 扩展字段
- `character_book`: 角色书（Lorebook）

工具会自动保留未识别字段，不会在导出时丢失。

## 导入兼容

- 支持导入 `chara_card_v2`
- 支持导入 Legacy Tavern v1（导入后自动转换为 v2 内部编辑模型）
