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

from config import SCHEDULE_ITEMS, OPERATOR_CONTACT, REFRESH_INTERVAL_MINUTES, LINK_COLLECTIONS, RESCENE_ALL_SONGS
from db import init_db, get_conn, get_recent_items, get_auto_schedule, get_official_schedule, get_previous_ranks, get_recent_fan_reactions
from chart_tracker import get_latest_all
from classify import classify_members, classify_category
from kst import now_kst, to_kst

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "data.js")


def build_archive():
    with get_conn() as conn:
        items = get_recent_items(conn, limit=500)

    grouped = defaultdict(list)
    for item in items:
        raw_time = item["published_at"] or item["fetched_at"]
        kst_dt = to_kst(raw_time)
        date_key = kst_dt.strftime("%Y-%m-%d")
        entry = {
            "title": item["title"],
            "link": item["link"],
            "source_type": item["source_type"],
            "source_name": item["source_name"],
            "time": kst_dt.strftime("%H:%M"),
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
            prev_ranks = get_previous_ranks(conn, platform)
            entries = []
            for s in songs:
                prev_rank = prev_ranks.get(s["song_title"])
                if prev_rank is None:
                    change = {"kind": "new"}
                else:
                    delta = prev_rank - s["rank"]  # 양수 = 순위 상승(숫자는 작아짐)
                    if delta > 0:
                        change = {"kind": "up", "delta": delta}
                    elif delta < 0:
                        change = {"kind": "down", "delta": -delta}
                    else:
                        change = {"kind": "same"}
                entries.append(
                    {
                        "rank": s["rank"],
                        "song_title": s["song_title"],
                        "artist_text": s["artist_text"],
                        "checked_at": to_kst(s["checked_at"]).strftime("%Y-%m-%d %H:%M"),
                        "change": change,
                    }
                )
            result[platform] = entries
    return result


def build_schedule():
    today_str = now_kst().strftime("%Y-%m-%d")

    manual_items = [
        {**s, "is_estimated": False, "mention_count": 1} for s in SCHEDULE_ITEMS
    ]

    # 공식 스케줄(Mnet Plus) - 이미 확정된 정보이므로 추정 표시 없음
    with get_conn() as conn:
        official_rows = get_official_schedule(conn)

    official_items = []
    for row in official_rows:
        title = row["title"]
        if row["time_text"]:
            title = f"{title} ({row['time_text']})"
        official_items.append(
            {
                "date": row["date"],
                "type": row["category"] or "기타",
                "title": title,
                "note": "출처: Mnet Plus 공식 스케줄",
                "is_estimated": False,
                "mention_count": 1,
            }
        )

    # 자동 추출된 항목(뉴스 기반)은 (날짜, 타입)이 같으면 하나로 합치고, 몇 건의
    # 기사에서 언급됐는지 기록 (기사가 많을수록 신뢰도가 높다는 신호)
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

    # 같은 날짜에 공식 스케줄이 이미 있으면, 뉴스 기반 추정 항목은 굳이 중복
    # 표시하지 않음 (공식 정보가 있는데 불확실한 추정을 같이 보여줄 필요 없음)
    # 공식(Mnet Plus) 또는 운영자가 직접 등록한 날짜와 겹치면, 불확실한 추정
    # 항목은 굳이 같이 보여줄 필요 없음
    trusted_dates = {item["date"] for item in official_items} | {item["date"] for item in manual_items}
    auto_items = [item for item in auto_items if item["date"] not in trusted_dates]

    all_items = manual_items + official_items + auto_items
    upcoming = sorted([s for s in all_items if s["date"] >= today_str], key=lambda s: s["date"])
    past = sorted([s for s in all_items if s["date"] < today_str], key=lambda s: s["date"], reverse=True)
    return {"upcoming": upcoming, "past": past}


def build_fan_reactions():
    with get_conn() as conn:
        rows = get_recent_fan_reactions(conn, limit=150)
    result = []
    for r in rows:
        published_dt = to_kst(r["published_at"]) if r["published_at"] else None
        result.append(
            {
                "video_link": r["video_link"],
                "video_title": r["video_title"],
                "author": r["author"],
                "text": r["text"],
                "like_count": r["like_count"],
                "published_at": published_dt.strftime("%Y-%m-%d %H:%M") if published_dt else "",
                "published_at_raw": r["published_at"] or "",
            }
        )
    return result


def main():
    init_db()
    data = {
        "generated_at": now_kst().strftime("%Y-%m-%d %H:%M"),
        "operator_contact": OPERATOR_CONTACT,
        "refresh_interval_minutes": REFRESH_INTERVAL_MINUTES,
        "archive": build_archive(),
        "chart": build_chart(),
        "schedule": build_schedule(),
        "links": LINK_COLLECTIONS,
        "fan_reactions": build_fan_reactions(),
        "all_songs": RESCENE_ALL_SONGS,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("const SITE_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    total_archive = sum(len(d["items"]) for d in data["archive"])
    print(f"data.js 생성 완료: 아카이브 {total_archive}건, "
          f"차트 {sum(len(v) for v in data['chart'].values())}건, "
          f"스케줄 {len(data['schedule']['upcoming'])}건(예정), "
          f"팬반응 {len(data['fan_reactions'])}건")


if __name__ == "__main__":
    main()
