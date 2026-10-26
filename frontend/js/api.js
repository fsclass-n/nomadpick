/* API 통신 · 인증 토큰 · 오프라인(샘플 데이터) 대체 */
window.NP = window.NP || {};

class ApiError extends Error {
  constructor(message, status = 0, code = "ERROR") {
    super(message);
    this.status = status;
    this.code = code;
  }
}
NP.ApiError = ApiError;

NP.auth = {
  token: () => localStorage.getItem("np_token"),
  user: () => JSON.parse(localStorage.getItem("np_user") || "null"),
  save(res) {
    localStorage.setItem("np_token", res.access_token);
    localStorage.setItem("np_user", JSON.stringify(res.user));
  },
  clear() {
    localStorage.removeItem("np_token");
    localStorage.removeItem("np_user");
  },
  isLoggedIn: () => !!localStorage.getItem("np_token"),
  isAdmin: () => (NP.auth.user() || {}).role === "ADMIN",
};

NP.qs = (params = {}) => {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.append(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
};

NP.api = async (path, { method = "GET", body, auth = false, raw = false, params } = {}) => {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = NP.auth.token();
  if (token) headers.Authorization = `Bearer ${token}`;

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), NP_CONFIG.REQUEST_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(`${NP_CONFIG.API_BASE}${path}${NP.qs(params)}`, {
      method, headers, body: body !== undefined ? JSON.stringify(body) : undefined, signal: ctrl.signal,
    });
  } catch (e) {
    throw new ApiError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", 0, "NETWORK");
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 401 && auth) {
    NP.auth.clear();
    location.href = `login.html?next=${encodeURIComponent(location.pathname.split("/").pop() + location.search)}`;
    throw new ApiError("로그인이 필요합니다.", 401, "UNAUTHORIZED");
  }
  if (!res.ok) {
    let err = {};
    try { err = await res.json(); } catch (_) { /* empty */ }
    throw new ApiError(err.message || `요청 실패 (${res.status})`, res.status, err.code || "ERROR");
  }
  if (raw) return res;
  return res.status === 204 ? null : res.json();
};

/* ---------- 오프라인 대체: 백엔드 미연결(1단계 Netlify) 또는 Render 슬립 시 샘플 데이터 ---------- */
NP.offline = false;
NP.sample = {
  _data: null,
  async load() {
    if (!this._data) this._data = await (await fetch(NP_CONFIG.SAMPLE_DATA)).json();
    return this._data;
  },
  async meta() {
    const d = await this.load();
    return d.meta;
  },
  async products(p = {}) {
    const d = await this.load();
    let items = d.products.slice();
    if (p.region) { const rs = p.region.split(","); items = items.filter((x) => rs.includes(x.region)); }
    if (p.price_max) items = items.filter((x) => x.price <= +p.price_max);
    if (p.month) items = items.filter((x) => x.depart_date.slice(0, 7) <= p.month && (x.depart_end || x.depart_date).slice(0, 7) >= p.month);
    if (p.agency) items = items.filter((x) => x.agency_code === p.agency || String(x.agency_id) === String(p.agency));
    if (p.theme) items = items.filter((x) => x.theme === p.theme);
    if (p.q) items = items.filter((x) => x.title.includes(p.q) || (x.city || "").includes(p.q));
    const sorters = {
      discount: (a, b) => b.discount_rate - a.discount_rate || a.price - b.price,
      price: (a, b) => a.price - b.price,
      depart: (a, b) => a.depart_date.localeCompare(b.depart_date),
    };
    items.sort(sorters[p.sort || "discount"]);
    const page = +p.page || 1, size = +p.size || 20;
    return { total: items.length, page, size, collected_at: d.meta.collected_at, items: items.slice((page - 1) * size, page * size) };
  },
  async product(id) {
    const d = await this.load();
    const p = d.products.find((x) => String(x.id) === String(id));
    if (!p) throw new ApiError("상품을 찾을 수 없습니다.", 404, "PRODUCT_NOT_FOUND");
    return { ...p, flights: (d.flights || {})[p.id] || [], is_favorite: false, previous_price: null };
  },
  async prices(id) {
    const d = await this.load();
    return { product_id: id, items: (d.prices || {})[id] || [] };
  },
};

/** 공개 조회 API: 서버 연결 실패(네트워크·5xx) 시 샘플 데이터로 대체 */
NP.publicGet = async (path, params, fallback) => {
  try {
    return await NP.api(path, { params });
  } catch (e) {
    if (e.status === 0 || e.status >= 500) {
      NP.offline = true;
      NP.showOfflineBanner && NP.showOfflineBanner();
      return fallback();
    }
    throw e;
  }
};
