// All communication with the Flask backend goes through this file.
// In development Vite proxies /api to Flask; in production set VITE_API_URL.

const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status = 0, code = "error") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** Turn a backend path like /api/images/x.png into a full URL for <img src>. */
export const assetUrl = (path) => `${BASE}${path}`;

async function request(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      "Cannot reach the backend. Make sure the Flask server is running on port 5000.",
      0,
      "network"
    );
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    throw new ApiError(
      data?.error?.message || `Request failed (HTTP ${res.status}).`,
      res.status,
      data?.error?.code || "error"
    );
  }
  return data;
}

export const getHealth = () => request("/api/health");

let categoriesPromise = null;
/** Categories rarely change, so fetch once and reuse. A failure is not cached. */
export function getCategories() {
  if (!categoriesPromise) {
    categoriesPromise = request("/api/categories").catch((err) => {
      categoriesPromise = null;
      throw err;
    });
  }
  return categoriesPromise;
}

export const generateImages = (params) => request("/api/generate", { method: "POST", body: params });

export function getHistory({ page = 1, limit = 12, category = "" } = {}) {
  const q = new URLSearchParams({ page, limit });
  if (category) q.set("category", category);
  return request(`/api/history?${q}`);
}

export const getGeneration = (id) => request(`/api/history/${id}`);
export const deleteGeneration = (id) => request(`/api/history/${id}`, { method: "DELETE" });
