# ALICE Development Session

Version: 1.1

Last Updated: August 2026

Status: ALICE v1.1 Stable

---

# Sprint 11 — Hardening

This session fixed every defect recorded in `docs/ANALYSIS.md` and added
the project's first test suite. The architecture was not redesigned; all
changes were made within the existing structure.

---

## Security

### eval() removed

`plugins/calculator.py` evaluated user input with
`eval(expression, {"__builtins__": {}}, {})`. Blanking builtins is not a
sandbox — the object graph remains reachable:

```
calculate (1).__class__.__mro__[1].__subclasses__()
```

returned the full class list, from which `os` and arbitrary code execution
are a short walk. `calculate 9**9**9` hung the process indefinitely.

Replaced with `utils/safe_math.py`, an AST walker that accepts only
`Expression`, `BinOp`, `UnaryOp` and numeric `Constant` nodes. Exponent
magnitude is capped before evaluation. 25 security tests pin this.

---

## Reliability

### First-run crash

`memory/storage.py` wrote to `data/profile.json` without creating the
parent directory, and `data/` is gitignored. The first fact a new user
stated raised `FileNotFoundError` and killed the session.

Fixed with `mkdir(parents=True, exist_ok=True)`. All writes are now
atomic via a temp file plus `os.replace`, so an interrupted save cannot
truncate a file.

### The conversation loop survives failures

`main.py` now catches unexpected exceptions per message and returns a
recovery response instead of terminating. `Ctrl-C` and `Ctrl-D` exit
politely.

---

## Routing

### Time keywords no longer hijack the router

`decision.py` matched `time`, `date` and `today` as substrings, before
every structured intent. Four working subsystems were unreachable:

| Message | Was | Now |
|---|---|---|
| `remind me to call mom at 5 pm today` | time | reminder |
| `note that the meeting is today` | time | notes |
| `add task finish the report on time` | time | todo |
| `what is my birth date` | time | memory recall |
| `what's the best time to visit Japan` | time | ai |

Time matching is now anchored on word boundaries and runs *after* intent
extraction.

### Greeting prefixes no longer swallow requests

`hey can you calculate 5+5` returned a greeting. Greetings are now only
matched when the message is nothing but a greeting; otherwise the prefix
is stripped and the remainder routed. Polite wrappers (`can you`,
`please`) are stripped the same way.

---

## Correctness

### Reminder time parsing

The greedy `at` split destroyed both fields:

| Message | Was | Now |
|---|---|---|
| `remind me to look at the report at 5pm` | task=`look` time=`the report at 5pm` | task=`look at the report` time=`5pm` |
| `remind me to call mom tomorrow` | time=`None` | time=`tomorrow` |
| `remind me to call mom tomorrow at 5pm` | task=`call mom tomorrow` | task=`call mom` time=`tomorrow 5pm` |

Time clauses are now anchored to the end of the string and ordered most
specific first.

### Memory no longer stores conversation

The bare `^my (.+?) is (.+)$` pattern stored ordinary chat as permanent
facts — `my question is why is the sky blue` became a stored "question",
which then polluted every future AI prompt. Added a `looks_like_fact`
guard on key length, question words, non-fact keys and value shape, plus
an explicit `remember that my X is Y` form that always stores.

### Response.message is always a string

`list_all()` in all three list plugins assigned a raw Python list to
`message`, which `core/models.py` types as `str`. Formatting moved into
`list_all()`; the structured list goes in `.data`, as the Response model
intends. This also removed the duplicated formatting loops in `handle()`.

### Prompt construction

- Memory and history are rendered as prose, not Python `repr`.
- The current message was appearing four times in one prompt; it now
  appears once.
- `detect_topic` reported the message being answered as the previous
  topic; detectors now receive the current message and skip it.
- History and memory sections are capped by character budget.
- Removed the dead `notes` field from `analyze()`.

---

## Maintainability

- `core/config.py` is now the single source of truth. `MEMORY_FILE`,
  `MAX_HISTORY` and `USER_TITLE` were duplicated in three modules, so
  editing config had no effect. Paths are overridable via
  `ALICE_DATA_DIR`.
- The ten unused personality templates are now actually used; the
  hardcoded duplicates in five modules are gone.
- JSON list I/O was triplicated across reminders, notes and to-dos. It
  now lives in `utils/store.py`.
- `decide()` returns the parsed intent, so handlers no longer re-parse
  every message. Extraction runs once instead of twice.
- Deleted four empty placeholder modules in `responses/`.
- Missing API key now gives a clear, actionable message instead of a
  failed HTTP request.

---

## Project Infrastructure

Added:

- `tests/` — 168 tests, offline, under a second
- `requirements.txt` and `requirements-dev.txt`
- `README.md`
- `.env.example`
- `.github/workflows/tests.yml` — CI on Python 3.9, 3.11, 3.12
- `pytest.ini`

---

# Testing Summary

```bash
python -m pytest
168 passed
```

| Suite | Covers |
|---|---|
| `test_safe_math.py` | arithmetic, sandbox escapes, resource exhaustion |
| `test_decision.py` | every routing case, including all former misroutes |
| `test_extractors.py` | memory, reminder, note and to-do parsing |
| `test_storage_and_plugins.py` | persistence, lifecycles, the message/data contract |
| `test_prompts_and_reasoning.py` | prompt rendering, topic detection, budgets |
| `test_router.py` | end-to-end through `route()` |

Every defect in `docs/ANALYSIS.md` has a regression test.

---

# Architecture Status

Status:

🟢 Frozen — unchanged this sprint

Verified mechanically:

- `main` → `core` → `ai` / `memory` / `plugins`
- No plugin imports another plugin
- No module imports the router
- No circular imports

---

# Next Sprint

Phase 3 — Internet

Goal: web search and live information.

Before starting, note that a search extractor will join the extractor
chain, and that network calls should reuse the timeout and error handling
already in `ai/chat.py`.
