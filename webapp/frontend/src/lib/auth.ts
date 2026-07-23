// Single-password auth state, kept in localStorage. When the backend has no
// password configured, auth is disabled and the token stays empty.

const TOKEN_KEY = "ta_web_token";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// Header to attach to REST calls (empty object when no token).
export function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

// EventSource can't set headers, so SSE URLs carry the token as a query param.
export function withTokenParam(url: string): string {
  const t = getToken();
  if (!t) return url;
  return url + (url.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(t);
}

// Listeners notified when a 401 is seen, so the app can bounce to the login page.
type Listener = () => void;
const unauthorizedListeners = new Set<Listener>();

export function onUnauthorized(fn: Listener): () => void {
  unauthorizedListeners.add(fn);
  return () => unauthorizedListeners.delete(fn);
}

export function notifyUnauthorized(): void {
  clearToken();
  unauthorizedListeners.forEach((fn) => fn());
}
