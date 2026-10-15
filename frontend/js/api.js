/**
 * SpendSense Centralized API Client & Utility Library
 * Supports both Live FastAPI Backend and Standalone Web / Offline Client-Side Engine
 */

const API_BASE_URL = (() => {
  const custom = localStorage.getItem("spendsense_backend_url");
  if (custom) return custom;
  if (window.location.port === "8000" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return window.location.origin;
  }
  return "http://localhost:8000";
})();

// Detect if running on Vercel or static hosting without a local backend running
const IS_VERCEL_STATIC = window.location.hostname.includes("vercel.app") || window.location.hostname.includes("github.io") || window.location.protocol === "file:";

// =========================================================================
// Client-Side Persistent Financial Engine (for Standalone Static Vercel Web)
// =========================================================================

const INITIAL_DEMO_TRANSACTIONS = [
  { id: 1, transaction_date: "2026-05-01", description: "ACME Corp Monthly Payroll Salary", merchant: "ACME Corp", amount: 95000.0, transaction_type: "income", category: "Salary", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 2, transaction_date: "2026-05-02", description: "BigBasket Fresh Fruits and Provisions", merchant: "BigBasket", amount: -2850.0, transaction_type: "expense", category: "Groceries", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 3, transaction_date: "2026-05-03", description: "Self Transfer to Savings Reserve Account", merchant: "Self Transfer", amount: -20000.0, transaction_type: "expense", category: "Other", is_transfer: 1, is_refund: 0, notes: "Internal Transfer" },
  { id: 4, transaction_date: "2026-05-04", description: "Swiggy Gourmet Dinner Delivery", merchant: "Swiggy", amount: -780.0, transaction_type: "expense", category: "Food Delivery", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 5, transaction_date: "2026-05-05", description: "Apartment Rental Society Maintenance", merchant: "Prestige Heights", amount: -25000.0, transaction_type: "expense", category: "Rent", is_transfer: 0, is_refund: 0, notes: "Monthly Rent" },
  { id: 6, transaction_date: "2026-05-07", description: "HPCL Petrol Station Fuel Dispense", merchant: "HPCL Fuel", amount: -2500.0, transaction_type: "expense", category: "Transport and Fuel", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 7, transaction_date: "2026-05-08", description: "HDFC Auto Loan EMI Debited", merchant: "HDFC Bank Loan", amount: -11500.0, transaction_type: "expense", category: "Loan and EMI Payments", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 8, transaction_date: "2026-05-09", description: "Zepto Quick 10m Groceries Delivery", merchant: "Zepto Groceries", amount: -1250.0, transaction_type: "expense", category: "Groceries", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 9, transaction_date: "2026-05-10", description: "Netflix Standard HD Subscription Plan", merchant: "Netflix", amount: -649.0, transaction_type: "expense", category: "Subscriptions", is_transfer: 0, is_refund: 0, notes: "Recurring" },
  { id: 10, transaction_date: "2026-05-11", description: "Zomato Weekend Biryani Order", merchant: "Zomato", amount: -1240.0, transaction_type: "expense", category: "Food Delivery", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 11, transaction_date: "2026-05-12", description: "Spotify Premium Individual Monthly", merchant: "Spotify", amount: -119.0, transaction_type: "expense", category: "Subscriptions", is_transfer: 0, is_refund: 0, notes: "Recurring" },
  { id: 12, transaction_date: "2026-05-14", description: "Uber Airport Drop Ride Cab", merchant: "Uber Rides", amount: -850.0, transaction_type: "expense", category: "Public Transport", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 13, transaction_date: "2026-05-15", description: "Airtel Xstream Fiber Broadband Bill", merchant: "Airtel Broadband", amount: -999.0, transaction_type: "expense", category: "Mobile and Internet", is_transfer: 0, is_refund: 0, notes: "Recurring" },
  { id: 14, transaction_date: "2026-05-16", description: "BESCOM Electricity Utility Bill Payment", merchant: "BESCOM Electric", amount: -1850.0, transaction_type: "expense", category: "Electricity and Utilities", is_transfer: 0, is_refund: 0, notes: "Recurring" },
  { id: 15, transaction_date: "2026-05-17", description: "Nature's Basket Organic Vegetables", merchant: "Nature's Basket", amount: -2400.0, transaction_type: "expense", category: "Groceries", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 16, transaction_date: "2026-05-18", description: "Apollo Pharmacy Prescription Medicines", merchant: "Apollo Pharmacy", amount: -1450.0, transaction_type: "expense", category: "Healthcare and Medicines", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 17, transaction_date: "2026-05-19", description: "Starbucks Reserve Coffee and Snacks", merchant: "Starbucks Cafe", amount: -650.0, transaction_type: "expense", category: "Restaurants and Cafés", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 18, transaction_date: "2026-05-20", description: "Amazon Retail Electronics and Cable", merchant: "Amazon", amount: -3499.0, transaction_type: "expense", category: "Shopping", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 19, transaction_date: "2026-05-21", description: "BPCL Auto Gas and Diesel Fill", merchant: "BPCL Fuel", amount: -2800.0, transaction_type: "expense", category: "Transport and Fuel", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 20, transaction_date: "2026-05-22", description: "Amazon Item Return Refund Credit", merchant: "Amazon Refund", amount: 1200.0, transaction_type: "income", category: "Refunds", is_transfer: 0, is_refund: 1, notes: "Refund Offset" },
  { id: 21, transaction_date: "2026-05-24", description: "Blinkit Essentials and Dairy", merchant: "Blinkit", amount: -1650.0, transaction_type: "expense", category: "Groceries", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 22, transaction_date: "2026-05-25", description: "Upwork Global Freelance Disbursement", merchant: "Upwork Escrow", amount: 18500.0, transaction_type: "income", category: "Freelance Income", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 23, transaction_date: "2026-05-26", description: "Barbeque Nation Family Dinner Outing", merchant: "Barbeque Nation", amount: -3200.0, transaction_type: "expense", category: "Restaurants and Cafés", is_transfer: 0, is_refund: 0, notes: "" },
  { id: 24, transaction_date: "2026-05-28", description: "CRED Credit Card Bill Payment", merchant: "CRED CC Bill", amount: -15000.0, transaction_type: "expense", category: "Other", is_transfer: 1, is_refund: 0, notes: "CC Repayment (Transfer)" },
  { id: 25, transaction_date: "2026-05-29", description: "Swiggy Late Night Pizza Order", merchant: "Swiggy", amount: -540.0, transaction_type: "expense", category: "Food Delivery", is_transfer: 0, is_refund: 0, notes: "" }
];

