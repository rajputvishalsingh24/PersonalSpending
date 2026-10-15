/**
 * SpendSense Transactions Manager Script
 */

let currentPage = 1;
let currentTotalPages = 1;
let currentCurrency = "INR";
let cachedCategories = [];

document.addEventListener("DOMContentLoaded", async () => {
  await loadCategories();

  // Check URL query parameters (e.g. ?category=Restaurants)
  const urlParams = new URLSearchParams(window.location.search);
  const initialCategory = urlParams.get("category");
  if (initialCategory) {
    const catSelect = document.getElementById("filter-category");
    if (catSelect) catSelect.value = initialCategory;
  }

  await loadTransactions();

  // Event Listeners for Filters
  let debounceTimeout;
  document.getElementById("filter-search").addEventListener("input", () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      currentPage = 1;
      loadTransactions();
    }, 300);
  });

  ["filter-category", "filter-type", "filter-sort"].forEach(id => {
    document.getElementById(id).addEventListener("change", () => {
      currentPage = 1;
      loadTransactions();
    });
  });

  document.getElementById("btn-reset-filters").addEventListener("click", () => {
    document.getElementById("filter-search").value = "";
    document.getElementById("filter-category").value = "";
    document.getElementById("filter-type").value = "";
    document.getElementById("filter-sort").value = "transaction_date-desc";
    currentPage = 1;
    loadTransactions();
  });

  // Pagination
  document.getElementById("btn-prev-page").addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      loadTransactions();
    }
  });

  document.getElementById("btn-next-page").addEventListener("click", () => {
    if (currentPage < currentTotalPages) {
      currentPage++;
      loadTransactions();
    }
  });

  // Export CSV
  document.getElementById("btn-export-csv").addEventListener("click", () => {
    const cat = document.getElementById("filter-category").value;
    const url = `${API_BASE_URL}/api/reports/export?category=${encodeURIComponent(cat)}`;
    window.open(url, "_blank");
  });

  // Modal Listeners
  document.getElementById("btn-close-modal").addEventListener("click", closeModal);
  document.getElementById("btn-cancel-edit").addEventListener("click", closeModal);
  document.getElementById("btn-save-edit").addEventListener("click", saveTransactionEdit);
});

async function loadCategories() {
  try {
    const settings = await api.get("/api/settings");
    currentCurrency = settings.default_currency;
    cachedCategories = settings.categories || [];

    const filterSelect = document.getElementById("filter-category");
    const editSelect = document.getElementById("edit-category");

    const optionsHtml = cachedCategories.map(c => `
      <option value="${c.category_name}">${c.category_name} (${c.category_type})</option>
    `).join("");

    if (filterSelect) {
      filterSelect.innerHTML = `<option value="">All Categories</option>${optionsHtml}`;
    }
    if (editSelect) {
      editSelect.innerHTML = optionsHtml;
    }
  } catch (err) {
    console.error("Failed to load categories:", err);
  }
}

