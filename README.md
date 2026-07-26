# RESCENE(리센느) 덕질 트래커 v4 — 배포용

오로라 그라데이션 테마의 정적 웹페이지. **로컬 개인용**과 **GitHub Pages 배포용**을
동시에 지원합니다. API 키 없이 무료 소스(RSS, 공개 차트 페이지)만 사용합니다.

## 신규 기능 (배포용)

- **⭐ 즐겨찾기**: 각 항목 카드의 ☆ 버튼으로 즐겨찾기. 브라우저 localStorage에
  저장되어 방문자 각자의 기기에만 남고, 다른 사람과 공유되지 않습니다.
- **📤 공유하기**: 상단 공유 버튼(사이트 전체) + 각 카드의 공유 버튼(개별 항목).
  모바일에서는 기기 공유 시트가, 데스크톱에서는 링크 복사가 뜹니다. 카카오톡 등에
  링크를 붙여넣으면 og 메타태그 덕분에 미리보기 카드가 자동으로 뜹니다.
- **ℹ️ 안내 탭**: 비공식·비영리 안내, 데이터 출처, 문의/삭제 요청 연락처, 자동
  갱신 주기를 명시 — 카페 등에 공식 배포할 때 필요한 최소한의 고지입니다.
- **🤖 자동 갱신(GitHub Actions)**: 배포 후에는 방문자 브라우저에서 수집을 실행할
  수 없으므로, `.github/workflows/refresh.yml`이 3시간마다 자동으로 수집·차트조회·
  스케줄추정을 실행하고 결과를 저장소에 커밋합니다. (로컬에서 쓰던 "🔄 새로고침"
  버튼은 localhost에서 실행할 때만 보이고, 배포 후 방문자에게는 보이지 않습니다.)

## 1. 설치 (로컬 테스트용)

```bash
cd rescene_tracker
pip install -r requirements.txt
```

## 2. 로컬에서 먼저 확인하기

**`refresh_and_open.bat` 더블클릭** — 수집 → 차트조회 → 로컬 서버 실행 →
브라우저 자동 오픈까지 한 번에 됩니다. 로컬에서는 화면의 "🔄 새로고침" 버튼도
그대로 사용 가능합니다.

## 3. GitHub Pages로 배포하기

1. GitHub에 새 저장소를 만들고 (예: `rescene-tracker`), 이 폴더 전체를 push합니다.
   ```bash
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/본인아이디/rescene-tracker.git
   git push -u origin main
   ```
2. 저장소 **Settings → Pages**에서:
   - Source: `Deploy from a branch`
   - Branch: `main`, 폴더: `/site`
   - Save
3. 몇 분 후 `https://본인아이디.github.io/rescene-tracker/`에서 사이트가 뜹니다.
4. `config.py`의 `SITE_URL`을 실제 주소로 바꾸고, `site/index.html`의
   `og:image`/`twitter:image` 두 줄에 있는 `your-github-id`도 실제 아이디로
   바꿔서 다시 push해주세요 (카카오톡 공유 카드가 정상적으로 뜨려면 필요합니다).
5. 저장소 **Settings → Actions → General**에서 "Workflow permissions"을
   **Read and write permissions**로 설정해주세요 (자동 커밋을 위해 필요합니다).

이후로는 `.github/workflows/refresh.yml`이 자동으로 3시간마다 데이터를 갱신하고
커밋합니다. Actions 탭에서 수동으로 "Run workflow"를 눌러 즉시 갱신할 수도 있습니다.

## 4. 화면 구성

- **🗂️ 아카이브**: 날짜별로 묶은 유튜브(공식/콜라보)·뉴스. 소스·멤버별 필터,
  각 카드에 즐겨찾기·공유 버튼.
