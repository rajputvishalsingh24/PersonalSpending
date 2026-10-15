/**
 * SpendSense Centralized API Client & Utility Library
 * Supports HttpOnly Session Cookies & Bearer Token Authentication
 */

const API_BASE_URL = (() => {
  // If running from FastAPI server
  if (window.location.port === "8000" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return window.location.origin;
  }
  // Default development backend URL
  return "http://localhost:8000";
})();

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    if (options.params) {
      Object.entries(options.params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== "") {
          url.searchParams.append(key, val);
        }
      });
    }

    const headers = options.headers || {};

    // Token fallback from storage if available
    const token = localStorage.getItem("spendsense_token") || sessionStorage.getItem("spendsense_token");
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      method: options.method || "GET",
      headers,
      credentials: "include", // Essential for HttpOnly session cookie delivery
      ...options
    };

    if (config.body && typeof config.body === "object" && !(config.body instanceof FormData)) {
      config.headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url.toString(), config);
      
      // Handle 401 Unauthorized for protected pages
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
      console.error(`API Error on [${config.method} ${endpoint}]:`, err);
      throw err;
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
    const formData = new FormData();
    formData.append("file", file);
    return this.request(endpoint, {
      method: "POST",
      body: formData
    });
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
  exportCsvUrl: () => `${API_BASE_URL}/api/reports/export/csv`,
  exportJsonUrl: () => `${API_BASE_URL}/api/reports/export/json`
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
