from core.decision import decide
from core.context import get_history

from memory.manager import handle as memory_handle
from memory.manager import all_memory

from responses.greetings import hello, goodbye

from plugins.calculator import calculate
from plugins.time import handle as time_handle

from plugins.reminder import handle as reminder_handle
from plugins.notes import handle as notes_handle
from plugins.todo import handle as todo_handle

from ai.chat import ask

from core.response import error


def route(message: str, name: str):

    destination = decide(message)

    if destination == "greeting":
        return hello(name)

    if destination == "goodbye":
        return goodbye(name)

    if destination in (
        "memory_learn",
        "memory_recall",
        "memory_forget",
        "memory_list",
    ):
        return memory_handle(message)

    if destination == "calculator":
        return calculate(message)

    if destination == "time":
        return time_handle(message)

    if destination == "reminder":
        return reminder_handle(message)

    if destination == "notes":
        return notes_handle(message)

    if destination == "todo":
        return todo_handle(message)

    if destination == "ai":

        history = get_history()

        memory = all_memory()

        return ask(
            message,
            history,
            memory,
        )

    return error(
        f"No handler found for '{destination}'.",
        source="router",
    )
