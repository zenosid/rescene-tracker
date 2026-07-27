# -*- coding: utf-8 -*-
"""
이미 저장된 뉴스 중, 구글/네이버에서 같은 기사가 서로 다른 링크로 중복 저장된
것들을 정리하는 일회성 스크립트입니다. 제목을 정규화해서 비교하고, 같은
그룹 안에서는 가장 먼저 저장된 것(id가 가장 작은 것)만 남기고 나머지를 지웁니다.

실행: python cleanup_duplicate_news.py
"""
from collections import defaultdict

from collector import _normalize_title_for_dedup
from db import get_conn


def cleanup():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, source_name FROM items WHERE source_type = 'news' ORDER BY id ASC"
        ).fetchall()

        groups = defaultdict(list)
        for row in rows:
            key = _normalize_title_for_dedup(row["title"])
            groups[key].append(row)

        to_delete = []
        for key, items in groups.items():
            if len(items) <= 1:
                continue
            # id가 가장 작은(=가장 먼저 저장된) 것만 남기고 나머지 삭제
            keep, *dupes = items
            print(f"[중복 {len(items)}건] \"{keep['title'][:50]}\" -> 유지: {keep['source_name']}")
            for d in dupes:
                print(f"    삭제: {d['source_name']} - {d['title'][:50]}")
                to_delete.append(d["id"])

        if to_delete:
            conn.executemany("DELETE FROM items WHERE id = ?", [(i,) for i in to_delete])

        print(f"\n정리 완료: {len(to_delete)}건 삭제됨")


if __name__ == "__main__":
    cleanup()
