# -*- coding: utf-8 -*-
"""
멜론 / 지니 / 벅스 공개 차트 페이지(로그인 불필요)에서
리센느 곡의 실시간 순위를 조회해서 DB에 기록합니다.

주의:
- 개인 사용 목적의 저빈도 조회용입니다 (버튼 누를 때마다 1회 요청).
- 각 사이트의 HTML 구조가 바뀌면 파싱이 깨질 수 있습니다.
- 스포티파이/유튜브뮤직/바이브/플로는 로그인 없이 안정적으로 파싱하기 어려워
  우선 제외했습니다. 필요하시면 공식 API(Spotify Web API 등) 연동을 추가로 논의할 수 있습니다.

실행: python chart_tracker.py  (단독 실행 시 콘솔에 결과 출력)
"""
import requests
from bs4 import BeautifulSoup

from config import CHART_KEYWORDS, CHART_SOURCES
from db import init_db, get_conn, save_chart_snapshot, get_latest_chart_snapshot

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _is_our_group(text):
    return any(keyword in text for keyword in CHART_KEYWORDS)


def fetch_melon():
    """멜론 TOP100 전체를 순회하며 리센느 곡만 추출."""
    r = requests.get(CHART_SOURCES["melon"], headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for row in soup.select("tr.lst50, tr.lst100"):
        rank_el = row.select_one(".rank")
        title_el = row.select_one(".rank01 a")
        artist_el = row.select_one(".rank02 a")
        if not (rank_el and title_el and artist_el):
            continue
        artist_text = artist_el.get_text(strip=True)
        if _is_our_group(artist_text):
            results.append(
                {
                    "rank": int(rank_el.get_text(strip=True)),
                    "song_title": title_el.get_text(strip=True),
                    "artist_text": artist_text,
                }
            )
    return results


def fetch_genie():
    """지니 TOP200(웹 페이지 기준 50위까지 노출) 중 리센느 곡만 추출."""
    r = requests.get(CHART_SOURCES["genie"], headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for row in soup.select("tr.list"):
        rank_el = row.select_one(".number")
        title_el = row.select_one(".title")
        artist_el = row.select_one(".artist")
        if not (rank_el and title_el and artist_el):
            continue
        artist_text = artist_el.get_text(strip=True)
        if _is_our_group(artist_text):
            # rank_el 안에 "1위" 텍스트와 변동 정보가 섞여있어 숫자만 추출
            rank_num = "".join(ch for ch in rank_el.get_text() if ch.isdigit())
            if not rank_num:
                continue
            results.append(
                {
                    "rank": int(rank_num),
                    "song_title": title_el.get_text(strip=True),
                    "artist_text": artist_text,
                }
            )
    return results


def fetch_bugs():
    """벅스 실시간 차트 중 리센느 곡만 추출."""
    r = requests.get(CHART_SOURCES["bugs"], headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for row in soup.select("table.byChart tbody tr"):
        rank_el = row.select_one(".ranking")
        title_el = row.select_one(".title a")
        artist_el = row.select_one(".artist a")
        if not (rank_el and title_el and artist_el):
            continue
        artist_text = artist_el.get_text(strip=True)
        if _is_our_group(artist_text):
            rank_num = "".join(ch for ch in rank_el.get_text() if ch.isdigit())
            if not rank_num:
                continue
            results.append(
                {
                    "rank": int(rank_num),
                    "song_title": title_el.get_text(strip=True),
                    "artist_text": artist_text,
                }
            )
    return results


FETCHERS = {
    "melon": fetch_melon,
    "genie": fetch_genie,
    "bugs": fetch_bugs,
}


def refresh_all_charts():
    """모든 플랫폼을 조회해서 DB에 스냅샷 저장. 결과와 에러를 함께 반환."""
    init_db()
    summary = {}
    errors = []
    with get_conn() as conn:
        for platform, fetch_fn in FETCHERS.items():
            try:
                songs = fetch_fn()
                for s in songs:
                    save_chart_snapshot(
                        conn, platform, s["rank"], s["song_title"], s["artist_text"]
                    )
                summary[platform] = songs
            except Exception as e:
                errors.append((platform, str(e)))
                summary[platform] = []
    return summary, errors


def get_latest_all(conn):
    """플랫폼별 가장 최근 스냅샷을 딕셔너리로 반환."""
    return {platform: get_latest_chart_snapshot(conn, platform) for platform in FETCHERS}


if __name__ == "__main__":
    summary, errors = refresh_all_charts()
    for platform, songs in summary.items():
        if songs:
            for s in songs:
                print(f"[{platform}] {s['rank']}위 - {s['song_title']} ({s['artist_text']})")
        else:
            print(f"[{platform}] 리센느 곡이 현재 차트에 없습니다 (또는 조회 실패).")
    for platform, err in errors:
        print(f"[에러] {platform}: {err}")
