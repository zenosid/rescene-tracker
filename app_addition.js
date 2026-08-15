function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

// ── 포토카드 발매 기록 렌더링 ─────────────────────────────────
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
