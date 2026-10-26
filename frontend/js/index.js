/* SC-04 오늘의 특가 */
NP.renderLayout("index");

const state = { page: 1, size: 20, regions: new Set() };
const form = document.getElementById("filterForm");
const cards = document.getElementById("cards");

function nextMonths(n = 6) {
  const out = [];
  const d = new Date();
  for (let i = 0; i < n; i += 1) {
    const m = new Date(d.getFullYear(), d.getMonth() + i, 1);
    out.push(`${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, "0")}`);
  }
  return out;
}

function params() {
  const fd = new FormData(form);
  return {
    region: [...state.regions].join(","),
    price_max: fd.get("price_max"),
    month: fd.get("month"),
    agency: fd.get("agency"),
    theme: fd.get("theme"),
    q: (fd.get("q") || "").trim(),
    sort: fd.get("sort") || "discount",
    page: state.page,
    size: state.size,
  };
}

async function loadMeta() {
  const meta = await NP.publicGet("/meta", {}, () => NP.sample.meta());
  document.getElementById("statTotal").textContent = `${meta.total.toLocaleString()}개`;
  document.getElementById("statAgencies").textContent = `${meta.agencies.length}곳`;
  document.getElementById("statUpdated").textContent = meta.collected_at ? NP.datetime(meta.collected_at) : "-";

  document.getElementById("regionChips").innerHTML = ['<span class="small text-secondary me-1 align-self-center">지역</span>']
    .concat(meta.regions.map((r, i) => `
      <input type="checkbox" class="btn-check" id="rg${i}" value="${r}" autocomplete="off">
      <label class="btn btn-sm btn-outline-primary np-chip" for="rg${i}">${r}</label>`)).join("");
  document.querySelectorAll("#regionChips .btn-check").forEach((el) => el.addEventListener("change", () => {
    el.checked ? state.regions.add(el.value) : state.regions.delete(el.value);
    reload();
  }));
  document.getElementById("agencySelect").innerHTML += meta.agencies.map((a) => `<option value="${a.code}">${a.name} (${a.count})</option>`).join("");
  document.getElementById("themeSelect").innerHTML += meta.themes.map((t) => `<option>${t}</option>`).join("");
  document.getElementById("monthSelect").innerHTML += nextMonths().map((m) => `<option value="${m}">${+m.slice(5)}월 (${m.slice(0, 4)})</option>`).join("");
}

async function load(append = false) {
  const p = params();
  const data = await NP.publicGet("/products", p, () => NP.sample.products(p));
  if (!append) cards.innerHTML = "";
  if (!data.items.length && !append) {
    cards.innerHTML = '<div class="w-100 text-center text-secondary py-5"><i class="bi bi-search fs-1 d-block mb-2"></i>조건에 맞는 특가가 없습니다. 필터를 조정해 보세요.</div>';
  }
  cards.insertAdjacentHTML("beforeend", data.items.map((x) => NP.productCard(x, { favorite: true })).join(""));
  NP.bindFavoriteButtons(cards);
  document.getElementById("resultInfo").innerHTML =
    `총 <b>${data.total.toLocaleString()}</b>개 특가 · ${data.collected_at ? `${NP.datetime(data.collected_at)} RPA 수집 기준` : "수집 대기 중"}`;
  document.getElementById("moreBtn").classList.toggle("d-none", data.page * data.size >= data.total);
}

function reload() {
  state.page = 1;
  load().catch((e) => NP.toast(e.message, "danger"));
}

form.addEventListener("change", (e) => {
  if (e.target.closest("#regionChips")) return;
  if (window.innerWidth >= 992) reload();
});
form.addEventListener("submit", (e) => { e.preventDefault(); reload(); });
form.q.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); reload(); } });
document.getElementById("sortMobile").addEventListener("change", (e) => { document.getElementById("sortSelect").value = e.target.value; reload(); });
document.getElementById("resetBtn").addEventListener("click", () => {
  form.reset();
  state.regions.clear();
  document.querySelectorAll("#regionChips .btn-check").forEach((el) => { el.checked = false; });
});
document.getElementById("moreBtn").addEventListener("click", () => { state.page += 1; load(true); });

loadMeta().then(() => load()).catch((e) => NP.toast(e.message, "danger"));
