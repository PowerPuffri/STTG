# Nuomi Circuit - AI Companion Telegram Bot

Nuomi Circuit 是一个功能强大的 Telegram AI 角色扮演伴侣机器人。它结合了大语言模型（LLM）、语音识别（ASR）、语音合成（TTS）和图像生成技术，为用户提供沉浸式的多模态角色扮演体验。

## 🌟 核心功能

*   **🎭 深度角色扮演**：支持导入 SillyTavern 格式的角色卡（JSON / PNG）。每个角色拥有独特的性格、背景故事和对话风格。
*   **⚡ 流式对话**：基于 Zhipu AI (GLM-4-Plus)，实现低延迟的逐字流式回复，体验如真人聊天般顺畅。
*   **🗣️ 语音交互 (Voice-to-Voice)**：
    *   **听得懂**：用户可发送语音消息，系统（Deepgram）不仅能识别文字，还能感知**语气和情绪**，并让 AI 做出相应的反应。
    *   **说得出**：支持高质量 TTS（Deepgram Aura / OpenAI），支持设置“语音专属角色”（例如只发语音不发文字）。
*   **📸 动态私房照**：基于剧情发展，AI 可自动生成并发送符合当前场景和角色设定的照片 (GLM-Image)。
*   **🧠 智能记忆管理**：长对话自动触发摘要压缩机制，既不会遗忘关键设定，也不会因为上下文过长导致 API 报错。
*   **💎 商业化模块**：内置完整的 Freemium (免费+内购) 机制。
    *   **免费用户**：每日 30 条对话限制，图片功能被锁定。
    *   **VIP 用户**：无限畅聊，解锁所有高清私房照。

## 🛠️ 技术栈

*   **语言**: Python 3.10+
*   **框架**: `python-telegram-bot` (v20+)
*   **LLM & 图像引擎**: Zhipu AI (GLM-4-Plus, GLM-Image)
*   **语音引擎 (ASR & TTS)**: Deepgram / OpenAI
*   **数据库**: SQLite3
*   **进程管理**: PM2

## 🚀 快速开始

### 1. 环境准备
确保已安装 Python 3.10+ 和 PM2。
```bash
# 安装依赖
pip install -r requirements.txt
# (或者直接安装核心依赖)
pip install python-telegram-bot zhipuai httpx deepgram-sdk
```

### 2. 配置环境变量
复制配置模板并填入你的 API Keys：
```bash
cp config.example.py config.py
```
在 `config.py` 中填写：
*   `BOT_TOKEN`: 你的 Telegram Bot Token (从 @BotFather 获取)
*   `ADMIN_ID`: 你的 Telegram 用户 ID
*   `LLM_API_KEY`: 智谱 AI (Zhipu) 密钥
*   `DEEPGRAM_API_KEY`: Deepgram 密钥 (用于语音识别和合成)

### 3. 导入角色卡
将你的 SillyTavern 角色卡（`.png` 或 `.json`）放入项目根目录下的 `角色卡/` 文件夹中。
系统会在启动时自动解析并同步这些角色。

### 4. 启动服务
建议使用 PM2 进行后台常驻运行：
```bash
pm2 start telegram_bot.py --interpreter python3 --name nuomi-bot
```

## 🎮 Telegram 使用指令

*   `/start` - 唤醒机器人并注册账号
*   `/chars` - 呼出角色选择菜单 (带有 🎙️ 的为语音专属角色)
*   `/img [提示词]` - (VIP功能) 主动要求角色发送自拍
*   `/subscribe` - 查看会员订阅状态和权限

## 📁 目录结构

```text
STTG/
├── telegram_bot.py       # 主程序入口
├── st_client.py          # LLM API 客户端 (异步流式)
├── tts_client.py         # 语音合成客户端 (支持多引擎切换)
├── asr_client.py         # 语音识别客户端 (带情绪分析)
├── image_client.py       # 图像生成客户端
├── character_manager.py  # 角色卡解析与管理
├── database.py           # SQLite 用户与额度管理
├── config.py             # 核心配置文件 (不上传至 Git)
├── 角色卡/                # 用户放置 PNG/JSON 角色卡的目录
└── templates/            # 系统解析后存储的角色模板
```

## ⚠️ 注意事项

1. **隐私安全**：请勿将包含真实 API Key 的 `config.py` 提交到公开仓库。
2. **网络要求**：运行此 Bot 的服务器需要能够正常访问 Telegram API (`api.telegram.org`)。
3. **TTS 语言**：当前默认使用的 Deepgram Aura 模型在英语发音上表现极佳，若主要使用中文，建议在 `config.py` 中配置 `OPENAI_API_KEY` 以启用更自然的中文 TTS。

---
*Built with ❤️ for immersive AI companionship.*