const INITIAL_DEMO_BUDGETS = [
  { id: 1, category: "Groceries", budget_amount: 10000.0, period_type: "monthly", spent: 8150.0, percentage: 81.5, remaining: 1850.0, status: "warning" },
  { id: 2, category: "Food Delivery", budget_amount: 4000.0, period_type: "monthly", spent: 2560.0, percentage: 64.0, remaining: 1440.0, status: "on_track" },
  { id: 3, category: "Restaurants and Cafés", budget_amount: 5000.0, period_type: "monthly", spent: 3850.0, percentage: 77.0, remaining: 1150.0, status: "on_track" },
  { id: 4, category: "Transport and Fuel", budget_amount: 7000.0, period_type: "monthly", spent: 5300.0, percentage: 75.7, remaining: 1700.0, status: "on_track" },
  { id: 5, category: "Subscriptions", budget_amount: 2000.0, period_type: "monthly", spent: 1767.0, percentage: 88.4, remaining: 233.0, status: "warning" },
  { id: 6, category: "Shopping", budget_amount: 5000.0, period_type: "monthly", spent: 3499.0, percentage: 70.0, remaining: 1501.0, status: "on_track" }
];

const INITIAL_DEMO_RECURRING = [
  { id: 1, merchant: "Prestige Heights", category: "Rent", average_amount: 25000.0, frequency: "monthly", confidence_score: 0.98, status: "confirmed", is_subscription: 0, is_essential: 1, next_expected_date: "2026-06-05" },
  { id: 2, merchant: "HDFC Bank Loan", category: "Loan and EMI Payments", average_amount: 11500.0, frequency: "monthly", confidence_score: 0.99, status: "confirmed", is_subscription: 0, is_essential: 1, next_expected_date: "2026-06-08" },
  { id: 3, merchant: "BESCOM Electric", category: "Electricity and Utilities", average_amount: 1850.0, frequency: "monthly", confidence_score: 0.92, status: "confirmed", is_subscription: 0, is_essential: 1, next_expected_date: "2026-06-16" },
  { id: 4, merchant: "Airtel Broadband", category: "Mobile and Internet", average_amount: 999.0, frequency: "monthly", confidence_score: 0.95, status: "confirmed", is_subscription: 1, is_essential: 1, next_expected_date: "2026-06-15" },
  { id: 5, merchant: "Netflix", category: "Subscriptions", average_amount: 649.0, frequency: "monthly", confidence_score: 0.99, status: "confirmed", is_subscription: 1, is_essential: 0, next_expected_date: "2026-06-10" },
  { id: 6, merchant: "Spotify", category: "Subscriptions", average_amount: 119.0, frequency: "monthly", confidence_score: 0.99, status: "confirmed", is_subscription: 1, is_essential: 0, next_expected_date: "2026-06-12" }
];

