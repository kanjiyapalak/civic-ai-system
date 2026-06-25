import { getToken } from "../auth";
import { API_BASE } from "../api";

export async function apiStreamRequest(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const token = getToken();
  const headers = {
    ...(options.headers || {})
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    let message = "Request failed";
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const payload = await response.json();
      message = payload?.detail || payload?.message || message;
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return response;
}

export async function consumeSSE(response, handlers = {}) {
  if (!response.body) {
    throw new Error("Streaming is not supported in this browser");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      if (!chunk.trim()) {
        continue;
      }

      let eventName = "message";
      let dataLine = "";

      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLine = line.slice(5).trim();
        }
      }

      if (!dataLine) {
        continue;
      }

      const payload = JSON.parse(dataLine);
      const handler = handlers[eventName];
      if (handler) {
        await handler(payload);
      }
    }
  }
}
