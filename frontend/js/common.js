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
    `<li class="nav-item"><a class="nav-link ${active === key ? "active" : ""}" href="${href}"${active === key ? ' aria-current="page"' : ""}><i class="bi ${icon} me-1"></i>${label}</a></li>`;
  const right = user
    ? `<li class="nav-item dropdown">
         <a class="nav-link dropdown-toggle np-user-btn" href="#" data-bs-toggle="dropdown">
           <span class="np-avatar-sm">${NP.esc((user.name || "?").slice(0, 1))}</span>${NP.esc(user.name)}</a>
         <ul class="dropdown-menu dropdown-menu-end np-user-menu">
           <li class="px-3 py-2 small text-secondary">${user.role === "ADMIN" ? "관리자 계정" : "반가워요, " + NP.esc(user.name) + "님"}</li>
           <li><a class="dropdown-item" href="preferences.html"><i class="bi bi-sliders me-2"></i>선호 설정</a></li>
           <li><a class="dropdown-item" href="mypage.html"><i class="bi bi-heart me-2"></i>마이페이지</a></li>
           <li><hr class="dropdown-divider"></li>
           <li><button class="dropdown-item" id="np-logout"><i class="bi bi-box-arrow-right me-2"></i>로그아웃</button></li>
         </ul></li>`
    : `<li class="nav-item"><a class="nav-link np-login-link" href="login.html"><i class="bi bi-person me-1"></i>로그인</a></li>
       <li class="nav-item"><a class="btn np-signup-btn ms-lg-2" href="signup.html">회원가입</a></li>`;

  document.body.insertAdjacentHTML("afterbegin", `
    <div id="np-offline" class="np-offline small py-2 d-none"><div class="container">
      <i class="bi bi-wifi-off me-1"></i>백엔드 서버에 연결하지 못해 <b>오프라인 데모 데이터</b>를 표시하고 있습니다.
      (Render 무료 인스턴스는 첫 접속 시 깨어나는 데 최대 1분이 걸릴 수 있습니다)
      <a href="#" onclick="location.reload();return false;" class="ms-2">다시 시도</a></div></div>
    <nav class="navbar navbar-expand-lg np-navbar sticky-top">
      <div class="container">
        <a class="navbar-brand np-brand" href="index.html"><i class="bi bi-compass-fill"></i>NomadPick</a>
        <button class="np-burger d-lg-none" id="npBurger" type="button" aria-label="메뉴 열기" aria-controls="npDrawer" aria-expanded="false">
          <span></span><span></span><span></span></button>
        <div class="collapse navbar-collapse" id="npNav">
          <ul class="navbar-nav mx-auto np-main-nav">
            ${link("index.html", "오늘의 특가", "index", "bi-lightning-charge")}
            ${link("recommend.html", "맞춤 추천", "recommend", "bi-stars")}
            ${link("mypage.html", "마이페이지", "mypage", "bi-heart")}
            ${user && user.role === "ADMIN" ? link("admin.html", "수집 모니터링", "admin", "bi-speedometer2") : ""}
          </ul>
          <ul class="navbar-nav align-items-lg-center">${right}</ul>
        </div>
      </div>
      ${NP.drawerHtml(active, user)}
    </nav>`);

  document.body.insertAdjacentHTML("beforeend", `
    <footer class="np-footer mt-5">
      <div class="container">
        <div class="np-footer-top">
          <div class="np-footer-brand">
            <a class="np-footer-logo np-display" href="index.html"><i class="bi bi-compass-fill me-1"></i>NomadPick</a>
            <p>RPA 기반 개인 맞춤형 여행상품 추천 서비스.<br>여러 여행사의 특가를 30분마다 모아 내 취향에 맞게 골라 드립니다.</p>
            <div class="np-footer-social">
              <a href="https://github.com/fsclass-n/nomadpick" target="_blank" rel="noopener" aria-label="GitHub"><i class="bi bi-github"></i></a>
              <a href="https://fsclass-n.github.io/nomadpick/" target="_blank" rel="noopener" aria-label="프로젝트 소개"><i class="bi bi-play-circle"></i></a>
              <a href="https://nomadpick.onrender.com/docs" target="_blank" rel="noopener" aria-label="API 문서"><i class="bi bi-code-slash"></i></a>
            </div>
          </div>
          <div class="np-footer-col"><h6>서비스</h6>
            <a href="index.html">오늘의 특가</a><a href="recommend.html">맞춤 추천</a><a href="preferences.html">선호 설정</a><a href="mypage.html">마이페이지</a></div>
          <div class="np-footer-col"><h6>제휴 여행사</h6>
            <a href="https://www.hanatour.com/" target="_blank" rel="noopener">하나투어</a><a href="https://www.modetour.com/" target="_blank" rel="noopener">모두투어</a>
            <a href="https://www.ybtour.co.kr/" target="_blank" rel="noopener">노랑풍선</a></div>
          <div class="np-footer-col"><h6>프로젝트</h6>
            <a href="https://fsclass-n.github.io/nomadpick/" target="_blank" rel="noopener">소개 · 시연 영상</a>
            <a href="https://github.com/fsclass-n/nomadpick" target="_blank" rel="noopener">GitHub</a>
            <a href="https://nomadpick.onrender.com/docs" target="_blank" rel="noopener">API 문서</a></div>
          <div class="np-footer-col np-footer-info"><h6>데이터 안내</h6>
            <p><i class="bi bi-robot"></i> 특가 30분 주기 자동 수집</p>
            <p><i class="bi bi-airplane"></i> 국내선 운항정보: 국토교통부(TAGO)</p>
            <p><i class="bi bi-shield-check"></i> 예약·결제는 각 여행사에서 진행</p></div>
        </div>
        <div class="np-footer-bottom">
          <span>© 2026 NomadPick · Semi-Project 3조 (김길동 · 박미금 · 이오리 · 홍기흥)</span>
          <span>상품 정보는 각 여행사 공개 특가 페이지 기준이며, 실제 가격·좌석은 여행사 사이트에서 확인해 주세요.</span>
        </div>
      </div>
    </footer>
    <button type="button" class="np-totop" id="npTop" aria-label="맨 위로 이동">
      <svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="21"/></svg>
      <i class="bi bi-arrow-up"></i><span>TOP</span>
    </button>`);

  document.querySelectorAll("#np-logout, #np-drawer-logout").forEach((b) => b.addEventListener("click", NP.logout));
  NP.initDrawer();
  NP.initScrollUi();
};

