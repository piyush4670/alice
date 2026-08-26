# ALICE Web Architecture (v2)

Version: 2.0
Status: Shipped

---

# Mission

Alice v1 answered messages. Alice v2 finishes tasks.

The web layer adds three things without touching the v1 core:

1. A **mission engine** that plans, acts, observes and reflects until a
   goal is genuinely complete — collaborating with the user mid-mission.
2. A **proper backend**: FastAPI + WebSockets, every state change streamed.
3. A **mission-control UI**: futuristic, hi-tech, unmistakably Alice.

---

# Core philosophy (unchanged)

1. One module = One responsibility.
2. The router decides. Modules execute.
3. AI assists. It never controls.
4. Documentation is the source of truth.

New rules added by v2:

5. Brains decide. Tools act. The engine sequences.
6. A broken brain is an observation, never a crash.
7. The UI is a view of the event bus — it holds no truth of its own.

---

# The mission loop

```
plan → [ act → observe → (ask user)? ] × steps → reflect → report
              ↑______________________ replan ______________________|
```

- **plan**: goal → 2–6 concrete steps (or a deterministic local plan).
- **act**: the brain picks exactly one action per round — a tool call, a
  reply, a question, or a final answer.
- **observe**: tool results feed straight back into the next round.
- **ask user**: the engine parks the mission (status `waiting_user`),
  emits `task.question`, and blocks on a threading.Event until the user
  answers or `AGENT_ASK_TIMEOUT` expires — then proceeds with best
  judgement.
- **reflect**: after each step — continue / replan / ask_user / complete.
- **report**: final summary; artifacts listed by name.

Safety rails: `AGENT_MAX_STEPS` per mission, `AGENT_ROUNDS_PER_STEP` per
step, graceful cancellation between every round.

---

# Two brains, one contract

`agent/brain.py` defines the contract: `plan`, `act`, `reflect`,
`summarize`, `converse`.

- **LinkedBrain** — any OpenAI-compatible endpoint (Groq default).
  JSON-bounded replies with fence-stripping repair. Any failure raises
  `BrainUnavailable`.
- **LocalBrain** — deterministic classifier + fragment planner that runs
  the same tool registry. No key required. Wikipedia and web search still
  work when the network allows.

The engine holds whichever brain it started with; if a linked call dies
mid-mission the engine swaps in a LocalBrain for the rest of that mission
and says so in the event feed. Alice degrades; she never goes dark.

---

# Event protocol (server → client)

| Event | Meaning |
|---|---|
| `hello` | identity, brain, telemetry, memory, recent tasks |
| `chat.delta` / `chat.done` | streamed conversational replies |
| `task.snapshot` | full task state (id, goal, steps, artifacts) |
| `task.state` | planning / working / waiting_user / done / failed / cancelled |
| `task.log` | levelled feed: step / tool / thought / info / good / warn |
| `task.delta` / `task.message_done` | Alice narrating the mission |
| `task.question` | the mission needs the user |
| `task.artifact` | a file landed in the workspace |
| `web.open` | ALICE opened a site — the embedded web deck should slide up |
| `system.notify` | ALICE raised a browser notification |
| `reminder.fire` | a reminder came due (ring it, post a notification) |
| `memory.updated` | the memory lattice changed |
| `system.telemetry` | heartbeat (load, memory, disk) |

Client → server: `user.message` (mode auto/chat/mission), `task.reply`,
`task.cancel`, `user.name`, `ping`.

---

# Threading model

- Mission engines run in daemon threads (one per mission).
- Chat replies run in a worker thread so sockets never block.
- All events flow through `server/bus.py`: `loop.call_soon_threadsafe`
  into bounded per-client queues. A slow client sheds its oldest events;
  it never blocks a mission.

---

# Frontend

Vanilla HTML/CSS/JS, no build step, one WebSocket. Modules mirror the
backend's single-responsibility rule:

```
state.js    one observable store
bus.js      socket + reconnect
core.js     the Alice Core orb (canvas)
audio.js    live voice/speech visualiser (canvas)
chat.js     stream + composer
mission.js  mission control panel + event feed
panels.js   memory / telemetry / artifacts
voice.js    speech synthesis + dictation + "Hey Alice" wake word engine
webdock.js  embedded browser, driven by the web deck
notify.js   permission-aware browser notifications
startup.js  passcode gate + cinematic boot sequence
sound.js    quiet WebAudio chimes
md.js       minimal safe markdown
level.js    shared live mic-level bucket
main.js     boot sequence + wiring
```

# Installable app (PWA)

- `manifest.webmanifest` — name/theme/icons/start_url/shortcuts.
- `service-worker.js` — caches the static shell (cache-first for assets,
  network-first for navigations), never caches `/api`, `/ws` or `/web`
  (live data and the proxy must always hit the server).

# Embedded web deck

Sites can't be framed (X-Frame-Options / CSP). `server/webproxy.py`
re-serves a page from ALICE's own origin, strictly https/http, blocking
private/loopback hosts (SSRF), stripping frame-busting headers and
re-anchoring relative links via a `<base>` tag. If the proxy can't load a
site the frontend shows a fallback with an "open in new tab" escape hatch.

Design language: deep ice. Calm, crystalline, precise — every cinematic-
assistant capability, in Alice's own voice.
