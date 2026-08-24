/* ALICE mission control — bootstrap and wiring.
   Modules are small and single-purpose, mirroring the backend. */

import { set, subscribe, aliceState, state } from "./state.js";
import { on, send, start } from "./bus.js";
import { startOrb } from "./core.js";
import { initVoice, toggleSpeak } from "./voice.js";
import { setSoundEnabled, sfx } from "./sound.js";
import {
  initComposer,
  onChatDelta,
  onChatDone,
  showTyping,
  removeTyping,
  aliceSay,
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

/* ---------------- Boot sequence ---------------- */

const BOOT_LINES = [
  ["boot", "ALICE kernel 2.0 — cold start"],
  ["ok", "cognitive core ............ online"],
  ["ok", "memory lattice ............ mounted"],
  ["ok", "tool registry ............. 19 instruments"],
  ["ok", "mission engine ............ armed"],
  ["ok", "voice interface ........... ready"],
  ["ok", "event bus ................. live"],
  ["boot", "handshake with mission control"],
];

function typeBoot() {

  return new Promise((resolve) => {

    const log = document.getElementById("boot-log");

    let line = 0;
    let char = 0;
    let buffer = "";
    let skipped = false;

    const finish = () => {

      if (skipped) return;

      skipped = true;

      document.getElementById("boot").classList.add("off");

      resolve();
    };

    const step = () => {

      if (skipped) return;

      if (line >= BOOT_LINES.length) {
        setTimeout(finish, 500);
        return;
      }

      const [kind, text] = BOOT_LINES[line];

      if (char === 0 && kind !== "boot") buffer += "  ";

      if (char < text.length) {

        buffer += text[char++];
        log.innerHTML = buffer
          .split("\n")
          .map((l) => `<span>${l}</span>`)
          .join("\n");

        setTimeout(step, 8 + Math.random() * 14);

      } else {

        buffer += "\n";
        line += 1;
        char = 0;

        setTimeout(step, 90);
      }
    };

    document.getElementById("boot").addEventListener("click", finish);

    step();
  });
}

/* ---------------- Ambient stars ---------------- */

function scatterStars() {

  const field = document.getElementById("stars");

  for (let i = 0; i < 70; i++) {

    const star = document.createElement("i");
    star.className = "star";

    star.style.left = `${Math.random() * 100}%`;
    star.style.top = `${Math.random() * 100}%`;
    star.style.animationDelay = `${Math.random() * 4}s`;
    star.style.opacity = String(0.15 + Math.random() * 0.5);

    if (Math.random() > 0.85) {
      star.style.width = "3px";
      star.style.height = "3px";
      star.style.boxShadow = "0 0 6px rgba(190,235,255,0.9)";
    }

    field.appendChild(star);
  }
}

/* ---------------- Identity ---------------- */

function greet() {

  const linked = state.brain.mode === "linked";
  const name = state.user || "Boss";

  const lines = linked
    ? `All systems online, ${name}. Full reasoning core linked — I can plan, search, act and stay on a task until it's done.\nStart a mission with **mission:** or just ask. 💙`
    : `Systems online, ${name}. I'm running on my offline core — memory, planning, tools and missions all work. Add an API key to *.env* to wake my full reasoning core.\nStart a mission with **mission:**. 💙`;

  aliceSay(lines, "online", "greeting");
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

  on("pong", () => set({ link: "online" }));
}

/* ---------------- Status chips ---------------- */

function wireStatus() {

  subscribe((s) => {

    const label = {
      connecting: "linking",
      online: "online",
      offline: "offline",
    }[s.link];

    const linkLabel = document.getElementById("link-label");

    if (linkLabel.textContent !== label) linkLabel.textContent = label;

    document.getElementById("link-dot").style.background =
      s.link === "online" ? "var(--good)" : s.link === "offline" ? "var(--bad)" : "var(--warn)";

    document.getElementById("link-dot").style.boxShadow = `0 0 8px currentColor`;

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

    /* speaking indicator */
    const wave = document.getElementById("wave");
    wave.classList.toggle("on", s.speak && s.aliceState !== "boot");
  });

  document.getElementById("btn-voice").addEventListener("click", (e) => {

    const on = toggleSpeak();

    e.currentTarget.setAttribute("aria-pressed", String(on));

    if (on) aliceSay("Voice online. I'll read my replies aloud from here.", null, `voice-${Date.now()}`);
  });

  document.getElementById("btn-sound").addEventListener("click", (e) => {

    const next = e.currentTarget.getAttribute("aria-pressed") !== "true";

    e.currentTarget.setAttribute("aria-pressed", String(next));
    setSoundEnabled(next);

    if (next) sfx.message();
  });

  /* heartbeat ping */
  setInterval(() => send({ type: "ping" }), 20000);
}

/* ---------------- Launch ---------------- */

async function main() {

  scatterStars();

  startOrb();
  startClock();
  initMemory();
  initArtifactViewer();
  initMissionHandlers();
  initComposer();
  initVoice();

  wireBus();
  wireStatus();

  start();

  await typeBoot();

  set({ booted: true });

  sfx.boot();

  aliceState("idle");

  refreshMission();
}

main();
