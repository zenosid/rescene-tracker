# -*- coding: utf-8 -*-
"""
YouTube 채널 RSS + 뉴스 RSS를 수집해서 DB에 저장.
API 키가 전혀 필요 없는 무료 수집 단계입니다.

실행: python collector.py
"""
import re
import json
import feedparser
import requests
from datetime import datetime, timezone, timedelta

from config import (
    YOUTUBE_CHANNELS, NEWS_RSS_FEEDS, COLLAB_CHANNELS,
    CHART_KEYWORDS, MEMBER_KEYWORDS, SEARCH_QUERIES, SEARCH_MIN_VIEWS,
)
from db import init_db, get_conn, insert_item, get_recent_items, insert_auto_schedule
from schedule_extractor import extract_schedule_candidates

YOUTUBE_RSS_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
YOUTUBE_SEARCH_URL = "https://www.youtube.com/results?search_query={query}"

SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    # 상대 시간 텍스트("2 weeks ago")를 일정한 형식으로 받기 위해 영어로 고정
    "Accept-Language": "en-US,en;q=0.9",
}

# 검색 결과 중, 이미 공식 채널로 등록된 곳은 여기서 다시 수집하지 않음 (중복 방지)
# 이름이 아니라 채널 ID로 비교해야 정확합니다 (표시 이름이 다를 수 있음, 예:
# 우리가 등록한 이름은 "RESCENE 공식 유튜브"지만 실제 채널 표시 이름은 "RESCENE").
_OFFICIAL_CHANNEL_IDS = {ch["channel_id"] for ch in YOUTUBE_CHANNELS}

# 콜라보 채널에서 "리센느 관련 영상"으로 인정할 키워드 (그룹명 + 멤버 이름 전체)
_COLLAB_MATCH_KEYWORDS = list(CHART_KEYWORDS) + [
    kw for kws in MEMBER_KEYWORDS.values() for kw in kws
]

_RELATIVE_TIME_UNITS = {
    "second": 1, "minute": 60, "hour": 3600,
    "day": 86400, "week": 604800, "month": 2629800, "year": 31557600,
}


def _is_relevant_to_us(title):
    return any(kw in title for kw in _COLLAB_MATCH_KEYWORDS)


def _parsed_time_to_iso(entry):
    """feedparser의 struct_time을 ISO 문자열로 변환. 없으면 현재 시각."""
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _get_text(node):
    """유튜브 검색 결과 JSON의 simpleText/runs 형태를 일반 문자열로 변환."""
    if not node:
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    if "runs" in node:
        return "".join(r.get("text", "") for r in node["runs"])
    return ""


def _parse_view_count(view_text):
    m = re.search(r"([\d,]+)", view_text)
    return int(m.group(1).replace(",", "")) if m else 0


