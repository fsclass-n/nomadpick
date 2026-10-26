/* SC-05 맞춤 추천 */
NP.renderLayout("recommend");

function prefChips(p) {
  if (!p) {
    return '<span class="text-secondary">선호 설정이 없어 할인율 순으로 추천합니다.</span><a href="preferences.html" class="btn btn-sm btn-primary ms-auto">선호 설정하기</a>';
  }
  const chip = (icon, text) => `<span class="badge rounded-pill text-bg-light border fs-6 fw-normal"><i class="bi ${icon} me-1 text-primary"></i>${NP.esc(text)}</span>`;
  const out = [];
  if (p.regions?.length) out.push(chip("bi-geo-alt", p.regions.join(" · ")));
  if (p.budget_max) out.push(chip("bi-wallet2", `${NP.manwon(p.budget_min || 0)} ~ ${NP.manwon(p.budget_max)}`));
  if (p.depart_months?.length) out.push(chip("bi-calendar3", p.depart_months.map((m) => `${+m.slice(5)}월`).join(", ")));
  if (p.nights_min !== null && p.nights_max !== null) out.push(chip("bi-moon-stars", `${p.nights_min}~${p.nights_max}박`));
  if (p.theme) out.push(chip("bi-tag", p.theme));
  if (p.companion) out.push(chip("bi-people", p.companion));
  return out.join("");
}

function row(r, i) {
  return `
  <div class="np-panel p-3">
    <div class="d-flex gap-3 align-items-start">
      <div class="np-rank">${i + 1}</div>
      <div class="flex-grow-1 min-w-0">
        <div class="d-flex flex-wrap gap-1 mb-1">
          ${r.discount_rate > 0 ? `<span class="badge np-badge-discount">-${Math.round(r.discount_rate)}%</span>` : ""}
          <span class="badge text-bg-primary-subtle text-primary-emphasis">${NP.esc(r.agency)}</span>
          <span class="badge text-bg-light border">${NP.esc(r.region)} · ${NP.esc(r.city || "")}</span>
          ${NP.sourceBadge(r)}
        </div>
        <a class="fw-semibold text-reset fs-5" href="product.html?id=${r.product_id}">${NP.esc(r.title)}</a>
        <div class="small text-secondary my-1"><i class="bi bi-calendar-event me-1"></i>${NP.depart(r)} · ${r.nights}박 ${r.days}일
          ${NP.seats(r.seats_left)}</div>
        <div>${r.reasons.map((x) => `<span class="np-reason">${NP.esc(x)}</span>`).join("")}</div>
      </div>
      <div class="text-end d-none d-md-block" style="min-width:170px">
        ${r.original_price ? `<div class="np-price-org">${NP.won(r.original_price)}</div>` : ""}
        <div class="np-price">${NP.won(r.price)}</div>
        <div class="np-score mt-2"><small class="text-secondary">추천 점수 <b class="text-primary">${r.score}</b></small>
          <div class="progress"><div class="progress-bar" style="width:${Math.min(r.score, 100)}%"></div></div></div>
      </div>
    </div>
    <div class="d-md-none d-flex justify-content-between align-items-end mt-2">
      <small class="text-secondary">추천 점수 <b class="text-primary">${r.score}</b></small><div class="np-price">${NP.won(r.price)}</div>
    </div>
  </div>`;
}

async function init() {
  if (!NP.requireLogin()) return;
  const list = document.getElementById("list");
  try {
    const [pref, items] = await Promise.all([NP.api("/preferences", { auth: true }), NP.api("/recommendations", { auth: true })]);
    document.getElementById("prefSummary").innerHTML = prefChips(pref);
    list.innerHTML = items.length
      ? items.map(row).join("")
      : '<div class="text-center text-secondary py-5">추천할 특가가 아직 없습니다. RPA 수집이 완료되면 표시됩니다.</div>';
  } catch (e) {
    list.innerHTML = `<div class="alert alert-warning">${NP.esc(e.message)}</div>`;
  }
}

document.getElementById("excelBtn").addEventListener("click", async (e) => {
  e.target.disabled = true;
  try {
    await NP.download("/recommendations/excel", "nomadpick_recommendations.xlsx");
    NP.toast("추천 결과 엑셀을 다운로드했습니다.", "success");
  } catch (err) {
    NP.toast(err.message, "danger");
  } finally {
    e.target.disabled = false;
  }
});

init();
