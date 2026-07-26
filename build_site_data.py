# -*- coding: utf-8 -*-
"""
DB(items, chart_snapshots)와 config(SCHEDULE_ITEMS)를 읽어서
정적 HTML 사이트가 바로 읽을 수 있는 data.js 파일을 생성합니다.

file:// 로 index.html을 열어도 fetch()의 CORS 제약 없이 동작하도록
<script> 태그로 바로 불러올 수 있는 JS 변수 형태로 만듭니다.

실행: python build_site_data.py
(refresh_and_open.bat이 수집 → 차트조회 → 이 스크립트를 순서대로 실행합니다)
"""
import json
import os
from collections import defaultdict
from datetime import datetime

from config import SCHEDULE_ITEMS, OPERATOR_CONTACT, REFRESH_INTERVAL_HOURS
from db import init_db, get_conn, get_recent_items, get_auto_schedule
from chart_tracker import get_latest_all
from classify import classify_members, classify_category

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "data.js")


def build_archive():
    with get_conn() as conn:
        items = get_recent_items(conn, limit=500)

    grouped = defaultdict(list)
    for item in items:
        date_key = (item["published_at"] or item["fetched_at"])[:10]
        entry = {
            "title": item["title"],
            "link": item["link"],
            "source_type": item["source_type"],
            "source_name": item["source_name"],
            "time": (item["published_at"] or "")[11:16],
            "category": classify_category(item["title"], item["source_type"]),
            "members": classify_members(item["title"]),
        }
        grouped[date_key].append(entry)

    # 최신 날짜 순으로 정렬된 리스트로 변환
    result = []
    for date_key in sorted(grouped.keys(), reverse=True):
        try:
            date_display = datetime.strptime(date_key, "%Y-%m-%d").strftime("%Y년 %m월 %d일")
        except ValueError:
            date_display = date_key
        result.append({"date": date_key, "date_display": date_display, "items": grouped[date_key]})
    return result


def build_chart():
    with get_conn() as conn:
        latest = get_latest_all(conn)
    result = {}
    for platform, songs in latest.items():
        result[platform] = [
            {
                "rank": s["rank"],
                "song_title": s["song_title"],
                "artist_text": s["artist_text"],
                "checked_at": s["checked_at"],
            }
            for s in songs
        ]
    return result


def build_schedule():
    today_str = datetime.now().strftime("%Y-%m-%d")

    manual_items = [
        {**s, "is_estimated": False, "mention_count": 1} for s in SCHEDULE_ITEMS
    ]

    # 자동 추출된 항목은 (날짜, 타입)이 같으면 하나로 합치고, 몇 건의 기사에서
    # 언급됐는지 기록 (기사가 많을수록 신뢰도가 높다는 신호)
    with get_conn() as conn:
        auto_rows = get_auto_schedule(conn)

    grouped_auto = {}
    for row in auto_rows:
        key = (row["date"], row["type"])
        if key not in grouped_auto:
            grouped_auto[key] = {
                "date": row["date"],
                "type": row["type"],
                "title": row["title"],
                "note": row["note"],
                "is_estimated": True,
                "mention_count": 1,
            }
        else:
            grouped_auto[key]["mention_count"] += 1

    auto_items = list(grouped_auto.values())
    for item in auto_items:
        if item["mention_count"] > 1:
            item["note"] += f" 외 {item['mention_count'] - 1}건 추가 언급"

    all_items = manual_items + auto_items
    upcoming = sorted([s for s in all_items if s["date"] >= today_str], key=lambda s: s["date"])
    past = sorted([s for s in all_items if s["date"] < today_str], key=lambda s: s["date"], reverse=True)
    return {"upcoming": upcoming, "past": past}


def main():
    init_db()
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "operator_contact": OPERATOR_CONTACT,
        "refresh_interval_hours": REFRESH_INTERVAL_HOURS,
        "archive": build_archive(),
        "chart": build_chart(),
        "schedule": build_schedule(),
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("const SITE_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    total_archive = sum(len(d["items"]) for d in data["archive"])
    print(f"data.js 생성 완료: 아카이브 {total_archive}건, "
          f"차트 {sum(len(v) for v in data['chart'].values())}건, "
          f"스케줄 {len(data['schedule']['upcoming'])}건(예정)")


if __name__ == "__main__":
    main()
