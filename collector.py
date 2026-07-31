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


_TITLE_SOURCE_SUFFIX_RE = re.compile(r"\s*[-–—]\s*[^-–—]{1,20}$")  # "제목 - 언론사명" 꼬리표 제거
_TITLE_NORMALIZE_RE = re.compile(r"[^\w가-힣]+")  # 공백/기호 제거 비교용


def _normalize_title_for_dedup(title):
    """
    구글 뉴스와 네이버 뉴스가 같은 기사를 서로 다른 링크로 줄 때도 같은 기사로
    인식하기 위해, 제목 끝의 "- 언론사명" 꼬리표를 떼고 공백/기호를 없애서 비교.
    """
    without_source = _TITLE_SOURCE_SUFFIX_RE.sub("", title)
    return _TITLE_NORMALIZE_RE.sub("", without_source).lower()


def _load_existing_news_titles(conn):
    """이미 저장된 뉴스 항목들의 정규화된 제목 집합을 반환 (중복 판정용)."""
    rows = conn.execute("SELECT title FROM items WHERE source_type = 'news'").fetchall()
    return {_normalize_title_for_dedup(row["title"]) for row in rows}


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
            normalized = _normalize_title_for_dedup(title)
            if normalized in seen_titles:
                continue  # 이미 (구글이든 네이버든) 같은 제목의 기사를 저장했음
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
    """
    네이버 검색 API 응답은 검색어를 <b>태그</b>로 감싸고, "&quot;" 같은 HTML
    엔티티도 그대로 줘서 둘 다 정리합니다.
    """
    without_tags = _NAVER_TAG_RE.sub("", text or "")
    return html.unescape(without_tags)


def _is_our_group(text):
    return any(keyword in text for keyword in CHART_KEYWORDS)


def _naver_pubdate_to_iso(pub_date_text):
    """'Mon, 27 Jul 2026 10:00:00 +0900' 형식을 UTC ISO로 변환."""
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(pub_date_text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def collect_naver_news(conn, seen_titles):
    """
    네이버 공식 검색 API(오픈 API)로 뉴스를 가져옵니다. 키가 없으면 조용히 건너뜁니다.
    """
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
            # 네이버 검색이 느슨하게 매칭해서 무관한 기사가 섞여 들어올 수 있어
            # 제목+본문에 실제로 우리 그룹 키워드가 있는지 한 번 더 확인
            # 본문 어딘가에 스쳐 지나가듯 언급된 것(예: "OOO축제에 존박·웬디·
            # 리센느 등 출연" 같은 라인업 나열 기사)까지 걸리는 걸 막기 위해,
            # 제목에 실제로 우리 그룹이 있는 기사만 인정 (본문은 보지 않음)
            if not _is_our_group(title):
                continue
            normalized = _normalize_title_for_dedup(title)
            if normalized in seen_titles:
                continue  # 구글 뉴스에서 이미 같은 제목의 기사를 저장했음
            is_new = insert_item(conn, "news", "네이버 뉴스", title, link, published_at, snippet)
            if is_new:
                new_count += 1
                seen_titles.add(normalized)
                print(f"  [신규/네이버뉴스] {title}")
    return new_count


def collect_naver_cafe(conn, seen_titles):
    """
    네이버 카페글 검색 API - 리시안셔스뿐 아니라 검색에 공개적으로 노출되는
    모든 네이버 카페의 게시글을 검색합니다. 브랜드 콜라보 후기 등 뉴스로는
    안 잡히는 소식을 잡기 위한 용도. 키가 없으면 조용히 건너뜁니다.
    """
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
    """
    네이버 블로그 검색 API - 개인 블로거의 방문 후기/콜라보 소식 등을 잡습니다.
    키가 없으면 조용히 건너뜁니다.
    """
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
        print("뉴스(구글) 수집 중...")
        seen_titles = _load_existing_news_titles(conn)
        news_new = collect_news(conn, seen_titles)
        print("뉴스(네이버) 수집 중...")
        naver_news_new = collect_naver_news(conn, seen_titles)
        print("커뮤니티(네이버 카페글) 수집 중...")
        cafe_new = collect_naver_cafe(conn, seen_titles)
        print("커뮤니티(네이버 블로그) 수집 중...")
        blog_new = collect_naver_blog(conn, seen_titles)
        print("뉴스에서 일정 추정 중...")
        schedule_new = collect_auto_schedule(conn)
    total = yt_new + collab_new + search_new + news_new + naver_news_new + cafe_new + blog_new
    print(
        f"\n완료: 신규 {total}건 "
        f"(공식 {yt_new} / 콜라보-등록 {collab_new} / 콜라보-검색 {search_new} / "
        f"뉴스-구글 {news_new} / 뉴스-네이버 {naver_news_new} / "
        f"카페글 {cafe_new} / 블로그 {blog_new}) "
        f"· 추정 일정 {schedule_new}건"
    )
    return total


if __name__ == "__main__":
    run_collection()
