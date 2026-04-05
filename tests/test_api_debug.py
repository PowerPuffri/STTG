import requests
import json
import os

# Config from config.py
LLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
# Using the key from config.py
# LLM_API_KEY = "702410a536764a848acfce74f143bde4.MnDcPltUO1y3zHDd"
# Try the other key
LLM_API_KEY = "c00f4a00b83b438a830ec506d0b87529.RjlUYTQo1J5jEs37"
LLM_MODEL = "glm-4-flash"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LLM_API_KEY}"
}

payload = {
    "model": LLM_MODEL,
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "stream": False,
    "max_tokens": 100,
    "temperature": 0.7
}

print(f"Testing Model: {LLM_MODEL}")
print(f"URL: {LLM_API_URL}")
print(f"Headers: {headers}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(LLM_API_URL, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
