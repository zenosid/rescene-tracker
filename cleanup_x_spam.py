# -*- coding: utf-8 -*-
"""
X 수집분 중 포카 양도/판매, 대리찍사·사후 데이터 판매, 팬싸컷 상담, 토토·매크로 광고 같은
'소식이 아닌' 글을 정리합니다 (판정: x_filter.is_trading_or_spam).

  python cleanup_x_spam.py          ← 미리보기만 (아무것도 지우지 않음)
  python cleanup_x_spam.py --apply  ← 실제 삭제 (rescene_tracker.db.bak 으로 백업 후)

'판매·교환·공구'처럼 공식 MD 판매 안내에도 쓰이는 단어만 걸린 글은 대상이 아닙니다.
"""
import shutil
import sys

from config import DB_PATH
from db import init_db, get_conn
from x_filter import is_trading_or_spam


def main(apply):
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, source_name, title, snippet FROM items WHERE source_type = 'x'"
        ).fetchall()
        bad = [r for r in rows if is_trading_or_spam((r["snippet"] or "") + " " + r["title"])]
        for r in bad[:40]:
            print(f"[삭제대상] {r['source_name'][:22]:22} | {(r['snippet'] or r['title'])[:55]!r}")
        if len(bad) > 40:
            print(f"... 외 {len(bad) - 40}건")
        print(f"\nX {len(rows)}건 중 거래·스팸 {len(bad)}건")
        if not apply:
            print("미리보기입니다. 지우려면: python cleanup_x_spam.py --apply")
            return
        if bad:
            shutil.copyfile(DB_PATH, str(DB_PATH) + ".bak")
            conn.executemany("DELETE FROM items WHERE id = ?", [(r["id"],) for r in bad])
            print(f"삭제 완료 ({len(bad)}건). 백업: {DB_PATH}.bak")


if __name__ == "__main__":
    main("--apply" in sys.argv)