/* 스크롤: 헤더 그림자 · 맨 위로 버튼(진행률 링) */
NP.initScrollUi = () => {
  const nav = document.querySelector(".np-navbar");
  const top = document.getElementById("npTop");
  const ring = top && top.querySelector("circle");
  const len = ring ? 2 * Math.PI * 21 : 0;
  if (ring) ring.style.strokeDasharray = `${len}`;
  let ticking = false;
  const update = () => {
    const y = window.scrollY;
    const max = document.documentElement.scrollHeight - innerHeight;
    if (nav) nav.classList.toggle("np-scrolled", y > 8);
    if (top) {
      top.classList.toggle("show", y > 400);
      ring.style.strokeDashoffset = `${len * (1 - (max > 0 ? Math.min(y / max, 1) : 0))}`;
    }
    ticking = false;
  };
  window.addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  if (top) top.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  update();
};

/* 모바일 메뉴: 햄버거(≡ ↔ ✕ 모핑) + 오른쪽에서 슬라이드되는 드로어 */
NP.drawerHtml = (active, user) => {
  const items = [
    ["index.html", "index", "bi-lightning-charge-fill", "오늘의 특가", "3개 여행사 특가를 한눈에"],
    ["recommend.html", "recommend", "bi-stars", "맞춤 추천", "내 취향 Top 10 + 추천 이유"],
    ["mypage.html", "mypage", "bi-heart-fill", "마이페이지", "관심 상품 · 가격 하락 알림"],
    ...(user && user.role === "ADMIN" ? [["admin.html", "admin", "bi-speedometer2", "수집 모니터링", "RPA 수집 현황 · 리포트"]] : []),
  ];
  const menu = items.map(([href, key, icon, label, desc], i) => `
    <li style="--i:${i}"><a class="${active === key ? "active" : ""}" href="${href}">
      <span class="np-dm-icon"><i class="bi ${icon}"></i></span>
      <span class="np-dm-text"><b>${label}</b><small>${desc}</small></span>
      <i class="bi bi-chevron-right np-dm-arrow"></i></a></li>`).join("");
  const head = user
    ? `<div class="np-drawer-user"><span class="np-avatar">${NP.esc((user.name || "?").slice(0, 1))}</span>
         <div><b>${NP.esc(user.name)}님</b><small>${user.role === "ADMIN" ? "관리자" : "반가워요! 오늘의 특가를 확인해 보세요"}</small></div></div>`
    : `<div class="np-drawer-guest"><b>로그인하고 맞춤 추천을 받아보세요</b>
         <div class="d-flex gap-2 mt-3"><a class="btn btn-light flex-fill" href="login.html">로그인</a>
         <a class="btn btn-warning flex-fill fw-semibold" href="signup.html">회원가입</a></div></div>`;
  const sub = user
    ? `<ul class="np-drawer-sub" style="--i:${items.length}">
         <li><a href="preferences.html"><i class="bi bi-sliders"></i>선호 설정</a></li>
         <li><button type="button" id="np-drawer-logout"><i class="bi bi-box-arrow-right"></i>로그아웃</button></li></ul>`
    : "";
  return `
    <div class="np-drawer-backdrop" id="npBackdrop"></div>
    <aside class="np-drawer" id="npDrawer" aria-hidden="true" aria-label="전체 메뉴">
      <div class="np-drawer-top">
        <a class="np-drawer-brand np-display" href="index.html"><i class="bi bi-compass-fill me-1"></i>NomadPick</a>
        ${head}
      </div>
      <ul class="np-drawer-menu">${menu}</ul>
      ${sub}
      <div class="np-drawer-foot"><i class="bi bi-robot me-1"></i>RPA가 30분마다 특가를 업데이트합니다</div>
    </aside>`;
};