async function loadTransactions() {
  const search = document.getElementById("filter-search").value.trim();
  const category = document.getElementById("filter-category").value;
  const type = document.getElementById("filter-type").value;
  const sortVal = document.getElementById("filter-sort").value.split("-");
  const sortBy = sortVal[0];
  const sortOrder = sortVal[1] || "desc";

  try {
    const res = await api.get("/api/transactions", {
      page: currentPage,
      page_size: 20,
      search: search || null,
      category: category || null,
      transaction_type: type || null,
      sort_by: sortBy,
      sort_order: sortOrder
    });

    currentPage = res.page;
    currentTotalPages = res.total_pages;

    renderTransactionsTable(res.items);
    renderPagination(res);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTransactionsTable(items) {
  const tbody = document.getElementById("transactions-tbody");
  if (!tbody) return;

  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="py-12 text-center text-xs text-slate-400">No transactions match your current search and filter criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(t => {
    const isIncome = t.transaction_type === "income";
    const amtColor = isIncome ? "text-emerald-600 font-bold" : "text-slate-900 font-bold";
    const prefix = isIncome ? "+" : "-";

    let badges = "";
    if (t.is_transfer) badges += `<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200 mr-1">Transfer</span>`;
    if (t.is_refund) badges += `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 mr-1">Refund</span>`;
    if (t.is_recurring) badges += `<span class="px-1.5 py-0.5 rounded text-[10px] bg-purple-50 text-purple-700 border border-purple-200 mr-1">Recurring</span>`;

    return `
      <tr class="hover:bg-slate-50 transition-colors">
        <td class="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">${formatDate(t.transaction_date)}</td>
        <td class="py-3 px-4">
          <div class="font-bold text-slate-900 text-sm">${escapeHtml(t.merchant || t.description)}</div>
          <div class="text-[11px] text-slate-400 truncate max-w-sm">${escapeHtml(t.description)}</div>
          ${t.notes ? `<div class="text-[10px] text-purple-600 italic mt-0.5">Note: ${escapeHtml(t.notes)}</div>` : ''}
        </td>
        <td class="py-3 px-4">
          <span class="px-2 py-1 rounded-lg bg-slate-100 font-semibold text-slate-700">${escapeHtml(t.category)}</span>
        </td>
        <td class="py-3 px-4 whitespace-nowrap">
          <span class="capitalize font-semibold ${isIncome ? 'text-emerald-700' : 'text-slate-600'} mr-1.5">${t.transaction_type}</span>
          ${badges}
        </td>
        <td class="py-3 px-4 text-right font-mono text-sm ${amtColor} whitespace-nowrap">
          ${prefix}${formatCurrency(Math.abs(t.amount), currentCurrency)}
        </td>
        <td class="py-3 px-4 text-center whitespace-nowrap space-x-1.5">
          <button onclick="openEditModal(${t.id})" class="p-1.5 rounded-lg text-slate-600 hover:bg-slate-200 transition" title="Edit Category & Details">
            ✎
          </button>
          <button onclick="deleteTransactionPrompt(${t.id})" class="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 transition" title="Delete Transaction">
            ✕
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function renderPagination(res) {
  document.getElementById("pagination-page-info").innerText = `Showing Page ${res.page} of ${res.total_pages} (${res.total_count} total records)`;
  document.getElementById("btn-prev-page").disabled = res.page <= 1;
  document.getElementById("btn-next-page").disabled = res.page >= res.total_pages;
  document.getElementById("total-results-label").innerText = `Displaying ${res.items.length} of ${res.total_count} transactions`;
}

async function openEditModal(txnId) {
  try {
    const t = await api.get(`/api/transactions/${txnId}`);
    document.getElementById("edit-txn-id").value = t.id;
    document.getElementById("edit-merchant").value = t.merchant;
    document.getElementById("edit-category").value = t.category;
    document.getElementById("edit-notes").value = t.notes || "";
    document.getElementById("edit-is-transfer").checked = !!t.is_transfer;
    document.getElementById("edit-is-refund").checked = !!t.is_refund;

    document.getElementById("edit-modal").classList.remove("hidden");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function closeModal() {
  document.getElementById("edit-modal").classList.add("hidden");
}

async function saveTransactionEdit() {
  const txnId = document.getElementById("edit-txn-id").value;
  const merchant = document.getElementById("edit-merchant").value.trim();
  const category = document.getElementById("edit-category").value;
  const notes = document.getElementById("edit-notes").value.trim();
  const isTransfer = document.getElementById("edit-is-transfer").checked;
  const isRefund = document.getElementById("edit-is-refund").checked;

  try {
    await api.patch(`/api/transactions/${txnId}`, {
      merchant: merchant,
      category: category,
      notes: notes,
      is_transfer: isTransfer,
      is_refund: isRefund
    });
    showToast("Transaction updated and category rule saved.", "success");
    closeModal();
    loadTransactions();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteTransactionPrompt(txnId) {
  if (!confirm(`Are you sure you want to delete transaction #${txnId} from SQLite?`)) return;

  try {
    await api.delete(`/api/transactions/${txnId}`);
    showToast("Transaction deleted successfully.", "info");
    loadTransactions();
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
