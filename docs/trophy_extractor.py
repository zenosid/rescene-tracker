# -*- coding: utf-8 -*-
"""
뉴스 기사 제목에서 두 종류의 수상 기록을 추출합니다.
1) 음악방송 1위 - "방송 이름 + 1위/정상" 패턴 (기존)
2) 시상식 수상 - "시상식 이름 + 상 이름 + 수상 관련 표현" 패턴 (신규)

둘 다 날짜를 텍스트에서 따로 안 찾고, 기사 자체의 발행일(이미 알고 있음)을
그대로 수상일로 씁니다 - 수상 발표 기사는 보통 당일 바로 나오기 때문에
훨씬 신뢰도가 높습니다.
"""
import re

from config import RESCENE_ALL_SONGS, SONG_ALIASES, CHART_KEYWORDS, MEMBER_KEYWORDS
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


# ── 시상식 수상 ──────────────────────────────────────────────
# 시상식은 매년 여러 아티스트를 한꺼번에 다루는 기사가 많아서(라인업 기사 등),
# 실제로 우리 그룹/멤버가 언급된 기사인지 먼저 확인해야 함
_AWARD_CEREMONY_KEYWORDS = [
    "AAA", "아시아 아티스트 어워즈",
    "MMA", "멜론뮤직어워드", "멜론 뮤직 어워드",
    "골든디스크", "Golden Disc",
    "MAMA", "엠넷 아시안 뮤직 어워드",
    "서울가요대상", "서울가요대상",
    "하이큐어워즈", "하이큐 어워즈",
    "가온차트뮤직어워즈", "가온차트 뮤직 어워즈",
    "케이월드드림어워즈", "K-월드 드림 어워즈",
    "지니뮤직어워드",
    "SBS가요대전", "SBS 가요대전",
    "MBC가요대제전", "MBC 가요대제전",
    "KBS가요대축제", "KBS 가요대축제",
]
_AWARD_TYPE_KEYWORDS = [
    "대상", "본상", "신인상", "인기상", "베스트", "뉴웨이브상",
    "글로벌", "핫트렌드상", "포토제닉상", "월드퍼포먼스상", "차세대",
]
_AWARD_WIN_INDICATORS = ["수상", "받았다", "받아", "차지", "영예", "거머쥐"]

# 트로피 곡 매칭과 달리, 시상식은 곡이 아니라 그룹/멤버 단위 수상이 많아서
# 그룹명 표기 변형 + 멤버 이름까지 폭넓게 확인 (schedule/collector와 같은 원칙)
_MEMBER_NAMES = list(MEMBER_KEYWORDS.keys())
_GROUP_NAME_VARIANTS = [kw.lower() for kw in CHART_KEYWORDS] + ["르센느", "이센느"]


def _is_our_group_or_member(title):
    lowered = title.lower()
    if any(kw in lowered for kw in _GROUP_NAME_VARIANTS):
        return True
    return any(name in title for name in _MEMBER_NAMES)


def _match_award_ceremony(title):
    for ceremony in _AWARD_CEREMONY_KEYWORDS:
        if ceremony.lower() in title.lower():
            return ceremony
    return None


def _match_award_type(title):
    for award_type in _AWARD_TYPE_KEYWORDS:
        if award_type in title:
            return award_type
    return None


def extract_award_candidates(news_items):
    """
    news_items: db.get_recent_items()에서 source_type == 'news'인 항목들
    반환: [{"date": ..., "ceremony": ..., "award_name": ..., "title": ..., "source_link": ...}, ...]

    ⚠️ 시상식 이름과 상 이름 둘 중 하나만 확인되면 잡습니다(둘 다 있으면
       더 정확하지만, "OOO 신인상 수상" 처럼 시상식 이름 없이 상 이름만
       나오는 제목도 많아서). 다만 반드시 우리 그룹/멤버 언급 + 수상 표현이
       같이 있어야만 후보로 잡습니다.
    """
    candidates = []
    seen_keys = set()

    for item in news_items:
        title = item["title"]
        if not _is_our_group_or_member(title):
            continue
        if not any(ind in title for ind in _AWARD_WIN_INDICATORS):
            continue

        ceremony = _match_award_ceremony(title)
        award_name = _match_award_type(title)
        if not ceremony and not award_name:
            continue  # 시상식 이름도 상 이름도 없으면 신뢰도가 낮으니 건너뜀

        raw_date = item["published_at"] or item["fetched_at"]
        try:
            event_date = to_kst(raw_date).strftime("%Y-%m-%d")
        except Exception:
            continue

        key = (event_date, ceremony, award_name)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        candidates.append(
            {
                "date": event_date,
                "ceremony": ceremony or "시상식",
                "award_name": award_name,
                "title": title[:80],
                "source_link": item["link"],
            }
        )

    return candidates
