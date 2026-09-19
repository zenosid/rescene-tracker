# -*- coding: utf-8 -*-
"""
YouTube 채널 RSS + 뉴스 RSS를 수집해서 DB에 저장.
API 키가 전혀 필요 없는 무료 수집 단계입니다.

실행: python collector.py
"""
import html
import os
import re
import json
import feedparser
import requests
from datetime import datetime, timezone, timedelta

from config import (
    YOUTUBE_CHANNELS, NEWS_RSS_FEEDS, COLLAB_CHANNELS,
    CHART_KEYWORDS, MEMBER_KEYWORDS, SEARCH_QUERIES, SEARCH_MIN_VIEWS,
    NAVER_NEWS_QUERIES, NAVER_NEWS_MAX_RESULTS,
    NAVER_CAFE_QUERIES, NAVER_CAFE_MAX_RESULTS,
    NAVER_BLOG_QUERIES, NAVER_BLOG_MAX_RESULTS,
    RESCENE_ALL_SONGS,
)
from db import (
    init_db, get_conn, insert_item, get_recent_items, insert_auto_schedule,
    insert_trophy, insert_award,
)
from schedule_extractor import extract_schedule_candidates
from trophy_extractor import extract_trophy_candidates, extract_award_candidates
from x_collector import collect_x
from moderation_scan import scan_for_moderation

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
_COLLAB_MATCH_KEYWORDS = [kw.lower() for kw in CHART_KEYWORDS] + [
    "르센느", "이센느", "resene", "ricenne",
] + [
    kw.lower() for kws in MEMBER_KEYWORDS.values() for kw in kws
] + [
    song.lower() for song in RESCENE_ALL_SONGS
]

_RELATIVE_TIME_UNITS = {
    "second": 1, "minute": 60, "hour": 3600,
    "day": 86400, "week": 604800, "month": 2629800, "year": 31557600,
}


def _is_relevant_to_us(title):
    lowered = title.lower()
    return any(kw in lowered for kw in _COLLAB_MATCH_KEYWORDS)


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
            video_id = entry.get("yt_videoid")
            link = f"https://www.youtube.com/watch?v={video_id}" if video_id else entry.get("link", "")
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
                continue
            video_id = entry.get("yt_videoid")
            link = f"https://www.youtube.com/watch?v={video_id}" if video_id else entry.get("link", "")
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
            if not _is_relevant_to_us(title):
                continue

            byline_node = v.get("longBylineText") or v.get("ownerText")
            channel = _get_text(byline_node) or "알 수 없음"
            channel_id = _get_channel_id(byline_node)
            view_text = _get_text(v.get("viewCountText"))
            view_count = _parse_view_count(view_text)

            if channel_id and channel_id in _OFFICIAL_CHANNEL_IDS:
                continue
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


_TITLE_SOURCE_SUFFIX_RE = re.compile(r"\s*[-–—]\s*[^-–—]{1,20}$")
_TITLE_NORMALIZE_RE = re.compile(r"[^\w가-힣]+")


def _normalize_title_for_dedup(title):
    without_source = _TITLE_SOURCE_SUFFIX_RE.sub("", title)
    return _TITLE_NORMALIZE_RE.sub("", without_source).lower()


def _load_existing_news_titles(conn):
    rows = conn.execute("SELECT title FROM items WHERE source_type = 'news'").fetchall()
    return {_normalize_title_for_dedup(row["title"]) for row in rows}


def _is_our_group(text):
    lowered = text.lower()
    group_variants = [kw.lower() for kw in CHART_KEYWORDS] + ["르센느", "이센느"]
    if any(kw in lowered for kw in group_variants):
        return True
    return any(name in text for name in MEMBER_KEYWORDS.keys())


def collect_news(conn, seen_titles):
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
            if not _is_our_group(title):
                continue
            normalized = _normalize_title_for_dedup(title)
            if normalized in seen_titles:
                continue
            is_new = insert_item(
                conn, "news", feed_conf["name"], title, link, published_at, snippet
            )
            if is_new:
                new_count += 1
                seen_titles.add(normalized)
                print(f"  [신규/뉴스] {feed_conf['name']} - {title}")
    return new_count


_NAVER_TAG_RE = re.compile(r"</?b>")


def _strip_naver_tags(text):
    without_tags = _NAVER_TAG_RE.sub("", text or "")
    return html.unescape(without_tags)


