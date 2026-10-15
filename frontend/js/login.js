/**
 * SpendSense Login Controller (Customer & Owner Support)
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const roleBtnCustomer = document.getElementById("role-btn-customer");
  const roleBtnOwner = document.getElementById("role-btn-owner");

  const tabEmail = document.getElementById("tab-btn-email");
  const tabPhone = document.getElementById("tab-btn-phone");
  const formEmail = document.getElementById("form-login-email");
  const formPhone = document.getElementById("form-login-phone");

  const alertBox = document.getElementById("auth-alert");
  const alertIcon = document.getElementById("auth-alert-icon");
  const alertMsg = document.getElementById("auth-alert-message");

  const emailInput = document.getElementById("login-email");
  const passwordInput = document.getElementById("login-password");
  const rememberMeCheckbox = document.getElementById("login-remember-me");
  const btnTogglePassword = document.getElementById("btn-toggle-password");
  const btnSubmitEmail = document.getElementById("btn-submit-email");

  const phoneStepNumber = document.getElementById("phone-step-number");
  const phoneStepOtp = document.getElementById("phone-step-otp");
  const countryCodeSelect = document.getElementById("login-country-code");
  const phoneInput = document.getElementById("login-phone");
  const btnSendOtp = document.getElementById("btn-send-otp");
  const btnEditPhone = document.getElementById("btn-edit-phone");
  const displayTargetPhone = document.getElementById("display-target-phone");
  const otpCountdown = document.getElementById("otp-countdown");
  const btnResendOtp = document.getElementById("btn-resend-otp");
  const otpBoxes = document.querySelectorAll(".otp-box");
  const btnVerifyOtp = document.getElementById("btn-verify-otp");
  const btnAutoFillOtp = document.getElementById("btn-auto-fill-otp");
  const btnQuickFillPhone = document.getElementById("btn-quick-fill-phone");

  const btnFillCustomerDemo = document.getElementById("btn-fill-customer-demo");
  const btnFillOwnerDemo = document.getElementById("btn-fill-owner-demo");

  let selectedRole = "customer"; // 'customer' or 'owner'
  let countdownInterval = null;

  function showAlert(message, type = "error") {
    alertBox.className = type === "error"
      ? "mb-5 p-3.5 rounded-xl text-sm border flex items-start space-x-3 bg-rose-50 text-rose-800 border-rose-200"
      : "mb-5 p-3.5 rounded-xl text-sm border flex items-start space-x-3 bg-emerald-50 text-emerald-800 border-emerald-200";
    alertIcon.innerText = type === "error" ? "⚠️" : "✓";
    alertMsg.innerText = message;
    alertBox.classList.remove("hidden");
  }

  function hideAlert() {
    alertBox.classList.add("hidden");
  }

  // 1. Role Switching
  function updateRoleUI() {
    if (selectedRole === "customer") {
      roleBtnCustomer.className = "flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all shadow-sm bg-white text-slate-900 flex items-center justify-center space-x-1.5";
      roleBtnOwner.className = "flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl text-slate-600 hover:text-slate-900 transition-all flex items-center justify-center space-x-1.5";
      if (btnQuickFillPhone) btnQuickFillPhone.innerText = "Use Customer Demo (98765 43210)";
    } else {
      roleBtnOwner.className = "flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all shadow-sm bg-slate-900 text-white flex items-center justify-center space-x-1.5";
      roleBtnCustomer.className = "flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl text-slate-600 hover:text-slate-900 transition-all flex items-center justify-center space-x-1.5";
      if (btnQuickFillPhone) btnQuickFillPhone.innerText = "Use Owner Demo (99999 99999)";
    }
  }

  if (roleBtnCustomer) {
    roleBtnCustomer.addEventListener("click", () => {
      selectedRole = "customer";
      updateRoleUI();
      hideAlert();
    });
  }

  if (roleBtnOwner) {
    roleBtnOwner.addEventListener("click", () => {
      selectedRole = "owner";
      updateRoleUI();
      hideAlert();
      phoneInput.value = "9999999999";
      emailInput.value = "owner@spendsense.ai";
      showAlert("👑 Owner Portal active. Use phone 99999 99999 or email owner@spendsense.ai with demo OTP 123456.", "info");
    });
  }

  // 2. Tab Switching (Phone OTP vs Email)
  tabPhone.addEventListener("click", () => {
    tabPhone.className = "flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all shadow-sm bg-white text-slate-900";
    tabEmail.className = "flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl text-slate-600 hover:text-slate-900 transition-all";
    formPhone.classList.remove("hidden");
    formEmail.classList.add("hidden");
    hideAlert();
  });

  tabEmail.addEventListener("click", () => {
    tabEmail.className = "flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all shadow-sm bg-white text-slate-900";
    tabPhone.className = "flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl text-slate-600 hover:text-slate-900 transition-all";
    formEmail.classList.remove("hidden");
    formPhone.classList.add("hidden");
    hideAlert();
  });

  // 3. Toggle Password Visibility
  if (btnTogglePassword) {
    btnTogglePassword.addEventListener("click", () => {
      const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
      passwordInput.setAttribute("type", type);
    });
  }

  // 4. Email & Password Login Submission
  formEmail.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();

    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const rememberMe = rememberMeCheckbox ? rememberMeCheckbox.checked : false;

    if (!email || !password) {
      showAlert("Please enter both email and password.");
      return;
    }

    try {
      btnSubmitEmail.disabled = true;
      btnSubmitEmail.innerHTML = `
        <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
        <span>Signing in...</span>
      `;

      const res = await authAPI.login({
        email,
        password,
        role: selectedRole,
        remember_me: rememberMe
      });

      if (res.session_token) {
        if (rememberMe) {
          localStorage.setItem("spendsense_token", res.session_token);
        } else {
          sessionStorage.setItem("spendsense_token", res.session_token);
        }
      }

      triggerConfetti();
      showToast(`Welcome back, ${res.user.full_name}!`, "success");
      
      const targetPage = (res.user.role === "owner" || selectedRole === "owner") ? "admin.html" : "dashboard.html";
      const redirect = sessionStorage.getItem("spendsense_redirect") || targetPage;
      sessionStorage.removeItem("spendsense_redirect");
      setTimeout(() => window.location.href = redirect, 500);

    } catch (err) {
      showAlert(err.message || "Invalid credentials.");
      btnSubmitEmail.disabled = false;
      btnSubmitEmail.innerHTML = "<span>Log In</span>";
    }
  });

  // 5. Phone OTP Step 1: Send OTP
  btnSendOtp.addEventListener("click", async () => {
    hideAlert();
    const countryCode = countryCodeSelect.value;
    const phone = phoneInput.value.trim().replace(/[\s\-\(\)]/g, "");

    if (countryCode === "+91") {
      if (!/^[6-9]\d{9}$/.test(phone)) {
        showAlert("Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.");
        return;
      }
    } else if (!phone || phone.length < 6) {
      showAlert("Please enter a valid phone number.");
      return;
    }

    try {
      btnSendOtp.disabled = true;
      btnSendOtp.innerHTML = `
        <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
        <span>Sending Code...</span>
      `;

      const res = await authAPI.sendOtp({
        country_code: countryCode,
        phone,
        role: selectedRole,
        purpose: "login"
      });

      displayTargetPhone.innerText = `${countryCode} ${phone}`;
      phoneStepNumber.classList.add("hidden");
      phoneStepOtp.classList.remove("hidden");

      if (otpBoxes.length > 0) otpBoxes[0].focus();

      showAlert(res.message || "Verification code sent to your phone!", "success");
      startCountdown();

    } catch (err) {
      showAlert(err.message || "Failed to send verification code. Please try again.");
    } finally {
      btnSendOtp.disabled = false;
      btnSendOtp.innerHTML = `
        <span>Send Verification Code</span>
        <svg class="w-4 h-4 ml-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
      `;
    }
  });

  // Edit Phone
  btnEditPhone.addEventListener("click", () => {
    clearInterval(countdownInterval);
    phoneStepOtp.classList.add("hidden");
    phoneStepNumber.classList.remove("hidden");
    phoneInput.focus();
  });

  // OTP inputs auto-advance
  otpBoxes.forEach((box, index) => {
    box.addEventListener("input", (e) => {
      const val = e.target.value.replace(/[^0-9]/g, "");
      e.target.value = val;
      if (val && index < otpBoxes.length - 1) {
        otpBoxes[index + 1].focus();
      }
    });

    box.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !e.target.value && index > 0) {
        otpBoxes[index - 1].focus();
      }
    });

    box.addEventListener("paste", (e) => {
      e.preventDefault();
      const pasteData = (e.clipboardData || window.clipboardData).getData("text").replace(/[^0-9]/g, "").slice(0, 6);
      pasteData.split("").forEach((char, i) => {
        if (otpBoxes[i]) otpBoxes[i].value = char;
      });
      if (otpBoxes[pasteData.length - 1]) otpBoxes[pasteData.length - 1].focus();
    });
  });

  function startCountdown() {
    let secondsLeft = 60;
    btnResendOtp.disabled = true;
    otpCountdown.innerText = secondsLeft;
    clearInterval(countdownInterval);
    countdownInterval = setInterval(() => {
      secondsLeft--;
      otpCountdown.innerText = secondsLeft;
      if (secondsLeft <= 0) {
        clearInterval(countdownInterval);
        btnResendOtp.disabled = false;
        document.getElementById("otp-timer-display").innerText = "Did not receive code?";
      }
    }, 1000);
  }

  btnResendOtp.addEventListener("click", async () => {
    btnSendOtp.click();
  });

  // Auto-fill demo OTP code
  if (btnAutoFillOtp) {
    btnAutoFillOtp.addEventListener("click", () => {
      const demoCode = "123456";
      otpBoxes.forEach((box, i) => {
        box.value = demoCode[i] || "";
      });
      if (otpBoxes.length > 0) otpBoxes[otpBoxes.length - 1].focus();
      showToast("Demo verification code 123456 filled!", "info");
    });
  }

  // Quick-fill demo mobile number
  if (btnQuickFillPhone) {
    btnQuickFillPhone.addEventListener("click", () => {
      if (selectedRole === "owner") {
        phoneInput.value = "9999999999";
        showToast("Owner mobile number filled!", "info");
      } else {
        phoneInput.value = "9876543210";
        showToast("Customer mobile number filled!", "info");
      }
      phoneInput.focus();
    });
  }

  // 6. Phone OTP Step 2: Verify & Log In
  formPhone.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();

    let otpCode = "";
    otpBoxes.forEach(box => otpCode += box.value.trim());

    if (otpCode.length !== 6) {
      showAlert("Please enter the complete 6-digit verification code.");
      return;
    }

    try {
      btnVerifyOtp.disabled = true;
      btnVerifyOtp.innerHTML = `
        <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
        <span>Verifying...</span>
      `;

      const res = await authAPI.verifyOtp({
        country_code: countryCodeSelect.value,
        phone: phoneInput.value.trim().replace(/[\s\-\(\)]/g, ""),
        otp_code: otpCode,
        role: selectedRole,
        purpose: "login"
      });

      const token = res.session_token || res.token || "mock_session_token_12345";
      sessionStorage.setItem("spendsense_token", token);
      localStorage.setItem("spendsense_token", token);

      triggerConfetti();
      showToast(res.message || "Phone verified successfully!", "success");

      const targetPage = (res.user && res.user.role === "owner" || selectedRole === "owner") ? "admin.html" : "dashboard.html";
      const redirect = sessionStorage.getItem("spendsense_redirect") || targetPage;
      sessionStorage.removeItem("spendsense_redirect");
      setTimeout(() => window.location.href = redirect, 650);

    } catch (err) {
      showAlert(err.message || "Verification failed. Check your code.");
      btnVerifyOtp.disabled = false;
      btnVerifyOtp.innerHTML = `<span>Sign In with OTP</span>`;
    }
  });

  // 7. Instant Demo Account Logins
  if (btnFillCustomerDemo) {
    btnFillCustomerDemo.addEventListener("click", async () => {
      selectedRole = "customer";
      updateRoleUI();
      try {
        const res = await authAPI.login({
          email: "aarav@spendsense.local",
          password: "password123",
          role: "customer"
        });
        triggerConfetti();
        showToast("Logged in as Customer (Aarav Sharma)!", "success");
        setTimeout(() => window.location.href = "dashboard.html", 500);
      } catch (e) {
        window.location.href = "dashboard.html";
      }
    });
  }

  if (btnFillOwnerDemo) {
    btnFillOwnerDemo.addEventListener("click", async () => {
      selectedRole = "owner";
      updateRoleUI();
      try {
        const res = await authAPI.login({
          email: "owner@spendsense.ai",
          password: "adminpassword123",
          role: "owner"
        });
        triggerConfetti();
        showToast("👑 Logged in as Platform Owner / Administrator!", "success");
        setTimeout(() => window.location.href = "admin.html", 500);
      } catch (e) {
        window.location.href = "admin.html";
      }
    });
  }
});
