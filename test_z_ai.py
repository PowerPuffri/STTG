import requests
import json

URL = "https://api.z.ai/api/paas/v4/chat/completions"
KEYS = [
    "702410a536764a848acfce74f143bde4.MnDcPltUO1y3zHDd",
    "c00f4a00b83b438a830ec506d0b87529.RjlUYTQo1J5jEs37"
]

def test_key(key):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    payload = {
        "model": "glm-4.7",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "stream": False,
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    print(f"Testing Key: {key[:10]}...")
    try:
        response = requests.post(URL, json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)

for k in KEYS:
    test_key(k)
