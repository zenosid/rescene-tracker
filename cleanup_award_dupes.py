# -*- coding: utf-8 -*-
"""
1) 같은 시상식이 "TMA"/"더팩트 뮤직 어워즈" 등 표기만 다르게 저장돼서
   중복으로 남아있는 것을 정식 표기로 통일합니다.
2) 상 이름이 비어있는 항목 중, 같은 시상식+비슷한 날짜에 상 이름이 있는
   더 구체적인 항목이 있으면 비어있는 쪽을 지웁니다.

실행: python cleanup_award_dupes.py
"""
from datetime import date as _date_cls

from db import init_db, get_conn
from trophy_extractor import _CEREMONY_CANONICAL

with get_conn() as conn:
    init_db()

    # 1) 표기 통일
    rows = conn.execute("SELECT id, ceremony FROM awards").fetchall()
    renamed = 0
    for r in rows:
        canonical = _CEREMONY_CANONICAL.get(r["ceremony"])
        if canonical and canonical != r["ceremony"]:
            conn.execute("UPDATE awards SET ceremony = ? WHERE id = ?", (canonical, r["id"]))
            renamed += 1
    if renamed:
        print(f"표기 통일: {renamed}건 (예: '더팩트 뮤직 어워즈' → 'TMA')")

    # 2) 상 이름 없는 중복 제거
    all_rows = conn.execute("SELECT id, date, ceremony, award_name, title FROM awards").fetchall()
    specific = [r for r in all_rows if r["award_name"]]
    empty = [r for r in all_rows if not r["award_name"]]

    to_delete = []
    for e in empty:
        try:
            e_date = _date_cls.fromisoformat(e["date"])
        except ValueError:
            continue
        for s in specific:
            if s["ceremony"] != e["ceremony"]:
                continue
            try:
                s_date = _date_cls.fromisoformat(s["date"])
            except ValueError:
                continue
            if abs((e_date - s_date).days) <= 3:
                to_delete.append(e)
                break

    if to_delete:
        print(f"\n상 이름 없는 중복 삭제 대상 {len(to_delete)}건:")
        for r in to_delete:
            print(f"  - {r['date']} {r['ceremony']} - {r['title'][:50]}")
        conn.executemany("DELETE FROM awards WHERE id = ?", [(r["id"],) for r in to_delete])
        print(f"{len(to_delete)}건 삭제 완료")
    else:
        print("\n상 이름 없는 중복이 없습니다.")