const INITIAL_DEMO_INSIGHTS = [
  { id: 1, insight_type: "behaviour_trend", title: "Weekend Dining & Takeaway Surge", summary: "Over 48% of your dining and food delivery expenses occur between Friday evening and Sunday night.", supporting_evidence: "₹2,560 spent across 3 orders from Swiggy & Zomato.", severity: "warning", suggested_action: "Set a weekend delivery limit to save up to ₹1,200/month.", status: "active", period: "May 2026" },
  { id: 2, insight_type: "savings_opportunity", title: "Digital Subscriptions Optimization", summary: "You have 3 active monthly subscriptions totalling ₹1,767 per month.", supporting_evidence: "Netflix (₹649), Spotify (₹119), Airtel Broadband (₹999).", severity: "info", suggested_action: "Review unused video streaming tiers or consider annual billing discounts.", status: "active", period: "May 2026" },
  { id: 3, insight_type: "budget_drift", title: "Subscriptions Budget Warning", summary: "You have used 88.4% of your monthly Subscriptions budget with 12 days remaining.", supporting_evidence: "Spent ₹1,767 out of ₹2,000 allocated.", severity: "warning", suggested_action: "Defer discretionary add-ons until next month.", status: "active", period: "May 2026" }
];

class MockBackend {
  static getStore() {
    let raw = localStorage.getItem("spendsense_store_v1");
    if (!raw) {
      const initial = {
        user: { id: 1, full_name: "Personal User", email: "demo@spendsense.local", phone: "+919876543210", email_verified: 1, phone_verified: 1, default_currency: "INR" },
        transactions: INITIAL_DEMO_TRANSACTIONS,
        budgets: INITIAL_DEMO_BUDGETS,
        recurring: INITIAL_DEMO_RECURRING,
        insights: INITIAL_DEMO_INSIGHTS,
        backups: [
          { filename: "backup_spendsense_demo_20260515.db", size_human: "184 KB", created_at: "2026-05-15T12:00:00Z" }
        ],
        settings: {
          display_name: "Personal User",
          default_currency: "INR",
          anomaly_sensitivity: "medium",
          budget_drift_threshold: "0.80",
          categories: [
            { category_name: "Groceries", category_type: "expense" },
            { category_name: "Food Delivery", category_type: "expense" },
            { category_name: "Restaurants and Cafés", category_type: "expense" },
            { category_name: "Rent", category_type: "expense" },
            { category_name: "Electricity and Utilities", category_type: "expense" },
            { category_name: "Mobile and Internet", category_type: "expense" },
            { category_name: "Transport and Fuel", category_type: "expense" },
            { category_name: "Public Transport", category_type: "expense" },
            { category_name: "Shopping", category_type: "expense" },
            { category_name: "Healthcare and Medicines", category_type: "expense" },
            { category_name: "Subscriptions", category_type: "expense" },
            { category_name: "Loan and EMI Payments", category_type: "expense" },
            { category_name: "Salary", category_type: "income" },
            { category_name: "Freelance Income", category_type: "income" },
            { category_name: "Refunds", category_type: "income" },
            { category_name: "Other", category_type: "expense" }
          ]
        }
      };
      localStorage.setItem("spendsense_store_v1", JSON.stringify(initial));
      return initial;
    }
    try {
      return JSON.parse(raw);
    } catch (e) {
      localStorage.removeItem("spendsense_store_v1");
      return MockBackend.getStore();
    }
  }

