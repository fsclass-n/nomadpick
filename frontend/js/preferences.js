/* SC-03 선호 설정 */
NP.renderLayout("");

const REGIONS = ["일본", "동남아", "중화권", "대양주", "유럽", "미주", "국내"];
const THEMES = ["휴양", "관광", "골프", "효도", "자유여행"];
const COMPANIONS = ["혼자", "친구", "연인", "가족"];

const $ = (id) => document.getElementById(id);

function chips(containerId, name, values, type = "checkbox") {
  $(containerId).innerHTML = values.map((v, i) => {
    const [value, label] = Array.isArray(v) ? v : [v, v];
    return `<input type="${type}" class="btn-check" name="${name}" id="${name}${i}" value="${value}" autocomplete="off">
            <label class="btn btn-outline-primary" for="${name}${i}">${label}</label>`;
  }).join("");
}

function months(n = 8) {
  const d = new Date();
  return Array.from({ length: n }, (_, i) => {
    const m = new Date(d.getFullYear(), d.getMonth() + i, 1);
    const v = `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, "0")}`;
    return [v, `${m.getMonth() + 1}월${m.getFullYear() !== d.getFullYear() ? ` (${m.getFullYear()})` : ""}`];
  });
}

function checked(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((el) => el.value);
}

function setChecked(name, values) {
  document.querySelectorAll(`input[name="${name}"]`).forEach((el) => { el.checked = (values || []).includes(el.value); });
}

function syncBudget(e) {
  let lo = +$("budgetMin").value;
  let hi = +$("budgetMax").value;
  if (lo > hi) {
    if (e && e.target.id === "budgetMin") hi = lo; else lo = hi;
    $("budgetMin").value = lo;
    $("budgetMax").value = hi;
  }
  $("budgetMinLabel").textContent = NP.manwon(lo);
  $("budgetMaxLabel").textContent = NP.manwon(hi);
}

async function init() {
  if (!NP.requireLogin()) return;
  if (NP.param("welcome")) $("welcome").classList.remove("d-none");
  chips("regions", "region", REGIONS);
  chips("months", "month", months());
  chips("themes", "theme", THEMES, "radio");
  chips("companions", "companion", COMPANIONS, "radio");
  const nights = Array.from({ length: 11 }, (_, i) => `<option value="${i}">${i}</option>`).join("");
  $("nightsMin").innerHTML = nights;
  $("nightsMax").innerHTML = nights;
  $("nightsMin").value = 2;
  $("nightsMax").value = 5;
  ["budgetMin", "budgetMax"].forEach((id) => $(id).addEventListener("input", syncBudget));

  try {
    const p = await NP.api("/preferences", { auth: true });
    if (p) {
      setChecked("region", p.regions);
      setChecked("month", p.depart_months);
      setChecked("theme", [p.theme]);
      setChecked("companion", [p.companion]);
      if (p.budget_min !== null) $("budgetMin").value = p.budget_min;
      if (p.budget_max !== null) $("budgetMax").value = p.budget_max;
      if (p.nights_min !== null) $("nightsMin").value = p.nights_min;
      if (p.nights_max !== null) $("nightsMax").value = p.nights_max;
    }
  } catch (e) {
    NP.toast(e.message, "danger");
  }
  syncBudget();
}

$("prefForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    regions: checked("region"),
    depart_months: checked("month"),
    theme: checked("theme")[0] || null,
    companion: checked("companion")[0] || null,
    budget_min: +$("budgetMin").value,
    budget_max: +$("budgetMax").value,
    nights_min: +$("nightsMin").value,
    nights_max: +$("nightsMax").value,
  };
  if (!body.regions.length) return NP.toast("여행 지역을 1개 이상 선택해 주세요.", "warning");
  $("saveBtn").disabled = true;
  try {
    await NP.api("/preferences", { method: "PUT", body, auth: true });
    location.href = "recommend.html";
  } catch (err) {
    NP.toast(err.message, "danger");
  } finally {
    $("saveBtn").disabled = false;
  }
});

init();
