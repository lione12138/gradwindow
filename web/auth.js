import { state } from "./state.js";
import { t } from "./strings.js";
import {
  ensureTurnstileWidget,
  resetTurnstileWidget,
  turnstileToken,
} from "./turnstile.js";

// Password/email-code sign-in, profile, and favourites sync.
// Auth updates page UI it does not own (board, favourite controls, review
// panel), so app.js injects those refreshers via initAuth() instead of this
// module importing app.js back (which would create a cycle).

const AUTH_TOKEN_KEY = "gradwindow:authToken";
const GUEST_FAVORITES_KEY = "gradwindow:favorites";
const USER_FAVORITES_PREFIX = "gradwindow:favorites:user:";
const AUTH_TURNSTILE_CONTAINER = "auth-turnstile";
const AUTH_TURNSTILE_ACTION = "auth-login";
let authMode = "password";
let favoriteSyncInFlight = false;

function pendingFavorites(user = state.user) {
  try {
    const value = JSON.parse(
      localStorage.getItem(`${userFavoritesKey(user)}:pending`) || "{}",
    );
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : {};
  } catch {
    return {};
  }
}

let deps = {
  render: () => {},
  updateFavoriteControls: () => {},
  updateReviewAuthState: () => {},
  openHome: () => {},
};

export function initAuth(callbacks = {}) {
  deps = { ...deps, ...callbacks };
}

export function feedbackApiBase() {
  const config = window.GRADWINDOW_CONFIG || {};
  return String(config.roadmapUrl || config.subscribeUrl || "").replace(
    /\/$/,
    "",
  );
}

function authApiBase() {
  return feedbackApiBase();
}

export function authHeaders(includeJson = true) {
  const headers = {};
  if (includeJson) headers["Content-Type"] = "application/json";
  if (state.authToken) headers.Authorization = `Bearer ${state.authToken}`;
  return headers;
}

function setAuthStatus(message, kind = "") {
  const status = document.getElementById("auth-status");
  if (!status) return;
  status.textContent = message || "";
  status.className = `auth-status${kind ? ` ${kind}` : ""}`;
}

function saveAuthToken(token) {
  state.authToken = token || "";
  if (state.authToken) localStorage.setItem(AUTH_TOKEN_KEY, state.authToken);
  else localStorage.removeItem(AUTH_TOKEN_KEY);
}

function favoriteSetFromStorage(key) {
  try {
    const payload = JSON.parse(localStorage.getItem(key) || "[]");
    return new Set(Array.isArray(payload) ? payload.filter(Boolean) : []);
  } catch {
    return new Set();
  }
}

function userFavoritesKey(user = state.user) {
  return user?.id ? `${USER_FAVORITES_PREFIX}${user.id}` : "";
}

export function loadInitialFavorites() {
  return favoriteSetFromStorage(GUEST_FAVORITES_KEY);
}

export function persistFavorites() {
  const key = userFavoritesKey() || GUEST_FAVORITES_KEY;
  if (state.user) {
    const previous = favoriteSetFromStorage(key);
    const pending = pendingFavorites();
    for (const item of new Set([...previous, ...state.favorites])) {
      if (previous.has(item) !== state.favorites.has(item))
        pending[item] = state.favorites.has(item);
    }
    localStorage.setItem(`${key}:pending`, JSON.stringify(pending));
  }
  localStorage.setItem(key, JSON.stringify([...state.favorites]));
  state.favoriteSyncStatus = state.user ? "pending" : "local";
  deps.updateFavoriteControls();
  scheduleFavoriteSync();
  window.dispatchEvent(new Event("accountchange"));
}

function useSignedInFavorites(user, remoteFavorites = []) {
  if (!user?.id) throw new Error("invalid user response");
  const serverFavorites = Array.isArray(remoteFavorites) ? remoteFavorites : [];
  const guestFavorites = state.user
    ? new Set()
    : favoriteSetFromStorage(GUEST_FAVORITES_KEY);
  state.user = user;
  state.favorites = new Set([
    ...serverFavorites.filter(Boolean),
    ...guestFavorites,
  ]);
  const pending = pendingFavorites(user);
  for (const key of guestFavorites) pending[key] = true;
  localStorage.setItem(
    `${userFavoritesKey(user)}:pending`,
    JSON.stringify(pending),
  );
  for (const [key, saved] of Object.entries(pending)) {
    if (saved) state.favorites.add(key);
    else state.favorites.delete(key);
  }
  localStorage.removeItem(GUEST_FAVORITES_KEY);
  localStorage.setItem(
    userFavoritesKey(user),
    JSON.stringify([...state.favorites]),
  );
  state.favoriteSyncStatus = "pending";
}

