# -*- coding: utf-8 -*-
"""
이미 수집된 뉴스/커뮤니티/X 글 중에서, 부적절할 수 있는 내용을 다루는 것으로
보이는 항목을 골라서 표시합니다.

중요: 이 모듈은 아무것도 자동으로 신고하지 않습니다. 키워드가 걸렸다고 해서
실제로 문제가 있다는 뜻은 아니며(예: "논란"이라는 단어는 긍정적인 맥락에서도
쓰일 수 있음), 그냥 "사람이 한번 검토해볼 만한 것"으로만 표시합니다.
결과는 공개 사이트(data.js)에 절대 포함되지 않고, moderation_flags 테이블과
GitHub Actions 실행 로그(저장소 소유자/협업자만 볼 수 있음)에만 남습니다.

실행: python moderation_scan.py
"""
from config import MODERATION_KEYWORDS
from db import init_db, get_conn, get_recent_items, insert_moderation_flag


def _matched_keyword(title):
    for kw in MODERATION_KEYWORDS:
        if kw in title:
            return kw
    return None


def scan_for_moderation(conn):
    """이미 저장된 뉴스/커뮤니티/X 항목을 스캔해서 새로 걸린 것만 기록."""
    items = get_recent_items(conn, limit=1000)
    targets = [i for i in items if i["source_type"] in ("news", "community", "x")]

    new_count = 0
    for item in targets:
        matched = _matched_keyword(item["title"])
        if not matched:
            continue
        is_new = insert_moderation_flag(
            conn, item["source_type"], item["source_name"], item["title"],
            item["link"], matched,
        )
        if is_new:
            new_count += 1
            print(f"  [모더레이션 검토 필요] ({matched}) {item['source_name']} - {item['title']}")
            print(f"      링크: {item['link']}")

    if new_count == 0:
        print("  신규 검토 대상 없음.")
    else:
        print(
            f"\n  ⚠️  총 {new_count}건이 검토 대상으로 새로 표시됐습니다. "
            f"위 링크들을 직접 확인하시고, 실제로 문제가 있다고 판단되면 "
            f"각 플랫폼의 정식 신고 기능으로 신고해주세요 (자동 신고 아님)."
        )
    return new_count


if __name__ == "__main__":
    init_db()
    with get_conn() as conn:
        scan_for_moderation(conn)
