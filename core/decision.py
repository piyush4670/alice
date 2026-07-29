from ai.extractor import extract


GREETING_WORDS = {
    "hello",
    "hi",
    "hey",
}

GREETING_PHRASES = {
    "good morning",
    "good afternoon",
    "good evening",
}

EXIT_WORDS = {
    "bye",
    "goodbye",
    "exit",
    "quit",
}

TIME_KEYWORDS = (
    "time",
    "date",
    "today",
)


def is_greeting(message: str) -> bool:

    if message in GREETING_PHRASES:
        return True

    words = message.split()

    if not words:
        return False

    return words[0] in GREETING_WORDS


def decide(message: str) -> str:

    message = message.lower().strip()

    # Greetings
    if is_greeting(message):
        return "greeting"

    # Exit
    if message in EXIT_WORDS:
        return "goodbye"

    # Time & Date
    if any(
        keyword in message
        for keyword in TIME_KEYWORDS
    ):
        return "time"

    # Calculator
    if message.startswith("calculate "):
        return "calculator"

    operators = (
        "+",
        "-",
        "*",
        "/",
        "%",
        "**",
        "(",
        ")",
    )

    if any(op in message for op in operators):

        allowed = set("0123456789+-*/%.() ")

        if all(ch in allowed for ch in message):
            return "calculator"

    # Intent Extraction
    intent = extract(message)

    if intent:

        if intent["intent"] == "remember":
            return "memory_learn"

        if intent["intent"] == "recall":
            return "memory_recall"

        if intent["intent"] == "forget":
            return "memory_forget"

        if intent["intent"] == "list":
            return "memory_list"

        if intent["intent"].startswith("reminder"):
            return "reminder"

        if intent["intent"].startswith("note"):
            return "notes"

        if intent["intent"].startswith("todo"):
            return "todo"

    # AI
    return "ai"
