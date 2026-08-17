# ALICE — Codebase Analysis

Date: 17 August 2026
Status: **All findings resolved in Sprint 11.** See `docs/SESSION.md`.
Scope: full repository (2,020 lines of Python across 34 files, 6 documents)
Method: static reading + empirical execution of every module with stubbed
`requests` / `dotenv` dependencies. Every issue below was reproduced, not inferred.

---

## 1. Executive Summary

ALICE is a rule-based personal assistant with an AI fallback. The architecture it
documents — `main → router → decision → module → Response` — is genuinely
implemented and genuinely clean. Module boundaries are respected, the dependency
direction is never violated, and there are no circular imports.

The problem is not the architecture. It is that **the routing layer is built on
substring matching**, which fails on ordinary English, and that **the code has never
been executed against adversarial or even mildly unusual input**. There are no tests,
no dependency manifest, and no README.

Health assessment (contrast with `PROJECT_STATE.md`, which self-reports 🟢 across the board):

| Area | Documented | Actual | Note |
|---|---|---|---|
| Architecture | 🟢 Stable | 🟢 Stable | Accurate. Real strength. |
| Code quality | 🟢 Excellent | 🟠 Mixed | Clean style, but critical logic defects. |
| Security | — | 🔴 Critical | `eval()` sandbox escape, reachable from user input. |
| Correctness | 🟢 On track | 🔴 Broken | Router misroutes common phrases; first-run crash. |
| Testing | ✅ "No regressions" | 🔴 None | Zero test files exist. Testing was manual only. |
| Docs | 🟢 Up-to-date | 🟠 Drifted | Describes modules that are empty or misdescribed. |

**Four issues should be fixed before any new feature work** (P0/P1 below). Sprint 11
should be a hardening sprint, not "Phase 3 — Internet".

---

## 2. Critical Findings

### P0-1 — `eval()` sandbox escape in the calculator 🔴

`plugins/calculator.py:11` evaluates user input with `eval(expression, {"__builtins__": {}}, {})`.
Blanking `__builtins__` is a well-known non-defence: the object graph is still reachable.

Reproduced:

```
Input:  calculate (1).__class__.__mro__[1].__subclasses__()
Output: The result is [<class 'type'>, <class 'async_generator'>, ... ]
```

From `__subclasses__()` an attacker walks to `os` and reaches arbitrary code execution.
Today the input is a local human, so real-world exposure is low — but `ROADMAP.md`
Phase 8 plans Discord, Telegram and a web interface. The moment any of those ships,
this becomes remote code execution on the host.

Compounding it, the same line is a denial-of-service:

```
Input:  calculate 9**9**9
Result: process still burning CPU after 8s; never returns. Assistant is dead.
```

**Fix:** replace `eval` with an AST-walking evaluator that whitelists
`ast.Expression / BinOp / UnaryOp / Constant` and the six documented operators,
rejecting every other node type. Cap operand magnitude before evaluating `**`.
~35 lines, no dependencies, fully unit-testable.

### P0-2 — Crash on first run 🔴

`memory/storage.py:23` opens `data/profile.json` for writing without creating the
parent directory. `data/` is gitignored, so it does not exist in a fresh clone.

Reproduced — the very first thing a new user does:

```
You: my name is Piyush
FileNotFoundError: [Errno 2] No such file or directory: 'data/profile.json'
```

The traceback escapes `main()` and kills the process. Note that
`plugins/reminder.py:26`, `notes.py:26` and `todo.py:26` all correctly call
`mkdir(parents=True, exist_ok=True)` — the memory module is the one that was missed.
`main.py` also has no `try/except` around the loop, so any unhandled exception
terminates the session and loses the conversation.

**Fix:** add `MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)` in `save_memory`;
wrap the `main()` loop to catch `KeyboardInterrupt`/`EOFError` cleanly and log
unexpected exceptions without exiting.

### P1-3 — The time-keyword rule hijacks the router 🔴

`core/decision.py:56` routes to the time plugin if `"time"`, `"date"` or `"today"`
appears **anywhere** in the message as a substring. It is checked *before* reminders,
notes, todos and AI. Every one of these is broken today:

