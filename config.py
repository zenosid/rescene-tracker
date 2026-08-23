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
    {"name": "SBS 인기가요", "channel_id": "UCS_hnpJLQTvBkqALgapi_4g"},
    {"name": "더쇼", "channel_id": "UCoRXPcv8XK5fAplLbk9PTww"},
    {"name": "음악중심", "channel_id": "UCe52oeb7Xv_KaJsEzcKXJJg"},
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


# ── 뉴스 RSS (구글) ─────────────────────────────────────────────
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

# ── 뉴스 (네이버, 공식 검색 API 필요) ─────────────────────────────
# 네이버 개발자센터(developers.naver.com)에서 앱 등록 후 Client ID/Secret 발급.
# 보안을 위해 이 파일에 직접 적지 말고 환경변수로 설정해주세요:
#   로컬:  $env:NAVER_CLIENT_ID="...", $env:NAVER_CLIENT_SECRET="..." (PowerShell)
#   배포:  저장소 Settings → Secrets and variables → Actions에 각각 등록
# 키가 없으면 이 기능은 조용히 건너뜁니다 (구글 뉴스 수집엔 영향 없음).
NAVER_NEWS_QUERIES = ["리센느", "RESCENE"]
NAVER_NEWS_MAX_RESULTS = 20  # 검색어당 최대 몇 건

# 네이버 카페글/블로그 검색도 같은 Client ID/Secret으로 됩니다 (별도 키 불필요).
# 팬카페·개인 블로그에 올라오는 콜라보/후기 소식은 뉴스로는 안 잡히는 경우가 많아서
# 추가한 소스입니다. (예: 브랜드 콜라보 이벤트를 다녀온 블로그 후기 등)
NAVER_CAFE_QUERIES = ["리센느", "RESCENE"]
NAVER_CAFE_MAX_RESULTS = 20
NAVER_BLOG_QUERIES = ["리센느", "RESCENE"]
NAVER_BLOG_MAX_RESULTS = 20

