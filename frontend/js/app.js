/**
 * SpendSense Main Application Controller & Motion / Navigation / Auth System
 */

const DOODLES = {
  coin: `
    <svg class="w-12 h-12 text-amber-500 doodle-float" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2.5" fill="#FEF3C7" fill-opacity="0.6"/>
      <circle cx="24" cy="24" r="15" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 3"/>
      <path d="M22 16H27M24 16V32M21 32H27" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    </svg>
  `,
  rupee: `
    <div class="doodle-coin-3d w-14 h-14 rounded-full bg-gradient-to-tr from-amber-400 via-amber-300 to-amber-500 shadow-xl border-2 border-amber-200/90 flex items-center justify-center text-amber-950 font-black text-2xl select-none">
      ₹
    </div>
  `,
  trending: `
    <div class="float-levitate w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 shadow-lg flex items-center justify-center text-white">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
    </div>
  `,
  shield: `
    <div class="float-levitate w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 shadow-lg flex items-center justify-center text-white glow-pulse">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
    </div>
  `,
  receipt: `
    <svg class="w-12 h-12 text-slate-500 doodle-bob" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 8H34V40L30 37L26 40L24 37L20 40L16 37L14 40V8Z" stroke="currentColor" stroke-width="2" fill="#F8FAFC"/>
      <line x1="18" y1="16" x2="30" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="18" y1="22" x2="26" y2="22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="18" y1="28" x2="28" y2="28" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `,
  sparkle: `
    <svg class="w-6 h-6 text-purple-400 doodle-twinkle" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="currentColor"/>
    </svg>
  `,
  piggy: `
    <svg class="w-14 h-14 text-emerald-600 doodle-float-alt" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M38 24C38 31.732 31.732 38 24 38C19.5 38 15 36 12 32L6 33L8 28C6.5 25.5 6 23 6 20C6 12.268 14 8 24 8C34 8 38 16 38 24Z" stroke="currentColor" stroke-width="2.5" fill="#ECFDF5"/>
      <circle cx="16" cy="18" r="2" fill="currentColor"/>
      <line x1="22" y1="14" x2="26" y2="14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <path d="M14 38V42M30 38V42" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    </svg>
  `,
  wallet: `
    <svg class="w-12 h-12 text-indigo-500 doodle-float" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="14" width="32" height="22" rx="4" stroke="currentColor" stroke-width="2.5" fill="#EEF2FF"/>
      <path d="M8 20C8 17 11 14 14 14H34C37 14 40 17 40 20" stroke="currentColor" stroke-width="2"/>
      <path d="M30 22H38V28H30C28.3431 28 27 26.6569 27 25C27 23.3431 28.3431 22 30 22Z" fill="currentColor" stroke="currentColor" stroke-width="1.5"/>
      <circle cx="33" cy="25" r="1.5" fill="#FFFFFF"/>
    </svg>
  `
};

