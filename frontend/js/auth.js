/* SC-01 로그인 / SC-02 회원가입 */
NP.renderLayout("");

const errorBox = document.getElementById("error");
const submitBtn = document.getElementById("submitBtn");

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.classList.remove("d-none");
}

async function submit(path, body) {
  errorBox.classList.add("d-none");
  submitBtn.disabled = true;
  try {
    const res = await NP.api(path, { method: "POST", body });
    NP.auth.save(res);
    const next = NP.param("next");
    if (res.user.role === "ADMIN" && !next) location.href = "admin.html";
    else if (!res.has_preference) location.href = "preferences.html?welcome=1";
    else location.href = next && !next.includes("//") ? next : "recommend.html";
  } catch (e) {
    showError(e.code === "NETWORK" ? "백엔드 서버에 연결할 수 없습니다. (서버 준비 중이면 잠시 후 다시 시도해 주세요)" : e.message);
  } finally {
    submitBtn.disabled = false;
  }
}

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = loginForm.email.value.trim();
    const password = loginForm.password.value;
    if (!email || !password) return showError("이메일과 비밀번호를 입력해 주세요.");
    submit("/auth/login", { email, password });
  });
}

/* 테스트 계정 바로 로그인 (일반 회원 / 읽기 전용 관리자) */
document.querySelectorAll("[data-demo]").forEach((btn) =>
  btn.addEventListener("click", () => submit("/auth/demo-login", { role: btn.dataset.demo })));

/* SNS 로그인: 백엔드 OAuth 시작 주소로 이동 → 로그인 후 이 페이지로 #oauth_token 과 함께 돌아옴 */
const apiAbs = () => (NP_CONFIG.API_BASE.startsWith("/") ? location.origin + NP_CONFIG.API_BASE : NP_CONFIG.API_BASE);
const snsButtons = document.querySelectorAll("[data-sns]");
if (snsButtons.length) {
  NP.api("/auth/oauth/providers").then((on) => snsButtons.forEach((b) => {
    if (!on[b.dataset.sns]) { b.classList.add("np-off"); b.title = "관리자가 OAuth 키를 설정하면 사용할 수 있습니다."; }
  })).catch(() => {});
  snsButtons.forEach((b) => b.addEventListener("click", () => {
    if (b.classList.contains("np-off")) return NP.toast(`${b.textContent.trim().replace("로 계속하기", "")} 로그인은 아직 설정되지 않았습니다. (OAuth 키 필요)`, "secondary");
    const back = location.origin + location.pathname + location.search;
    location.href = `${apiAbs()}/auth/oauth/${b.dataset.sns}/start?return_to=${encodeURIComponent(back)}`;
  }));
}

(async function handleOAuthReturn() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("oauth_error")) { history.replaceState(null, "", location.pathname + location.search); return showError(h.get("oauth_error")); }
  const token = h.get("oauth_token");
  if (!token) return;
  history.replaceState(null, "", location.pathname + location.search);
  try {
    localStorage.setItem("np_token", token);
    const user = await NP.api("/users/me");
    NP.auth.save({ access_token: token, user });
    const next = NP.param("next");
    location.href = h.get("pref") === "1" ? (next && !next.includes("//") ? next : "recommend.html") : "preferences.html?welcome=1";
  } catch (e) {
    NP.auth.clear();
    showError("SNS 로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.");
  }
})();

/* 왼쪽 소개 영역: 실시간 수집 현황 */
if (document.getElementById("stTotal")) {
  NP.api("/meta").then((m) => {
    document.getElementById("stTotal").textContent = `${Number(m.total || 0).toLocaleString("ko-KR")}개`;
    document.getElementById("stUpdated").textContent = m.collected_at ? NP.datetime(m.collected_at) : "-";
  }).catch(() => {});
}

const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const f = signupForm;
    if (!f.name.value.trim()) return showError("이름을 입력해 주세요.");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email.value.trim())) return showError("올바른 이메일을 입력해 주세요.");
    if (f.password.value.length < 8) return showError("비밀번호는 8자 이상이어야 합니다.");
    if (f.password.value !== f.password2.value) return showError("비밀번호 확인이 일치하지 않습니다.");
    submit("/auth/signup", { name: f.name.value.trim(), email: f.email.value.trim(), password: f.password.value });
  });
}
