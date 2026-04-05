import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
ADMIN_HANDLE = "default-user"
ADMIN_PASSWORD = "123456"

def delete_user(handle):
    session = requests.Session()
    
    # CSRF
    resp = session.get(f"{BASE_URL}/csrf-token")
    csrf = resp.json().get("token")
    headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf}
    
    # Login
    login_payload = {"handle": ADMIN_HANDLE, "password": ADMIN_PASSWORD}
    session.post(f"{BASE_URL}/api/users/login", json=login_payload, headers=headers)
    
    # Delete
    del_payload = {"handle": handle, "purge": True}
    resp = session.post(f"{BASE_URL}/api/users/delete", json=del_payload, headers=headers)
    
    print(f"Delete {handle}: {resp.status_code}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        delete_user(sys.argv[1])
