import { state } from "./state.js";
import { t } from "./strings.js";
import {
  ensureTurnstileWidget,
  resetTurnstileWidget,
  turnstileToken,
} from "./turnstile.js";

// Email-code sign-in, profile, and favourites sync for the tracker page.
// Auth updates page UI it does not own (board, favourite controls, review
// panel), so app.js injects those refreshers via initAuth() instead of this
// module importing app.js back (which would create a cycle).

const AUTH_TOKEN_KEY = "gradwindow:authToken";
const GUEST_FAVORITES_KEY = "gradwindow:favorites";
const USER_FAVORITES_PREFIX = "gradwindow:favorites:user:";
const AUTH_TURNSTILE_CONTAINER = "auth-turnstile";
const AUTH_TURNSTILE_ACTION = "auth-login";

let deps = {
  render: () => {},
  updateFavoriteControls: () => {},
  updateReviewAuthState: () => {},
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
  localStorage.setItem(key, JSON.stringify([...state.favorites]));
  state.favoriteSyncStatus = state.user ? "pending" : "local";
  deps.updateFavoriteControls();
  scheduleFavoriteSync();
}

function useSignedInFavorites(user, remoteFavorites = []) {
  if (!user?.id) throw new Error("invalid user response");
  const serverFavorites = Array.isArray(remoteFavorites) ? remoteFavorites : [];
  const guestFavorites = state.user
    ? new Set()
    : favoriteSetFromStorage(GUEST_FAVORITES_KEY);
  const accountFavorites = favoriteSetFromStorage(userFavoritesKey(user));
  state.user = user;
  state.favorites = new Set([
    ...accountFavorites,
    ...serverFavorites.filter(Boolean),
    ...guestFavorites,
  ]);
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
    toggle.textContent = signedIn
      ? state.user.displayName || t("accountTitle")
      : t("signIn");
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
}

export function openAuthPanel(message = "") {
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
    if (!response.ok) throw new Error("auth expired");
    const payload = await response.json();
    useSignedInFavorites(payload.user, payload.favorites || []);
    scheduleFavoriteSync();
  } catch {
    saveAuthToken("");
    useGuestFavorites();
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
  const base = authApiBase();
  if (!base) return;
  state.favoriteSyncStatus = "syncing";
  deps.updateFavoriteControls();
  try {
    const response = await fetch(`${base}/me/favorites`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ favorites: [...state.favorites] }),
    });
    if (response.status === 401) {
      saveAuthToken("");
      useGuestFavorites();
      updateAuthUi();
      deps.updateFavoriteControls();
      deps.render();
      return;
    }
    if (!response.ok) throw new Error("favorite sync failed");
    state.favoriteSyncStatus = "synced";
  } catch {
    state.favoriteSyncStatus = "error";
  }
  deps.updateFavoriteControls();
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
    body: JSON.stringify({ email, code }),
  });
  if (!response.ok) throw new Error("login verify failed");
  const payload = await response.json();
  saveAuthToken(payload.token || "");
  useSignedInFavorites(payload.user, payload.favorites || []);
  setAuthStatus(t("authSignedIn"), "success");
  updateAuthUi();
  deps.updateFavoriteControls();
  deps.render();
  scheduleFavoriteSync();
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
        await requestLoginCode(email);
        document.getElementById("auth-code").focus();
      } catch {
        setAuthStatus(t("authError"), "error");
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
  setAuthStep("email");
  updateAuthUi();
  refreshMe();
}
