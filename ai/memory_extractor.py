import re


ALIASES = {
    "favorite color": "favourite colour",
    "favorite colour": "favourite colour",
    "favourite color": "favourite colour",
    "fav colour": "favourite colour",
    "fav color": "favourite colour",
    "hometown": "city",
    "home town": "city",
    "place": "city",
    "phone number": "phone",
    "mobile number": "phone",
    "e-mail": "email",
    "birth date": "birthday",
    "date of birth": "birthday",
    "dob": "birthday",
}


FIXED_PATTERNS = [
    (r"^i live in (.+)$", "city"),
    (r"^i study at (.+)$", "college"),
    (r"^my name is (.+)$", "name"),
    (r"^i like (.+)$", "likes"),
    (r"^i love (.+)$", "likes"),
    (r"^i enjoy (.+)$", "likes"),
    (r"^i prefer (.+)$", "likes"),
    (r"^i work as (.+)$", "occupation"),
    (r"^i work at (.+)$", "workplace"),
    (r"^my birthday is (.+)$", "birthday"),
    (r"^my hobby is (.+)$", "hobby"),
]


# An explicit request always stores, regardless of the heuristics below.
EXPLICIT_PATTERNS = (
    r"^remember that my (.+?) is (.+)$",
    r"^remember my (.+?) is (.+)$",
    r"^please remember my (.+?) is (.+)$",
)


ABOUT_ME_PATTERN = re.compile(r"^i(?:'m| am) (.+)$", re.IGNORECASE)


# "I am ..." states that are transient, not identity.
TRANSIENT_PREFIXES = (
    "planning",
    "going",
    "trying",
    "thinking",
    "looking",
    "working on",
    "travelling",
    "traveling",
    "visiting",
    "learning",
    "studying",
    "waiting",
    "wondering",
    "asking",
    "curious",
    "confused",
    "stuck",
    "tired",
    "hungry",
    "bored",
    "busy",
    "sorry",
    "sure",
    "fine",
    "okay",
    "ok",
    "good",
    "great",
    "happy",
    "sad",
    "angry",
    "afraid",
    "not ",
    "here",
    "back",
    "done",
    "ready",
    "glad",
)


# Words that mark a phrase as conversation rather than a stored fact.
QUESTION_WORDS = {
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "whether",
    "if",
}

# Keys that indicate the user is talking, not declaring a fact.
NON_FACT_KEYS = {
    "question",
    "problem",
    "issue",
    "point",
    "answer",
    "reply",
    "response",
    "guess",
    "opinion",
    "concern",
    "worry",
    "doubt",
    "understanding",
    "thought",
    "idea",
    "plan",
    "code",
    "error",
    "bug",
    "output",
    "result",
    "goal for today",
}

# Values that describe a state of affairs rather than a fact worth storing.
NON_FACT_VALUE_PREFIXES = (
    "not ",
    "n't",
    "that ",
    "why ",
    "what ",
    "how ",
    "when ",
    "where ",
    "who ",
    "because ",
    "still ",
    "already ",
    "kind of",
    "sort of",
)

MAX_KEY_WORDS = 3

MAX_VALUE_WORDS = 12

LIST_PHRASES = (
    "what do you know about me",
    "what do you remember about me",
    "show my memory",
    "show what you know about me",
    "list my memory",
    "what have you remembered",
)


def normalize_key(key: str) -> str:

    key = re.sub(r"\s+", " ", key.strip().lower())

    return ALIASES.get(key, key)


def looks_like_fact(key: str, value: str) -> bool:
    """Guard the generic 'my X is Y' pattern against ordinary conversation."""

    key = key.strip().lower()
    value = value.strip()

    if not key or not value:
        return False

    key_words = key.split()

    if len(key_words) > MAX_KEY_WORDS:
        return False

    if key in NON_FACT_KEYS:
        return False

    if any(word in QUESTION_WORDS for word in key_words):
        return False

    lowered_value = value.lower()

    if len(value.split()) > MAX_VALUE_WORDS:
        return False

    if lowered_value.startswith(NON_FACT_VALUE_PREFIXES):
        return False

    if "?" in value:
        return False

    return True


def remember(key: str, value: str) -> dict:

    return {
        "intent": "remember",
        "key": normalize_key(key),
        "value": value.strip().rstrip(".!"),
    }


def extract(message: str):

    original = message.strip()
    text = original.lower().rstrip(" .!")

    # -------------------------
    # Remember (Explicit)
    # -------------------------

    for pattern in EXPLICIT_PATTERNS:

        match = re.match(pattern, original, re.IGNORECASE)

        if match:
            return remember(match.group(1), match.group(2))

    # -------------------------
    # List Memory
    # -------------------------

    if text.rstrip("?") in LIST_PHRASES:
        return {"intent": "list"}

    # -------------------------
    # Recall
    # -------------------------

    recall = re.match(
        r"^(?:what|who|where)(?:'s| is|s)?\s+my\s+(.+?)\??$",
        text,
    )

    if recall:
        return {
            "intent": "recall",
            "key": normalize_key(recall.group(1)),
        }

    if original.endswith("?"):
        return None

    # -------------------------
    # Forget
    # -------------------------

    forget = re.match(r"^forget my (.+)$", text)

    if forget:
        return {
            "intent": "forget",
            "key": normalize_key(forget.group(1)),
        }

    # -------------------------
    # Remember (Fixed)
    # -------------------------

    for pattern, key in FIXED_PATTERNS:

        match = re.match(pattern, original, re.IGNORECASE)

        if match:
            return remember(key, match.group(1))

    # -------------------------
    # Remember (Generic, guarded)
    # -------------------------

    generic = re.match(r"^my (.+?) is (.+)$", original, re.IGNORECASE)

    if generic:

        key = generic.group(1)
        value = generic.group(2)

        if looks_like_fact(key, value):
            return remember(key, value)

        return None

    # -------------------------
    # Remember (About Me, guarded)
    # -------------------------

    about = ABOUT_ME_PATTERN.match(original)

    if about:

        value = about.group(1).strip()

        lowered = value.lower()

        if lowered.startswith(TRANSIENT_PREFIXES):
            return None

        if len(value.split()) > MAX_VALUE_WORDS:
            return None

        return remember("about me", value)

    return None
