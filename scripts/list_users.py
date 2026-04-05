import requests

BASE_URL = "http://127.0.0.1:8000"
ADMIN_HANDLE = "default-user"
ADMIN_PASSWORD = "123456"

def list_users():
    session = requests.Session()
    
    # CSRF
    resp = session.get(f"{BASE_URL}/csrf-token")
    csrf = resp.json().get("token")
    headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf}
    
    # Login
    login_payload = {"handle": ADMIN_HANDLE, "password": ADMIN_PASSWORD}
    session.post(f"{BASE_URL}/api/users/login", json=login_payload, headers=headers)
    
    # List
    resp = session.post(f"{BASE_URL}/api/users/get", headers=headers) # api/users/get is admin only, lists all users details
    print(resp.json())

if __name__ == "__main__":
    list_users()
