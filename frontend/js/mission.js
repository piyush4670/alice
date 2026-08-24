/* Mission control: live plan, steps, questions, artifacts, event feed. */

import { md } from "./md.js";
import { aliceState, set, upsertTask, activeTaskSnapshot, focusTaskSnapshot, state } from "./state.js";
import { send } from "./bus.js";
import { aliceSay, scrollDown } from "./chat.js";
import { speak } from "./voice.js";
import { sfx } from "./sound.js";

const STEP_ICON = {
  pending: "○",
  running: "",
  done: "✓",
  failed: "✕",
  skipped: "·",
};

const STATE_LABEL = {
  planning: "planning",
  working: "working",
  waiting_user: "needs you",
  done: "complete",
  failed: "failed",
  cancelled: "aborted",
};

let lastSnapshot = null;

function el(id) {
  return document.getElementById(id);
}

function renderMission(task) {

  const panel = el("panel-mission");

  const finished = task.steps.filter((s) => ["done", "failed", "skipped"].includes(s.status)).length;
  const percent = task.steps.length ? Math.round((100 * finished) / task.steps.length) : 0;

  panel.dataset.state = task.status;

  el("mission-idle").classList.add("hidden");
  el("mission-live").classList.remove("hidden");

  el("mission-state-text").textContent = STATE_LABEL[task.status] || task.status;
  el("mission-goal").textContent = task.goal;

  el("mission-progress").style.width = `${percent}%`;
  el("mission-step-count").textContent = `${finished} / ${task.steps.length} steps`;

  const minutes = Math.max(0, (Date.now() / 1000 - task.created_at) / 60);

  el("mission-elapsed").textContent =
    task.status === "done" || task.status === "cancelled" || task.status === "failed"
      ? `closed`
      : `${minutes < 1 ? "<1" : Math.round(minutes)} min`;

  el("btn-cancel").classList.toggle("hidden", ["done", "failed", "cancelled"].includes(task.status));

  /* steps */
  const stepsEl = el("mission-steps");

  stepsEl.innerHTML = "";

  for (const step of task.steps) {

    const node = document.createElement("div");
    node.className = `step ${step.status}`;

    node.innerHTML = `
      <div class="step-icon">${STEP_ICON[step.status] || ""}</div>
      <div class="step-body">
        <div class="step-title"></div>
        ${step.result ? '<div class="step-result"></div>' : ""}
      </div>`;

    node.querySelector(".step-title").textContent = step.title;

    if (step.result) node.querySelector(".step-result").textContent = step.result;

    stepsEl.appendChild(node);
  }

  /* question */
  const questionEl = el("mission-question");

  if (task.question && !task.question.answered) {

    questionEl.classList.remove("hidden");

    if (el("question-text").textContent !== task.question.text) {

      el("question-text").textContent = task.question.text;

      aliceSay(`⏸ ${task.question.text}`, "needs you", `q-${task.question.id}`);

      speak(task.question.text);

      sfx.question();

      scrollDown();
    }

    el("question-input").focus();
  }

  else {
    questionEl.classList.add("hidden");
  }

  /* artifacts */
  const artsEl = el("mission-artifacts");

  artsEl.innerHTML = "";

  for (const artifact of task.artifacts || []) {

    const chip = document.createElement("button");

    chip.className = "artifact-chip";
    chip.innerHTML = `<svg class="ic"><use href="#i-file"/></svg>`;
    chip.append(artifact.name);
    chip.title = "view artifact";

    chip.addEventListener("click", () => window.alice.openArtifact(artifact.name));

    artsEl.appendChild(chip);
  }
}

function renderIdle() {

  el("panel-mission").dataset.state = "idle";
  el("mission-idle").classList.remove("hidden");
  el("mission-live").classList.add("hidden");
}

export function refreshMission() {

  const task = focusTaskSnapshot();

  if (!task) {
    renderIdle();
    return;
  }

  const fingerprint = JSON.stringify(task);

  if (lastSnapshot === fingerprint) return;

  lastSnapshot = fingerprint;

  renderMission(task);
}

/* ---------------- Event feed ---------------- */

const LEVEL_LABEL = {
  info: "info",
  good: " ok ",
  warn: "warn",
  tool: "tool",
  thought: "thnk",
  step: "step",
};

function addLog(level, text, at) {

  const log = el("log");

  const empty = log.querySelector(".empty");

  if (empty) empty.remove();

  const line = document.createElement("div");

  line.className = `log-line ${level}`;

  const time = new Date((at || Date.now() / 1000) * 1000).toLocaleTimeString([], { hour12: false });

  const label = LEVEL_LABEL[level] || level;

  line.innerHTML = `<span class="t">${time}</span><span class="k">${label}</span><span class="tx"></span>`;
  line.querySelector(".tx").textContent = String(text).slice(0, 220);

  log.appendChild(line);

  while (log.children.length > 160) log.firstChild.remove();

  log.scrollTop = log.scrollHeight;
}

/* ---------------- Socket handlers ---------------- */

export function initMissionHandlers() {

  const questionForm = el("question-form");

  questionForm.addEventListener("submit", (e) => {

    e.preventDefault();

    const input = el("question-input");
    const text = input.value.trim();

    if (!text || !state.activeTask) return;

    send({ type: "task.reply", task_id: state.activeTask, text });

    input.value = "";

    aliceSay(text, "you", `u-${Date.now()}`);
  });

  el("btn-cancel").addEventListener("click", () => {

    if (state.activeTask) send({ type: "task.cancel", task_id: state.activeTask });
  });
}

export function onTaskSnapshot(event) {

  upsertTask(event.task);

  refreshMission();

  if (event.task.status === "working" && state.aliceState !== "speaking") aliceState("working");
}

export function onTaskState(event) {

  const task = state.tasks.find((t) => t.id === event.task_id) || activeTaskSnapshot();

  if (task) {

    task.status = event.state;

    upsertTask(task);
  }

  refreshMission();

  if (event.state === "planning") aliceState("thinking");

  if (event.state === "working") aliceState("working");

  if (event.state === "waiting_user") aliceState("waiting");

  if (["done", "failed", "cancelled"].includes(event.state)) {

    aliceState("idle");

    if (event.state === "done") sfx.complete();
  }
}

export function onTaskLog(event) {

  addLog(event.level, event.text, event.at);

  if (event.level === "step") sfx.step();
}

export function onTaskDelta(event) {

  const entry = aliceSay(event.text, "mission", event.mid);

  speak(event.text);

  scrollDown();
}

export function onTaskQuestion(event) {

  const task = activeTaskSnapshot();

  if (task) {

    task.question = event.question;
    task.status = "waiting_user";

    upsertTask(task);
    refreshMission();
  }
}

export function onTaskArtifact() {

  /* artifacts arrive inside snapshots; just refresh */
}
