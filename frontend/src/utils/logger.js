const isDev = import.meta.env.DEV;

/**
 * Resolve API base URL from environment or fallback.
 */
function getApiBase() {
  return (
    window.APP_CONFIG?.API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    "https://api.spravka.novamedika.com"
  ).replace(/\/$/, "");
}

/**
 * Send error data to backend logging endpoint.
 * Falls back to sendBeacon for reliability.
 */
function sendToServer(message) {
  try {
    const payload = {
      error: String(message || ""),
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
    };
    const apiUrl = getApiBase() + "/api/log/client-error";

    if (navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(payload)], {
        type: "application/json",
      });
      navigator.sendBeacon(apiUrl, blob);
    } else {
      fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(() => {});
    }
  } catch (e) {
    // Silently fail
  }
}

export const logger = {
  log: (...args) => {
    if (isDev) console.log(...args);
  },
  debug: (...args) => {
    if (isDev) console.debug(...args);
  },
  error: (...args) => {
    if (isDev) console.error(...args);
    // Send to server in production too
    sendToServer(
      args
        .map((a) => (typeof a === "object" ? JSON.stringify(a) : String(a)))
        .join(" "),
    );
  },
  warn: (...args) => {
    if (isDev) console.warn(...args);
  },
  info: (...args) => {
    if (isDev) console.info(...args);
  },
};
