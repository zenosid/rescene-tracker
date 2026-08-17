# -*- coding: utf-8 -*-
"""
유튜브 RSS(shorts/영상ID)와 백필(watch?v=영상ID)이 같은 영상을 서로 다른
링크로 저장해서 생긴 중복을 정리합니다. 영상 ID 기준으로 그룹핑해서,
가장 먼저 저장된 것 하나만 남기고 나머지는 삭제합니다.

실행: python cleanup_duplicate_youtube.py
"""
import re
from collections import defaultdict

from db import init_db, get_conn

_VIDEO_ID_RE = re.compile(r"(?:watch\?v=|shorts/)([\w-]{11})")


def _extract_video_id(link):
    m = _VIDEO_ID_RE.search(link)
    return m.group(1) if m else None


def cleanup():
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM items WHERE source_type IN ('youtube', 'youtube_collab') ORDER BY id ASC"
        ).fetchall()

        groups = defaultdict(list)
        for row in rows:
            video_id = _extract_video_id(row["link"])
            if not video_id:
                continue  # ID를 못 뽑아내면 안전하게 건드리지 않음
            key = (row["source_type"], row["source_name"], video_id)
            groups[key].append(row)

        to_delete = []
        for key, items in groups.items():
            if len(items) <= 1:
                continue
            keep, *dupes = items  # id가 가장 작은(먼저 저장된) 것만 유지
            print(f"[중복 {len(items)}건] {key[1]} - {keep['title'][:40]}")
            for d in dupes:
                to_delete.append(d["id"])

        if to_delete:
            conn.executemany("DELETE FROM items WHERE id = ?", [(i,) for i in to_delete])

    print(f"\n정리 완료: {len(to_delete)}건 삭제됨")


if __name__ == "__main__":
    cleanup()
