// RESCENE Tracker — 렌더링 스크립트
// data.js에서 정의된 전역 SITE_DATA를 읽어서 화면을 그립니다.

const SOURCE_META = {
  youtube: { icon: "▶️", label: "공식 유튜브" },
  youtube_collab: { icon: "🤝", label: "콜라보" },
  news: { icon: "📰", label: "뉴스" },
  community: { icon: "💬", label: "카페/블로그" },
  x: { icon: "𝕏", label: "X" },
};

const MEMBER_COLORS = {
  "원이": "var(--aurora-pink)",
  "리브": "var(--aurora-violet)",
  "미나미": "var(--aurora-cyan)",
  "메이": "var(--aurora-mint)",
  "제나": "var(--aurora-amber)",
};

// 곡별 종합 테이블에 쓸 컬럼 (한국 기준 8개 플랫폼)
const CHART_TABLE_PLATFORMS = [
  { key: "melon", label: "MELON" },
  { key: "genie", label: "GENIE" },
  { key: "bugs", label: "BUGS" },
  { key: "flo", label: "FLO" },
  { key: "spotify_kr", label: "SPOTIFY" },
  { key: "shazam_kr", label: "SHAZAM" },
  { key: "youtube_kr", label: "YT MUSIC" },
  { key: "apple_music_kr", label: "APPLE MUSIC" },
];

// 해외(미국·일본)는 곡별 테이블 아래 작은 보조 섹션으로 따로 표시
const INTERNATIONAL_EXTRA_SERVICES = [
  { key: "spotify", label: "Spotify" },
  { key: "shazam", label: "Shazam" },
  { key: "youtube", label: "YouTube" },
  { key: "apple_music", label: "Apple Music" },
];
const INTERNATIONAL_EXTRA_COUNTRIES = [
  { code: "us", label: "US" },
  { code: "jp", label: "JP" },
];

const PLATFORM_LABELS = {
  melon: "멜론",
  genie: "지니",
  bugs: "벅스",
  flo: "FLO",
  spotify_kr: "Spotify (KR)",
  spotify_us: "Spotify (US)",
  spotify_jp: "Spotify (JP)",
  shazam_kr: "Shazam (KR)",
  shazam_us: "Shazam (US)",
  shazam_jp: "Shazam (JP)",
  youtube_kr: "YouTube (KR)",
  youtube_us: "YouTube (US)",
  youtube_jp: "YouTube (JP)",
  apple_music_kr: "Apple Music (KR)",
  apple_music_us: "Apple Music (US)",
  apple_music_jp: "Apple Music (JP)",
};
const FAVORITES_KEY = "rescene_tracker_favorites"; // localStorage 키 (이 브라우저 전용)
const REACTION_API_BASE = "https://rescene-reactions.zenosid1.workers.dev";
const REACTION_EMOJIS = ["👍", "🥹", "🔥", "😍"];

const CATEGORY_LIST = ["음악방송", "MV", "Live", "Shorts", "자체컨텐츠", "외부컨텐츠", "기타"];

// ── 상태 ──────────────────────────────────────────────────
const state = {
  sourceTab: "all", // 단일 선택: "all" | "youtube" | "youtube_collab" | "news"
  categoryTab: "all", // 단일 선택: "all" | "음악방송" | "MV" | ...
  yearTab: "all", // 단일 선택: "all" | "2026" | "2025" | ...
  members: new Set(), // 비어있으면 전체
  reactionSort: "likes", // "likes" | "recent"
  archiveSort: "newest", // "newest" | "oldest"
  archiveSearch: "", // 제목 텍스트 검색어
  archiveVisibleGroups: 30, // "더보기"로 늘어나는, 화면에 그릴 날짜 그룹 개수
};

// ── 즐겨찾기 (localStorage, 이 브라우저에만 저장) ───────────
function loadFavorites() {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch (e) {
    return new Set();
  }
}
function saveFavorites(set) {
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify([...set]));
  } catch (e) {
    // localStorage를 쓸 수 없는 환경(프라이빗 모드 등)이면 조용히 무시
  }
}
const favorites = loadFavorites();

function toggleFavorite(link) {
  if (favorites.has(link)) {
    favorites.delete(link);
  } else {
    favorites.add(link);
  }
  saveFavorites(favorites);
}

// ── 토스트 알림 ───────────────────────────────────────────
let toastTimer = null;
function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2200);
}

// ── 공유 헬퍼 ─────────────────────────────────────────────
async function shareLink(url, title) {
  if (navigator.share) {
    try {
      await navigator.share({ title: title || "RESCENE Tracker", url });
      return;
    } catch (e) {
      return; // 사용자가 공유 취소한 경우 등 - 조용히 무시
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    showToast("링크가 복사되었습니다 📋");
  } catch (e) {
    showToast("복사에 실패했습니다. 링크: " + url);
  }
}

// ── 탭 전환 ───────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("view-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "favorites") renderFavorites();
    if (btn.dataset.tab === "links") renderLinks();
    if (btn.dataset.tab === "reactions") renderReactions();
    if (btn.dataset.tab === "stats") renderStats();
  });
});

