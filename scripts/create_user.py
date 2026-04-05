import requests
import json
import sys
import argparse

def create_user(admin_password=""):
    # Configuration
    BASE_URL = "http://127.0.0.1:8000"  # Adjust port if necessary
    ADMIN_HANDLE = "default-user"       # Default admin handle
    NEW_USER_HANDLE = "user_001"
    NEW_USER_NAME = "User 001"
    NEW_USER_PASSWORD = "password123"

    session = requests.Session()

    # Step 1: Get CSRF Token
    # SillyTavern uses csrf-sync. We need to fetch the token first.
    # The token is returned in the JSON body of GET /csrf-token
    # and must be sent in the 'X-CSRF-Token' header for subsequent POST requests.
    print(f"[*] Fetching CSRF token from {BASE_URL}/csrf-token...")
    try:
        response = session.get(f"{BASE_URL}/csrf-token")
        response.raise_for_status()
        csrf_data = response.json()
        csrf_token = csrf_data.get("token")
        print(f"[+] CSRF Token: {csrf_token}")
    except requests.exceptions.RequestException as e:
        print(f"[-] Failed to get CSRF token: {e}")
        csrf_token = None

    headers = {
        "Content-Type": "application/json"
    }
    if csrf_token and csrf_token != "disabled":
        headers["X-CSRF-Token"] = csrf_token

    # Step 2: Login as Admin
    # Endpoint: /api/users/login
    # Logic: Validates handle/password, sets 'connect.sid' cookie.
    print(f"[*] Logging in as admin ({ADMIN_HANDLE})...")
    login_payload = {
        "handle": ADMIN_HANDLE,
        "password": admin_password
    }
    
    try:
        response = session.post(
            f"{BASE_URL}/api/users/login",
            json=login_payload,
            headers=headers
        )
        
        if response.status_code == 200:
            print("[+] Login successful.")
        else:
            print(f"[-] Login failed: {response.status_code} - {response.text}")
            print("    Hint: Check if the admin password is correct.")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"[-] Login request error: {e}")
        sys.exit(1)

    # Step 3: Create New User
    # Endpoint: /api/users/create
    # Logic: Requires admin session (checked via requireAdminMiddleware).
    print(f"[*] Creating new user: {NEW_USER_HANDLE}...")
    create_payload = {
        "handle": NEW_USER_HANDLE,
        "name": NEW_USER_NAME,
        "password": NEW_USER_PASSWORD,
        "admin": False
    }

    try:
        response = session.post(
            f"{BASE_URL}/api/users/create",
            json=create_payload,
            headers=headers
        )

        if response.status_code == 200:
            print(f"[+] User '{NEW_USER_HANDLE}' created successfully.")
            print(f"    Response: {response.json()}")
        elif response.status_code == 409:
             print(f"[-] User '{NEW_USER_HANDLE}' already exists.")
        else:
            print(f"[-] Failed to create user: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"[-] Create user request error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a user in SillyTavern.")
    parser.add_argument("--password", help="Admin password", default="")
    args = parser.parse_args()
    
    create_user(args.password)
