/**
 * SpendSense Settings & Categories Controller
 */

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  await loadBackups();

  document.getElementById("btn-save-settings").addEventListener("click", savePreferences);
  document.getElementById("btn-add-category").addEventListener("click", addCategory);
  
  const btnCsv = document.getElementById("btn-export-all-csv");
  if (btnCsv) {
    btnCsv.addEventListener("click", () => {
      window.open(reportsAPI.exportCsvUrl(), "_blank");
    });
  }

  const btnJson = document.getElementById("btn-export-all-json");
  if (btnJson) {
    btnJson.addEventListener("click", () => {
      window.open(reportsAPI.exportJsonUrl(), "_blank");
    });
  }

  const btnCreateBackup = document.getElementById("btn-create-backup");
  if (btnCreateBackup) {
    btnCreateBackup.addEventListener("click", createBackup);
  }
});

async function loadSettings() {
  try {
    const s = await api.get("/api/settings");

    const currSelect = document.getElementById("setting-currency");
    if (currSelect) currSelect.value = s.default_currency;

    const anomSelect = document.getElementById("setting-anomaly");
    if (anomSelect) anomSelect.value = s.anomaly_sensitivity;

    renderCategoryTags(s.categories || []);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderCategoryTags(categories) {
  const container = document.getElementById("categories-tags-container");
  if (!container) return;

  container.innerHTML = categories.map(c => {
    const isIncome = c.category_type === "income";
    const badgeColor = isIncome ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-slate-100 text-slate-700 border-slate-200";

    return `
      <span class="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-semibold border ${badgeColor}">
        <span>${escapeHtml(c.category_name)}</span>
        <span class="text-[10px] opacity-60 ml-1.5 uppercase font-bold">(${c.category_type})</span>
      </span>
    `;
  }).join("");
}

async function savePreferences() {
  const currency = document.getElementById("setting-currency").value;
  const anomaly = document.getElementById("setting-anomaly").value;

  try {
    await api.patch("/api/settings", {
      default_currency: currency,
      anomaly_sensitivity: anomaly
    });
    showToast("Preferences updated successfully.", "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function addCategory() {
  const nameInput = document.getElementById("new-cat-name");
  const typeSelect = document.getElementById("new-cat-type");

  const name = nameInput.value.trim();
  const catType = typeSelect.value;

  if (!name) {
    showToast("Please enter a category name.", "error");
    return;
  }

  try {
    await api.post("/api/settings/categories", {
      category_name: name,
      category_type: catType
    });
    showToast(`Category '${name}' created.`, "success");
    nameInput.value = "";
    await loadSettings();
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

async function loadBackups() {
  const container = document.getElementById("backups-list-container");
  if (!container) return;

  try {
    const res = await reportsAPI.listBackups();
    const backups = res.backups || [];

    if (backups.length === 0) {
      container.innerHTML = `
        <div class="text-xs text-slate-400 py-3 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
          No backups created yet. Click "+ Create Instant Backup" to protect your financial data.
        </div>
      `;
      return;
    }

    container.innerHTML = backups.map(b => `
      <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs">
        <div class="space-y-0.5">
          <div class="font-bold text-slate-800 flex items-center space-x-1.5">
            <span>💾 ${escapeHtml(b.filename)}</span>
            <span class="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-purple-100 text-purple-700">${b.size_human}</span>
          </div>
          <div class="text-[11px] text-slate-400">Created: ${formatDateIndian(b.created_at.slice(0, 10))} ${b.created_at.slice(11, 16)} UTC</div>
        </div>
        <button onclick="restoreBackup('${b.filename}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-purple-700 bg-white hover:bg-purple-50 border border-purple-200 shadow-sm transition">
          Restore
        </button>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-rose-500 py-2">Failed to load backups: ${escapeHtml(err.message)}</div>`;
  }
}

async function createBackup() {
  const btn = document.getElementById("btn-create-backup");
  try {
    if (btn) {
      btn.disabled = true;
      btn.innerText = "Backing up...";
    }
    const res = await reportsAPI.createBackup();
    showToast(res.message, "success");
    await loadBackups();
  } catch (err) {
    showToast(err.message || "Backup failed.", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "+ Create Instant Backup";
    }
  }
}

async function restoreBackup(filename) {
  if (!confirm(`Are you sure you want to restore database from '${filename}'? Current data will be replaced with this backup.`)) {
    return;
  }

  try {
    const res = await reportsAPI.restoreBackup(filename);
    showToast(res.message, "success");
    setTimeout(() => window.location.reload(), 1000);
  } catch (err) {
    showToast(err.message || "Restore failed.", "error");
  }
}
window.restoreBackup = restoreBackup;
