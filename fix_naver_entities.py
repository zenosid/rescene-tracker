# -*- coding: utf-8 -*-
"""
이미 저장된 네이버 뉴스 항목 중 "&quot;" 같은 HTML 엔티티가 그대로 남아있는
제목/본문을 일괄로 복구하는 일회성 스크립트입니다.

실행: python fix_naver_entities.py
"""
import html

from db import get_conn


def fix():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, snippet FROM items WHERE source_name = '네이버 뉴스'"
        ).fetchall()

        fixed_count = 0
        for row in rows:
            new_title = html.unescape(row["title"] or "")
            new_snippet = html.unescape(row["snippet"] or "")
            if new_title != row["title"] or new_snippet != row["snippet"]:
                conn.execute(
                    "UPDATE items SET title = ?, snippet = ? WHERE id = ?",
                    (new_title, new_snippet, row["id"]),
                )
                fixed_count += 1
                print(f"  [복구] {row['title'][:50]} -> {new_title[:50]}")

    print(f"\n복구 완료: {fixed_count}건")


if __name__ == "__main__":
    fix()