// ── 헤더: 생성 시각 / 공유 버튼 ────────────────────────────
document.getElementById("generatedAt").textContent =
  "최근 갱신: " + (SITE_DATA.generated_at || "-");

document.getElementById("shareBtn").addEventListener("click", () => {
  shareLink(location.href, "🩷 RESCENE TRACKER");
});

// 로컬에서 실행 중일 때만 새로고침 버튼 노출 (배포 후에는 방문자 브라우저에서
// 수집을 실행할 수 없으므로 GitHub Actions 자동 갱신에 맡깁니다)
if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
  document.getElementById("refreshBtn").style.display = "inline-block";
}

// ── 안내 탭: 연락처/갱신주기 채우기 ─────────────────────────
document.getElementById("operatorContact").textContent = SITE_DATA.operator_contact || "-";
document.getElementById("refreshIntervalText").textContent = SITE_DATA.refresh_interval_minutes
  ? `약 ${SITE_DATA.refresh_interval_minutes}분마다`
  : "비정기적";

// ── 필터 칩 렌더링 ────────────────────────────────────────
function buildSourceChips() {
  const wrap = document.getElementById("sourceChips");
  wrap.innerHTML = "";

  const options = [{ key: "all", icon: "🗂️", label: "전체" }].concat(
    Object.entries(SOURCE_META).map(([key, meta]) => ({ key, icon: meta.icon, label: meta.label }))
  );

  options.forEach(({ key, icon, label }) => {
    const tab = document.createElement("button");
    tab.className = "source-tab" + (state.sourceTab === key ? " active" : "");
    tab.dataset.chip = key;
    tab.textContent = icon + " " + label;
    tab.addEventListener("click", () => {
      state.sourceTab = key;
      state.archiveVisibleGroups = 30;
      buildSourceChips();
      renderArchive();
    });
    wrap.appendChild(tab);
  });
}

function buildMemberChips() {
  const wrap = document.getElementById("memberChips");
  wrap.innerHTML = "";
  Object.keys(MEMBER_COLORS).forEach((name) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (state.members.has(name) ? " on" : "");
    chip.dataset.member = name;
    if (state.members.has(name)) chip.style.background = MEMBER_COLORS[name];
    chip.textContent = name;
    chip.addEventListener("click", () => {
      if (state.members.has(name)) {
        state.members.delete(name);
      } else {
        state.members.add(name);
      }
      state.archiveVisibleGroups = 30;
      buildMemberChips();
      renderArchive();
    });
    wrap.appendChild(chip);
  });
}

function buildCategoryChips() {
  const wrap = document.getElementById("categoryChips");
  if (!wrap) return;
  wrap.innerHTML = "";

  const options = ["all", ...CATEGORY_LIST];
  options.forEach((cat) => {
    const tab = document.createElement("button");
    tab.className = "source-tab" + (state.categoryTab === cat ? " active" : "");
    tab.dataset.category = cat;
    tab.textContent = cat === "all" ? "🗂️ 전체" : cat;
    tab.addEventListener("click", () => {
      state.categoryTab = cat;
      state.archiveVisibleGroups = 30;
      buildCategoryChips();
      renderArchive();
    });
    wrap.appendChild(tab);
  });
}

function buildYearChips() {
  const wrap = document.getElementById("yearChips");
  if (!wrap) return;
  wrap.innerHTML = "";

  // 아카이브에 실제 있는 연도만 최신순으로 뽑아냄
  const years = [...new Set((SITE_DATA.archive || []).map((g) => g.date.slice(0, 4)))].sort(
    (a, b) => b.localeCompare(a)
  );

  const options = ["all", ...years];
  options.forEach((year) => {
    const tab = document.createElement("button");
    tab.className = "source-tab" + (state.yearTab === year ? " active" : "");
    tab.dataset.year = year;
    tab.textContent = year === "all" ? "🗂️ 전체" : year + "년";
    tab.addEventListener("click", () => {
      state.yearTab = year;
      state.archiveVisibleGroups = 30;
      buildYearChips();
      renderArchive();
    });
    wrap.appendChild(tab);
  });
}

// ── 아이템 카드 (아카이브·즐겨찾기 공용) ───────────────────
function itemPassesFilter(item) {
  if (state.sourceTab !== "all" && item.source_type !== state.sourceTab) return false;
  if (state.categoryTab !== "all" && item.category !== state.categoryTab) return false;
  if (state.members.size > 0) {
    const hasOverlap = item.members.some((m) => state.members.has(m));
    if (!hasOverlap) return false;
  }
  if (state.archiveSearch.trim()) {
    const query = state.archiveSearch.trim().toLowerCase();
    if (!item.title.toLowerCase().includes(query)) return false;
  }
  return true;
}

function memberBadgeHtml(members) {
  return members
    .filter((m) => m !== "전체")
    .map((m) => `<span class="badge member" style="background:${MEMBER_COLORS[m] || "#888"}">${m}</span>`)
    .join("");
}

