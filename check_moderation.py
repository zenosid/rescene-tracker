# -*- coding: utf-8 -*-
"""
아직 검토 안 한(reviewed=0) 모더레이션 후보 목록을 콘솔에 출력합니다.
공개 사이트엔 안 나오는 정보라, 이 스크립트로 직접 확인하시면 됩니다.

실행: python check_moderation.py
"""
from db import init_db, get_conn, get_unreviewed_moderation_flags

init_db()

with get_conn() as conn:
    rows = get_unreviewed_moderation_flags(conn, limit=100)

if not rows:
    print("아직 검토 안 한 항목이 없습니다.")
else:
    print(f"검토 필요 항목 {len(rows)}건:\n")
    for r in rows:
        print(f"[{r['matched_keyword']}] {r['source_name']} - {r['title']}")
        print(f"    {r['link']}")
        print()
