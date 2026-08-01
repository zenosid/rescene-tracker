# -*- coding: utf-8 -*-
"""
기존 트로피 기록을 정리하는 일회성 스크립트입니다.
1) 제목에서 곡명을 다시 매칭해서 song 컬럼을 채워넣고 (예전엔 없었음)
2) 같은 방송+같은 곡이 3일 이내에 여러 건 있으면(언론사별 보도 시차 때문)
   가장 먼저 저장된 것 하나만 남기고 나머지는 지웁니다.
3) 곡명을 특정 못 하는 기존 기록은 신뢰도가 낮으므로 삭제합니다.

실행: python cleanup_duplicate_trophies.py
"""
from collections import defaultdict
from datetime import date as date_cls

from trophy_extractor import _match_song
from db import get_conn


def cleanup():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM trophies ORDER BY id ASC").fetchall()

        to_delete = []
        song_updates = []  # (id, song)

        # 1) 곡명 백필 + 곡명 특정 안 되는 건 삭제 대상으로
        enriched = []
        for row in rows:
            song = row["song"] or _match_song(row["title"])
            if not song:
                print(f"[곡명 특정 불가, 삭제] {row['date']} {row['show']} - {row['title'][:50]}")
                to_delete.append(row["id"])
                continue
            if song != row["song"]:
                song_updates.append((row["id"], song))
            enriched.append({**dict(row), "song": song})

        # 2) (방송, 곡) 그룹 안에서 3일 이내 근접 날짜는 하나로 합침
        groups = defaultdict(list)
        for row in enriched:
            groups[(row["show"], row["song"])].append(row)

        for (show, song), items in groups.items():
            items.sort(key=lambda r: r["id"])  # 먼저 저장된 것 우선
            kept = []
            for item in items:
                item_date = date_cls.fromisoformat(item["date"])
                is_dup = any(
                    abs((item_date - date_cls.fromisoformat(k["date"])).days) <= 3 for k in kept
                )
                if is_dup:
                    print(f"[중복, 삭제] {item['date']} {show} {song} - {item['title'][:40]}")
                    to_delete.append(item["id"])
                else:
                    kept.append(item)

        for trophy_id, song in song_updates:
            if trophy_id not in to_delete:
                conn.execute("UPDATE trophies SET song = ? WHERE id = ?", (song, trophy_id))

        if to_delete:
            conn.executemany(
                "DELETE FROM trophies WHERE id = ?", [(i,) for i in set(to_delete)]
            )

    print(f"\n정리 완료: {len(set(to_delete))}건 삭제, {len(song_updates)}건 곡명 보완")


if __name__ == "__main__":
    cleanup()
