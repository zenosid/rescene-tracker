# -*- coding: utf-8 -*-
"""
네이버 뉴스로 이미 저장된 항목 중, 제목+본문에 리센느/RESCENE이 실제로 없는
(느슨한 매칭으로 잘못 들어온) 기존 데이터를 정리하는 일회성 스크립트입니다.

앞으로 새로 수집되는 건 collector.py에 이미 필터가 적용되어 있어서
자동으로 걸러지고, 이 스크립트는 "이미 쌓여있던 예전 데이터"만 청소합니다.

실행: python cleanup_naver_news.py
"""
from config import CHART_KEYWORDS
from db import get_conn


def _is_our_group(text):
    return any(keyword in text for keyword in CHART_KEYWORDS)


def cleanup():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, snippet FROM items WHERE source_name = '네이버 뉴스'"
        ).fetchall()

        # 제목에 실제로 우리 그룹이 없는 건 삭제 (본문에 스쳐 지나가듯 언급된
        # 라인업 나열 기사 등을 걸러내기 위해 제목만 기준으로 봄)
        to_delete = [row["id"] for row in rows if not _is_our_group(row["title"])]

        print(f"네이버 뉴스 전체 {len(rows)}건 중, 무관한 {len(to_delete)}건 삭제 예정")
        for row in rows:
            if row["id"] in to_delete:
                print(f"  [삭제] {row['title'][:60]}")

        if to_delete:
            conn.executemany(
                "DELETE FROM items WHERE id = ?", [(i,) for i in to_delete]
            )

    print(f"\n정리 완료: {len(to_delete)}건 삭제됨")


if __name__ == "__main__":
    cleanup()