function buildItemCard(item) {
  const meta = SOURCE_META[item.source_type] || { icon: "📄", label: item.source_type };
  const card = document.createElement("div");
  card.className = "card item-card";

  const isFav = favorites.has(item.link);
  const reactionId = encodeURIComponent(item.link);

  card.innerHTML = `
    <a class="item-top" href="${item.link}" target="_blank" rel="noopener noreferrer" style="text-decoration:none; color:inherit;">
      <span class="item-icon">${meta.icon}</span>
      <span class="item-title">${escapeHtml(item.title)}</span>
    </a>
    <div class="item-meta">
      <span class="badge category">${escapeHtml(item.category)}</span>
      ${memberBadgeHtml(item.members)}
      <span>${escapeHtml(item.source_name)}</span>
      ${item.time ? `<span>· ${item.time}</span>` : ""}
    </div>
    <div class="item-reactions">
      ${REACTION_EMOJIS.map(
        (emoji) => `
        <button class="reaction-btn" data-emoji="${emoji}" type="button">
          <span class="reaction-emoji">${emoji}</span><span class="reaction-count">·</span>
        </button>`
      ).join("")}
    </div>
    <div class="item-actions">
      <button class="item-action-btn fav-btn${isFav ? " favorited" : ""}" title="즐겨찾기" type="button">${isFav ? "★" : "☆"}</button>
      <button class="item-action-btn share-item-btn" title="공유" type="button">📤</button>
    </div>
  `;

  card.querySelector(".fav-btn").addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleFavorite(item.link);
    const nowFav = favorites.has(item.link);
    e.currentTarget.classList.toggle("favorited", nowFav);
    e.currentTarget.textContent = nowFav ? "★" : "☆";
    showToast(nowFav ? "즐겨찾기에 추가했어요 ⭐" : "즐겨찾기에서 제거했어요");
    if (document.getElementById("view-favorites").classList.contains("active")) {
      renderFavorites();
    }
  });

  card.querySelector(".share-item-btn").addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    shareLink(item.link, item.title);
  });

  setupReactionButtons(card, reactionId);

  return card;
}

// ── 반응(이모지) 버튼 - Cloudflare Worker + KV로 익명 카운트 저장 ──────
function setupReactionButtons(card, reactionId) {
  const buttons = card.querySelectorAll(".reaction-btn");

  // 이 브라우저에서 이미 누른 이모지는 표시만 해두고(서버도 하루 1회로 막지만,
  // 굳이 실패할 요청을 또 보내지 않도록 미리 비활성화)
  buttons.forEach((btn) => {
    const emoji = btn.dataset.emoji;
    const reactedKey = `rescene_reacted_${reactionId}_${emoji}`;
    if (localStorage.getItem(reactedKey)) {
      btn.classList.add("reacted");
    }
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (btn.classList.contains("reacted")) return;

      btn.disabled = true;
      try {
        const res = await fetch(`${REACTION_API_BASE}/react`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: reactionId, emoji }),
        });
        if (res.ok) {
          const data = await res.json();
          btn.querySelector(".reaction-count").textContent = data[emoji];
          btn.classList.add("reacted");
          try {
            localStorage.setItem(`rescene_reacted_${reactionId}_${emoji}`, "1");
          } catch (err) {
            // localStorage 사용 불가 환경이면 조용히 무시
          }
        }
      } catch (err) {
        // 네트워크 오류 등은 조용히 무시 (반응 기능은 부가 기능이라 실패해도 사이트 이용엔 지장 없음)
      }
      btn.disabled = false;
    });
  });

  // 카드가 만들어질 때 현재 카운트를 비동기로 가져와서 채워넣음
  fetch(`${REACTION_API_BASE}/counts?id=${reactionId}`)
    .then((res) => (res.ok ? res.json() : null))
    .then((counts) => {
      if (!counts) return;
      buttons.forEach((btn) => {
        const emoji = btn.dataset.emoji;
        btn.querySelector(".reaction-count").textContent = counts[emoji] || 0;
      });
    })
    .catch(() => {
      // 네트워크 오류 등은 조용히 무시
    });
}

