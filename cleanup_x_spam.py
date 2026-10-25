# -*- coding: utf-8 -*-
"""
X 수집분 중 '소식이 아닌' 글을 정리합니다 (판정: x_filter.py).

  거래·대행 글 (포카 양도·판매, 대리찍사, 팬싸컷 상담 등) → 삭제
  유해 광고 의심 (계정 판매·해킹·토토·신분증/학생증 대여 등) → 삭제 + 운영자 점검 목록
      (moderation_flags)에 링크와 걸린 표현만 기록 (글 내용은 저장하지 않음)

  python cleanup_x_spam.py          ← 미리보기만 (아무것도 지우지 않음)
  python cleanup_x_spam.py --apply  ← 실제 반영 (rescene_tracker.db.bak 으로 백업 후)

점검 목록 확인: python check_moderation.py
※ 저장소가 public이면 DB 파일도 공개됩니다. 링크와 표현만 기록하는 이유입니다.
"""
import shutil
import sys

from config import DB_PATH
from db import init_db, get_conn, insert_moderation_flag
from x_filter import is_trading_or_spam, harmful_keyword


def main(apply):
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, source_name, title, snippet, link FROM items WHERE source_type = 'x'"
        ).fetchall()
        trade, harmful = [], []
        for r in rows:
            text = (r["snippet"] or "") + " " + r["title"]
            kw = harmful_keyword(text)
            if kw:
                harmful.append((r, kw))
            elif is_trading_or_spam(text):
                trade.append(r)

        for r in trade[:25]:
            print(f"[거래글]   {(r['snippet'] or r['title'])[:60]!r}")
        if len(trade) > 25:
            print(f"... 거래글 외 {len(trade) - 25}건")
        print(f"[유해광고 의심] {len(harmful)}건 (내용은 출력하지 않음)")
        print(f"\nX {len(rows)}건 중 거래글 {len(trade)}건 + 유해광고 의심 {len(harmful)}건 = {len(trade) + len(harmful)}건")
        if not apply:
            print("미리보기입니다. 반영하려면: python cleanup_x_spam.py --apply")
            return

        shutil.copyfile(DB_PATH, str(DB_PATH) + ".bak")
        for r, kw in harmful:
            insert_moderation_flag(conn, "x", "X", "(유해 광고 의심 · 내용 비공개)", r["link"], f"유해광고:{kw}")
        ids = [(r["id"],) for r in trade] + [(r["id"],) for r, _ in harmful]
        conn.executemany("DELETE FROM items WHERE id = ?", ids)
        print(f"완료: 삭제 {len(ids)}건 (이 중 점검 목록 기록 {len(harmful)}건). 백업: {DB_PATH}.bak")


if __name__ == "__main__":
    main("--apply" in sys.argv)
