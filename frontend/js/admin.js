/* SC-08 관리자 수집 모니터링 */
NP.renderLayout("admin");

const STATUS = {
  SUCCESS: "text-bg-success", WARN: "text-bg-warning", FAIL: "text-bg-danger", SKIPPED: "text-bg-secondary", NONE: "text-bg-light border",
};
const badge = (s) => `<span class="badge ${STATUS[s] || "text-bg-light"}">${s}</span>`;

async function loadStats() {
  const d = await NP.api("/admin/rpa-logs", { auth: true, params: { days: 7 } });
  document.getElementById("kRuns").textContent = `${d.summary.today_runs}회`;
  document.getElementById("kCollected").textContent = `${d.summary.today_collected.toLocaleString()}건`;
  document.getElementById("kSuccess").textContent = `${d.summary.success_rate}%`;
  const fail = document.getElementById("kFail");
  fail.textContent = `${d.summary.parse_fail_rate}%`;
  fail.className = `value ${d.summary.parse_fail_rate > 20 ? "text-danger" : ""}`;

  document.getElementById("agencyRows").innerHTML = d.agencies.map((a) => `
    <tr><td class="fw-semibold">${NP.esc(a.name)}</td><td>${NP.datetime(a.last_run)}</td><td>${badge(a.status)} ${a.source === "sample" ? '<span class="badge text-bg-light border">sample</span>' : ""}</td>
    <td class="text-end">${a.collected.toLocaleString()}</td><td class="text-end">${a.failed}</td><td class="text-end">${a.success_rate}%</td></tr>`).join("");

  document.getElementById("logRows").innerHTML = d.logs.map((l) => `
    <tr><td class="text-nowrap">${NP.datetime(l.started_at)}</td><td class="text-nowrap">${l.job_name}</td><td class="text-nowrap">${NP.esc(l.agency)}</td><td>${badge(l.status)}</td>
    <td>${l.source || "-"}</td><td class="text-end">${l.collected}</td><td class="text-end">${l.failed}</td><td class="text-end">${l.retries}</td>
    <td class="small text-secondary" style="min-width:260px">${NP.esc(l.message || "")}</td></tr>`).join("")
    || '<tr><td colspan="9" class="text-center text-secondary py-4">실행 이력이 없습니다.</td></tr>';

  Plotly.newPlot("dailyChart", [
    { x: d.daily.map((x) => x.date), y: d.daily.map((x) => x.collected), type: "bar", name: "수집", marker: { color: "#0d6efd" } },
    { x: d.daily.map((x) => x.date), y: d.daily.map((x) => x.failed), type: "bar", name: "실패", marker: { color: "#fd7e14" } },
  ], { barmode: "stack", margin: { l: 50, r: 10, t: 10, b: 40 }, legend: { orientation: "h", y: -0.2 }, xaxis: { type: "category" }, font: { family: "Pretendard, sans-serif" } },
  { displayModeBar: false, responsive: true });
}

async function loadReports() {
  const rows = await NP.api("/admin/reports", { auth: true });
  const box = document.getElementById("reports");
  box.innerHTML = rows.map((r) => `
    <li class="list-group-item d-flex justify-content-between align-items-center px-0">
      <div><b>${r.report_date}</b><div class="small text-secondary">${r.summary ? `${r.summary.total}건 · 평균 할인 ${r.summary.avg_discount}%` : ""}</div></div>
      <div class="btn-group btn-group-sm">
        <button class="btn btn-outline-success" data-xlsx="${r.report_date}"><i class="bi bi-file-earmark-excel"></i></button>
        <button class="btn btn-outline-primary" data-html="${r.report_date}"><i class="bi bi-bar-chart"></i></button>
      </div></li>`).join("") || '<li class="list-group-item text-secondary px-0">생성된 리포트가 없습니다. (매일 21:30 자동 생성)</li>';
  box.querySelectorAll("[data-xlsx]").forEach((b) => b.addEventListener("click", () =>
    NP.download(`/admin/reports/${b.dataset.xlsx}`, `nomadpick_daily_${b.dataset.xlsx}.xlsx`).catch((e) => NP.toast(e.message, "danger"))));
  box.querySelectorAll("[data-html]").forEach((b) => b.addEventListener("click", async () => {
    const win = window.open("", "_blank");
    const res = await NP.api(`/admin/reports/${b.dataset.html}`, { auth: true, raw: true, params: { format: "html" } });
    const url = URL.createObjectURL(new Blob([await res.text()], { type: "text/html" }));
    win.location.href = url;
  }));
}

document.querySelectorAll("[data-run]").forEach((b) => b.addEventListener("click", async () => {
  b.disabled = true;
  try {
    await NP.api("/admin/rpa/run", { method: "POST", auth: true, params: { job: b.dataset.run } });
    NP.toast("RPA 작업을 시작했습니다. 잠시 후 새로고침합니다.", "success");
    setTimeout(() => { loadStats(); loadReports(); }, 8000);
  } catch (e) {
    NP.toast(e.message, "danger");
  } finally {
    setTimeout(() => { b.disabled = false; }, 8000);
  }
}));

/* 회원 권한 관리 */
const members = { page: 1, size: 20, total: 0 };
const ROLE_LABEL = { ADMIN: '<span class="badge text-bg-primary">관리자</span>', USER: '<span class="badge text-bg-light border">일반 회원</span>' };
const roleModal = new bootstrap.Modal(document.getElementById("roleModal"));
let pendingRole = null;

