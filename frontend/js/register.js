/**
 * SpendSense Registration Controller (Email & Phone OTP)
 */

document.addEventListener("DOMContentLoaded", () => {
  const tabEmail = document.getElementById("tab-btn-email");
  const tabPhone = document.getElementById("tab-btn-phone");
  const formEmail = document.getElementById("form-register-email");
  const formPhone = document.getElementById("form-register-phone");

  const alertBox = document.getElementById("auth-alert");
  const alertIcon = document.getElementById("auth-alert-icon");
  const alertMsg = document.getElementById("auth-alert-message");

  const nameInput = document.getElementById("reg-name");
  const emailInput = document.getElementById("reg-email");
  const passwordInput = document.getElementById("reg-password");
  const confirmPasswordInput = document.getElementById("reg-confirm-password");
  const termsCheckbox = document.getElementById("reg-terms");
  const matchText = document.getElementById("match-text");
  const btnSubmitEmail = document.getElementById("btn-submit-reg-email");

  const strengthBars = [
    document.getElementById("strength-bar-1"),
    document.getElementById("strength-bar-2"),
    document.getElementById("strength-bar-3"),
    document.getElementById("strength-bar-4")
  ];
  const strengthText = document.getElementById("strength-text");

  const regPhoneStep1 = document.getElementById("reg-phone-step-1");
  const regPhoneStep2 = document.getElementById("reg-phone-step-2");
  const regPhoneName = document.getElementById("reg-phone-name");
  const regCountryCode = document.getElementById("reg-country-code");
  const regPhoneNumber = document.getElementById("reg-phone-number");
  const btnRegSendOtp = document.getElementById("btn-reg-send-otp");
  const btnRegEditPhone = document.getElementById("btn-reg-edit-phone");
  const regDisplayPhone = document.getElementById("reg-display-phone");
  const regOtpBoxes = document.querySelectorAll(".reg-otp-box");
  const regOtpCountdown = document.getElementById("reg-otp-countdown");
  const btnRegResend = document.getElementById("btn-reg-resend");
  const btnCompletePhoneReg = document.getElementById("btn-complete-phone-reg");
  const btnRegAutoFillOtp = document.getElementById("btn-reg-auto-fill-otp");

  const roleBtnCustomer = document.getElementById("role-btn-customer");
  const roleBtnOwner = document.getElementById("role-btn-owner");

  let selectedRole = "customer"; // 'customer' or 'owner'

  function updateRoleUI() {
    if (selectedRole === "customer") {
      roleBtnCustomer.className = "flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all shadow-sm bg-white text-slate-900 flex items-center justify-center space-x-1.5";
      roleBtnOwner.className = "flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl text-slate-600 hover:text-slate-900 transition-all flex items-center justify-center space-x-1.5";
    } else {
      roleBtnOwner.className = "flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all shadow-sm bg-slate-900 text-white flex items-center justify-center space-x-1.5";
      roleBtnCustomer.className = "flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl text-slate-600 hover:text-slate-900 transition-all flex items-center justify-center space-x-1.5";
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
      showAlert("👑 Registering as Platform Owner / Administrator account.", "info");
    });
  }

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

  // 2. Real-time Password Strength Meter
  passwordInput.addEventListener("input", () => {
    const pw = passwordInput.value;
    let score = 0;

    if (pw.length >= 8) score++;
    if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;

    const colors = ["bg-rose-500", "bg-amber-500", "bg-indigo-500", "bg-emerald-500"];
    const labels = ["Weak", "Fair", "Good", "Strong"];

    strengthBars.forEach((bar, idx) => {
      bar.className = "h-1.5 flex-1 rounded-full transition-all";
      if (idx < score) {
        bar.classList.add(colors[score - 1]);
      } else {
        bar.classList.add("bg-slate-200");
      }
    });

    if (!pw) {
      strengthText.innerText = "Empty";
      strengthText.className = "text-xs font-semibold text-slate-400 pl-1.5";
    } else {
      strengthText.innerText = labels[score - 1] || "Very Weak";
      strengthText.className = `text-xs font-bold pl-1.5 ${score <= 1 ? "text-rose-500" : (score === 2 ? "text-amber-500" : (score === 3 ? "text-indigo-500" : "text-emerald-500"))}`;
    }

    validatePasswordMatch();
  });

  confirmPasswordInput.addEventListener("input", validatePasswordMatch);

  function validatePasswordMatch() {
    if (!confirmPasswordInput.value) {
      matchText.classList.add("hidden");
      return;
    }
    if (passwordInput.value !== confirmPasswordInput.value) {
      matchText.classList.remove("hidden");
    } else {
      matchText.classList.add("hidden");
    }
  }

  // 3. Email Registration Submission
  formEmail.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();

    const fullName = nameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;
    const terms = termsCheckbox.checked;

    if (!fullName || !email || !password || !confirmPassword) {
      showAlert("Please fill in all required fields.");
      return;
    }

    if (password !== confirmPassword) {
      showAlert("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      showAlert("Password must be at least 8 characters long.");
      return;
    }

    if (!terms) {
      showAlert("You must accept the Terms and Privacy Policy.");
      return;
    }

    try {
      btnSubmitEmail.disabled = true;
      btnSubmitEmail.innerHTML = `
        <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
        <span>Creating Account...</span>
      `;

      const res = await authAPI.register({
        full_name: fullName,
        email,
        password,
        confirm_password: confirmPassword,
        role: selectedRole,
        terms_accepted: true
      });

      if (res.session_token) {
        sessionStorage.setItem("spendsense_token", res.session_token);
      }

      showToast("Account created successfully! Welcome to SpendSense.", "success");
      const targetPage = selectedRole === "owner" ? "admin.html" : "dashboard.html";
      setTimeout(() => window.location.href = targetPage, 600);

    } catch (err) {
      showAlert(err.message || "Failed to create account.");
      btnSubmitEmail.disabled = false;
      btnSubmitEmail.innerHTML = `
        <span>Create Account</span>
        <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
      `;
    }
  });

  // 4. Phone Registration Step 1: Send OTP
  btnRegSendOtp.addEventListener("click", async () => {
    hideAlert();
    const fullName = regPhoneName.value.trim();
    const countryCode = regCountryCode.value;
    const phone = regPhoneNumber.value.trim().replace(/[\s\-\(\)]/g, "");

    if (!fullName) {
      showAlert("Please enter your full name.");
      return;
    }

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
      btnRegSendOtp.disabled = true;
      btnRegSendOtp.innerHTML = `
        <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
        <span>Sending Code...</span>
      `;

      const res = await authAPI.sendOtp({
        country_code: countryCode,
        phone,
        purpose: "register"
      });

      regDisplayPhone.innerText = res.phone || `${countryCode} ${phone}`;
      regPhoneStep1.classList.add("hidden");
      regPhoneStep2.classList.remove("hidden");
      showToast(res.message, "info");

      if (regOtpBoxes.length > 0) regOtpBoxes[0].focus();
      startRegCountdown();

    } catch (err) {
      showAlert(err.message || "Failed to send code.");
      btnRegSendOtp.disabled = false;
      btnRegSendOtp.innerHTML = `<span>Send OTP Verification Code</span>`;
    }
  });

  btnRegEditPhone.addEventListener("click", () => {
    regPhoneStep2.classList.add("hidden");
    regPhoneStep1.classList.remove("hidden");
    btnRegSendOtp.disabled = false;
    btnRegSendOtp.innerHTML = `<span>Send OTP Verification Code</span>`;
    clearInterval(countdownInterval);
  });

  // 5. Phone Registration OTP Boxes
  regOtpBoxes.forEach((box, idx) => {
    box.addEventListener("input", (e) => {
      const val = e.target.value.replace(/[^0-9]/g, "");
      e.target.value = val ? val[val.length - 1] : "";
      if (val && idx < regOtpBoxes.length - 1) {
        regOtpBoxes[idx + 1].focus();
      }
    });

    box.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !box.value && idx > 0) {
        regOtpBoxes[idx - 1].focus();
      }
    });

    box.addEventListener("paste", (e) => {
      e.preventDefault();
      const pasteData = (e.clipboardData || window.clipboardData).getData("text").replace(/[^0-9]/g, "");
      if (pasteData.length >= 6) {
        for (let i = 0; i < 6; i++) {
          regOtpBoxes[i].value = pasteData[i];
        }
        regOtpBoxes[5].focus();
      }
    });
  });

  function startRegCountdown() {
    let secondsLeft = 60;
    btnRegResend.disabled = true;
    regOtpCountdown.innerText = secondsLeft;

    clearInterval(countdownInterval);
    countdownInterval = setInterval(() => {
      secondsLeft--;
      regOtpCountdown.innerText = secondsLeft;
      if (secondsLeft <= 0) {
        clearInterval(countdownInterval);
        btnRegResend.disabled = false;
        document.getElementById("reg-otp-timer").innerText = "Did not receive code?";
      }
    }, 1000);
  }

  btnRegResend.addEventListener("click", () => {
    btnRegSendOtp.click();
  });

  // Auto-fill demo OTP
  if (btnRegAutoFillOtp) {
    btnRegAutoFillOtp.addEventListener("click", () => {
      const demoCode = "123456";
      regOtpBoxes.forEach((box, i) => {
        box.value = demoCode[i] || "";
      });
      if (regOtpBoxes.length > 0) regOtpBoxes[regOtpBoxes.length - 1].focus();
      showToast("Demo verification code 123456 filled!", "info");
    });
  }

  // 6. Complete Phone Registration Submission
  formPhone.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();

    let otpCode = "";
    regOtpBoxes.forEach(box => otpCode += box.value.trim());

    if (otpCode.length !== 6) {
      showAlert("Please enter the complete 6-digit verification code.");
      return;
    }

    try {
      btnCompletePhoneReg.disabled = true;
      btnCompletePhoneReg.innerHTML = `
        <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
        <span>Verifying & Setting up...</span>
      `;

      const res = await authAPI.verifyOtp({
        country_code: regCountryCode.value,
        phone: regPhoneNumber.value.trim().replace(/[\s\-\(\)]/g, ""),
        otp_code: otpCode,
        full_name: regPhoneName.value.trim(),
        role: selectedRole,
        purpose: "register"
      });

      const token = res.session_token || res.token || "mock_session_token_12345";
      sessionStorage.setItem("spendsense_token", token);
      localStorage.setItem("spendsense_token", token);

      triggerConfetti();
      showToast("Registration successful! Welcome to SpendSense.", "success");
      const targetPage = selectedRole === "owner" ? "admin.html" : "dashboard.html";
      setTimeout(() => window.location.href = targetPage, 650);

    } catch (err) {
      showAlert(err.message || "Verification failed. Check the code.");
      btnCompletePhoneReg.disabled = false;
      btnCompletePhoneReg.innerHTML = `<span>Complete Registration</span>`;
    }
  });
});
