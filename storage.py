import sqlite3
import datetime
import config

class HugoStorage:
    """独立轻量 SQLite 存储模块，管理文章抓取去重与发帖记录"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawled_items (
                    item_key TEXT PRIMARY KEY,
                    item_type TEXT,
                    appid INTEGER,
                    title TEXT,
                    hugo_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def is_crawled(self, item_key: str) -> bool:
        if not item_key:
            return False
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM crawled_items WHERE item_key = ? LIMIT 1", (item_key,))
            return cursor.fetchone() is not None

    def mark_crawled(self, item_key: str, item_type: str, appid: int, title: str, hugo_file: str):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO crawled_items (item_key, item_type, appid, title, hugo_file, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item_key, item_type, appid, title, hugo_file, datetime.datetime.now().isoformat()))
            conn.commit()

    def get_total_crawled(self) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crawled_items")
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_recent_crawled(self, limit: int = 10) -> list[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crawled_items ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
