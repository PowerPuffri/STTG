import logging
import copy
import config
import asyncio
import queue
from zhipuai import ZhipuAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class STClient:
    """
    Client for interacting with LLM APIs (ZhipuAI).
    Handles prompt construction and request sending.
    """
    
    def __init__(self, api_base_url=None, api_key=None):
        # We don't use api_base_url for ZhipuAI SDK standard init unless strictly needed
        self.api_key = api_key or config.LLM_API_KEY
        # Initialize ZhipuAI client
        # It automatically handles token generation
        self.client = ZhipuAI(api_key=self.api_key)

    def construct_payload(self, char_data, chat_history, user_name="User", model=None):
        """
        Constructs the payload for the Chat Completion API.
        Combines character definitions (System Prompt) and chat history.
        """
        model = model or config.LLM_MODEL
        
        # 1. Extract Character Info
        # Handle V2 card structure (data might be nested)
        data = char_data.get('data', char_data)
        
        name = data.get('name', 'Assistant')
        description = data.get('description', '')
        personality = data.get('personality', '')
        scenario = data.get('scenario', '')
        mes_example = data.get('mes_example', '')
        
        # 3. Build System Prompt
        # This is a basic template. You can customize this significantly.
        system_prompt = f"""You are {name}.
        
Description:
{description}

Personality:
{personality}

Scenario:
{scenario}

Chat Examples:
{mes_example}

Instructions:
- Stay in character at all times.
- Write your response as {name}.
- Do not speak for {user_name}.
- **IMPORTANT**: You can choose to send an image (e.g., selfie, photo of surroundings) if the context requires it.
- **Protocol**: 
  - To reply with text, wrap your response in `<reply>...</reply>`.
  - To send an image, use `<image_prompt>...</image_prompt>` with a detailed visual description in English.
  - You can combine both. E.g., `<reply>Check this out!</reply><image_prompt>A photo of a sunset...</image_prompt>`
  - **Rules for Images**:
    - Only generate an `<image_prompt>` if the user EXPLICITLY asks for a picture OR if the visual context is extremely significant to the plot.
    - Do not spam images for every reply. Use sparingly.
- **Language**: Reply in the same language as the user's last message. If the user speaks Chinese, you MUST reply in Chinese.
"""
        
        # 3. Build Messages List
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 4. Append Chat History
        # Ensure history is in correct format
        for msg in chat_history:
            role = msg.get('role')
            content = msg.get('content')
            if role and content:
                # Map roles if necessary (e.g., if you store 'char' instead of 'assistant')
                if role == 'char': role = 'assistant'
                messages.append({"role": role, "content": content})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True, # Enable streaming by default
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        
        return payload

    async def generate_response(self, payload):
        """
        Async generator that wraps the synchronous SDK call in a thread.
        """
        model = payload.get('model')
        messages = payload.get('messages')
        temperature = payload.get('temperature', 0.7)
        max_tokens = payload.get('max_tokens', 1024)
        top_p = payload.get('top_p', 0.9)
        
        logger.info(f"Sending request to ZhipuAI with model {model} (Async Wrapper)")
        
        # Create a queue to communicate between thread and async generator
        q = asyncio.Queue()
        loop = asyncio.get_event_loop()
        
        def worker():
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p
                )
                
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        loop.call_soon_threadsafe(q.put_nowait, content)
                
                # Signal done
                loop.call_soon_threadsafe(q.put_nowait, None)
                
            except Exception as e:
                logger.error(f"Worker API Request Failed: {e}")
                loop.call_soon_threadsafe(q.put_nowait, f"[Error: {str(e)}]")
                loop.call_soon_threadsafe(q.put_nowait, None)

        # Start the worker thread
        loop.run_in_executor(None, worker)
        
        # Consume the queue
        while True:
            chunk = await q.get()
            if chunk is None:
                break
            yield chunk

if __name__ == "__main__":
    pass
