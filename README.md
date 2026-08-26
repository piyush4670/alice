# ALICE

**A**rtificial **L**earning **I**ntelligent **C**ognitive **E**ngine — a modular
personal AI assistant with a futuristic mission-control UI, a proper backend,
and an agent that stays on a task until it is actually finished.

ALICE routes each message to exactly one module: memory, a plugin, or the AI.
Every module has a single responsibility and returns a standard `Response`.

---

## Quick Start

### Web UI (recommended)

```bash
git clone https://github.com/piyush4670/alice.git
cd alice

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # optional: add an API key for the full brain
python -m server
```

Open **http://localhost:8000** — passcode gate, boot sequence, mission control,
wake word, the embedded web deck and voice, all in your browser.

### Installable app (PWA)

ALICE registers a service worker and ships a web manifest, so you can add her
to your home screen and launch her like a native app. On mobile browsers:

- Open the site, then **Add to Home Screen / Install app**.
- Grant microphone permission when you turn on **hands-free** (the ear icon)
  so she can hear _"Hey Alice"_.
- Grant notification permission (the bell icon) for reminder and
  mission-complete pings.

### Terminal (the classic interface)

```bash
python main.py
```

---

## Two brains, one Alice

| Brain | When | What it can do |
|---|---|---|
| **Linked** | `API_KEY` set in `.env` | Full reasoning: multi-step missions, tool planning, reflection, open conversation, research |
| **Local** | no key (default) | Deterministic planning + all tools: reminders, notes, to-dos, memory, maths, time, Wikipedia, web search, artifacts |

The linked brain works with any OpenAI-compatible endpoint (Groq by default).
If it ever drops mid-mission, Alice falls back to the local core and finishes
what she can — she never goes dark.

---

## Missions: not one reply — a finished task

Ask for something small and Alice answers in chat. Give her a **mission** and
she plans, executes, observes, reflects and keeps working until the goal is
done — asking you questions along the way when a decision belongs to you.

```
mission: research the Voyager probes and write me a short summary file
mission: plan my weekend, add the tasks and set a reminder for Saturday
mission: calculate our burn rate and save the result to a report
```

What happens next, live in the UI:

1. **Plan** — the goal becomes 2–6 concrete, checkable steps.
2. **Act** — each step runs with real tools (21 of them): web search,
   Wikipedia, calculator, clock, reminders, notes, to-dos, memory, workspace
   artifacts, the embedded browser and notifications.
3. **Observe** — every tool result feeds back into her reasoning.
4. **Reflect** — after each step she decides: continue, revise the plan,
   ask you, or finish.
5. **Report** — a clear summary, artifacts listed by name.

Some tool calls create **live side-effects**, not just text: opening a site
slides up the embedded web deck, finishing a long task raises a browser
notification, and reminders ring in real time.

Anything that looks like a big request can also start a mission automatically
("research…", "plan…", "write… and then…"), or you can force it with the
**mission** toggle in the composer.

---

## The interface

- **Access gate** — ALICE opens on a passcode screen; nothing runs until you
  unlock her.
- **Alice Core** — a living orb: it breathes when idle, spins while thinking,
  ripples when she speaks, and orbits nodes while a mission runs.
- **Voice wave** — a live audio visualiser that reacts to your microphone in
  real time while she listens and to her broadcast envelope while she speaks.
- **Mission Control** — goal, live step checklist, progress, artifacts and the
  raw event feed, second by second.
- **Web Deck** — an embedded browser so Alice can open YouTube, Wikipedia,
  Google and more right inside the interface (proxied server-side, with an
  escape hatch to open a site in a new tab).
- **Voice** — she reads her replies (toggle in the top bar), the mic button
  takes dictation, and a hands-free **wake word** lets you say _"Hey Alice"_
  at any moment to interrupt her and give a new instruction.
- **Memory & telemetry** — what Alice knows about you and the state of the
  machine she runs on, always visible.
- **Boot sequence** — because it should feel like waking something up.

The design language is deliberate: deep ice, calm light, quiet precision.
Every capability you'd want from a cinematic AI assistant — presence, memory,
voice, telemetry, relentless task execution — in Alice's own voice, not
anyone else's.

---

## What ALICE Can Do

| Say this | ALICE does |
|---|---|
| `my name is Piyush` | stores a fact |
| `what is my name` | recalls it |
| `forget my name` | deletes it |
| `what do you know about me` | lists everything stored |
| `what is 2+2` / `calculate (3+4)*2` | arithmetic |
| `what is the time` / `what is the date` | clock and calendar |
| `remind me to call mom tomorrow at 5pm` | adds a reminder |
| `show my reminders` / `delete reminder 1` | manages reminders |
| `note that the sky is blue` | adds a note |
| `show my notes` / `delete note 1` | manages notes |
| `add task write the report` | adds a to-do |
| `show my tasks` / `complete task 1` | manages to-dos |
| `open arxiv.org` / `open youtube` | opens it in the embedded web deck |
| `notify me when it's done` | posts a browser notification |
| `mission: …` (or any big request) | plans and works it to completion |
| anything else | answered by the AI |

Say **_"Hey Alice"_** at any time to interrupt her mid-sentence and give a
fresh instruction — hands-free, no button press.

Greetings and polite wrappers are understood, so
`hey can you calculate 5+5` reaches the calculator.

---

## Architecture

```
main.py                 CLI entry point — no business logic
server/                 FastAPI backend: WebSocket protocol, REST, static UI
  app.py                assembly only
  bus.py                thread-safe event bus (engine threads → sockets)
  websocket.py          the live protocol
  routes.py             /api: system, tasks, memory, board, artifacts
  runtime.py            singletons (bus + orchestrator)
agent/                  the mission engine
  engine.py             plan → act → observe → reflect → ask → finish
  orchestrator.py       mission threads, questions, cancellation
  brain.py              the brain contract
  llm_brain.py          linked brain (OpenAI-compatible, JSON-bounded)
  local_brain.py        offline core (deterministic planning, all tools)
  conversation.py       chat traffic reusing the classic router
  triage.py             chat vs mission
  prompts.py            mission prompts (one identity, one voice)
tools/                  21 tools behind one registry (+ browser, notifications)
  integrations.py        open_website (web deck) + notify
memory/ plugins/ core/  unchanged, shared by CLI and web
utils/                  safe_math, timeparse (reminder time resolution)
frontend/               vanilla HTML/CSS/JS — no build step, PWA-ready
  startup.js            passcode gate + cinematic boot
  voice.js              speak, dictation, and "Hey Alice" wake word engine
  audio.js              live voice/speech visualiser
  webdock.js            embedded browser (server-side proxied)
  notify.js             permission-aware browser notifications
  manifest.webmanifest  installable web app manifest
  service-worker.js     offline shell cache + static assets
```

Run the tests:

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Configuration

Everything lives in `.env` (see `.env.example`): the API key and model, the
port, and the agent's safety limits (max steps per mission, rounds per step,
how long Alice waits for your answer before proceeding with her best
judgement).
