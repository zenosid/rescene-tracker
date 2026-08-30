# -*- coding: utf-8 -*-
"""
필터가 빠져있던 동안(collect_news, collect_collab_by_search) 잘못 들어간,
제목에 "리센느"/"RESCENE"이 전혀 없는 뉴스·유튜브 항목을 정리합니다.

공식 채널(source_type='youtube')은 채널 자체가 공식이라 제목에 키워드가
없어도 정상이니 건드리지 않습니다. 카페글/블로그/X는 원래부터 필터가
있었어서 이미 깨끗할 겁니다.

실행: python cleanup_irrelevant_items.py
"""
from config import CHART_KEYWORDS
from db import init_db, get_conn


def _is_our_group(text):
    return any(keyword in text for keyword in CHART_KEYWORDS)


def cleanup():
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, source_type, source_name, title FROM items "
            "WHERE source_type IN ('news', 'youtube_collab')"
        ).fetchall()

        to_delete = []
        for row in rows:
            if not _is_our_group(row["title"]):
                to_delete.append(row["id"])
                print(f"[삭제] ({row['source_type']}) {row['source_name']} - {row['title'][:50]}")

        if to_delete:
            conn.executemany("DELETE FROM items WHERE id = ?", [(i,) for i in to_delete])

    print(f"\n정리 완료: {len(to_delete)}건 삭제됨")


if __name__ == "__main__":
    cleanup()
