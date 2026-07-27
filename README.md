# RESCENE(리센느) 덕질 트래커 v4 — 배포용

오로라 그라데이션 테마의 정적 웹페이지. **로컬 개인용**과 **GitHub Pages 배포용**을
동시에 지원합니다. API 키 없이 무료 소스(RSS, 공개 차트 페이지)만 사용합니다.

## 신규 기능 (배포용)

- **⭐ 즐겨찾기**: 각 항목 카드의 ☆ 버튼으로 즐겨찾기. 브라우저 localStorage에
  저장되어 방문자 각자의 기기에만 남고, 다른 사람과 공유되지 않습니다.
- **📤 공유하기**: 상단 공유 버튼(사이트 전체) + 각 카드의 공유 버튼(개별 항목).
  모바일에서는 기기 공유 시트가, 데스크톱에서는 링크 복사가 뜹니다. 카카오톡 등에
  링크를 붙여넣으면 og 메타태그 덕분에 미리보기 카드가 자동으로 뜹니다.
- **🔗 링크 탭**: 공식 계정·커뮤니티·팬튜브 채널 등을 카테고리별로 정리한 링크 모음.
- **📊 차트 확장**: 멜론·지니·벅스에 더해 kworb.net(스포티파이가 공개한 데이터를
  미러링하는 공개 통계 사이트)을 통해 Spotify·YouTube·Shazam 한국 순위까지 총
  6개 플랫폼. 모든 플랫폼에 전 회차 대비 순위 변동(▲상승/▼하락/NEW신규) 표시.
- **📅 공식 스케줄(Mnet Plus)**: 이번 달 포함 앞으로 6개월치(설정 가능)를
  자동으로 가져와서 확정 일정으로 표시.
- **ℹ️ 안내 탭**: 비공식·비영리 안내, 데이터 출처, 문의/삭제 요청 연락처, 자동
  갱신 주기를 명시 — 카페 등에 공식 배포할 때 필요한 최소한의 고지입니다.
- **🤖 자동 갱신(GitHub Actions, 2개 워크플로)**:
  - `refresh.yml` — 30분마다 유튜브·뉴스·차트·뉴스기반 일정추정을 갱신
  - `official_schedule.yml` — 6시간마다 Mnet Plus 공식 스케줄을 갱신 (Playwright
    설치 시간이 있어서 더 낮은 빈도로 분리)

  배포 후에는 방문자 브라우저에서 수집을 실행할 수 없어서 이 두 워크플로가
  대신 갱신합니다. (로컬에서 쓰던 "🔄 새로고침" 버튼은 localhost에서 실행할
  때만 보이고, 배포 후 방문자에게는 보이지 않습니다.)

## 1. 설치 (로컬 테스트용)

```bash
cd rescene_tracker
pip install -r requirements.txt
python -m playwright install chromium
```

(마지막 줄은 공식 스케줄(Mnet Plus) 수집에만 필요합니다. 아카이브·차트만
쓰실 거면 생략해도 됩니다.)

## 2. 로컬에서 먼저 확인하기

**`refresh_and_open.bat` 더블클릭** — 수집 → 차트조회 → 로컬 서버 실행 →
브라우저 자동 오픈까지 한 번에 됩니다. 로컬에서는 화면의 "🔄 새로고침" 버튼도
그대로 사용 가능합니다.

## 3. GitHub Pages로 배포하기

`zenosid/rescene-tracker` 저장소 기준으로 이미 `config.py`의 `SITE_URL`과
`docs/index.html`의 `og:image` 주소를 채워뒀습니다. 저장소 이름을 다르게
만드셨다면 이 두 곳만 실제 주소로 바꿔서 다시 push해주세요.

1. GitHub에 새 저장소를 만들고, 이 폴더 전체를 push합니다. (이미 하셨다면 생략)
   ```bash
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/zenosid/rescene-tracker.git
   git push -u origin main
   ```
2. 저장소 **Settings → Pages**에서:
   - Source: `Deploy from a branch`
   - Branch: `main`, 폴더: `/docs` (⚠️ GitHub Pages는 `/ (root)`와 `/docs`만
     선택할 수 있어서 폴더명을 `docs`로 맞춰뒀습니다)
   - Save
3. 몇 분 후 `https://zenosid.github.io/rescene-tracker/`에서 사이트가 뜹니다.
4. 저장소 **Settings → Actions → General**에서 "Workflow permissions"을
   **Read and write permissions**로 설정해주세요 (자동 커밋을 위해 필요합니다).

이후로는 `.github/workflows/refresh.yml`이 자동으로 30분마다 데이터를 갱신하고
커밋합니다. Actions 탭에서 수동으로 "Run workflow"를 눌러 즉시 갱신할 수도 있습니다.


## 4. 화면 구성

- **🗂️ 아카이브**: 날짜별로 묶은 유튜브(공식/콜라보)·뉴스. 소스·멤버별 필터,
  각 카드에 즐겨찾기·공유 버튼.
- **📊 차트**: 멜론·지니·벅스·Spotify(KR)·YouTube(KR)·Shazam(KR) 실시간 순위 +
  전 회차 대비 변동(▲▼NEW).
- **📅 스케줄**: ① Mnet Plus 공식 아티스트 페이지에서 자동 수집한 확정 일정
  (배지 없음 = 공식), ② 수동 등록한 확실한 일정, ③ 뉴스 기사에서 자동 추정한
  일정(`추정` 배지). 같은 날짜에 공식 일정이 이미 있으면 불확실한 추정 항목은
  자동으로 숨겨집니다.