// ── 아카이브 렌더링 ───────────────────────────────────────
function renderArchive() {
  const container = document.getElementById("archiveContent");
  container.innerHTML = "";

  // 검색창
  const searchBar = document.createElement("div");
  searchBar.className = "archive-search-bar";
  searchBar.innerHTML = `
    <input type="text" id="archiveSearchInput" placeholder="🔍 제목으로 검색..." value="${escapeHtml(state.archiveSearch)}" />
  `;
  container.appendChild(searchBar);
  searchBar.querySelector("input").addEventListener("input", (e) => {
    state.archiveSearch = e.target.value;
    state.archiveVisibleGroups = 30; // 검색어 바뀌면 페이지네이션 처음부터
    renderArchive();
    // 입력 중 포커스가 날아가지 않도록 다시 포커스 + 커서 위치 복원
    const input = document.getElementById("archiveSearchInput");
    input.focus();
    input.setSelectionRange(state.archiveSearch.length, state.archiveSearch.length);
  });

  // 정렬 토글 (최신순 기본 / 과거순)
  const sortBar = document.createElement("div");
  sortBar.className = "archive-sort-bar";
  sortBar.innerHTML = `
    <button class="source-tab${state.archiveSort === "newest" ? " active" : ""}" data-archive-sort="newest">🕒 최신순</button>
    <button class="source-tab${state.archiveSort === "oldest" ? " active" : ""}" data-archive-sort="oldest">📜 과거순</button>
  `;
  sortBar.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.archiveSort = btn.dataset.archiveSort;
      state.archiveVisibleGroups = 30;
      renderArchive();
    });
  });
  container.appendChild(sortBar);

  // SITE_DATA.archive는 항상 최신순으로 옴 - 과거순이면 그대로 뒤집으면 됨
  const orderedGroups =
    state.archiveSort === "oldest" ? [...SITE_DATA.archive].reverse() : SITE_DATA.archive;

  // 필터를 통과하는 그룹만 먼저 추려서, 그중 앞에서부터 N개(더보기 단위)만 실제로 그림
  // - 9000건 넘게 쌓인 상태라 한 번에 다 그리면 느려져서, 처음엔 일부만 그리고
  //   "더보기"를 눌러야 더 그리는 방식으로 부담을 줄임
  const matchingGroups = [];
  orderedGroups.forEach((group) => {
    if (state.yearTab !== "all" && group.date.slice(0, 4) !== state.yearTab) return;
    const visibleItems = group.items.filter(itemPassesFilter);
    if (visibleItems.length === 0) return;
    matchingGroups.push({ group, visibleItems });
  });

  const groupsToRender = matchingGroups.slice(0, state.archiveVisibleGroups);
  let totalShown = 0;
  let lastYear = null;

  groupsToRender.forEach(({ group, visibleItems }) => {
    totalShown += visibleItems.length;

    // 날짜(YYYY-MM-DD)의 앞 4자리로 연도 구분, 바뀔 때마다 큰 연도 헤더 삽입
    const year = group.date.slice(0, 4);
    if (year !== lastYear) {
      const yearHeading = document.createElement("div");
      yearHeading.className = "year-heading";
      yearHeading.textContent = year + "년";
      container.appendChild(yearHeading);
      lastYear = year;
    }

    const dateGroup = document.createElement("div");
    dateGroup.className = "date-group";

    const heading = document.createElement("div");
    heading.className = "date-heading";
    heading.innerHTML = `<h2>${group.date_display}</h2><div class="date-rule"></div>`;
    dateGroup.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "item-grid";
    visibleItems.forEach((item) => grid.appendChild(buildItemCard(item)));

    dateGroup.appendChild(grid);
    container.appendChild(dateGroup);
  });

  if (matchingGroups.length === 0) {
    container.innerHTML += `<div class="empty-state">조건에 맞는 항목이 없습니다.<br/>필터를 조정하거나 검색어를 바꿔보세요.</div>`;
    return;
  }

  if (matchingGroups.length > groupsToRender.length) {
    const moreBtn = document.createElement("button");
    moreBtn.className = "refresh-btn archive-more-btn";
    const remainingGroups = matchingGroups.length - groupsToRender.length;
    moreBtn.textContent = `더보기 (날짜 ${remainingGroups}개 더 있음)`;
    moreBtn.addEventListener("click", () => {
      state.archiveVisibleGroups += 30;
      renderArchive();
    });
    container.appendChild(moreBtn);
  }
}

// ── 즐겨찾기 탭 렌더링 ───────────────────────────────────────
function renderFavorites() {
  const container = document.getElementById("favoritesContent");
  container.innerHTML = "";

  if (favorites.size === 0) {
    container.innerHTML = `<div class="empty-state">아직 즐겨찾기한 항목이 없습니다.<br/>아카이브에서 ☆ 버튼을 눌러 추가해보세요.</div>`;
    return;
  }

  const allItems = SITE_DATA.archive.flatMap((g) => g.items);
  const favItems = allItems.filter((item) => favorites.has(item.link));

  const grid = document.createElement("div");
  grid.className = "item-grid";
  favItems.forEach((item) => grid.appendChild(buildItemCard(item)));
  container.appendChild(grid);
}

// ── 링크 모음 렌더링 ─────────────────────────────────────────
function renderLinks() {
  const container = document.getElementById("linksContent");
  container.innerHTML = "";

  const collections = SITE_DATA.links || [];
  const hasAny = collections.some((c) => c.items && c.items.length > 0);

  if (!hasAny) {
    container.innerHTML = `<div class="empty-state">등록된 링크가 없습니다.<br/>config.py의 LINK_COLLECTIONS에 추가해주세요.</div>`;
    return;
  }

  collections.forEach((col) => {
    if (!col.items || col.items.length === 0) return;

    const title = document.createElement("section");
    title.className = "block-title";
    title.textContent = col.category;
    container.appendChild(title);

    const grid = document.createElement("div");
    grid.className = "link-grid";
    col.items.forEach((item) => {
      const a = document.createElement("a");
      a.className = "card link-card";
      a.href = item.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.innerHTML = `<span class="link-icon">🔗</span><span>${escapeHtml(item.name)}</span>`;
      grid.appendChild(a);
    });
    container.appendChild(grid);
  });
}

