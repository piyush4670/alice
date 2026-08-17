"""Request routing.

The Router routes. It never performs business logic.
"""

from ai.chat import ask
from core.context import get_history
from core.decision import decide
from core.response import error
from memory.manager import all_memory
from memory.manager import handle as memory_handle
from plugins.calculator import calculate
from plugins.notes import handle as notes_handle
from plugins.reminder import handle as reminder_handle
from plugins.time import handle as time_handle
from plugins.todo import handle as todo_handle
from responses.greetings import goodbye, hello
from responses.system import empty_message

MEMORY_DESTINATIONS = (
    "memory_learn",
    "memory_recall",
    "memory_forget",
    "memory_list",
)


def route(message: str, name: str = None):

    decision = decide(message)

    destination = decision.destination

    request = decision.message

    if destination == "empty":
        return empty_message()

    if destination == "greeting":
        return hello()

    if destination == "goodbye":
        return goodbye()

    if destination in MEMORY_DESTINATIONS:
        return memory_handle(request, decision.intent)

    if destination == "calculator":
        return calculate(request)

    if destination == "time":
        return time_handle(request)

    if destination == "reminder":
        return reminder_handle(request, decision.intent)

    if destination == "notes":
        return notes_handle(request, decision.intent)

    if destination == "todo":
        return todo_handle(request, decision.intent)

    if destination == "ai":
        return ask(
            request,
            get_history(),
            all_memory(),
        )

    return error(
        f"No handler found for '{destination}'.",
        source="router",
    )
