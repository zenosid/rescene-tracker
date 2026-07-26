# -*- coding: utf-8 -*-
"""
리센느(RESCENE) 덕질 트래커 설정 파일 v2
- Claude 요약 기능은 제거되었습니다 (아카이브 + 차트 + 스케줄 전용).
- 여기 있는 값만 수정하면 소스를 추가/변경할 수 있습니다.
"""

# ── YouTube 채널 (RSS 방식, API 키 불필요) ──────────────────────────
YOUTUBE_CHANNELS = [
    {"name": "RESCENE 공식 유튜브", "channel_id": "UCtKtCiaWRz-d3EZn2xd1mdA"},
    {"name": "안녕하세요원이입니다잘부탁드립니다", "channel_id": "UCWpY0eSJtyO-qNAPbKFRSSg"},
]

# ── 콜라보/외부 채널 (수동 등록) ──────────────────────────────
# 확실히 챙기고 싶은 채널은 여기 등록하면 조회수 상관없이 항상 수집합니다.
COLLAB_CHANNELS = [
    {"name": "침착맨", "channel_id": "UCUj6rrhMTR9pipbAWBAMvUQ"},
    {"name": "도미노피자", "channel_id": "UCrDYPLah4QRsqEZVvWQ6t7g"},
]

# ── 콜라보 자동 발견 (유튜브 검색 기반) ─────────────────────────
# 채널을 미리 등록하지 않아도, 아래 검색어로 유튜브를 검색해서
# 조회수가 SEARCH_MIN_VIEWS 이상인 영상은 채널 상관없이 자동으로 수집합니다.
SEARCH_QUERIES = ["리센느", "RESCENE 리센느"]
SEARCH_MIN_VIEWS = 100_000


# ── 분류용 키워드 ───────────────────────────────────────────────
# 멤버별 필터링에 쓰입니다. 제목에 아래 키워드 중 하나라도 있으면 해당 멤버로 태깅.
MEMBER_KEYWORDS = {
    "원이": ["원이", "WONI"],
    "리브": ["리브", "LIV"],
    "미나미": ["미나미", "MINAMI"],
    "메이": ["메이", "MAY"],
    "제나": ["제나", "ZENA"],
}

# 영상 카테고리 추론용 키워드 (제목 기준, 대략적인 분류이며 100% 정확하지 않을 수 있음)
CATEGORY_KEYWORDS = {
    "음악방송": [
        "엠카운트다운", "M COUNTDOWN", "뮤직뱅크", "Music Bank", "인기가요", "inkigayo",
        "음악중심", "쇼! 음악중심", "엠카", "Show Champion", "쇼챔피언",
        "MusicCore", "Show! MusicCore", "음악방송",
    ],
    "MV": ["M/V", "MV", "뮤직비디오", "Official MV"],
    "Live": ["LIVE", "라이브", "Live Clip"],
    "Shorts": ["Shorts", "쇼츠", "#Shorts"],
}


# ── 뉴스 RSS ────────────────────────────────────────────────────
NEWS_RSS_FEEDS = [
    {
        "name": "구글 뉴스 - 리센느",
        "url": "https://news.google.com/rss/search?q=%EB%A6%AC%EC%84%BC%EB%8A%90&hl=ko&gl=KR&ceid=KR:ko",
    },
    {
        "name": "구글 뉴스 - RESCENE",
        "url": "https://news.google.com/rss/search?q=RESCENE+%EA%B0%80%EC%88%98&hl=ko&gl=KR&ceid=KR:ko",
    },
]

# ── 인스타그램 (자동 수집 대신 수동 확인용 링크만) ──────────────────
INSTAGRAM_LINKS = [
    {"name": "RESCENE 공식 인스타그램", "url": "https://www.instagram.com/rescene_official/"},
]

# ── 차트 추적 ───────────────────────────────────────────────────
# 아티스트/곡 텍스트에 이 키워드 중 하나라도 포함되면 "우리 그룹 곡"으로 인식합니다.
CHART_KEYWORDS = ["리센느", "RESCENE"]

# 공개 웹페이지(로그인 불필요)만 대상으로 합니다. 개인 사용 목적의 저빈도 조회이며,
# 재배포/상업적 이용이 아닙니다. 사이트 구조가 바뀌면 파싱이 깨질 수 있습니다.
CHART_SOURCES = {
    "melon": "https://www.melon.com/chart/index.htm",
    "genie": "https://www.genie.co.kr/chart/top200",
    "bugs": "https://music.bugs.co.kr/chart",
}

# ── 스케줄 (수동 관리) ───────────────────────────────────────────
# Mnet Plus 등 공식 스케줄은 인증 없이 안정적으로 자동 수집하기 어려워
# 우선 수동 입력 방식으로 시작합니다. 새 일정이 뜨면 여기에 추가해주세요.
# date는 'YYYY-MM-DD' 형식, type은 자유롭게 (방송/라디오/행사/팬사인회/공연 등)
SCHEDULE_ITEMS = [
    # {"date": "2026-07-31", "type": "행사", "title": "롯데 자이언츠 시구 (미나미)", "note": "사직구장, 삼성전"},
    # {"date": "2026-08-02", "type": "공연", "title": "보령머드축제", "note": ""},
]

# ── 배포 정보 ────────────────────────────────────────────────
# GitHub Pages로 배포할 때 실제 주소로 바꿔주세요 (예: https://아이디.github.io/저장소명/)
SITE_URL = "https://zenosid.github.io/rescene-tracker/"

# 카페 등에 안내할 운영자 연락처 (문의/삭제 요청용). 원하시는 값으로 바꿔주세요.
OPERATOR_CONTACT = "네이버 카페 '리시안셔스' 쪽지"

# GitHub Actions가 몇 분마다 자동 갱신하는지 (표시용 텍스트와 워크플로 cron이
# 실제로 일치하도록 .github/workflows/refresh.yml의 cron도 함께 맞춰주세요)
REFRESH_INTERVAL_MINUTES = 30

# ── 저장소 ──────────────────────────────────────────────────────
DB_PATH = "rescene_tracker.db"