NP.initDrawer = () => {
  const burger = document.getElementById("npBurger");
  const drawer = document.getElementById("npDrawer");
  const backdrop = document.getElementById("npBackdrop");
  if (!burger || !drawer) return;
  const root = document.documentElement;
  const set = (open) => {
    root.classList.toggle("np-menu-open", open);
    burger.setAttribute("aria-expanded", String(open));
    burger.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
    drawer.setAttribute("aria-hidden", String(!open));
  };
  burger.addEventListener("click", () => set(!root.classList.contains("np-menu-open")));
  backdrop.addEventListener("click", () => set(false));
  drawer.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => set(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") set(false); });
  window.matchMedia("(min-width: 992px)").addEventListener("change", (e) => { if (e.matches) set(false); });
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

/** 여행사 상품 이미지(있을 때만). 불러오기 실패 시 이미지를 지워 지역 그라데이션 썸네일로 돌아간다. */
NP.thumbImg = (p) => (/^https?:\/\//.test(p.image_url || "")
  ? `<img class="np-thumb-img" src="${NP.esc(p.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer"
      onerror="this.parentNode.classList.remove('has-img');this.remove()">` : "");
NP.thumbClass = (p) => `np-thumb rg-${NP.esc(p.region)}${NP.thumbImg(p) ? " has-img" : ""}`;

NP.sourceBadge = (p) => (p.source === "sample" ? `<span class="badge text-bg-light border" title="여행사 실사이트가 동적 렌더링·접근 차단되어 내장 샘플 특가 페이지로 수집된 데이터">샘플</span>` : "");

NP.productCard = (p, { favorite = false } = {}) => `
  <div class="np-card-wrap">
    <div class="card np-card">
      <a href="product.html?id=${p.id}" class="text-reset">
        <div class="${NP.thumbClass(p)}">
          ${NP.thumbImg(p)}<i class="bi bi-airplane"></i>
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