function useGuestFavorites() {
  state.user = null;
  state.favorites = favoriteSetFromStorage(GUEST_FAVORITES_KEY);
  state.favoriteSyncStatus = "local";
}

function setAuthStep(step) {
  const requesting = step !== "code";
  const requestForm = document.getElementById("auth-request-form");
  const verifyForm = document.getElementById("auth-verify-form");
  if (requestForm) requestForm.hidden = !requesting;
  if (verifyForm) verifyForm.hidden = requesting;
  if (!requesting) {
    const target = document.getElementById("auth-code-email");
    const email = document.getElementById("auth-email")?.value.trim();
    if (target) target.textContent = email || "";
  }
}

export function updateAuthUi() {
  const signedIn = Boolean(state.user);
  const toggle = document.getElementById("auth-toggle");
  if (toggle) {
    toggle.textContent = signedIn ? t("personalHome") : t("signIn");
  }
  const signedOut = document.getElementById("auth-signed-out");
  const signedInPanel = document.getElementById("auth-signed-in");
  if (signedOut) signedOut.hidden = signedIn;
  if (signedInPanel) signedInPanel.hidden = !signedIn;
  if (signedIn) {
    document.getElementById("auth-user-name").textContent =
      state.user.displayName || t("accountTitle");
    document.getElementById("profile-name").value =
      state.user.displayName || "";
    document.getElementById("profile-country").value = state.user.country || "";
    document.getElementById("profile-intake").value =
      state.user.targetIntake || "";
  }
  const mobileProfileLabel = document.querySelector(
    '[data-mobile-nav="profile"] b',
  );
  if (mobileProfileLabel) {
    mobileProfileLabel.textContent = signedIn
      ? state.user.displayName || t("mobileNavAccount")
      : t("mobileNavProfile");
  }
  deps.updateReviewAuthState();
  window.dispatchEvent(new Event("accountchange"));
}

export function openAuthPanel(message = "", settings = false) {
  if (state.user && !settings) {
    deps.openHome();
    return;
  }
  const panel = document.getElementById("auth-panel");
  if (!panel) return;
  panel.hidden = false;
  setAuthStatus(message);
  updateAuthUi();
  if (!state.user) {
    ensureTurnstileWidget(
      AUTH_TURNSTILE_CONTAINER,
      AUTH_TURNSTILE_ACTION,
    ).catch(() => setAuthStatus(t("authChallengeError"), "error"));
  }
  const email = document.getElementById("auth-email");
  const profileName = document.getElementById("profile-name");
  requestAnimationFrame(() => {
    if (state.user) profileName?.focus();
    else email?.focus();
  });
}

function closeAuthPanel() {
  const panel = document.getElementById("auth-panel");
  if (panel) panel.hidden = true;
}

async function refreshMe() {
  if (!state.authToken) return;
  const base = authApiBase();
  if (!base) return;
  try {
    const response = await fetch(`${base}/me`, {
      headers: authHeaders(false),
    });
    if (response.status === 401) {
      saveAuthToken("");
      useGuestFavorites();
      updateAuthUi();
      deps.render();
      return;
    }
    if (!response.ok) throw new Error("auth unavailable");
    const payload = await response.json();
    useSignedInFavorites(payload.user, payload.favorites || []);
    scheduleFavoriteSync();
  } catch {
    setAuthStatus(t("authError"), "error");
  }
  updateAuthUi();
  deps.updateFavoriteControls();
  deps.render();
}

export function scheduleFavoriteSync() {
  if (!state.authToken || !state.user) return;
  clearTimeout(state.favoriteSyncTimer);
  state.favoriteSyncStatus = "pending";
  deps.updateFavoriteControls();
  state.favoriteSyncTimer = setTimeout(syncFavorites, 400);
}

