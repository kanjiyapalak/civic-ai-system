import { getToken } from "./auth";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function apiRequest(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const token = getToken();
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {})
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json();
  }

  if (!response.ok) {
    const message = payload?.detail || payload?.message || "Request failed";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload;
}

export { getToken };
