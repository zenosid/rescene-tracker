# -*- coding: utf-8 -*-
"""
뉴스 기사 제목/본문 일부에서 "N월 N일" 또는 "N일" + 이벤트 키워드(시구/콘서트/방송 등)를
감지해서 일정 후보를 뽑아냅니다.

⚠️ 100% 정확하지 않은 휴리스틱입니다. 공식 소스로 확인되지 않은 내용이므로
   모든 결과는 반드시 "추정"으로 표시합니다 (config.py 표준 원칙과 동일).
"""
import re
from datetime import date, timedelta

# 키워드가 걸리면 해당 타입으로 분류 (먼저 매칭되는 키워드 우선)
EVENT_KEYWORDS = [
    ("시구", "행사"),
    ("팬사인회", "팬사인회"),
    ("팬미팅", "팬미팅"),
    ("쇼케이스", "쇼케이스"),
    ("컴백", "발매"),
    ("발매", "발매"),
    ("콘서트", "공연"),
    ("페스티벌", "행사"),
    ("축제", "행사"),
    ("생방송", "방송"),
    ("출연", "방송"),
    ("공연", "공연"),
]

_FULL_DATE_RE = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_DAY_ONLY_RE = re.compile(r"(\d{1,2})\s*일")


def _match_event_type(text):
    for keyword, event_type in EVENT_KEYWORDS:
        if keyword in text:
            return event_type, keyword
    return None, None


def _resolve_full_date(month, day, today):
    """N월 N일 형태 - 이미 지난 달/일이면 내년으로 추정."""
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return None
    if candidate < today - timedelta(days=3):
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            return None
    return candidate


def _resolve_day_only(day, today):
    """N일만 있는 경우 - 이번 달 기준, 이미 많이 지났으면 다음 달로 추정."""
    try:
        candidate = date(today.year, today.month, day)
    except ValueError:
        return None
    if candidate < today - timedelta(days=5):
        month, year = today.month + 1, today.year
        if month > 12:
            month, year = 1, year + 1
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
    return candidate


def extract_schedule_candidates(news_items, today=None):
    """
    news_items: db.get_recent_items()에서 source_type == 'news'인 항목들
    반환: [{"date": "YYYY-MM-DD", "type": ..., "title": ..., "note": ..., "source_link": ...}, ...]
    """
    today = today or date.today()
    candidates = []

    for item in news_items:
        text = f"{item['title']} {item['snippet'] or ''}"
        event_type, matched_keyword = _match_event_type(text)
        if not event_type:
            continue

        event_date = None
        m_full = _FULL_DATE_RE.search(text)
        if m_full:
            event_date = _resolve_full_date(int(m_full.group(1)), int(m_full.group(2)), today)
        else:
            m_day = _DAY_ONLY_RE.search(text)
            if m_day:
                event_date = _resolve_day_only(int(m_day.group(1)), today)

        if not event_date:
            continue
        # 너무 먼 과거로 잘못 추정된 경우는 제외 (감지 실패 가능성이 높음)
        if event_date < today - timedelta(days=3):
            continue

        candidates.append(
            {
                "date": event_date.isoformat(),
                "type": event_type,
                "title": item["title"][:70],
                "note": f"[추정] 뉴스 기사 자동 추출 (키워드: {matched_keyword}) · {item['source_name']}",
                "source_link": item["link"],
            }
        )

    return candidates