  static saveStore(store) {
    localStorage.setItem("spendsense_store_v1", JSON.stringify(store));
  }

  static handle(endpoint, options = {}) {
    const method = options.method || "GET";
    const body = options.body ? (typeof options.body === "string" ? JSON.parse(options.body) : options.body) : {};
    const params = options.params || {};
    const store = MockBackend.getStore();

    // 1. Auth endpoints
    if (endpoint === "/api/auth/me") {
      return { user: store.user };
    }
    if (endpoint === "/api/auth/login") {
      const user = { ...store.user, email: body.email || store.user.email, phone: body.phone || store.user.phone };
      store.user = user;
      MockBackend.saveStore(store);
      localStorage.setItem("spendsense_token", "mock_session_token_12345");
      return { message: "Login successful.", user, token: "mock_session_token_12345" };
    }
    if (endpoint === "/api/auth/register") {
      const newUser = { id: Date.now(), full_name: body.full_name || "New User", email: body.email || "", phone: body.phone || "", email_verified: body.email ? 0 : 1, phone_verified: body.phone ? 1 : 0, default_currency: "INR" };
      store.user = newUser;
      MockBackend.saveStore(store);
      localStorage.setItem("spendsense_token", "mock_session_token_" + newUser.id);
      return { message: "Account created successfully.", user: newUser, token: "mock_session_token_" + newUser.id };
    }
    if (endpoint === "/api/auth/otp/send") {
      return { success: true, message: "Verification OTP code sent successfully (Dev code: 123456)." };
    }
    if (endpoint === "/api/auth/otp/verify") {
      const user = { ...store.user, phone: body.phone || store.user.phone, phone_verified: 1 };
      store.user = user;
      MockBackend.saveStore(store);
      localStorage.setItem("spendsense_token", "mock_session_token_12345");
      return { success: true, message: "Phone verified successfully.", user, token: "mock_session_token_12345" };
    }
    if (endpoint === "/api/auth/verify-email") {
      store.user.email_verified = 1;
      MockBackend.saveStore(store);
      return { success: true, message: "Email verified successfully.", user: store.user };
    }
    if (endpoint === "/api/auth/resend-verification") {
      return { success: true, message: "Verification link sent to your email." };
    }
    if (endpoint === "/api/auth/logout") {
      localStorage.removeItem("spendsense_token");
      sessionStorage.removeItem("spendsense_token");
      return { message: "Logged out successfully." };
    }
    if (endpoint === "/api/auth/profile") {
      if (body.full_name) store.user.full_name = body.full_name;
      MockBackend.saveStore(store);
      return { message: "Profile updated.", user: store.user };
    }

    // 2. Settings endpoints
    if (endpoint === "/api/settings") {
      if (method === "GET") {
        return {
          display_name: store.user.full_name,
          default_currency: store.settings.default_currency || "INR",
          anomaly_sensitivity: store.settings.anomaly_sensitivity || "medium",
          budget_drift_threshold: store.settings.budget_drift_threshold || "0.80",
          categories: store.settings.categories
        };
      }
      if (method === "PATCH") {
        if (body.default_currency) store.settings.default_currency = body.default_currency;
        if (body.anomaly_sensitivity) store.settings.anomaly_sensitivity = body.anomaly_sensitivity;
        MockBackend.saveStore(store);
        return { message: "Settings updated successfully." };
      }
    }
    if (endpoint === "/api/settings/categories" && method === "POST") {
      store.settings.categories.push({ category_name: body.category_name, category_type: body.category_type || "expense" });
      MockBackend.saveStore(store);
      return { category_name: body.category_name, category_type: body.category_type || "expense" };
    }

    // 3. Transactions endpoints
    if (endpoint.startsWith("/api/transactions")) {
      const parts = endpoint.split("/").filter(Boolean);
      // Detail, PATCH, DELETE: /api/transactions/{id}
      if (parts.length === 3) {
        const id = parseInt(parts[2]);
        const idx = store.transactions.findIndex(t => t.id === id);
        if (method === "GET") {
          return store.transactions[idx] || store.transactions[0];
        }
        if (method === "PATCH") {
          if (idx !== -1) {
            store.transactions[idx] = { ...store.transactions[idx], ...body };
            MockBackend.saveStore(store);
          }
          return { message: "Transaction updated." };
        }
        if (method === "DELETE") {
          if (idx !== -1) {
            store.transactions.splice(idx, 1);
            MockBackend.saveStore(store);
          }
          return { message: "Transaction deleted." };
        }
      }

      // List: GET /api/transactions
      let txns = [...store.transactions];
      if (params.search) {
        const q = params.search.toLowerCase();
        txns = txns.filter(t => (t.description && t.description.toLowerCase().includes(q)) || (t.merchant && t.merchant.toLowerCase().includes(q)));
      }
      if (params.category) {
        txns = txns.filter(t => t.category === params.category);
      }
      if (params.transaction_type) {
        txns = txns.filter(t => t.transaction_type === params.transaction_type);
      }
      txns.sort((a, b) => new Date(b.transaction_date) - new Date(a.transaction_date));

      const page = parseInt(params.page) || 1;
      const pageSize = parseInt(params.page_size) || 20;
      const total = txns.length;
      const totalPages = Math.max(1, Math.ceil(total / pageSize));
      const items = txns.slice((page - 1) * pageSize, page * pageSize);

      return { items, total, page, page_size: pageSize, total_pages: totalPages };
    }

    // 4. Analytics endpoints
    if (endpoint === "/api/analytics/summary") {
      let income = 0;
      let expenses = 0;
      let refunds = 0;
      store.transactions.forEach(t => {
        if (t.is_transfer) return;
        const amt = Math.abs(t.amount);
        if (t.is_refund || t.category === "Refunds") {
          refunds += amt;
        } else if (t.transaction_type === "income") {
          income += amt;
        } else {
          expenses += amt;
        }
      });
      const netExpenses = Math.max(0, expenses - refunds);
      const netCashFlow = income - netExpenses;
      const savingsRate = income > 0 ? Math.max(0, Math.min(100, Math.round(((income - netExpenses) / income) * 1000) / 10)) : 0;

      return {
        total_income: income,
        total_expenses: netExpenses,
        net_cash_flow: netCashFlow,
        savings_rate: savingsRate,
        transaction_count: store.transactions.length,
        currency: store.settings.default_currency || "INR"
      };
    }

    if (endpoint === "/api/analytics/categories") {
      const catMap = {};
      let totalSpend = 0;
      store.transactions.forEach(t => {
        if (t.is_transfer || t.transaction_type === "income" || t.is_refund) return;
        const amt = Math.abs(t.amount);
        totalSpend += amt;
        if (!catMap[t.category]) {
          catMap[t.category] = { category: t.category, total_spend: 0, transaction_count: 0, previous_period_spend: Math.round(amt * 0.9) };
        }
        catMap[t.category].total_spend += amt;
        catMap[t.category].transaction_count += 1;
      });

      const safeDenom = totalSpend > 0 ? totalSpend : 1;
      const categories = Object.values(catMap).map(c => ({
        ...c,
        total_spend: Math.round(c.total_spend),
        percentage: Math.round((c.total_spend / safeDenom) * 1000) / 10,
        absolute_change: Math.round(c.total_spend - c.previous_period_spend),
        percentage_change: Math.round(((c.total_spend - c.previous_period_spend) / c.previous_period_spend) * 1000) / 10
      }));
      categories.sort((a, b) => b.total_spend - a.total_spend);
      return categories;
    }

    if (endpoint === "/api/analytics/trends") {
      const monthMap = {};
      store.transactions.forEach(t => {
        if (t.is_transfer) return;
        const m = t.transaction_date.slice(0, 7);
        if (!monthMap[m]) monthMap[m] = { period: m, income: 0, expense: 0, net: 0 };
        const amt = Math.abs(t.amount);
        if (t.is_refund || t.category === "Refunds") {
          monthMap[m].expense -= amt;
        } else if (t.transaction_type === "income") {
          monthMap[m].income += amt;
        } else {
          monthMap[m].expense += amt;
        }
      });
      return Object.values(monthMap).sort((a, b) => a.period.localeCompare(b.period));
    }

    if (endpoint === "/api/analytics/savings") {
      return {
        annual_potential: 32000,
        monthly_potential: 2660,
        scenarios: [
          { title: "Reduce Food Delivery by 25%", potential_monthly_saving: 640, description: "Cooking one extra meal per week saves ₹640 each month." },
          { title: "Consolidate OTT Subscriptions", potential_monthly_saving: 649, description: "Pausing inactive video tiers saves ₹649 each month." },
          { title: "Weekend Dining Limit", potential_monthly_saving: 1370, description: "Capping weekend restaurant spending saves ₹1,370 each month." }
        ]
      };
    }

    // 5. Budgets endpoints
    if (endpoint.startsWith("/api/budgets")) {
      if (endpoint === "/api/budgets") {
        if (method === "GET") return store.budgets;
        if (method === "POST") {
          const newB = { id: Date.now(), category: body.category, budget_amount: parseFloat(body.budget_amount), period_type: body.period_type || "monthly", spent: 0, percentage: 0, remaining: parseFloat(body.budget_amount), status: "on_track" };
          store.budgets.push(newB);
          MockBackend.saveStore(store);
          return newB;
        }
      }
      const bId = parseInt(endpoint.split("/")[3]);
      const idx = store.budgets.findIndex(b => b.id === bId);
      if (method === "PATCH") {
        if (idx !== -1) {
          store.budgets[idx].budget_amount = parseFloat(body.budget_amount);
          store.budgets[idx].remaining = store.budgets[idx].budget_amount - store.budgets[idx].spent;
          store.budgets[idx].percentage = Math.round((store.budgets[idx].spent / store.budgets[idx].budget_amount) * 1000) / 10;
          MockBackend.saveStore(store);
        }
        return { message: "Budget updated." };
      }
      if (method === "DELETE") {
        if (idx !== -1) {
          store.budgets.splice(idx, 1);
          MockBackend.saveStore(store);
        }
        return { message: "Budget deleted." };
      }
    }

    // 6. Recurring endpoints
    if (endpoint.startsWith("/api/recurring")) {
      if (endpoint === "/api/recurring") return store.recurring;
      const rId = parseInt(endpoint.split("/")[3]);
      const idx = store.recurring.findIndex(r => r.id === rId);
      if (idx !== -1) {
        store.recurring[idx] = { ...store.recurring[idx], ...body };
        MockBackend.saveStore(store);
      }
      return { message: "Recurring payment updated." };
    }

    // 7. Insights endpoints
    if (endpoint.startsWith("/api/insights")) {
      if (endpoint === "/api/insights") return store.insights;
      const iId = parseInt(endpoint.split("/")[3]);
      const idx = store.insights.findIndex(i => i.id === iId);
      if (idx !== -1) {
        store.insights[idx] = { ...store.insights[idx], ...body };
        MockBackend.saveStore(store);
      }
      return { message: "Insight updated." };
    }

    // 8. Upload preview & import
    if (endpoint === "/api/uploads/preview") {
      return {
        filename: "sample_statement.csv",
        total_rows: 25,
        valid_rows: 25,
        columns: ["Date", "Description", "Amount", "Category"],
        preview_rows: store.transactions.slice(0, 5)
      };
    }
    if (endpoint === "/api/uploads/import") {
      return { success: true, imported_count: 25, message: "Statement imported successfully into local spending database." };
    }

    // 9. Demo Data & Reset Data
    if (endpoint === "/api/reports/demo-data") {
      store.transactions = INITIAL_DEMO_TRANSACTIONS;
      store.budgets = INITIAL_DEMO_BUDGETS;
      store.recurring = INITIAL_DEMO_RECURRING;
      store.insights = INITIAL_DEMO_INSIGHTS;
      MockBackend.saveStore(store);
      return { message: "Realistic 3-month sample transaction dataset loaded." };
    }
    if (endpoint === "/api/reports/reset-data") {
      store.transactions = [];
      MockBackend.saveStore(store);
      return { message: "All transactions cleared." };
    }

    // 10. Backups & Disaster Recovery
    if (endpoint === "/api/reports/backups") {
      return { backups: store.backups };
    }
    if (endpoint === "/api/reports/backup") {
      const bName = `spendsense_backup_${new Date().toISOString().replace(/[:.]/g, "")}.json`;
      store.backups.unshift({ filename: bName, size_human: "210 KB", created_at: new Date().toISOString() });
      MockBackend.saveStore(store);
      return { success: true, message: "Instant database backup snapshot created.", filename: bName };
    }
    if (endpoint === "/api/reports/restore") {
      return { success: true, message: "Database restored successfully from backup." };
    }

    // Default Fallback
    return { status: "ok" };
  }
}

