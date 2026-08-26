/* Startup: secure access, then a cinematic boot sequence.

ALICE never opens the dashboard until the passcode gate lets you in. Once
unlocked she runs a short system boot and only then hands over to Mission
Control. Everything here is cosmetic plumbing around two real calls:
``/api/auth/check`` (am I needed?) and ``/api/auth`` (am I allowed?).
*/

import { set } from "./state.js";
import { sfx } from "./sound.js";

const BOOT_LINES = [
  ["boot", "ALICE kernel 2.1 — cold start"],
  ["ok", "cognitive core ............ online"],
  ["ok", "memory lattice ............ mounted"],
  ["ok", "tool registry ............. 21 instruments"],
  ["ok", "mission engine ............ armed"],
  ["ok", "voice interface ........... ready"],
  ["ok", "wake word ................. “Hey Alice”"],
  ["ok", "web deck .................. linked"],
  ["ok", "event bus ................. live"],
  ["boot", "handshake with mission control"],
];

let unlockResolve = null;

function el(id) {
  return document.getElementById(id);
}

/* ---------------- Auth gate ---------------- */

async function authCheck() {
  try {
    const res = await fetch("/api/auth/check");
    return await res.json();
  } catch {
    // No reachable server — don't lock the user out of the shell.
    return { required: false, authorised: true };
  }
}

export async function ensureAuth() {
  const info = await authCheck();

  if (!info.required || info.authorised) {
    set({ auth: "open" });
    return true;
  }

  return requestUnlock();
}

/** Show the passcode gate and wait for the user to unlock. */
export function requestUnlock() {
  set({ auth: "locked" });
  const gate = el("auth");
  gate.classList.remove("hidden");
  gate.classList.add("open");

  const input = el("auth-pin");
  const error = el("auth-error");

  if (input) setTimeout(() => input.focus(), 60);
  if (error) {
    error.textContent = "";
    error.classList.add("hidden");
  }

  return new Promise((resolve) => {
    unlockResolve = resolve;
  });
}

export function resolveUnlock(ok) {
  if (unlockResolve) {
    const resolve = unlockResolve;
    unlockResolve = null;
    resolve(ok);
  }
}

export function wireAuthGate() {
  const form = el("auth-form");
  const input = el("auth-pin");
  const error = el("auth-error");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const passcode = input.value.trim();
    if (!passcode) return;

    error.classList.add("hidden");

    try {
      const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passcode }),
      });

      if (res.ok) {
        input.value = "";
        el("auth").classList.add("hidden");
        el("auth").classList.remove("open");
        set({ auth: "open" });
        sfx.boot();
        resolveUnlock(true);
        return;
      }

      error.textContent = res.status === 429
        ? "too many attempts — wait a minute"
        : "wrong access code";
      error.classList.remove("hidden");
      error.style.animation = "none";
      void error.offsetWidth;
      error.style.animation = "";

    } catch {
      error.textContent = "cannot reach Alice";
      error.classList.remove("hidden");
    }
  });

  // Entering the dash lets you press unlock too, but keep it simple & safe.
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const gate = el("auth");
      if (!gate.classList.contains("hidden")) {
        // Do not allow escape to bypass the gate; no-op.
      }
    }
  });
}

/* ---------------- Boot sequence ---------------- */

export function runBoot() {
  return new Promise((resolve) => {
    const log = el("boot-log");

    let line = 0;
    let char = 0;
    let buffer = "";
    let skipped = false;

    const finish = () => {
      if (skipped) return;
      skipped = true;
      el("boot").classList.add("off");
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
        setTimeout(step, 70);
      }
    };

    el("boot").addEventListener("click", finish);
    step();
  });
}

export function scatterStars() {
  const field = el("stars");
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
