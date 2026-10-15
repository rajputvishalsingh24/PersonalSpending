/**
 * SpendSense Login Controller (Email & Phone OTP)
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
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

  const btnFillDemo = document.getElementById("btn-fill-demo");

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

  // 1. Tab Switching (Phone OTP is default for India)
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

  // 2. Toggle Password Visibility
  if (btnTogglePassword) {
    btnTogglePassword.addEventListener("click", () => {
      const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
      passwordInput.setAttribute("type", type);
    });
  }

  // 3. Email & Password Login Submission
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
        remember_me: rememberMe
      });

      // Store fallback token
      if (res.session_token) {
        if (rememberMe) {
          localStorage.setItem("spendsense_token", res.session_token);
        } else {
          sessionStorage.setItem("spendsense_token", res.session_token);
        }
      }

      showToast(`Welcome back, ${res.user.full_name}!`, "success");
      
      const redirect = sessionStorage.getItem("spendsense_redirect") || "dashboard.html";
      sessionStorage.removeItem("spendsense_redirect");
      setTimeout(() => window.location.href = redirect, 500);

    } catch (err) {
      showAlert(err.message || "Invalid credentials.");
      btnSubmitEmail.disabled = false;
      btnSubmitEmail.innerHTML = "<span>Log In</span>";
    }
  });

  // 4. Phone OTP Step 1: Send OTP
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
        purpose: "login"
      });

      displayTargetPhone.innerText = res.phone || `${countryCode} ${phone}`;
      phoneStepNumber.classList.add("hidden");
      phoneStepOtp.classList.remove("hidden");
      showToast(res.message, "info");

      // Auto-focus first OTP box
      if (otpBoxes.length > 0) otpBoxes[0].focus();

      startOtpCountdown();

    } catch (err) {
      const msg = err.message || "Failed to send verification code.";
      if (msg.includes("register") || msg.includes("sign up") || msg.includes("No account found")) {
        showAlert(`${msg} <a href="register.html" class="underline font-bold ml-1">Create Account →</a>`);
      } else {
        showAlert(msg);
      }
      btnSendOtp.disabled = false;
      btnSendOtp.innerHTML = `<span>Send Verification Code</span>`;
    }
  });

  // Edit phone number
  btnEditPhone.addEventListener("click", () => {
    phoneStepOtp.classList.add("hidden");
    phoneStepNumber.classList.remove("hidden");
    btnSendOtp.disabled = false;
    btnSendOtp.innerHTML = `<span>Send Verification Code</span>`;
    clearInterval(countdownInterval);
  });

  // 5. OTP 6-Digit Box Auto-Focus and Paste Handling
  otpBoxes.forEach((box, idx) => {
    box.addEventListener("input", (e) => {
      const val = e.target.value.replace(/[^0-9]/g, "");
      e.target.value = val ? val[val.length - 1] : "";
      if (val && idx < otpBoxes.length - 1) {
        otpBoxes[idx + 1].focus();
      }
    });

    box.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !box.value && idx > 0) {
        otpBoxes[idx - 1].focus();
      }
    });

    box.addEventListener("paste", (e) => {
      e.preventDefault();
      const pasteData = (e.clipboardData || window.clipboardData).getData("text").replace(/[^0-9]/g, "");
      if (pasteData.length >= 6) {
        for (let i = 0; i < 6; i++) {
          otpBoxes[i].value = pasteData[i];
        }
        otpBoxes[5].focus();
      }
    });
  });

  function startOtpCountdown() {
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
      phoneInput.value = "9876543210";
      phoneInput.focus();
      showToast("Demo mobile number filled!", "info");
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
        purpose: "login"
      });

      const token = res.session_token || res.token || "mock_session_token_12345";
      sessionStorage.setItem("spendsense_token", token);
      localStorage.setItem("spendsense_token", token);

      triggerConfetti();
      showToast(res.message || "Phone verified successfully!", "success");
      const redirect = sessionStorage.getItem("spendsense_redirect") || "dashboard.html";
      sessionStorage.removeItem("spendsense_redirect");
      setTimeout(() => window.location.href = redirect, 650);

    } catch (err) {
      showAlert(err.message || "Verification failed. Check your code.");
      btnVerifyOtp.disabled = false;
      btnVerifyOtp.innerHTML = `<span>Sign In with OTP</span>`;
    }
  });

  // 7. Quick Demo Account auto-fill
  if (btnFillDemo) {
    btnFillDemo.addEventListener("click", () => {
      if (!formPhone.classList.contains("hidden")) {
        phoneInput.value = "9876543210";
        showAlert("ℹ️ Demo mobile number filled! Click 'Send Verification Code' to receive OTP 123456.", "info");
      } else {
        emailInput.value = "demo@spendsense.local";
        passwordInput.value = "demo123";
        showAlert("ℹ️ Click 'Log In with Password' to access the pre-seeded demo environment.", "info");
      }
    });
  }
});