- **📊 차트**: 멜론·지니·벅스 실시간 순위.
- **📅 스케줄**: 공식 등록 일정 + 뉴스 기반 자동 추정 일정(`추정` 배지).
- **⭐ 즐겨찾기**: 이 브라우저에서 즐겨찾기한 항목만 모아보기.
- **ℹ️ 안내**: 비공식 고지, 데이터 출처, 문의 연락처.

## 5. 폴더 구조

```
rescene_tracker/
├── .github/workflows/refresh.yml  # 자동 갱신 (GitHub Actions)
├── config.py                       # 채널/키워드/스케줄/배포 설정
├── db.py                            # SQLite 저장소
├── collector.py                     # 유튜브(공식·콜라보·검색발견)·뉴스 수집
├── chart_tracker.py                 # 차트 조회
├── classify.py                       # 멤버/카테고리 분류
├── schedule_extractor.py             # 뉴스 → 일정 후보 추출
├── build_site_data.py               # DB → site/data.js 변환
├── local_server.py                   # (로컬 전용) 정적 서빙 + 새로고침 API
├── refresh_and_open.bat             # (로컬 전용) 실행 버튼
├── rescene_tracker.db               # (자동 생성/갱신) 데이터 저장소
└── site/
    ├── index.html                   # 화면
    ├── app.js                        # 렌더링 로직
    ├── data.js                       # (자동 생성) 화면에 뿌려질 데이터
    └── og-image.png                  # 공유 미리보기 카드 이미지
```

## 6. 커스터마이징 (`config.py`)

- `YOUTUBE_CHANNELS` — 공식/준공식 채널 (전체 영상 수집)
- `COLLAB_CHANNELS` — 반드시 챙기고 싶은 콜라보 채널 (조회수 상관없이 항상 수집)
- `SEARCH_QUERIES` / `SEARCH_MIN_VIEWS` — 채널을 몰라도 "리센느" 검색 결과 중 조회수
  기준(기본 10만 회) 이상인 영상을 자동으로 찾아서 수집 (채널 등록 불필요)
- `MEMBER_KEYWORDS` — 멤버별 필터링 키워드
- `CATEGORY_KEYWORDS` — 음악방송/MV/Live 등 자동 분류 키워드
- `SCHEDULE_ITEMS` — 일정 수동 등록

콜라보 채널은 이제 두 가지 경로로 잡힙니다: ① `COLLAB_CHANNELS`에 등록한 채널은
조회수 상관없이 항상, ② 등록하지 않은 채널이라도 "리센느" 검색 결과에서 조회수
10만 이상이면 자동으로. 둘 다 공식 채널(YOUTUBE_CHANNELS)과 겹치는 영상은
채널 ID 기준으로 정확히 제외해서 중복 없이 수집됩니다.

## 7. 알아두어야 할 제약

- **차트**: 멜론·지니·벅스 공개 페이지를 저빈도 조회합니다. 사이트 구조가
  바뀌면 파싱이 깨질 수 있습니다.
- **인스타그램/X**: 자동 수집 대상에서 제외되어 있습니다 (API 제약/비용 문제).
- **스케줄**: 뉴스 기사에서 날짜+키워드를 감지하는 방식이라 100% 정확하지 않습니다.
  (예: "31일"만 있고 월 표기가 없으면 이번 달/다음 달로 추정) 그래서 자동 감지된
  항목은 전부 `추정` 배지가 붙고, 확실한 일정은 `config.py`의 `SCHEDULE_ITEMS`에
  직접 등록하시는 걸 권장합니다.
- **즐겨찾기**: 브라우저별로 따로 저장됩니다 (localStorage). 카페 회원 전체가
  공유하는 즐겨찾기가 아니라, 각자 자기 브라우저에서만 보이는 개인 북마크입니다.
- **차트/영상 검색 스크래핑**: 개인·비영리 사용을 전제로 저빈도(3시간 간격)로
  조회하도록 설계되어 있습니다. 방문자가 많아져도 스크래핑 빈도 자체는 늘지
  않습니다(방문자 브라우저가 아니라 GitHub Actions가 조회하기 때문).
