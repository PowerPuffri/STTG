import asyncio
import httpx
import logging
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = config.DEEPGRAM_API_KEY

async def test_deepgram_chinese():
    url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Test Chinese text
    payload = {
        "text": "你好，我是Ray。这是一段中文语音测试。"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                with open("deepgram_cn_test.mp3", "wb") as f:
                    f.write(response.content)
                logger.info(f"Success! Saved deepgram_cn_test.mp3 ({len(response.content)} bytes)")
                return True
            else:
                logger.error(f"Failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_deepgram_chinese())
