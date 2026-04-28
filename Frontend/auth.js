const loginTab = document.getElementById("login-tab");
const registerTab = document.getElementById("register-tab");
const nameRow = document.getElementById("name-row");
const authForm = document.getElementById("auth-form");
const authBanner = document.getElementById("auth-banner");
const submitButton = document.getElementById("submit-btn");
const switchModeButton = document.getElementById("switch-mode-btn");
const authFooter = document.getElementById("auth-footer");
const passwordInput = document.getElementById("password");
const themeToggleButton = document.getElementById("theme-toggle-btn");

const THEME_STORAGE_KEY = "clear-transit-theme";

let mode = "login";

function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function updateThemeToggleLabel() {
  if (!themeToggleButton) {
    return;
  }

  const theme = currentTheme();
  themeToggleButton.textContent = theme === "dark" ? "Dark mode" : "Light mode";
  themeToggleButton.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  updateThemeToggleLabel();
}

function setMode(nextMode) {
  mode = nextMode;
  const registerMode = mode === "register";
  loginTab.classList.toggle("active", !registerMode);
  registerTab.classList.toggle("active", registerMode);
  nameRow.classList.toggle("hidden", !registerMode);
  submitButton.textContent = registerMode ? "Create account" : "Login";
  authFooter.innerHTML = registerMode
    ? `Already have an account? <button id="switch-mode-btn" class="text-btn" type="button">Log in</button>`
    : `New here? <button id="switch-mode-btn" class="text-btn" type="button">Create an account</button>`;

  document.getElementById("switch-mode-btn").addEventListener("click", () => {
    setMode(registerMode ? "login" : "register");
  });

  passwordInput.setAttribute("autocomplete", registerMode ? "new-password" : "current-password");
  hideBanner();
}

function showBanner(message, tone = "error") {
  authBanner.textContent = message;
  authBanner.className = `auth-banner ${tone}`;
}

function hideBanner() {
  authBanner.textContent = "";
  authBanner.className = "auth-banner hidden";
}

async function submitAuth(event) {
  event.preventDefault();
  const formData = new FormData(authForm);
  const payload = Object.fromEntries(formData.entries());

  submitButton.disabled = true;
  submitButton.textContent = mode === "register" ? "Creating..." : "Logging in...";
  hideBanner();

  try {
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Authentication failed");
    }

    showBanner(mode === "register" ? "Account created. Redirecting..." : "Login successful. Redirecting...", "success");
    window.location.href = "/";
  } catch (error) {
    showBanner(error.message, "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = mode === "register" ? "Create account" : "Login";
  }
}

async function checkExistingSession() {
  const response = await fetch("/api/auth/me");
  const data = await response.json();
  if (data.authenticated) {
    window.location.href = "/";
  }
}

loginTab.addEventListener("click", () => setMode("login"));
registerTab.addEventListener("click", () => setMode("register"));
authForm.addEventListener("submit", submitAuth);
switchModeButton.addEventListener("click", () => setMode("register"));
themeToggleButton?.addEventListener("click", () => {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
});

updateThemeToggleLabel();
checkExistingSession();
