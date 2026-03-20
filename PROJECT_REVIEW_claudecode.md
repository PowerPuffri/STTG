# STTG 项目复盘文档

> 项目：Telegram Bot + SillyTavern 集成
> 时间：2025年1月底 - 2025年2月初
> 状态：基本功能可用

---

## 一、项目架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Telegram  │ ───> │ Telegram     │ ───> │   ChatBridge│
│    User     │      │   Adapter    │      │  Forwarder  │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                     │
                                                     ▼
                                           ┌─────────────────┐
                                           │  SillyTavern    │
                                           │  (AI Chat Engine)│
                                           └─────────────────┘
```

### 核心组件

| 组件 | 文件路径 | 功能 |
|------|---------|------|
| Telegram Adapter | `telegram_adapter.py` | 轮询Telegram消息，管理用户状态机 |
| Middleware | `middleware.py` | Telegram用户 ↔ SillyTavern账户映射 |
| ChatBridge Forwarder | `ChatBridge_APIHijackForwarder.py` | WebSocket转发，API代理 |
| ChatBridge Extension | `index.js` | SillyTavern浏览器扩展，WebSocket客户端 |
| SillyTavern | `/SillyTavern/` | AI聊天引擎本体 |

### 用户流程

```
/start → 欢迎界面(欢迎来到 Nuomi Circuit ～)
         ↓
    点击"进入"按钮
         ↓
    角色选择界面(显示可用角色列表)
         ↓
    选择角色 → 发送角色开场白 → 进入聊天模式
```

---

## 二、解决的问题记录

### 问题1：Telegram API无法访问（网络问题）

**现象**：
```
Failed to get updates: HTTPSConnectionPool(host='api.telegram.org', port=443): Max retries exceeded
```

**原因**：Telegram在中国被墙，直连API失败

**解决方案**：
1. 确认系统代理：V2rayU 运行在 `127.0.0.1:7897`
2. 在 `telegram_adapter.py` 中硬编码代理配置：
```python
def _get_proxies(self):
    return {
        'http': 'http://127.0.0.1:7897',
        'https': 'http://127.0.0.1:7897'
    }
```
3. 所有requests调用添加 `verify=False` 跳过SSL验证

---

### 问题2：ChatBridge返回格式不兼容

**现象**：
```python
# telegram_adapter期望的格式
{
  "choices": [{"message": {"content": "..."}}]
}

# 实际ChatBridge返回的格式
"直接返回字符串内容"
```

**原因**：ChatBridge直接转发SillyTavern响应，未包装OpenAI格式

**解决方案**：修改 `ChatBridge_APIHijackForwarder.py`：
```python
# 在handle_user_api中包装响应
content = await asyncio.wait_for(future, timeout=300.0)
openai_response = {
    "choices": [{
        "message": {
            "content": content,
            "role": "assistant"
        }
    }]
}
return web.json_response(openai_response)
```

---

### 问题3：角色列表获取失败（403 Forbidden）

**现象**：
```
Failed to get characters: Status 403 - Forbidden
```

**原因**：SillyTavern API需要CSRF Token，原代码未携带

**解决方案**：重写 `middleware.py` 的 `get_characters()` 方法：
```python
def get_characters(self, user_id, user_name):
    # 1. 创建新session获取CSRF
    session = requests.Session()
    csrf_token = self._get_csrf_token(session)

    # 2. 用用户凭证登录
    payload = {"handle": handle, "password": password}
    headers = self._get_headers(csrf)
    session.post(f"{self.base_url}/api/users/login", json=payload, headers=headers)

    # 3. 登录后再次获取CSRF
    csrf_token = self._get_csrf_token(session)

    # 4. 带CSRF请求角色列表
    headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf_token}
    response = session.post(f"{self.base_url}/api/characters/all", json={}, headers=headers)
```

---

### 问题4：角色切换后不显示开场白

**现象**：选择角色后ChatBridge日志显示切换成功，但Telegram没收到开场白消息

**原因**：
1. 角色开场白字段名不统一（`first_mes` vs `data.first_mes` vs `greeting`）
2. `get_character_greeting()` 直接读取数据库而非调用API

**解决方案**：修改为多字段检查：
```python
def get_character_greeting(self, character_name, user_id, user_name):
    characters = self.get_characters(user_id, user_name)  # 先获取完整角色数据
    for char in characters:
        if char.get('name') == character_name:
            # 1. Try 'first_mes' (Standard V2)
            if char.get('first_mes'):
                return char.get('first_mes')
            # 2. Try 'data.first_mes' (Nested V2)
            if char.get('data') and char.get('data').get('first_mes'):
                return char.get('data').get('first_mes')
            # 3. Fallback
            if char.get('greeting'):
                return char.get('greeting')
            return "你好～ (未找到开场白)"
