"""Intent detection.

The Decision Engine decides WHERE a request goes. It never performs the
work itself. It returns the parsed intent alongside the destination so
that handlers never have to re-parse the same message.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional

from ai.extractor import extract


@dataclass
class Decision:
    destination: str
    intent: Optional[dict] = None
    message: Any = None


GREETING_WORDS = {
    "hello",
    "hi",
    "hey",
    "yo",
    "hiya",
}

GREETING_PHRASES = (
    "good morning",
    "good afternoon",
    "good evening",
)

EXIT_WORDS = {
    "bye",
    "goodbye",
    "exit",
    "quit",
    "see you",
    "good night",
}

# Anchored on word boundaries so "update", "sometimes" and "birth date"
# no longer route to the time plugin.
TIME_PATTERNS = (
    r"\bwhat(?:'s| is)? the time\b",
    r"\bwhat time is it\b",
    r"\bcurrent time\b",
    r"\btime now\b",
    r"\bthe time now\b",
    r"\btell me the time\b",
)

DATE_PATTERNS = (
    r"\bwhat(?:'s| is)? the date\b",
    r"\bwhat(?:'s| is)? today(?:'s)? date\b",
    r"\btoday(?:'s)? date\b",
    r"\bcurrent date\b",
    r"\bwhat day is it\b",
    r"\bwhat(?:'s| is)? the day today\b",
    r"\btell me the date\b",
)

CALCULATOR_PREFIXES = (
    "calculate ",
    "compute ",
    "solve ",
)

# Polite lead-ins that wrap a real request: "can you calculate 5+5".
POLITE_PREFIXES = (
    "can you please",
    "could you please",
    "can you",
    "could you",
    "would you",
    "will you",
    "please",
    "i want you to",
    "i need you to",
)

MATH_CHARACTERS = set("0123456789+-*/%.() ")

MATH_OPERATORS = set("+-*/%")


INTENT_DESTINATIONS = {
    "remember": "memory_learn",
    "recall": "memory_recall",
    "forget": "memory_forget",
    "list": "memory_list",
}

INTENT_PREFIXES = (
    ("reminder", "reminder"),
    ("note", "notes"),
    ("todo", "todo"),
)


def normalise(message: str) -> str:
    return (message or "").strip()


def strip_greeting(message: str) -> str:
    """Remove a leading greeting so the real request survives.

    'hey can you calculate 5+5' becomes 'can you calculate 5+5'.
    """

    text = message.strip()

    lowered = text.lower()

    for phrase in GREETING_PHRASES:

        if lowered.startswith(phrase):
            return text[len(phrase):].lstrip(" ,.!-").strip()

    match = re.match(r"^([a-z]+)\b[\s,!.]*(.*)$", lowered, re.DOTALL)

    if match and match.group(1) in GREETING_WORDS:
        remainder = text[len(match.group(1)):]
        return remainder.lstrip(" ,.!-").strip()

    return text


def strip_politeness(message: str) -> str:
    """Remove a leading 'can you' / 'please' wrapper."""

    text = message.strip()

    lowered = text.lower()

    for phrase in POLITE_PREFIXES:

        if lowered.startswith(phrase + " "):
            return text[len(phrase):].lstrip(" ,").strip()

    return text


def is_greeting(message: str) -> bool:
    """True only when the message is nothing but a greeting."""

    text = message.lower().strip().rstrip("!.?")

    if text in GREETING_WORDS:
        return True

    if text in GREETING_PHRASES:
        return True

    return not strip_greeting(text) and bool(strip_greeting(text) != text)


def is_exit(message: str) -> bool:

    text = message.lower().strip().rstrip("!.?")

    return text in EXIT_WORDS


def is_time_request(message: str) -> bool:

    text = message.lower()

    patterns = TIME_PATTERNS + DATE_PATTERNS

    return any(re.search(pattern, text) for pattern in patterns)


def is_math(message: str) -> bool:

    text = message.lower().strip()

    if text.startswith(CALCULATOR_PREFIXES):
        return True

    stripped = text
    for prefix in ("what is ", "what's "):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break

    stripped = stripped.rstrip("=?").strip()

    if not stripped:
        return False

    if not any(character in MATH_OPERATORS for character in stripped):
        return False

    if not any(character.isdigit() for character in stripped):
        return False

    return all(character in MATH_CHARACTERS for character in stripped)


def destination_for(intent: dict) -> Optional[str]:

    name = intent.get("intent", "")

    if name in INTENT_DESTINATIONS:
        return INTENT_DESTINATIONS[name]

    for prefix, destination in INTENT_PREFIXES:

        if name.startswith(prefix):
            return destination

    return None


def decide(message: str) -> Decision:

    original = normalise(message)

    if not original:
        return Decision("empty", message=original)

    if is_exit(original):
        return Decision("goodbye", message=original)

    if is_greeting(original):
        return Decision("greeting", message=original)

    # A greeting or a polite wrapper may prefix a real request:
    # answer the request itself.
    request = strip_politeness(strip_greeting(original))

    if not request:
        return Decision("greeting", message=original)

    if is_exit(request):
        return Decision("goodbye", message=request)

    # Structured intents are checked before generic keywords so that
    # "remind me to call mom today" reaches the reminder plugin.
    intent = extract(request)

    if intent:

        destination = destination_for(intent)

        if destination:
            return Decision(destination, intent=intent, message=request)

    if is_math(request):
        return Decision("calculator", message=request)

    if is_time_request(request):
        return Decision("time", message=request)

    return Decision("ai", message=request)
