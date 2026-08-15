# -*- coding: utf-8 -*-
"""
X(트위터) 공식 API(v2 검색 엔드포인트)로 "리센느"/"RESCENE" 언급 게시물을
가져옵니다. 2026년 2월부터 완전 종량제(조회 1건당 $0.005)라 비용이 들고,
X_BEARER_TOKEN 환경변수가 없으면 조용히 건너뜁니다.

비용을 아끼기 위해 자주 돌릴 필요는 없어서, 공식 스케줄/플로 차트와 같은
6시간 주기 워크플로에 포함시키는 걸 권장합니다.

실행: python x_collector.py
"""
import os

import requests

from config import X_SEARCH_QUERIES, X_SEARCH_MAX_RESULTS, CHART_KEYWORDS
from db import init_db, get_conn, insert_item

X_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"


def _is_our_group(text):
    return any(keyword in text for keyword in CHART_KEYWORDS)


def _fetch_x_search(bearer_token, query, max_results):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "query": f"{query} -is:retweet lang:ko",
        "max_results": min(max(max_results, 10), 100),  # X API 제약: 10~100
        "tweet.fields": "created_at,author_id,public_metrics",
        "expansions": "author_id",
        "user.fields": "username",
    }
    r = requests.get(X_SEARCH_URL, headers=headers, params=params, timeout=15)
    if r.status_code != 200:
        return [], f"HTTP {r.status_code} - {r.text[:200]}"

    data = r.json()
    tweets = data.get("data", [])
    users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}

    results = []
    for t in tweets:
        username = users.get(t.get("author_id"), "unknown")
        results.append(
            {
                "id": t["id"],
                "text": t.get("text", ""),
                "username": username,
                "created_at": t.get("created_at", ""),
                "link": f"https://x.com/{username}/status/{t['id']}",
            }
        )
    return results, None


def collect_x(conn):
    bearer_token = os.environ.get("X_BEARER_TOKEN")
    if not bearer_token:
        print("X_BEARER_TOKEN이 설정되어 있지 않아 X 수집을 건너뜁니다.")
        return 0

    new_count = 0
    for query in X_SEARCH_QUERIES:
        tweets, err = _fetch_x_search(bearer_token, query, X_SEARCH_MAX_RESULTS)
        if err:
            print(f"  [경고] X 검색 실패 ({query}): {err}")
            continue

        for t in tweets:
            if not _is_our_group(t["text"]):
                continue
            title = t["text"][:80].replace("\n", " ")
            is_new = insert_item(
                conn, "x", f"X · @{t['username']}", title, t["link"],
                t["created_at"], t["text"][:500],
            )
            if is_new:
                new_count += 1
                print(f"  [신규/X] @{t['username']} - {title}")

    return new_count


if __name__ == "__main__":
    init_db()
    with get_conn() as conn:
        collect_x(conn)
