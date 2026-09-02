import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

export const client = axios.create({ baseURL: BASE_URL });

function getTokens() {
  return {
    access: localStorage.getItem("access"),
    refresh: localStorage.getItem("refresh"),
  };
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem("access", access);
  if (refresh) localStorage.setItem("refresh", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
}

/**
 * Phase 7 (CCTV) — the MJPEG stream endpoint has to be a plain <img src="">,
 * which can't carry an Authorization header, so it authenticates via a
 * `?token=` query param instead. Exported so pages can build that URL.
 */
export function getAccessToken() {
  return getTokens().access;
}

export const API_BASE_URL = BASE_URL;

client.interceptors.request.use((config) => {
  const { access } = getTokens();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

// If an access token expires mid-session, use the refresh token once to get
// a new one and retry the original request, instead of forcing a re-login.
let refreshInFlight = null;

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const { refresh } = getTokens();

    if (error.response?.status === 401 && refresh && !original._retried) {
      original._retried = true;
      try {
        if (!refreshInFlight) {
          refreshInFlight = axios
            .post(`${BASE_URL}/auth/refresh/`, { refresh })
            .finally(() => {
              refreshInFlight = null;
            });
        }
        const { data } = await refreshInFlight;
        setTokens({ access: data.access });
        original.headers.Authorization = `Bearer ${data.access}`;
        return client(original);
      } catch (refreshError) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Shared helper for "download this as a file" buttons (CSV exports, the
 * AI Risk Report PDF, etc). Fetches `url` as a blob through the same JWT
 * client used everywhere else, then triggers a browser download with
 * `filename`. Throws on failure so callers can show their own error state.
 */
export async function downloadBlob(url, filename) {
  const res = await client.get(url, { responseType: "blob" });
  const blob = new Blob([res.data], { type: res.headers["content-type"] || "application/octet-stream" });
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}
