# -*- coding: utf-8 -*-
"""
저장은 항상 UTC로 하되(서버가 어디서 돌든 일관되게), 화면 표시용으로 변환할 때만
이 모듈을 거쳐 KST(Asia/Seoul, UTC+9)로 바꿉니다.

- GitHub Actions 러너는 UTC로 동작하므로, datetime.now()를 그냥 쓰면 로컬(한국)에서
  돌릴 때와 9시간 차이가 나서 값이 달라집니다. 그래서 "현재 시각"이 필요한 곳은
  전부 now_kst()를 쓰고, DB에 저장된 UTC 문자열은 표시 직전에 변환합니다.
"""
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def now_kst():
    return datetime.now(KST)


def to_kst(value):
    """
    ISO 형식('...T...+00:00') 또는 SQLite 기본 형식('YYYY-MM-DD HH:MM:SS',
    tzinfo 없는 UTC naive) 문자열을 모두 받아서 KST datetime으로 변환.
    이미 datetime 객체면 그대로 tzinfo만 보정.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def to_kst_str(value, fmt="%Y-%m-%d %H:%M"):
    dt = to_kst(value)
    return dt.strftime(fmt) if dt else ""
