# -*- coding: utf-8 -*-
"""
지니/벅스 파싱 버그(순위+변동 숫자가 합쳐져서 저장된 경우)로 잘못 기록된
비정상적인 순위 스냅샷을 정리하는 일회성 스크립트입니다.

지니는 TOP 200, 벅스는 TOP 100까지만 존재하므로, 그보다 훨씬 큰 값(예: 300
이상)은 파싱 버그로 생긴 잘못된 기록으로 보고 삭제합니다.

실행: python cleanup_bad_ranks.py
"""
from db import get_conn

# 플랫폼별로 "이 숫자보다 크면 확실히 잘못된 값" 기준
MAX_PLAUSIBLE_RANK = {
    "genie": 200,
    "bugs": 100,
}


def cleanup():
    with get_conn() as conn:
        total_deleted = 0
        for platform, max_rank in MAX_PLAUSIBLE_RANK.items():
            rows = conn.execute(
                "SELECT id, rank, song_title, checked_at FROM chart_snapshots "
                "WHERE platform = ? AND rank > ?",
                (platform, max_rank),
            ).fetchall()
            if not rows:
                print(f"[{platform}] 이상값 없음")
                continue
            print(f"[{platform}] 이상값 {len(rows)}건 삭제 예정 (최대 허용: {max_rank})")
            for row in rows:
                print(f"  [삭제] {row['checked_at']} - {row['rank']}위 {row['song_title']}")
            ids = [(r["id"],) for r in rows]
            conn.executemany("DELETE FROM chart_snapshots WHERE id = ?", ids)
            total_deleted += len(rows)

    print(f"\n정리 완료: 총 {total_deleted}건 삭제됨")


if __name__ == "__main__":
    cleanup()
