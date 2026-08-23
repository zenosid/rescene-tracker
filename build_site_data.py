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
from datetime import datetime, date

from config import (
    OPERATOR_CONTACT, REFRESH_INTERVAL_MINUTES, LINK_COLLECTIONS,
    RESCENE_ALL_SONGS, DEBUT_DATE, MEMBER_BIRTHDAYS, ARCHIVE_DISPLAY_LIMIT, TROPHY_ITEMS,
    PHOTOCARD_RELEASES,
)
from db import (
    init_db, get_conn, get_recent_items, get_official_schedule,
    get_previous_ranks, get_recent_fan_reactions, get_recent_trophies,
)
from chart_tracker import get_latest_all
from classify import classify_members, classify_category
from kst import now_kst, to_kst

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "data.js")


def build_archive():
    with get_conn() as conn:
        items = get_recent_items(conn, limit=ARCHIVE_DISPLAY_LIMIT)

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
    """
    Mnet Plus 공식 스케줄만 사용합니다. 뉴스 기반 추정(auto_schedule)과 수동
    등록(SCHEDULE_ITEMS)은 그동안 여러 차례 오탐이 있었어서(엉뚱한 날짜로
    튀는 등) 신뢰도 문제로 뺐습니다. 공식 확인된 정보만 보여줍니다.
    """
    today_str = now_kst().strftime("%Y-%m-%d")

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

    upcoming = sorted([s for s in official_items if s["date"] >= today_str], key=lambda s: s["date"])
    past = sorted([s for s in official_items if s["date"] < today_str], key=lambda s: s["date"], reverse=True)
    return {"upcoming": upcoming, "past": past}


def build_anniversaries():
    """데뷔일 + 멤버 생일의 다음 도래 시점을 계산해서 가까운 순으로 정렬."""
    today = now_kst().date()
    items = []

    debut = datetime.strptime(DEBUT_DATE, "%Y-%m-%d").date()

    def _next_occurrence(month, day):
        try:
            candidate = date(today.year, month, day)
        except ValueError:
            return None
        if candidate < today:
            candidate = date(today.year + 1, month, day)
        return candidate

    debut_next = _next_occurrence(debut.month, debut.day)
    if debut_next:
        years = debut_next.year - debut.year
        items.append(
            {
                "type": "데뷔",
                "name": f"데뷔 {years}주년",
                "date": debut_next.isoformat(),
                "d_day": (debut_next - today).days,
            }
        )

    for member, mmdd in MEMBER_BIRTHDAYS.items():
        try:
            month, day = (int(x) for x in mmdd.split("-"))
        except ValueError:
            continue
        next_bday = _next_occurrence(month, day)
        if next_bday:
            items.append(
                {
                    "type": "생일",
                    "name": f"{member} 생일",
                    "member": member,
                    "date": next_bday.isoformat(),
                    "d_day": (next_bday - today).days,
                }
            )

    # 가까운 순이 아니라, 지정된 고정 순서(데뷔 → 원이 → 미나미 → 리브 → 메이 → 제나)로 정렬
    FIXED_ORDER = ["데뷔", "원이", "미나미", "리브", "메이", "제나"]

    def _sort_key(item):
        label = item["type"] if item["type"] == "데뷔" else item.get("member", "")
        try:
            return FIXED_ORDER.index(label)
        except ValueError:
            return len(FIXED_ORDER)  # 목록에 없는 항목은 맨 뒤로

    items.sort(key=_sort_key)
    return items


def build_trophies():
    from datetime import date as _date_cls

    manual_items = [
        {
            "date": t["date"],
            "show": t["show"],
            "song": t["song"],
            "title": t.get("note", ""),
            "source_link": "",
            "is_manual": True,
        }
        for t in TROPHY_ITEMS
    ]

    with get_conn() as conn:
        rows = get_recent_trophies(conn, limit=100)
    auto_items = [
        {
            "date": r["date"],
            "show": r["show"],
            "song": r["song"] if r["song"] else "",
            "title": r["title"],
            "source_link": r["source_link"],
            "is_manual": False,
        }
        for r in rows
    ]

    # 수동 등록과 (방송, 곡)이 같고 날짜도 3일 이내로 가까우면 자동 감지 쪽은
    # 중복이니 빼고 수동 등록(더 신뢰할 수 있는 쪽)만 남김
    def _is_near_manual(auto_item):
        for m in manual_items:
            if m["show"] != auto_item["show"] or m["song"] != auto_item["song"]:
                continue
            try:
                d1 = _date_cls.fromisoformat(m["date"])
                d2 = _date_cls.fromisoformat(auto_item["date"])
            except ValueError:
                continue
            if abs((d1 - d2).days) <= 3:
                return True
        return False

    auto_items = [a for a in auto_items if not _is_near_manual(a)]

    all_items = manual_items + auto_items
    all_items.sort(key=lambda x: x["date"], reverse=True)
    return all_items


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
        "anniversaries": build_anniversaries(),
        "trophies": build_trophies(),
        "photocard_releases": PHOTOCARD_RELEASES,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("const SITE_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    total_archive = sum(len(d["items"]) for d in data["archive"])
    print(f"data.js 생성 완료: 아카이브 {total_archive}건, "
          f"차트 {sum(len(v) for v in data['chart'].values())}건, "
          f"스케줄 {len(data['schedule']['upcoming'])}건(예정), "
          f"팬반응 {len(data['fan_reactions'])}건, "
          f"포토카드 {len(data['photocard_releases'])}건")


if __name__ == "__main__":
    main()
