# -*- coding: utf-8 -*-
"""
영상 제목을 보고 멤버·카테고리를 대략적으로 추론합니다.
100% 정확하지 않을 수 있는 키워드 기반 휴리스틱입니다 (config.py에서 키워드 수정 가능).
"""
import re

from config import MEMBER_KEYWORDS, CATEGORY_KEYWORDS

_ASCII_RE = re.compile(r"^[A-Za-z0-9 ]+$")
_PARTICLES = "은|는|이|가|의|를|을|도|와|과|만|에|랑|로|야|아|님|씨|까지|처럼|에게|한테"

# 그룹명 표기 변형(오타·유사 표기 포함)
GROUP_NAME_RE = re.compile(r"리센느|르센느|이센느|rescene|resene|ricenne", re.I)

# 다른 그룹·일반 단어와 헷갈릴 일이 적은 멤버 표기. 방송 채널처럼 모든 가수 영상이
# 올라오는 곳에서는 그룹명이 없어도 이 이름이 '단독으로' 쓰인 경우에만 인정합니다.
DISTINCT_MEMBER_KEYWORDS = ["미나미", "MINAMI", "원이", "WONI", "제나", "ZENA"]


def _kw_in(text, kw):
    """영문 키워드는 단어 경계, 한글 키워드는 앞뒤가 한글로 이어지지 않을 때만(조사는 허용) 일치."""
    if _ASCII_RE.match(kw):
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(kw) + r"(?![A-Za-z0-9])", text, re.I) is not None
    pat = r"(?<![가-힣A-Za-z0-9])" + re.escape(kw) + r"(?:(?![가-힣])|(?=(?:" + _PARTICLES + r")))"
    return re.search(pat, text) is not None


def member_name_in(text):
    """멤버 이름(한글·영문 전부)이 단어 경계를 지켜 쓰였는지. 조사(은/는/가/의/와…)는 허용."""
    return any(_kw_in(text or "", kw) for kws in MEMBER_KEYWORDS.values() for kw in kws)


def is_relevant_broadcast(title, source_name=""):
    """
    음악방송 채널(음악중심·인기가요·더쇼)·유튜브 검색 결과처럼 '리센느와 무관한 영상이
    대부분'인 곳에서 쓰는 엄격한 관련성 판정.
      1) 제목/채널명에 그룹명이 있거나
      2) 구별되는 멤버 이름(미나미·원이·제나)이 단독으로 쓰인 경우만 통과.
    'LIVE'의 liv, 'Bloom' 같은 일반 곡명, '82메이저'의 메이 등은 통과하지 못합니다.
    """
    text = f"{title or ''} {source_name or ''}"
    if GROUP_NAME_RE.search(text):
        return True
    return any(_kw_in(title or "", kw) for kw in DISTINCT_MEMBER_KEYWORDS)


def classify_members(title):
    """제목에서 언급된 멤버 이름 목록을 반환. 아무도 안 걸리면 ['전체'].
    영문 키워드는 단어 경계로 비교합니다(예: LIVE의 'LIV'가 리브로 잡히는 문제 방지)."""
    matched = []
    for member, keywords in MEMBER_KEYWORDS.items():
        for kw in keywords:
            hit = _kw_in(title, kw) if _ASCII_RE.match(kw) else (kw in title)
            if hit:
                matched.append(member)
                break
    return matched if matched else ["전체"]


def classify_category(title, source_type):
    """제목/소스타입 기반 카테고리 추론."""
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in title.lower() for kw in keywords):
            return category
    if source_type == "youtube_collab":
        return "외부컨텐츠"
    if source_type == "youtube":
        return "자체컨텐츠"
    return "기타"
