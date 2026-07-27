# -*- coding: utf-8 -*-
"""
SQLite 저장소.
- items: 유튜브/뉴스 아카이브
- chart_snapshots: 차트 조회 시점의 리센느 곡 순위 기록 (히스토리 누적)
"""
import sqlite3
from contextlib import contextmanager
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,      -- 'youtube' | 'news'
    source_name TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,      -- 중복 방지의 핵심 (링크 기준 dedup)
    published_at TEXT,              -- 원본 발행 시각 (ISO 문자열)
    snippet TEXT,
    fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chart_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,         -- 'melon' | 'genie' | 'bugs' ...
    rank INTEGER NOT NULL,
    song_title TEXT NOT NULL,
    artist_text TEXT NOT NULL,
    checked_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS auto_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,             -- 'YYYY-MM-DD' (추정치)
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    note TEXT,
    source_link TEXT NOT NULL UNIQUE,  -- 같은 기사에서 중복 추출 방지
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS official_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,             -- 'YYYY-MM-DD'
    time_text TEXT,                 -- 'PM 10:00' 등 원문 표기 그대로
    title TEXT NOT NULL,
    category TEXT,
    dedup_key TEXT NOT NULL UNIQUE,  -- date+title+time_text 조합, 중복 저장 방지
    created_at TEXT DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ── 아카이브(items) ──────────────────────────────────────────
def insert_item(conn, source_type, source_name, title, link, published_at, snippet):
    """이미 존재하는 link면 무시(INSERT OR IGNORE)하고 신규 여부를 반환."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO items
           (source_type, source_name, title, link, published_at, snippet)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (source_type, source_name, title, link, published_at, snippet),
    )
    return cur.rowcount > 0


def get_recent_items(conn, limit=200):
    return conn.execute(
        "SELECT * FROM items ORDER BY published_at DESC LIMIT ?", (limit,)
    ).fetchall()


# ── 차트 스냅샷 ─────────────────────────────────────────────
def save_chart_snapshot(conn, platform, rank, song_title, artist_text):
    conn.execute(
        """INSERT INTO chart_snapshots (platform, rank, song_title, artist_text)
           VALUES (?, ?, ?, ?)""",
        (platform, rank, song_title, artist_text),
    )


def get_latest_chart_snapshot(conn, platform):
    """플랫폼별 가장 최근 조회 시각의 스냅샷 전체를 반환."""
    latest_time_row = conn.execute(
        "SELECT MAX(checked_at) AS t FROM chart_snapshots WHERE platform = ?",
        (platform,),
    ).fetchone()
    if not latest_time_row or not latest_time_row["t"]:
        return []
    return conn.execute(
        """SELECT * FROM chart_snapshots
           WHERE platform = ? AND checked_at = ?
           ORDER BY rank ASC""",
        (platform, latest_time_row["t"]),
    ).fetchall()


def get_chart_history(conn, platform, song_title, limit=30):
    return conn.execute(
        """SELECT * FROM chart_snapshots
           WHERE platform = ? AND song_title = ?
           ORDER BY checked_at DESC LIMIT ?""",
        (platform, song_title, limit),
    ).fetchall()


# ── 뉴스 기반 자동 스케줄 ────────────────────────────────────
def insert_auto_schedule(conn, date, type_, title, note, source_link):
    """같은 기사(source_link)에서는 한 번만 추출되도록 UNIQUE 제약으로 중복 방지."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO auto_schedule (date, type, title, note, source_link)
           VALUES (?, ?, ?, ?, ?)""",
        (date, type_, title, note, source_link),
    )
    return cur.rowcount > 0


def get_auto_schedule(conn):
    return conn.execute("SELECT * FROM auto_schedule ORDER BY date ASC").fetchall()


# ── 공식 스케줄 (Mnet Plus) ─────────────────────────────────
def insert_official_schedule(conn, date, time_text, title, category, dedup_key):
    cur = conn.execute(
        """INSERT OR IGNORE INTO official_schedule (date, time_text, title, category, dedup_key)
           VALUES (?, ?, ?, ?, ?)""",
        (date, time_text, title, category, dedup_key),
    )
    return cur.rowcount > 0


def get_official_schedule(conn):
    return conn.execute("SELECT * FROM official_schedule ORDER BY date ASC").fetchall()