- **⭐ 즐겨찾기**: 이 브라우저에서 즐겨찾기한 항목만 모아보기.
- **🔗 링크**: 공식 계정·커뮤니티·팬튜브 채널 등 카테고리별 링크 모음.
- **ℹ️ 안내**: 비공식 고지, 데이터 출처, 문의 연락처.

## 5. 폴더 구조

```
rescene_tracker/
├── .github/workflows/
│   ├── refresh.yml                  # 자동 갱신 (뉴스·차트·유튜브, 30분마다)
│   └── official_schedule.yml        # 공식 스케줄 자동 갱신 (Mnet Plus, 6시간마다)
├── config.py                        # 채널/키워드/스케줄/링크/배포 설정
├── db.py                             # SQLite 저장소
├── collector.py                      # 유튜브(공식·콜라보·검색발견)·뉴스 수집
├── chart_tracker.py                  # 차트 조회
├── classify.py                        # 멤버/카테고리 분류
├── schedule_extractor.py              # 뉴스 → 일정 후보 추출 (추정)
├── official_schedule.py               # Mnet Plus 공식 스케줄 수집 (Playwright)
├── kst.py                              # UTC → KST 시간대 변환 유틸
├── build_site_data.py                 # DB → docs/data.js 변환
├── local_server.py                     # (로컬 전용) 정적 서빙 + 새로고침 API
├── refresh_and_open.bat               # (로컬 전용) 실행 버튼
├── rescene_tracker.db                 # (자동 생성/갱신) 데이터 저장소
└── docs/
    ├── index.html                     # 화면
    ├── app.js                          # 렌더링 로직
    ├── data.js                         # (자동 생성) 화면에 뿌려질 데이터
    └── og-image.png                    # 공유 미리보기 카드 이미지
```

## 6. 커스터마이징 (`config.py`)

- `YOUTUBE_CHANNELS` — 공식/준공식 채널 (전체 영상 수집)
- `COLLAB_CHANNELS` — 반드시 챙기고 싶은 콜라보 채널 (조회수 상관없이 항상 수집)
- `SEARCH_QUERIES` / `SEARCH_MIN_VIEWS` — 채널을 몰라도 "리센느" 검색 결과 중 조회수
  기준(기본 10만 회) 이상인 영상을 자동으로 찾아서 수집 (채널 등록 불필요)
- `MEMBER_KEYWORDS` — 멤버별 필터링 키워드
- `CATEGORY_KEYWORDS` — 음악방송/MV/Live 등 자동 분류 키워드
- `SCHEDULE_ITEMS` — 확실한 일정 수동 등록 (공식 자동 수집보다 더 신뢰)
- `MNET_PLUS_ARTIST_SLUG` — 공식 스케줄을 가져올 Mnet Plus 아티스트 페이지 슬러그
- `MNET_PLUS_MONTHS_AHEAD` — 이번 달 포함해서 앞으로 몇 개월치를 가져올지 (기본 6개월 뒤까지, 총 7개월)
- `LINK_COLLECTIONS` — 🔗 링크 탭에 표시할 카테고리별 링크 모음 (공식 계정/커뮤니티/팬튜브 등)

콜라보 채널은 이제 두 가지 경로로 잡힙니다: ① `COLLAB_CHANNELS`에 등록한 채널은
조회수 상관없이 항상, ② 등록하지 않은 채널이라도 "리센느" 검색 결과에서 조회수
10만 이상이면 자동으로. 둘 다 공식 채널(YOUTUBE_CHANNELS)과 겹치는 영상은
채널 ID 기준으로 정확히 제외해서 중복 없이 수집됩니다.

## 7. 알아두어야 할 제약

- **차트**: 멜론·지니·벅스 공개 페이지를 저빈도 조회합니다. 사이트 구조가
  바뀌면 파싱이 깨질 수 있습니다.
- **인스타그램/X**: 자동 수집 대상에서 제외되어 있습니다 (API 제약/비용 문제).
- **스케줄(자동 추정)**: 뉴스 기사에서 날짜+키워드를 감지하는 방식이라 100% 정확하지
  않습니다. (예: "31일"만 있고 월 표기가 없으면 이번 달/다음 달로 추정) 그래서
  뉴스 기반 자동 감지 항목만 `추정` 배지가 붙고, 확실한 일정은 `config.py`의
  `SCHEDULE_ITEMS`에 직접 등록하시는 걸 권장합니다.
- **스케줄(공식)**: Mnet Plus 공식 아티스트 페이지(`artist.mnetplus.world`)에서
  Playwright(브라우저 자동화)로 가져옵니다. 6시간마다 별도 워크플로
  (`.github/workflows/official_schedule.yml`)로 갱신되며, 로컬에서 이 부분을
  테스트하려면 `python -m playwright install chromium`을 한 번 실행해야 합니다.
- **즐겨찾기**: 브라우저별로 따로 저장됩니다 (localStorage). 카페 회원 전체가
  공유하는 즐겨찾기가 아니라, 각자 자기 브라우저에서만 보이는 개인 북마크입니다.
- **차트/영상 검색 스크래핑**: 개인·비영리 사용을 전제로 저빈도(30분 간격)로
  조회하도록 설계되어 있습니다. 방문자가 많아져도 스크래핑 빈도 자체는 늘지
  않습니다(방문자 브라우저가 아니라 GitHub Actions가 조회하기 때문).
