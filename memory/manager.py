from ai.extractor import extract
from core.personality import (
    MEMORY_CONFIRM,
    MEMORY_EMPTY,
    MEMORY_FORGOTTEN,
    MEMORY_KNOWN,
    MEMORY_LIST_HEADER,
    MEMORY_MISSING,
    MEMORY_RECALL,
    MEMORY_UNKNOWN,
    MEMORY_UPDATED,
    SIGNATURE,
    boss,
)
from core.response import error, success
from memory.storage import load_memory, save_memory


def remember(key: str, value):
    """Return 'created', 'updated' or 'unchanged'."""

    memory = load_memory()

    existing = memory.get(key)

    if existing == value:
        return "unchanged"

    memory[key] = value

    save_memory(memory)

    return "updated" if existing is not None else "created"


def recall(key: str):
    return load_memory().get(key)


def forget(key: str) -> bool:

    memory = load_memory()

    if key not in memory:
        return False

    del memory[key]

    save_memory(memory)

    return True


def exists(key: str) -> bool:
    return key in load_memory()


def all_memory():
    return load_memory()


def handle_remember(data):

    outcome = remember(data["key"], data["value"])

    if outcome == "created":
        return success(
            MEMORY_CONFIRM.format(
                title=boss(),
                key=data["key"],
                heart=SIGNATURE,
            ),
            source="memory",
        )

    if outcome == "updated":
        return success(
            MEMORY_UPDATED.format(
                title=boss(),
                key=data["key"],
                heart=SIGNATURE,
            ),
            source="memory",
        )

    return success(
        MEMORY_KNOWN.format(title=boss(), key=data["key"]),
        source="memory",
    )


def handle_recall(data):

    value = recall(data["key"])

    if value is None:
        return success(
            MEMORY_UNKNOWN.format(title=boss(), key=data["key"]),
            source="memory",
        )

    return success(
        MEMORY_RECALL.format(key=data["key"], value=value),
        source="memory",
        data=value,
    )


def handle_forget(data):

    if forget(data["key"]):
        return success(
            MEMORY_FORGOTTEN.format(title=boss(), key=data["key"]),
            source="memory",
        )

    return success(
        MEMORY_MISSING.format(title=boss(), key=data["key"]),
        source="memory",
    )


def handle_list():

    memory = all_memory()

    if not memory:
        return success(MEMORY_EMPTY, source="memory")

    facts = [f"- {key}: {value}" for key, value in memory.items()]

    return success(
        MEMORY_LIST_HEADER + "\n\n" + "\n".join(facts),
        source="memory",
        data=memory,
    )


def handle(message: str, intent: dict = None):

    data = intent if intent is not None else extract(message)

    if data is None:
        return error(
            "I couldn't understand that memory request.",
            source="memory",
        )

    name = data.get("intent")

    if name == "remember":
        return handle_remember(data)

    if name == "recall":
        return handle_recall(data)

    if name == "forget":
        return handle_forget(data)

    if name == "list":
        return handle_list()

    return error("Unknown memory operation.", source="memory")
