/* Side panels: memory, telemetry, clock, artifact viewer. */

import { set, state } from "./state.js";
import { aliceState } from "./state.js";

function el(id) {
  return document.getElementById(id);
}

/* ---------------- Clock ---------------- */

export function startClock() {

  const tick = () => {

    const now = new Date();

    el("clock-time").textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    el("clock-date").textContent = now.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
  };

  tick();
  setInterval(tick, 1000);
}

/* ---------------- Memory ---------------- */

function renderMemory() {

  const list = el("memory-list");

  const entries = Object.entries(state.memory || {});

  if (!entries.length) {
    list.innerHTML = '<div class="empty">nothing stored yet</div>';
    return;
  }

  list.innerHTML = "";

  for (const [key, value] of entries) {

    const item = document.createElement("div");
    item.className = "memory-item";

    item.innerHTML = `
      <span class="k"></span>
      <span class="v" title=""></span>
      <button title="forget"><svg class="ic"><use href="#i-x"/></svg></button>`;

    item.querySelector(".k").textContent = key;
    item.querySelector(".v").textContent = value;
    item.querySelector(".v").title = value;

    item.querySelector("button").addEventListener("click", async () => {

      await fetch(`/api/memory/${encodeURIComponent(key)}`, { method: "DELETE" });

      set({ memory: Object.fromEntries(Object.entries(state.memory).filter(([k]) => k !== key)) });

      renderMemory();
    });

    list.appendChild(item);
  }
}

export function initMemory() {

  renderMemory();

  el("memory-add").addEventListener("submit", async (e) => {

    e.preventDefault();

    const input = el("memory-input");
    const pair = input.value.trim();

    if (!pair) return;

    input.value = "";

    const response = await fetch("/api/memory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pair }),
    });

    if (response.ok) {
      set({ memory: (await response.json()).items });
      renderMemory();
    }
  });
}

export function onMemoryUpdated(event) {

  set({ memory: event.items });

  renderMemory();
}

/* ---------------- Telemetry ---------------- */

function setBar(idSuffix, value) {

  const bar = el(`t-${idSuffix}`);
  const label = el(`t-${idSuffix}-v`);

  if (value == null) {
    bar.style.width = "0%";
    label.textContent = "—";
    return;
  }

  bar.style.width = `${Math.min(100, value)}%`;
  label.textContent = `${value}%`;
}

function formatUptime(startedAt) {

  const seconds = Math.max(0, Date.now() / 1000 - startedAt);

  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${s}s`;
  return `${s}s`;
}

export function onTelemetry(event) {

  const t = event.telemetry || {};

  setBar("cpu", t.cpu_load != null ? Math.min(100, t.cpu_load * 25) : null);
  setBar("mem", t.memory);
  setBar("disk", t.disk);

  el("t-uptime").textContent = formatUptime(event.identity?.started_at || state.identity?.started_at || Date.now() / 1000);
  el("t-host").textContent = (event.identity?.host || state.identity?.host || "local").slice(0, 16);

  if (event.brain) set({ brain: event.brain });
}

/* ---------------- Artifacts viewer ---------------- */

export function initArtifactViewer() {

  window.alice = window.alice || {};

  window.alice.openArtifact = async (name) => {

    const response = await fetch(`/api/artifacts/${encodeURIComponent(name)}`);

    if (!response.ok) return;

    el("artifact-title").textContent = name;
    el("artifact-body").textContent = await response.text();

    el("modal-artifact").classList.remove("hidden");
  };

  el("artifact-close").addEventListener("click", () => el("modal-artifact").classList.add("hidden"));

  el("modal-artifact").addEventListener("click", (e) => {

    if (e.target === el("modal-artifact")) el("modal-artifact").classList.add("hidden");
  });
}
