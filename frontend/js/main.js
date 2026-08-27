/* ALICE mission control — bootstrap and wiring.
   Modules are small and single-purpose, mirroring the backend. */

import { set, subscribe, aliceState, state } from "./state.js";
import { on, send, start, pause as pauseBus, resume as resumeBus } from "./bus.js";
import { startOrb } from "./core.js";
import {
  initVoice,
  toggleSpeak,
  setWakeHandlers,
  enableWakeWord,
  disableWakeWord,
  isWakeEnabled,
  cancelSpeech,
  unlockAudio,
  speak,
} from "./voice.js";
import { setSoundEnabled, sfx } from "./sound.js";
import { initAudio } from "./audio.js";
import { initWebDock, onWebOpen, toggleWeb } from "./webdock.js";
import {
  ensurePermission,
  notify,
  setPermissionStatus,
  canNotify,
} from "./notify.js";
import {
  ensureAuth,
  wireAuthGate,
  runBoot,
  scatterStars,
  requestUnlock,
} from "./startup.js";
import {
  initComposer,
  onChatDelta,
  onChatDone,
  showTyping,
  removeTyping,
  aliceSay,
  submitText,
} from "./chat.js";
import {
  initMissionHandlers,
  onTaskSnapshot,
  onTaskState,
  onTaskLog,
  onTaskDelta,
  onTaskQuestion,
  onTaskArtifact,
  refreshMission,
} from "./mission.js";
import {
  startClock,
  initMemory,
  onMemoryUpdated,
  onTelemetry,
  initArtifactViewer,
} from "./panels.js";

/* ---------------- Toasts ---------------- */

function toast(text, kind = "info") {
  const holder = document.getElementById("toasts");
  const node = document.createElement("div");
  node.className = `toast ${kind}`;
  node.textContent = text;
  holder.appendChild(node);
  requestAnimationFrame(() => node.classList.add("show"));
  setTimeout(() => {
    node.classList.remove("show");
    setTimeout(() => node.remove(), 300);
  }, 2600);
}

/* A small permission explainer — ALICE always says *why* before asking. */
function askPermission({ title, body, onAllow }) {
  const modal = document.getElementById("perm-modal");
  document.getElementById("perm-title").textContent = title;
  document.getElementById("perm-body").textContent = body;

  modal.classList.remove("hidden");

  return new Promise((resolve) => {
    const finish = (ok) => {
      modal.classList.add("hidden");
      form.removeEventListener("submit", allow);
      deny.removeEventListener("click", denyClick);
      if (ok && onAllow) onAllow();
      resolve(ok);
    };
    const allow = (e) => { e.preventDefault(); finish(true); };
    const denyClick = () => finish(false);
    const form = document.getElementById("perm-form");
    const deny = document.getElementById("perm-deny");
    form.addEventListener("submit", allow);
    deny.addEventListener("click", denyClick);
  });
}

/* ---------------- Identity ---------------- */

function greet() {
  const linked = state.brain.mode === "linked";
  const name = state.user || "Boss";

  const lines = linked
    ? `All systems online, ${name}. Full reasoning core linked — I can plan, search, act and stay on a task until it's done.
Start a mission with **mission:** or just ask. 💙`
    : `Systems online, ${name}. I'm running on my offline core — memory, planning, tools and missions all work. I can still chat, take notes, set reminders and run missions. Add an API key to *.env* for my full reasoning core.
Start a mission with **mission:**, or just talk to me. 💙`;

  aliceSay(lines, "online", "greeting");
  if (state.speak) speak(lines);
}

function maybeAskName() {
  const modal = document.getElementById("modal-name");
  const saved = localStorage.getItem("alice.user");

  if (saved) {
    send({ type: "user.name", name: saved });
    return;
  }

  modal.classList.remove("hidden");

  document.getElementById("name-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const name = document.getElementById("name-input").value.trim();
    if (name) {
      localStorage.setItem("alice.user", name);
      send({ type: "user.name", name });
    }
    modal.classList.add("hidden");
  });

  document.getElementById("name-skip").addEventListener("click", () => modal.classList.add("hidden"));
}

/* ---------------- Socket wiring ---------------- */

