const SCRIPT_SELECTOR = "script[data-gradwindow-turnstile]";
const widgets = new Map();
let loadPromise = null;

function siteKey() {
  return String(window.GRADWINDOW_CONFIG?.turnstileSiteKey || "").trim();
}

function loadTurnstileApi() {
  if (window.turnstile?.render) return Promise.resolve(window.turnstile);
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    let script = document.querySelector(SCRIPT_SELECTOR);
    const finish = () => {
      if (window.turnstile?.render) resolve(window.turnstile);
      else reject(new Error("Turnstile did not load"));
    };
    if (!script) {
      script = document.createElement("script");
      script.src =
        "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      script.defer = true;
      script.dataset.gradwindowTurnstile = "true";
      document.head.appendChild(script);
    }
    script.addEventListener("load", finish, { once: true });
    script.addEventListener(
      "error",
      () => reject(new Error("Turnstile failed to load")),
      { once: true },
    );
  });
  return loadPromise;
}

export async function ensureTurnstileWidget(containerId, action) {
  const key = siteKey();
  const container = document.getElementById(containerId);
  if (!key || !container) return null;
  if (widgets.has(containerId)) return widgets.get(containerId);

  const turnstile = await loadTurnstileApi();
  const widgetId = turnstile.render(container, {
    sitekey: key,
    action,
    theme: document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  });
  widgets.set(containerId, widgetId);
  return widgetId;
}

export function turnstileToken(containerId) {
  const widgetId = widgets.get(containerId);
  if (widgetId === undefined || !window.turnstile?.getResponse) return "";
  return window.turnstile.getResponse(widgetId) || "";
}

export function resetTurnstileWidget(containerId) {
  const widgetId = widgets.get(containerId);
  if (widgetId !== undefined && window.turnstile?.reset) {
    window.turnstile.reset(widgetId);
  }
}