def _parse_relative_time_to_iso(text):
    """'2 weeks ago', 'Streamed 3 days ago' 등을 대략적인 ISO 시각으로 변환."""
    now = datetime.now(timezone.utc)
    m = re.search(r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", text)
    if not m:
        return now.isoformat()
    n, unit = int(m.group(1)), m.group(2)
    return (now - timedelta(seconds=n * _RELATIVE_TIME_UNITS[unit])).isoformat()


def _get_channel_id(byline_node):
    """longBylineText/ownerText에서 채널 ID(browseId)를 추출."""
    try:
        run = byline_node["runs"][0]
        return run["navigationEndpoint"]["browseEndpoint"]["browseId"]
    except (KeyError, IndexError, TypeError):
        return None
def _find_video_renderers(obj, results):
    """유튜브 검색 결과 JSON(ytInitialData)에서 videoRenderer 블록만 재귀적으로 추출."""
    if isinstance(obj, dict):
        if "videoRenderer" in obj:
            results.append(obj["videoRenderer"])
        for v in obj.values():
            _find_video_renderers(v, results)
    elif isinstance(obj, list):
        for v in obj:
            _find_video_renderers(v, results)


def collect_youtube(conn):
    new_count = 0
    for ch in YOUTUBE_CHANNELS:
        url = YOUTUBE_RSS_TEMPLATE.format(channel_id=ch["channel_id"])
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            print(f"  [경고] {ch['name']} RSS 파싱 실패 (채널 ID 확인 필요)")
            continue
        for entry in feed.entries:
            title = entry.get("title", "(제목 없음)")
            link = entry.get("link", "")
            published_at = _parsed_time_to_iso(entry)
            snippet = entry.get("summary", "")[:500]
            if not link:
                continue
            is_new = insert_item(
                conn, "youtube", ch["name"], title, link, published_at, snippet
            )
            if is_new:
                new_count += 1
                print(f"  [신규/유튜브] {ch['name']} - {title}")
    return new_count


def collect_collab(conn):
    """수동 등록된 콜라보 채널에서 리센느(또는 멤버 이름)가 제목에 들어간 영상만 수집."""
    new_count = 0
    for ch in COLLAB_CHANNELS:
        url = YOUTUBE_RSS_TEMPLATE.format(channel_id=ch["channel_id"])
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            print(f"  [경고] {ch['name']} RSS 파싱 실패 (채널 ID 확인 필요)")
            continue
        for entry in feed.entries:
            title = entry.get("title", "(제목 없음)")
            if not _is_relevant_to_us(title):
                continue  # 리센느와 무관한 영상은 건너뜀
            link = entry.get("link", "")
            published_at = _parsed_time_to_iso(entry)
            snippet = entry.get("summary", "")[:500]
            if not link:
                continue
            is_new = insert_item(
                conn, "youtube_collab", ch["name"], title, link, published_at, snippet
            )
            if is_new:
                new_count += 1
                print(f"  [신규/콜라보] {ch['name']} - {title}")
    return new_count


def collect_collab_by_search(conn):
    """
    채널을 미리 등록하지 않아도, 유튜브 검색으로 '리센느' 관련 영상을 찾아서
    조회수가 SEARCH_MIN_VIEWS 이상이면 채널 상관없이 자동 수집.
    (공개 검색 페이지를 개인 사용 목적으로 저빈도 조회합니다.)
    """
    new_count = 0
    seen_video_ids = set()

    for query in SEARCH_QUERIES:
        url = YOUTUBE_SEARCH_URL.format(query=requests.utils.quote(query))
        try:
            r = requests.get(url, headers=SEARCH_HEADERS, timeout=15)
        except Exception as e:
            print(f"  [경고] 검색 실패 ({query}): {e}")
            continue

        m = re.search(r"var ytInitialData = (\{.*?\});</script>", r.text)
        if not m:
            print(f"  [경고] 검색 결과 파싱 실패 ({query}) - 유튜브 페이지 구조가 바뀌었을 수 있습니다.")
            continue

        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            print(f"  [경고] 검색 결과 JSON 파싱 실패 ({query})")
            continue

        video_renderers = []
        _find_video_renderers(data, video_renderers)

        for v in video_renderers:
            video_id = v.get("videoId")
            if not video_id or video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)

            title = _get_text(v.get("title"))
            byline_node = v.get("longBylineText") or v.get("ownerText")
            channel = _get_text(byline_node) or "알 수 없음"
            channel_id = _get_channel_id(byline_node)
            view_text = _get_text(v.get("viewCountText"))
            view_count = _parse_view_count(view_text)

            if channel_id and channel_id in _OFFICIAL_CHANNEL_IDS:
                continue  # 이미 공식 채널 RSS로 수집되는 채널은 건너뜀
            if view_count < SEARCH_MIN_VIEWS:
                continue

            published_text = _get_text(v.get("publishedTimeText"))
            published_at = _parse_relative_time_to_iso(published_text) if published_text else datetime.now(timezone.utc).isoformat()
            link = f"https://www.youtube.com/watch?v={video_id}"
            snippet = f"조회수 {view_count:,}회 · {channel}"

            is_new = insert_item(
                conn, "youtube_collab", channel, title, link, published_at, snippet
            )
            if is_new:
                new_count += 1
                print(f"  [신규/콜라보-검색] {channel} ({view_count:,}회) - {title}")

    return new_count


def collect_news(conn):
    new_count = 0
    for feed_conf in NEWS_RSS_FEEDS:
        feed = feedparser.parse(feed_conf["url"])
        for entry in feed.entries:
            title = entry.get("title", "(제목 없음)")
            link = entry.get("link", "")
            published_at = _parsed_time_to_iso(entry)
            snippet = entry.get("summary", "")[:500]
            if not link:
                continue
            is_new = insert_item(
                conn, "news", feed_conf["name"], title, link, published_at, snippet
            )
            if is_new:
                new_count += 1
                print(f"  [신규/뉴스] {feed_conf['name']} - {title}")
    return new_count


def collect_auto_schedule(conn):
    """이미 수집된 뉴스 전체를 스캔해서 일정 후보를 추출 (중복은 UNIQUE 제약으로 자동 방지)."""
    news_items = [i for i in get_recent_items(conn, limit=1000) if i["source_type"] == "news"]
    candidates = extract_schedule_candidates(news_items)
    new_count = 0
    for c in candidates:
        is_new = insert_auto_schedule(
            conn, c["date"], c["type"], c["title"], c["note"], c["source_link"]
        )
        if is_new:
            new_count += 1
            print(f"  [신규/추정일정] {c['date']} {c['type']} - {c['title']}")
    return new_count


def run_collection():
    init_db()
    with get_conn() as conn:
        print("유튜브(공식) 수집 중...")
        yt_new = collect_youtube(conn)
        print("유튜브(콜라보-등록채널) 수집 중...")
        collab_new = collect_collab(conn)
        print("유튜브(콜라보-검색발견) 수집 중...")
        search_new = collect_collab_by_search(conn)
        print("뉴스 수집 중...")
        news_new = collect_news(conn)
        print("뉴스에서 일정 추정 중...")
        schedule_new = collect_auto_schedule(conn)
    total = yt_new + collab_new + search_new + news_new
    print(
        f"\n완료: 신규 {total}건 "
        f"(공식 {yt_new} / 콜라보-등록 {collab_new} / 콜라보-검색 {search_new} / 뉴스 {news_new}) "
        f"· 추정 일정 {schedule_new}건"
    )
    return total


if __name__ == "__main__":
    run_collection()