let currentAuthenticatedUser = null;

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Render all declarative moving doodles
  document.querySelectorAll("[data-doodle]").forEach(el => {
    const key = el.getAttribute("data-doodle");
    if (DOODLES[key]) {
      el.innerHTML = DOODLES[key];
    }
  });

  // 2. Initialize 3D Perspective Tilt on metric cards
  initTiltCards();

  // 3. Initialize scroll entrance reveals
  initScrollReveals();

  // 4. Auto-initialize animated number counters
  document.querySelectorAll("[data-counter]").forEach(el => {
    const val = parseFloat(el.getAttribute("data-counter")) || 0;
    const prefix = el.getAttribute("data-prefix") ?? "₹";
    const suffix = el.getAttribute("data-suffix") ?? "";
    animateCounter(el, val, 950, prefix, suffix);
  });

  // 3. Highlight active page in sidebar
  const currentPath = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-link").forEach(link => {
    const href = link.getAttribute("href");
    if (href === currentPath || (currentPath === "" && href === "index.html")) {
      link.classList.add("bg-slate-900", "text-white", "shadow-sm");
      link.classList.remove("text-slate-600", "hover:bg-slate-100");
    }
  });

  // 4. Setup Mobile Drawer Toggle
  const mobileMenuBtn = document.getElementById("mobile-menu-toggle");
  const sidebar = document.getElementById("sidebar-navigation");
  const backdrop = document.getElementById("mobile-drawer-backdrop");

  if (mobileMenuBtn && sidebar) {
    mobileMenuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("-translate-x-full");
      if (backdrop) backdrop.classList.toggle("hidden");
    });
  }
  if (backdrop && sidebar) {
    backdrop.addEventListener("click", () => {
      sidebar.classList.add("-translate-x-full");
      backdrop.classList.add("hidden");
    });
  }

  // 5. Auth State & Global Header Initialization
  await checkGlobalAuth(currentPath);

  // 6. Global Demo Data Loader CTA button
  const loadDemoBtn = document.getElementById("btn-load-demo-data");
  if (loadDemoBtn) {
    loadDemoBtn.addEventListener("click", async () => {
      try {
        loadDemoBtn.disabled = true;
        loadDemoBtn.innerText = "Loading Demo...";

        // If unauthenticated, log in as demo account first
        if (!currentAuthenticatedUser) {
          try {
            const loginRes = await authAPI.login({
              email: "demo@spendsense.local",
              password: "demo123"
            });
            if (loginRes.session_token) {
              sessionStorage.setItem("spendsense_token", loginRes.session_token);
            }
          } catch (loginErr) {
            // Demo account fallback, proceed to load data
          }
        }

        const res = await api.post("/api/reports/demo-data");
        triggerConfetti();
        showToast(res.message || "Demonstration dataset loaded!", "success");
        setTimeout(() => window.location.href = "dashboard.html", 600);
      } catch (err) {
        showToast(err.message || "Failed to load demo data", "error");
        loadDemoBtn.disabled = false;
        loadDemoBtn.innerText = "Explore Demo Data";
      }
    });
  }

  // 7. Global Reset Data CTA
  const resetDataBtn = document.getElementById("btn-reset-all-data");
  if (resetDataBtn) {
    resetDataBtn.addEventListener("click", async () => {
      if (!confirm("WARNING: This will permanently delete your imported transactions, uploads, and budgets.\n\nAre you sure you want to proceed?")) return;
      try {
        const res = await api.post("/api/reports/reset-data");
        showToast(res.message, "info");
        setTimeout(() => window.location.reload(), 600);
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 8. Global Logout Button Handler
  document.querySelectorAll(".btn-global-logout, #btn-sidebar-logout, #dropdown-logout").forEach(btn => {
    btn.addEventListener("click", async () => {
      try {
        await authAPI.logout();
      } catch (e) {}
      localStorage.removeItem("spendsense_token");
      sessionStorage.removeItem("spendsense_token");
      showToast("Signed out safely.", "info");
      setTimeout(() => window.location.href = "login.html", 400);
    });
  });
});

/**
 * Check authentication and dynamically populate page header
 */
async function checkGlobalAuth(currentPath) {
  const publicPages = ["index.html", "login.html", "register.html", "forgot-password.html", "reset-password.html", ""];
  const isPublicPage = publicPages.includes(currentPath);

  try {
    let user = await authAPI.getMe();
    if (user && user.user) user = user.user;
    currentAuthenticatedUser = user;

    const fullName = user?.full_name || user?.display_name || "SpendSense User";
    const displayName = user?.display_name || (fullName ? fullName.split(" ")[0] : "User");

    // If on landing page (index.html), customize nav buttons & hero CTAs
    if (currentPath === "index.html" || currentPath === "") {
      const authNavContainer = document.getElementById("landing-auth-nav");
      if (authNavContainer) {
        const initial = (fullName || "U")[0].toUpperCase();
        authNavContainer.innerHTML = `
          <a href="dashboard.html" class="px-4 py-2 text-sm font-semibold rounded-xl text-slate-700 bg-slate-100 hover:bg-slate-200 transition-all border border-slate-200 flex items-center space-x-2">
            <span>Dashboard</span>
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          </a>
          <a href="profile.html" class="w-9 h-9 rounded-xl bg-slate-900 text-white font-bold flex items-center justify-center text-sm shadow hover:scale-105 transition-transform" title="${fullName}">
            ${initial}
          </a>
        `;
      }

      const heroPrimary = document.getElementById("hero-cta-primary");
      if (heroPrimary) {
        heroPrimary.href = "dashboard.html";
        heroPrimary.innerHTML = `<span>Go to Dashboard</span><svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>`;
      }
      const heroSecondary = document.getElementById("hero-cta-secondary");
      if (heroSecondary) {
        heroSecondary.href = "upload.html";
        heroSecondary.innerText = "Upload Statement";
      }
    }

    // Populate user info in header on protected pages
    const headerUserName = document.getElementById("header-user-name");
    if (headerUserName && user) {
      headerUserName.innerText = displayName;
    }

    // Insert user dropdown menu into header if placeholder exists
    renderHeaderUserDropdown(user);

  } catch (err) {
    currentAuthenticatedUser = null;

    // If protected page and unauthenticated, redirect to login
    if (!isPublicPage) {
      sessionStorage.setItem("spendsense_redirect", window.location.href);
      window.location.href = "login.html";
    }
  }
}

/**
 * Renders user avatar and dropdown menu in the header
 */
function renderHeaderUserDropdown(user) {
  const target = document.getElementById("header-user-menu-container");
  if (!target || !user) return;

  const fullName = user.full_name || user.display_name || "SpendSense User";
  const displayName = user.display_name || (fullName ? fullName.split(" ")[0] : "User");

  const initials = (fullName || "U")
    .split(" ")
    .filter(Boolean)
    .map(p => p[0])
    .join("")
    .substring(0, 2)
    .toUpperCase() || "U";

  target.innerHTML = `
    <div class="relative inline-block text-left" id="user-dropdown-wrapper">
      <button id="user-menu-btn" type="button" class="flex items-center space-x-2 p-1.5 rounded-xl hover:bg-slate-100 transition-colors focus:outline-none">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-700 to-indigo-600 text-white text-xs font-bold flex items-center justify-center shadow-sm">
          ${initials}
        </div>
        <span class="hidden sm:inline text-xs font-bold text-slate-700">${displayName}</span>
        <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
      </button>

      <!-- Dropdown Popup -->
      <div id="user-menu-dropdown" class="hidden absolute right-0 mt-2 w-56 rounded-2xl bg-white shadow-2xl border border-slate-200/80 py-2 z-50 text-xs">
        <div class="px-4 py-2.5 border-b border-slate-100">
          <p class="font-bold text-slate-900 truncate">${user.full_name}</p>
          <p class="text-slate-400 truncate">${user.email || user.phone || ""}</p>
          <span class="inline-block mt-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 uppercase tracking-wider">${user.default_currency || "INR"}</span>
        </div>

        <div class="py-1">
          <a href="profile.html" class="flex items-center space-x-2.5 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
            <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
            <span>Account & Security</span>
          </a>
          <a href="settings.html" class="flex items-center space-x-2.5 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
            <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            <span>Preferences & Categories</span>
          </a>
        </div>

        <div class="border-t border-slate-100 pt-1">
          <button id="dropdown-logout" type="button" class="w-full text-left flex items-center space-x-2.5 px-4 py-2 font-bold text-rose-600 hover:bg-rose-50 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  `;

  const btn = document.getElementById("user-menu-btn");
  const dropdown = document.getElementById("user-menu-dropdown");

  if (btn && dropdown) {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("hidden");
    });

    document.addEventListener("click", (e) => {
      if (!target.contains(e.target)) {
        dropdown.classList.add("hidden");
      }
    });
  }

  const dropLogout = document.getElementById("dropdown-logout");
  if (dropLogout) {
    dropLogout.addEventListener("click", async () => {
      try {
        await authAPI.logout();
      } catch (e) {}
      localStorage.removeItem("spendsense_token");
      sessionStorage.removeItem("spendsense_token");
      showToast("Signed out safely.", "info");
      setTimeout(() => window.location.href = "login.html", 400);
    });
  }
}

/**
 * Initializes IntersectionObserver for scroll-triggered entrance reveals
 */
function initScrollReveals() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll(".reveal-init").forEach(el => el.classList.add("revealed"));
    return;
  }

  const reveals = document.querySelectorAll(".reveal-init");
  if (!reveals.length) return;

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("revealed");
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  reveals.forEach(el => observer.observe(el));
}

