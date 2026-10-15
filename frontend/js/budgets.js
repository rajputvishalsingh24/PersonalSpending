/**
 * SpendSense Budgets & Drift Controller
 */

let cachedBudgets = [];
let availableCategories = [];

document.addEventListener("DOMContentLoaded", async () => {
  await loadCategories();
  await loadBudgets();

  // Modal controls
  document.getElementById("btn-open-create-budget").addEventListener("click", () => openBudgetModal());
  document.getElementById("btn-close-budget-modal").addEventListener("click", closeBudgetModal);
  document.getElementById("btn-cancel-budget-modal").addEventListener("click", closeBudgetModal);
  document.getElementById("btn-save-budget").addEventListener("click", saveBudget);
});

async function loadCategories() {
  try {
    const settings = await api.get("/api/settings");
    const expenseCats = (settings.categories || []).filter(c => c.category_type === "expense");
    availableCategories = expenseCats.map(c => c.category_name);

    const select = document.getElementById("modal-budget-category");
    select.innerHTML = `
      <option value="__overall__">Overall Monthly Spend</option>
      ${availableCategories.map(c => `<option value="${c}">${c}</option>`).join("")}
    `;
  } catch (err) {
    console.error("Failed to load categories for budget:", err);
  }
}

async function loadBudgets() {
  try {
    cachedBudgets = await api.get("/api/budgets");
    renderBudgets(cachedBudgets);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderBudgets(budgets) {
  const overallCard = document.getElementById("overall-budget-card");
  const overallBudget = budgets.find(b => b.category === "__overall__");

  if (overallBudget) {
    document.getElementById("overall-budget-amt").innerText = formatCurrency(overallBudget.budget_amount);
    document.getElementById("overall-remaining").innerText = `${formatCurrency(overallBudget.remaining_budget)} remaining`;
    document.getElementById("overall-spent-label").innerText = `${formatCurrency(overallBudget.actual_spending)} spent`;
    document.getElementById("overall-utilization-label").innerText = `${overallBudget.utilization_pct}% Utilized`;

    const bar = document.getElementById("overall-progress-bar");
    const clampedPct = Math.min(100, Math.max(0, overallBudget.utilization_pct));
    bar.style.width = `${clampedPct}%`;

    const statusPill = document.getElementById("overall-status-pill");
    statusPill.innerText = overallBudget.status;
    if (overallBudget.status === "Over Budget") {
      statusPill.className = "px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200";
      bar.className = "h-3 rounded-full bg-rose-600 progress-bar-fill";
    } else if (overallBudget.status === "Approaching Limit") {
      statusPill.className = "px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200";
      bar.className = "h-3 rounded-full bg-amber-500 progress-bar-fill";
    } else {
      statusPill.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200";
      bar.className = "h-3 rounded-full bg-emerald-600 progress-bar-fill";
    }

    const totalDays = overallBudget.days_elapsed + overallBudget.days_remaining;
    const timePct = Math.round((overallBudget.days_elapsed / totalDays) * 100);
    document.getElementById("time-pacing-label").innerText = `Day ${overallBudget.days_elapsed} of ${totalDays} (${timePct}% of month elapsed)`;

    const driftEl = document.getElementById("overall-drift-alert");
    driftEl.innerText = overallBudget.drift_alert || (overallBudget.projected_spend ? `Projected: ${formatCurrency(overallBudget.projected_spend)}` : '');
  } else {
    document.getElementById("overall-budget-amt").innerText = "Not Configured";
    document.getElementById("overall-remaining").innerText = "Set an overall budget to track pacing";
  }

  // Category Budgets Grid
  const categoryBudgets = budgets.filter(b => b.category !== "__overall__");
  document.getElementById("budget-count-label").innerText = `${categoryBudgets.length} configured`;

  const grid = document.getElementById("category-budgets-grid");
  if (!grid) return;

  if (categoryBudgets.length === 0) {
    grid.innerHTML = `
      <div class="col-span-3 text-center py-12 bg-white rounded-3xl border border-slate-200 p-8 space-y-3">
        <p class="text-sm font-semibold text-slate-700">No category budgets created yet.</p>
        <p class="text-xs text-slate-400">Set targeted limits for Groceries, Dining, Fuel, or Shopping to prevent overspending.</p>
        <button onclick="openBudgetModal()" class="px-4 py-2 text-xs font-bold rounded-xl text-white bg-slate-900 hover:bg-slate-800 transition">
          + Add First Category Budget
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = categoryBudgets.map(b => {
    let barColor = "bg-emerald-600";
    let pillColor = "bg-emerald-50 text-emerald-700";

    if (b.status === "Over Budget") {
      barColor = "bg-rose-600";
      pillColor = "bg-rose-50 text-rose-700";
    } else if (b.status === "Approaching Limit") {
      barColor = "bg-amber-500";
      pillColor = "bg-amber-50 text-amber-700";
    }

    const clamped = Math.min(100, Math.max(0, b.utilization_pct));

    return `
      <div class="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between tilt-card">
        <div>
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-slate-900 text-sm">${escapeHtml(b.category)}</h4>
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold ${pillColor}">${b.status}</span>
          </div>

          <div class="mt-3 flex items-baseline justify-between">
            <span class="text-2xl font-extrabold text-slate-900">${formatCurrency(b.actual_spending)}</span>
            <span class="text-xs text-slate-400 font-medium">of ${formatCurrency(b.budget_amount)}</span>
          </div>

          <!-- Progress Bar with Shimmer Animation -->
          <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden mt-2">
            <div class="${barColor} h-2 rounded-full progress-bar-fill transition-all duration-500" style="width: ${clamped}%"></div>
          </div>

          <div class="flex justify-between text-[11px] font-semibold text-slate-500 mt-1.5">
            <span>${b.utilization_pct}% used</span>
            <span>${formatCurrency(b.remaining_budget)} left</span>
          </div>

          ${b.drift_alert ? `<div class="mt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded-lg font-medium leading-tight">⚠️ ${escapeHtml(b.drift_alert)}</div>` : ''}
        </div>

        <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          <span class="text-slate-400 text-[11px]">${b.days_remaining} days left</span>
          <div class="space-x-2">
            <button onclick="openBudgetModal(${b.id})" class="text-slate-600 hover:text-slate-900 font-semibold">Edit</button>
            <button onclick="deleteBudgetPrompt(${b.id}, '${escapeHtml(b.category)}')" class="text-rose-600 hover:text-rose-800 font-semibold">Delete</button>
          </div>
        </div>
      </div>
    `;
  }).join("");

  initTiltCards();
}

function openBudgetModal(budgetId = null) {
  const modal = document.getElementById("budget-modal");
  const title = document.getElementById("budget-modal-title");
  const idInput = document.getElementById("modal-budget-id");
  const catSelect = document.getElementById("modal-budget-category");
  const amtInput = document.getElementById("modal-budget-amount");
  const catWrapper = document.getElementById("category-select-wrapper");

  if (budgetId) {
    const b = cachedBudgets.find(x => x.id === budgetId);
    if (!b) return;
    title.innerText = `Edit Budget: ${b.category === '__overall__' ? 'Overall Spend' : b.category}`;
    idInput.value = b.id;
    catSelect.value = b.category;
    amtInput.value = b.budget_amount;
    catWrapper.classList.add("hidden");
  } else {
    title.innerText = "Set Monthly Budget";
    idInput.value = "";
    amtInput.value = "";
    catWrapper.classList.remove("hidden");
  }

  modal.classList.remove("hidden");
}

function closeBudgetModal() {
  document.getElementById("budget-modal").classList.add("hidden");
}

async function saveBudget() {
  const id = document.getElementById("modal-budget-id").value;
  const category = document.getElementById("modal-budget-category").value;
  const amount = parseFloat(document.getElementById("modal-budget-amount").value);

  if (!amount || amount <= 0) {
    showToast("Please enter a valid positive budget amount.", "error");
    return;
  }

  try {
    if (id) {
      await api.patch(`/api/budgets/${id}`, { budget_amount: amount });
      showToast("Budget updated successfully.", "success");
    } else {
      await api.post("/api/budgets", {
        category: category,
        budget_amount: amount,
        period_type: "monthly"
      });
      triggerConfetti();
      showToast("New budget created.", "success");
    }
    closeBudgetModal();
    loadBudgets();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteBudgetPrompt(id, categoryName) {
  if (!confirm(`Are you sure you want to delete the budget for ${categoryName}?`)) return;
  try {
    await api.delete(`/api/budgets/${id}`);
    showToast("Budget deleted successfully.", "info");
    loadBudgets();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[m]));
}
