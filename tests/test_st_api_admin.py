import requests
from middleware import SillyTavernMiddleware
import logging

logging.basicConfig(level=logging.INFO)

mw = SillyTavernMiddleware(admin_password="123456")

# 1. Admin Login
print("--- Admin Login ---")
csrf = mw._admin_login()
print(f"Admin CSRF: {csrf}")
print(f"Admin Session Cookies: {mw.admin_session.cookies.get_dict()}")

# 2. Get Characters as Admin
try:
    headers = {"X-CSRF-Token": csrf}
    resp = mw.admin_session.post("http://127.0.0.1:8000/api/characters", headers=headers) # POST usually for filtering? Or GET?
    # Try GET first
    resp = mw.admin_session.get("http://127.0.0.1:8000/api/characters", headers=headers)
    print(f"Admin Get Characters Status: {resp.status_code}")
    if resp.status_code == 200:
        chars = resp.json()
        print(f"Found {len(chars)} characters")
        for c in chars[:3]:
            print(f" - {c.get('name')} (avatar: {c.get('avatar')})")
    else:
        print(resp.text)
except Exception as e:
    print(f"Error: {e}")
