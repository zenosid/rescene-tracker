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

CREATE TABLE IF NOT EXISTS fan_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_link TEXT NOT NULL,
    video_title TEXT NOT NULL,
    author TEXT NOT NULL,
    text TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    published_at TEXT,
    comment_id TEXT NOT NULL UNIQUE,  -- 유튜브 댓글 고유 ID, 중복 저장 방지
    fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trophies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,           -- 뉴스 발행일(KST) 기준 'YYYY-MM-DD'
    show TEXT NOT NULL,           -- 음악방송 이름
    song TEXT,                    -- 1위한 곡명
    title TEXT NOT NULL,          -- 원 기사 제목
    source_link TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS moderation_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,     -- 'news' | 'community' | 'x'
    source_name TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    matched_keyword TEXT NOT NULL, -- 어떤 키워드에 걸렸는지 (검토 시 참고용)
    reviewed INTEGER DEFAULT 0,    -- 운영자가 확인했는지 (0/1), 직접 DB에서 체크
    fetched_at TEXT DEFAULT (datetime('now'))
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
        # 이미 만들어져 있던 DB에는 song 컬럼이 없을 수 있어서 있는지 확인 후 추가
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(trophies)").fetchall()]
        if "song" not in cols:
            conn.execute("ALTER TABLE trophies ADD COLUMN song TEXT")


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


def get_previous_ranks(conn, platform):
    """
    해당 플랫폼의 '가장 최근' 스냅샷 이전, 즉 그 전 회차의 곡별 순위를
    {곡제목: 순위} 딕셔너리로 반환. (최신 대비 변동 계산용)
    """
    times = conn.execute(
        """SELECT DISTINCT checked_at FROM chart_snapshots
           WHERE platform = ? ORDER BY checked_at DESC LIMIT 2""",
        (platform,),
    ).fetchall()
    if len(times) < 2:
        return {}
    prev_time = times[1]["checked_at"]
    rows = conn.execute(
        "SELECT song_title, rank FROM chart_snapshots WHERE platform = ? AND checked_at = ?",
        (platform, prev_time),
    ).fetchall()
    return {row["song_title"]: row["rank"] for row in rows}


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


def delete_official_schedule_month(conn, year, month):
    """특정 연-월의 공식 스케줄을 전부 지움 (다시 최신 상태로 채워넣기 전 초기화용)."""
    prefix = f"{year}-{month:02d}-"
    conn.execute("DELETE FROM official_schedule WHERE date LIKE ?", (prefix + "%",))


def get_official_schedule(conn):
    return conn.execute("SELECT * FROM official_schedule ORDER BY date ASC").fetchall()


# ── 팬 반응 (유튜브 댓글) ────────────────────────────────────
def insert_fan_reaction(conn, video_link, video_title, author, text, like_count, published_at, comment_id):
    cur = conn.execute(
        """INSERT OR IGNORE INTO fan_reactions
           (video_link, video_title, author, text, like_count, published_at, comment_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (video_link, video_title, author, text, like_count, published_at, comment_id),
    )
    return cur.rowcount > 0


def get_recent_fan_reactions(conn, limit=100):
    return conn.execute(
        "SELECT * FROM fan_reactions ORDER BY like_count DESC, fetched_at DESC LIMIT ?",
        (limit,),
    ).fetchall()


# ── 트로피(1위 수상 기록) ────────────────────────────────────
def insert_trophy(conn, date, show, song, title, source_link):
    # 같은 수상을 언론사마다 하루이틀 차이나는 날짜로 보도하는 경우가 많아서,
    # 같은 방송+같은 곡이 최근 며칠(3일) 이내에 이미 있으면 중복으로 보고 건너뜀
    from datetime import date as _date_cls

    existing_rows = conn.execute(
        "SELECT id, date FROM trophies WHERE show = ? AND song = ?", (show, song)
    ).fetchall()
    try:
        new_date = _date_cls.fromisoformat(date)
    except ValueError:
        new_date = None

    for row in existing_rows:
        if new_date is None:
            return False  # 날짜 파싱이 안 되면 안전하게 중복 취급
        try:
            existing_date = _date_cls.fromisoformat(row["date"])
        except ValueError:
            continue
        if abs((new_date - existing_date).days) <= 3:
            return False

    cur = conn.execute(
        "INSERT OR IGNORE INTO trophies (date, show, song, title, source_link) VALUES (?, ?, ?, ?, ?)",
        (date, show, song, title, source_link),
    )
    return cur.rowcount > 0


def get_recent_trophies(conn, limit=100):
    return conn.execute(
        "SELECT * FROM trophies ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()


# ── 모더레이션 플래그(악플/부적절 콘텐츠 후보, 운영자 전용) ─────────
def insert_moderation_flag(conn, source_type, source_name, title, link, matched_keyword):
    cur = conn.execute(
        """INSERT OR IGNORE INTO moderation_flags
           (source_type, source_name, title, link, matched_keyword)
           VALUES (?, ?, ?, ?, ?)""",
        (source_type, source_name, title, link, matched_keyword),
    )
    return cur.rowcount > 0


def get_unreviewed_moderation_flags(conn, limit=50):
    return conn.execute(
        "SELECT * FROM moderation_flags WHERE reviewed = 0 ORDER BY fetched_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
