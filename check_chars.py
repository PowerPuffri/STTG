import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def check_chars():
    try:
        # Check CSRF Token first
        print("Checking GET /csrf-token...")
        csrf_res = requests.get(f"{BASE_URL}/csrf-token")
        print(f"CSRF Status: {csrf_res.status_code}")
        print(f"CSRF Content: {csrf_res.text}")
        
        # Try POST (as discovered)
        print("Attempting POST /api/characters/all...")
        res = requests.post(f"{BASE_URL}/api/characters/all")
        print(f"Status: {res.status_code}")
        try:
            data = res.json()
            print(f"Type: {type(data)}")
            if isinstance(data, list):
                print(f"Count: {len(data)}")
                if len(data) > 0:
                    print(f"First char: {data[0].get('name')}")
            else:
                print(f"Data: {data}")
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            print(f"Text: {res.text[:200]}")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    check_chars()
