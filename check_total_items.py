# -*- coding: utf-8 -*-
"""DB에 실제로 쌓인 전체 항목 수와, 가장 오래된 항목 날짜를 확인합니다."""
from db import get_conn

with get_conn() as conn:
    total = conn.execute("SELECT COUNT(*) as c FROM items").fetchone()["c"]
    oldest = conn.execute("SELECT MIN(published_at) as m FROM items").fetchone()["m"]
    print(f"DB에 쌓인 전체 항목 수: {total}건")
    print(f"가장 오래된 항목: {oldest}")
    print()
    if total > 3000:
        print(f"⚠️  ARCHIVE_DISPLAY_LIMIT(3000)보다 많습니다 — {total - 3000}건이 화면에 안 보이고 있을 겁니다.")
    else:
        print("현재 설정(3000)으로 전체가 다 보이고 있습니다.")
