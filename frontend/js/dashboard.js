/**
 * SpendSense Overview Dashboard Script
 */

let categoryChartInstance = null;
let trendChartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  await loadDashboardData();

  const emptyDemoBtn = document.getElementById("btn-empty-demo");
  if (emptyDemoBtn) {
    emptyDemoBtn.addEventListener("click", async () => {
      try {
        emptyDemoBtn.disabled = true;
        emptyDemoBtn.innerText = "Loading...";
        const res = await api.post("/api/reports/demo-data");
        showToast(res.message, "success");
        await loadDashboardData();
      } catch (err) {
        showToast(err.message, "error");
        emptyDemoBtn.disabled = false;
        emptyDemoBtn.innerText = "Explore Demo Data";
      }
    });
  }
});

async function loadDashboardData() {
  try {
    // 1. Fetch Summary
    const summary = await api.get("/api/analytics/summary");

    const emptyView = document.getElementById("empty-state-view");
    const liveView = document.getElementById("live-dashboard-view");

    if (!summary || summary.transaction_count === 0) {
      if (emptyView) emptyView.classList.remove("hidden");
      if (liveView) liveView.classList.add("hidden");
      return;
    }

    if (emptyView) emptyView.classList.add("hidden");
    if (liveView) liveView.classList.remove("hidden");

    // Render Summary Headers
    const periodLabel = document.getElementById("label-reporting-period");
    if (periodLabel) periodLabel.innerText = summary.reporting_period;

    const countLabel = document.getElementById("label-txn-count");
    if (countLabel) countLabel.innerText = `${summary.transaction_count} recorded transactions`;

    const currencyLabel = document.getElementById("label-currency");
    if (currencyLabel) currencyLabel.innerText = `${summary.currency} (${summary.currency === "INR" ? "₹" : "$"})`;

    // Render 6 KPI Cards
    document.getElementById("kpi-income").innerText = formatCurrency(summary.total_income, summary.currency);
    document.getElementById("kpi-expenses").innerText = formatCurrency(summary.total_expenses, summary.currency);

    const cashflowEl = document.getElementById("kpi-cashflow");
    cashflowEl.innerText = formatCurrency(summary.net_cash_flow, summary.currency);
    const cfBadge = document.getElementById("kpi-cashflow-badge");
    if (summary.net_cash_flow >= 0) {
      cashflowEl.className = "text-3xl font-extrabold text-emerald-600 tracking-tight";
      cfBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700";
      cfBadge.innerText = "Net Surplus";
    } else {
      cashflowEl.className = "text-3xl font-extrabold text-rose-600 tracking-tight";
      cfBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700";
      cfBadge.innerText = "Deficit";
    }

    document.getElementById("kpi-savings-rate").innerText = summary.savings_rate_label;

    const momEl = document.getElementById("kpi-mom");
    const momLabelEl = document.getElementById("kpi-mom-label");
    const momIcon = document.getElementById("kpi-mom-icon");
    if (summary.mom_spending_change_pct !== null) {
      momEl.innerText = `${summary.mom_spending_change_pct > 0 ? "+" : ""}${summary.mom_spending_change_pct}%`;
      momLabelEl.innerText = summary.mom_spending_change_label;
      if (summary.mom_spending_change_pct > 0) {
        momEl.className = "text-3xl font-extrabold text-amber-600 tracking-tight";
        momIcon.innerText = "▲";
        momIcon.className = "text-xs font-bold text-amber-600";
      } else {
        momEl.className = "text-3xl font-extrabold text-emerald-600 tracking-tight";
        momIcon.innerText = "▼";
        momIcon.className = "text-xs font-bold text-emerald-600";
      }
    } else {
      momEl.innerText = "New";
      momLabelEl.innerText = summary.mom_spending_change_label;
    }

    document.getElementById("kpi-recurring").innerText = formatCurrency(summary.active_recurring_expenses, summary.currency);
    document.getElementById("kpi-recurring-count").innerText = `${summary.active_recurring_count} verified`;

    // 2. Fetch and render Categories Donut Chart
    const categories = await api.get("/api/analytics/categories");
    renderCategoryChart(categories, summary.currency);

    // 3. Fetch and render Trend Chart
    const trends = await api.get("/api/analytics/trends", { interval: "monthly" });
    renderTrendChart(trends, summary.currency);

    // 4. Fetch Insights Preview
    const insights = await api.get("/api/insights");
    renderInsightsPreview(insights);

    // 5. Fetch Recent Transactions
    const txnsRes = await api.get("/api/transactions", { page: 1, page_size: 5 });
    renderRecentTransactions(txnsRes.items, summary.currency);

    initTiltCards();
  } catch (err) {
    console.error("Dashboard Loading Error:", err);
    showToast("Failed to load dashboard: " + err.message, "error");
  }
}