// ── 차트 변동 배지 ────────────────────────────────────────
function changeBadgeHtml(change) {
  if (!change) return "";
  if (change.kind === "new") return `<span class="chart-change new">NEW</span>`;
  if (change.kind === "up") return `<span class="chart-change up">▲ ${change.delta}</span>`;
  if (change.kind === "down") return `<span class="chart-change down">▼ ${change.delta}</span>`;
  return ""; // 변동 없음(same)은 아무 표시도 안 함 - 매번 "-"가 뜨면 지저분해짐
}

// ── 팬 반응 렌더링 ───────────────────────────────────────────
function renderReactions() {
  const container = document.getElementById("reactionsContent");
  container.innerHTML = "";

  const reactions = SITE_DATA.fan_reactions || [];
  if (reactions.length === 0) {
    container.innerHTML = `<div class="empty-state">아직 수집된 팬 반응이 없습니다.<br/>(YouTube API 키 설정이 필요할 수 있습니다)</div>`;
    return;
  }

  // 정렬 토글 (좋아요순 기본 / 최신순)
  const sortBar = document.createElement("div");
  sortBar.className = "reaction-sort-bar";
  sortBar.innerHTML = `
    <button class="source-tab${state.reactionSort === "likes" ? " active" : ""}" data-sort="likes">👍 좋아요순</button>
    <button class="source-tab${state.reactionSort === "recent" ? " active" : ""}" data-sort="recent">🕒 최신순</button>
  `;
  sortBar.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.reactionSort = btn.dataset.sort;
      renderReactions();
    });
  });
  container.appendChild(sortBar);

  const sorted = [...reactions].sort((a, b) => {
    if (state.reactionSort === "recent") {
      return (b.published_at_raw || "").localeCompare(a.published_at_raw || "");
    }
    return b.like_count - a.like_count;
  });

  const list = document.createElement("div");
  sorted.forEach((r) => {
    const card = document.createElement("div");
    card.className = "card reaction-card";
    card.innerHTML = `
      <a class="reaction-video" href="${r.video_link}" target="_blank" rel="noopener noreferrer">
        ▶️ ${escapeHtml(r.video_title)}
      </a>
      <div class="reaction-text">${escapeHtml(r.text)}</div>
      <div class="reaction-meta">
        <span>${escapeHtml(r.author)}</span>
        <span class="reaction-like">👍 ${r.like_count.toLocaleString()}</span>
        ${r.published_at ? `<span>${r.published_at}</span>` : ""}
      </div>
    `;
    list.appendChild(card);
  });
  container.appendChild(list);
}

// ── 차트 렌더링 ───────────────────────────────────────────
function chartRowsHtml(songs) {
  if (songs.length === 0) {
    return `<div class="chart-empty">현재 차트에 리센느 곡이 없습니다.</div>`;
  }
  return songs
    .map(
      (s) => `
    <div class="chart-row">
      <div class="chart-rank">${s.rank}</div>
      <div class="chart-song">${escapeHtml(s.song_title)}</div>
      ${changeBadgeHtml(s.change)}
    </div>`
    )
    .join("");
}

// ── 곡별 종합 테이블용 데이터 피벗 ───────────────────────────
function buildSongChartRows() {
  const songMap = {}; // 곡제목 -> { platformKey: {rank, change} }

  // 1) 전체 곡 목록을 기준으로 행을 먼저 만들어둠 (차트에 없어도 "-"로 표시)
  (SITE_DATA.all_songs || []).forEach((title) => {
    songMap[title] = {};
  });

  // 2) 실제 차트에 잡힌 곡은 순위 정보를 채워넣음 (목록에 없던 곡이면 새로 추가)
  CHART_TABLE_PLATFORMS.forEach(({ key }) => {
    const songs = (SITE_DATA.chart && SITE_DATA.chart[key]) || [];
    songs.forEach((s) => {
      if (!songMap[s.song_title]) songMap[s.song_title] = {};
      songMap[s.song_title][key] = { rank: s.rank, change: s.change };
    });
  });

  const rows = Object.entries(songMap).map(([title, platforms]) => ({ title, platforms }));
  rows.sort((a, b) => {
    const ranksA = Object.values(a.platforms).map((p) => p.rank);
    const ranksB = Object.values(b.platforms).map((p) => p.rank);
    const bestA = ranksA.length ? Math.min(...ranksA) : Infinity;
    const bestB = ranksB.length ? Math.min(...ranksB) : Infinity;
    return bestA - bestB;
  });
  return rows;
}

function chartCellHtml(cell) {
  if (!cell) return `<div class="chart-cell empty">-</div>`;
  const changeHtml = cell.change ? changeBadgeHtml(cell.change) : "";
  return `<div class="chart-cell"><span class="chart-cell-rank">${cell.rank}</span>${changeHtml}</div>`;
}

