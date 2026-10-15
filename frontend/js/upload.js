/**
 * SpendSense Transaction Upload Wizard Controller
 */

let currentPreviewData = null;

document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("file-input");
  const browseBtn = document.getElementById("btn-browse-file");
  const dropzone = document.getElementById("dropzone-card");
  const cancelBtn = document.getElementById("btn-cancel-import");
  const confirmBtn = document.getElementById("btn-confirm-import");

  if (browseBtn && fileInput) {
    browseBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
      }
    });
  }

  if (dropzone) {
    ["dragenter", "dragover"].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.add("border-purple-500", "bg-purple-50/20");
      });
    });

    ["dragleave", "drop"].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.remove("border-purple-500", "bg-purple-50/20");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", resetUploadView);
  }

  if (confirmBtn) {
    confirmBtn.addEventListener("click", executeImport);
  }
});

async function handleFileUpload(file) {
  const dropzone = document.getElementById("dropzone-card");
  const loading = document.getElementById("upload-loading");
  const previewPanel = document.getElementById("preview-panel");

  try {
    dropzone.classList.add("hidden");
    loading.classList.remove("hidden");
    previewPanel.classList.add("hidden");

    const data = await api.upload("/api/uploads/preview", file);
    currentPreviewData = data;

    renderPreview(data);

    loading.classList.add("hidden");
    previewPanel.classList.remove("hidden");
  } catch (err) {
    showToast(err.message, "error");
    resetUploadView();
  }
}

function renderPreview(data) {
  document.getElementById("preview-filename").innerText = `${data.filename} (${data.file_type})`;
  document.getElementById("stat-valid").innerText = data.valid_rows_count;
  document.getElementById("stat-duplicates").innerText = data.duplicate_rows_count;
  document.getElementById("stat-errors").innerText = data.error_rows_count;

  // Populate column mapping selects
  const mapping = data.column_mapping;
  const cols = ["(None)", ...data.columns_found];

  populateSelect("map-date", cols, mapping.date_col);
  populateSelect("map-desc", cols, mapping.desc_col);
  populateSelect("map-merchant", cols, mapping.merchant_col);
  populateSelect("map-amount", cols, mapping.amount_col || mapping.debit_col);

  // Render first 10 rows
  const tbody = document.getElementById("preview-tbody");
  tbody.innerHTML = data.preview_rows.slice(0, 10).map(r => {
    let statusBadge = `<span class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold text-[10px]">Valid</span>`;
    if (r.validation_error) {
      statusBadge = `<span class="px-2 py-0.5 rounded bg-rose-50 text-rose-700 font-semibold text-[10px]">${r.validation_error}</span>`;
    } else if (r.is_duplicate) {
      statusBadge = `<span class="px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-semibold text-[10px]">Duplicate</span>`;
    }

    const amtStr = r.parsed_amount !== null
      ? `${r.parsed_amount < 0 ? '-' : '+'}₹${Math.abs(r.parsed_amount).toFixed(2)}`
      : r.raw_amount;

    return `
      <tr class="hover:bg-slate-50 transition-colors">
        <td class="py-2.5 px-3 font-mono text-slate-500 whitespace-nowrap">${r.parsed_date || r.raw_date}</td>
        <td class="py-2.5 px-3 font-medium text-slate-900 truncate max-w-xs">${r.raw_description}</td>
        <td class="py-2.5 px-3 text-slate-600">${r.merchant || '-'}</td>
        <td class="py-2.5 px-3 text-slate-700"><span class="px-2 py-0.5 bg-slate-100 rounded">${r.category}</span></td>
        <td class="py-2.5 px-3 text-right font-bold font-mono ${r.transaction_type === 'income' ? 'text-emerald-600' : 'text-slate-900'}">${amtStr}</td>
        <td class="py-2.5 px-3 whitespace-nowrap">${statusBadge}</td>
      </tr>
    `;
  }).join("");
}

function populateSelect(selectId, options, selectedVal) {
  const select = document.getElementById(selectId);
  if (!select) return;

  select.innerHTML = options.map(opt => `
    <option value="${opt === '(None)' ? '' : opt}" ${opt === selectedVal ? 'selected' : ''}>
      ${opt}
    </option>
  `).join("");
}

async function executeImport() {
  if (!currentPreviewData) return;

  const confirmBtn = document.getElementById("btn-confirm-import");
  const skipDuplicates = document.getElementById("chk-skip-duplicates").checked;

  const mapping = {
    date_col: document.getElementById("map-date").value || null,
    desc_col: document.getElementById("map-desc").value || null,
    merchant_col: document.getElementById("map-merchant").value || null,
    amount_col: document.getElementById("map-amount").value || null,
    debit_col: currentPreviewData.column_mapping.debit_col,
    credit_col: currentPreviewData.column_mapping.credit_col,
    category_col: currentPreviewData.column_mapping.category_col,
    type_col: currentPreviewData.column_mapping.type_col
  };

  try {
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
      <span>Importing to SQLite...</span>
    `;

    const res = await api.post("/api/uploads/import", {
      temp_file_token: currentPreviewData.temp_file_token,
      column_mapping: mapping,
      skip_duplicates: skipDuplicates,
      default_currency: "INR"
    });

    showToast(`Successfully imported ${res.transaction_count} transactions to database.`, "success");
    setTimeout(() => {
      window.location.href = "dashboard.html";
    }, 800);
  } catch (err) {
    showToast(err.message, "error");
    confirmBtn.disabled = false;
    confirmBtn.innerText = "Confirm & Import Records";
  }
}

function resetUploadView() {
  currentPreviewData = null;
  document.getElementById("dropzone-card").classList.remove("hidden");
  document.getElementById("upload-loading").classList.add("hidden");
  document.getElementById("preview-panel").classList.add("hidden");
  const fileInput = document.getElementById("file-input");
  if (fileInput) fileInput.value = "";
}
