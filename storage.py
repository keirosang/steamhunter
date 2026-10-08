import os
import sqlite3
import datetime
import yaml
import config

class HugoStorage:
    """独立轻量 SQLite 存储模块，管理文章抓取去重与发帖记录（支持跨机文件自愈去重）"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()
        self._sync_existing_posts()

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

    def _sync_existing_posts(self):
        """扫描 content/posts/*.md，自动从已有 Markdown 文章重建去重索引（实现多服务器无感同步与冷启动零重复）"""
        if not os.path.exists(config.CONTENT_POSTS_DIR):
            return

        md_files = [f for f in os.listdir(config.CONTENT_POSTS_DIR) if f.endswith(".md") and not f.startswith("_")]
        if not md_files:
            return

        with self._get_conn() as conn:
            cursor = conn.cursor()
            for filename in md_files:
                filepath = os.path.join(config.CONTENT_POSTS_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()

                    if not content.startswith("---"):
                        continue

                    parts = content.split("---", 2)
                    if len(parts) < 3:
                        continue

                    meta = yaml.safe_load(parts[1]) or {}
                    appid = meta.get("appid", 0)
                    item_type = meta.get("item_type", "news")
                    title = meta.get("title", "")
                    created_at = meta.get("date", datetime.datetime.now().isoformat())
                    item_key = meta.get("item_key")

                    if not item_key:
                        # 兼容老文章，从类型与 appid 构建保底键
                        item_key = f"recovered_{filename[:-3]}"

                    rel_path = f"content/posts/{filename}"
                    cursor.execute("""
                        INSERT OR IGNORE INTO crawled_items (item_key, item_type, appid, title, hugo_file, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (item_key, item_type, appid, title, rel_path, created_at))
                except Exception:
                    pass
            conn.commit()

    def is_crawled(self, item_key: str) -> bool:
        """检查特定唯一键是否已入库"""
        if not item_key:
            return False
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM crawled_items WHERE item_key = ? LIMIT 1", (item_key,))
            return cursor.fetchone() is not None

    def has_recent_article(self, appid: int, item_type: str = None, days: int = 7) -> bool:
        """
        检查指定 AppID 在指定冷却天数内是否已发布过同类型文章
        用于特惠大促与限免活动去重，防止同一次促销在活动持续期间每日重复发文刷屏。
        """
        if not appid:
            return False
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if item_type:
                cursor.execute("""
                    SELECT 1 FROM crawled_items 
                    WHERE appid = ? AND item_type = ? AND created_at >= ?
                    LIMIT 1
                """, (appid, item_type, cutoff))
            else:
                cursor.execute("""
                    SELECT 1 FROM crawled_items 
                    WHERE appid = ? AND created_at >= ?
                    LIMIT 1
                """, (appid, cutoff))
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
