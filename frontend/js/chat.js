/* The conversation stream and composer. */

import { md, plain } from "./md.js";
import { state, aliceState } from "./state.js";
import { send } from "./bus.js";
import { speak, startListening, stopListening, canListen } from "./voice.js";
import { sfx } from "./sound.js";

const streamEl = () => document.getElementById("stream");

const live = new Map(); // mid -> { bubble, text }

function scrollDown() {

  const el = streamEl();

  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 140;

  if (nearBottom) el.scrollTop = el.scrollHeight;
}

export function addUserMessage(text) {

  const wrap = document.createElement("div");
  wrap.className = "msg user";

  wrap.innerHTML = `
    <div class="avatar"><svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2"><circle cx="12" cy="8" r="3.6"/><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0"/></svg></div>
    <div class="bubble"><div class="md"></div></div>`;

  wrap.querySelector(".md").textContent = text;

  streamEl().appendChild(wrap);
  scrollDown();
}

export function aliceBubble(mid, tag = null) {

  if (live.has(mid)) return live.get(mid);

  const wrap = document.createElement("div");
  wrap.className = "msg alice";

  wrap.innerHTML = `
    <div class="avatar"><svg viewBox="0 0 100 100"><polygon points="50,6 90,28 90,72 50,94 10,72 10,28"/></svg></div>
    <div class="bubble">
      <div class="meta"><span class="who">Alice</span>${tag ? `<span class="msg-tag">${tag}</span>` : ""}</div>
      <div class="md"></div>
    </div>`;

  streamEl().appendChild(wrap);

  const entry = { wrap, md: wrap.querySelector(".md"), text: "" };

  live.set(mid, entry);

  scrollDown();

  return entry;
}

function renderStreaming(entry) {

  entry.md.innerHTML = md(entry.text);
  entry.md.insertAdjacentHTML("beforeend", '<span class="caret"></span>');

  scrollDown();
}

export function onChatDelta(event) {

  const entry = aliceBubble(event.mid);

  entry.text += event.text;

  renderStreaming(entry);
}

export function onChatDone(event) {

  const entry = aliceBubble(event.mid);

  entry.md.innerHTML = md(event.message || entry.text);

  live.delete(event.mid);

  scrollDown();

  sfx.message();
  speak(event.message || entry.text);

  if (state.aliceState === "thinking") aliceState("idle");
}

export function showTyping(mid = "typing") {

  const entry = aliceBubble(mid);

  if (!entry.text) {

    entry.md.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';

    scrollDown();
  }

  return entry;
}

export function removeTyping(mid = "typing") {

  const entry = live.get(mid);

  if (entry && !entry.text) {
    entry.wrap.remove();
    live.delete(mid);
  }
}

export function aliceSay(text, tag = null, mid = `local-${Math.random().toString(36).slice(2, 9)}`) {

  const entry = aliceBubble(mid, tag);

  entry.md.innerHTML = md(text);
  entry.text = text;

  scrollDown();

  return entry;
}

/* ---------------- Composer ---------------- */

let dictating = false;

export function initComposer() {

  const form = document.getElementById("composer");
  const input = document.getElementById("input");
  const picker = document.getElementById("mode-picker");
  const mic = document.getElementById("btn-mic");

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submit();
  });

  input.addEventListener("keydown", (e) => {

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });

  input.addEventListener("focus", () => form.classList.add("focus"));
  input.addEventListener("blur", () => form.classList.remove("focus"));

  input.addEventListener("input", () => {

    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
  });

  picker.addEventListener("click", (e) => {

    const button = e.target.closest("button[data-mode]");

    if (!button) return;

    picker.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === button));

    state.mode = button.dataset.mode;
  });

  if (!canListen()) mic.classList.add("hidden");

  mic.addEventListener("click", () => {

    if (dictating) {

      stopListening();
      dictating = false;
      mic.classList.remove("listening");

      return;
    }

    const started = startListening((text, final) => {

      input.value = text;

      if (final) {

        dictating = false;
        mic.classList.remove("listening");

        submit();
      }
    });

    if (started) {
      dictating = true;
      mic.classList.add("listening");
    }
  });

  document.querySelectorAll(".q-chip").forEach((chip) => {

    chip.addEventListener("click", () => {

      input.value = chip.dataset.q;
      submit();
    });
  });
}

export function submitText(text) {

  text = (text || "").trim();

  if (!text) return;

  addUserMessage(text);

  sfx.send();

  const mission = state.mode === "mission" || (state.mode === "auto" && /^(mission|task)\s*:/i.test(text));

  if (mission) aliceState("working");
  else {
    showTyping();
    aliceState("thinking");
  }

  send({ type: "user.message", text, mode: state.mode });
}

function submit() {

  const input = document.getElementById("input");
  const text = input.value.trim();

  if (!text) return;

  input.value = "";
  input.style.height = "auto";

  submitText(text);
}

export { scrollDown };
