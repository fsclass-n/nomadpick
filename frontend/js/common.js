/* 공통 UI - 내비게이션, 푸터, 포맷터, 상품 카드, 토스트 */
window.NP = window.NP || {};

NP.esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
NP.won = (n) => (n === null || n === undefined ? "-" : `${Number(n).toLocaleString("ko-KR")}원`);
NP.manwon = (n) => `${Math.round(n / 10000).toLocaleString("ko-KR")}만 원`;
const WD = "일월화수목금토";
NP.date = (s) => {
  if (!s) return "-";
  const d = new Date(`${s.slice(0, 10)}T00:00:00`);
  return `${d.getMonth() + 1}.${String(d.getDate()).padStart(2, "0")}(${WD[d.getDay()]})`;
};
NP.datetime = (s) => {
  if (!s) return "-";
  const [d, t] = s.split("T");
  return `${d.slice(5).replace("-", ".")} ${t.slice(0, 5)}`;
};
/** 출발일 표기: 단일 '11.05(목) 출발' / 기간·목록 '11.01(일)~12.31(목) 출발' */
NP.depart = (p, suffix = " 출발") => (p.depart_end ? `${NP.date(p.depart_date)}~${NP.date(p.depart_end)}` : NP.date(p.depart_date)) + suffix;
NP.param = (k) => new URLSearchParams(location.search).get(k);

