import requests
from middleware import SillyTavernMiddleware
import logging

logging.basicConfig(level=logging.INFO)

# 初始化 middleware
mw = SillyTavernMiddleware(admin_password="123456") # 假设 ecosystem.config.js 里是 123456

# 模拟获取 token (这一步会登录并获取 cookie)
# 这里用一个已存在的 telegram_id，或者新的
tg_id = 7974510481 # 从日志里看到的你的 ID
token = mw.get_st_token(tg_id, "TestUser")

print(f"Token: {token}")

# 构造 headers
headers = {
    "Cookie": token,
    "Content-Type": "application/json"
}

# 1. 尝试获取角色列表
try:
    resp = requests.get("http://127.0.0.1:8000/api/characters", headers=headers)
    print(f"Get Characters Status: {resp.status_code}")
    if resp.status_code == 200:
        chars = resp.json()
        print(f"Found {len(chars)} characters")
        for c in chars[:3]:
            print(f" - {c.get('name')} ({c.get('avatar')})")
    else:
        print(resp.text)
except Exception as e:
    print(f"Error getting characters: {e}")

# 2. 尝试获取当前激活的角色 (如果有这个 API)
# 通常是 GET /api/settings/current_character 或者类似的，或者在 settings.json 里
# SillyTavern 的状态通常是保存在服务端的 session 里的吗？还是客户端维护？
# 如果是客户端维护，那我们只是切换了 "Telegram Adapter" 认为的角色。
# 但 ChatBridge 是把请求发给 ST，ST 会根据当前加载的角色来回复。
# 所以我们必须告诉 ST "现在给这个用户加载这个角色"。

# 尝试 POST /api/characters/load
# payload: { "avatar": "filename.png" }
