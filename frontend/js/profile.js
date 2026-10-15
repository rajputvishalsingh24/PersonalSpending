/**
 * SpendSense Profile & Account Management Controller
 */

document.addEventListener("DOMContentLoaded", async () => {
  // Elements
  const profileAvatar = document.getElementById("profile-avatar");
  const profileName = document.getElementById("profile-name");
  const profileEmail = document.getElementById("profile-email-display");
  const profilePhone = document.getElementById("profile-phone-display");
  const profileMemberSince = document.getElementById("profile-member-since");
  const badgeEmail = document.getElementById("badge-email-status");
  const badgePhone = document.getElementById("badge-phone-status");
  const headerUserName = document.getElementById("header-user-name");

  // Forms
  const formProfile = document.getElementById("form-update-profile");
  const profNameInput = document.getElementById("prof-name");
  const profCurrencySelect = document.getElementById("prof-currency");
  const profPhoneInput = document.getElementById("prof-phone");
  const btnSaveProfile = document.getElementById("btn-save-profile");

  const formPassword = document.getElementById("form-change-password");
  const pwdCurrent = document.getElementById("pwd-current");
  const pwdNew = document.getElementById("pwd-new");
  const pwdConfirm = document.getElementById("pwd-confirm");
  const btnUpdatePwd = document.getElementById("btn-update-pwd");

  // Danger Zone
  const btnOpenDeleteModal = document.getElementById("btn-open-delete-modal");
  const deleteModal = document.getElementById("delete-modal");
  const deleteConfirmInput = document.getElementById("delete-confirm-input");
  const btnCancelDelete = document.getElementById("btn-cancel-delete");
  const btnConfirmDelete = document.getElementById("btn-confirm-delete");

  const btnSidebarLogout = document.getElementById("btn-sidebar-logout");

  // 1. Load User Profile
  async function loadProfile() {
    try {
      let user = await authAPI.getMe();
      if (!user) return;
      if (user && user.user) user = user.user;

      // Update avatar initials
      const name = user.full_name || user.display_name || "SpendSense User";
      profileName.innerText = name;
      if (headerUserName) headerUserName.innerText = user.display_name || (name ? name.split(" ")[0] : "User");

      const initials = (name || "U").split(" ").filter(Boolean).map(n => n[0]).join("").substring(0, 2).toUpperCase() || "U";
      profileAvatar.innerText = initials;

      profileEmail.innerText = user.email || "No email address linked";
      profilePhone.innerText = user.phone || "No phone number linked";

      if (user.created_at) {
        const d = new Date(user.created_at);
        profileMemberSince.innerText = `Member since ${d.toLocaleDateString("en-IN", { month: "short", year: "numeric" })}`;
      }

      // Email badge
      if (user.email_verified) {
        badgeEmail.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200";
        badgeEmail.innerText = "Email Verified";
      } else {
        badgeEmail.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200";
        badgeEmail.innerText = "Email Unverified";
      }

      // Phone badge
      if (user.phone_verified && user.phone) {
        badgePhone.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200";
        badgePhone.innerText = "Phone Verified";
      } else {
        badgePhone.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-500 border border-slate-200";
        badgePhone.innerText = user.phone ? "Phone Unverified" : "Phone Not Linked";
      }

      // Populate input fields
      profNameInput.value = user.full_name || "";
      if (user.default_currency) {
        profCurrencySelect.value = user.default_currency;
      }
      profPhoneInput.value = user.phone || "";

    } catch (err) {
      console.error("Failed to load profile:", err);
    }
  }

  await loadProfile();

  // 2. Save Personal Profile
  formProfile.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fullName = profNameInput.value.trim();
    const currency = profCurrencySelect.value;
    const phone = profPhoneInput.value.trim();

    try {
      btnSaveProfile.disabled = true;
      btnSaveProfile.innerText = "Saving...";

      const updated = await authAPI.updateProfile({
        full_name: fullName,
        default_currency: currency,
        phone: phone || null
      });

      showToast("Profile details updated successfully!", "success");
      await loadProfile();

    } catch (err) {
      showToast(err.message || "Failed to update profile.", "error");
    } finally {
      btnSaveProfile.disabled = false;
      btnSaveProfile.innerText = "Save Profile Changes";
    }
  });

  // 3. Change Password
  formPassword.addEventListener("submit", async (e) => {
    e.preventDefault();
    const currentPassword = pwdCurrent.value;
    const newPassword = pwdNew.value;
    const confirmPassword = pwdConfirm.value;

    if (newPassword !== confirmPassword) {
      showToast("New password and confirmation do not match.", "error");
      return;
    }

    if (newPassword.length < 8) {
      showToast("New password must be at least 8 characters long.", "error");
      return;
    }

    try {
      btnUpdatePwd.disabled = true;
      btnUpdatePwd.innerText = "Updating...";

      const res = await authAPI.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      });

      showToast(res.message || "Password changed successfully!", "success");
      formPassword.reset();

    } catch (err) {
      showToast(err.message || "Failed to update password.", "error");
    } finally {
      btnUpdatePwd.disabled = false;
      btnUpdatePwd.innerText = "Update Password";
    }
  });

  // 4. Delete Account Modal Flow
  btnOpenDeleteModal.addEventListener("click", () => {
    deleteConfirmInput.value = "";
    btnConfirmDelete.disabled = true;
    deleteModal.classList.remove("hidden");
  });

  btnCancelDelete.addEventListener("click", () => {
    deleteModal.classList.add("hidden");
  });

  deleteConfirmInput.addEventListener("input", () => {
    btnConfirmDelete.disabled = deleteConfirmInput.value.trim() !== "DELETE";
  });

  btnConfirmDelete.addEventListener("click", async () => {
    try {
      btnConfirmDelete.disabled = true;
      btnConfirmDelete.innerText = "Deleting...";

      const res = await authAPI.deleteAccount();
      localStorage.removeItem("spendsense_token");
      sessionStorage.removeItem("spendsense_token");
      showToast("Account deleted. Redirecting...", "info");
      setTimeout(() => window.location.href = "index.html", 800);

    } catch (err) {
      showToast(err.message || "Failed to delete account.", "error");
      btnConfirmDelete.disabled = false;
      btnConfirmDelete.innerText = "Permanently Delete";
    }
  });

  // 5. Sign Out
  if (btnSidebarLogout) {
    btnSidebarLogout.addEventListener("click", async () => {
      try {
        await authAPI.logout();
      } catch (e) {}
      localStorage.removeItem("spendsense_token");
      sessionStorage.removeItem("spendsense_token");
      showToast("You have been signed out safely.", "info");
      setTimeout(() => window.location.href = "login.html", 400);
    });
  }
});
