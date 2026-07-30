# -*- coding: utf-8 -*-
"""
뉴스 기사 제목/본문 일부에서 "N월 N일" 또는 "N일" + 이벤트 키워드(시구/콘서트/방송 등)를
감지해서 일정 후보를 뽑아냅니다.

⚠️ 100% 정확하지 않은 휴리스틱입니다. 공식 소스로 확인되지 않은 내용이므로
   모든 결과는 반드시 "추정"으로 표시합니다 (config.py 표준 원칙과 동일).
"""
import re
from datetime import date, timedelta

from kst import now_kst

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
    ("공연", "공연"),
    ("출격", "행사"),
    # 아래 둘은 다른 키워드보다 범용적이라 맨 뒤에 둡니다 (다른 키워드가 먼저 매칭되면 그걸 우선)
    ("확정", "행사"),
    ("예정", "행사"),
]

# 이 뒤에 나오면 "안 한다/못 한다"는 뜻이라 스케줄로 잡으면 안 되는 경우들
# (예: "출연없이 1위" = 방송에 안 나왔다는 뜻이지 출연 예정이라는 뜻이 아님)
_NEGATION_SUFFIXES = ["없이", "없는", "없다", "안 ", "무산", "취소", "불참", "못 "]

# 이런 표현이 기사에 있으면 "이미 나온 콘텐츠에 대한 소식"이지 앞으로 갈 일정이
# 아니므로, 다른 키워드가 매칭되더라도 통째로 스케줄 후보에서 제외합니다.
_CONTENT_RELEASE_INDICATORS = [
    "선공개", "공개된", "영상 공개", "화보 공개", "포스터 공개", "티저 공개",
    "썸네일", "예고편",
]


def _is_content_release_news(text):
    return any(indicator in text for indicator in _CONTENT_RELEASE_INDICATORS)

_FULL_DATE_RE = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_NUMERIC_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})(?!\d)")
_DAY_ONLY_RE = re.compile(r"(\d{1,2})\s*일")


def _match_event_type(text):
    for keyword, event_type in EVENT_KEYWORDS:
        idx = text.find(keyword)
        if idx == -1:
            continue
        after = text[idx + len(keyword): idx + len(keyword) + 4]
        if any(after.startswith(neg) for neg in _NEGATION_SUFFIXES):
            continue  # 부정형 표현이므로 이 키워드는 건너뛰고 다음 후보 키워드로
        return event_type, keyword, idx
    return None, None, -1


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
    today = today or now_kst().date()
    candidates = []

    for item in news_items:
        text = f"{item['title']} {item['snippet'] or ''}"
        if _is_content_release_news(text):
            continue  # "선공개/영상 공개" 등은 이미 나온 콘텐츠 소식이지 예정된 일정이 아님
        event_type, matched_keyword, keyword_idx = _match_event_type(text)
        if not event_type:
            continue

        # 날짜는 키워드와 완전히 무관한 곳(기사 다른 부분)에 있으면 안 되므로,
        # 키워드 주변(앞뒤 약 40자) 범위에서만 날짜를 찾음 - 서로 관련 없는
        # 키워드와 날짜가 우연히 한 기사에 같이 있어서 잘못 엮이는 걸 방지
        window_start = max(0, keyword_idx - 40)
        window_end = keyword_idx + len(matched_keyword) + 40
        search_text = text[window_start:window_end]

        event_date = None
        m_full = _FULL_DATE_RE.search(search_text)
        if m_full:
            event_date = _resolve_full_date(int(m_full.group(1)), int(m_full.group(2)), today)
        else:
            m_numeric = _NUMERIC_DATE_RE.search(search_text)
            if m_numeric:
                month, day = int(m_numeric.group(1)), int(m_numeric.group(2))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    event_date = _resolve_full_date(month, day, today)
            if not event_date:
                m_day = _DAY_ONLY_RE.search(search_text)
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
