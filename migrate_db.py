import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "st_tg_mapping.db"

def migrate():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        logger.info(f"Current columns: {columns}")
        
        if 'state' not in columns:
            logger.info("Adding 'state' column...")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN state TEXT DEFAULT 'welcome'")
                logger.info("Added 'state' column.")
            except Exception as e:
                logger.error(f"Failed to add 'state': {e}")

        if 'selected_character' not in columns:
            logger.info("Adding 'selected_character' column...")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN selected_character TEXT")
                logger.info("Added 'selected_character' column.")
            except Exception as e:
                logger.error(f"Failed to add 'selected_character': {e}")
        
        conn.commit()
        logger.info("Migration complete.")

if __name__ == "__main__":
    migrate()
