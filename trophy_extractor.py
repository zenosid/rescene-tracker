# -*- coding: utf-8 -*-
"""
뉴스 기사 제목에서 "음악방송 이름 + 1위/정상" 패턴을 감지해서 수상 기록을
추출합니다. 스케줄 추출과 달리 날짜를 텍스트에서 따로 안 찾고, 기사 자체의
발행일(이미 알고 있음)을 그대로 수상일로 씁니다 - 수상 발표 기사는 보통
당일 바로 나오기 때문에 훨씬 신뢰도가 높습니다.
"""
import re

from kst import to_kst

_SHOW_KEYWORDS = [
    "엠카운트다운", "M COUNTDOWN", "뮤직뱅크", "Music Bank", "인기가요", "Inkigayo",
    "음악중심", "쇼! 음악중심", "쇼챔피언", "Show Champion", "더쇼", "The Show",
    "쇼케이스",  # 쇼케이스는 방송 이름은 아니지만 "1위 기념 쇼케이스"류 기사 방지용 제외 목록에 사용
]
_WIN_INDICATORS = ["1위", "정상"]
_EXCLUDE_KEYWORDS = ["쇼케이스"]  # 이 단어가 있으면 "1위 기념 행사" 기사일 뿐 수상 발표가 아닐 수 있어 제외


def extract_trophy_candidates(news_items):
    """
    news_items: db.get_recent_items()에서 source_type == 'news'인 항목들
    반환: [{"date": "YYYY-MM-DD", "show": ..., "title": ..., "source_link": ...}, ...]
    """
    candidates = []
    seen_keys = set()

    for item in news_items:
        title = item["title"]
        if any(ex in title for ex in _EXCLUDE_KEYWORDS):
            continue
        if not any(ind in title for ind in _WIN_INDICATORS):
            continue

        matched_show = None
        for show in _SHOW_KEYWORDS:
            if show.lower() in title.lower() and show != "쇼케이스":
                matched_show = show
                break
        if not matched_show:
            continue

        raw_date = item["published_at"] or item["fetched_at"]
        try:
            event_date = to_kst(raw_date).strftime("%Y-%m-%d")
        except Exception:
            continue

        key = (event_date, matched_show)
        if key in seen_keys:
            continue  # 같은 날 같은 방송 수상 기사가 여러 언론사에서 나온 경우 하나만
        seen_keys.add(key)

        candidates.append(
            {
                "date": event_date,
                "show": matched_show,
                "title": title[:80],
                "source_link": item["link"],
            }
        )

    return candidates