function wireBus() {

  on("hello", (event) => {
    set({
      identity: event.identity,
      brain: event.identity.brain,
      telemetry: event.telemetry,
      memory: event.memory,
      user: event.user,
      tasks: event.tasks,
    });

    onTelemetry({ telemetry: event.telemetry, identity: event.identity });

    (event.tasks || []).forEach((task) => onTaskSnapshot({ task }));

    aliceState("idle");

    if (!state.greeted) {
      set({ greeted: true });
      greet();
    }

    maybeAskName();
  });

  on("chat.delta", (event) => {
    removeTyping();
    onChatDelta(event);
  });

  on("chat.done", (event) => onChatDone(event));

  on("task.snapshot", onTaskSnapshot);
  on("task.state", onTaskState);
  on("task.log", onTaskLog);
  on("task.delta", onTaskDelta);
  on("task.question", onTaskQuestion);
  on("task.artifact", onTaskArtifact);
  on("memory.updated", onMemoryUpdated);
  on("system.telemetry", onTelemetry);
  on("user.updated", (event) => set({ user: event.name }));

  on("web.open", (event) => onWebOpen(event));

  on("system.notify", (event) => {
    notify(event.title || "Alice", event.body || "");
    sfx.notify();
  });

  on("reminder.fire", (event) => {
    notify(event.task || "Reminder", event.time ? `Scheduled: ${event.time}` : "");
    sfx.notify();
    const line = event.text || event.task || "Reminder";
    aliceSay(`⏰ ${line}`, "reminder", `reminder-${event.resolved || Date.now()}`);
    if (state.speak) speak(line);
  });

  on("pong", () => set({ link: "online" }));

  on("auth.required", () => {
    pauseBus();
    set({ link: "offline" });
    requestUnlock().then((ok) => {
      if (ok) {
        set({ link: "online" });
        resumeBus();
      }
    });
  });
}

/* ---------------- Status chips + buttons ---------------- */

function wireStatus() {

  subscribe((s) => {
    const label = { connecting: "linking", online: "online", offline: "offline" }[s.link];
    const linkLabel = document.getElementById("link-label");
    if (linkLabel.textContent !== label) linkLabel.textContent = label;

    document.getElementById("link-dot").style.background =
      s.link === "online" ? "var(--good)" : s.link === "offline" ? "var(--bad)" : "var(--warn)";

    document.getElementById("link-dot").style.boxShadow = "0 0 8px currentColor";

    const brainLabel = document.getElementById("brain-label");
    const brainText = s.brain.mode === "linked" ? `linked · ${s.brain.label}` : "offline core";
    if (brainLabel.textContent !== brainText) brainLabel.textContent = brainText;

    const stateLabels = {
      boot: "booting",
      idle: "idle",
      thinking: "thinking",
      speaking: "speaking",
      listening: "listening",
      working: "mission",
      waiting: "needs you",
    };

    const stateLabel = document.getElementById("state-label");
    const orbState = document.getElementById("orb-state");
    const text = stateLabels[s.aliceState] || s.aliceState;

    if (stateLabel.textContent !== text) {
      stateLabel.textContent = text;
      orbState.textContent = text;
    }

    /* speaking / listening indication */
    const wave = document.getElementById("wave");
    wave.classList.toggle("on", s.speak && s.aliceState !== "boot");

    const wakeHint = document.getElementById("wake-hint");
    wakeHint.classList.toggle("hidden", !s.wake);
    const wakeText = document.getElementById("wake-hint-text");
    if (wakeText && s.wake) wakeText.textContent = "listening for your instruction…";

    updateWakeButton();
    updateNotifyButton();
  });

  document.getElementById("btn-voice").addEventListener("click", (e) => {
    unlockAudio();
    const on = toggleSpeak();
    e.currentTarget.setAttribute("aria-pressed", String(on));
    e.currentTarget.classList.toggle("active", on);
    if (on) {
      const line = "Voice online. I'll read my replies aloud from here.";
      aliceSay(line, null, `voice-${Date.now()}`);
      // Speak immediately so the user hears Alice right away.
      speak(line);
      toast("Alice will speak her replies", "good");
    } else {
      toast("Alice muted");
    }
  });

  // Reflect speak preference on the button (default ON so Alice talks).
  const voiceBtn = document.getElementById("btn-voice");
  if (voiceBtn) {
    voiceBtn.setAttribute("aria-pressed", String(Boolean(state.speak)));
    voiceBtn.classList.toggle("active", Boolean(state.speak));
    voiceBtn.title = state.speak
      ? "Alice speaks — tap to mute"
      : "Alice muted — tap so she reads replies aloud";
  }

  document.getElementById("btn-sound").addEventListener("click", (e) => {
    const next = e.currentTarget.getAttribute("aria-pressed") !== "true";
    e.currentTarget.setAttribute("aria-pressed", String(next));
    setSoundEnabled(next);
    if (next) sfx.message();
  });

  setInterval(() => send({ type: "ping" }), 20000);
}

