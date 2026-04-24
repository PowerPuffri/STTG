<h1 align="center">Nuomi Circuit</h1>

<p align="center">
  <strong>Multi-modal AI Chat System with Full-duplex Voice & Context-aware Vision</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue.svg" />
  <img alt="Telegram" src="https://img.shields.io/badge/Telegram-Bot%20API-0088cc.svg" />
  <img alt="LLM" src="https://img.shields.io/badge/LLM-Zhipu%20GLM--4.7-orange.svg" />
  <img alt="ASR" src="https://img.shields.io/badge/ASR-Deepgram-purple.svg" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green.svg" />
</p>

<hr />

## 📖 项目简介

**Nuomi Circuit** 是一款基于 Telegram 的高性能多模态 AI 对话系统。本项目深度整合了大语言模型（LLM）、流式语音识别（ASR）、高保真语音合成（TTS）以及上下文驱动的图像生成技术，为用户提供一个稳定、极速且多模态交互的 AI 聊天环境。

在架构层面，本项目通过引入并深度定制开源社区的 `ChatBridge` 扩展（SillyTavern-Extension-ChatBridge），打通了 Telegram 与底层 AI 聊天引擎（SillyTavern）之间的异步通信链路。它不仅解决了复杂的网络并发问题，还通过自定义的中间件实现了完善的多租户（Multi-tenant）物理隔离。

## ✨ 核心特性与技术挑战

- 🎭 **多轮角色对话引擎**：全面兼容 SillyTavern V2 规范，支持解析复杂的设定档、预设记忆与动态世界观。
  - **技术挑战与解决**：通过构建标准化的中间件层，解决了异构 AI 引擎之间的数据结构对齐与兼容性问题。
- ⚡ **微秒级流式响应**：基于 `asyncio` 和 `WebSocket` 的全链路异步设计。
  - **技术挑战与解决**：将底层单体 AI 引擎的流式事件转化为标准 HTTP 同步/异步响应，彻底解决了代理环境下的长连接断流、高延迟与并发冲突。
- 🗣️ **双向 Voice-to-Voice (全双工语音)**：
  - **基于 Prompt Engineering 的细粒度语气识别**：不仅能精准转录语音，更能通过微提示词工程提取用户的**情绪标签**，并作为隐式上下文注入给大模型。
    - **技术挑战与解决**：克服了传统 ASR 丢失非文本意图的局限，提升了多模态对话的上下文感知能力。
  - **动态情感 TTS**：对接高质量的 Deepgram Aura 和 OpenAI TTS。
    - **技术挑战与解决**：实现跨引擎的高并发音频流媒体调度与毫秒级延迟处理。
- 📸 **上下文驱动的视觉生成**：基于对话历史和角色外观设定，自动生成符合当前场景的图像。
  - **技术挑战与解决**：设计了多模态 Prompt 组装与降维工作流，确保文本大模型输出的场景描述能精准转化为视觉生成引擎（如 GLM-Image）可执行的绘图指令。
- 🧠 **长上下文记忆管理**：内置智能滑动窗口与摘要压缩机制。
  - **技术挑战与解决**：彻底解决了长文本对话导致的 API Token 超限与关键记忆遗忘问题，保障了系统在高频多轮交互下的稳定性。
- 🛡️ **分布式多租户隔离**：支持多用户并发操作。
  - **技术挑战与解决**：基于 SQLite 设计了轻量级的会话状态机（State Machine）管理与数据隔离，配合动态 CSRF 令牌获取机制，实现了多并发场景下的物理级数据安全隔离。

## 🛠️ 技术栈与底层选型

- **核心开发语言**: Python 3.10+, Node.js (桥接服务)
- **网络与并发**: `asyncio`, `aiohttp`, WebSocket
- **机器人框架**: `python-telegram-bot` (v20+)
- **AI / 模型驱动**: 
  - 核心推理层：Zhipu AI (GLM-4.7)
  - 视觉生成层：GLM-Image
  - 语音基建层：Deepgram SDK / OpenAI
- **数据持久化与状态隔离**: SQLite3
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
pm2 start deploy/ecosystem.config.js
```

## 🎮 使用指南 (Telegram 端)

在 Telegram 中找到您的机器人，输入以下指令开始交互：

- `/start` - 初始化系统并分配多租户隔离沙箱
- `/chars` - 呼出模型选择面板 (标记有 🎙️ 的为支持全双工语音的模型接口)
- `/img [提示词]` - 根据提示词实时生成上下文驱动的视觉图像
- `/subscribe` - 查看当前的资源配额与并发限制状态

## 📁 核心目录结构

```text
STTG/
├── telegram_bot.py       # Telegram 机器人主循环与指令路由 (系统主入口)
├── app/                  # 核心业务逻辑包
│   ├── clients/          # 所有的 AI 大模型与多模态客户端
│   ├── core/             # 中间件、多租户映射与核心引擎
│   └── utils/            # 角色配置解析等工具类
├── config.py             # 全局配置文件
├── deploy/               # 运维与服务部署脚本
├── docs/                 # 项目文档与架构设计图
├── scripts/              # 运维与管理工具脚本
├── tests/                # 单元与集成测试
└── 角色卡/                # 设定档与数据模板
```

## 🤝 贡献与反馈

如果您对如何改进本项目的网络桥接层、增加新的 TTS 引擎或提升长上下文的记忆压缩算法有任何建议，欢迎提交 Pull Request 或 Issue。

## 📜 许可证

本项目基于 [MIT License](LICENSE) 开源，请在遵守相关大语言模型及第三方 API 使用协议的前提下进行二次开发。

---
*Crafted with engineering rigor for multi-modal AI systems.*