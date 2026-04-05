import os
from zhipuai import ZhipuAI

api_key = "702410a536764a848acfce74f143bde4.MnDcPltUO1y3zHDd"
client = ZhipuAI(api_key=api_key)

models_to_test = ["glm-4", "glm-4-flash", "glm-4-air", "glm-4-plus", "glm-4.7"]

print(f"Testing API Key: {api_key[:10]}...")

for model in models_to_test:
    print(f"Testing model: {model} ...", end=" ")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10
        )
        print("SUCCESS")
        print(response.choices[0].message.content)
        break # Stop at first working model
    except Exception as e:
        print(f"FAILED: {e}")