/* ---------------- Voice / hands-free ---------------- */

function updateWakeButton() {
  const btn = document.getElementById("btn-wake");
  const on = isWakeEnabled();
  btn.setAttribute("aria-pressed", String(on));
  btn.classList.toggle("active", on);
  btn.title = on ? "Hands-free on — tap to mute" : "Hands-free — say “Hey Alice”";
}

function updateNotifyButton() {
  const btn = document.getElementById("btn-notify");
  const on = canNotify();
  btn.setAttribute("aria-pressed", String(on));
  btn.classList.toggle("active", on);
  btn.title = on ? "Notifications on" : "Enable notifications";
}

function wakeInterim(text) {
  const hint = document.getElementById("wake-hint");
  const label = document.getElementById("wake-hint-text");
  if (label) label.textContent = text ? `“${text}”` : "listening for your instruction…";
}

function wireVoice() {
  setWakeHandlers({
    onWake: () => {
      set({ wake: true, listening: true });
      sfx.wake();
      aliceState("listening");
    },
    onCommand: (command) => {
      aliceState("thinking");
      submitText(command);
    },
    onInterim: wakeInterim,
    onPermissionDenied: () => {
      disableWakeWord();
      toast("Mic permission denied — hands-free off", "warn");
    },
    onError: (message) => {
      toast(message || "Mic error", "warn");
    },
  });

  document.getElementById("btn-wake").addEventListener("click", async () => {
    unlockAudio();
    if (isWakeEnabled()) {
      disableWakeWord();
      cancelSpeech();
      toast("Hands-free off");
      return;
    }

    const ok = await askPermission({
      title: "Enable hands-free?",
      body: "To hear “Hey Alice” at any time and interrupt me mid-sentence, I need microphone access. On Android, the mic button (tap-to-talk) is the most reliable way to speak to me — hands-free works best on desktop Chrome.",
      onAllow: async () => {
        const started = await enableWakeWord();
        if (started) toast("Hands-free online — say “Hey Alice”", "good");
        else toast("Hands-free unavailable here — use the mic button instead", "warn");
      },
    });

    if (ok) updateWakeButton();
  });

  // Unlock audio on first user gesture anywhere — required for Android TTS.
  const unlockOnce = () => {
    unlockAudio();
    document.removeEventListener("pointerdown", unlockOnce, true);
    document.removeEventListener("keydown", unlockOnce, true);
  };
  document.addEventListener("pointerdown", unlockOnce, true);
  document.addEventListener("keydown", unlockOnce, true);
}

/* ---------------- Web deck ---------------- */

function wireWeb() {
  initWebDock();
}

/* ---------------- Notifications ---------------- */

function wireNotify() {
  setPermissionStatus();

  document.getElementById("btn-notify").addEventListener("click", async () => {
    if (canNotify()) {
      toast("Notifications already enabled");
      return;
    }

    const ok = await askPermission({
      title: "Enable notifications?",
      body: "I'd like to ping you when a long mission finishes, a background task completes, or a reminder is due — even while the tab is in the background. I only ever send these after this permission.",
      onAllow: () => ensurePermission(),
    });

    if (ok) {
      toast("Notifications enabled");
      updateNotifyButton();
      notify("ALICE", "Notifications are online. I'll ping you when something's ready.");
    }
  });
}

/* ---------------- Launch ---------------- */

async function main() {
  scatterStars();
  startOrb();
  initAudio();
  startClock();
  initMemory();
  initArtifactViewer();
  initMissionHandlers();
  initComposer();
  initVoice();
  wireBus();
  wireStatus();
  wireVoice();
  wireWeb();
  wireNotify();
  wireAuthGate();

  // 1. Secure access first.
  const unlocked = await ensureAuth();

  // 2. Cinematic boot only once you're in.
  if (unlocked) {
    await runBoot();
    set({ booted: true });
    sfx.boot();
    document.getElementById("app").classList.remove("hidden");
    aliceState("idle");
  }

  // 3. Open the live wire.
  start();

  // 4. Make ALICE installable as a PWA (never blocks the boot).
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js").catch(() => { /* offline unsupported */ });
  }

  // Deep-link: /?action=mission pre-arms the composer for a mission.
  const action = new URLSearchParams(location.search).get("action");
  if (action === "mission") {
    state.mode = "mission";
    const picker = document.getElementById("mode-picker");
    const missionBtn = picker.querySelector('button[data-mode="mission"]');
    if (missionBtn) {
      picker.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === missionBtn));
    }
  }

  refreshMission();
}

main();
