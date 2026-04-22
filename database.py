"""
Database module for user tracking and statistics.
Uses SQLite for simplicity and persistence.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = Path(__file__).parent / "data" / "bot_database.db"


@dataclass
class UserRecord:
    """User record from database"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    first_seen: datetime
    last_seen: datetime
    stickers_created: int


class Database:
    """SQLite database for user tracking and statistics"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    stickers_created INTEGER DEFAULT 0
                )
            """)

            # Activity log table for detailed tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    stickers_count INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_timestamp
                ON activity_log(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_user
                ON activity_log(user_id)
            """)

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()

    def upsert_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> None:
        """Insert or update user record"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing user
                cursor.execute("""
                    UPDATE users
                    SET username = COALESCE(?, username),
                        first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name),
                        last_seen = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (username, first_name, last_name, user_id))
            else:
                # Insert new user
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, first_name, last_name))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to upsert user {user_id}: {e}")
        finally:
            conn.close()

    def log_activity(
        self,
        user_id: int,
        action: str,
        stickers_count: int = 0
    ) -> None:
        """Log user activity"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Log the activity
            cursor.execute("""
                INSERT INTO activity_log (user_id, action, stickers_count)
                VALUES (?, ?, ?)
            """, (user_id, action, stickers_count))

            # Update user's sticker count if stickers were created
            if stickers_count > 0:
                cursor.execute("""
                    UPDATE users
                    SET stickers_created = stickers_created + ?,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (stickers_count, user_id))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to log activity for user {user_id}: {e}")
        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[UserRecord]:
        """Get user by ID"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return UserRecord(
                    user_id=row["user_id"],
                    username=row["username"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    first_seen=datetime.fromisoformat(row["first_seen"]),
                    last_seen=datetime.fromisoformat(row["last_seen"]),
                    stickers_created=row["stickers_created"]
                )
            return None

        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
        finally:
            conn.close()

    def get_total_stickers(self) -> int:
        """Get total stickers created"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(SUM(stickers_created), 0) FROM users")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get total stickers: {e}")
            return 0
        finally:
            conn.close()

    def get_unique_users_count(self) -> int:
        """Get total unique users"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get unique users count: {e}")
            return 0
        finally:
            conn.close()

    def get_stickers_last_24h(self) -> int:
        """Get stickers created in last 24 hours"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(stickers_count), 0)
                FROM activity_log
                WHERE timestamp > datetime('now', '-1 day')
                AND action = 'stickers_created'
            """)
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get stickers last 24h: {e}")
            return 0
        finally:
            conn.close()

    def get_active_users_count(self, hours: int = 24) -> int:
        """Get count of active users in specified time period"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT COUNT(DISTINCT user_id)
                FROM activity_log
                WHERE timestamp > datetime('now', '-{hours} hours')
            """)
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get active users count: {e}")
            return 0
        finally:
            conn.close()

    def get_last_active_users(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get last N active users"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.user_id, u.username, u.first_name, u.last_name,
                       u.stickers_created, u.last_seen
                FROM users u
                ORDER BY u.last_seen DESC
                LIMIT ?
            """, (limit,))

            users = []
            for row in cursor.fetchall():
                users.append({
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "stickers_created": row["stickers_created"],
                    "last_seen": row["last_seen"]
                })
            return users

        except Exception as e:
            logger.error(f"Failed to get last active users: {e}")
            return []
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            "total_stickers": self.get_total_stickers(),
            "unique_users": self.get_unique_users_count(),
            "stickers_24h": self.get_stickers_last_24h(),
            "active_24h": self.get_active_users_count(24),
            "active_week": self.get_active_users_count(24 * 7),
            "active_month": self.get_active_users_count(24 * 30),
            "last_users": self.get_last_active_users(3)
        }


# Global database instance
db = Database()
