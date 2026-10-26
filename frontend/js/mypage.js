/* SC-07 마이페이지 - 관심 상품, 가격 하락 배지 */
NP.renderLayout("mypage");

function favRow(f) {
  const badge = !f.is_active
    ? '<span class="badge text-bg-dark">판매 종료</span>'
    : f.price_dropped
      ? `<span class="badge text-bg-success">가격 하락 ▼ ${NP.won(-f.price_diff)}</span>`
      : f.price_diff > 0 ? `<span class="badge text-bg-secondary">▲ ${NP.won(f.price_diff)}</span>` : '<span class="badge text-bg-light border">변동 없음</span>';
  return `
  <div class="np-panel p-3 d-flex flex-column flex-md-row gap-3 align-items-md-center">
    <div class="np-thumb rg-${NP.esc(f.region)} rounded-3" style="height:64px;width:110px;padding:.4rem .7rem"><div class="np-city" style="font-size:16px">${NP.esc(f.city || f.region)}</div></div>
    <div class="flex-grow-1 min-w-0">
      <div class="d-flex flex-wrap gap-1 mb-1"><span class="badge text-bg-primary-subtle text-primary-emphasis">${NP.esc(f.agency)}</span>${badge}${NP.sourceBadge(f)}</div>
      <a class="fw-semibold text-reset" href="product.html?id=${f.id}">${NP.esc(f.title)}</a>
      <div class="small text-secondary">${NP.depart(f)} · 등록가 ${NP.won(f.saved_price)}</div>
    </div>
    <div class="text-md-end"><div class="np-price">${NP.won(f.price)}</div></div>
    <button class="btn btn-sm btn-outline-secondary" data-del="${f.id}"><i class="bi bi-x-lg"></i> 해제</button>
  </div>`;
}

async function load() {
  const box = document.getElementById("favorites");
  const favs = await NP.api("/favorites", { auth: true });
  box.innerHTML = favs.length
    ? favs.map(favRow).join("")
    : '<div class="np-panel p-5 text-center text-secondary"><i class="bi bi-heart fs-1 d-block mb-2"></i>관심 상품이 없습니다. <a href="index.html">오늘의 특가</a>에서 하트를 눌러 등록해 보세요.</div>';
  box.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    await NP.api(`/favorites/${b.dataset.del}`, { method: "DELETE", auth: true });
    NP.toast("관심 상품에서 해제했습니다.");
    load();
  }));
}

(async () => {
  if (!NP.requireLogin()) return;
  try {
    const me = await NP.api("/users/me", { auth: true });
    document.getElementById("userName").textContent = `${me.name} 님`;
    document.getElementById("userEmail").textContent = me.email;
    await load();
  } catch (e) {
    NP.toast(e.message, "danger");
  }
})();