NP.toast = (message, type = "primary") => {
  let box = document.getElementById("np-toasts");
  if (!box) {
    box = document.createElement("div");
    box.id = "np-toasts";
    box.className = "toast-container position-fixed bottom-0 end-0 p-3";
    document.body.appendChild(box);
  }
  const el = document.createElement("div");
  el.className = `toast align-items-center text-bg-${type} border-0`;
  el.innerHTML = `<div class="d-flex"><div class="toast-body">${NP.esc(message)}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
  box.appendChild(el);
  new bootstrap.Toast(el, { delay: 2800 }).show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
};

NP.requireLogin = () => {
  if (!NP.auth.isLoggedIn()) {
    location.href = `login.html?next=${encodeURIComponent(location.pathname.split("/").pop() + location.search)}`;
    return false;
  }
  return true;
};

NP.logout = () => {
  NP.auth.clear();
  location.href = "index.html";
};

NP.download = async (path, fallbackName) => {
  const res = await NP.api(path, { auth: true, raw: true });
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename\*=UTF-8''([^;]+)/);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = m ? decodeURIComponent(m[1]) : fallbackName;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
};

NP.renderLayout = (active) => {
  const user = NP.auth.user();
  const link = (href, label, key, icon) =>
    `<li class="nav-item"><a class="nav-link ${active === key ? "active" : ""}" href="${href}"><i class="bi ${icon} me-1"></i>${label}</a></li>`;
  const right = user
    ? `<li class="nav-item dropdown">
         <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown"><i class="bi bi-person-circle me-1"></i>${NP.esc(user.name)}</a>
         <ul class="dropdown-menu dropdown-menu-end">
           <li><a class="dropdown-item" href="preferences.html"><i class="bi bi-sliders me-2"></i>선호 설정</a></li>
           <li><a class="dropdown-item" href="mypage.html"><i class="bi bi-heart me-2"></i>마이페이지</a></li>
           <li><hr class="dropdown-divider"></li>
           <li><button class="dropdown-item" id="np-logout"><i class="bi bi-box-arrow-right me-2"></i>로그아웃</button></li>
         </ul></li>`
    : `<li class="nav-item"><a class="nav-link" href="login.html">로그인</a></li>
       <li class="nav-item"><a class="btn btn-primary btn-sm ms-lg-2 mt-1" href="signup.html">회원가입</a></li>`;

  document.body.insertAdjacentHTML("afterbegin", `
    <div id="np-offline" class="np-offline small py-2 d-none"><div class="container">
      <i class="bi bi-wifi-off me-1"></i>백엔드 서버에 연결하지 못해 <b>오프라인 데모 데이터</b>를 표시하고 있습니다.
      (Render 무료 인스턴스는 첫 접속 시 깨어나는 데 최대 1분이 걸릴 수 있습니다)
      <a href="#" onclick="location.reload();return false;" class="ms-2">다시 시도</a></div></div>
    <nav class="navbar navbar-expand-lg np-navbar sticky-top">
      <div class="container">
        <a class="navbar-brand np-brand" href="index.html"><i class="bi bi-compass-fill me-1"></i>NomadPick</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#npNav"><span class="navbar-toggler-icon"></span></button>
        <div class="collapse navbar-collapse" id="npNav">
          <ul class="navbar-nav me-auto">
            ${link("index.html", "오늘의 특가", "index", "bi-lightning-charge")}
            ${link("recommend.html", "맞춤 추천", "recommend", "bi-stars")}
            ${link("mypage.html", "마이페이지", "mypage", "bi-heart")}
            ${user && user.role === "ADMIN" ? link("admin.html", "수집 모니터링", "admin", "bi-speedometer2") : ""}
          </ul>
          <ul class="navbar-nav align-items-lg-center">${right}</ul>
        </div>
      </div>
    </nav>`);

  document.body.insertAdjacentHTML("beforeend", `
    <footer class="np-footer mt-5 py-4"><div class="container d-flex flex-column flex-md-row justify-content-between gap-2">
      <div><b class="text-primary">NomadPick</b> · RPA 기반 개인 맞춤형 여행상품 추천 · 3조(김길동·박미금·이오리·홍기흥)</div>
      <div>상품 정보는 각 여행사 공개 특가 페이지 기준이며, 예약은 원 여행사에서 진행됩니다. 국내선 운항정보: 국토교통부(TAGO)</div>
    </div></footer>`);

  const btn = document.getElementById("np-logout");
  if (btn) btn.addEventListener("click", NP.logout);
};

NP.showOfflineBanner = () => {
  const el = document.getElementById("np-offline");
  if (el) el.classList.remove("d-none");
};

NP.seats = (n) => {
  if (n === null || n === undefined) return "";
  if (n === 0) return ' · <span class="badge text-bg-dark">마감</span>';
  return ` · <span class="${n <= 3 ? "text-danger fw-semibold" : ""}">잔여 ${n}석</span>`;
};

NP.sourceBadge = (p) => (p.source === "sample" ? `<span class="badge text-bg-light border" title="여행사 실사이트가 동적 렌더링·접근 차단되어 내장 샘플 특가 페이지로 수집된 데이터">샘플</span>` : "");

NP.productCard = (p, { favorite = false } = {}) => `
  <div class="np-card-wrap">
    <div class="card np-card">
      <a href="product.html?id=${p.id}" class="text-reset">
        <div class="np-thumb rg-${NP.esc(p.region)}">
          <i class="bi bi-airplane"></i>
          <div><div class="np-region">${NP.esc(p.region)} · ${p.nights ?? "-"}박 ${p.days ?? "-"}일</div><div class="np-city">${NP.esc(p.city || p.region)}</div></div>
        </div>
      </a>
      ${favorite ? `<button class="np-fav" data-fav="${p.id}" title="관심 상품"><i class="bi bi-heart"></i></button>` : ""}
      <div class="card-body d-flex flex-column">
        <div class="d-flex gap-1 mb-2 flex-wrap">
          ${p.discount_rate > 0 ? `<span class="badge np-badge-discount">-${Math.round(p.discount_rate)}%</span>` : ""}
          <span class="badge text-bg-primary-subtle text-primary-emphasis">${NP.esc(p.agency)}</span>
          ${p.theme ? `<span class="badge text-bg-light border">${NP.esc(p.theme)}</span>` : ""}
          ${NP.sourceBadge(p)}
        </div>
        <a href="product.html?id=${p.id}" class="text-reset np-title mb-2">${NP.esc(p.title)}</a>
        <div class="small text-secondary mb-2"><i class="bi bi-calendar-event me-1"></i>${NP.depart(p)}
          ${NP.seats(p.seats_left)}</div>
        <div class="mt-auto">
          ${p.original_price ? `<div class="np-price-org">${NP.won(p.original_price)}</div>` : ""}
          <div class="np-price">${NP.won(p.price)}<small class="fs-6 fw-normal text-secondary">~</small></div>
        </div>
      </div>
    </div>
  </div>`;

NP.bindFavoriteButtons = (root) => {
  root.querySelectorAll("[data-fav]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!NP.requireLogin()) return;
      try {
        await NP.api("/favorites", { method: "POST", body: { product_id: +btn.dataset.fav }, auth: true });
        btn.innerHTML = '<i class="bi bi-heart-fill"></i>';
        NP.toast("관심 상품에 등록했습니다. 가격이 내려가면 마이페이지에 표시됩니다.");
      } catch (err) {
        NP.toast(err.message, "danger");
      }
    });
  });
};