| User says | Routes to | Should be |
|---|---|---|
| `remind me to call mom at 5 pm today` | `time` | `reminder` |
| `note that the meeting is today` | `time` | `notes` |
| `add task finish the report on time` | `time` | `todo` |
| `what's the best time to visit Japan` | `time` | `ai` |
| `what is my birth date` | `time` | `memory_recall` |

The last row is especially bad: `"date"` is a substring of… nothing here, but
`"birth date"` contains `date`, so a memory recall is answered with today's calendar
date. Substring matching also means `update` contains `date`, and `sometimes`
contains `time`.

**Fix:** match on word boundaries (`re.search(r"\bwhat time\b|\bthe time\b|...")`)
and move the time check *below* the extractor dispatch, so specific structured
intents win over a generic keyword. Also consider having each plugin expose its own
`matches(message)` predicate so `decide()` stops accumulating special cases.

### P1-4 — Greeting detection swallows the rest of the sentence 🟠

`core/decision.py:40` returns `"greeting"` whenever the **first word** is hi/hello/hey,
discarding everything after it.

```
hey can you calculate 5+5   -> greeting   (expected: calculator)
hello what is my name       -> greeting   (expected: memory_recall)
```

`hi, remind me to call mom at 5` escapes only because the comma makes the first token
`hi,`, which is not in the set — an accident, not a design.

**Fix:** only treat a message as a pure greeting when it is *just* a greeting
(≤ 3 tokens, no other detected intent); otherwise strip the greeting prefix and
re-run the decision on the remainder.

---

## 3. Correctness Defects

### 3-5 — `Response.message` is populated with a `list` 🟠

`plugins/reminder.py:59`, `notes.py:56`, `todo.py:63` — all three `list_all()`
functions pass the raw list as the `message` field:

```python
return success(reminders, source="reminder", data=reminders)
```

`core/models.py` types `message: str`. Verified: `list_all().message` is `[]`, a list.
Today `main.py` never prints these directly (`handle()` reformats into `data`), so it
is latent — but the moment any caller prints `list_all().message`, the user sees
`[{'task': 'call mom', 'time': None}]`. The dataclass has no runtime validation to
catch it.

**Fix:** `list_all()` should return the formatted string in `message` and the list in
`data` — the split the Response model already provides. The formatting loop currently
inside `handle()` should move into `list_all()`, removing the duplication.

### 3-6 — Reminder time parsing mangles tasks 🟠

`ai/reminder_extractor.py:13-18` — the patterns are ordered such that the greedy
`at`/`on` split fires on the wrong occurrence, and the `tomorrow` variant is listed
third so it never gets a chance when an `at` clause is present:

| Input | Parsed task | Parsed time | Correct? |
|---|---|---|---|
| `remind me to call mom tomorrow` | `call mom` | `None` | ✗ loses "tomorrow" |
| `remind me to call mom tomorrow at 5pm` | `call mom tomorrow` | `5pm` | ✗ "tomorrow" stuck in task |
| `remind me to look at the report at 5pm` | `look` | `the report at 5pm` | ✗ badly wrong |

The `look at the report` case splits on the *first* `at`, destroying both fields.

**Fix:** anchor the time clause to the *end* of the string (`(.+?)\s+(?:at|on)\s+(\S+(?:\s*[ap]m)?)$`),
try the most specific pattern first, and treat bare `tomorrow`/`tonight`/`today` as a
time value rather than discarding it.

### 3-7 — Memory extractor captures conversation as facts 🟠

`ai/memory_extractor.py:65` matches the bare pattern `^my (.+?) is (.+)$` before
anything else, so ordinary chat is silently written to the user's permanent profile:

```
"my biggest problem right now is that python is hard"
   -> remember key="biggest problem right now" value="that python is hard"
"my question is why is the sky blue"
   -> remember key="question" value="why is the sky blue"
"my code is not working"
   -> remember key="code" value="not working"
```

The user asked a question and got "Got it, Boss. I'll remember your question. 💙"
instead of an answer. The profile fills with garbage keys, and that garbage is then
injected into every subsequent AI prompt, degrading all future responses.

