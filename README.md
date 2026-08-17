# ALICE

**A**rtificial **L**earning **I**ntelligent **C**ognitive **E**ngine — a modular
personal AI assistant in Python.

ALICE routes each message to exactly one module: memory, a plugin, or the AI.
Every module has a single responsibility and returns a standard `Response`.

---

## Quick Start

```bash
git clone https://github.com/piyush4670/alice.git
cd alice

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # then add your API key
python main.py
```

ALICE runs without an API key — memory, calculator, time, reminders, notes and
to-dos all work offline. Only open-ended conversation needs a key.

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
| anything else | answered by the AI |

Greetings and polite wrappers are understood, so
`hey can you calculate 5+5` reaches the calculator.

---

## Architecture

```
User
 |
 v
main.py          reads input, prints output. No business logic.
 |
 v
core/router.py   routes. Never executes.
 |
 v
core/decision.py decides. Never acts.
 |
 +-------------+-------------+
 v             v             v
memory/      plugins/       ai/
```

**Dependency rule:** `main` -> `core` -> `ai` / `memory` / `plugins`.
Never reversed, never circular. Plugins never import other plugins.

| Directory | Responsibility |
|---|---|
| `core/` | routing, decisions, config, personality, context, Response |
| `ai/` | prompt building, reasoning, intent extraction, model calls |
| `memory/` | persistent user facts |
| `plugins/` | calculator, time, reminders, notes, to-dos |
| `responses/` | shared reply builders |
| `utils/` | safe arithmetic, shared JSON storage |
| `tests/` | the regression suite |

Configuration lives in **one** place: `core/config.py`. Nothing re-declares it.

---

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest              # 168 tests, well under a second
```

To enable CI, copy the ready-made workflow into place:

```bash
mkdir -p .github/workflows
cp docs/ci-workflow.yml .github/workflows/tests.yml
```

Tests run offline and never touch your real data — every store is redirected
to a temporary directory.

### Adding a plugin

1. Write the parser in `ai/<name>_extractor.py`, returning a dict with an
   `intent` key or `None`.
2. Register it in `ai/extractor.py`.
3. Write `plugins/<name>.py` with a `handle(message, intent=None)` that
   returns a `Response`.
4. Add the intent prefix to `INTENT_PREFIXES` in `core/decision.py` and a
   branch in `core/router.py`.
5. Add tests.

Storage helpers are in `utils/store.py` — don't re-implement JSON I/O.

### Rules

See `docs/RULES.md`. The short version: one module, one responsibility;
the router routes; the decision engine decides; modules execute; AI assists.

---

## Documentation

| File | Contents |
|---|---|
| `docs/ARCHITECTURE.md` | the architectural constitution |
| `docs/PROJECT_STATE.md` | current capabilities and status |
| `docs/ROADMAP.md` | completed and planned sprints |
| `docs/RULES.md` | development rules |
| `docs/ANALYSIS.md` | codebase audit |
| `docs/SESSION.md` | session log |

---

## Security

User input never reaches `eval()`. Arithmetic is evaluated by an AST walker
(`utils/safe_math.py`) that accepts only numeric literals and the documented
operators, with guards against oversized exponents. See
`tests/test_safe_math.py`.
