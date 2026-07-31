# -*- coding: utf-8 -*-
"""
같은 (날짜, 방송사) 조합으로 여러 언론사 기사 때문에 중복 저장된 트로피를
정리하는 일회성 스크립트입니다. 가장 먼저 저장된 것(id가 가장 작은 것)만 남깁니다.

실행: python cleanup_duplicate_trophies.py
"""
from collections import defaultdict

from db import get_conn


def cleanup():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM trophies ORDER BY id ASC").fetchall()

        groups = defaultdict(list)
        for row in rows:
            key = (row["date"], row["show"])
            groups[key].append(row)

        to_delete = []
        for key, items in groups.items():
            if len(items) <= 1:
                continue
            keep, *dupes = items
            print(f"[중복 {len(items)}건] {key[0]} {key[1]} -> 유지: {keep['title'][:50]}")
            for d in dupes:
                print(f"    삭제: {d['title'][:50]}")
                to_delete.append(d["id"])

        if to_delete:
            conn.executemany("DELETE FROM trophies WHERE id = ?", [(i,) for i in to_delete])

    print(f"\n정리 완료: {len(to_delete)}건 삭제됨")


if __name__ == "__main__":
    cleanup()
