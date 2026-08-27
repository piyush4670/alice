"""Conversational replies (non-mission traffic).

Reuses the existing router for every local destination so the CLI and
the web UI behave identically; only open-ended messages reach the brain.

When the linked brain is unreachable, we fall back to the local brain so
Alice never greets the user with a bare "AI brain unavailable" message
if the offline core can still help.
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

        # Linked brain failed mid-flight — hand off to the offline core
        # instead of apologising and going silent.
        chunks = list(_fallback_local(message, history, stored, emit, mid))

    # Forward side-effect events (web.open / system.notify) that a tool
    # produced so the UI can open the web deck or raise a notification.
    for effect in getattr(brain, "last_side_effects", None) or []:
        emit(effect)

    full = "".join(chunks)

    # If the linked brain yielded nothing usable, try the local core once.
    if not full.strip():
        chunks = list(_fallback_local(message, history, stored, emit, mid))
        full = "".join(chunks)

    emit({"type": "chat.done", "mid": mid, "message": full})

    add_message("assistant", full)


def _fallback_local(message, history, stored, emit, mid):
    """Yield chunks from the local brain, emitting deltas as they arrive."""

    from agent.local_brain import LocalBrain

    local = LocalBrain()
    produced = []

    try:

        for chunk in local.converse(message, history, stored):

            if not chunk:
                continue

            produced.append(chunk)
            emit({"type": "chat.delta", "mid": mid, "text": chunk})

        # Propagate any side-effects the local brain recorded.
        for effect in getattr(local, "last_side_effects", None) or []:
            emit(effect)

    except Exception:

        from core.personality import AI_UNAVAILABLE, boss

        text = AI_UNAVAILABLE.format(title=boss())
        produced = [text]
        emit({"type": "chat.delta", "mid": mid, "text": text})

    return produced


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
