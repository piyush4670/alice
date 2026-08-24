/* Central observable store. One source of truth for the UI. */

const listeners = new Set();

export const state = {
  link: "connecting",   // connecting | online | offline
  aliceState: "boot",   // idle | thinking | speaking | listening | working | waiting
  identity: null,
  brain: { mode: "local", label: "offline core" },
  telemetry: {},
  memory: {},
  user: "Boss",
  tasks: [],            // snapshots, newest first
  activeTask: null,     // id of a running mission (routing)
  focusTask: null,      // id of the mission shown in the panel (may be closed)
  mode: "auto",         // composer mode
  speak: false,
  sound: true,
  booted: false,
  greeted: false,
};

export function set(patch) {

  Object.assign(state, patch);

  for (const fn of listeners) {
    try { fn(state, patch); } catch (err) { console.error("[alice] listener", err); }
  }
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function aliceState(next) {

  if (state.aliceState === next) return;

  set({ aliceState: next });
}

const FINAL_STATES = ["done", "failed", "cancelled"];

export function upsertTask(snapshot) {

  const tasks = [...state.tasks];
  const index = tasks.findIndex((t) => t.id === snapshot.id);

  if (index >= 0) tasks[index] = snapshot;
  else tasks.unshift(snapshot);

  const active = tasks.find((t) => !FINAL_STATES.includes(t.status)) || null;

  // The panel keeps showing the latest mission after it closes, so the
  // user always sees how things ended.
  const stillThere = (id) => tasks.some((t) => t.id === id);

  const focus = (active && active.id)
    || (state.focusTask && stillThere(state.focusTask) && state.focusTask)
    || (tasks[0] ? tasks[0].id : null);

  set({ tasks, activeTask: active ? active.id : null, focusTask: focus });

  return snapshot;
}

export function activeTaskSnapshot() {
  return state.tasks.find((t) => t.id === state.activeTask) || null;
}

export function focusTaskSnapshot() {
  return state.tasks.find((t) => t.id === state.focusTask) || null;
}
