# -*- coding: utf-8 -*-
"""
영상 제목을 보고 멤버·카테고리를 대략적으로 추론합니다.
100% 정확하지 않을 수 있는 키워드 기반 휴리스틱입니다 (config.py에서 키워드 수정 가능).
"""
from config import MEMBER_KEYWORDS, CATEGORY_KEYWORDS


def classify_members(title):
    """제목에서 언급된 멤버 이름 목록을 반환. 아무도 안 걸리면 ['전체']."""
    matched = []
    for member, keywords in MEMBER_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            matched.append(member)
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
