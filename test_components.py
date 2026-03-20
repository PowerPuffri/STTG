import asyncio
import os
import logging
from st_client import STClient
from tts_client import TTSClient
# from asr_client import ASRClient # Skip ASR for now as it needs valid audio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_llm():
    print("\n--- Testing LLM (STClient) ---")
    client = STClient()
    payload = {
        "model": "glm-4-plus",
        "messages": [{"role": "user", "content": "Say 'LLM is working' in 3 words."}],
        "stream": True
    }
    
    print("Generating response...")
    full_text = ""
    async for chunk in client.generate_response(payload):
        print(chunk, end="", flush=True)
        full_text += chunk
    print("\n\nLLM Check:", "PASS" if "working" in full_text or "LLM" in full_text else "FAIL")

async def test_tts():
    print("\n--- Testing TTS (TTSClient) ---")
    client = TTSClient()
    text = "Testing text to speech system."
    print(f"Generating audio for: '{text}'")
    
    audio_data = await client.generate_speech(text)
    
    if audio_data and len(audio_data) > 100:
        print(f"Received {len(audio_data)} bytes of audio.")
        print("TTS Check: PASS")
    else:
        print("Received no audio or too small.")
        print("TTS Check: FAIL")

async def main():
    await test_llm()
    await test_tts()

if __name__ == "__main__":
    asyncio.run(main())