The `I am ...` branch (line 85) has the same problem with a partial guard: it excludes
eleven `TEMPORARY_PREFIXES`, so `I am planning a trip` is correctly skipped, but
`I am tired` is stored permanently as `about me = tired`.

**Fix:** whitelist storable keys instead of blacklisting phrasings. Keep the generic
pattern but require the key to be short (≤ 3 words), free of question words, and the
value to be a noun-ish phrase — or require explicit intent (`remember that my X is Y`).
Store an `updated_at` timestamp so stale facts can be aged out later.

### 3-8 — Reasoning reports the current message as the previous topic 🟠

`main.py:27` appends the user message to context *before* calling `route()`.
`ai/reasoning.py:72 detect_topic()` then scans history backwards for the most recent
user message — which is now the message being processed.

Verified: for input `explain quantum computing` on a fresh session,
`topic` and `active_subject` both come back as `explain quantum computing`.
The prompt therefore tells the model "the previous topic is X" about the message it
is currently answering, and X appears **4 times in a single prompt** (history, topic,
active_subject, current message). This wastes tokens and actively misleads the model
on follow-ups.

**Fix:** either add the user message to context *after* routing, or have
`detect_topic`/`detect_active_subject` skip the final entry when it equals the
current message.

### 3-9 — Raw Python `repr` is injected into the prompt 🟠

`ai/prompts.py:80,83` interpolates the memory `dict` and history `list` directly:

```
Known Information:
{'name': 'Piyush', 'favourite colour': 'blue'}

Conversation History:
[{'role': 'user', 'message': 'hi'}, {'role': 'assistant', 'message': '...'}]
```

The model receives Python syntax rather than prose. It mostly copes, but it is
needless noise, and any apostrophe in stored text produces confusing escaping.
There is also no truncation: at `MAX_HISTORY = 20` plus an unbounded profile, the
prompt grows without limit and will eventually exceed the context window.

**Fix:** render memory as `- key: value` lines and history as `User: ... / ALICE: ...`
turns; cap both by character budget.

### 3-10 — Every message is parsed twice 🟡

`core/decision.py:85` calls `extract(message)` to decide the destination, then
`memory/manager.py:60`, `plugins/reminder.py:88`, `notes.py:85` and `todo.py:118`
each call `extract(message)` again to get the payload. Confirmed by instrumenting
the call: two full passes over all four extractors per message.