```

---

### 问题5：AI响应不返回给Telegram

**现象**：SillyTavern生成回复，但Telegram收不到

**原因**：ChatBridge扩展未监听AI生成完成事件

**解决方案**：在 `index.js` 添加事件监听：
```javascript
// 监听流式生成结束事件
context.eventSource.on(context.eventTypes.MESSAGE_RECEIVED, (msgId) => {
    if (currentRequestId) {
        const lastMsg = context.chat[context.chat.length - 1];
        if (lastMsg && !lastMsg.is_user) {
            sendResponseToForwarder(lastMsg.mes);
        }
    }
});

// 备用：监听生成结束事件
context.eventSource.on(context.eventTypes.GENERATION_ENDED, () => {
    if (currentRequestId) {
        const lastMsg = context.chat[context.chat.length - 1];
        if (lastMsg && !lastMsg.is_user) {
            sendResponseToForwarder(lastMsg.mes);
        }
    }
});
```

---

### 问题6：ChatBridge超时导致502错误

**现象**：
```
ChatBridge error: 502 -
```

**原因**：SillyTavern AI生成超过60秒，但ChatBridge默认超时设置为60秒

**解决方案**：增加超时时间
```python
# ChatBridge_APIHijackForwarder.py
response = await asyncio.wait_for(future, timeout=300.0)  # 改为300秒
```

---

### 问题7：SSL EOF错误（间歇性）

**现象**：
```
SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol'))
```

**原因**：代理与Telegram API之间的SSL握手不稳定

**解决方案**：
1. 添加 `verify=False` 跳过SSL验证
2. 禁用SSL警告：`urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)`
3. 接受这是代理环境的已知限制，偶尔重试即可

---

## 三、技术要点总结

### 1. SillyTavern多用户架构
- 每个Telegram用户自动对应一个SillyTavern账户（`tg-{telegram_id}`）
- 密码随机生成并存储在SQLite数据库
- 角色文件从 `default-user/characters` 同步到各用户目录

### 2. CSRF处理机制
- SillyTavern API要求CSRF Token
- Token需要先获取 → 登录 → 再次获取
- Session cookies必须包含签名

### 3. WebSocket通信协议
```javascript
// 用户请求 → SillyTavern
{"type": "user_request", "id": "uuid", "user_id": "123", "content": {...}}

// 切换角色
{"type": "switch_character", "character_name": "角色名"}

// SillyTavern响应 → Forwarder
{"type": "st_response", "id": "uuid", "content": "AI回复内容"}
```

### 4. 状态机设计
| 状态 | 说明 |
|------|------|
| `welcome` | 初始状态，显示欢迎界面 |
| `character_select` | 角色选择状态 |
| `chat` | 聊天状态 |

---

## 四、待优化项

1. **SSL EOF错误**：需要更稳定的代理方案或重试机制
2. **超时设置**：300秒超时可能过长，考虑流式响应
3. **错误处理**：增加更友好的用户错误提示
4. **订阅系统**：`check_subscription()` 目前是占位实现
5. **长轮询优化**：考虑改用Webhook模式

---

## 五、启动命令

```bash
# 启动所有服务
cd ~/Desktop/STTG
bash start_prod.sh

# 查看日志
pm2 logs --lines 100

# 重启服务
pm2 restart all
```

---

## 六、重要配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Telegram Bot Token | `8528099425:AAFHxGGIHMSJkAHDBDXKJ9eim68wziF_rQQ` | @NuomiCircuit_bot |
| 代理地址 | `http://127.0.0.1:7897` | V2rayU |
| SillyTavern端口 | 8000 | 本地访问 |
| ChatBridge WebSocket | 8001 | 内部通信 |
| ChatBridge ST API | 8002 | SillyTavern代理 |
| ChatBridge User API | 8003 | Telegram接入 |
| 数据库文件 | `st_tg_mapping.db` | 用户映射存储 |

---

## 七、文件清单

```
STTG/
├── telegram_adapter.py          # Telegram Bot主逻辑
├── middleware.py                # SillyTavern中间件
├── start_prod.sh                # PM2启动脚本
├── st_tg_mapping.db            # SQLite数据库
├── logs/                        # 日志目录
│   ├── bot-error.log
│   ├── bridge-error.log
│   └── st-out.log
└── SillyTavern/
    └── public/scripts/extensions/third-party/SillyTavern-Extension-ChatBridge/
        ├── index.js             # 浏览器扩展
        ├── ChatBridge_APIHijackForwarder.py  # Python服务器
        └── settings.json        # 配置文件
```

---

*文档生成时间：2025年2月5日*
