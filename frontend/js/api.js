/**
 * frontend/js/api.js
 *
 * Central place for talking to the backend API. Every other JS file goes
 * through the functions here rather than calling fetch() directly, so auth
 * headers, error shape, and base URL only need to be handled in one place.
 */

const API_BASE_URL = "/api/v1";

/**
 * Session storage backend depends on "Remember me": checked -> localStorage
 * (survives closing the browser), unchecked -> sessionStorage (cleared when
 * the tab closes). The remember choice itself is always kept in
 * localStorage as a small flag so every page can find the right backend
 * without needing the checkbox value passed around.
 */
function isRememberMeEnabled() {
  return localStorage.getItem("ats_remember_me") === "1";
}

function setRememberMe(remember) {
  localStorage.setItem("ats_remember_me", remember ? "1" : "0");
}

function getSessionStorageBackend() {
  return isRememberMeEnabled() ? localStorage : sessionStorage;
}

function getAccessToken() {
  return getSessionStorageBackend().getItem("ats_access_token");
}

function getRefreshToken() {
  return getSessionStorageBackend().getItem("ats_refresh_token");
}

function getCurrentUser() {
  const raw = getSessionStorageBackend().getItem("ats_user");
  return raw ? JSON.parse(raw) : null;
}

function storeSession({ access_token, refresh_token, user }) {
  const storage = getSessionStorageBackend();
  if (access_token) storage.setItem("ats_access_token", access_token);
  if (refresh_token) storage.setItem("ats_refresh_token", refresh_token);
  if (user) storage.setItem("ats_user", JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem("ats_access_token");
  localStorage.removeItem("ats_refresh_token");
  localStorage.removeItem("ats_user");
  localStorage.removeItem("ats_remember_me");
  sessionStorage.removeItem("ats_access_token");
  sessionStorage.removeItem("ats_refresh_token");
  sessionStorage.removeItem("ats_user");
}

/**
 * Redirects to the login page if there's no access token. Call this at the
 * top of every protected page (dashboard, upload, results) before doing
 * anything else.
 */
function requireAuth() {
  if (!getAccessToken()) {
    window.location.href = "login.html";
  }
}

/**
 * Low-level request helper. Attaches the Authorization header automatically,
 * parses JSON, and normalizes errors into a thrown Error with a `.message`
 * matching the backend's { success, data, message } envelope.
 *
 * `isFormData` skips the JSON content-type header so the browser can set
 * the correct multipart boundary itself for file uploads.
 */
async function apiRequest(path, { method = "GET", body = null, isFormData = false } = {}) {
  const headers = {};
  const token = getAccessToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body && !isFormData) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    });
  } catch (networkError) {
    // Backend unreachable — surface a clear error so calling code can
    // fall back to demo data instead of leaving the UI blank.
    throw new Error("NETWORK_ERROR");
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
    /* no JSON body (e.g. 204) */
  }

  if (response.status === 401) {
    clearSession();
    window.location.href = "login.html";
    throw new Error("Session expired. Please sign in again.");
  }

  if (!response.ok) {
    const message = (payload && payload.message) || `Request failed (${response.status})`;
    const err = new Error(message);
    err.status = response.status;
    err.payload = payload;
    throw err;
  }

  return payload;
}

const api = {
  get: (path) => apiRequest(path, { method: "GET" }),
  post: (path, body, isFormData = false) => apiRequest(path, { method: "POST", body, isFormData }),
  patch: (path, body) => apiRequest(path, { method: "PATCH", body }),
  delete: (path) => apiRequest(path, { method: "DELETE" }),
};
