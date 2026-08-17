# -*- coding: utf-8 -*-
"""
YouTube Data API로 등록된 공식 채널의 '전체' 영상 이력을 가져옵니다.
평소 쓰는 RSS(collector.py)는 채널당 최근 15개 정도만 주기 때문에, 데뷔
시점까지 거슬러 올라가려면 이 스크립트가 필요합니다.

RSS와 달리 API 키(YOUTUBE_API_KEY, 팬 반응 기능과 같은 키 재사용)가 필요하고,
할당량을 아끼기 위해 30분마다 도는 collector.py에는 포함되어 있지 않습니다.
채널 영상이 아주 많이 늘어난 게 아니라면 가끔(예: 한 달에 한 번) 수동으로
한 번씩만 돌리시면 됩니다. 이미 저장된 영상은 링크 기준으로 중복 방지되니
여러 번 돌려도 안전합니다.

실행: python youtube_backfill.py
"""
import os

import requests

from config import YOUTUBE_CHANNELS
from db import init_db, get_conn, insert_item

API_BASE = "https://www.googleapis.com/youtube/v3"


def _uploads_playlist_id(channel_id):
    """채널의 '업로드 전체' 재생목록 ID는 채널 ID의 UC를 UU로 바꾼 것과 같습니다
    (유튜브가 채널마다 자동으로 만들어주는 재생목록의 관례적인 규칙)."""
    if channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return None


def backfill_channel(conn, api_key, channel_name, channel_id):
    playlist_id = _uploads_playlist_id(channel_id)
    if not playlist_id:
        print(f"  [경고] {channel_name}: 채널 ID 형식이 예상과 달라 건너뜁니다 ({channel_id})")
        return 0

    new_count = 0
    page_token = None
    page_num = 0

    while True:
        page_num += 1
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            r = requests.get(f"{API_BASE}/playlistItems", params=params, timeout=15)
        except requests.RequestException as e:
            print(f"  [경고] {channel_name} 백필 실패({page_num}페이지): {e}")
            break

        if r.status_code != 200:
            print(f"  [경고] {channel_name} 백필 실패: HTTP {r.status_code} - {r.text[:200]}")
            break

        data = r.json()
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            resource = snippet.get("resourceId", {})
            video_id = resource.get("videoId")
            if not video_id:
                continue  # 삭제/비공개 처리된 영상 등은 건너뜀

            title = snippet.get("title", "(제목 없음)")
            if title in ("Private video", "Deleted video"):
                continue

            published_at = snippet.get("publishedAt", "")
            description = (snippet.get("description") or "")[:500]
            link = f"https://www.youtube.com/watch?v={video_id}"

            is_new = insert_item(conn, "youtube", channel_name, title, link, published_at, description)
            if is_new:
                new_count += 1
                date_only = published_at[:10] if published_at else "?"
                print(f"  [신규/백필] {channel_name} - {date_only} - {title}")

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return new_count


def run_backfill():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("YOUTUBE_API_KEY가 설정되어 있지 않아 백필을 진행할 수 없습니다.")
        print("(팬 반응 기능과 같은 키를 씁니다 - 이미 등록되어 있다면 로컬 환경변수도 확인해주세요)")
        return

    init_db()
    with get_conn() as conn:
        total = 0
        for ch in YOUTUBE_CHANNELS:
            print(f"'{ch['name']}' 전체 영상 이력 백필 중...")
            total += backfill_channel(conn, api_key, ch["name"], ch["channel_id"])

    print(f"\n백필 완료: 신규 {total}건")


if __name__ == "__main__":
    run_backfill()
