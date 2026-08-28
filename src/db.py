"""
SQLite 데이터베이스 관리 모듈
- 이미 전송된 기사 식별자(URL, ID, 해시) 기록 및 중복 전송 방지
- 서버(길드)별 알림 채널 및 설정 저장
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.config import Config


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or Config.DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """데이터베이스 테이블 초기화"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 전송된 뉴스 기사 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sent_articles (
                    id TEXT PRIMARY KEY,
                    url TEXT UNIQUE,
                    title TEXT NOT NULL,
                    source TEXT,
                    category TEXT,
                    published_at TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. 서버(길드)별 알림 설정 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    interval_minutes INTEGER DEFAULT 15,
                    enabled INTEGER DEFAULT 1,
                    keywords TEXT DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sent_articles_url ON sent_articles(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sent_articles_created ON sent_articles(created_at)")
            conn.commit()

    @staticmethod
    def generate_article_id(url: str, title: str) -> str:
        """기사 URL 또는 제목 기반 고유 해시 생성"""
        content = f"{url.strip()}_{title.strip()}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def is_article_sent(self, article_id: str, url: str) -> bool:
        """기사가 이미 전송되었는지 확인"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM sent_articles WHERE id = ? OR url = ? LIMIT 1",
                (article_id, url)
            )
            return cursor.fetchone() is not None

    def mark_article_sent(
        self,
        article_id: str,
        url: str,
        title: str,
        source: str = "",
        category: str = "",
        published_at: str = ""
    ) -> bool:
        """기사를 전송 완료로 기록"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO sent_articles (id, url, title, source, category, published_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (article_id, url, title, source, category, published_at))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"[DB Error] mark_article_sent failed: {e}")
            return False

    def get_recent_sent_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 전송된 기사 목록 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, title, source, category, published_at, created_at
                FROM sent_articles
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def set_guild_channel(self, guild_id: int, channel_id: int, interval_minutes: int = 15) -> bool:
        """서버의 알림 채널 및 주기 등록/수정"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO guild_settings (guild_id, channel_id, interval_minutes, enabled, updated_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    interval_minutes = excluded.interval_minutes,
                    enabled = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (str(guild_id), str(channel_id), interval_minutes))
            conn.commit()
            return True

    def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """특정 서버의 설정 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_active_channels(self) -> List[Dict[str, Any]]:
        """알림이 활성화된 모든 채널 목록 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT guild_id, channel_id, interval_minutes FROM guild_settings WHERE enabled = 1")
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_articles(self, days: int = 30) -> int:
        """오래된 전송 이력 정리 (기본 30일 이전)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sent_articles
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days,))
            conn.commit()
            return cursor.rowcount


# 기본 인스턴스 생성
db = Database()
