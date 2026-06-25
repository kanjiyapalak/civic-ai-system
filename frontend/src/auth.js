import { apiRequest } from "./api";

const TOKEN_KEY = "civic_ai_token";

export function getToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export async function fetchCurrentUser() {
  return apiRequest("/auth/me");
}
