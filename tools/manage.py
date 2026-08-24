"""Life-management tools: memory, reminders, notes and to-dos.

These wrap the existing plugins so the agent and the CLI share one
implementation of every action.
"""

import re

import memory.manager as memory
from memory.manager import all_memory

from tools.results import ToolResult


def _plain(message: str):
    """Plugin handlers expect raw user phrasing; strip tool formality."""

    text = (message or "").strip()

    fillers = (
        "please ",
        "could you ",
        "can you ",
    )

    lowered = text.lower()

    for filler in fillers:

        if lowered.startswith(filler):
            text = text[len(filler):]
            lowered = text.lower()

    return text.strip()


# ===========
# Memory
# ===========

PAIR_PATTERN = re.compile(r"(.+?)\s+(?:is|are|=|:)\s+(.+)", re.IGNORECASE)


def remember(pair: str) -> ToolResult:

    text = _plain(pair).rstrip(".")

    match = PAIR_PATTERN.search(text)

    if not match:
        return ToolResult(False, "Use the form: 'key is value', e.g. 'favourite colour is blue'.")

    key = match.group(1).strip().lower()
    value = match.group(2).strip()

    outcome = memory.remember(key, value)

    if outcome == "unchanged":
        return ToolResult(True, f"I already had that: {key} = {value}.")

    verb = "Updated" if outcome == "updated" else "Stored"

    return ToolResult(
        True,
        f"{verb}: {key} = {value}.",
        {"memory": all_memory()},
    )


def recall(key: str) -> ToolResult:

    key = (key or "").strip().lower()

    if key in ("", "all", "everything"):

        stored = all_memory()

        if not stored:
            return ToolResult(True, "Nothing is stored about the user yet.")

        lines = [f"- {name}: {value}" for name, value in stored.items()]

        return ToolResult(True, "Known facts:\n" + "\n".join(lines), {"memory": stored})

    value = memory.recall(key)

    if value is None:
        return ToolResult(True, f"Nothing stored for '{key}'.")

    return ToolResult(True, f"{key}: {value}")


def forget(key: str) -> ToolResult:

    key = (key or "").strip().lower()

    if memory.forget(key):
        return ToolResult(True, f"Deleted fact '{key}'.")

    return ToolResult(True, f"Nothing stored under '{key}'.")


# ===========
# Reminders
# ===========

def add_reminder(reminder: str) -> ToolResult:

    from plugins.reminder import handle

    text = _plain(reminder)

    lowered = text.lower()

    if not lowered.startswith(("remind me", "reminder")):
        text = f"remind me to {text}"

    reply = handle(text)

    if reply.success:
        return ToolResult(True, reply.message, reply.data)

    return ToolResult(False, reply.message)


def list_reminders() -> ToolResult:

    from plugins.reminder import handle

    reply = handle("show my reminders")

    return ToolResult(reply.success, reply.message, reply.data)


def delete_reminder(number: int) -> ToolResult:

    from plugins.reminder import handle

    reply = handle(f"delete reminder {number}")

    return ToolResult(reply.success, reply.message, reply.data)


# ===========
# Notes
# ===========

def add_note(note: str) -> ToolResult:

    from plugins.notes import handle

    text = _plain(note)
    lowered = text.lower()

    if not lowered.startswith(("note that", "note ", "add note")):
        text = f"note that {text}"

    reply = handle(text)

    return ToolResult(reply.success, reply.message, reply.data)


def list_notes() -> ToolResult:

    from plugins.notes import handle

    reply = handle("show my notes")

    return ToolResult(reply.success, reply.message, reply.data)


def delete_note(number: int) -> ToolResult:

    from plugins.notes import handle

    reply = handle(f"delete note {number}")

    return ToolResult(reply.success, reply.message, reply.data)


# ===========
# To-dos
# ===========

def add_todo(task: str) -> ToolResult:

    from plugins.todo import handle

    text = _plain(task)
    lowered = text.lower()

    if not lowered.startswith(("add task", "add a task", "todo", "to do")):
        text = f"add task {text}"

    reply = handle(text)

    return ToolResult(reply.success, reply.message, reply.data)


def list_todos() -> ToolResult:

    from plugins.todo import handle

    reply = handle("show my tasks")

    return ToolResult(reply.success, reply.message, reply.data)


def complete_todo(number: int) -> ToolResult:

    from plugins.todo import handle

    reply = handle(f"complete task {number}")

    return ToolResult(reply.success, reply.message, reply.data)