Cheap today (regex on one string), but it violates RULES.md Rule 2 ("never duplicate
logic") and creates a real hazard: `decide()` and `handle()` can disagree if an
extractor is ever made non-deterministic or stateful. `handle()` also has to re-handle
the `None` case that `decide()` already ruled out — dead branches in four files.

**Fix:** have `decide()` return the extracted intent object alongside the destination
and let the router pass it to `handle(message, intent)`.

---

## 4. Architecture & Maintainability

### 4-11 — `core/config.py` is written but never read 🟡

Only `ai/chat.py` imports from it (`API_KEY`, `MODEL`, `BASE_URL`). Everything else
was re-declared locally:

| Config value | Duplicated at | Consequence |
|---|---|---|
| `MEMORY_FILE = "data/profile.json"` | `memory/storage.py:5` | changing config does nothing |
| `MAX_HISTORY = 20` | `core/context.py:3` | changing config does nothing |
| `USER_TITLE = "Boss"` | `core/personality.py:3` | changing config does nothing |
| `ASSISTANT_NAME = "ALICE"` | `ai/prompts.py` (hardcoded in text) | changing config does nothing |

Editing `config.py` to rename the assistant or lengthen history silently has zero
effect. This is exactly the "no hardcoded behaviour" rule the blueprint sets out.

**Fix:** make the modules import from `core.config`, and delete the duplicates.

### 4-12 — Half of `core/personality.py` is dead 🟡

`MEMORY_CONFIRM`, `MEMORY_RECALL`, `MEMORY_UNKNOWN`, `CALCULATOR_REPLY`,
`TIME_REPLY`, `DATE_REPLY`, `AI_UNAVAILABLE`, `SIGNATURE`, `VOICE_STYLE`,
`PERSONALITY` — grepped across the whole repo: **zero references** outside their own
file. The templates exist; the modules hardcode the same strings instead:

- `memory/manager.py:77` hardcodes `"Got it, {boss}. I'll remember your {key}. 💙"`
  while `MEMORY_CONFIRM` sits unused two files away.
- `plugins/calculator.py:18` hardcodes the result string; `CALCULATOR_REPLY` unused.
- `plugins/time.py:11,21` hardcode both; `TIME_REPLY`/`DATE_REPLY` unused.
- `ai/chat.py:63` hardcodes the failure message; `AI_UNAVAILABLE` unused.

The centralised personality system that ARCHITECTURE.md calls a "frozen decision" is
not actually wired up. Changing ALICE's tone requires editing five plugin files.

**Fix:** use the templates. This also removes the 💙 emoji duplication.

### 4-13 — Five empty modules and a documentation-reality gap 🟡

`responses/ai.py`, `casual.py`, `errors.py`, `memory.py`, `system.py` are all 0 bytes.
`responses/greetings.py` is the only real file in that package. Meanwhile
`ARCHITECTURE.md` lists them as responsibilities and describes:

- `ai/reasoning.py` as "Reserved … no implementation until reasoning is required" —
  it is in fact 283 lines, the largest file in the project, and fully wired in.
- `memory/service.py` as a module — it does not exist.
- `plugins/reminder.py` as "Reserved" under Frozen Decisions — it is implemented.
- `ai/extractor.py` scope as "Remember / Recall … NOT a general intent detector" —
  it is now precisely a general intent dispatcher across four extractors.

`PROJECT_STATE.md` lists "To-do lists" under *Current Limitations* while
`ROADMAP.md` marks Sprint 10 complete and `plugins/todo.py` is 177 working lines.
The two documents contradict each other.

**Fix:** delete the empty placeholders (Git remembers them), and reconcile
ARCHITECTURE.md / PROJECT_STATE.md with what actually shipped. RULES.md already
mandates this — it was skipped for Sprint 10.

### 4-14 — No tests, no manifest, no README 🟠

- **No test suite.** `SESSION.md` claims "✅ No regressions were detected during
  testing" across 19 features; that was manual REPL testing. Every defect in this
  document would have been caught by a table-driven test over `decide()`.
  RULES.md Rule 10 requires each module be independently testable — they are (pure
  functions, good separation), the tests were simply never written. This is the
  single highest-leverage gap: the design is *already* test-friendly.
- **No `requirements.txt`.** `requests` and `python-dotenv` are imported but
  undeclared; a fresh clone fails with `ModuleNotFoundError` (reproduced).
- **No README.** No setup instructions, no `.env.example` documenting `API_KEY`.
- **No graceful missing-key path.** With `API_KEY` unset, every AI turn makes a real
  HTTP request that 401s and reports "My AI brain is temporarily unavailable" —
  correct behaviour, misleading message. Verified.

### 4-15 — Minor observations 🟢

- `core/decision.py:79` — the calculator's `allowed` charset omits `**`'s components
  incorrectly? No: `*` is present, so `**` works. But `^` and `//` are silently
  rejected, and `1/0` routes to the calculator and returns the generic
  "I couldn't calculate that" rather than "you can't divide by zero".
- `ai/reasoning.py:282` — `analyze()` returns a `"notes": []` key that is never read
  by `build_reasoning()` or anything else. Dead field.
- `responses/greetings.py:11,21,31` — all three functions take a `name` parameter and
  ignore it, calling `friend()` instead. Misleading signature; `main.py` and
  `router.py` both pass `name` through for nothing.
- `core/personality.py:20` — `PERSONAL_NAME` is module-level mutable global state set
  via `set_user()`. Works for one CLI user; breaks the instant a second session
  exists (the Discord/web plans in Phase 8).
- `main.py:35` — exit words are checked *after* routing, so `bye` produces a goodbye
  and then re-checks the same string. Harmless but redundant with
  `decision.py:52`, which already detects it.
- `memory/manager.py:15` — `remember()` returns `False` for an unchanged value, and
  `handle()` reports "I already know your X" — good, deliberate touch.
- Memory key normalisation (`ALIASES`) genuinely works: `My Favorite Color is blue`
  then `what is my favourite colour` round-trips correctly. Verified.

---

## 5. What Is Genuinely Good

Worth stating plainly, because it is the reason the fixes above are cheap:

- **The layering is real.** `main` → `core` → `ai`/`memory`/`plugins` is never
  violated. No circular imports. No plugin imports another plugin. The dependency
  rule in the blueprint is actually enforced in the code.
- **The Response object pays off.** Uniform `success`/`error`/`info` construction
  means the router needs no per-module error handling, and adding a plugin required
  touching exactly two core files.
- **Plugins are truly removable.** Deleting `todo.py` breaks two import lines and
  nothing else — the independence claim holds.
- **Functions are small and single-purpose.** `reasoning.py` is 283 lines of nine
  independent pure detectors; each is trivially testable.
- **Extractors are separated from executors.** `ai/*_extractor.py` parse, `plugins/*`
  act. That split is what makes the reminder-parsing fix a 10-line change in one file.
- **Failure paths exist.** Every file I/O is wrapped; corrupt JSON degrades to empty
  rather than crashing. (Save paths are the exception — see P0-2.)
- **The documentation habit is a real asset**, even where it has drifted. Most
  projects this size have none.

---

## 6. Recommended Order of Work

**Sprint 11 — Hardening (do this before Phase 3):**

1. P0-1 Replace `eval()` with an AST evaluator; add an operand-size guard. *(security)*
2. P0-2 `mkdir` in `save_memory`; wrap the `main()` loop. *(first-run crash)*
3. P1-3 Word-boundary time matching, moved below extractor dispatch. *(routing)*
4. P1-4 Greeting prefix stripping. *(routing)*
5. Add `tests/` with a table-driven `decide()` suite covering every row in §2 and §3,
   plus extractor unit tests. Target the pure functions first — they need no mocks.
6. Add `requirements.txt`, `README.md`, `.env.example`.

**Sprint 12 — Consistency:**

7. 3-5 `list_all()` returns formatted `message` + structured `data`.
8. 3-6 Reminder time-clause anchoring.
9. 3-7 Memory extraction whitelist.
10. 3-8 Fix the context/reasoning ordering; 3-9 render prompts as prose with a budget.
11. 4-11 / 4-12 Wire up `config.py` and the personality templates; delete duplicates.
12. 4-13 Delete empty modules; reconcile ARCHITECTURE.md and PROJECT_STATE.md.

**Then** Phase 3 — Internet. Note that web search will add a third caller to the
extractor chain and a second network dependency; the double-extraction issue (3-10)
and the missing prompt budget (3-9) are both worth resolving first.

---

## 7. Issue Index

All items were fixed in Sprint 11. Each has a regression test.

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| P0-1 | 🔴 Critical | `eval()` sandbox escape + DoS | ✅ `utils/safe_math.py` AST evaluator |
| P0-2 | 🔴 Critical | First-run `FileNotFoundError` | ✅ atomic writes with `mkdir` |
| P1-3 | 🔴 High | Time keywords hijack routing | ✅ word-boundary match, runs after intents |
| P1-4 | 🟠 Medium | Greeting swallows the sentence | ✅ prefix stripped, request routed |
| 3-5 | 🟠 Medium | `list` assigned to `message: str` | ✅ formatting in `list_all()`, list in `.data` |
| 3-6 | 🟠 Medium | Time clause mangles task text | ✅ end-anchored patterns, specific first |
| 3-7 | 🟠 Medium | Chat stored as permanent facts | ✅ `looks_like_fact` guard |
| 3-8 | 🟠 Medium | Current message read as prior topic | ✅ detectors skip the current message |
| 3-9 | 🟠 Medium | Python `repr` in prompt; no budget | ✅ prose rendering + char budgets |
| 3-10 | 🟡 Low | Every message extracted twice | ✅ `Decision` carries the parsed intent |
| 4-11 | 🟡 Low | Config duplicated, never read | ✅ `core/config.py` is the only source |
| 4-12 | 🟡 Low | 10 unused templates | ✅ templates wired up, duplicates removed |
| 4-13 | 🟡 Low | Empty modules; docs contradict code | ✅ deleted; docs reconciled |
| 4-14 | 🟠 Medium | No tests, no manifest, no README | ✅ 168 tests, requirements, README, CI |
