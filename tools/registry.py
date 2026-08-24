"""Alice's hands: the tool registry.

The brain decides, tools act. Every tool declares a JSON-schema-style
contract so the linked brain can call it, and every call is wrapped so
a broken tool becomes an observation, never a crash.
"""

import json

from tools.results import ToolResult
from tools.builtin import calculator, current_date, current_time
from tools.knowledge import web_search, wikipedia
from tools.manage import (
    add_note,
    complete_todo,
    delete_note,
    delete_reminder,
    forget,
    list_notes,
    list_reminders,
    list_todos,
    add_reminder,
    add_todo,
    recall,
    remember,
)
from tools.workspace import read_file, write_file


def tool(name, description, parameters, handler):

    return {
        "name": name,
        "description": description,
        "parameters": parameters,
        "handler": handler,
    }


def _text(name, description, property_name, property_description, handler):

    return tool(
        name,
        description,
        {
            "type": "object",
            "properties": {
                property_name: {
                    "type": "string",
                    "description": property_description,
                }
            },
            "required": [property_name],
        },
        handler,
    )


def _index(name, description, handler, item):

    return tool(
        name,
        description,
        {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": f"1-based {item} number from the list",
                }
            },
            "required": ["number"],
        },
        handler,
    )


def _none(name, description, handler):

    return tool(
        name,
        description,
        {"type": "object", "properties": {}},
        handler,
    )


REGISTRY = [
    _text(
        "calculator",
        "Evaluate an arithmetic expression, e.g. (12.5 + 3) * 2 / 4.",
        "expression",
        "The arithmetic expression to evaluate",
        calculator,
    ),
    _none(
        "current_time",
        "Get the current local time and timezone.",
        current_time,
    ),
    _none(
        "current_date",
        "Get today's date and weekday.",
        current_date,
    ),
    _text(
        "web_search",
        "Search the public web for fresh information. Returns the top results with titles, addresses and snippets.",
        "query",
        "The search query",
        web_search,
    ),
    _text(
        "wikipedia",
        "Look a topic up on Wikipedia and get a concise summary. Good for facts about people, places, science and history.",
        "topic",
        "The topic to look up",
        wikipedia,
    ),
    _text(
        "remember",
        "Store a lasting fact about the user, e.g. key='favourite colour', value='blue'.",
        "pair",
        "A short phrase of the form: key is value",
        remember,
    ),
    _text(
        "recall",
        "Recall everything Alice has stored about the user, or check one fact.",
        "key",
        "Optional fact key to recall; use 'all' for everything",
        recall,
    ),
    _text(
        "forget",
        "Delete a stored fact about the user.",
        "key",
        "The fact key to delete",
        forget,
    ),
    _text(
        "add_reminder",
        "Save a reminder for the user, e.g. 'call the dentist tomorrow at 5pm'.",
        "reminder",
        "What to remind about, including any time",
        add_reminder,
    ),
    _none(
        "list_reminders",
        "List every saved reminder.",
        list_reminders,
    ),
    _index(
        "delete_reminder",
        "Delete one reminder by its number.",
        delete_reminder,
        "reminder",
    ),
    _text(
        "add_note",
        "Save a note for the user.",
        "note",
        "The note text",
        add_note,
    ),
    _none(
        "list_notes",
        "List every saved note.",
        list_notes,
    ),
    _index(
        "delete_note",
        "Delete one note by its number.",
        delete_note,
        "note",
    ),
    _text(
        "add_todo",
        "Add a task to the user's to-do list.",
        "task",
        "The task text",
        add_todo,
    ),
    _none(
        "list_todos",
        "List the user's to-do list.",
        list_todos,
    ),
    _index(
        "complete_todo",
        "Mark a to-do as complete by its number.",
        complete_todo,
        "to-do",
    ),
    tool(
        "write_file",
        "Write a text artifact (report, plan, draft, list) into Alice's workspace so the user can open it.",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "File name, e.g. 'trip-plan.md'",
                },
                "body": {
                    "type": "string",
                    "description": "The full text content to save",
                },
            },
            "required": ["name", "body"],
        },
        write_file,
    ),
    _text(
        "read_file",
        "Read back a file from Alice's workspace.",
        "name",
        "The file name",
        read_file,
    ),
]

TOOLS = {item["name"]: item for item in REGISTRY}


def schema() -> list:
    """The contract shown to the linked brain."""

    return [
        {
            "name": item["name"],
            "description": item["description"],
            "parameters": item["parameters"],
        }
        for item in REGISTRY
    ]


def has(name: str) -> bool:
    return name in TOOLS


def execute(name: str, args: dict) -> ToolResult:

    item = TOOLS.get(name)

    if item is None:
        return ToolResult(False, f"Unknown tool '{name}'.")

    if args is None:
        args = {}

    if not isinstance(args, dict):
        return ToolResult(False, "Tool arguments must be an object.")

    handler = item["handler"]

    try:
        result = handler(**args) if args else handler()

    except TypeError as exc:
        return ToolResult(False, f"Bad arguments for {name}: {exc}")

    except Exception as exc:  # A broken tool is an observation, not a crash.
        return ToolResult(False, f"{name} raised: {exc}")

    if isinstance(result, ToolResult):
        return result

    if isinstance(result, dict):

        ok = result.get("success", True)
        message = result.get("message", "")

        if isinstance(message, (dict, list)):
            message = json.dumps(message, ensure_ascii=False)

        return ToolResult(bool(ok), str(message), result.get("data"))

    return ToolResult(True, str(result))