function renderCategoryChart(categories, currency) {
  const ctx = document.getElementById("categoryDonutChart");
  if (!ctx) return;

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  const topCats = categories.slice(0, 6);
  const labels = topCats.map(c => c.category);
  const data = topCats.map(c => c.total_spend);

  const colors = [
    "#0F172A", "#6366F1", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#94A3B8"
  ];

  categoryChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 2,
        borderColor: "#FFFFFF"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      cutout: "68%"
    }
  });

  // Render Legend List
  const listEl = document.getElementById("category-legend-list");
  if (listEl) {
    listEl.innerHTML = topCats.map((c, idx) => `
      <div class="flex items-center justify-between text-xs py-1 hover:bg-slate-50 px-2 rounded-lg transition cursor-pointer" onclick="window.location.href='transactions.html?category=${encodeURIComponent(c.category)}'">
        <div class="flex items-center space-x-2">
          <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${colors[idx % colors.length]}"></span>
          <span class="font-medium text-slate-700">${c.category}</span>
          <span class="text-[10px] text-slate-400">(${c.percentage}%)</span>
        </div>
        <span class="font-bold text-slate-900">${formatCurrency(c.total_spend, currency)}</span>
      </div>
    `).join("");
  }
}

function renderTrendChart(trends, currency) {
  const ctx = document.getElementById("trendLineChart");
  if (!ctx) return;

  if (trendChartInstance) {
    trendChartInstance.destroy();
  }

  const labels = trends.map(t => t.period);
  const incomeData = trends.map(t => t.income);
  const expenseData = trends.map(t => t.expense);

  trendChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Income",
          data: incomeData,
          backgroundColor: "#10B981",
          borderRadius: 6
        },
        {
          label: "Expenses",
          data: expenseData,
          backgroundColor: "#0F172A",
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          ticks: {
            callback: (val) => `${currency === "INR" ? "₹" : "$"}${(val / 1000).toFixed(0)}k`
          }
        }
      }
    }
  });
}

function renderInsightsPreview(insights) {
  const container = document.getElementById("insights-preview-container");
  if (!container) return;

  if (!insights || insights.length === 0) {
    container.innerHTML = `
      <div class="col-span-3 text-center py-6 text-xs text-slate-400">
        No unusual spending alerts or budget deviations for this reporting period.
      </div>
    `;
    return;
  }

  const topThree = insights.slice(0, 3);
  const severityColors = {
    high: "bg-rose-50 border-rose-200 text-rose-800",
    medium: "bg-amber-50 border-amber-200 text-amber-800",
    positive: "bg-emerald-50 border-emerald-200 text-emerald-800",
    info: "bg-purple-50 border-purple-200 text-purple-800"
  };

  container.innerHTML = topThree.map(i => `
    <div class="p-4 rounded-2xl border ${severityColors[i.severity] || severityColors.info} space-y-2 flex flex-col justify-between">
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-[10px] font-extrabold uppercase tracking-wide opacity-80">${i.insight_type.replace('_', ' ')}</span>
          <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-white/60">${i.severity}</span>
        </div>
        <h4 class="font-bold text-sm text-slate-900">${i.title}</h4>
        <p class="text-xs text-slate-600 mt-1 leading-relaxed">${i.summary}</p>
      </div>
      <div class="pt-2 border-t border-slate-200/40">
        <span class="text-[11px] font-semibold text-slate-800">Action:</span>
        <span class="text-[11px] text-slate-600">${i.suggested_action}</span>
      </div>
    </div>
  `).join("");
}

function renderRecentTransactions(transactions, currency) {
  const tbody = document.getElementById("recent-transactions-tbody");
  if (!tbody) return;

  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-xs text-slate-400">No transactions recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = transactions.map(t => {
    const isIncome = t.transaction_type === "income";
    const amtColor = isIncome ? "text-emerald-600 font-bold" : "text-slate-900 font-bold";
    const prefix = isIncome ? "+" : "-";

    let badges = "";
    if (t.is_transfer) badges += `<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 mr-1">Transfer</span>`;
    if (t.is_refund) badges += `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 mr-1">Refund</span>`;
    if (t.is_recurring) badges += `<span class="px-1.5 py-0.5 rounded text-[10px] bg-purple-50 text-purple-700">Recurring</span>`;

    return `
      <tr class="hover:bg-slate-50/80 transition-colors">
        <td class="py-3 px-4 text-xs font-medium text-slate-500 whitespace-nowrap">${formatDate(t.transaction_date)}</td>
        <td class="py-3 px-4">
          <div class="font-semibold text-slate-900 text-sm">${t.merchant || t.description}</div>
          <div class="text-xs text-slate-400 truncate max-w-xs">${t.description} ${badges}</div>
        </td>
        <td class="py-3 px-4 text-xs">
          <span class="px-2 py-1 rounded-lg bg-slate-100 font-medium text-slate-700">${t.category}</span>
        </td>
        <td class="py-3 px-4 text-xs font-semibold capitalize ${isIncome ? 'text-emerald-700' : 'text-slate-600'}">
          ${t.transaction_type}
        </td>
        <td class="py-3 px-4 text-right text-sm ${amtColor} whitespace-nowrap">
          ${prefix}${formatCurrency(Math.abs(t.amount), currency)}
        </td>
      </tr>
    `;
  }).join("");
}