async function loadMembers() {
  const d = await NP.api("/admin/users", { auth: true, params: {
    q: document.getElementById("memberQ").value.trim(), role: document.getElementById("memberRole").value, page: members.page, size: members.size } });
  members.total = d.total;
  document.getElementById("memberReadOnly").classList.toggle("d-none", !d.read_only);
  document.getElementById("adminCount").textContent = `(현재 관리자 ${d.admin_count}명)`;
  document.getElementById("memberRows").innerHTML = d.items.map((u) => {
    const next = u.role === "ADMIN" ? "USER" : "ADMIN";
    const action = d.read_only || u.locked
      ? `<span class="small text-secondary" title="${NP.esc(u.locked || "체험 관리자는 조회만 가능합니다.")}"><i class="bi bi-lock"></i> ${u.locked ? "변경 불가" : "조회 전용"}</span>`
      : `<button class="btn btn-sm ${next === "ADMIN" ? "btn-outline-primary" : "btn-outline-danger"}" data-uid="${u.id}" data-role="${next}"
           data-name="${NP.esc(u.name)}" data-email="${NP.esc(u.email)}">${next === "ADMIN" ? "관리자 지정" : "관리자 해제"}</button>`;
    return `<tr><td class="fw-semibold text-nowrap">${NP.esc(u.name)}</td><td class="text-nowrap">${NP.esc(u.email)}</td><td class="text-nowrap">${u.created_at ? u.created_at.slice(0, 10) : "-"}</td>
      <td>${ROLE_LABEL[u.role] || NP.esc(u.role)}</td><td class="text-end">${action}</td></tr>`;
  }).join("") || '<tr><td colspan="5" class="text-center text-secondary py-4">검색 결과가 없습니다.</td></tr>';
  const last = Math.max(1, Math.ceil(d.total / members.size));
  document.getElementById("memberInfo").textContent = `총 ${d.total.toLocaleString()}명 · ${members.page}/${last} 페이지`;
  document.getElementById("memberPrev").disabled = members.page <= 1;
  document.getElementById("memberNext").disabled = members.page >= last;
}

document.getElementById("memberSearch").addEventListener("submit", (e) => { e.preventDefault(); members.page = 1; loadMembers().catch((er) => NP.toast(er.message, "danger")); });
document.getElementById("memberRole").addEventListener("change", () => { members.page = 1; loadMembers().catch((er) => NP.toast(er.message, "danger")); });
document.getElementById("memberPrev").addEventListener("click", () => { members.page -= 1; loadMembers().catch((er) => NP.toast(er.message, "danger")); });
document.getElementById("memberNext").addEventListener("click", () => { members.page += 1; loadMembers().catch((er) => NP.toast(er.message, "danger")); });
document.getElementById("memberRows").addEventListener("click", (e) => {
  const b = e.target.closest("[data-uid]");
  if (!b) return;
  pendingRole = { id: b.dataset.uid, role: b.dataset.role };
  const toAdmin = b.dataset.role === "ADMIN";
  document.getElementById("roleModalTitle").textContent = toAdmin ? "관리자 지정" : "관리자 해제";
  document.getElementById("roleModalBody").innerHTML = `<p class="mb-2"><b>${NP.esc(b.dataset.name)}</b> (${NP.esc(b.dataset.email)}) 님을
    <b>${toAdmin ? "관리자로 지정" : "일반 회원으로 변경"}</b>하시겠습니까?</p>
    <p class="small text-secondary mb-0">${toAdmin ? "관리자는 수집 모니터링, 리포트, RPA 수동 실행, 회원 권한 변경을 할 수 있습니다." : "관리자 화면과 관리자 API를 즉시 사용할 수 없게 됩니다."}</p>`;
  const ok = document.getElementById("roleConfirm");
  ok.className = `btn ${toAdmin ? "btn-primary" : "btn-danger"}`;
  ok.textContent = toAdmin ? "관리자로 지정" : "권한 해제";
  roleModal.show();
});
document.getElementById("roleConfirm").addEventListener("click", async (e) => {
  const btn = e.currentTarget;  // await 이후에는 e.currentTarget 이 null
  if (!pendingRole) return;
  btn.disabled = true;
  try {
    const u = await NP.api(`/admin/users/${pendingRole.id}/role`, { method: "PATCH", auth: true, body: { role: pendingRole.role } });
    NP.toast(`${u.name} 님의 권한을 ${u.role === "ADMIN" ? "관리자" : "일반 회원"}(으)로 변경했습니다.`, "success");
    roleModal.hide();
    await loadMembers();
  } catch (er) {
    NP.toast(er.message, "danger");
  } finally {
    btn.disabled = false;
    pendingRole = null;
  }
});

(async () => {
  if (!NP.requireLogin()) return;
  try {  // 권한이 바뀌었을 수 있으므로 서버 기준으로 다시 확인
    const me = await NP.api("/users/me", { auth: true });
    NP.auth.save({ access_token: NP.auth.token(), user: me });
  } catch (_) { /* 오프라인이면 저장된 정보 사용 */ }
  if (!NP.auth.isAdmin()) {
    document.querySelector("main").innerHTML = '<div class="alert alert-warning">관리자만 접근할 수 있습니다.</div>';
    return;
  }
  try {
    await Promise.all([loadStats(), loadReports(), loadMembers()]);
  } catch (e) {
    NP.toast(e.message, "danger");
  }
})();
