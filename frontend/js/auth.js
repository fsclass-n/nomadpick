/* SC-01 로그인 / SC-02 회원가입 */
NP.renderLayout("");

const errorBox = document.getElementById("error");
const submitBtn = document.getElementById("submitBtn");

document.querySelectorAll("[data-password-toggle]").forEach((button) => {
  const field = document.getElementById(button.dataset.passwordToggle);
  const label = button.getAttribute("aria-label").replace(" 표시", "");
  button.addEventListener("click", () => {
    const visible = field.type === "password";
    field.type = visible ? "text" : "password";
    button.setAttribute("aria-pressed", String(visible));
    button.setAttribute("aria-label", `${label} ${visible ? "숨기기" : "표시"}`);
    button.innerHTML = `<i class="fa-regular fa-eye${visible ? "-slash" : ""}" aria-hidden="true"></i>`;
  });
});

/* 비밀번호 규칙 - 서버 backend/app/security.py password_problem 과 동일 */
const PW_SPECIALS = "!@#$%^&*()-_=+[]{};:'\",.<>/?\\|`~";
const PW_ORDER = ["length", "chars", "mix", "repeat", "sequence", "email"];
const PW_MESSAGES = {
  length: "비밀번호는 8~20자로 입력해 주세요.",
  chars: "비밀번호는 영문, 숫자, 특수문자만 사용할 수 있습니다. (공백·한글 불가)",
  mix: "비밀번호는 영문, 숫자, 특수문자를 각각 1자 이상 포함해야 합니다.",
  repeat: "같은 문자를 3번 이상 연속해서 사용할 수 없습니다.",
  sequence: "연속된 문자나 숫자(abc, 123 등)를 3자 이상 사용할 수 없습니다.",
  email: "비밀번호에 이메일 아이디를 포함할 수 없습니다.",
};
const hasSequence = (pw) => {
  const s = pw.toLowerCase();
  for (let i = 0; i + 2 < s.length; i += 1) {
    const c = s.slice(i, i + 3);
    if (!/^(\d{3}|[a-z]{3})$/.test(c)) continue;
    const d1 = c.charCodeAt(1) - c.charCodeAt(0);
    if (Math.abs(d1) === 1 && c.charCodeAt(2) - c.charCodeAt(1) === d1) return true;
  }
  return false;
};
NP.passwordChecks = (pw, email = "") => {
  const local = email.split("@")[0].toLowerCase();
  const filled = pw.length > 0;
  return {
    length: pw.length >= 8 && pw.length <= 20,
    chars: filled && [...pw].every((c) => /[A-Za-z0-9]/.test(c) || PW_SPECIALS.includes(c)),
    mix: /[A-Za-z]/.test(pw) && /\d/.test(pw) && [...pw].some((c) => PW_SPECIALS.includes(c)),
    repeat: filled && !/(.)\1\1/.test(pw),
    sequence: filled && !hasSequence(pw),
    email: filled && !(local.length >= 4 && pw.toLowerCase().includes(local)),
  };
};

/* Caps Lock 안내 (로그인·회원가입 공통) */
document.querySelectorAll("[data-caps-for]").forEach((note) => {
  const field = document.getElementById(note.dataset.capsFor);
  const update = (e) => note.classList.toggle("d-none", !e.getModifierState?.("CapsLock"));
  field.addEventListener("keydown", update);
  field.addEventListener("keyup", update);
  field.addEventListener("blur", () => note.classList.add("d-none"));
});

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
  const f = signupForm;
  const rules = document.querySelectorAll("#pwRules [data-rule]");
  const meter = document.getElementById("pwStrength");
  const match = document.getElementById("pwMatch");
  const LEVELS = [["", "-"], ["weak", "위험"], ["fair", "보통"], ["strong", "안전"]];
  const refresh = () => {
    const pw = f.password.value;
    const checks = NP.passwordChecks(pw, f.email.value.trim());
    rules.forEach((li) => {
      li.classList.toggle("ok", checks[li.dataset.rule]);
      li.classList.toggle("bad", pw.length > 0 && !checks[li.dataset.rule]);
    });
    const valid = PW_ORDER.every((k) => checks[k]);
    const level = !pw ? 0 : !valid ? 1 : pw.length >= 12 || (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) ? 3 : 2;
    meter.dataset.level = LEVELS[level][0];
    meter.querySelector("em").textContent = LEVELS[level][1];
    f.password.setAttribute("aria-invalid", String(pw.length > 0 && !valid));
    const p2 = f.password2.value;
    match.className = `np-pw-match${p2 ? (p2 === pw ? " ok" : " bad") : ""}`;
    match.innerHTML = !p2 ? "" : p2 === pw
      ? '<i class="fa-solid fa-circle-check" aria-hidden="true"></i>비밀번호가 일치합니다.'
      : '<i class="fa-solid fa-circle-xmark" aria-hidden="true"></i>비밀번호가 일치하지 않습니다.';
  };
  [f.password, f.password2, f.email].forEach((el) => el.addEventListener("input", refresh));
  refresh();

  signupForm.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!f.name.value.trim()) return showError("이름을 입력해 주세요.");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email.value.trim())) return showError("올바른 이메일을 입력해 주세요.");
    const checks = NP.passwordChecks(f.password.value, f.email.value.trim());
    const failed = PW_ORDER.find((k) => !checks[k]);
    if (failed) { f.password.focus(); return showError(PW_MESSAGES[failed]); }
    if (f.password.value !== f.password2.value) { f.password2.focus(); return showError("비밀번호 확인이 일치하지 않습니다."); }
    submit("/auth/signup", { name: f.name.value.trim(), email: f.email.value.trim(), password: f.password.value });
  });
}
