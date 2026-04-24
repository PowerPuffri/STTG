# 系统架构与核心技术实现 (Architecture & Technical Details)

本项目（Nuomi Circuit）是一个基于 Telegram 和大语言模型的复杂 AI 角色扮演系统。它不仅提供了多模态的交互能力（文本、语音、图像），还在底层解决了一系列复杂的系统集成与异步通信难题。

## 一、系统架构概览

本项目采用了**模块化微服务**的设计思想，通过自定义中间件和 WebSocket 代理层，实现了 Telegram 客户端与底层 AI 引擎（SillyTavern 及各大模型 API）的无缝集成。

```mermaid
graph TD
    User((Telegram 用户)) <--> |长轮询/Webhook| Adapter[Telegram Adapter\n(状态机管理 & 消息解析)]
    
    subgraph Core System [核心业务系统]
        Adapter <--> |HTTP / WebSocket| Middleware[Middleware 层\n(多租户路由 & 凭证管理)]
        Middleware <--> |API 代理| ChatBridge[ChatBridge Forwarder\n(异步并发处理 & 流式传输)]
    end
    
    subgraph AI Engine [底层 AI 与多模态引擎]
        ChatBridge <--> |WebSocket| ST[SillyTavern\n(AI 聊天引擎与上下文管理)]
        ST <--> |API| LLM[大语言模型 API\n(Zhipu GLM-4 / Claude 等)]
        
        Adapter -.-> |音频处理| ASR[Deepgram ASR\n(语音识别与情绪提取)]
        Adapter -.-> |音频生成| TTS[Deepgram Aura / OpenAI TTS\n(语音合成)]
        Adapter -.-> |图像生成| ImageEngine[GLM-Image\n(场景图片生成)]
    end
```

### 核心组件职责
- **Telegram Adapter (`telegram_adapter.py`)**: 负责轮询 Telegram 消息，解析多模态输入（文本、语音），并管理每个用户的独立状态机（如 `welcome`, `character_select`, `chat` 等）。
- **Middleware (`middleware.py`)**: 负责 Telegram 用户与底层 AI 系统（SillyTavern）账户之间的映射关系。动态处理 CSRF Token，管理多租户角色数据的同步与隔离。
- **ChatBridge Forwarder**: 作为 WebSocket 转发器和 API 代理层，负责将同步的 HTTP 请求转化为长连接的 WebSocket 交互，并监听底层 AI 引擎的流式响应（Stream），从而实现极低的延迟。

---

## 二、攻克的核心技术挑战

在项目开发过程中，解决了一系列涉及异步网络通信、协议转换和分布式状态管理的复杂问题：

### 1. 复杂网络环境下的高可用 API 代理
**挑战**：Telegram API 及部分海外大模型 API 存在严格的网络访问限制，且长连接（如流式生成或 WebSocket）在代理环境下极易发生 `SSL EOF` 断流。
**解决方案**：
- 实现了一套带有**指数退避重试机制**的请求封装。
- 采用局部代理硬编码与连接池复用的策略，同时在长连接场景下禁用严格 SSL 校验以提升隧道稳定性，确保流式对话在网络波动时能够平滑重连。

### 2. 同步 API 与异步 WebSocket 的协议桥接 (ChatBridge)
**挑战**：底层 AI 聊天引擎（SillyTavern）的原生 API 未针对第三方高并发调用进行优化，且生成回复时使用 WebSocket 进行流式推送，而 Telegram 机器人端期望获得类似于 OpenAI API 的标准同步/异步 HTTP 响应格式。
**解决方案**：
- 在开源项目 `ChatBridge_APIHijackForwarder.py` 的基础上进行深度改造，实现了一个 **WebSocket 到 HTTP 的桥接代理**。
- 利用 Python `asyncio.Future` 和 `asyncio.wait_for` 拦截 WebSocket 流式事件。
- 在 Node.js 扩展端 (`index.js`) 监听底层的 `MESSAGE_RECEIVED` 和 `GENERATION_ENDED` 事件，主动将最终结果或流式 Chunk 推送至桥接代理。
- 最终将结果重组封装为标准的 OpenAI API JSON 格式 (`{"choices": [{"message": {"content": "..."}}]}`) 供上层调用。

### 3. 多租户 (Multi-tenant) 隔离与 CSRF 安全机制
**挑战**：底层引擎需要针对不同的 Telegram 用户维护独立的对话历史、角色关系和记忆（Memory），但原系统是一个单体应用，并且对所有 API 接口启用了严格的 CSRF 保护。
**解决方案**：
- 设计了 `st_tg_mapping.db` SQLite 数据库记录用户映射。
- 在 `middleware.py` 中实现了**动态 CSRF 令牌获取机制**：通过 `Session` 对象先获取匿名 Token -> 执行自动登录 -> 获取带有签名的授权 Token -> 在后续所有 API 调用中注入 `X-CSRF-Token` 请求头。
- 为每个新注册的 Telegram 用户在底层自动初始化沙箱目录，实现物理级别的数据隔离。

### 4. 语音情绪识别与多模态流转
**挑战**：传统的 Voice-to-Text 丢失了用户的语气与情绪，导致 AI 伴侣的回复显得生硬。
**解决方案**：
- 集成了高性能 ASR（如 Deepgram），并在语音转文字的 Pipeline 中加入了一个微型提示词注入环节。
- 引擎能够提取出语气的潜在信息（如“急促地”、“带着笑意”），并将其作为隐式 Context 拼接到用户的消息中，使大模型能够生成更加符合当前情绪的拟人化回复。

---

## 三、系统状态机设计

机器人的核心交互依赖于一套严密的有限状态机（FSM），确保用户体验的连贯性：

| 用户状态 (State) | 触发条件 | 系统行为 |
|----------------|---------|---------|
| `welcome` | 发送 `/start` 指令 | 初始化用户映射数据库，显示带有 "进入" 按钮的交互式欢迎界面 |
| `character_select` | 点击 "进入" 或发送 `/chars` | 拉取当前租户名下已授权的角色列表，展示多选菜单，标记语音专属角色 |
| `chat` | 选择特定角色后 | 读取对应角色的 `first_mes` (开场白)，建立 WebSocket 对话通道，接受多模态输入 |

通过这一套状态管理，系统能够优雅地处理并发用户的不同上下文，避免了上下文串联或指令冲突的问题。
