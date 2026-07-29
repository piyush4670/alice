from ai.extractor import extract

from memory.storage import load_memory, save_memory

from core.response import success, error
from core.personality import boss


def remember(key: str, value):

    memory = load_memory()

    existing = memory.get(key)

    if existing == value:
        return False

    memory[key] = value

    save_memory(memory)

    return True


def recall(key: str):

    memory = load_memory()

    return memory.get(key)


def forget(key: str):

    memory = load_memory()

    if key not in memory:
        return False

    del memory[key]

    save_memory(memory)

    return True


def exists(key: str):

    memory = load_memory()

    return key in memory


def all_memory():

    return load_memory()


def handle(message: str):

    data = extract(message)

    if data is None:

        return error(
            "I couldn't understand that memory request.",
            source="memory",
        )

    if data["intent"] == "remember":

        if remember(
            data["key"],
            data["value"],
        ):

            return success(
                f"Got it, {boss()}. I'll remember your {data['key']}. 💙",
                source="memory",
            )

        return success(
            f"I already know your {data['key']}, {boss()}.",
            source="memory",
        )

    if data["intent"] == "recall":

        value = recall(
            data["key"],
        )

        if value is None:

            return success(
                f"I don't know your {data['key']} yet, {boss()}.",
                source="memory",
            )

        return success(
            f"Your {data['key']} is {value}.",
            source="memory",
        )

    if data["intent"] == "forget":

        if forget(data["key"]):

            return success(
                f"I've forgotten your {data['key']}, {boss()}.",
                source="memory",
            )

        return success(
            f"I don't have your {data['key']} stored, {boss()}.",
            source="memory",
        )

    if data["intent"] == "list":

        memory = all_memory()

        if not memory:

            return success(
                "I don't know anything about you yet.",
                source="memory",
            )

        facts = []

        for key, value in memory.items():
            facts.append(f"{key}: {value}")

        return success(
            "Here's what I know about you:\n\n" + "\n".join(facts),
            source="memory",
        )

    return error(
        "Unknown memory operation.",
        source="memory",
    )