def _naver_pubdate_to_iso(pub_date_text):
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(pub_date_text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def collect_naver_news(conn, seen_titles):
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("NAVER_CLIENT_ID/SECRET이 설정되어 있지 않아 네이버 뉴스 수집을 건너뜁니다.")
        return 0

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    new_count = 0
    for query in NAVER_NEWS_QUERIES:
        try:
            r = requests.get(
                "https://openapi.naver.com/v1/search/news.json",
                headers=headers,
                params={"query": query, "display": NAVER_NEWS_MAX_RESULTS, "sort": "date"},
                timeout=15,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  [경고] 네이버 뉴스 검색 실패 ({query}): {e}")
            continue

        for item in r.json().get("items", []):
            title = _strip_naver_tags(item.get("title", "(제목 없음)"))
            link = item.get("originallink") or item.get("link", "")
            snippet = _strip_naver_tags(item.get("description", ""))[:500]
            published_at = _naver_pubdate_to_iso(item.get("pubDate", ""))
            if not link:
                continue
            if not _is_our_group(title):
                continue
            normalized = _normalize_title_for_dedup(title)
            if normalized in seen_titles:
                continue
            is_new = insert_item(conn, "news", "네이버 뉴스", title, link, published_at, snippet)
            if is_new:
                new_count += 1
                seen_titles.add(normalized)
                print(f"  [신규/네이버뉴스] {title}")
    return new_count


def collect_naver_cafe(conn, seen_titles):
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return 0

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    new_count = 0
    for query in NAVER_CAFE_QUERIES:
        try:
            r = requests.get(
                "https://openapi.naver.com/v1/search/cafearticle.json",
                headers=headers,
                params={"query": query, "display": NAVER_CAFE_MAX_RESULTS, "sort": "date"},
                timeout=15,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  [경고] 네이버 카페글 검색 실패 ({query}): {e}")
            continue

        for item in r.json().get("items", []):
            title = _strip_naver_tags(item.get("title", "(제목 없음)"))
            link = item.get("link", "")
            snippet = _strip_naver_tags(item.get("description", ""))[:500]
            cafe_name = _strip_naver_tags(item.get("cafename", "네이버 카페"))
            if not link or not _is_our_group(title):
                continue
            normalized = _normalize_title_for_dedup(title)
            if normalized in seen_titles:
                continue
            is_new = insert_item(
                conn, "community", f"네이버 카페 · {cafe_name}", title, link,
                datetime.now(timezone.utc).isoformat(), snippet,
            )
            if is_new:
                new_count += 1
                seen_titles.add(normalized)
                print(f"  [신규/카페글] {cafe_name} - {title}")
    return new_count


def collect_naver_blog(conn, seen_titles):
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return 0

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    new_count = 0
    for query in NAVER_BLOG_QUERIES:
        try:
            r = requests.get(
                "https://openapi.naver.com/v1/search/blog.json",
                headers=headers,
                params={"query": query, "display": NAVER_BLOG_MAX_RESULTS, "sort": "date"},
                timeout=15,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  [경고] 네이버 블로그 검색 실패 ({query}): {e}")
            continue

        for item in r.json().get("items", []):
            title = _strip_naver_tags(item.get("title", "(제목 없음)"))
            link = item.get("link", "")
            snippet = _strip_naver_tags(item.get("description", ""))[:500]
            blogger_name = _strip_naver_tags(item.get("bloggername", "네이버 블로그"))
            if not link or not _is_our_group(title):
                continue
            normalized = _normalize_title_for_dedup(title)
            if normalized in seen_titles:
                continue
            is_new = insert_item(
                conn, "community", f"네이버 블로그 · {blogger_name}", title, link,
                datetime.now(timezone.utc).isoformat(), snippet,
            )
            if is_new:
                new_count += 1
                seen_titles.add(normalized)
                print(f"  [신규/블로그] {blogger_name} - {title}")
    return new_count


def collect_auto_schedule(conn):
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


def collect_trophies(conn):
    """이미 수집된 뉴스에서 음악방송 1위 수상 기록을 추출."""
    news_items = [i for i in get_recent_items(conn, limit=1000) if i["source_type"] == "news"]
    candidates = extract_trophy_candidates(news_items)
    new_count = 0
    for c in candidates:
        is_new = insert_trophy(conn, c["date"], c["show"], c["song"], c["title"], c["source_link"])
        if is_new:
            new_count += 1
            print(f"  [신규/트로피] {c['date']} {c['show']} - {c['song']}")
    return new_count


def collect_awards(conn):
    """이미 수집된 뉴스에서 시상식 수상 기록을 추출."""
    news_items = [i for i in get_recent_items(conn, limit=1000) if i["source_type"] == "news"]
    candidates = extract_award_candidates(news_items)
    new_count = 0
    for c in candidates:
        is_new = insert_award(conn, c["date"], c["ceremony"], c["award_name"], c["title"], c["source_link"])
        if is_new:
            new_count += 1
            print(f"  [신규/시상식] {c['date']} {c['ceremony']} - {c['award_name']}")
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
        print("뉴스(구글) 수집 중...")
        seen_titles = _load_existing_news_titles(conn)
        news_new = collect_news(conn, seen_titles)
        print("뉴스(네이버) 수집 중...")
        naver_news_new = collect_naver_news(conn, seen_titles)
        print("커뮤니티(네이버 카페글) 수집 중...")
        cafe_new = collect_naver_cafe(conn, seen_titles)
        print("커뮤니티(네이버 블로그) 수집 중...")
        blog_new = collect_naver_blog(conn, seen_titles)
        print("X(트위터) 수집 중... (토큰 없으면 건너뜀)")
        x_new = collect_x(conn)
        print("뉴스에서 일정 추정 중...")
        schedule_new = collect_auto_schedule(conn)
        print("뉴스에서 1위 수상 기록 추출 중...")
        trophy_new = collect_trophies(conn)
        print("뉴스에서 시상식 수상 기록 추출 중...")
        award_new = collect_awards(conn)
        print("모더레이션(악플/부적절 콘텐츠 후보) 검토용 스캔 중...")
        moderation_new = scan_for_moderation(conn)
    total = yt_new + collab_new + search_new + news_new + naver_news_new + cafe_new + blog_new + x_new
    print(
        f"\n완료: 신규 {total}건 "
        f"(공식 {yt_new} / 콜라보-등록 {collab_new} / 콜라보-검색 {search_new} / "
        f"뉴스-구글 {news_new} / 뉴스-네이버 {naver_news_new} / "
        f"카페글 {cafe_new} / 블로그 {blog_new} / X {x_new}) "
        f"· 추정 일정 {schedule_new}건 · 신규 트로피 {trophy_new}건 · "
        f"신규 시상식 {award_new}건 · "
        f"모더레이션 검토대상 {moderation_new}건"
    )
    return total


if __name__ == "__main__":
    run_collection()
