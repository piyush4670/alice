"""Conversational replies (non-mission traffic).

Reuses the existing router for every local destination so the CLI and
the web UI behave identically; only open-ended messages reach the brain.
"""

from core.context import add_message, get_history
from core.decision import decide
from core.router import route
from memory import manager as memory
from agent.models import new_id


def respond(message: str, emit, brain) -> None:
    """Answer one chat message, emitting chat events as they arrive."""

    add_message("user", message)

    memory_before = memory.all_memory()

    decision = decide(message)

    if decision.destination == "ai":

        _reply_with_brain(message, emit, brain)

    else:

        reply = route(message)

        _emit_message(emit, reply.message, source=reply.source, data=reply.data)

        add_message("assistant", reply.message)

    if memory.all_memory() != memory_before:
        emit({"type": "memory.updated", "items": memory.all_memory()})


def _reply_with_brain(message: str, emit, brain) -> None:

    history = get_history()
    stored = memory.all_memory()

    mid = new_id("m")
    chunks = []

    try:

        for chunk in brain.converse(message, history, stored):

            if not chunk:
                continue

            chunks.append(chunk)

            emit(
                {
                    "type": "chat.delta",
                    "mid": mid,
                    "text": chunk,
                }
            )

    except Exception:

        from core.personality import AI_UNAVAILABLE, boss

        text = AI_UNAVAILABLE.format(title=boss())

        emit({"type": "chat.delta", "mid": mid, "text": text})

        chunks = [text]

    full = "".join(chunks)

    emit({"type": "chat.done", "mid": mid, "message": full})

    add_message("assistant", full)


def _emit_message(emit, text: str, source="system", data=None):

    mid = new_id("m")

    payload = {
        "type": "chat.delta",
        "mid": mid,
        "text": text,
    }

    emit(payload)

    emit(
        {
            "type": "chat.done",
            "mid": mid,
            "message": text,
            "source": source,
            "data": data,
        }
    )
