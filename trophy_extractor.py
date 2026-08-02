# -*- coding: utf-8 -*-
"""
뉴스 기사 제목에서 "음악방송 이름 + 1위/정상" 패턴을 감지해서 수상 기록을
추출합니다. 스케줄 추출과 달리 날짜를 텍스트에서 따로 안 찾고, 기사 자체의
발행일(이미 알고 있음)을 그대로 수상일로 씁니다 - 수상 발표 기사는 보통
당일 바로 나오기 때문에 훨씬 신뢰도가 높습니다.
"""
import re

from config import RESCENE_ALL_SONGS, SONG_ALIASES
from kst import to_kst

_SHOW_KEYWORDS = [
    "엠카운트다운", "M COUNTDOWN", "엠카", "뮤직뱅크", "Music Bank", "뮤뱅",
    "인기가요", "Inkigayo", "인가",
    "음악중심", "쇼! 음악중심", "음중", "쇼챔피언", "Show Champion", "쇼챔",
    "더쇼", "The Show",
    "쇼케이스",  # 쇼케이스는 방송 이름은 아니지만 "1위 기념 쇼케이스"류 기사 방지용 제외 목록에 사용
]
# 줄임말이 매칭되면 이 정식 명칭으로 통일 (다른 기사가 전체 이름을 써도 같은 방송으로 인식되게)
_SHOW_CANONICAL = {
    "M COUNTDOWN": "엠카운트다운", "엠카": "엠카운트다운",
    "Music Bank": "뮤직뱅크", "뮤뱅": "뮤직뱅크",
    "Inkigayo": "인기가요", "인가": "인기가요",
    "쇼! 음악중심": "음악중심", "음중": "음악중심",
    "Show Champion": "쇼챔피언", "쇼챔": "쇼챔피언",
    "The Show": "더쇼",
}
_WIN_INDICATORS = ["1위", "정상"]
_EXCLUDE_KEYWORDS = ["쇼케이스"]  # 이 단어가 있으면 "1위 기념 행사" 기사일 뿐 수상 발표가 아닐 수 있어 제외


def _match_song(title):
    """제목에서 실제 곡명을 찾아냄 (영문/한글 발음 별칭 다 포함). 못 찾으면 None."""
    for song in RESCENE_ALL_SONGS:
        if song.lower() in title.lower():
            return song
        for alias in SONG_ALIASES.get(song, []):
            if alias in title:
                return song
    return None


def _match_show(title):
    """
    "1위/정상"이라는 표현과 가장 가까운 위치에 있는 방송명을 찾음.
    (예: "더쇼 이어 '음중'도 1위" 같은 제목은 앞쪽 "더쇼"가 아니라
    "1위" 바로 앞의 "음중"이 실제로 이번에 수상한 방송이므로)
    """
    lower_title = title.lower()
    win_positions = [lower_title.find(w.lower()) for w in _WIN_INDICATORS]
    win_positions = [p for p in win_positions if p != -1]
    if not win_positions:
        return None
    win_pos = min(win_positions)

    best_show = None
    best_distance = None
    for show in _SHOW_KEYWORDS:
        if show == "쇼케이스":
            continue
        idx = lower_title.find(show.lower())
        if idx == -1:
            continue
        distance = abs(idx - win_pos)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_show = show
    return _SHOW_CANONICAL.get(best_show, best_show)


def extract_trophy_candidates(news_items):
    """
    news_items: db.get_recent_items()에서 source_type == 'news'인 항목들
    반환: [{"date": "YYYY-MM-DD", "show": ..., "song": ..., "title": ..., "source_link": ...}, ...]
    """
    candidates = []
    seen_keys = set()

    for item in news_items:
        title = item["title"]
        if any(ex in title for ex in _EXCLUDE_KEYWORDS):
            continue
        if not any(ind in title for ind in _WIN_INDICATORS):
            continue

        matched_show = _match_show(title)
        if not matched_show:
            continue

        matched_song = _match_song(title)
        if not matched_song:
            continue  # 곡명을 특정 못 하면 신뢰도가 낮으니 트로피로 안 잡음

        raw_date = item["published_at"] or item["fetched_at"]
        try:
            event_date = to_kst(raw_date).strftime("%Y-%m-%d")
        except Exception:
            continue

        key = (event_date, matched_show, matched_song)
        if key in seen_keys:
            continue  # 같은 날 같은 방송 같은 곡 수상 기사가 여러 언론사에서 나온 경우 하나만
        seen_keys.add(key)

        candidates.append(
            {
                "date": event_date,
                "show": matched_show,
                "song": matched_song,
                "title": title[:80],
                "source_link": item["link"],
            }
        )

    return candidates
