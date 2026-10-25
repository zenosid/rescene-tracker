# -*- coding: utf-8 -*-
"""
뉴스·블로그·외부 카페 글 중 '리센느와 무관'한 항목 정리 (멤버 이름이 다른 단어의 일부로
잡힌 경우: 메이딘, 리메이크, 유어메이트, 직원이 등).

  python cleanup_irrelevant_text.py          ← 미리보기만 (아무것도 지우지 않음)
  python cleanup_irrelevant_text.py --apply  ← 목록을 실제로 삭제 (rescene_tracker.db.bak 백업)

판정: 제목에 그룹명이 없고, 멤버 이름도 단어로 쓰이지 않았고, 본문 요약에도 그룹명이
없을 때만 대상입니다. 리센느 팬카페 글·X·공식 채널은 건드리지 않습니다.
이름이 겹치는 다른 사람 기사는 아래 MANUAL_EXCLUDE에 제목 일부를 적으면 함께 정리됩니다.
"""
import re
import shutil
import sys

from config import DB_PATH
from db import init_db, get_conn
from classify import GROUP_NAME_RE, member_name_in

MANUAL_EXCLUDE = ["카리나·원이 닮아", "무일푼 제나"]


def main(apply):
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, source_type, source_name, title, snippet FROM items "
            "WHERE source_type IN ('news', 'community')"
        ).fetchall()
        bad = []
        for r in rows:
            if r["source_type"] == "community" and re.search("리센느|rescene", r["source_name"], re.I):
                continue
            manual = any(p in r["title"] for p in MANUAL_EXCLUDE)
            auto = (not GROUP_NAME_RE.search(r["title"]) and not member_name_in(r["title"])
                    and not GROUP_NAME_RE.search(r["snippet"] or ""))
            if manual or auto:
                bad.append(r)
                print(f"[삭제대상] ({r['source_type']}) {r['source_name'][:16]} | {r['title'][:60]}")
        print(f"\n검사 {len(rows)}건 중 무관 {len(bad)}건")
        if not apply:
            print("미리보기입니다. 지우려면: python cleanup_irrelevant_text.py --apply")
            return
        if bad:
            shutil.copyfile(DB_PATH, str(DB_PATH) + ".bak")
            conn.executemany("DELETE FROM items WHERE id = ?", [(r["id"],) for r in bad])
            print(f"삭제 완료 ({len(bad)}건). 백업: {DB_PATH}.bak")


if __name__ == "__main__":
    main("--apply" in sys.argv)
