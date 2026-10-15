/**
 * SpendSense Insights & Savings Opportunities Controller
 */

let cachedInsights = [];
let activeFilter = "all";

document.addEventListener("DOMContentLoaded", async () => {
  await loadSavingsData();
  await loadInsightsData();
});

async function loadSavingsData() {
  const grid = document.getElementById("savings-opportunities-grid");
  if (!grid) return;

  try {
    const opps = await api.get("/api/analytics/savings");
    if (!opps || opps.length === 0) {
      grid.innerHTML = `
        <div class="col-span-3 text-center py-10 bg-white rounded-3xl border border-slate-200 p-8 space-y-2">
          <p class="font-bold text-slate-800 text-sm">No savings opportunities identified yet.</p>
          <p class="text-xs text-slate-400">Import at least 30–60 days of statements to uncover discretionary patterns and subscription reviews.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = opps.map(o => `
      <div class="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm tilt-card space-y-4 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-[10px] font-extrabold uppercase tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">${escapeHtml(o.opportunity_type.replace('_', ' '))}</span>
            <span class="text-xs font-semibold text-slate-400">${o.confidence} Confidence</span>
          </div>

          <h3 class="font-bold text-slate-900 text-base">${escapeHtml(o.title)}</h3>
          
          <div class="mt-3 p-3 bg-slate-50 rounded-2xl border border-slate-100 space-y-1">
            <span class="text-[11px] font-semibold text-slate-500">Estimated Monthly Impact:</span>
            <p class="text-2xl font-extrabold text-emerald-600">~${formatCurrency(o.estimated_potential_monthly_savings)}</p>
          </div>

          <p class="text-xs text-slate-600 mt-3 leading-relaxed">
            <strong class="text-slate-800">Assumptions:</strong> ${escapeHtml(o.assumptions)}
          </p>
        </div>

        <div class="pt-3 border-t border-slate-100 space-y-3">
          <div class="text-[11px] text-slate-500">
            <span class="font-semibold text-slate-700">Recommended Action:</span> ${escapeHtml(o.suggested_action)}
          </div>
          ${o.category ? `<a href="transactions.html?category=${encodeURIComponent(o.category)}" class="inline-block text-xs font-bold text-purple-700 hover:text-purple-900">Inspect ${escapeHtml(o.category)} Purchases →</a>` : ''}
        </div>
      </div>
    `).join("");

    initTiltCards();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadInsightsData() {
  try {
    cachedInsights = await api.get("/api/insights");
    renderInsights();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function filterInsights(filter) {
  activeFilter = filter;
  document.querySelectorAll(".ins-filter").forEach(btn => {
    if (btn.getAttribute("data-filter") === filter) {
      btn.className = "ins-filter px-3 py-1.5 rounded-lg bg-slate-900 text-white";
    } else {
      btn.className = "ins-filter px-3 py-1.5 rounded-lg text-slate-600 hover:bg-slate-100";
    }
  });
  renderInsights();
}

function renderInsights() {
  const container = document.getElementById("insights-list");
  if (!container) return;

  let filtered = cachedInsights;
  if (activeFilter === "high") {
    filtered = cachedInsights.filter(i => i.severity === "high");
  } else if (activeFilter === "positive") {
    filtered = cachedInsights.filter(i => i.severity === "positive");
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 bg-white rounded-3xl border border-slate-200 p-8 space-y-2">
        <p class="font-bold text-slate-800 text-sm">No active insights in this category.</p>
        <p class="text-xs text-slate-400">All current spending metrics and budget indicators are normal.</p>
      </div>
    `;
    return;
  }

  const severityStyles = {
    high: { border: "border-rose-200", bg: "bg-rose-50/50", pill: "bg-rose-100 text-rose-800", icon: "⚠️" },
    medium: { border: "border-amber-200", bg: "bg-amber-50/50", pill: "bg-amber-100 text-amber-800", icon: "⚡" },
    positive: { border: "border-emerald-200", bg: "bg-emerald-50/50", pill: "bg-emerald-100 text-emerald-800", icon: "✓" },
    info: { border: "border-purple-200", bg: "bg-purple-50/50", pill: "bg-purple-100 text-purple-800", icon: "ℹ" }
  };

  container.innerHTML = filtered.map(i => {
    const s = severityStyles[i.severity] || severityStyles.info;
    const isReviewed = i.status === "reviewed";

    return `
      <div class="bg-white rounded-3xl p-6 border ${s.border} shadow-sm space-y-4 ${isReviewed ? 'opacity-60' : ''}">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center space-x-2.5">
            <span class="w-7 h-7 rounded-lg flex items-center justify-center text-sm ${s.pill}">${s.icon}</span>
            <span class="text-xs font-bold uppercase tracking-wider text-slate-400">${escapeHtml(i.insight_type.replace('_', ' '))}</span>
            ${isReviewed ? `<span class="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">Reviewed</span>` : ''}
          </div>
          <span class="text-xs font-semibold text-slate-400">Period: ${i.period}</span>
        </div>

        <div>
          <h3 class="font-extrabold text-slate-900 text-base">${escapeHtml(i.title)}</h3>
          <p class="text-sm text-slate-600 mt-1 leading-relaxed">${escapeHtml(i.summary)}</p>
        </div>

        <div class="p-3 rounded-2xl bg-slate-50 border border-slate-100 text-xs">
          <span class="font-bold text-slate-800">Recommended Action:</span>
          <span class="text-slate-600 ml-1">${escapeHtml(i.suggested_action)}</span>
        </div>

        <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          <span class="text-slate-400 text-[11px]">${i.confidence_level} Confidence Data Engine</span>
          <div class="space-x-3">
            ${!isReviewed ? `<button onclick="updateInsight(${i.id}, 'reviewed')" class="font-semibold text-slate-600 hover:text-slate-900">Mark Reviewed</button>` : ''}
            <button onclick="updateInsight(${i.id}, 'dismissed')" class="font-semibold text-rose-600 hover:text-rose-800">Dismiss</button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

async function updateInsight(id, status) {
  try {
    await api.patch(`/api/insights/${id}`, { status: status });
    showToast(`Insight marked as ${status}.`, "info");
    await loadInsightsData();
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
