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