# ── 링크 모음 ────────────────────────────────────────────────
# 카페 공지·팬튜브 채널·공식 계정 등을 카테고리별로 정리해서 "🔗 링크" 탭에 보여줍니다.
# 얼마든지 카테고리/항목을 추가하셔도 됩니다.
LINK_COLLECTIONS = [
    {
        "category": "공식 계정",
        "items": [
            {"name": "RESCENE 공식 인스타그램", "url": "https://www.instagram.com/rescene_official/"},
            {"name": "RESCENE 공식 유튜브", "url": "https://www.youtube.com/channel/UCtKtCiaWRz-d3EZn2xd1mdA"},
            {"name": "RESCENE 공식 틱톡", "url": "https://www.tiktok.com/@rescene_official"},
            {"name": "RESCENE 공식 X(트위터)", "url": "https://x.com/RESCENEofficial?s=20"},
            {"name": "RESCENE 공식 멤버 X(트위터)", "url": "https://x.com/RESCENE_twt?s=20"},
            {"name": "RESCENE 공식 악플 신고", "url": "https://themuze.kr/protect"},
            # {"name": "RESCENE 공식 팬카페", "url": "https://cafe.naver.com/..."},
        ],
    },
    {
        "category": "커뮤니티",
        "items": [
            {"name": "네이버 팬카페 '리시안셔스'", "url": "https://cafe.naver.com/re5cene"},
            {"name": "이것도봐주마협회", "url": "https://bwajuma.club/"},
            {"name": "리센느 갤러리", "url": "https://gall.dcinside.com/mgallery/board/lists/?id=rescene1"},
        ],
    },
    {
        "category": "팬튜브",
        "items": [
            {"name": "르센느 아니고 리센느", "url": "https://youtube.com/channel/UCfd9mp2QKKprT1Iwt_2Jhng?si=zTtCEXDcSt2S7gGO"},
            {"name": "리센느서치P", "url": "https://youtube.com/channel/UCkQ_VWRV5xw4HJOQqaucIHg?si=TSkbFCEMHNr7lRgq"},
        ],
    },
    {
        "category": "기타",
        "items": [
            {"name": "리센느 영상 모음", "url": "https://adam-yam.github.io/SCENE-FLIX/?tab=allvideos"},
            {"name": "리센느 얼굴 맞추기", "url": "https://rescenehertz.github.io/rescene-face-game/"},
            {"name": "메이즈러너", "url": "https://twilight-dream-ed96.sparkeredm.workers.dev/"},
        ],
    },
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

# kworb.net 국가별 차트에서 가져올 국가 코드 (플랫폼별로 지원 국가가 다를 수 있음)
KWORB_SPOTIFY_COUNTRIES = ["kr", "us", "jp"]
KWORB_SHAZAM_COUNTRIES = ["kr", "us", "jp"]
KWORB_YOUTUBE_COUNTRIES = ["kr", "us", "jp"]

# ── 전체 곡 목록 (차트 테이블 기준 행) ──────────────────────────
# 차트에 현재 없는 곡도 "-"로 표시되도록, 발매된 곡 전체를 기준으로 둡니다.
# 새 곡이 나오면 여기에 추가해주세요. (위키백과/나무위키 기준으로 정리, 2026-07 기준)
RESCENE_ALL_SONGS = [
    "YoYo",       # 2024 선공개곡
    "UhUh",        # 2024 데뷔곡
    "LOVE ATTACK",  # 2024 1st 미니앨범 SCENEDROME 타이틀
    "Pinball",       # 2024 1st 미니앨범 SCENEDROME 타이틀
    "Glow Up",        # 2025 2nd 미니앨범 타이틀
    "Heart Drop",      # 2025 3rd 미니앨범 lip bomb 타이틀
    "Bloom",            # 2025 3rd 미니앨범 lip bomb 타이틀
    "Pretty Girl",        # 2026 리메이크 싱글
    "Deja Vu",             # 발매곡
    "Runaway",              # 2026 발매곡
    "Busy Boy",              # 2026 발매곡
    "밤밤밤",                  # OST 참여곡
    "고백주파수",                # OST 참여곡
    "Higher",                    # OST 참여곡
    "Dearest",                    # 발매곡
]

# 뉴스 기사 제목에 영문 대신 한글 발음으로 곡명이 쓰이는 경우가 많아서
# (예: "러브 어택" = LOVE ATTACK) 트로피 등에서 곡명을 정확히 매칭하기 위한 별칭
SONG_ALIASES = {
    "LOVE ATTACK": ["러브 어택", "러브어택"],
    "Pretty Girl": ["프리티 걸", "프리티걸"],
    "Deja Vu": ["데자뷰", "데자 뷰"],
    "Runaway": ["런어웨이"],
    "Pinball": ["핀볼"],
    "Busy Boy": ["비지 보이", "비지보이"],
    "Glow Up": ["글로우 업", "글로우업"],
    "Bloom": ["블룸"],
}

# ── 팬 반응 (유튜브 댓글, 공식 API 필요) ──────────────────────────
# YouTube Data API v3 키가 필요합니다 (무료, Google Cloud Console에서 발급).
# 보안을 위해 이 파일에 직접 적지 말고 환경변수로 설정해주세요:
#   로컬:  $env:YOUTUBE_API_KEY="여기에_키"  (PowerShell)
#   배포:  저장소 Settings → Secrets and variables → Actions → New repository secret
#          이름: YOUTUBE_API_KEY
# 키가 없으면 이 기능은 조용히 건너뜁니다 (다른 기능엔 영향 없음).
YOUTUBE_COMMENTS_MAX_VIDEOS = 15  # 최근 영상 몇 개까지 댓글을 확인할지
YOUTUBE_COMMENTS_PER_VIDEO = 15   # 영상당 댓글 몇 개까지 가져올지 (인기순)

# ── 스케줄 (수동 관리, 최우선 신뢰) ──────────────────────────────
# 자동 수집(공식/추정)보다 우선하고 싶은 확실한 정보가 있으면 여기에 직접 추가.
# date는 'YYYY-MM-DD' 형식, type은 자유롭게 (방송/라디오/행사/팬사인회/공연 등)
SCHEDULE_ITEMS = [
    {"date": "2026-12-05", "type": "행사", "title": "AAA 2026 (1일차)", "note": "2026.12.05(토)~12.06(일) 진행"},
    {"date": "2026-12-06", "type": "행사", "title": "AAA 2026 (2일차)", "note": "2026.12.05(토)~12.06(일) 진행"},
]

# ── 트로피 (수동 등록, 최우선 신뢰) ──────────────────────────────
# 뉴스 자동 감지가 놓친 확실한 수상 기록은 여기에 직접 추가해주세요.
# date는 'YYYY-MM-DD' 형식. (아래 3건은 나무위키 RESCENE/수상 문서로 교차 확인함)
TROPHY_ITEMS = [
    {"date": "2026-07-14", "show": "더쇼", "song": "Pretty Girl", "note": "SBS Life '더쇼' 케이블 음악방송 첫 1위 (데뷔 841일만)"},
    {"date": "2026-07-25", "show": "음악중심", "song": "Pretty Girl", "note": "MBC '쇼! 음악중심' 첫 지상파 음악방송 1위 (데뷔 852일만)"},
    {"date": "2026-07-26", "show": "인기가요", "song": "LOVE ATTACK", "note": "SBS '인기가요' 1위 (발매 699일만의 역주행 1위)"},
]

# ── 공식 스케줄 (Mnet Plus, 자동 수집) ──────────────────────────
# https://artist.mnetplus.world/main/{환경}/{아티스트 슬러그}/schedule/{연도}/{월}
# 형태의 공식 아티스트 페이지에서 실제 방영된 일정 그대로를 가져옵니다.
# JS로 렌더링되는 페이지라 Playwright(브라우저 자동화)로 접근하며,
# 부하를 줄이기 위해 이 부분만 6시간마다(뉴스/차트보다 낮은 빈도) 갱신됩니다.
MNET_PLUS_ENV = "stg"
MNET_PLUS_ARTIST_SLUG = "rescene-official"
# 이번 달 포함해서 몇 달치를 미리 가져올지 (예: 6이면 이번 달 + 앞으로 6개월 = 총 7개월)
MNET_PLUS_MONTHS_AHEAD = 6

# ── 포토카드 발매 기록 (텍스트 정보만, 이미지 없음) ────────────────
# hallyusuperstore.com의 판매 목록을 참고해서 정리했습니다 (2026-08 기준,
# 최신 30건). 실제 소장 여부와 무관하게 "이런 포토카드가 나왔다"는 발매
# 기록입니다. type: "방송"(음악방송 출연 기념) / "팬사인회" / "기타"
PHOTOCARD_RELEASES = [
    {"date": "2026-08-05", "release_name": "LOVE ATTACK - Broadcast Photocard (Gyaru Ver.)", "type": "방송"},
    {"date": "2026-07-30", "release_name": "Pretty Girl - Broadcast Photocard", "type": "방송"},
    {"date": "2026-07-30", "release_name": "Dearest - Million Music Photocard Set (5종)", "type": "기타"},
    {"date": "2026-07-24", "release_name": "Lip bomb - Official Photocard (QR)", "type": "기타"},
    {"date": "2026-07-24", "release_name": "Runaway - Million Music 팬사인회 포토카드", "type": "팬사인회"},
    {"date": "2026-07-24", "release_name": "제나 - Pretty Girl 방송 포토카드", "type": "방송"},
    {"date": "2026-07-24", "release_name": "Lip bomb - 쇼케이스 입장 포토카드 + 스페셜 기프트", "type": "기타"},
    {"date": "2026-07-20", "release_name": "Lip bomb - 포토카드 세트 (5종)", "type": "기타"},
    {"date": "2026-07-20", "release_name": "메이 - Lip bomb 방송 포토카드", "type": "방송"},
    {"date": "2026-07-20", "release_name": "Pretty Girl - 2주차 방송 포토카드", "type": "방송"},
    {"date": "2026-07-20", "release_name": "Pretty Girl - 1주차 방송 포토카드", "type": "방송"},
    {"date": "2026-07-14", "release_name": "Pretty Girl - 방송 포토카드", "type": "방송"},
    {"date": "2026-07-14", "release_name": "메이 - 방송 포토카드", "type": "방송"},
    {"date": "2026-07-10", "release_name": "방송 포토카드", "type": "방송"},
    {"date": "2026-07-07", "release_name": "방송 포토카드", "type": "방송"},
    {"date": "2026-07-07", "release_name": "Runaway - Withmuu 팬사인회 포토카드 R2", "type": "팬사인회"},
    {"date": "2026-07-02", "release_name": "Runaway - Withmuu 팬사인회 포토카드", "type": "팬사인회"},
    {"date": "2026-07-02", "release_name": "Dearest - Million Music 팬사인회 포토카드 R2", "type": "팬사인회"},
    {"date": "2026-06-30", "release_name": "Lip bomb - Million Music 팬사인회 포토카드", "type": "팬사인회"},
    {"date": "2026-06-30", "release_name": "Dearest - Million Music 팬사인회 포토카드", "type": "팬사인회"},
    {"date": "2026-06-25", "release_name": "방송 유닛 포토카드", "type": "방송"},
    {"date": "2026-06-25", "release_name": "Lip bomb - 쇼케이스 포토카드", "type": "기타"},
    {"date": "2026-06-23", "release_name": "It's LIVE 방송 포토카드", "type": "방송"},
    {"date": "2026-06-23", "release_name": "Lip bomb - 방송 포토카드", "type": "방송"},
    {"date": "2025-12-29", "release_name": "Dearest - ITTA 팬사인회 포토카드 (QR Ver.)", "type": "팬사인회"},
    {"date": "2025-12-29", "release_name": "Dearest - Who's Fan 팬사인회 포토카드 (QR Ver.)", "type": "팬사인회"},
    {"date": "2025-12-26", "release_name": "Lip bomb - 방송 미니팬미팅 포토카드", "type": "팬사인회"},
    {"date": "2025-12-17", "release_name": "Re:Scene - 팬사인회 앨범 컷페이지", "type": "팬사인회"},
    {"date": "2025-12-16", "release_name": "SCENEDROME - 팬사인회 앨범 컷페이지", "type": "팬사인회"},
]
# 참고: hallyusuperstore.com/collections/rescene 기준 130개 상품 중 최신 30건만
# 반영했습니다. 나머지 페이지도 원하시면 이어서 채워드릴 수 있습니다.

# ── 배포 정보 ────────────────────────────────────────────────
# GitHub Pages로 배포할 때 실제 주소로 바꿔주세요 (예: https://아이디.github.io/저장소명/)
SITE_URL = "https://zenosid.github.io/rescene-tracker/"

# 카페 등에 안내할 운영자 연락처 (문의/삭제 요청용). 원하시는 값으로 바꿔주세요.
OPERATOR_CONTACT = "네이버 카페 '리시안셔스' '첸드' 쪽지"

# GitHub Actions가 몇 분마다 자동 갱신하는지 (표시용 텍스트와 워크플로 cron이
# 실제로 일치하도록 .github/workflows/refresh.yml의 cron도 함께 맞춰주세요)
REFRESH_INTERVAL_MINUTES = 30

# ── 기념일 (D-day 카운트다운) ────────────────────────────────
# 데뷔일은 공식 확인됨(2024.03.26, 여러 소스 일치). 멤버 생일은 정확한 날짜를
# 직접 채워주세요 ("MM-DD" 형식, 연도 없이). 비워두면 그 멤버는 그냥 안 뜹니다.
DEBUT_DATE = "2024-03-26"

# ── 아카이브 화면 표시 개수 ──────────────────────────────────
# DB에는 수집된 모든 항목이 계속 쌓이지만(삭제 안 됨), 화면에는 최근 N건까지만
# 보여줍니다. 요즘 수집량이 많아서 500건이면 며칠 치밖에 안 보일 수 있어서
# 넉넉하게 늘려뒀습니다. 필요하면 더 키우셔도 됩니다.
# ── 아카이브 화면 표시 개수 ──────────────────────────────────
# None이면 무제한(전체 다 보여줌). DB에는 어차피 다 쌓여있고, 이건 화면에
# 몇 건까지 보여줄지만 정하는 값입니다. 데이터가 아주 많이 늘어나면
# data.js 파일 용량이 커져서 페이지 로딩이 느려질 수 있으니, 그럴 땐
# 숫자로 다시 제한하시면 됩니다 (예: 5000).
ARCHIVE_DISPLAY_LIMIT = None
MEMBER_BIRTHDAYS = {
    "원이": "05-25",
    "리브": "10-11",
    "미나미": "11-29",
    "메이": "08-19",
    "제나": "11-27",
}

# ── 라디오 문자 신청 채널 ────────────────────────────────────
# 채널(주파수) 단위 문자 신청 번호입니다 (프로그램마다 다른 게 아니라
# 방송사/채널 전체가 공용으로 씀). 사연쓰기 탭에서 채널을 고르면
# 문자 앱이 번호+내용 채워진 상태로 열리고, 실제 전송은 직접 누르셔야 합니다.
RADIO_CHANNELS = [
    {"broadcaster": "KBS", "name": "쿨FM (Happy/Cool)", "sms_number": "8910"},
    {"broadcaster": "KBS", "name": "해피FM", "sms_number": "1061"},
    {"broadcaster": "KBS", "name": "클래식FM", "sms_number": "9310"},
    {"broadcaster": "MBC", "name": "FM4U", "sms_number": "8000"},
    {"broadcaster": "MBC", "name": "표준FM", "sms_number": "8001"},
    {"broadcaster": "SBS", "name": "파워FM", "sms_number": "1077"},
    {"broadcaster": "SBS", "name": "러브FM", "sms_number": "1035"},
    {"broadcaster": "EBS", "name": "FM", "sms_number": "1045"},
]

# ── 채널별 시간대 편성표 (DJ 자동 감지용) ────────────────────────
# 사연쓰기 탭에서 채널을 누르면, 지금 시각 기준으로 이 표에서 DJ를 찾아
# 인사말에 자동으로 넣어줍니다. 아직 KBS 쿨FM(평일)만 채워뒀고, 나머지
# 채널/주말 시간표는 확인되는 대로 추가하면 됩니다. days는
# "mon","tue","wed","thu","fri","sat","sun" 조합.
# (나무위키 KBS 2FM 문서 기준으로 정리, 2026-07 기준 - 개편되면 바뀔 수 있음)
RADIO_SCHEDULE = {
    "8910": [  # KBS 쿨FM
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "05:00", "end": "07:00", "dj": "허유원"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "07:00", "end": "09:00", "dj": "조정식"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "11:00", "dj": "이현우"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "11:00", "end": "12:00", "dj": "박명수"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "12:00", "end": "14:00", "dj": "폴킴"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "14:00", "end": "16:00", "dj": "가비"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "16:00", "end": "18:00", "dj": "윤정수, 남창희"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "18:00", "end": "20:00", "dj": "이금희"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "20:00", "end": "22:00", "dj": "효정"},
        {"days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], "start": "22:00", "end": "24:00", "dj": "한해"},
    ],
    "8000": [  # MBC FM4U
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "07:00", "end": "09:00", "dj": "테이"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "11:00", "dj": "윤상"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "11:00", "end": "12:00", "dj": "이문세"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "12:00", "end": "14:00", "dj": "김신영"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "14:00", "end": "16:00", "dj": "안영미"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "16:00", "end": "18:00", "dj": "이상순"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "18:00", "end": "20:00", "dj": "배철수"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "20:00", "end": "22:00", "dj": "김이나"},
        {"days": ["mon", "tue", "wed"], "start": "22:00", "end": "24:00", "dj": "친한친구 방송반"},
        {"days": ["thu", "fri"], "start": "22:00", "end": "24:00", "dj": "IDOL RADIO"},
    ],
    "1077": [  # SBS 파워FM
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "07:00", "end": "09:00", "dj": "김영철"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "11:00", "dj": "봉태규"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "11:00", "end": "12:00", "dj": "박하선"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "12:00", "end": "14:00", "dj": "주현영"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "14:00", "end": "16:00", "dj": "정찬우, 김태균"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "16:00", "end": "18:00", "dj": "황제성"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "18:00", "end": "20:00", "dj": "박소현"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "20:00", "end": "22:00", "dj": "웬디"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "22:00", "end": "23:00", "dj": "배성재"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "23:00", "end": "01:00", "dj": "딘딘"},
    ],
    "1035": [  # SBS 러브FM
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "11:00", "dj": "이숙영"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "12:00", "end": "14:00", "dj": "유민상"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "14:00", "end": "16:00", "dj": "정엽"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "18:00", "end": "20:00", "dj": "김창완"},
        {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "20:00", "end": "22:00", "dj": "김윤상"},
    ],
    "1045": [  # EBS FM - "경청"에 아이돌 게스트/신청곡 코너가 실제로 있어서 유용
        {"days": ["mon", "tue", "wed", "thu", "fri", "sat"], "start": "22:00", "end": "24:00", "dj": "경청 DJ"},
    ],
}

# ── 저장소 ──────────────────────────────────────────────────────
DB_PATH = "rescene_tracker.db"
