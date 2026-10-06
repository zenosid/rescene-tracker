# -*- coding: utf-8 -*-
"""
리센느 콜라보·팝업 소식 수집기 (6시간 주기 권장).

수집원 (모두 공개 검색/공식 API):
  1) Google 뉴스 RSS  - 키 불필요
  2) 네이버 뉴스·블로그·카페 검색 API - NAVER_CLIENT_ID/SECRET 없으면 건너뜀
  3) X 검색 API - X_BEARER_TOKEN 없으면 건너뜀 (조회당 과금이라 쿼리를 최소화)
  4) 이미 아카이브(items)에 쌓인 뉴스/커뮤니티/X 글도 한 번 더 훑음 (추가 비용 없음)
인스타그램은 자동 수집이 불가능해서 config.EVENT_ITEMS에 수동 등록합니다.

실행: python event_collector.py
"""
import os
import html
import re
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests

from config import EVENT_SEARCH_QUERIES, EVENT_X_QUERIES, EVENT_MAX_RESULTS
from db import init_db, get_conn, insert_event_mention
from event_extractor import detect_event, extract_instagram_links

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_naver_tags(text):
    return html.unescape(_TAG_RE.sub("", text or ""))


def _naver_pubdate_to_iso(text):
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _parsed_time_to_iso(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"


def _save(conn, title, link, source_name, published_at, snippet="", is_news=True, extra_text=""):
    ev = detect_event(title, snippet)
    if not ev or not link:
        return 0
    # 뉴스가 아닌 글(X/카페/블로그)은 팬의 후기·잡담이 많아서, 브랜드를 특정할 수
    # 있을 때만 소식으로 인정 (뉴스는 브랜드 불명이어도 통과)
    if not is_news and not ev["brand"]:
        return 0
    # 인스타그램 링크: X 게시물의 펼친 URL·본문, 블로그/카페 요약에서 찾음 (첫 번째만 보관)
    igs = extract_instagram_links(f"{extra_text} {snippet} {title}")
    ok = insert_event_mention(
        conn, ev["kind"], ev["brand"], title, link, source_name, published_at,
        ev["period_text"], is_news, igs[0] if igs else None,
    )
    if ok:
        print(f"  [신규/{ev['kind']}] {source_name} - {title[:60]}")
    return 1 if ok else 0


def collect_google_news(conn):
    n = 0
    for q in EVENT_SEARCH_QUERIES:
        feed = feedparser.parse(GOOGLE_NEWS_RSS.format(q=quote(q)))
        for e in feed.entries:
            src = (e.get("source") or {}).get("title", "") or "Google 뉴스"
            n += _save(conn, e.get("title", ""), e.get("link", ""), f"Google 뉴스 · {src}",
                       _parsed_time_to_iso(e), _strip_naver_tags(e.get("summary", ""))[:300], True)
    return n


_NAVER_ENDPOINTS = [
    ("news", "https://openapi.naver.com/v1/search/news.json", "네이버 뉴스"),
    ("blog", "https://openapi.naver.com/v1/search/blog.json", "네이버 블로그"),
    ("cafe", "https://openapi.naver.com/v1/search/cafearticle.json", "네이버 카페"),
]


def collect_naver(conn):
    cid, secret = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")
    if not cid or not secret:
        print("NAVER 키가 없어 네이버 콜라보·팝업 수집을 건너뜁니다.")
        return 0
    headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret}
    n = 0
    for kind, url, label in _NAVER_ENDPOINTS:
        for q in EVENT_SEARCH_QUERIES:
            try:
                r = requests.get(url, headers=headers, timeout=15,
                                 params={"query": q, "display": EVENT_MAX_RESULTS, "sort": "date"})
                r.raise_for_status()
            except requests.RequestException as ex:
                print(f"  [경고] {label} 검색 실패 ({q}): {ex}")
                continue
            for it in r.json().get("items", []):
                title = _strip_naver_tags(it.get("title", ""))
                snippet = _strip_naver_tags(it.get("description", ""))[:300]
                if kind == "news":
                    link = it.get("originallink") or it.get("link", "")
                    published = _naver_pubdate_to_iso(it.get("pubDate", ""))
                    name = label
                else:
                    link = it.get("link", "")
                    published = datetime.now(timezone.utc).isoformat()
                    name = f"{label} · {_strip_naver_tags(it.get('cafename') or it.get('bloggername') or '')}"
                n += _save(conn, title, link, name, published, snippet, is_news=(kind == "news"))
    return n


def _fetch_x_with_urls(token, query, max_results):
    """x_collector와 같은 검색이지만 entities(펼친 URL)까지 받아 인스타 링크를 찾을 수 있게 함."""
    params = {
        "query": f"{query} -is:retweet lang:ko",
        "max_results": min(max(max_results, 10), 100),
        "tweet.fields": "created_at,author_id,entities",
        "expansions": "author_id",
        "user.fields": "username",
    }
    r = requests.get("https://api.x.com/2/tweets/search/recent",
                     headers={"Authorization": f"Bearer {token}"}, params=params, timeout=15)
    if r.status_code != 200:
        return [], f"HTTP {r.status_code} - {r.text[:200]}"
    data = r.json()
    users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}
    out = []
    for t in data.get("data", []):
        uname = users.get(t.get("author_id"), "unknown")
        urls = " ".join(u.get("expanded_url") or u.get("unwound_url") or ""
                        for u in (t.get("entities") or {}).get("urls", []))
        out.append({"text": t.get("text", ""), "username": uname, "created_at": t.get("created_at", ""),
                    "link": f"https://x.com/{uname}/status/{t['id']}", "urls": urls})
    return out, None


def collect_x_events(conn):
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        print("X_BEARER_TOKEN이 없어 X 콜라보·팝업 수집을 건너뜁니다.")
        return 0
    n = 0
    for q in EVENT_X_QUERIES:
        tweets, err = _fetch_x_with_urls(token, q, EVENT_MAX_RESULTS)
        if err:
            print(f"  [경고] X 검색 실패 ({q}): {err}")
            continue
        for t in tweets:
            title = t["text"][:100].replace("\n", " ")
            n += _save(conn, title, t["link"], f"X · @{t['username']}", t["created_at"], t["text"][:300], False, t["urls"])
    return n


def scan_archive(conn):
    """이미 수집된 아카이브 글(뉴스/커뮤니티/X)에서 추가로 소식 후보를 찾음."""
    rows = conn.execute(
        "SELECT title, link, source_name, source_type, published_at, snippet FROM items "
        "WHERE source_type IN ('news','community','x')"
    ).fetchall()
    n = 0
    for r in rows:
        n += _save(conn, r["title"], r["link"], r["source_name"], r["published_at"],
                   r["snippet"] or "", is_news=(r["source_type"] == "news"))
    return n


def run_event_collection():
    init_db()
    with get_conn() as conn:
        g = collect_google_news(conn)
        nv = collect_naver(conn)
        x = collect_x_events(conn)
        a = scan_archive(conn)
    print(f"\n완료: 콜라보·팝업 신규 {g + nv + x + a}건 "
          f"(Google {g} / 네이버 {nv} / X {x} / 아카이브 재검사 {a})")
    return g + nv + x + a


if __name__ == "__main__":
    run_event_collection()
