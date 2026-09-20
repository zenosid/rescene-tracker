# -*- coding: utf-8 -*-
"""
같은 시상식이 "TMA"/"더팩트 뮤직 어워즈" 등 표기만 다르게 저장돼서
중복으로 남아있는 것을 정식 표기로 통일합니다.

⚠️ 예전 버전에 있던 "상 이름 없는 항목 자동 삭제" 기능은 뺐습니다 - 한
시상식에서 여러 상을 동시에 받는 경우가 실제로 있어서(예: 같은 날 '올해의
아티스트'와 '투데이스 초이스'를 둘 다 수상), 그 로직이 서로 다른 진짜
수상 기록을 중복으로 착각해서 지워버리는 사고가 있었습니다. 표기 통일만
안전하게 하고, 나머지 중복 방지는 trophy_extractor.py의 추출 시점 로직에
맡깁니다 (한 번의 추출 작업 안에서 완전히 같은 정보일 때만 병합함).

실행: python cleanup_award_dupes.py
"""
from db import init_db, get_conn
from trophy_extractor import _CEREMONY_CANONICAL

with get_conn() as conn:
    init_db()

    rows = conn.execute("SELECT id, ceremony FROM awards").fetchall()
    renamed = 0
    for r in rows:
        canonical = _CEREMONY_CANONICAL.get(r["ceremony"])
        if canonical and canonical != r["ceremony"]:
            conn.execute("UPDATE awards SET ceremony = ? WHERE id = ?", (canonical, r["id"]))
            renamed += 1

    if renamed:
        print(f"표기 통일: {renamed}건 (예: '더팩트 뮤직 어워즈' → 'TMA')")
    else:
        print("표기 통일할 항목이 없습니다.")
