import os
import logging
import io
import asyncio
import httpx
from openai import AsyncOpenAI
import config

logger = logging.getLogger(__name__)

# Deepgram Aura Voices
# https://developers.deepgram.com/docs/tts-models
DEFAULT_VOICE_DEEPGRAM = "aura-asteria-en"

# OpenAI Voices
# alloy, echo, fable, onyx, nova, shimmer
DEFAULT_VOICE_OPENAI = "nova"

class TTSClient:
    """
    Text-to-Speech client supporting multiple providers.
    Priority: OpenAI > Deepgram
    """
    
    def __init__(self):
        self.provider = config.TTS_PROVIDER
        
        # 1. Initialize OpenAI
        self.openai_client = None
        if config.OPENAI_API_KEY:
            try:
                self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
                self.provider = "openai"
                logger.info("OpenAI TTS enabled.")
            except Exception as e:
                logger.error(f"OpenAI Init failed: {e}")

        # 2. Initialize Deepgram
        self.deepgram_key = config.DEEPGRAM_API_KEY
        self.deepgram_url = "https://api.deepgram.com/v1/speak"
        
        if not self.deepgram_key:
            logger.warning("Deepgram API Key missing!")

    async def generate_speech(self, text, voice_id=None):
        """
        Generate speech using the best available provider.
        """
        if not text or not text.strip():
            return None
            
        # Try OpenAI first if available
        if self.provider == "openai" and self.openai_client:
            return await self._generate_openai(text, voice_id)
            
        # Fallback to Deepgram
        return await self._generate_deepgram(text, voice_id)

    async def _generate_openai(self, text, voice_id=None):
        try:
            # Map "english" or "default" to specific OpenAI voices if needed
            voice = DEFAULT_VOICE_OPENAI
            if voice_id == "male":
                voice = "onyx"
            
            logger.info(f"Generating OpenAI TTS ({voice}) for: {text[:20]}...")
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            return response.content
        except Exception as e:
            logger.error(f"OpenAI TTS failed: {e}")
            logger.info("Falling back to Deepgram...")
            return await self._generate_deepgram(text, voice_id)

    async def _generate_deepgram(self, text, voice_id=None):
        try:
            # Determine model
            model = voice_id if voice_id and "aura" in voice_id else DEFAULT_VOICE_DEEPGRAM
            if voice_id == "english":
                model = "aura-asteria-en"
            
            url = f"{self.deepgram_url}?model={model}"
            headers = {
                "Authorization": f"Token {self.deepgram_key}",
                "Content-Type": "application/json"
            }
            payload = {"text": text}
            
            logger.info(f"Generating Deepgram TTS ({model}) for: {text[:20]}...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Deepgram TTS failed: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Deepgram TTS error: {e}")
            return None

# For testing
if __name__ == "__main__":
    async def test():
        client = TTSClient()
        print(f"Testing with provider: {client.provider}")
        audio = await client.generate_speech("Hello, I am Ray. Testing TTS switch.")
        if audio:
            with open("test_hybrid.mp3", "wb") as f:
                f.write(audio)
            print(f"Saved test_hybrid.mp3 ({len(audio)} bytes)")
        else:
            print("Failed")
    
    asyncio.run(test())