async function syncFavorites() {
  if (!state.authToken || !state.user) return;
  if (favoriteSyncInFlight) {
    state.favoriteSyncTimer = setTimeout(syncFavorites, 400);
    return;
  }
  const base = authApiBase();
  if (!base) return;
  favoriteSyncInFlight = true;
  const token = state.authToken;
  const storageKey = userFavoritesKey();
  const pendingSnapshot = pendingFavorites();
  state.favoriteSyncStatus = "syncing";
  deps.updateFavoriteControls();
  try {
    const response = await fetch(`${base}/me/favorites`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ favorites: [...state.favorites] }),
    });
    if (state.authToken !== token) return;
    if (response.status === 401) {
      saveAuthToken("");
      useGuestFavorites();
      updateAuthUi();
      deps.updateFavoriteControls();
      deps.render();
      return;
    }
    if (!response.ok) throw new Error("favorite sync failed");
    const pending = pendingFavorites();
    for (const [key, saved] of Object.entries(pendingSnapshot)) {
      if (pending[key] === saved) delete pending[key];
    }
    localStorage.setItem(`${storageKey}:pending`, JSON.stringify(pending));
    state.favoriteSyncStatus = "synced";
  } catch {
    if (state.authToken === token) state.favoriteSyncStatus = "error";
  } finally {
    favoriteSyncInFlight = false;
  }
  deps.updateFavoriteControls();
  window.dispatchEvent(new Event("accountchange"));
}

async function requestLoginCode(email) {
  const base = authApiBase();
  if (!base) throw new Error("auth unavailable");
  setAuthStatus(t("authSendingCode"));
  await ensureTurnstileWidget(AUTH_TURNSTILE_CONTAINER, AUTH_TURNSTILE_ACTION);
  const challengeToken = turnstileToken(AUTH_TURNSTILE_CONTAINER);
  if ((window.GRADWINDOW_CONFIG?.turnstileSiteKey || "") && !challengeToken) {
    throw new Error("challenge required");
  }
  const response = await fetch(`${base}/auth/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      language: state.language,
      turnstileToken: challengeToken,
    }),
  });
  if (!response.ok) throw new Error("login request failed");
  resetTurnstileWidget(AUTH_TURNSTILE_CONTAINER);
  setAuthStep("code");
  setAuthStatus(t("authCodeSent"), "success");
}

async function verifyLoginCode(email, code) {
  const base = authApiBase();
  if (!base) throw new Error("auth unavailable");
  setAuthStatus(t("authVerifying"));
  const response = await fetch(`${base}/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      code,
      ...(["register", "reset"].includes(authMode)
        ? { password: document.getElementById("auth-password").value }
        : {}),
    }),
  });
  if (!response.ok) throw new Error("login verify failed");
  const payload = await response.json();
  finishLogin(payload);
}

function finishLogin(payload) {
  saveAuthToken(payload.token || "");
  useSignedInFavorites(payload.user, payload.favorites || []);
  setAuthStatus(t("authSignedIn"), "success");
  updateAuthUi();
  deps.updateFavoriteControls();
  deps.render();
  scheduleFavoriteSync();
  document.getElementById("auth-password").value = "";
  document.getElementById("auth-password-confirm").value = "";
  document.getElementById("auth-code").value = "";
  closeAuthPanel();
  deps.openHome();
}

function setAuthMode(mode) {
  authMode = mode;
  setAuthStep("email");
  const password = document.getElementById("auth-password");
  const confirm = document.getElementById("auth-password-confirm");
  const setting = ["register", "reset"].includes(mode);
  document.getElementById("auth-password-fields").hidden = mode === "code";
  password.required = mode !== "code";
  password.autocomplete = setting ? "new-password" : "current-password";
  password.value = "";
  confirm.value = "";
  confirm.required = setting;
  confirm.hidden = !setting;
  document.getElementById("auth-confirm-label").hidden = !setting;
  const submit = document.getElementById("auth-request-button");
  submit.dataset.i18n = mode === "password" ? "passwordLogin" : "sendLoginCode";
  submit.textContent = t(submit.dataset.i18n);
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.authMode === mode),
    );
  });
  setAuthStatus(setting ? t("passwordSetup") : "");
}