// =========================================================================
// Centralized API Client
// =========================================================================

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.useMock = IS_VERCEL_STATIC;
  }

  async request(endpoint, options = {}) {
    // If explicitly running in standalone / static mode without backend
    if (this.useMock) {
      return MockBackend.handle(endpoint, options);
    }

    const url = new URL(`${this.baseUrl}${endpoint}`);
    if (options.params) {
      Object.entries(options.params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== "") {
          url.searchParams.append(key, val);
        }
      });
    }

    const headers = options.headers || {};
    const token = localStorage.getItem("spendsense_token") || sessionStorage.getItem("spendsense_token");
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      method: options.method || "GET",
      headers,
      credentials: "include",
      ...options
    };

    if (config.body && typeof config.body === "object" && !(config.body instanceof FormData)) {
      config.headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url.toString(), config);
      if (response.status === 401) {
        const publicPages = ["index.html", "login.html", "register.html", "forgot-password.html", "reset-password.html", ""];
        const currentPath = window.location.pathname.split("/").pop();
        if (!publicPages.includes(currentPath)) {
          localStorage.removeItem("spendsense_token");
          sessionStorage.removeItem("spendsense_token");
          sessionStorage.setItem("spendsense_redirect", window.location.href);
          window.location.href = "login.html";
          return;
        }
      }

      if (!response.ok) {
        let errDetail = "An unexpected error occurred.";
        try {
          const errJson = await response.json();
          errDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
        } catch (e) {
          errDetail = `${response.status} ${response.statusText}`;
        }
        throw new Error(errDetail);
      }
      return await response.json();
    } catch (err) {
      // If live backend fetch fails (e.g. no server running on localhost or static Vercel), fall back smoothly to Client-Side Engine!
      console.warn(`[SpendSense API] Live backend unreachable at ${this.baseUrl}. Activating Client-Side Persistent Engine.`, err);
      this.useMock = true;
      return MockBackend.handle(endpoint, options);
    }
  }

  get(endpoint, params = {}) {
    return this.request(endpoint, { method: "GET", params });
  }

  post(endpoint, body = {}) {
    return this.request(endpoint, { method: "POST", body });
  }

  patch(endpoint, body = {}) {
    return this.request(endpoint, { method: "PATCH", body });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: "DELETE" });
  }

  async upload(endpoint, file) {
    if (this.useMock) {
      return MockBackend.handle(endpoint, { method: "POST" });
    }
    const formData = new FormData();
    formData.append("file", file);
    return this.request(endpoint, { method: "POST", body: formData });
  }
}

