from zhipuai import AsyncZhipuAI
import asyncio
import os

api_key = "702410a536764a848acfce74f143bde4.MnDcPltUO1y3zHDd"

async def test_async():
    try:
        client = AsyncZhipuAI(api_key=api_key)
        print("AsyncZhipuAI class exists!")
        response = await client.chat.completions.create(
            model="glm-4-plus",
            messages=[{"role": "user", "content": "hello"}],
            stream=True
        )
        async for chunk in response:
            print(chunk.choices[0].delta.content, end="")
    except Exception as e:
        print(f"Async failed or not found: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_async())
    except ImportError:
        print("Could not import AsyncZhipuAI")
