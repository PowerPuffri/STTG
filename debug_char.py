import requests
import json
import sqlite3

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = "st_tg_mapping.db"
USER_ID = 7974510481 # From logs

def check_char_structure():
    session = requests.Session()
    
    # 1. Get user credentials from DB
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT st_handle, st_password FROM users WHERE telegram_id = ?", (USER_ID,))
        row = cursor.fetchone()
        if not row:
            print("User not found in DB")
            return
        handle, password = row
        print(f"User: {handle}")

    # 2. Login
    csrf_res = session.get(f"{BASE_URL}/csrf-token")
    csrf_token = csrf_res.json().get("token")
    
    login_payload = {"handle": handle, "password": password}
    login_headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf_token}
    
    res = session.post(f"{BASE_URL}/api/users/login", json=login_payload, headers=login_headers)
    print(f"Login Status: {res.status_code}")
    
    # 3. Get Characters
    csrf_token = session.get(f"{BASE_URL}/csrf-token").json().get("token")
    headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf_token}
    
    res = session.post(f"{BASE_URL}/api/characters/all", json={}, headers=headers)
    print(f"Get Chars Status: {res.status_code}")
    
    if res.status_code == 200:
        chars = res.json()
        if chars:
            c = chars[0]
            print(f"First Char Name: {c.get('name')}")
            print(f"Keys: {list(c.keys())}")
            print(f"first_mes: {c.get('first_mes')}")
            print(f"data.first_mes: {c.get('data', {}).get('first_mes')}")
            print(f"greeting: {c.get('greeting')}")
        else:
            print("No characters found")

if __name__ == "__main__":
    check_char_structure()
