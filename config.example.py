import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# --- Telegram Bot Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 123456789))

# --- LLM API Config (Zhipu AI GLM-4) ---
LLM_API_URL = os.getenv("LLM_API_URL", "https://open.bigmodel.cn/api/paas/v4")
LLM_API_KEY = os.getenv("LLM_API_KEY", "YOUR_ZHIPU_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-plus") 

# --- Image Generation Config (Zhipu AI / GLM-Image) ---
# Provider options: "zhipu", "novita", "sd_webui", "mock"
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "zhipu") 
IMAGE_API_URL = os.getenv("IMAGE_API_URL", "https://open.bigmodel.cn/api/paas/v4/images/generations")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "YOUR_ZHIPU_IMAGE_API_KEY")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "glm-image") # User specified model

# --- TTS Config ---
# Supported providers: "deepgram", "openai", "elevenlabs"
# Default is "deepgram" as it's included in ASR key.
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "deepgram")

# Deepgram (Included, works well for English)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "YOUR_DEEPGRAM_API_KEY")

# OpenAI (Optional, BEST for Chinese/Multilingual)
# Get key here: https://platform.openai.com/api-keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") 

# ElevenLabs (Optional, BEST for Character Voices)
# Get key here: https://elevenlabs.io/
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")



# --- Business Logic ---
DAILY_MSG_LIMIT = 30