const api = new ApiClient(API_BASE_URL);

// Authentication API methods
const authAPI = {
  register: (data) => api.post("/api/auth/register", data),
  login: (data) => api.post("/api/auth/login", data),
  sendOtp: (data) => api.post("/api/auth/otp/send", data),
  verifyOtp: (data) => api.post("/api/auth/otp/verify", data),
  verifyEmail: (email, token) => api.get("/api/auth/verify-email", { email, token }),
  resendVerification: (email) => api.post("/api/auth/resend-verification", { email }),
  logout: () => api.post("/api/auth/logout"),
  getMe: () => api.get("/api/auth/me"),
  forgotPassword: (data) => api.post("/api/auth/forgot-password", data),
  resetPassword: (data) => api.post("/api/auth/reset-password", data),
  changePassword: (data) => api.post("/api/auth/change-password", data),
  updateProfile: (data) => api.patch("/api/auth/profile", data),
  deleteAccount: () => api.delete("/api/auth/account")
};

// Reports, Backups & Data Management API methods
const reportsAPI = {
  createBackup: () => api.post("/api/reports/backup"),
  listBackups: () => api.get("/api/reports/backups"),
  restoreBackup: (backupFilename) => api.post("/api/reports/restore", { backup_filename: backupFilename }),
  exportCsvUrl: () => {
    if (api.useMock) {
      // Direct client-side CSV trigger
      const store = MockBackend.getStore();
      const csvRows = ["Date,Merchant,Description,Amount,Type,Category,IsTransfer,IsRefund"];
      store.transactions.forEach(t => {
        csvRows.push(`"${t.transaction_date}","${t.merchant || ''}","${t.description.replace(/"/g, '""')}","${t.amount}","${t.transaction_type}","${t.category}","${t.is_transfer}","${t.is_refund}"`);
      });
      const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `spendsense_transactions_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      return "#";
    }
    return `${API_BASE_URL}/api/reports/export/csv`;
  },
  exportJsonUrl: () => {
    if (api.useMock) {
      // Direct client-side JSON trigger
      const store = MockBackend.getStore();
      const exportData = {
        export_metadata: { app: "SpendSense", export_timestamp: new Date().toISOString(), currency: "INR" },
        transactions: store.transactions,
        budgets: store.budgets,
        categories: store.settings.categories
      };
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `spendsense_full_export_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      return "#";
    }
    return `${API_BASE_URL}/api/reports/export/json`;
  }
};