function renderChart() {
  const grid = document.getElementById("chartGrid");
  grid.innerHTML = "";

  // 최근 조회 시각 (아무 플랫폼이나 하나 참고)
  let checkedAt = null;
  for (const { key } of CHART_TABLE_PLATFORMS) {
    const songs = (SITE_DATA.chart && SITE_DATA.chart[key]) || [];
    if (songs.length > 0) {
      checkedAt = songs[0].checked_at;
      break;
    }
  }

  const tableWrap = document.createElement("div");
  tableWrap.className = "card chart-table-wrap";

  const rows = buildSongChartRows();
  const headerCells = CHART_TABLE_PLATFORMS.map((p) => `<th>${p.label}</th>`).join("");

  let bodyHtml;
  if (rows.length === 0) {
    bodyHtml = `<tr><td colspan="${CHART_TABLE_PLATFORMS.length + 1}"><div class="chart-empty">현재 차트에 리센느 곡이 없습니다.</div></td></tr>`;
  } else {
    bodyHtml = rows
      .map(
        (row) => `
      <tr>
        <td class="chart-song-cell">${escapeHtml(row.title)}</td>
        ${CHART_TABLE_PLATFORMS.map((p) => `<td>${chartCellHtml(row.platforms[p.key])}</td>`).join("")}
      </tr>`
      )
      .join("");
  }

  tableWrap.innerHTML = `
    <div class="chart-table-head">
      <div class="chart-platform">국내 종합 차트</div>
      <div class="chart-checked">${checkedAt ? checkedAt + " 기준" : "미조회"}</div>
    </div>
    <div class="chart-table-scroll">
      <table class="chart-table">
        <thead><tr><th></th>${headerCells}</tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    </div>
  `;
  grid.appendChild(tableWrap);

  // ── 해외(미국·일본) 보조 섹션 ───────────────────────────
  const intlTitle = document.createElement("section");
  intlTitle.className = "block-title";
  intlTitle.textContent = "해외 차트 (US·JP)";
  grid.appendChild(intlTitle);

  const intlGrid = document.createElement("div");
  intlGrid.className = "chart-grid-inner";
  INTERNATIONAL_EXTRA_SERVICES.forEach(({ key, label }) => {
    const card = document.createElement("div");
    card.className = "card chart-card";

    const countryBlocks = INTERNATIONAL_EXTRA_COUNTRIES.map(({ code, label: countryLabel }) => {
      const platform = `${key}_${code}`;
      const songs = (SITE_DATA.chart && SITE_DATA.chart[platform]) || [];
      return `
        <div class="chart-country-block">
          <div class="chart-country-label">${countryLabel}</div>
          ${chartRowsHtml(songs)}
        </div>
      `;
    }).join("");

    card.innerHTML = `
      <div class="chart-card-head">
        <div class="chart-platform">${label}</div>
      </div>
      ${countryBlocks}
    `;
    intlGrid.appendChild(card);
  });
  grid.appendChild(intlGrid);
}

// ── 기념일 D-day 렌더링 ───────────────────────────────────
function renderAnniversaries() {
  const grid = document.getElementById("anniversaryGrid");
  if (!grid) return;
  grid.innerHTML = "";

  const items = SITE_DATA.anniversaries || [];
  if (items.length === 0) {
    grid.innerHTML = `<div class="empty-state">등록된 기념일이 없습니다. config.py에서 멤버 생일을 채워주세요.</div>`;
    return;
  }

  items.forEach((a) => {
    const card = document.createElement("div");
    card.className = "card dday-card";
    const label = a.d_day === 0 ? "D-DAY" : `D-${a.d_day}`;
    card.innerHTML = `
      <div class="dday-value">${label}</div>
      <div class="dday-name">${escapeHtml(a.name)}</div>
      <div class="dday-date">${a.date}</div>
    `;
    grid.appendChild(card);
  });
}

// ── 트로피 렌더링 ─────────────────────────────────────────
function renderTrophies() {
  const container = document.getElementById("trophiesContent");
  container.innerHTML = "";

  const trophies = SITE_DATA.trophies || [];
  if (trophies.length === 0) {
    container.innerHTML = `<div class="empty-state">아직 감지된 1위 수상 기록이 없습니다.</div>`;
    return;
  }

  trophies.forEach((t) => {
    const row = document.createElement("a");
    row.className = "card trophy-row";
    row.href = t.source_link;
    row.target = "_blank";
    row.rel = "noopener noreferrer";
    row.style.textDecoration = "none";
    row.style.color = "inherit";
    row.innerHTML = `
      <span class="trophy-icon">🏆</span>
      <div style="flex:1;">
        <div class="trophy-show">${escapeHtml(t.show)}${t.song ? ` · ${escapeHtml(t.song)}` : ""}</div>
        <div class="trophy-title">${escapeHtml(t.title)}</div>
      </div>
      <div class="trophy-date">${t.date}</div>
    `;
    container.appendChild(row);
  });
}

