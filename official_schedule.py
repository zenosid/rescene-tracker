# -*- coding: utf-8 -*-
"""
Mnet Plus 공식 아티스트 스케줄 페이지에서 실제 방영된 그대로의 일정을 가져옵니다.
JS로 렌더링되는 페이지라 requests/BeautifulSoup만으로는 안 되고, Playwright로
브라우저를 띄워서 렌더링된 결과를 읽습니다.

다른 수집(뉴스/차트)보다 자주 돌릴 필요가 없어서(공식 일정이 30분마다 바뀌진
않음) 별도 GitHub Actions 워크플로(6시간 간격)로 분리되어 있습니다.

사전 준비 (최초 1회):
    pip install playwright
    python -m playwright install chromium --with-deps

실행: python official_schedule.py
"""
import re
from datetime import datetime

from bs4 import BeautifulSoup

from config import MNET_PLUS_ENV, MNET_PLUS_ARTIST_SLUG, MNET_PLUS_MONTHS_AHEAD
from db import init_db, get_conn, insert_official_schedule, delete_official_schedule_month
from kst import now_kst

BASE_URL = "https://artist.mnetplus.world/main/{env}/{slug}/schedule/{year}/{month:02d}"

# 이벤트 제목 키워드로 카테고리를 대략 분류 (공식 페이지 자체 필터 라벨과 유사하게)
_CATEGORY_RULES = [
    (re.compile(r"[<〈].+?[>〉]"), "방송"),  # "SBS <인기가요>" 처럼 방송/프로그램명이 꺾쇠로 표시됨
    (re.compile(r"라디오"), "라디오"),
    (re.compile(r"팬사인회|팬미팅"), "팬사인회"),
    (re.compile(r"콘서트|페스티벌|퍼포먼스|공연"), "공연"),
    (re.compile(r"발매|Special Single|앨범|Album"), "발매"),
    (re.compile(r"시구|위촉식|축제|파티|홍보대사"), "행사"),
]


def _classify(title):
    for pattern, category in _CATEGORY_RULES:
        if pattern.search(title):
            return category
    return "기타"


def _fetch_month_html(year, month):
    """Playwright로 해당 월의 스케줄 페이지를 렌더링해서 HTML을 반환."""
    from playwright.sync_api import sync_playwright  # 지연 import (미설치 환경 배려)

    url = BASE_URL.format(env=MNET_PLUS_ENV, slug=MNET_PLUS_ARTIST_SLUG, year=year, month=month)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(ignore_https_errors=True)
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3500)  # React 렌더링 대기
        html = page.content()
        browser.close()
    return html


def _parse_month_html(html):
    """FullCalendar 리스트뷰 HTML에서 (date, time_text, title, category)를 추출."""
    soup = BeautifulSoup(html, "html.parser")
    events = []
    current_date = None

    for row in soup.select("tr.fc-list-day, tr.fc-list-event"):
        classes = row.get("class", [])
        if "fc-list-day" in classes:
            current_date = row.get("data-date")
            continue
        if "fc-list-event" in classes and current_date:
            title_el = row.select_one('[class*="ListEventContentContainer_title"]')
            duration_el = row.select_one('[class*="ListEventContentContainer_duration"]')
            title = title_el.get_text(strip=True) if title_el else row.get_text(" ", strip=True)
            time_text = duration_el.get_text(strip=True) if duration_el else ""
            if not title:
                continue
            events.append(
                {
                    "date": current_date,
                    "time_text": time_text,
                    "title": title,
                    "category": _classify(title),
                }
            )
    return events


def collect_official_schedule():
    """이번 달부터 MNET_PLUS_MONTHS_AHEAD개월 뒤까지 공식 스케줄을 가져와서 DB에 저장."""
    init_db()
    today = now_kst().date()

    months_to_fetch = []
    year, month = today.year, today.month
    for _ in range(MNET_PLUS_MONTHS_AHEAD + 1):  # 이번 달 포함
        months_to_fetch.append((year, month))
        month += 1
        if month > 12:
            month, year = 1, year + 1

    new_count = 0
    consecutive_empty = 0
    with get_conn() as conn:
        for year, month in months_to_fetch:
            try:
                html = _fetch_month_html(year, month)
            except Exception as e:
                print(f"  [경고] {year}-{month:02d} 페이지 로딩 실패: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    print("  연속 2개월 조회 실패라 이후 달은 건너뜁니다 (다음 실행에서 재시도).")
                    break
                continue

            events = _parse_month_html(html)
            print(f"  {year}-{month:02d}: {len(events)}건 발견")
            consecutive_empty = consecutive_empty + 1 if len(events) == 0 else 0

            # 이번에 조회한 달은 최신 상태로 완전히 교체 (Mnet에서 삭제/변경된
            # 일정이 저희 DB에 예전 상태로 계속 남아있는 걸 방지)
            delete_official_schedule_month(conn, year, month)
            for ev in events:
                dedup_key = f"{ev['date']}|{ev['title']}|{ev['time_text']}"
                is_new = insert_official_schedule(
                    conn, ev["date"], ev["time_text"], ev["title"], ev["category"], dedup_key
                )
                if is_new:
                    new_count += 1
                    print(f"    [신규] {ev['date']} {ev['time_text']} - {ev['title']}")

            # 아직 일정이 안 잡힌 먼 미래 달이 연속으로 비어있으면 굳이 더 안 봐도 됨
            # (그래도 최소 몇 달은 항상 확인하도록 위에서 이미 목록을 다 만들어뒀음)
            if consecutive_empty >= 3:
                print("  연속 3개월간 일정이 없어 이후 달 조회를 생략합니다.")
                break

    print(f"\n공식 스케줄 신규 {new_count}건")
    return new_count


if __name__ == "__main__":
    collect_official_schedule()
