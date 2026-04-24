import sqlite3
import requests
import secrets
import string
import logging
import os
import shutil
import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SillyTavernMiddleware:
    def __init__(self, base_url="http://127.0.0.1:8000", admin_handle="default-user", admin_password="", db_path="st_tg_mapping.db"):
        self.base_url = base_url.rstrip('/')
        self.admin_handle = admin_handle
        self.admin_password = admin_password
        self.db_path = db_path
        # Hardcoded data root for this environment
        self.data_root = os.path.join(os.getcwd(), "SillyTavern", "data")
        self._init_db()
        
        # We use separate sessions for admin ops and user logins to avoid cookie conflicts
        self.admin_session = requests.Session()
        self.csrf_token = None

    def _init_db(self):
        """Initialize the SQLite database for user mapping."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    st_handle TEXT UNIQUE NOT NULL,
                    st_password TEXT NOT NULL,
                    state TEXT DEFAULT 'welcome',
                    selected_character TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _get_csrf_token(self, session):
        """Fetch CSRF token for a specific session."""
        try:
            response = session.get(f"{self.base_url}/csrf-token")
            response.raise_for_status()
            data = response.json()
            token = data.get("token")
            if token and token != "disabled":
                return token
            return None
        except Exception as e:
            logger.error(f"Failed to get CSRF token: {e}")
            return None

    def _get_headers(self, csrf_token=None):
        headers = {"Content-Type": "application/json"}
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token
        return headers

    def _admin_login(self):
        """Log in as admin to perform administrative tasks."""
        # 1. Get CSRF for admin session
        csrf = self._get_csrf_token(self.admin_session)
        
        # 2. Login
        payload = {
            "handle": self.admin_handle,
            "password": self.admin_password
        }
        headers = self._get_headers(csrf)
        
        try:
            response = self.admin_session.post(
                f"{self.base_url}/api/users/login",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            logger.info("Admin login successful")
            return csrf # Return the CSRF token used for this session
        except requests.exceptions.HTTPError as e:
            logger.error(f"Admin login failed: {e.response.status_code} - {e.response.text}")
            raise Exception("Admin login failed")

    def _create_st_user(self, handle, name, password):
        """Create a new user in SillyTavern using admin credentials."""
        # Ensure we are logged in as admin
        csrf = self._admin_login()
        
        payload = {
            "handle": handle,
            "name": name,
            "password": password,
            "admin": False
        }
        headers = self._get_headers(csrf)

        try:
            response = self.admin_session.post(
                f"{self.base_url}/api/users/create",
                json=payload,
                headers=headers
            )
            if response.status_code == 409:
                logger.warning(f"User {handle} already exists in ST backend")
                return True
            response.raise_for_status()
            logger.info(f"Created new ST user: {handle}")
            return True
        except Exception as e:
            logger.error(f"Failed to create user {handle}: {e}")
            raise

    def _generate_password(self, length=12):
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(length))

    def _login_user(self, handle, password):
        """Login as a specific user and return the session cookie."""
        session = requests.Session()
        csrf = self._get_csrf_token(session)
        
        payload = {
            "handle": handle,
            "password": password
        }
        headers = self._get_headers(csrf)
        
        try:
            response = session.post(
                f"{self.base_url}/api/users/login",
                json=payload,
                headers=headers
            )
            if response.status_code != 200:
                logger.error(f"Login failed payload: handle={handle}, password={password}")
                logger.error(f"Login response: {response.text}")
            response.raise_for_status()
            
            # Return the connect.sid cookie
            cookies = session.cookies.get_dict()
            logger.info(f"Received cookies: {cookies}")
            
            # Construct Cookie header with ALL session cookies (including signature)
            cookie_parts = []
            for name, value in cookies.items():
                if name.startswith('session-'):
                    cookie_parts.append(f"{name}={value}")
            
            if cookie_parts:
                full_cookie = "; ".join(cookie_parts)
                logger.info(f"Successfully retrieved token for {handle}")
                return full_cookie
            else:
                raise Exception("No session cookie found in response")
                
        except Exception as e:
            logger.error(f"User login failed for {handle}: {e}")
            raise

    def _sync_characters(self, target_handle):
        """Sync characters from default-user to target user."""
        try:
            source_dir = os.path.join(self.data_root, "default-user", "characters")
            target_dir = os.path.join(self.data_root, target_handle, "characters")
            
            if not os.path.exists(source_dir):
                logger.warning(f"Source directory not found: {source_dir}")
                return

            if not os.path.exists(target_dir):
                logger.info(f"Target directory not found, creating: {target_dir}")
                os.makedirs(target_dir, exist_ok=True)

            logger.info(f"Syncing characters from {source_dir} to {target_dir}")
            
            # Copy all files
            for item in os.listdir(source_dir):
                s = os.path.join(source_dir, item)
                d = os.path.join(target_dir, item)
                if os.path.isfile(s):
                    if not os.path.exists(d) or os.path.getmtime(s) > os.path.getmtime(d):
                        shutil.copy2(s, d)
                        logger.info(f"Copied {item}")
                elif os.path.isdir(s):
                     if not os.path.exists(d):
                        shutil.copytree(s, d)
                        logger.info(f"Copied directory {item}")
        except Exception as e:
            logger.error(f"Failed to sync characters: {e}")

    def get_st_token(self, telegram_id, telegram_name=None):
        """
        Main entry point.
        Maps Telegram ID -> ST Token.
        Auto-registers if necessary.
        """
        if telegram_name is None:
            telegram_name = f"User {telegram_id}"

        # 1. Check database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT st_handle, st_password FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()

        if row:
            handle, password = row
            logger.info(f"Found existing user mapping: {telegram_id} -> {handle}")
        else:
            # 2. Register new user
            handle = f"tg-{telegram_id}"
            password = self._generate_password()
            logger.info(f"Registering new user mapping: {telegram_id} -> {handle}")
            
            # Create in ST
            self._create_st_user(handle, telegram_name, password)
            
            # Save to DB
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO users (telegram_id, st_handle, st_password) VALUES (?, ?, ?)",
                    (telegram_id, handle, password)
                )
        
        # SYNC CHARACTERS NOW
        self._sync_characters(handle)
        
        # 3. Login and return token
        return self._login_user(handle, password)

    def get_user_state(self, telegram_id):
        """Get current state for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state, selected_character FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            if row:
                return {'state': row[0], 'selected_character': row[1]}
            return {'state': 'welcome', 'selected_character': None}

    def set_user_state(self, telegram_id, state, selected_character=None):
        """Set state for a user."""
        with sqlite3.connect(self.db_path) as conn:
            if selected_character:
                conn.execute(
                    "UPDATE users SET state = ?, selected_character = ? WHERE telegram_id = ?",
                    (state, selected_character, telegram_id)
                )
            else:
                conn.execute(
                    "UPDATE users SET state = ? WHERE telegram_id = ?",
                    (state, telegram_id)
                )

    def get_characters(self, user_id, user_name):
        """Get list of characters from SillyTavern."""
        try:
            # Create a new session to get CSRF token
            session = requests.Session()
            csrf_token = self._get_csrf_token(session)

            # Login as the user
            user_state = self.get_user_state(user_id)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT st_handle, st_password FROM users WHERE telegram_id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    return []
                handle, password = row

            # Sync characters before listing
            self._sync_characters(handle)

            # Login to get fresh cookies
            csrf = self._get_csrf_token(session)
            payload = {"handle": handle, "password": password}
            headers = self._get_headers(csrf)
            login_response = session.post(
                f"{self.base_url}/api/users/login",
                json=payload,
                headers=headers
            )
            login_response.raise_for_status()

            # Get the CSRF token after login
            csrf_token = self._get_csrf_token(session)

            # Now get characters with CSRF token and session cookies
            headers = {
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf_token
            }

            response = session.post(
                f"{self.base_url}/api/characters/all",
                json={},
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get characters: Status {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Failed to get characters: {e}")
            return []

    def get_character_greeting(self, character_name, user_id, user_name):
        """Get the greeting message for a character."""
        try:
            characters = self.get_characters(user_id, user_name)
            for char in characters:
                if char.get('name') == character_name:
                    # 1. Try 'first_mes' (Standard V2)
                    first_mes = char.get('first_mes')
                    if first_mes:
                        return first_mes
                    
                    # 2. Try 'data.first_mes' (Nested V2)
                    if char.get('data') and char.get('data').get('first_mes'):
                        return char.get('data').get('first_mes')

                    # 3. Fallback (Old or custom)
                    greeting = char.get('greeting')
                    if greeting:
                        return greeting
                        
                    return "你好～ (未找到开场白)"
            return "你好～ (未找到角色)"
        except Exception as e:
            logger.error(f"Failed to get character greeting: {e}")
            return "你好～"

# Example usage
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ST Middleware for Telegram")
    parser.add_argument("telegram_id", type=int, help="Telegram User ID")
    parser.add_argument("--name", type=str, default="Telegram User", help="Display Name")
    parser.add_argument("--admin_pass", type=str, default="", help="ST Admin Password")
    args = parser.parse_args()

    middleware = SillyTavernMiddleware(admin_password=args.admin_pass)
    try:
        token = middleware.get_st_token(args.telegram_id, args.name)
        print(f"SUCCESS: {token}")
    except Exception as e:
        print(f"ERROR: {e}")
