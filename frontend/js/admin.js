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

(async () => {
  if (!NP.requireLogin()) return;
  if (!NP.auth.isAdmin()) {
    document.querySelector("main").innerHTML = '<div class="alert alert-warning">관리자만 접근할 수 있습니다.</div>';
    return;
  }
  try {
    await Promise.all([loadStats(), loadReports()]);
  } catch (e) {
    NP.toast(e.message, "danger");
  }
})();
