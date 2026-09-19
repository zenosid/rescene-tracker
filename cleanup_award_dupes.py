# -*- coding: utf-8 -*-
"""
상 이름(award_name)이 비어있는 채로 잘못 자동 감지된 시상식 항목을 정리합니다.
(수동 등록과 상 이름이 안 맞아서 중복 제거가 안 됐던 것들)

실행: python cleanup_award_dupes.py
"""
from db import init_db, get_conn

with get_conn() as conn:
    init_db()
    rows = conn.execute(
        "SELECT id, date, ceremony, title FROM awards WHERE award_name IS NULL OR award_name = ''"
    ).fetchall()

    if not rows:
        print("상 이름이 비어있는 항목이 없습니다.")
    else:
        print(f"삭제 대상 {len(rows)}건:")
        for r in rows:
            print(f"  - {r['date']} {r['ceremony']} - {r['title'][:50]}")
        conn.execute("DELETE FROM awards WHERE award_name IS NULL OR award_name = ''")
        print(f"\n{len(rows)}건 삭제 완료")
