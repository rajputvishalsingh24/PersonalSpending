/**
 * SpendSense Recurring Expenses & Subscriptions Controller
 */

let cachedRecurring = [];

document.addEventListener("DOMContentLoaded", async () => {
  await loadRecurringData();
});

async function loadRecurringData() {
  try {
    cachedRecurring = await api.get("/api/recurring");
    renderRecurringSummary(cachedRecurring);
    renderRecurringTable(cachedRecurring);
    initTiltCards();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderRecurringSummary(patterns) {
  const active = patterns.filter(p => p.status !== "dismissed");
  let totalMonthly = 0;
  let totalAnnual = 0;
  let subCount = 0;

  active.forEach(p => {
    const avg = p.average_amount;
    const freq = p.frequency;
    totalAnnual += p.annual_estimate;
    if (freq === "weekly") totalMonthly += avg * 4.33;
    else if (freq === "monthly") totalMonthly += avg;
    else if (freq === "quarterly") totalMonthly += avg / 3;
    else if (freq === "annual") totalMonthly += avg / 12;
    else totalMonthly += avg;

    if (p.is_subscription) subCount++;
  });

  document.getElementById("rec-kpi-monthly").innerText = formatCurrency(totalMonthly);
  document.getElementById("rec-kpi-annual").innerText = formatCurrency(totalAnnual);
  document.getElementById("rec-kpi-count").innerText = `${subCount} active`;
}

function renderRecurringTable(patterns) {
  const tbody = document.getElementById("recurring-tbody");
  if (!tbody) return;

  if (!patterns || patterns.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="py-12 text-center text-xs text-slate-400">No recurring payment patterns detected. Import at least 2–3 months of statements to reveal repeating bills.</td></tr>`;
    return;
  }

  tbody.innerHTML = patterns.map(p => {
    const isDismissed = p.status === "dismissed";
    const isConfirmed = p.status === "confirmed";

    let statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700">Detected</span>`;
    if (isConfirmed) statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700">Confirmed</span>`;
    if (isDismissed) statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-500">Dismissed</span>`;

    const subPill = p.is_subscription
      ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-purple-100 text-purple-700 font-bold ml-1.5">Sub</span>`
      : "";

    return `
      <tr class="hover:bg-slate-50 transition-colors ${isDismissed ? 'opacity-50' : ''}">
        <td class="py-3 px-4">
          <div class="font-bold text-slate-900 text-sm flex items-center">
            ${escapeHtml(p.merchant)} ${subPill}
          </div>
          <div class="text-[10px] text-slate-400">${p.occurrences_count} transactions verified</div>
        </td>
        <td class="py-3 px-4 text-slate-700">${escapeHtml(p.category)}</td>
        <td class="py-3 px-4 capitalize font-semibold text-slate-800">${p.frequency}</td>
        <td class="py-3 px-4 font-mono font-bold text-slate-900">${formatCurrency(p.average_amount)}</td>
        <td class="py-3 px-4 font-mono font-medium text-slate-600">${formatCurrency(p.annual_estimate)}</td>
        <td class="py-3 px-4">
          <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">${Math.round(p.confidence_score * 100)}%</span>
        </td>
        <td class="py-3 px-4">${statusBadge}</td>
        <td class="py-3 px-4 text-center whitespace-nowrap space-x-1.5">
          ${!isConfirmed ? `<button onclick="updateRecurringStatus(${p.id}, 'confirmed')" class="px-2.5 py-1 rounded-lg text-emerald-700 bg-emerald-50 hover:bg-emerald-100 font-semibold transition" title="Confirm as real recurring bill">Confirm</button>` : ''}
          ${!isDismissed ? `<button onclick="updateRecurringStatus(${p.id}, 'dismissed')" class="px-2.5 py-1 rounded-lg text-rose-700 bg-rose-50 hover:bg-rose-100 font-semibold transition" title="Dismiss false positive">Dismiss</button>` : ''}
          <button onclick="toggleSubscriptionFlag(${p.id}, ${!p.is_subscription})" class="px-2 py-1 rounded-lg text-slate-600 hover:bg-slate-200 transition" title="Toggle Subscription Flag">
            ${p.is_subscription ? 'Unmark Sub' : 'Mark Sub'}
          </button>
          <a href="transactions.html?search=${encodeURIComponent(p.merchant)}" class="px-2 py-1 rounded-lg text-purple-700 hover:bg-purple-50 transition" title="View historical records">
            History →
          </a>
        </td>
      </tr>
    `;
  }).join("");
}

async function updateRecurringStatus(id, newStatus) {
  try {
    await api.patch(`/api/recurring/${id}`, { status: newStatus });
    showToast(`Recurring item marked as ${newStatus}.`, "success");
    await loadRecurringData();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function toggleSubscriptionFlag(id, isSub) {
  try {
    await api.patch(`/api/recurring/${id}`, { is_subscription: isSub });
    showToast(`Subscription status updated.`, "info");
    await loadRecurringData();
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
