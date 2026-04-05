<h1 align="center">Nuomi Circuit</h1>

<p align="center">
  <strong>一个功能强大的多模态 AI 角色扮演 Telegram 伴侣机器人</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue.svg" />
  <img alt="Telegram" src="https://img.shields.io/badge/Telegram-Bot%20API-0088cc.svg" />
  <img alt="LLM" src="https://img.shields.io/badge/LLM-Zhipu%20GLM--4-orange.svg" />
  <img alt="ASR" src="https://img.shields.io/badge/ASR-Deepgram-purple.svg" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green.svg" />
</p>

<hr />

## 📖 项目简介

**Nuomi Circuit** 是一款基于 Telegram 的高性能多模态 AI 伴侣系统。该项目将大语言模型（LLM）、流式语音识别（ASR）、高保真语音合成（TTS）以及图像生成（Text-to-Image）技术进行深度整合，为用户提供沉浸式的全双工角色扮演体验。

本项目原生支持解析 **SillyTavern** 标准格式的角色卡（JSON / PNG），通过自研的 `ChatBridge` 实现了异步状态下的微秒级消息投递，并突破了 Telegram API 在国内外的网络与流式通讯限制。

## ✨ 核心特性

- 🎭 **深度角色扮演引擎**：全面兼容 SillyTavern V2 角色规范，支持解析复杂的角色设定档、预设记忆与动态世界观。
- ⚡ **微秒级流式响应**：基于 `asyncio` 和 `WebSocket` 的全链路异步设计，实现极低延迟的逐字流式回复，极大提升了对话的拟真感。
- 🗣️ **双向 Voice-to-Voice (全双工语音)**：
  - **情感捕捉 ASR**：不仅能精准识别用户的语音消息，更能通过微提示词工程捕捉用户的**语气与情绪**，生成情感一致的回复。
  - **动态情感 TTS**：对接高质量的 Deepgram Aura 和 OpenAI TTS，根据上下文的张力动态调整角色的发声情绪。
- 📸 **剧情驱动的图像生成**：内置多模态工作流，基于当前聊天的上下文剧情和角色外观设定，AI 可自动“自拍”并生成高质量的场景照片，推动剧情发展。
- 🧠 **长上下文记忆管理**：内置智能滑动窗口与摘要压缩机制，彻底解决长文本对话导致的 API 报错与关键记忆遗忘问题。
- 🛡️ **分布式多租户隔离**：支持多用户并发操作，每个用户的角色数据、聊天历史与状态机完全隔离。

## 🛠️ 技术栈与底层选型

- **核心开发语言**: Python 3.10+, Node.js (桥接服务)
- **网络与并发**: `asyncio`, `aiohttp`, WebSocket
- **机器人框架**: `python-telegram-bot` (v20+)
- **AI / 模型驱动**: 
  - 核心大脑：Zhipu AI (GLM-4.7)
  - 视觉引擎：GLM-Image
  - 语音基建：Deepgram SDK / OpenAI
- **数据持久化**: SQLite3
- **进程守护与管理**: PM2

> **架构与技术细节探讨**：关于 WebSocket 桥接、多租户 CSRF 突破机制以及状态机的详细设计，请参阅 📄 [系统架构与技术白皮书](./docs/architecture.md)。

---

## 🚀 快速部署与运行

### 1. 环境依赖准备
请确保您的服务器已安装 Python 3.10+、Node.js 以及 PM2。

```bash
# 克隆仓库
git clone https://github.com/yourusername/NuomiCircuit.git
cd NuomiCircuit

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
系统采用严格的环境变量与配置文件分离策略。

```bash
cp config.example.py config.py
```
使用文本编辑器打开 `config.py`，并填入以下凭证：
- `BOT_TOKEN`: Telegram 机器人 Token (通过 `@BotFather` 申请)
- `ADMIN_ID`: 管理员的 Telegram ID
- `LLM_API_KEY`: 大语言模型 API 密钥
- `DEEPGRAM_API_KEY`: Deepgram 语音服务密钥

### 3. 导入设定档
将 SillyTavern 格式的图片角色卡（`.png`）或数据文件（`.json`）放置在根目录下的 `角色卡/` 文件夹中。系统启动时会自动扫描、解析并建立本地索引。

### 4. 启动服务集群
我们建议使用 PM2 启动项目以获得自动重启和日志切分能力：

```bash
# 启动机器人主程序及内部桥接服务
pm2 start telegram_bot.py --interpreter python3 --name nuomi-bot
```

## 🎮 使用指南 (Telegram 端)

在 Telegram 中找到您的机器人，输入以下指令开始交互：

- `/start` - 初始化系统并注册您的专属数字身份
- `/chars` - 呼出角色选择面板 (标记有 🎙️ 的为支持全双工语音的专属角色)
- `/img [提示词]` - (高级功能) 根据提示词要求角色实时生成场景照片
- `/subscribe` - 查看当前的资源配额与对话限制状态

## 📁 核心目录结构

```text
STTG/
├── telegram_bot.py       # Telegram 机器人主循环与指令路由
├── st_client.py          # 异步大语言模型 API 客户端 (流式传输)
├── tts_client.py         # 语音合成客户端 (支持多底层切换)
├── asr_client.py         # 语音识别客户端 (附带情绪特征提取)
├── image_client.py       # 图像生成与处理客户端
├── middleware.py         # 多租户管理与 SillyTavern API 中间件
├── character_manager.py  # 角色卡解析、格式校验与状态机管理
├── database.py           # 轻量级 SQLite 用户会话与额度管理
├── docs/                 # 项目文档与架构设计图
├── 角色卡/                # 角色卡原始文件存放目录
└── templates/            # 经系统解析后序列化的标准角色模板
```

## 🤝 贡献与反馈

如果您对如何改进本项目的网络桥接层、增加新的 TTS 引擎或提升长上下文的记忆压缩算法有任何建议，欢迎提交 Pull Request 或 Issue。

## 📜 许可证

本项目基于 [MIT License](LICENSE) 开源，请在遵守相关大语言模型及第三方 API 使用协议的前提下进行二次开发。

---
*Crafted with passion for the ultimate AI interactive experience.*
