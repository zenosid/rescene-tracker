# -*- coding: utf-8 -*-
"""
음악방송 채널(음악중심/인기가요/더쇼)·유튜브 검색으로 잘못 들어온 '리센느와 무관한'
콜라보 영상을 정리합니다. 판정은 수집기와 같은 엄격한 규칙(classify.is_relevant_broadcast)입니다.

  python cleanup_irrelevant_collab.py          ← 미리보기만 (아무것도 지우지 않음)
  python cleanup_irrelevant_collab.py --apply  ← 미리보기 목록을 실제로 삭제

삭제 전에 지울 목록을 rescene_tracker.db.bak 으로 백업합니다(되돌릴 수 있음).
대상은 source_type='youtube_collab' 뿐이고, 뉴스/카페/블로그/X와 공식 채널은 건드리지 않습니다.
"""
import shutil
import sys

from config import DB_PATH
from db import init_db, get_conn
from classify import is_relevant_broadcast


def main(apply):
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, source_name, title FROM items WHERE source_type = 'youtube_collab'"
        ).fetchall()
        bad = [r for r in rows if not is_relevant_broadcast(r["title"], r["source_name"])]
        for r in bad:
            print(f"[삭제대상] {r['source_name'][:14]:14} | {r['title'][:60]}")
        print(f"\n콜라보 영상 {len(rows)}건 중 무관 {len(bad)}건")
        if not apply:
            print("미리보기입니다. 지우려면: python cleanup_irrelevant_collab.py --apply")
            return
        if bad:
            shutil.copyfile(DB_PATH, str(DB_PATH) + ".bak")
            conn.executemany("DELETE FROM items WHERE id = ?", [(r["id"],) for r in bad])
            print(f"삭제 완료 ({len(bad)}건). 백업: {DB_PATH}.bak")


if __name__ == "__main__":
    main("--apply" in sys.argv)
