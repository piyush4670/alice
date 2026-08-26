/* The Web Deck — ALICE's embedded browser.

A dockable panel with a quick-app bar and an address bar driving an iframe.
Because most sites refuse to be framed, the iframe requests the server-side
proxy (``/web/proxy``) which re-serves the page from ALICE's own origin.
When ALICE opens a site from a mission she raises a ``web.open`` event, and
the deck slides in automatically.
*/

import { set, state } from "./state.js";
import { sfx } from "./sound.js";

const APPS = [
  { key: "youtube", label: "YouTube", url: "https://www.youtube.com" },
  { key: "wikipedia", label: "Wikipedia", url: "https://en.wikipedia.org" },
  { key: "google", label: "Google", url: "https://www.google.com" },
  { key: "duckduckgo", label: "DuckDuckGo", url: "https://duckduckgo.com" },
  { key: "github", label: "GitHub", url: "https://github.com" },
  { key: "maps", label: "Maps", url: "https://maps.google.com" },
];

function el(id) {
  return document.getElementById(id);
}

function proxyUrl(url) {
  const u = new URL(url, window.location.origin);
  // Only route external http(s) through the proxy; same-origin stays direct.
  if (u.origin === window.location.origin) return u.href;
  return `/web/proxy?url=${encodeURIComponent(u.href)}`;
}

function renderApps() {
  const bar = el("web-apps");
  if (!bar) return;
  bar.innerHTML = "";
  for (const app of APPS) {
    const chip = document.createElement("button");
    chip.className = "web-app";
    chip.textContent = app.label;
    chip.addEventListener("click", () => openWeb(app.url, app.label));
    bar.appendChild(chip);
  }
}

export function openWeb(url, title = "") {
  if (!url) return;
  const frame = el("web-frame");
  const dock = el("webdeck");

  hideFallback();
  frame.src = proxyUrl(url);
  set({ webView: { open: true, url, title } });

  if (title) el("web-title").textContent = title;
  el("web-address").value = url;

  dock.classList.remove("hidden");
  dock.classList.add("open");
}

/* Detect a proxy failure (same-origin) and offer an escape hatch. */
function hideFallback() {
  el("web-fallback").classList.add("hidden");
}

function detectFallback() {
  try {
    const doc = el("web-frame").contentDocument;
    if (!doc) return;
    const text = (doc.body && doc.body.innerText) || "";
    if (/Could not load that page|Only http and https URLs are allowed|not reachable from here/i.test(text)) {
      el("web-fallback").classList.remove("hidden");
    }
  } catch {
    /* cross-origin or not ready — ignore */
  }
}

export function closeWeb() {
  const dock = el("webdeck");
  dock.classList.add("hidden");
  dock.classList.remove("open");
  const frame = el("web-frame");
  frame.src = "about:blank";
  set({ webView: { open: false, url: "", title: "" } });
}

export function toggleWeb() {
  if (state.webView.open) closeWeb();
  else openWeb("https://duckduckgo.com", "DuckDuckGo");
}

export function initWebDock() {
  renderApps();

  el("btn-web").addEventListener("click", () => {
    sfx.step();
    toggleWeb();
  });

  el("web-close").addEventListener("click", closeWeb);

  el("web-back").addEventListener("click", () => {
    try { el("web-frame").contentWindow.history.back(); } catch { /* cross-origin */ }
  });

  el("web-forward").addEventListener("click", () => {
    try { el("web-frame").contentWindow.history.forward(); } catch { /* cross-origin */ }
  });

  el("web-reload").addEventListener("click", () => {
    const frame = el("web-frame");
    if (frame.src) frame.src = frame.src;
  });

  el("web-open-tab").addEventListener("click", () => {
    const url = state.webView.url;
    if (url) window.open(url, "_blank", "noopener");
  });

  el("web-fallback-open").addEventListener("click", () => {
    const url = state.webView.url;
    if (url) window.open(url, "_blank", "noopener");
  });

  el("web-frame").addEventListener("load", () => {
    // Give the proxy a moment; then check whether it surfaced an error.
    setTimeout(detectFallback, 1200);
  });

  const form = el("web-form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = el("web-address").value.trim();
    if (!value) return;
    const url = looksLikeUrl(value) ? value : `https://duckduckgo.com/?q=${encodeURIComponent(value)}`;
    openWeb(url, value);
  });

  // Let the deck be dismissed by clicking the dim backdrop.
  el("webdeck").addEventListener("click", (e) => {
    if (e.target === el("webdeck")) closeWeb();
  });
}

function looksLikeUrl(text) {
  return /^(https?:\/\/|www\.)/i.test(text) || /^[a-z0-9-]+(\.[a-z0-9-]+)+/i.test(text);
}

/* ALICE can drive the deck from a mission via a web.open event. */
export function onWebOpen(event) {
  openWeb(event.url, event.title || event.url);
}
