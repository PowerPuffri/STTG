# Nuomi Circuit 项目技术文档 (Technical Documentation)

本目录包含了 Nuomi Circuit 项目的核心架构设计与技术方案白皮书。这些文档详细记录了在开发过程中所面临的技术挑战、系统架构演进以及具体的解决方案，旨在为面试官、技术评审或二次开发者提供深度的项目剖析。

## 📑 文档索引

### 1. [系统架构与核心技术实现 (Architecture & Technical Details)](./architecture.md)
**内容摘要**：
- 系统的整体微服务架构图（基于 Mermaid）。
- Telegram 与底层大模型及多模态引擎的数据流向。
- 重点攻克的技术难点：包括异步网络环境下的 WebSocket 桥接（基于开源 `ChatBridge` 扩展的深度改造）、长连接的 SSL 断流处理、以及多租户（Multi-tenant）环境下的物理隔离与动态 CSRF 安全机制。
- 核心状态机（State Machine）的设计逻辑。

### 2. [语音交互与情绪识别架构设计 (Voice Interaction & Emotion Recognition Design)](./voice_interaction_design.md)
**内容摘要**：
- 全双工语音（Voice-to-Voice）交互链路的设计与选型。
- 语音识别（ASR）引擎的性能评估与落地策略（Groq Whisper vs. OpenAI）。
- 基于大语言模型（LLM）的多模态隐式情绪嗅探机制的设计思路。
- 语音数据的端到端流转流程。

---
*这些文档不仅展示了项目的功能完备性，更体现了在面对复杂系统集成、异步通信及并发状态管理时的工程化思考与解决问题的方法论。*
