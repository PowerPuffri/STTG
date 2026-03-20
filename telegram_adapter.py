import requests
import time
import logging
import json
import os
from middleware import SillyTavernMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TelegramAdapter")

class TelegramAdapter:
    def __init__(self, bot_token, chatbridge_url="http://127.0.0.1:5000/v1/chat/completions", admin_pass=""):
        self.bot_token = bot_token
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.chatbridge_url = chatbridge_url
        self.middleware = SillyTavernMiddleware(admin_password=admin_pass)
        self.last_update_id = 0
        self.proxies = self._get_proxies()
        logger.info(f"Using proxy: {self.proxies.get('https') if self.proxies else 'None (direct connection)'}")

    def _get_proxies(self):
        """Get proxy settings from environment variables."""
        # Force local proxy for testing if auto-detection fails
        # You can remove the hardcoded values later
        return {
            'http': 'http://127.0.0.1:7897',
            'https': 'http://127.0.0.1:7897'
        }
        
        # http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        # https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        # all_proxy = os.environ.get('ALL_PROXY') or os.environ.get('all_proxy')

        # proxy = https_proxy or http_proxy or all_proxy
        # if proxy:
        #     return {'http': proxy, 'https': proxy}
        # return None

    def get_updates(self):
        """Poll Telegram for updates."""
        try:
            params = {"offset": self.last_update_id + 1, "timeout": 30}
            # Added verify=False to bypass SSL errors with proxy
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(f"{self.api_base}/getUpdates", params=params, timeout=35, proxies=self.proxies, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get updates: {e}")
            return None

    def send_message(self, chat_id, text, reply_markup=None):
        """Send message back to Telegram with optional inline keyboard."""
        try:
            payload = {"chat_id": chat_id, "text": text}
            if reply_markup:
                payload["reply_markup"] = reply_markup
            requests.post(f"{self.api_base}/sendMessage", json=payload, proxies=self.proxies, verify=False)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def send_welcome(self, chat_id):
        """Send welcome message with Enter button."""
        text = "欢迎来到 Nuomi Circuit ～"
        reply_markup = {
            "inline_keyboard": [[
                {"text": "进入", "callback_data": "enter"}
            ]]
        }
        self.send_message(chat_id, text, reply_markup)

    def send_character_select(self, chat_id, user_id, user_name):
        """Send character selection menu."""
        chars = self.middleware.get_characters(user_id, user_name)
        if not chars:
            self.send_message(chat_id, "暂无可用角色，请联系管理员。")
            return

        # Build inline keyboard with character buttons
        buttons = []
        for char in chars[:20]:  # Limit to 20 characters
            name = char.get('name', 'Unknown')
            buttons.append([{"text": name, "callback_data": f"char_{name}"}])

        reply_markup = {"inline_keyboard": buttons}
        self.send_message(chat_id, "请选择角色：", reply_markup)

    def switch_character(self, character_name, user_id, user_name, chat_id):
        """Switch to a character and send greeting."""
        logger.info(f"switch_character called: name={character_name}, user={user_id}")

        # Send switch command to ChatBridge
        try:
            base_url = self.chatbridge_url.split('/v1/')[0]
            command_url = f"{base_url}/v1/command"

            payload = {
                "type": "switch_character",
                "character_name": character_name
            }
            requests.post(command_url, json=payload, proxies=self.proxies, verify=False)
            logger.info(f"Switched to character: {character_name}")
        except Exception as e:
            logger.error(f"Failed to switch character: {e}")

        # Update user state
        self.middleware.set_user_state(user_id, 'chat', character_name)

        # Get and send character greeting
        try:
            greeting = self.middleware.get_character_greeting(character_name, user_id, user_name)
            logger.info(f"Got greeting: {greeting[:50] if greeting else 'None'}...")
            self.send_message(chat_id, f"✅ 已切换到 **{character_name}**\n\n{greeting}")
        except Exception as e:
            logger.error(f"Failed to get greeting or send message: {e}", exc_info=True)

    def check_subscription(self, user_id):
        """Check if user has valid subscription (placeholder for future)."""
        # TODO: Implement subscription check
        return True  # Always allow for now

    def process_message(self, message):
        """Process a single message from Telegram."""
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        user_name = message.get("from", {}).get("first_name", "Unknown")
        text = message.get("text", "")

        if not chat_id:
            return

        logger.info(f"Received message from {user_name} ({user_id}): {text}")

        # Get user state
        user_state = self.middleware.get_user_state(user_id)
        current_state = user_state['state']
        logger.info(f"User {user_id} current state: {current_state}")

        # Handle /start command - always show welcome
        if text and text.strip() == '/start':
            self.middleware.set_user_state(user_id, 'welcome')
            self.send_welcome(chat_id)
            return

        # Handle /reset command - reset to welcome
        if text and text.strip() == '/reset':
            self.middleware.set_user_state(user_id, 'welcome')
            self.send_welcome(chat_id)
            return

        # State machine
        if current_state == 'welcome':
            # Any message in welcome state shows welcome screen
            self.send_welcome(chat_id)

        elif current_state == 'character_select':
            # Should be handled by callback, but if user types, show menu again
            self.send_character_select(chat_id, user_id, user_name)

        elif current_state == 'chat':
            # Check subscription
            if not self.check_subscription(user_id):
                self.send_message(chat_id, "❌ 订阅已过期，请续费后继续使用。")
                return

            # Normal chat - forward to AI
            if not text:
                return

            self.forward_to_ai(chat_id, user_id, user_name, text)

    def forward_to_ai(self, chat_id, user_id, user_name, text):
        """Forward user message to ChatBridge/SillyTavern."""
        try:
            st_token = self.middleware.get_st_token(user_id, user_name)
            logger.info(f"Obtained ST Token for {user_id}: {st_token[:20]}...")
        except Exception as e:
            logger.error(f"Failed to get ST token: {e}")
            self.send_message(chat_id, "Error: Could not link to SillyTavern account.")
            return

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": text}],
            "user_id": str(user_id),
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {st_token}",
            "Cookie": st_token,
            "X-User-ID": str(user_id)
        }

        try:
            logger.info(f"Forwarding to ChatBridge: {self.chatbridge_url}")
            # Increase timeout to 300s for slow AI responses (SillyTavern generation can be slow)
            response = requests.post(self.chatbridge_url, json=payload, headers=headers, proxies=self.proxies, verify=False, timeout=300)

            if response.status_code == 200:
                result = response.json()

                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except:
                        pass

                if isinstance(result, dict):
                    choices = result.get("choices", [])
                    if choices and isinstance(choices, list):
                        reply_text = choices[0].get("message", {}).get("content", "")
                    else:
                        reply_text = result.get("content", "") or str(result)
                else:
                    reply_text = str(result)

                if reply_text:
                    self.send_message(chat_id, reply_text)
                else:
                    logger.warning(f"Empty response content from ChatBridge. Raw result: {result}")
            else:
                logger.error(f"ChatBridge error: {response.status_code} - {response.text}")
                if response.status_code == 503:
                    self.send_message(chat_id, "⚠️ 错误: SillyTavern 未连接。\n请在浏览器中刷新 SillyTavern 页面以重新连接插件。")
                elif response.status_code == 504:
                    self.send_message(chat_id, "⚠️ 错误: AI 生成超时。\n请尝试重新发送，或检查 SillyTavern 是否正在生成。")
                else:
                    self.send_message(chat_id, f"Error: Failed to get response from AI (Status {response.status_code}).")

        except requests.exceptions.Timeout:
            logger.error("Request to ChatBridge timed out")
            self.send_message(chat_id, "Error: Connection to AI timed out (wait > 5min).")
        except Exception as e:
            logger.error(f"Failed to contact ChatBridge: {e}", exc_info=True)
            self.send_message(chat_id, "Error: Connection to AI backend failed.")

    def process_callback_query(self, callback_query):
        """Process inline button callback queries."""
        query_id = callback_query.get("id")
        chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
        user_id = callback_query.get("from", {}).get("id")
        user_name = callback_query.get("from", {}).get("first_name", "Unknown")
        data = callback_query.get("data", "")

        # Answer the callback query to remove loading state
        requests.post(f"{self.api_base}/answerCallbackQuery",
                     json={"callback_query_id": query_id},
                     proxies=self.proxies, verify=False)

        logger.info(f"Callback from {user_name} ({user_id}): {data}")

        if data == "enter":
            # Check subscription before proceeding
            if not self.check_subscription(user_id):
                self.send_message(chat_id, "❌ 订阅已过期，请续费后继续使用。")
                return

            self.middleware.set_user_state(user_id, 'character_select')
            self.send_character_select(chat_id, user_id, user_name)

        elif data.startswith("char_"):
            character_name = data[5:]  # Remove "char_" prefix
            self.switch_character(character_name, user_id, user_name, chat_id)

    def run(self):
        logger.info("Telegram Adapter started...")
        while True:
            updates = self.get_updates()
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    self.last_update_id = update["update_id"]
                    if "message" in update:
                        self.process_message(update["message"])
                    elif "callback_query" in update:
                        self.process_callback_query(update["callback_query"])
            time.sleep(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="Telegram Bot Token", required=True)
    parser.add_argument("--admin_pass", help="SillyTavern Admin Password", default="")
    parser.add_argument("--chatbridge_url", help="ChatBridge User API URL", default="http://127.0.0.1:8003/v1/chat/completions")
    
    args = parser.parse_args()
    
    adapter = TelegramAdapter(args.token, args.chatbridge_url, args.admin_pass)
    adapter.run()
