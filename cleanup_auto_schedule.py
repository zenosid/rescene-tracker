# -*- coding: utf-8 -*-
"""
이미 auto_schedule 테이블에 저장된 "뉴스 기반 추정 스케줄" 중, 개선된 필터
기준(선공개/영상공개 등 제외, '출연' 키워드 제거)으로 다시 걸러서 더 이상
유효하지 않은 항목을 정리하는 일회성 스크립트입니다.

실행: python cleanup_auto_schedule.py
"""
from schedule_extractor import _match_event_type, _is_content_release_news
from db import get_conn


def cleanup():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM auto_schedule").fetchall()

        to_delete = []
        for row in rows:
            text = row["title"]  # 원문 스니펫은 auto_schedule에 저장 안 해서 제목 기준으로만 재검증
            if _is_content_release_news(text):
                to_delete.append(row["id"])
                continue
            event_type, _keyword = _match_event_type(text)
            if not event_type:
                to_delete.append(row["id"])

        print(f"자동 스케줄 전체 {len(rows)}건 중, 더 이상 유효하지 않은 {len(to_delete)}건 삭제 예정")
        for row in rows:
            if row["id"] in to_delete:
                print(f"  [삭제] {row['date']} {row['type']} - {row['title'][:50]}")

        if to_delete:
            conn.executemany("DELETE FROM auto_schedule WHERE id = ?", [(i,) for i in to_delete])

    print(f"\n정리 완료: {len(to_delete)}건 삭제됨")


if __name__ == "__main__":
    cleanup()
