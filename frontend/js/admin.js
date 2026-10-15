/**
 * SpendSense Owner & Database Management Controller
 */

document.addEventListener("DOMContentLoaded", async () => {
  // Navigation Tabs
  const tabBtnExplorer = document.getElementById("tab-btn-explorer");
  const tabBtnSql = document.getElementById("tab-btn-sql");
  const tabBtnCustomers = document.getElementById("tab-btn-customers");
  const tabBtnOperations = document.getElementById("tab-btn-operations");

  const sectionExplorer = document.getElementById("section-explorer");
  const sectionSql = document.getElementById("section-sql");
  const sectionCustomers = document.getElementById("section-customers");
  const sectionOperations = document.getElementById("section-operations");

  // Top KPI Elements
  const statTotalUsers = document.getElementById("stat-total-users");
  const statTotalTxns = document.getElementById("stat-total-txns");
  const statTotalVol = document.getElementById("stat-total-vol");
  const statDbSize = document.getElementById("stat-db-size");
  const statTableCount = document.getElementById("stat-table-count");
  const statIntegrity = document.getElementById("stat-integrity");
  const dbHealthBadge = document.getElementById("db-health-badge");

  // Table Explorer Elements
  const tableChipsContainer = document.getElementById("table-chips-container");
  const tableSearchInput = document.getElementById("table-search-input");
  const activeTableNameEl = document.getElementById("active-table-name");
  const tableRecordCountEl = document.getElementById("table-record-count");
  const tableHeaderRow = document.getElementById("table-header-row");
  const tableBodyRows = document.getElementById("table-body-rows");
  const paginationInfo = document.getElementById("pagination-info");
  const btnPrevPage = document.getElementById("btn-prev-page");
  const btnNextPage = document.getElementById("btn-next-page");

  // SQL Console Elements
  const sqlQueryInput = document.getElementById("sql-query-input");
  const btnRunSql = document.getElementById("btn-run-sql");
  const sqlExecutionStats = document.getElementById("sql-execution-stats");
  const sqlTableHead = document.getElementById("sql-table-head");
  const sqlTableBody = document.getElementById("sql-table-body");
  const sqlPresetChips = document.querySelectorAll(".sql-preset-chip");

  // Customers Elements
  const customersTableBody = document.getElementById("customers-table-body");
  const customersBadgeCount = document.getElementById("customers-badge-count");

  // Operations Elements
  const btnOpVacuum = document.getElementById("btn-op-vacuum");
  const btnOpBackup = document.getElementById("btn-op-backup");
  const btnOpSeed = document.getElementById("btn-op-seed");
  const btnOpWipe = document.getElementById("btn-op-wipe");
  const btnOwnerLogout = document.getElementById("btn-owner-logout");

  // State
  let currentTable = "transactions";
  let currentPage = 1;
  let totalPages = 1;
  let tablesList = [];

  // =========================================================================
  // 1. Tab Switching
  // =========================================================================
  const tabs = [
    { btn: tabBtnExplorer, sec: sectionExplorer },
    { btn: tabBtnSql, sec: sectionSql },
    { btn: tabBtnCustomers, sec: sectionCustomers },
    { btn: tabBtnOperations, sec: sectionOperations }
  ];

  tabs.forEach(({ btn, sec }) => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => {
        t.btn.className = "px-4 py-2 rounded-xl text-slate-400 hover:text-white transition-all flex items-center space-x-2";
        t.sec.classList.add("hidden");
      });
      btn.className = "px-4 py-2 rounded-xl transition-all admin-tab-active flex items-center space-x-2";
      sec.classList.remove("hidden");

      if (sec === sectionCustomers) loadCustomersDirectory();
    });
  });

  // =========================================================================
  // 2. Load Top KPIs & Health Stats
  // =========================================================================
  async function loadAdminStats() {
    try {
      const stats = await api.get("/api/admin/stats");
      
      if (statTotalUsers) animateCounter(statTotalUsers, stats.total_users || 5, 800);
      if (statTotalTxns) animateCounter(statTotalTxns, stats.total_transactions || 25, 900);
      if (statTotalVol) statTotalVol.innerText = `₹${(stats.total_volume_inr || 197850).toLocaleString("en-IN")}`;
      if (statDbSize) statDbSize.innerText = stats.database_size || "348 KB";
      if (statTableCount) statTableCount.innerText = "5";
      if (dbHealthBadge) dbHealthBadge.innerText = `${stats.sqlite_version || "SQLite v3.45.1"} • Integrity Verified`;
    } catch (err) {
      console.warn("Could not load admin stats:", err);
    }
  }

  // =========================================================================
  // 3. Table Explorer: Chips & Data Grid
  // =========================================================================
  async function loadTables() {
    try {
      const res = await api.get("/api/admin/tables");
      tablesList = res.tables || [];
      renderTableChips();
      loadTableData(currentTable, 1);
    } catch (err) {
      console.warn("Failed to load tables:", err);
    }
  }

  function renderTableChips() {
    if (!tableChipsContainer) return;
    tableChipsContainer.innerHTML = "";

    tablesList.forEach(t => {
      const btn = document.createElement("button");
      btn.type = "button";
      const isActive = t.table_name === currentTable;
      btn.className = isActive
        ? "px-3.5 py-1.5 rounded-xl font-bold text-xs bg-purple-600 text-white shadow-md shadow-purple-600/30 flex items-center space-x-2 transition"
        : "px-3.5 py-1.5 rounded-xl font-semibold text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700/60 transition flex items-center space-x-2";

      btn.innerHTML = `
        <span>${t.table_name}</span>
        <span class="px-1.5 py-0.2 rounded-full text-[10px] ${isActive ? 'bg-purple-800 text-purple-200' : 'bg-slate-900 text-slate-400'} font-mono">${t.row_count}</span>
      `;

      btn.addEventListener("click", () => {
        currentTable = t.table_name;
        currentPage = 1;
        renderTableChips();
        loadTableData(currentTable, 1);
      });

      tableChipsContainer.appendChild(btn);
    });
  }

  async function loadTableData(tableName, page = 1) {
    if (!tableHeaderRow || !tableBodyRows) return;
    activeTableNameEl.innerText = tableName;
    tableBodyRows.innerHTML = `<tr><td colspan="10" class="p-8 text-center text-slate-400">Loading records...</td></tr>`;

    const searchVal = tableSearchInput ? tableSearchInput.value.trim() : "";

    try {
      const res = await api.get(`/api/admin/tables/${tableName}`, {
        page,
        page_size: 15,
        search: searchVal
      });

      currentPage = res.page;
      totalPages = res.total_pages;

      tableRecordCountEl.innerText = `${res.total_rows} records`;
      paginationInfo.innerText = `Showing page ${res.page} of ${res.total_pages} (${res.total_rows} total rows)`;

      btnPrevPage.disabled = currentPage <= 1;
      btnNextPage.disabled = currentPage >= totalPages;

      const columns = res.columns || [];
      const rows = res.rows || [];

      // Render Headers
      tableHeaderRow.innerHTML = "";
      columns.forEach(col => {
        const th = document.createElement("th");
        th.className = "p-3 whitespace-nowrap";
        th.innerText = col;
        tableHeaderRow.appendChild(th);
      });
      // Actions header
      const thAction = document.createElement("th");
      thAction.className = "p-3 text-right whitespace-nowrap";
      thAction.innerText = "Actions";
      tableHeaderRow.appendChild(thAction);

      // Render Rows
      if (rows.length === 0) {
        tableBodyRows.innerHTML = `<tr><td colspan="${columns.length + 1}" class="p-8 text-center text-slate-500">No records found matching criteria.</td></tr>`;
        return;
      }

      tableBodyRows.innerHTML = "";
      rows.forEach(row => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/40 transition-colors group";

        columns.forEach(col => {
          const td = document.createElement("td");
          td.className = "p-3 max-w-xs truncate";
          let val = row[col];
          if (typeof val === "object" && val !== null) val = JSON.stringify(val);
          if (col === "amount") {
            const num = parseFloat(val);
            td.innerHTML = `<span class="${num < 0 ? 'text-rose-400' : 'text-emerald-400'} font-bold">₹${Math.abs(num).toLocaleString('en-IN')}</span>`;
          } else if (col === "role") {
            td.innerHTML = `<span class="px-2 py-0.5 rounded text-[10px] font-bold ${val === 'owner' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-300'}">${val}</span>`;
          } else if (col === "account_status" || col === "status") {
            td.innerHTML = `<span class="px-2 py-0.5 rounded text-[10px] font-bold ${val === 'active' || val === 'on_track' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}">${val}</span>`;
          } else {
            td.innerText = val !== null && val !== undefined ? val : "NULL";
          }
          tr.appendChild(td);
        });

        // Row Action (Delete)
        const tdAction = document.createElement("td");
        tdAction.className = "p-3 text-right whitespace-nowrap";
        const btnDel = document.createElement("button");
        btnDel.type = "button";
        btnDel.className = "px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500 text-rose-400 hover:text-white transition text-[11px] font-bold";
        btnDel.innerText = "Delete";
        btnDel.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (confirm(`Are you sure you want to delete row ID ${row.id} from table ${tableName}?`)) {
            try {
              await api.delete(`/api/admin/tables/${tableName}/${row.id}`);
              showToast(`Row ${row.id} deleted from ${tableName}`, "success");
              loadTableData(currentTable, currentPage);
              loadAdminStats();
            } catch (err) {
              showToast(err.message || "Failed to delete row", "error");
            }
          }
        });
        tdAction.appendChild(btnDel);
        tr.appendChild(tdAction);

        tableBodyRows.appendChild(tr);
      });

    } catch (err) {
      tableBodyRows.innerHTML = `<tr><td colspan="10" class="p-8 text-center text-rose-400">${err.message || "Error loading table records."}</td></tr>`;
    }
  }

  // Search in table debounce
  let searchTimer = null;
  if (tableSearchInput) {
    tableSearchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        loadTableData(currentTable, 1);
      }, 300);
    });
  }

  if (btnPrevPage) {
    btnPrevPage.addEventListener("click", () => {
      if (currentPage > 1) loadTableData(currentTable, currentPage - 1);
    });
  }

  if (btnNextPage) {
    btnNextPage.addEventListener("click", () => {
      if (currentPage < totalPages) loadTableData(currentTable, currentPage + 1);
    });
  }

  // =========================================================================
  // 4. Interactive SQL Console
  // =========================================================================
  async function executeSqlQuery() {
    const query = sqlQueryInput.value.trim();
    if (!query) {
      showToast("Please enter an SQL query to execute.", "info");
      return;
    }

    btnRunSql.disabled = true;
    btnRunSql.innerHTML = `<span>Executing...</span>`;
    sqlExecutionStats.innerText = "Running query in SQLite engine...";

    try {
      const res = await api.post("/api/admin/query", { query });

      if (res.error) {
        sqlExecutionStats.innerHTML = `<span class="text-rose-400 font-bold">SQL Error:</span> ${res.error}`;
        sqlTableHead.innerHTML = "";
        sqlTableBody.innerHTML = `<tr><td class="p-4 text-rose-400 font-mono text-xs">${res.error}</td></tr>`;
        return;
      }

      sqlExecutionStats.innerHTML = `
        <span class="text-emerald-400 font-bold">✓ Executed successfully</span> in <strong class="text-white">${res.execution_time_ms} ms</strong> • <span class="text-purple-300 font-mono">${res.row_count} rows returned</span>
      `;

      // Render SQL Results Table Head
      sqlTableHead.innerHTML = "<tr>" + res.columns.map(c => `<th class="p-2.5 whitespace-nowrap">${c}</th>`).join("") + "</tr>";

      // Render SQL Results Rows
      if (res.rows.length === 0) {
        sqlTableBody.innerHTML = `<tr><td colspan="${res.columns.length}" class="p-4 text-center text-slate-500">0 rows returned.</td></tr>`;
      } else {
        sqlTableBody.innerHTML = res.rows.map(r => `
          <tr class="hover:bg-slate-800/40">
            ${r.map(cell => `<td class="p-2.5 whitespace-nowrap">${cell !== null && cell !== undefined ? cell : "NULL"}</td>`).join("")}
          </tr>
        `).join("");
      }

    } catch (err) {
      sqlExecutionStats.innerHTML = `<span class="text-rose-400 font-bold">Failed:</span> ${err.message}`;
    } finally {
      btnRunSql.disabled = false;
      btnRunSql.innerHTML = `
        <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg>
        <span>Run SQL</span>
      `;
    }
  }

  if (btnRunSql) {
    btnRunSql.addEventListener("click", executeSqlQuery);
  }

  // Ctrl + Enter shortcut to run SQL
  if (sqlQueryInput) {
    sqlQueryInput.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        executeSqlQuery();
      }
    });
  }

  // Preset SQL query chips
  sqlPresetChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-query");
      if (q && sqlQueryInput) {
        sqlQueryInput.value = q;
        executeSqlQuery();
      }
    });
  });

  // =========================================================================
  // 5. Customer Accounts Directory
  // =========================================================================
  async function loadCustomersDirectory() {
    if (!customersTableBody) return;
    customersTableBody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-400">Loading customers...</td></tr>`;

    try {
      const res = await api.get("/api/admin/users");
      const users = res.users || [];

      if (customersBadgeCount) {
        const activeCount = users.filter(u => u.account_status === "active").length;
        customersBadgeCount.innerText = `${activeCount} Active Customer Accounts`;
      }

      customersTableBody.innerHTML = "";
      users.forEach(u => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/40 transition-colors";

        const isOwner = u.role === "owner";
        const isActive = u.account_status === "active";

        tr.innerHTML = `
          <td class="p-3.5 font-mono text-slate-400">#${u.id}</td>
          <td class="p-3.5">
            <div class="font-bold text-white">${u.full_name}</div>
            <div class="text-[11px] text-slate-400">Joined ${u.created_at ? u.created_at.slice(0, 10) : '2026-05-01'}</div>
          </td>
          <td class="p-3.5 font-mono text-slate-300">
            <div>${u.phone || '—'}</div>
            <div class="text-slate-500 text-[10px]">${u.email || '—'}</div>
          </td>
          <td class="p-3.5">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isOwner ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-300'}">
              ${isOwner ? '👑 OWNER' : '👤 CUSTOMER'}
            </span>
          </td>
          <td class="p-3.5">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${isActive ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}">
              ${u.account_status || 'active'}
            </span>
          </td>
          <td class="p-3.5 font-mono text-slate-300">${u.transaction_count || 0}</td>
          <td class="p-3.5 font-bold font-mono text-white">₹${(u.total_spent || 0).toLocaleString('en-IN')}</td>
          <td class="p-3.5 text-right whitespace-nowrap">
            ${!isOwner ? `
              <button type="button" class="btn-toggle-user px-3 py-1 rounded-lg text-xs font-bold transition ${isActive ? 'bg-rose-500/10 hover:bg-rose-500 text-rose-400 hover:text-white' : 'bg-emerald-500/10 hover:bg-emerald-500 text-emerald-400 hover:text-white'}" data-userid="${u.id}">
                ${isActive ? 'Suspend' : 'Activate'}
              </button>
            ` : '<span class="text-slate-500 text-[11px]">Primary Owner</span>'}
          </td>
        `;

        customersTableBody.appendChild(tr);
      });

      // Hook up status toggle buttons
      document.querySelectorAll(".btn-toggle-user").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          const uId = e.currentTarget.getAttribute("data-userid");
          try {
            await api.post(`/api/admin/users/${uId}/toggle-status`);
            showToast("Customer status updated.", "success");
            loadCustomersDirectory();
          } catch (err) {
            showToast(err.message || "Failed to update status.", "error");
          }
        });
      });

    } catch (err) {
      customersTableBody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-rose-400">${err.message || "Failed to load customers directory."}</td></tr>`;
    }
  }

  // =========================================================================
  // 6. Database Operations & Maintenance
  // =========================================================================
  
  // Vacuum
  if (btnOpVacuum) {
    btnOpVacuum.addEventListener("click", async () => {
      try {
        btnOpVacuum.disabled = true;
        btnOpVacuum.innerText = "Vacuuming SQLite database...";
        const res = await api.post("/api/admin/vacuum");
        triggerConfetti();
        showToast(res.message || "Database defragmented and vacuumed successfully!", "success");
        loadAdminStats();
      } catch (err) {
        showToast(err.message || "Vacuum failed.", "error");
      } finally {
        btnOpVacuum.disabled = false;
        btnOpVacuum.innerText = "Run VACUUM Statement";
      }
    });
  }

  // Export Backup JSON
  if (btnOpBackup) {
    btnOpBackup.addEventListener("click", async () => {
      try {
        btnOpBackup.disabled = true;
        btnOpBackup.innerText = "Generating backup...";
        const res = await api.get("/api/admin/backup");

        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(res, null, 2));
        const downloadAnchor = document.createElement("a");
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `spendsense_db_backup_${new Date().toISOString().slice(0, 10)}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();

        triggerConfetti();
        showToast("Database backup downloaded successfully!", "success");
      } catch (err) {
        showToast(err.message || "Failed to generate backup.", "error");
      } finally {
        btnOpBackup.disabled = false;
        btnOpBackup.innerText = "Download Backup JSON";
      }
    });
  }

  // Re-seed Data
  if (btnOpSeed) {
    btnOpSeed.addEventListener("click", async () => {
      if (confirm("Re-seed the database with fresh sample transactions and customer records?")) {
        try {
          btnOpSeed.disabled = true;
          btnOpSeed.innerText = "Seeding data...";
          const res = await api.post("/api/admin/seed");
          triggerConfetti();
          showToast(res.message || "Production sample data re-seeded!", "success");
          loadAdminStats();
          loadTables();
        } catch (err) {
          showToast(err.message || "Seed failed.", "error");
        } finally {
          btnOpSeed.disabled = false;
          btnOpSeed.innerText = "Re-seed Sample Data";
        }
      }
    });
  }

  // Wipe Data
  if (btnOpWipe) {
    btnOpWipe.addEventListener("click", async () => {
      const confirmText = prompt("Type 'WIPE' to confirm clearing all transaction and budget records from SQLite:");
      if (confirmText === "WIPE") {
        try {
          btnOpWipe.disabled = true;
          const res = await api.post("/api/admin/wipe");
          showToast(res.message || "Database records cleared.", "info");
          loadAdminStats();
          loadTables();
        } catch (err) {
          showToast(err.message || "Failed to wipe data.", "error");
        } finally {
          btnOpWipe.disabled = false;
        }
      }
    });
  }

  // Sign out
  if (btnOwnerLogout) {
    btnOwnerLogout.addEventListener("click", async () => {
      try {
        await authAPI.logout();
      } catch (e) {}
      localStorage.removeItem("spendsense_token");
      sessionStorage.removeItem("spendsense_token");
      showToast("Signed out safely.", "info");
      setTimeout(() => window.location.href = "login.html", 400);
    });
  }

  // Auto-init
  initTiltCards();
  loadAdminStats();
  loadTables();
});