async function passwordLogin(email) {
  const base = authApiBase();
  if (!base) throw new Error("auth unavailable");
  await ensureTurnstileWidget(AUTH_TURNSTILE_CONTAINER, AUTH_TURNSTILE_ACTION);
  const token = turnstileToken(AUTH_TURNSTILE_CONTAINER);
  if (window.GRADWINDOW_CONFIG?.turnstileSiteKey && !token)
    throw new Error("challenge required");
  try {
    const response = await fetch(`${base}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password: document.getElementById("auth-password").value,
        turnstileToken: token,
      }),
    });
    if (!response.ok) {
      const error = new Error("login failed");
      error.status = response.status;
      throw error;
    }
    finishLogin(await response.json());
  } finally {
    resetTurnstileWidget(AUTH_TURNSTILE_CONTAINER);
  }
}

async function saveProfile() {
  const base = authApiBase();
  if (!base || !state.authToken) throw new Error("auth unavailable");
  const response = await fetch(`${base}/me`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({
      displayName: document.getElementById("profile-name").value,
      country: document.getElementById("profile-country").value,
      targetIntake: document.getElementById("profile-intake").value,
      language: state.language,
    }),
  });
  if (!response.ok) throw new Error("profile failed");
  const payload = await response.json();
  state.user = payload.user || state.user;
  setAuthStatus(t("authProfileSaved"), "success");
  updateAuthUi();
}

async function signOut() {
  clearTimeout(state.favoriteSyncTimer);
  const base = authApiBase();
  if (base && state.authToken) {
    try {
      await fetch(`${base}/auth/logout`, {
        method: "POST",
        headers: authHeaders(false),
      });
    } catch {
      // Local sign-out still clears the session from this browser.
    }
  }
  if (state.user) {
    localStorage.setItem(
      userFavoritesKey(),
      JSON.stringify([...state.favorites]),
    );
  }
  saveAuthToken("");
  useGuestFavorites();
  setAuthStatus("");
  setAuthStep("email");
  updateAuthUi();
  deps.updateFavoriteControls();
  deps.render();
}

export function setupAuthPanel() {
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () =>
      setAuthMode(button.dataset.authMode),
    );
  });
  document
    .getElementById("account-password-reset")
    ?.addEventListener("click", () => {
      document.getElementById("auth-signed-in").hidden = true;
      document.getElementById("auth-signed-out").hidden = false;
      setAuthMode("reset");
      ensureTurnstileWidget(
        AUTH_TURNSTILE_CONTAINER,
        AUTH_TURNSTILE_ACTION,
      ).catch(() => setAuthStatus(t("authChallengeError"), "error"));
      document.getElementById("auth-email").focus();
    });
  document.getElementById("auth-toggle")?.addEventListener("click", () => {
    openAuthPanel();
  });
  document.querySelectorAll("[data-auth-close]").forEach((button) => {
    button.addEventListener("click", closeAuthPanel);
  });
  document
    .getElementById("auth-request-form")
    ?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = document.getElementById("auth-request-button");
      const email = document.getElementById("auth-email").value.trim();
      button.disabled = true;
      try {
        if (
          ["register", "reset"].includes(authMode) &&
          document.getElementById("auth-password").value !==
            document.getElementById("auth-password-confirm").value
        ) {
          setAuthStatus(t("passwordMismatch"), "error");
          return;
        }
        if (authMode === "password") await passwordLogin(email);
        else {
          await requestLoginCode(email);
          document.getElementById("auth-code").focus();
        }
      } catch (error) {
        setAuthStatus(
          t(
            error.status === 429
              ? "authRateLimited"
              : error.status === 401
                ? "passwordLoginError"
                : "authError",
          ),
          "error",
        );
        resetTurnstileWidget(AUTH_TURNSTILE_CONTAINER);
      } finally {
        button.disabled = false;
      }
    });
  document
    .getElementById("auth-change-email")
    ?.addEventListener("click", () => {
      document.getElementById("auth-code").value = "";
      setAuthStep("email");
      setAuthStatus("");
      ensureTurnstileWidget(
        AUTH_TURNSTILE_CONTAINER,
        AUTH_TURNSTILE_ACTION,
      ).catch(() => setAuthStatus(t("authChallengeError"), "error"));
      document.getElementById("auth-email")?.focus();
    });
  document
    .getElementById("auth-verify-form")
    ?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = document.getElementById("auth-verify-button");
      const email = document.getElementById("auth-email").value.trim();
      const code = document.getElementById("auth-code").value.trim();
      button.disabled = true;
      try {
        await verifyLoginCode(email, code);
      } catch {
        setAuthStatus(t("authError"), "error");
      } finally {
        button.disabled = false;
      }
    });
  document
    .getElementById("profile-form")
    ?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = document.getElementById("profile-save-button");
      button.disabled = true;
      try {
        await saveProfile();
      } catch {
        setAuthStatus(t("authError"), "error");
      } finally {
        button.disabled = false;
      }
    });
  document
    .getElementById("auth-logout-button")
    ?.addEventListener("click", signOut);
  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      !document.getElementById("auth-panel")?.hidden
    ) {
      closeAuthPanel();
    }
  });
  state.authToken = localStorage.getItem(AUTH_TOKEN_KEY) || "";
  setAuthMode("password");
  updateAuthUi();
  refreshMe();
}
