/* SC-06 상품 상세 - 가격 추이(Plotly), 국내선 항공편(국토교통부), 관심 등록, 원문 링크 */
NP.renderLayout("index");

const id = NP.param("id");
let product = null;

function priceDelta(p) {
  if (p.saved_price) {
    const diff = p.price - p.saved_price;
    if (diff !== 0) return `<span class="badge ${diff < 0 ? "text-bg-success" : "text-bg-secondary"}">관심 등록 대비 ${diff < 0 ? "▼" : "▲"} ${NP.won(Math.abs(diff))}</span>`;
  }
  if (p.previous_price && p.previous_price !== p.price) {
    const diff = p.price - p.previous_price;
    return `<span class="badge ${diff < 0 ? "text-bg-success" : "text-bg-secondary"}">직전 수집 대비 ${diff < 0 ? "▼" : "▲"} ${NP.won(Math.abs(diff))}</span>`;
  }
  return "";
}

function renderDetail(p) {
  document.title = `${p.title} | NomadPick`;
  document.getElementById("detail").innerHTML = `
  <div class="np-panel overflow-hidden">
    <div class="row g-0">
      <div class="col-md-4"><div class="${NP.thumbClass(p)} h-100" style="min-height:200px">${NP.thumbImg(p)}<i class="bi bi-airplane"></i>
        <div><div class="np-region">${NP.esc(p.region)} · ${NP.esc(p.country_code || "")}</div><div class="np-city" style="font-size:30px">${NP.esc(p.city || p.region)}</div></div></div></div>
      <div class="col-md-8 p-4">
        <div class="d-flex flex-wrap gap-1 mb-2">
          ${p.discount_rate > 0 ? `<span class="badge np-badge-discount fs-6">-${Math.round(p.discount_rate)}%</span>` : ""}
          <span class="badge text-bg-primary-subtle text-primary-emphasis fs-6">${NP.esc(p.agency)}</span>
          ${p.theme ? `<span class="badge text-bg-light border fs-6">${NP.esc(p.theme)}</span>` : ""}
          ${NP.sourceBadge(p)}
          ${p.is_active === false ? '<span class="badge text-bg-dark fs-6">판매 종료</span>' : ""}
        </div>
        <h1 class="mb-3">${NP.esc(p.title)}</h1>
        <div class="row g-2 small mb-3">
          <div class="col-6 col-lg-3"><div class="text-secondary">출발일</div><b>${NP.depart(p, "")}</b></div>
          <div class="col-6 col-lg-3"><div class="text-secondary">일정</div><b>${p.nights ?? "-"}박 ${p.days ?? "-"}일</b></div>
          <div class="col-6 col-lg-3"><div class="text-secondary">항공사</div><b>${NP.esc(p.airline || "-")}</b></div>
          <div class="col-6 col-lg-3"><div class="text-secondary">잔여석</div><b class="${p.seats_left !== null && p.seats_left <= 3 ? "text-danger" : ""}">${p.seats_left === 0 ? "마감" : `${p.seats_left ?? "-"}석`}</b></div>
        </div>
        <div class="d-flex flex-wrap align-items-end gap-3">
          <div>
            ${p.original_price ? `<div class="np-price-org">정상가 ${NP.won(p.original_price)}</div>` : ""}
            <div class="np-price" style="font-size:28px">${NP.won(p.price)}</div>
            <div class="mt-1">${priceDelta(p)}</div>
          </div>
          <div class="ms-auto d-flex gap-2">
            <button class="btn btn-outline-danger" id="favBtn"><i class="bi ${p.is_favorite ? "bi-heart-fill" : "bi-heart"} me-1"></i>${p.is_favorite ? "관심 해제" : "관심 등록"}</button>
            <a class="btn btn-primary" href="${NP.esc(p.detail_url || "#")}" target="_blank" rel="noopener"><i class="bi bi-box-arrow-up-right me-1"></i>예약하러 가기</a>
          </div>
        </div>
        <div class="small text-secondary mt-3">상품코드 ${NP.esc(p.product_code || "")} · 최근 수집 ${NP.datetime(p.last_seen_at)}</div>
      </div>
    </div>
  </div>`;
  document.getElementById("favBtn").addEventListener("click", toggleFavorite);
}

