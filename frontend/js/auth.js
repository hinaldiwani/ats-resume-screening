/**
 * frontend/js/auth.js
 *
 * Handles the login and register forms. These call the real, working
 * backend endpoints (/api/v1/auth/login, /register) — unlike the other
 * pages' JS files, no demo-data fallback is used here, since auth is the
 * one module that's actually implemented server-side.
 */

function showAuthAlert(el, message, type = "error") {
  el.textContent = message;
  el.className = `auth-alert show ${type}`;
}

function hideAuthAlert(el) {
  el.className = "auth-alert";
}

function setButtonLoading(button, loading, loadingText = "Please wait…") {
  if (loading) {
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = `<span class="spinner-c me-2"></span>${loadingText}`;
    button.disabled = true;
  } else {
    button.innerHTML = button.dataset.originalText || button.innerHTML;
    button.disabled = false;
  }
}

function validateEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

/**
 * Wires a show/hide toggle button to a password input. Reusable — pass any
 * input/button id pair, so the same function could later be attached to
 * register.html's password fields without duplicating this logic.
 */
function initPasswordToggle(inputId, buttonId) {
  const input = document.getElementById(inputId);
  const button = document.getElementById(buttonId);
  if (!input || !button) return;

  button.addEventListener("click", () => {
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    button.innerHTML = `<i class="bi ${isHidden ? "bi-eye-slash" : "bi-eye"}"></i>`;
    button.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
    button.setAttribute("aria-pressed", String(isHidden));
  });
}

const REMEMBERED_EMAIL_KEY = "ats_remembered_email";

/* ---------------------------------------------------------------------------
   Login
   ------------------------------------------------------------------------ */
function initLoginForm() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  const alertEl = document.getElementById("authAlert");
  const emailInput = document.getElementById("loginEmail");
  const passwordInput = document.getElementById("loginPassword");
  const rememberCheckbox = document.getElementById("rememberMeCheckbox");
  const submitBtn = document.getElementById("loginSubmitBtn");

  initPasswordToggle("loginPassword", "loginPasswordToggle");

  // Pre-fill email if a previous session chose "Remember me".
  const rememberedEmail = localStorage.getItem(REMEMBERED_EMAIL_KEY);
  if (rememberedEmail) {
    emailInput.value = rememberedEmail;
    rememberCheckbox.checked = true;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAuthAlert(alertEl);

    if (!validateEmail(emailInput.value)) {
      showAuthAlert(alertEl, "Enter a valid email address.");
      emailInput.focus();
      return;
    }
    if (!passwordInput.value) {
      showAuthAlert(alertEl, "Enter your password.");
      passwordInput.focus();
      return;
    }

    setButtonLoading(submitBtn, true, "Signing in…");
    try {
      const result = await api.post("/auth/login", {
        email: emailInput.value.trim(),
        password: passwordInput.value,
      });

      // Decide the storage backend (localStorage vs sessionStorage) before
      // storing anything, since storeSession() reads this flag internally.
      setRememberMe(rememberCheckbox.checked);
      if (rememberCheckbox.checked) {
        localStorage.setItem(REMEMBERED_EMAIL_KEY, emailInput.value.trim());
      } else {
        localStorage.removeItem(REMEMBERED_EMAIL_KEY);
      }

      storeSession({
        access_token: result.data.access_token,
        refresh_token: result.data.refresh_token,
      });

      // Fetch the recruiter's profile so the sidebar/navbar can show their
      // real name instead of a placeholder.
      try {
        const me = await api.get("/auth/me");
        storeSession({ user: me.data });
      } catch (_) {
        /* non-fatal — dashboard will show a generic label */
      }

      window.location.href = "dashboard.html";
    } catch (err) {
      showAuthAlert(alertEl, err.message === "NETWORK_ERROR"
        ? "Can't reach the server. Confirm the API is running and try again."
        : err.message);
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });
}

/* ---------------------------------------------------------------------------
   Register
   ------------------------------------------------------------------------ */
function initRegisterForm() {
  const form = document.getElementById("registerForm");
  if (!form) return;

  const alertEl = document.getElementById("authAlert");
  const nameInput = document.getElementById("registerName");
  const emailInput = document.getElementById("registerEmail");
  const companyInput = document.getElementById("registerCompany");
  const passwordInput = document.getElementById("registerPassword");
  const confirmInput = document.getElementById("registerConfirmPassword");
  const submitBtn = document.getElementById("registerSubmitBtn");

  initPasswordToggle("registerPassword", "registerPasswordToggle");
  initPasswordToggle("registerConfirmPassword", "registerConfirmPasswordToggle");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAuthAlert(alertEl);

    if (nameInput.value.trim().length < 2) {
      showAuthAlert(alertEl, "Enter your full name.");
      nameInput.focus();
      return;
    }
    if (!validateEmail(emailInput.value)) {
      showAuthAlert(alertEl, "Enter a valid email address.");
      emailInput.focus();
      return;
    }
    if (passwordInput.value.length < 8) {
      showAuthAlert(alertEl, "Password must be at least 8 characters.");
      passwordInput.focus();
      return;
    }
    if (passwordInput.value !== confirmInput.value) {
      showAuthAlert(alertEl, "Passwords don't match.");
      confirmInput.focus();
      return;
    }

    setButtonLoading(submitBtn, true, "Creating account…");
    try {
      await api.post("/auth/register", {
        name: nameInput.value.trim(),
        email: emailInput.value.trim(),
        password: passwordInput.value,
        company_name: companyInput.value.trim() || null,
      });

      showAuthAlert(alertEl, "Account created. Redirecting to sign in…", "success");
      setTimeout(() => (window.location.href = "login.html"), 1200);
    } catch (err) {
      showAuthAlert(alertEl, err.message === "NETWORK_ERROR"
        ? "Can't reach the server. Confirm the API is running and try again."
        : err.message);
      setButtonLoading(submitBtn, false);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initLoginForm();
  initRegisterForm();
});
