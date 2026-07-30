# -*- coding: utf-8 -*-
"""
YouTube Data API v3(공식 API)로 최근 영상들의 인기 댓글을 가져와서
"팬 반응"으로 저장합니다.

사전 준비:
- Google Cloud Console에서 YouTube Data API v3를 사용 설정하고 API 키를 발급받아
  환경변수 YOUTUBE_API_KEY로 설정해야 합니다. (config.py 참고)
- 키가 없으면 이 모듈은 아무 것도 하지 않고 조용히 넘어갑니다.

실행: python fan_reactions.py
"""
import os
import re

import requests

from config import YOUTUBE_COMMENTS_MAX_VIDEOS, YOUTUBE_COMMENTS_PER_VIDEO
from db import init_db, get_conn, get_recent_items, insert_fan_reaction

API_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
_VIDEO_ID_RE = re.compile(r"(?:v=|/shorts/|youtu\.be/)([\w-]{11})")


def _extract_video_id(link):
    m = _VIDEO_ID_RE.search(link or "")
    return m.group(1) if m else None


def _fetch_comments_for_video(api_key, video_id, max_results):
    """댓글이 잠겨있거나 비활성화된 영상은 조용히 빈 목록 반환. 그 외 에러는 표시."""
    params = {
        "part": "snippet",
        "videoId": video_id,
        "order": "relevance",  # 인기(관련도) 순
        "maxResults": max_results,
        "textFormat": "plainText",
        "key": api_key,
    }
    try:
        r = requests.get(API_URL, params=params, timeout=15)
    except requests.RequestException as e:
        return [], f"네트워크 오류: {e}"

    if r.status_code != 200:
        error_info = {}
        try:
            error_info = r.json().get("error", {})
        except Exception:
            pass
        reasons = [e.get("reason", "") for e in error_info.get("errors", [])]

        if "commentsDisabled" in reasons or "videoNotFound" in reasons:
            return [], None  # 흔한 정상 상황 - 조용히 건너뜀

        # 그 외(할당량 초과, 키 오류 등)는 진짜 문제니 표시해야 함
        message = error_info.get("message") or r.text[:200]
        return [], f"HTTP {r.status_code} - {message}"

    items = r.json().get("items", [])
    results = []
    for item in items:
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        results.append(
            {
                "comment_id": item["id"],
                "author": snippet.get("authorDisplayName", "익명"),
                "text": snippet.get("textDisplay", ""),
                "like_count": snippet.get("likeCount", 0),
                "published_at": snippet.get("publishedAt", ""),
            }
        )
    return results, None


def collect_fan_reactions():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("YOUTUBE_API_KEY가 설정되어 있지 않아 팬 반응 수집을 건너뜁니다.")
        return 0

    init_db()
    with get_conn() as conn:
        items = get_recent_items(conn, limit=500)
        videos = [
            i for i in items if i["source_type"] in ("youtube", "youtube_collab")
        ][:YOUTUBE_COMMENTS_MAX_VIDEOS]

        new_count = 0
        for video in videos:
            video_id = _extract_video_id(video["link"])
            if not video_id:
                continue
            comments, err = _fetch_comments_for_video(api_key, video_id, YOUTUBE_COMMENTS_PER_VIDEO)
            if err:
                print(f"  [경고] {video['title'][:30]} 댓글 조회 실패: {err}")
                continue
            for c in comments:
                is_new = insert_fan_reaction(
                    conn,
                    video["link"],
                    video["title"],
                    c["author"],
                    c["text"],
                    c["like_count"],
                    c["published_at"],
                    c["comment_id"],
                )
                if is_new:
                    new_count += 1

    print(f"팬 반응(유튜브 댓글) 신규 {new_count}건")
    return new_count


if __name__ == "__main__":
    collect_fan_reactions()
