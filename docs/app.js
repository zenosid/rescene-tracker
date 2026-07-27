// RESCENE Tracker — 렌더링 스크립트
// data.js에서 정의된 전역 SITE_DATA를 읽어서 화면을 그립니다.

const SOURCE_META = {
  youtube: { icon: "▶️", label: "공식 유튜브" },
  youtube_collab: { icon: "🤝", label: "콜라보" },
  news: { icon: "📰", label: "뉴스" },
};

const MEMBER_COLORS = {
  "원이": "var(--aurora-pink)",
  "리브": "var(--aurora-violet)",
  "미나미": "var(--aurora-cyan)",
  "메이": "var(--aurora-mint)",
  "제나": "var(--aurora-amber)",
};

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

const CATEGORY_LIST = ["음악방송", "MV", "Live", "Shorts", "자체컨텐츠", "외부컨텐츠", "기타"];

// ── 상태 ──────────────────────────────────────────────────
const state = {
  sourceTab: "all", // 단일 선택: "all" | "youtube" | "youtube_collab" | "news"
  members: new Set(), // 비어있으면 전체
  categories: new Set(), // 비어있으면 전체
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
  CATEGORY_LIST.forEach((cat) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (state.categories.has(cat) ? " on category-on" : "");
    chip.dataset.category = cat;
    chip.textContent = cat;
    chip.addEventListener("click", () => {
      if (state.categories.has(cat)) {
        state.categories.delete(cat);
      } else {
        state.categories.add(cat);
      }
      buildCategoryChips();
      renderArchive();
    });
    wrap.appendChild(chip);
  });
}

// ── 아이템 카드 (아카이브·즐겨찾기 공용) ───────────────────
function itemPassesFilter(item) {
  if (state.sourceTab !== "all" && item.source_type !== state.sourceTab) return false;
  if (state.categories.size > 0 && !state.categories.has(item.category)) return false;
  if (state.members.size > 0) {
    const hasOverlap = item.members.some((m) => state.members.has(m));
    if (!hasOverlap) return false;
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

  return card;
}

// ── 아카이브 렌더링 ───────────────────────────────────────
function renderArchive() {
  const container = document.getElementById("archiveContent");
  container.innerHTML = "";

  let totalShown = 0;

  SITE_DATA.archive.forEach((group) => {
    const visibleItems = group.items.filter(itemPassesFilter);
    if (visibleItems.length === 0) return;
    totalShown += visibleItems.length;

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

  if (totalShown === 0) {
    container.innerHTML = `<div class="empty-state">조건에 맞는 항목이 없습니다.<br/>필터를 조정하거나 데이터를 새로고침해주세요.</div>`;
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
  return `<span class="chart-change same">–</span>`;
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

  reactions.forEach((r) => {
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
      </div>
    `;
    container.appendChild(card);
  });
}

// ── 차트 렌더링 ───────────────────────────────────────────
function renderChart() {
  const grid = document.getElementById("chartGrid");
  grid.innerHTML = "";

  Object.entries(PLATFORM_LABELS).forEach(([platform, label]) => {
    const songs = (SITE_DATA.chart && SITE_DATA.chart[platform]) || [];
    const card = document.createElement("div");
    card.className = "card chart-card";

    const checkedAt = songs.length > 0 ? songs[0].checked_at : null;
    let rowsHtml = "";
    if (songs.length === 0) {
      rowsHtml = `<div class="chart-empty">현재 차트에 리센느 곡이 없습니다.</div>`;
    } else {
      rowsHtml = songs
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

    card.innerHTML = `
      <div class="chart-card-head">
        <div class="chart-platform">${label}</div>
        <div class="chart-checked">${checkedAt ? checkedAt : "미조회"}</div>
      </div>
      ${rowsHtml}
    `;
    grid.appendChild(card);
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
buildMemberChips();
renderArchive();
renderChart();
renderSchedule();
startAutoRefreshWatcher();
