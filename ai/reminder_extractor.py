import re


# Relative day words are a time value in their own right, not noise to drop.
DAY_WORDS = (
    "today",
    "tonight",
    "tomorrow",
    "tomorrow morning",
    "tomorrow afternoon",
    "tomorrow evening",
    "tomorrow night",
    "tonight",
    "this evening",
    "this afternoon",
    "this morning",
    "next week",
    "next monday",
    "next tuesday",
    "next wednesday",
    "next thursday",
    "next friday",
    "next saturday",
    "next sunday",
)

# A clock time such as "5pm", "5 pm", "17:30", "9 o'clock".
CLOCK = r"\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.|o'clock)?"

DAY_ALTERNATION = "|".join(
    re.escape(word) for word in sorted(DAY_WORDS, key=len, reverse=True)
)

# Ordered most specific first. Each anchors the time clause to the END of
# the string, so "remind me to look at the report at 5pm" keeps its task.
ADD_PATTERNS = (
    # ... <day> at <clock>
    rf"^remind me to (.+?)\s+(?:on\s+|at\s+)?({DAY_ALTERNATION})\s+at\s+({CLOCK})$",
    # ... at <clock> on <day>
    rf"^remind me to (.+?)\s+at\s+({CLOCK})\s+(?:on\s+)?({DAY_ALTERNATION})$",
    # ... at <clock>
    rf"^remind me to (.+?)\s+at\s+({CLOCK})$",
    # ... on <date/day>
    r"^remind me to (.+?)\s+on\s+(.+)$",
    # ... <day>
    rf"^remind me to (.+?)\s+({DAY_ALTERNATION})$",
    # bare task
    r"^remind me to (.+)$",
)

LIST_PHRASES = (
    "show my reminders",
    "list my reminders",
    "show reminders",
    "list reminders",
    "what are my reminders",
    "my reminders",
)


def join_time(parts):

    values = [part.strip() for part in parts if part and part.strip()]

    if not values:
        return None

    return " ".join(values)


def extract(message: str):

    original = message.strip()
    lower = original.lower()

    # -------------------------
    # Add Reminder
    # -------------------------

    for pattern in ADD_PATTERNS:

        match = re.match(pattern, original, re.IGNORECASE)

        if not match:
            continue

        groups = match.groups()

        task = groups[0].strip().rstrip(",.")

        if not task:
            continue

        return {
            "intent": "reminder_add",
            "task": task,
            "time": join_time(groups[1:]),
        }

    # -------------------------
    # List Reminders
    # -------------------------

    if lower.rstrip("?.!") in LIST_PHRASES:

        return {
            "intent": "reminder_list",
        }

    # -------------------------
    # Delete Reminder
    # -------------------------

    delete = re.match(
        r"^(?:delete|remove|clear) reminder (?:number\s+)?(\d+)$",
        lower.rstrip(".!"),
    )

    if delete:

        return {
            "intent": "reminder_delete",
            "index": int(delete.group(1)) - 1,
        }

    return None
