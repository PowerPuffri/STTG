import sqlite3
import os
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Database:
    """
    Manages SQLite database for user data and subscription status.
    """
    
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        telegram_id INTEGER PRIMARY KEY,
                        is_vip BOOLEAN DEFAULT 0,
                        daily_msg_count INTEGER DEFAULT 0,
                        daily_img_count INTEGER DEFAULT 0,
                        last_active_date TEXT,
                        username TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def get_user(self, telegram_id):
        """Get user data by Telegram ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def create_user(self, telegram_id, username=None):
        """Create a new user."""
        try:
            today = datetime.date.today().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO users (telegram_id, username, last_active_date) VALUES (?, ?, ?)",
                    (telegram_id, username, today)
                )
                conn.commit()
            return self.get_user(telegram_id)
        except Exception as e:
            logger.error(f"Failed to create user {telegram_id}: {e}")
            return None

    def check_and_reset_daily_limit(self, telegram_id):
        """
        Checks if the date has changed since last activity.
        If so, resets daily_msg_count to 0 and updates last_active_date.
        Returns the updated user object.
        """
        user = self.get_user(telegram_id)
        if not user:
            return None

        today = datetime.date.today().isoformat()
        last_date = user.get('last_active_date')

        if last_date != today:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE users SET daily_msg_count = 0, daily_img_count = 0, last_active_date = ? WHERE telegram_id = ?",
                        (today, telegram_id)
                    )
                    conn.commit()
                return self.get_user(telegram_id)
            except Exception as e:
                logger.error(f"Failed to reset daily limit for {telegram_id}: {e}")
        
        return user

    def increment_msg_count(self, telegram_id):
        """Increments the daily message count for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET daily_msg_count = daily_msg_count + 1 WHERE telegram_id = ?",
                    (telegram_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to increment message count for {telegram_id}: {e}")

    def increment_img_count(self, telegram_id):
        """Increments the daily image count for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET daily_img_count = daily_img_count + 1 WHERE telegram_id = ?",
                    (telegram_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to increment image count for {telegram_id}: {e}")

    def set_vip_status(self, telegram_id, is_vip):
        """Sets the VIP status for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET is_vip = ? WHERE telegram_id = ?",
                    (1 if is_vip else 0, telegram_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to set VIP status for {telegram_id}: {e}")

if __name__ == "__main__":
    # Test code
    db = Database()
    uid = 123456
    db.create_user(uid, "test_user")
    print("User:", db.get_user(uid))
    
    db.increment_msg_count(uid)
    print("After increment:", db.get_user(uid))
    
    # Simulate date change (hack for testing)
    with sqlite3.connect(db.db_path) as conn:
        conn.execute("UPDATE users SET last_active_date = '2000-01-01' WHERE telegram_id = ?", (uid,))
        conn.commit()
    
    print("After date reset:", db.check_and_reset_daily_limit(uid))
