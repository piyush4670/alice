# ALICE v1.1 - Architecture Constitution

Version: 1.2
Status: Active

---

# Vision

ALICE is a modular AI assistant designed to be intelligent, scalable, maintainable, and easy to extend.

Every module has a single responsibility.

No module should perform the work of another module.

---

# Engineering Principles

1. Simplicity over complexity.
2. One module = One responsibility.
3. The Core controls the application.
4. AI is a service, never the controller.
5. Every feature must be independently testable.
6. Prefer extension over modification.
7. Documentation is the source of truth.
8. Architecture changes require deliberate review.

---

# Current Project Structure

alice/

main.py

core/
- router.py
- decision.py
- response.py
- context.py
- personality.py
- config.py
- models.py

ai/
- chat.py
- prompts.py
- extractor.py
- reasoning.py
- memory_extractor.py
- reminder_extractor.py
- notes_extractor.py
- todo_extractor.py

memory/
- storage.py
- manager.py

plugins/
- calculator.py
- time.py
- reminder.py
- notes.py
- todo.py

responses/
- greetings.py
- system.py

utils/
- safe_math.py
- store.py

tests/

voice/
- Reserved

vision/
- Reserved

data/
- profile.json

docs/
- ARCHITECTURE.md
- ROADMAP.md
- PROJECT_STATE.md
- RULES.md
- SESSION.md

---

# Responsibilities

## main.py

Responsible for:

- Starting ALICE
- Reading user input
- Displaying responses

Never contains business logic.

---

## core/router.py

Responsible for:

- Receiving every user message
- Calling decision.py
- Sending requests to the correct module

Never performs business logic.

---

## core/decision.py

Responsible for:

- Determining which module should handle the request

It decides WHERE a request goes.

It never performs the work itself.

---

## core/context.py

Responsible for:

- Storing recent conversation history
- Clearing conversation history
- Returning conversation history

It never filters or interprets history.

---

## core/personality.py

Responsible for:

- ALICE identity
- User addressing
- Personality configuration
- Shared personality helpers

It does not contain general responses.

---

## core/response.py

Responsible for:

- Standardizing every response

Every module returns a Response object.

---

## ai/chat.py

Responsible for:

- Communicating with the AI model
- Returning AI-generated responses

It never routes requests.

---

## ai/prompts.py

Responsible for:

- AI system prompt
- Prompt construction

No application logic belongs here.

---

## ai/extractor.py

Responsible for:

- Dispatching a message to each specialised extractor in turn

Current extractors:

- memory_extractor.py
- reminder_extractor.py
- notes_extractor.py
- todo_extractor.py

Each extractor returns a dict containing an `intent` key, or None.
The dispatcher returns the first match.

---

## ai/reasoning.py

Responsible for:

- Follow-up detection
- Detail level detection
- Topic and active subject detection
- Conversation stage and intent
- Question type and user goal
- Pronoun resolution

Every detector is a pure function. The result is summarised into the
AI prompt. Detectors that read history receive the current message so
they never report it as the previous topic.

---

## memory/storage.py

Responsible for:

- Reading memory
- Writing memory

Nothing else.

---

## memory/manager.py

Responsible for:

- Memory operations
- Memory responses
- Using extractor.py

It never performs routing.

---

## utils/

Shared helpers that belong to no single module.

- `safe_math.py` evaluates arithmetic without eval().
- `store.py` provides atomic JSON list persistence.

Plugins depend on utils. Utils depend on nothing.

---

## Plugins

Each plugin:

- Performs one task
- Is independent
- Never calls another plugin
- Returns a Response object

---

# Data Flow

User

↓

main.py

↓

router.py

↓

decision.py

↓

Selected Module

↓

response.py

↓

User

---

# Dependency Rules

Allowed:

main.py
↓

core
↓

ai / memory / plugins

Forbidden:

plugins → plugins

memory → router

ai → router

Circular imports

---

# AI Rules

AI may:

- Generate text
- Answer questions
- Extract structured information

AI must never:

- Route requests
- Read files directly
- Print output
- Control application flow

---

# Memory Rules

Memory may:

- Save information
- Retrieve information
- Update information

Memory must never:

- Route requests
- Call the AI
- Print output

---

# Personality Rules

Greeting messages:

- Use the user's name.

Task completion:

- Prefer "Boss".

Neutral factual replies:

- Usually use neither name nor Boss.

Avoid mixing the user's name and "Boss" in the same response unless context requires it.

---

# Response Rules

Every module returns a Response object.

No module prints directly.

main.py is the only place responsible for displaying output.

---

# Reserved Modules

The following remain reserved until needed:

- voice/
- vision/

Do not assign unrelated responsibilities to them.

---

# Frozen Decisions

These architectural decisions are considered stable.

✓ Modular architecture

✓ Single Responsibility Principle

✓ Router controls application flow

✓ AI is a service

✓ Response object standardization

✓ Personality separated from business logic

✓ Memory extraction handled by extractor.py

✓ Conversation history handled by context.py

✓ Configuration centralised in core/config.py

✓ No module re-declares a configured value

✓ User input never reaches eval()

✓ Decision returns the parsed intent; handlers never re-parse

✓ Response.message is always a string; structured data goes in .data

---

# Future Expansion

The architecture supports future additions without redesign:

- Voice
- Vision
- Long-term memory
- Web search
- Automation
- Scheduling
- Desktop application
- Mobile application
- Discord integration
- Telegram integration

---

# Final Principle

The User gives intent.

The Core decides.

The Modules execute.

The AI assists.

ALICE remains modular.

---

# Security Rules

User input must never reach `eval`, `exec`, `compile`, `pickle` or a shell.

Arithmetic is evaluated by the AST walker in `utils/safe_math.py`, which
accepts only numeric literals and the documented operators. Every other
syntax node is rejected.

Any future feature that interprets user input must follow the same
whitelist approach.

---

# Testing Rules

Every module must have tests. Tests must:

- Run offline, with no network and no API key.
- Never touch real user data; use the `isolated_data` fixture.
- Pin the behaviour of every bug that has been fixed.

Run with `python -m pytest`.