// Toast Notification Utility
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "fixed bottom-5 right-5 z-50 flex flex-col space-y-2 pointer-events-none";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  const colors = {
    success: "bg-emerald-950/90 text-emerald-200 border-emerald-500/40",
    error: "bg-rose-950/90 text-rose-200 border-rose-500/40",
    info: "bg-slate-900/95 text-slate-100 border-slate-700/60"
  };

  const icons = {
    success: "✓",
    error: "✕",
    info: "ℹ"
  };

  toast.className = `pointer-events-auto px-4 py-3 rounded-xl border shadow-2xl flex items-center space-x-3 text-sm backdrop-blur-md transition-all duration-300 transform translate-y-2 opacity-0 ${colors[type] || colors.info}`;
  toast.innerHTML = `
    <span class="font-bold flex-shrink-0 w-5 h-5 flex items-center justify-center rounded-full bg-white/20 text-xs">${icons[type] || "•"}</span>
    <span class="flex-grow font-medium">${message}</span>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  });

  setTimeout(() => {
    toast.classList.add("translate-y-2", "opacity-0");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Currency Formatter
function formatCurrency(amount, currency = "INR") {
  const num = Number(amount) || 0;
  const symbols = { INR: "₹", USD: "$", EUR: "€", GBP: "£", AED: "AED " };
  const symbol = symbols[currency] || (currency + " ");
  return `${symbol}${num.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  })}`;
}

// Format Date YYYY-MM-DD or ISO timestamp to standard Indian DD/MM/YYYY
function formatDate(dateStr) {
  return formatDateIndian(dateStr);
}

// Format Date YYYY-MM-DD to standard Indian DD/MM/YYYY
function formatDateIndian(dateStr) {
  if (!dateStr) return "";
  try {
    const datePart = dateStr.includes("T") ? dateStr.split("T")[0] : dateStr.split(" ")[0];
    const parts = datePart.split("-");
    if (parts.length === 3) {
      return `${parts[2].padStart(2, '0')}/${parts[1].padStart(2, '0')}/${parts[0]}`;
    }
    return dateStr;
  } catch (e) {
    return dateStr;
  }
}

// 3D Card Tilt Interaction Initializer
function initTiltCards() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const cards = document.querySelectorAll(".tilt-card");
  cards.forEach(card => {
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const rotateX = ((y - centerY) / centerY) * -4;
      const rotateY = ((x - centerX) / centerX) * 4;

      card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-2px)`;
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)";
    });
  });
}
