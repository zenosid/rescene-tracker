# -*- coding: utf-8 -*-
"""
멜론 / 지니 / 벅스 공개 차트 페이지(로그인 불필요) + kworb.net(2012년부터 운영된
공개 음원 통계 사이트 - 스포티파이/유튜브/샤잠이 공개한 데이터를 미러링)에서
리센느 곡의 실시간 순위를 조회해서 DB에 기록합니다.

kworb의 국가별 전체 차트(TOP 200 등)를 멜론/지니/벅스와 똑같은 방식으로
"전체 목록을 훑어서 우리 그룹만 골라내는" 방식으로 처리합니다. 국가는
config.py의 KWORB_SPOTIFY_COUNTRIES / KWORB_SHAZAM_COUNTRIES /
KWORB_YOUTUBE_COUNTRIES에서 자유롭게 추가/삭제할 수 있습니다.

주의:
- 개인 사용 목적의 저빈도 조회용입니다.
- 각 사이트의 HTML 구조가 바뀌면 파싱이 깨질 수 있습니다.
- VIBE/FLO/유튜브뮤직(국내 자체 차트)은 로그인 없이 안정적으로 파싱하기 어려워 제외했습니다.

실행: python chart_tracker.py  (단독 실행 시 콘솔에 결과 출력)
"""
import re

import requests
from bs4 import BeautifulSoup

from config import (
    CHART_KEYWORDS,
    CHART_SOURCES,
    KWORB_SPOTIFY_COUNTRIES,
    KWORB_SHAZAM_COUNTRIES,
    KWORB_YOUTUBE_COUNTRIES,
)
from db import init_db, get_conn, save_chart_snapshot, get_latest_chart_snapshot

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# "RESCENE-LOVE ATTACK"(스포티파이, 공백 없음) / "RESCENE - LOVE ATTACK"(샤잠·유튜브,
# 공백 있음) 두 표기 모두 처리
_ARTIST_TITLE_RE = re.compile(r"^(RESCENE|리센느)\s*-\s*(.+)$", re.IGNORECASE)


def _is_our_group(text):
    return any(keyword in text for keyword in CHART_KEYWORDS)


def _fetch_kworb_country_chart(url):
    """
    kworb.net의 국가별 차트 페이지(테이블: 순위 | 변동 | '아티스트 - 곡명' | ...)에서
    리센느 곡만 추출하는 공용 함수. 스포티파이/샤잠/유튜브(insights) 모두 이 형태.
    """
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    results = []
    if not table:
        return results

    for row in table.select("tr")[1:]:
        tds = row.find_all("td")
        if len(tds) < 3:
            continue
        try:
            rank = int(tds[0].get_text(strip=True))
        except ValueError:
            continue

        combined_text = tds[2].get_text(" ", strip=True)
        m = _ARTIST_TITLE_RE.match(combined_text)
        if not m:
            continue
        song_title = m.group(2).strip()
        results.append({"rank": rank, "song_title": song_title, "artist_text": "RESCENE"})
    return results


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

# kworb 국가별 차트: (플랫폼 접두어, URL 템플릿, 국가 목록)
_KWORB_SOURCES = [
    ("spotify", "https://kworb.net/spotify/country/{cc}_daily.html", KWORB_SPOTIFY_COUNTRIES),
    ("shazam", "https://kworb.net/charts/shazam/{cc}.html", KWORB_SHAZAM_COUNTRIES),
    ("youtube", "https://kworb.net/youtube/insights/{cc}_daily.html", KWORB_YOUTUBE_COUNTRIES),
]


def _kworb_platform_list():
    return [f"{prefix}_{cc}" for prefix, _url, countries in _KWORB_SOURCES for cc in countries]


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
                    save_chart_snapshot(conn, platform, s["rank"], s["song_title"], s["artist_text"])
                summary[platform] = songs
            except Exception as e:
                errors.append((platform, str(e)))
                summary[platform] = []

        for prefix, url_template, countries in _KWORB_SOURCES:
            for country_code in countries:
                platform = f"{prefix}_{country_code}"
                try:
                    songs = _fetch_kworb_country_chart(url_template.format(cc=country_code))
                    for s in songs:
                        save_chart_snapshot(conn, platform, s["rank"], s["song_title"], s["artist_text"])
                    summary[platform] = songs
                except Exception as e:
                    errors.append((platform, str(e)))
                    summary[platform] = []

    return summary, errors


def get_latest_all(conn):
    """플랫폼별 가장 최근 스냅샷을 딕셔너리로 반환."""
    all_platforms = list(FETCHERS.keys()) + _kworb_platform_list()
    return {platform: get_latest_chart_snapshot(conn, platform) for platform in all_platforms}


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
