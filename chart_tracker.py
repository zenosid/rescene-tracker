# -*- coding: utf-8 -*-
"""
멜론 / 지니 / 벅스 공개 차트 페이지(로그인 불필요) + kworb.net(스포티파이가
공개한 데이터를 미러링하는 오래된 공개 통계 사이트, 2012년~)에서 리센느 곡의
실시간 순위를 조회해서 DB에 기록합니다.

주의:
- 개인 사용 목적의 저빈도 조회용입니다.
- 각 사이트의 HTML 구조가 바뀌면 파싱이 깨질 수 있습니다.
- VIBE/FLO/유튜브뮤직 자체 차트는 로그인 없이 안정적으로 파싱하기 어려워 제외했습니다.

실행: python chart_tracker.py  (단독 실행 시 콘솔에 결과 출력)
"""
import re

import requests
from bs4 import BeautifulSoup

from config import CHART_KEYWORDS, CHART_SOURCES, KWORB_SPOTIFY_COUNTRIES
from db import init_db, get_conn, save_chart_snapshot, get_latest_chart_snapshot

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

KWORB_URL = "https://kworb.net/itunes/artist/rescene.html"
KWORB_SPOTIFY_COUNTRY_URL = "https://kworb.net/spotify/country/{cc}_daily.html"
# kworb 표기 -> 우리 플랫폼 키 (한국 순위만 사용, 스포티파이는 국가별로 별도 처리)
_KWORB_SERVICE_MAP = {"YouTube": "youtube_kr", "Shazam": "shazam_kr"}
_KWORB_LINE_RE = re.compile(r"^(\w[\w\s]*?):\s*#(\d+)\s+(.+?)\s*\(([^)]+)\)$")


def _is_our_group(text):
    return any(keyword in text for keyword in CHART_KEYWORDS)


def fetch_kworb_spotify_country(country_code):
    """
    kworb.net의 국가별 스포티파이 데일리 차트(TOP 200) 전체에서 리센느 곡만 추출.
    (멜론/지니/벅스와 같은 방식 - 전체 목록을 훑어서 우리 그룹만 골라냄)
    """
    url = KWORB_SPOTIFY_COUNTRY_URL.format(cc=country_code)
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
        artist_link = tds[2].find("a")
        artist_name = artist_link.get_text(strip=True) if artist_link else ""
        if not _is_our_group(artist_name):
            continue
        combined_text = tds[2].get_text(strip=True)
        song_title = combined_text[len(artist_name):].lstrip("-").strip() or combined_text
        try:
            rank = int(tds[0].get_text(strip=True))
        except ValueError:
            continue
        results.append({"rank": rank, "song_title": song_title, "artist_text": artist_name})
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


def fetch_kworb_global():
    """
    kworb.net에서 스포티파이/유튜브/샤잠의 한국 순위(+전일 대비 변동)를 가져옵니다.
    변동 표기는 kworb가 이미 계산해둔 걸 그대로 씁니다 ("NE"=신규, "="=변동없음,
    "+3"/"-3" 등은 순위 상승/하락).
    """
    r = requests.get(KWORB_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    seen = set()
    results = []
    for wrap in soup.find_all("div", class_="wrap"):
        song_title = wrap.get_text(strip=True)
        node = wrap
        while True:
            node = node.find_next_sibling()
            if node is None or (node.name == "div" and "wrap" in (node.get("class") or [])):
                break
            if node.name != "div":
                continue
            m = _KWORB_LINE_RE.match(node.get_text(" ", strip=True))
            if not m:
                continue
            service, rank, country, change = m.groups()
            if service not in _KWORB_SERVICE_MAP or "South Korea" not in country:
                continue
            key = (service, song_title)
            if key in seen:  # 페이지에 같은 정보가 두 번 나오는 구간이 있어서 중복 제거
                continue
            seen.add(key)
            platform = _KWORB_SERVICE_MAP[service]
            results.append(
                {
                    "platform": platform,
                    "rank": int(rank),
                    "song_title": song_title,
                    "artist_text": "RESCENE",
                }
            )
    return results


FETCHERS = {
    "melon": fetch_melon,
    "genie": fetch_genie,
    "bugs": fetch_bugs,
}

# kworb 아티스트 요약 페이지는 한 번 요청으로 유튜브/샤잠 정보를 동시에 줌
KWORB_PLATFORMS = list(_KWORB_SERVICE_MAP.values())
# 스포티파이는 국가별로 각각 요청 (KWORB_SPOTIFY_COUNTRIES 설정에 따라 결정)
KWORB_SPOTIFY_PLATFORMS = [f"spotify_{cc}" for cc in KWORB_SPOTIFY_COUNTRIES]


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

        # 스포티파이 국가별 차트 (저장 키: spotify_kr, spotify_us, spotify_jp ...)
        for country_code in KWORB_SPOTIFY_COUNTRIES:
            platform = f"spotify_{country_code}"
            try:
                songs = fetch_kworb_spotify_country(country_code)
                for s in songs:
                    save_chart_snapshot(conn, platform, s["rank"], s["song_title"], s["artist_text"])
                summary[platform] = songs
            except Exception as e:
                errors.append((platform, str(e)))
                summary[platform] = []

        # 유튜브/샤잠(한국) - 아티스트 요약 페이지에서 한 번에
        try:
            kworb_songs = fetch_kworb_global()
            for platform in KWORB_PLATFORMS:
                summary[platform] = []
            for s in kworb_songs:
                save_chart_snapshot(conn, s["platform"], s["rank"], s["song_title"], s["artist_text"])
                summary[s["platform"]].append(s)
        except Exception as e:
            errors.append(("kworb(youtube/shazam)", str(e)))
            for platform in KWORB_PLATFORMS:
                summary[platform] = []

    return summary, errors


def get_latest_all(conn):
    """플랫폼별 가장 최근 스냅샷을 딕셔너리로 반환."""
    all_platforms = list(FETCHERS.keys()) + KWORB_SPOTIFY_PLATFORMS + KWORB_PLATFORMS
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
