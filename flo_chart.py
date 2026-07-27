# -*- coding: utf-8 -*-
"""
플로(FLO) "FLO차트"를 조회해서 DB에 저장합니다. Playwright(브라우저 자동화)가
필요해서, 이미 Playwright를 쓰고 있는 공식 스케줄 워크플로(6시간 간격)에
합류시켰습니다 (30분 주기 워크플로는 Playwright가 설치되어 있지 않습니다).

실행: python flo_chart.py
"""
from chart_tracker import fetch_flo
from db import init_db, get_conn, save_chart_snapshot


def collect_flo():
    init_db()
    try:
        songs = fetch_flo()
    except Exception as e:
        print(f"[경고] 플로 차트 조회 실패: {e}")
        return 0

    new_count = 0
    with get_conn() as conn:
        for s in songs:
            save_chart_snapshot(conn, "flo", s["rank"], s["song_title"], s["artist_text"])
            new_count += 1
            print(f"  [플로] {s['rank']}위 - {s['song_title']}")

    if not songs:
        print("플로 차트에 리센느 곡이 없습니다 (또는 페이지 구조 변경).")
    return new_count


if __name__ == "__main__":
    collect_flo()
