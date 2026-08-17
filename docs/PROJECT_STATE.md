# ALICE Project State

Version: 3.1

Status: Active Development

Last Updated: August 2026

---

# Overview

ALICE is a modular personal AI assistant built in Python.

The architecture is stable and considered frozen.

Current development focuses on expanding ALICE's capabilities while preserving the existing architecture.

---

# Architecture Status

Status:

🟢 Stable

Current Architecture

```
User
   │
   ▼
main.py
   │
   ▼
router.py
   │
   ▼
decision.py
   │
   ├──────────────┬──────────────┐
   ▼              ▼              ▼
Memory        Plugins         AI System
                                 │
                                 ▼
                           Prompt Builder
                                 │
                                 ▼
                             AI Model
```

Core architecture is frozen.

Future development should extend capabilities without redesigning the architecture.

---

# Core Modules

## main.py

Responsible for:

- Starting ALICE
- User interaction
- Conversation loop
- Context updates

---

## router.py

Responsible for:

- Routing requests
- Dispatching modules
- Returning Response objects

---

## decision.py

Responsible for:

- Intent detection
- Greeting detection
- Tool selection
- Calculator detection
- Memory routing
- Reminder routing
- Notes routing
- AI fallback

---

## response.py

Provides a unified Response model for the entire project.

---

## personality.py

Centralized personality configuration.

Contains:

- Greetings
- Assistant identity
- Titles
- Default responses

---

## context.py

Maintains conversation history.

Current capabilities:

- Circular history
- Maximum history size
- Shared with AI reasoning

---

# AI System

Directory:

```
ai/
```

Modules:

## chat.py

Responsible for:

- Prompt creation
- API communication
- AI responses

---

## prompts.py

Builds prompts using:

- System prompt
- User memory
- Conversation history
- Reasoning
- Current user message

---

## reasoning.py

Current capabilities:

- Follow-up detection
- Detail level detection
- Topic detection
- Question type detection
- User goal detection
- Pronoun resolution

Reasoning information is automatically included in AI prompts.

---

## extractor.py

Acts as the central intent dispatcher.

Current extractors:

- Memory Extractor
- Reminder Extractor
- Notes Extractor

---

# Memory System

Directory:

```
memory/
```

Capabilities:

- Persistent storage
- JSON profile
- Remember
- Recall
- Forget
- List memory
- Memory normalization

Memory is automatically supplied to the AI.

---

# Plugins

Current plugins:

## Calculator

Supports:

- +
- -
- *
- /
- %
- **

Automatic expression detection.

---

## Time

Supports:

- Current time
- Current date

---

## Reminder

Supports:

- Add reminder
- List reminders
- Delete reminders
- Persistent storage

Data stored in:

```
data/reminders.json
```

---

## Notes

Supports:

- Add note
- List notes
- Delete notes
- Persistent storage

Data stored in:

```
data/notes.json
```

---

# Response System

Every module returns a standard Response object.

Benefits:

- Consistency
- Easier debugging
- Cleaner routing
- Better modularity

---

# Current Capabilities

ALICE can currently:

✅ Natural conversation

✅ AI-powered responses

✅ Remember information

✅ Recall information

✅ Forget memories

✅ List stored memories

✅ Conversation history

✅ Follow-up understanding

✅ Topic continuity

✅ Pronoun resolution

✅ User goal detection

✅ Detail level detection

✅ Mathematical calculations

✅ Current time

✅ Current date

✅ Reminder management

✅ Notes management

✅ Long-term memory integration

✅ To-do list management

✅ Greeting and politeness prefix handling

---

# Current Limitations

Not yet implemented:

- Scheduling
- Reminder execution
- Internet access
- Web search
- Weather
- News
- Voice interaction
- Vision
- Automation
- Memory ranking
- Memory summarization
- Relationship graph

---

# Engineering Principles

The project follows:

- Modular architecture
- Single Responsibility Principle
- Standard Response objects
- Minimal dependencies
- Independent modules

Architecture changes require strong justification.

Features are added without redesigning the existing system.

---

# Current Development Focus

Current milestone:

**ALICE v1.1**

Completed:

- Foundation
- Intelligence
- Memory
- Context awareness
- Reminders
- Notes
- To-do lists
- Sprint 11 hardening

Next milestone:

Phase 3 - Internet

Goal:

Add web search and live information using the existing architecture.

---

# Testing

Directory:

```
tests/
```

168 tests covering routing, extraction, persistence, prompt construction
and arithmetic safety. They run offline in under a second and never touch
real user data.

```bash
python -m pytest
```

Every defect recorded in `docs/ANALYSIS.md` has a regression test.

---

# Security

User input never reaches `eval()`. Arithmetic uses the AST evaluator in
`utils/safe_math.py`, which whitelists numeric literals and the documented
operators and rejects every other syntax node.

Writes to disk are atomic, so an interrupted save cannot corrupt a file.

---

# Overall Project Health

Architecture

🟢 Stable

Code Quality

🟢 Good

Test Coverage

🟢 168 tests

Security

🟢 Hardened

Documentation

🟢 Up-to-date

Development Progress

🟢 On Track

Project Readiness

Ready for Phase 3 development.