// ── 포토카드 발매 기록 렌더링 ─────────────────────────────
// ── 통계 대시보드 렌더링 ─────────────────────────────────────
function renderStats() {
  const container = document.getElementById("statsContent");
  if (!container) return;
  container.innerHTML = "";

  const allItems = (SITE_DATA.archive || []).flatMap((g) =>
    g.items.map((item) => ({ ...item, date: g.date }))
  );

  if (allItems.length === 0) {
    container.innerHTML = `<div class="empty-state">아직 통계를 낼 데이터가 없습니다.</div>`;
    return;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // ── 이번 주 / 이번 달 요약 ────────────────────────────
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);
  const monthAgo = new Date(today);
  monthAgo.setDate(monthAgo.getDate() - 30);

  const isAfter = (dateStr, cutoff) => new Date(dateStr + "T00:00:00") >= cutoff;

  const weekItems = allItems.filter((i) => isAfter(i.date, weekAgo));
  const monthItems = allItems.filter((i) => isAfter(i.date, monthAgo));

  const weekTrophies = (SITE_DATA.trophies || []).filter((t) => isAfter(t.date, weekAgo));

  const summaryCard = document.createElement("div");
  summaryCard.className = "card stats-summary-card";
  summaryCard.innerHTML = `
    <div class="stats-summary-grid">
      <div class="stats-summary-item">
        <div class="stats-summary-value">${weekItems.length}</div>
        <div class="stats-summary-label">최근 7일 신규 소식</div>
      </div>
      <div class="stats-summary-item">
        <div class="stats-summary-value">${monthItems.length}</div>
        <div class="stats-summary-label">최근 30일 신규 소식</div>
      </div>
      <div class="stats-summary-item">
        <div class="stats-summary-value">${weekTrophies.length}</div>
        <div class="stats-summary-label">최근 7일 신규 트로피</div>
      </div>
      <div class="stats-summary-item">
        <div class="stats-summary-value">${allItems.length.toLocaleString()}</div>
        <div class="stats-summary-label">누적 전체 소식</div>
      </div>
    </div>
  `;
  container.appendChild(summaryCard);

  // ── 최근 7일 카테고리 분포 ────────────────────────────
  if (weekItems.length > 0) {
    const catTitle = document.createElement("section");
    catTitle.className = "block-title";
    catTitle.textContent = "이번 주 카테고리 분포";
    container.appendChild(catTitle);

    const catCounts = {};
    weekItems.forEach((i) => {
      catCounts[i.category] = (catCounts[i.category] || 0) + 1;
    });
    const maxCat = Math.max(...Object.values(catCounts));

    const catCard = document.createElement("div");
    catCard.className = "card stats-bar-card";
    catCard.innerHTML = Object.entries(catCounts)
      .sort((a, b) => b[1] - a[1])
      .map(
        ([cat, count]) => `
        <div class="stats-bar-row">
          <div class="stats-bar-label">${escapeHtml(cat)}</div>
          <div class="stats-bar-track"><div class="stats-bar-fill" style="width:${(count / maxCat) * 100}%"></div></div>
          <div class="stats-bar-count">${count}</div>
        </div>`
      )
      .join("");
    container.appendChild(catCard);
  }

  // ── 월별 소식 수 추이(최근 12개월) ───────────────────────
  const monthTitle = document.createElement("section");
  monthTitle.className = "block-title";
  monthTitle.textContent = "월별 소식 수 추이 (최근 12개월)";
  container.appendChild(monthTitle);

  const monthCounts = {};
  allItems.forEach((i) => {
    const monthKey = i.date.slice(0, 7); // YYYY-MM
    monthCounts[monthKey] = (monthCounts[monthKey] || 0) + 1;
  });

  const months = [];
  const cursor = new Date(today.getFullYear(), today.getMonth(), 1);
  for (let i = 0; i < 12; i++) {
    const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}`;
    months.unshift(key);
    cursor.setMonth(cursor.getMonth() - 1);
  }
  const maxMonth = Math.max(1, ...months.map((m) => monthCounts[m] || 0));

  const monthCard = document.createElement("div");
  monthCard.className = "card stats-monthchart-card";
  monthCard.innerHTML = `
    <div class="stats-monthchart">
      ${months
        .map((m) => {
          const count = monthCounts[m] || 0;
          const heightPct = Math.max(3, (count / maxMonth) * 100);
          const label = m.slice(2).replace("-", ".");
          return `
          <div class="stats-monthbar-wrap">
            <div class="stats-monthbar-count">${count}</div>
            <div class="stats-monthbar" style="height:${heightPct}%"></div>
            <div class="stats-monthbar-label">${label}</div>
          </div>`;
        })
        .join("")}
    </div>
  `;
  container.appendChild(monthCard);

  // ── 트로피 누적 (방송별) ────────────────────────────
  const trophies = SITE_DATA.trophies || [];
  if (trophies.length > 0) {
    const trophyTitle = document.createElement("section");
    trophyTitle.className = "block-title";
    trophyTitle.textContent = "방송별 누적 트로피";
    container.appendChild(trophyTitle);

    const showCounts = {};
    trophies.forEach((t) => {
      showCounts[t.show] = (showCounts[t.show] || 0) + 1;
    });

    const trophyCard = document.createElement("div");
    trophyCard.className = "card stats-bar-card";
    trophyCard.innerHTML = Object.entries(showCounts)
      .sort((a, b) => b[1] - a[1])
      .map(
        ([show, count]) => `
        <div class="stats-bar-row">
          <div class="stats-bar-label">🏆 ${escapeHtml(show)}</div>
          <div class="stats-bar-track"><div class="stats-bar-fill" style="width:${(count / trophies.length) * 100}%"></div></div>
          <div class="stats-bar-count">${count}</div>
        </div>`
      )
      .join("");
    container.appendChild(trophyCard);
  }
}

function renderPhotocards() {
  const container = document.getElementById("photocardContent");
  if (!container) return;
  container.innerHTML = "";

  const releases = SITE_DATA.photocard_releases || [];
  if (releases.length === 0) {
    container.innerHTML = `<div class="empty-state">등록된 포토카드 발매 기록이 없습니다.</div>`;
    return;
  }

  const typeBadgeClass = { "방송": "badge-broadcast", "팬사인회": "badge-fansign", "기타": "badge-etc" };

  releases.forEach((r) => {
    const row = document.createElement("div");
    row.className = "card photocard-row";
    row.innerHTML = `
      <span class="photocard-date">${r.date}</span>
      <span class="photocard-name">${escapeHtml(r.release_name)}</span>
      <span class="photocard-type ${typeBadgeClass[r.type] || "badge-etc"}">${escapeHtml(r.type)}</span>
    `;
    container.appendChild(row);
  });
}

// ── 스케줄 렌더링 ─────────────────────────────────────────
function dDayLabel(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr + "T00:00:00");
  const diffDays = Math.round((target - today) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "D-DAY";
  if (diffDays > 0) return "D-" + diffDays;
  return "D+" + Math.abs(diffDays);
}

function renderSchedule() {
  const upcomingWrap = document.getElementById("scheduleUpcoming");
  const pastWrap = document.getElementById("schedulePast");
  const pastTitle = document.getElementById("pastTitle");
  upcomingWrap.innerHTML = "";
  pastWrap.innerHTML = "";

  const sched = SITE_DATA.schedule || { upcoming: [], past: [] };

  if (sched.upcoming.length === 0) {
    upcomingWrap.innerHTML = `<div class="empty-state">등록된 예정 일정이 없습니다.<br/>config.py의 SCHEDULE_ITEMS에 추가해주세요.</div>`;
  } else {
    sched.upcoming.forEach((s) => {
      upcomingWrap.appendChild(scheduleRow(s));
    });
  }

  if (sched.past.length > 0) {
    pastTitle.style.display = "block";
    sched.past.forEach((s) => {
      pastWrap.appendChild(scheduleRow(s));
    });
  }
}

function scheduleRow(s) {
  const row = document.createElement("div");
  row.className = "card schedule-row";
  const estimatedBadge = s.is_estimated
    ? `<span class="badge estimated">추정</span>`
    : "";
  row.innerHTML = `
    <div class="schedule-dday">${dDayLabel(s.date)}</div>
    <div class="schedule-body">
      <div class="schedule-date">${s.date}</div>
      <div class="schedule-title">${escapeHtml(s.title)} ${estimatedBadge}</div>
      ${s.note ? `<div class="schedule-note">${escapeHtml(s.note)}</div>` : ""}
    </div>
    <div class="schedule-type">${escapeHtml(s.type)}</div>
  `;
  return row;
}

// ── 유틸 ──────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

// ── 새로고침 버튼 (로컬 실행 시에만 동작) ───────────────────
const refreshBtn = document.getElementById("refreshBtn");
if (refreshBtn) {
  refreshBtn.addEventListener("click", async () => {
    const original = refreshBtn.textContent;
    refreshBtn.disabled = true;
    refreshBtn.textContent = "⏳ 갱신 중... (최대 1분)";
    try {
      const res = await fetch("/api/refresh");
      const result = await res.json();
      if (result.status === "ok") {
        location.reload();
      } else {
        alert("새로고침 중 문제가 발생했습니다: " + result.message);
        refreshBtn.disabled = false;
        refreshBtn.textContent = original;
      }
    } catch (e) {
      alert(
        "서버에 연결할 수 없습니다.\n" +
          "refresh_and_open.bat(또는 local_server.py)이 실행 중인지 확인해주세요."
      );
      refreshBtn.disabled = false;
      refreshBtn.textContent = original;
    }
  });
}

// ── 자동 새로고침 감지 ───────────────────────────────────────
// 방문자가 페이지를 계속 켜두고 있어도, 새 데이터가 서버(GitHub Pages)에
// 올라오면 몇 분 안에 자동으로 알아채서 새로고침합니다 (수동 새로고침 불필요).
const AUTO_REFRESH_CHECK_INTERVAL_MS = 2 * 60 * 1000; // 2분마다 확인

function startAutoRefreshWatcher() {
  if (!SITE_DATA || !SITE_DATA.generated_at) return;
  const loadedAt = SITE_DATA.generated_at;

  setInterval(async () => {
    try {
      const res = await fetch("data.js?t=" + Date.now(), { cache: "no-store" });
      if (!res.ok) return;
      const text = await res.text();
      const m = text.match(/"generated_at":\s*"([^"]+)"/);
      if (m && m[1] !== loadedAt) {
        location.reload();
      }
    } catch (e) {
      // file:// 로컬 테스트 등 fetch가 안 되는 환경에서는 조용히 무시
    }
  }, AUTO_REFRESH_CHECK_INTERVAL_MS);
}

// ── 초기 렌더 ─────────────────────────────────────────────
buildSourceChips();
buildCategoryChips();
buildYearChips();
buildMemberChips();
renderArchive();
renderChart();
renderSchedule();
renderAnniversaries();
renderTrophies();
renderPhotocards();
renderStats();
startAutoRefreshWatcher();