function renderFlights(p) {
  const box = document.getElementById("flights");
  if (!p.is_domestic) {
    box.innerHTML = '<i class="bi bi-info-circle me-1"></i>국외 상품은 여행사 패키지 항공편이 포함되어 있습니다. 국토교통부 운항정보는 국내 상품(제주·부산 등)에 표시됩니다.';
    return;
  }
  if (!p.flights?.length) {
    box.innerHTML = "출발일 운항 정보가 아직 수집되지 않았습니다. (매일 07:00 갱신, 출발 30일 이내)";
    return;
  }
  const min = Math.min(...p.flights.filter((f) => f.economy_charge).map((f) => f.economy_charge));
  box.innerHTML = `
    <div class="mb-2 text-body">김포 → ${NP.esc(p.flights[0].arr_airport_nm || p.city)} · ${NP.date(p.flights[0].flight_date || p.depart_date)} · <b>${p.flights.length}편</b>
      ${Number.isFinite(min) ? ` · 일반석 최저 <b class="text-primary">${NP.won(min)}</b>` : ""}
      ${p.flights[0].source === "sample" ? ' <span class="badge text-bg-light border">샘플</span>' : ""}</div>
    <div class="table-responsive" style="max-height:250px"><table class="table table-sm table-np mb-0">
      <thead><tr><th>항공사</th><th>편명</th><th>출발</th><th>도착</th><th class="text-end">일반석</th></tr></thead>
      <tbody>${p.flights.map((f) => `<tr><td>${NP.esc(f.airline_nm)}</td><td>${NP.esc(f.flight_no)}</td><td>${f.dep_time}</td><td>${f.arr_time || "-"}</td>
        <td class="text-end">${f.economy_charge ? NP.won(f.economy_charge) : "-"}</td></tr>`).join("")}</tbody></table></div>`;
}

function renderChart(items) {
  const el = document.getElementById("priceChart");
  if (!items.length) {
    el.innerHTML = '<div class="text-secondary py-5 text-center">가격 이력이 없습니다.</div>';
    return;
  }
  const prices = items.map((i) => i.price);
  const lo = Math.min(...prices), hi = Math.max(...prices);
  const pad = Math.max((hi - lo) * 0.2, hi * 0.05);  // 이력이 1건이거나 변동이 없을 때도 축이 자연스럽도록
  if (items.length < 2) {
    el.insertAdjacentHTML("beforebegin", '<p class="small text-secondary mb-1" id="chartNote">가격 이력이 쌓이는 중입니다 (30분마다 수집).</p>');
  }
  Plotly.newPlot(el, [{
    x: items.map((i) => i.collected_at), y: items.map((i) => i.price), type: "scatter", mode: "lines+markers",
    line: { color: "#0d6efd", width: 3, shape: "hv" }, marker: { size: 5 },
    hovertemplate: "%{x|%m.%d %H:%M}<br><b>%{y:,}원</b><extra></extra>",
  }], {
    margin: { l: 70, r: 10, t: 10, b: 40 }, yaxis: { tickformat: ",", ticksuffix: "원", range: [Math.max(lo - pad, 0), hi + pad] },
    xaxis: { tickformat: "%m.%d" }, plot_bgcolor: "#fff", paper_bgcolor: "#fff", font: { family: "Pretendard, sans-serif" },
  }, { displayModeBar: false, responsive: true });
}

async function toggleFavorite() {
  if (!NP.requireLogin()) return;
  try {
    if (product.is_favorite) {
      await NP.api(`/favorites/${product.id}`, { method: "DELETE", auth: true });
      NP.toast("관심 상품에서 해제했습니다.");
    } else {
      await NP.api("/favorites", { method: "POST", body: { product_id: product.id }, auth: true });
      NP.toast("관심 상품에 등록했습니다.", "success");
    }
    await load();
  } catch (e) {
    NP.toast(e.message, "danger");
  }
}

async function load() {
  product = await NP.publicGet(`/products/${id}`, {}, () => NP.sample.product(id));
  renderDetail(product);
  renderFlights(product);
}

(async () => {
  if (!id) return (location.href = "index.html");
  try {
    await load();
    const prices = await NP.publicGet(`/products/${id}/prices`, { days: 30 }, () => NP.sample.prices(id));
    renderChart(prices.items);
  } catch (e) {
    document.getElementById("detail").innerHTML = `<div class="alert alert-warning mt-3">${NP.esc(e.message)}</div>`;
  }
})();
