import re


ALIASES = {
    "favorite color": "favourite colour",
    "favorite colour": "favourite colour",
    "favourite color": "favourite colour",
    "hometown": "city",
    "home town": "city",
    "place": "city",
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


ABOUT_ME_PATTERN = re.compile(
    r"^i(?:'m| am) (.+)$",
    re.IGNORECASE,
)

TEMPORARY_PREFIXES = (
    "planning",
    "going",
    "trying",
    "thinking",
    "looking",
    "working",
    "travelling",
    "traveling",
    "visiting",
    "learning",
    "studying",
)


def normalize_key(key: str):

    key = key.strip().lower()

    return ALIASES.get(key, key)


def extract(message: str):

    original = message.strip()
    text = original.lower()

    # -------------------------
    # Remember (Generic)
    # -------------------------

    generic = re.match(
        r"^my (.+?) is (.+)$",
        original,
        re.IGNORECASE,
    )

    if generic:

        return {
            "intent": "remember",
            "key": normalize_key(
                generic.group(1),
            ),
            "value": generic.group(2).strip(),
        }

    # -------------------------
    # Remember (About Me)
    # -------------------------

    about = ABOUT_ME_PATTERN.match(original)

    if about:

        value = about.group(1).strip()

        if not value.lower().startswith(TEMPORARY_PREFIXES):

            return {
                "intent": "remember",
                "key": "about me",
                "value": value,
            }

    # -------------------------
    # Remember (Fixed)
    # -------------------------

    for pattern, key in FIXED_PATTERNS:

        match = re.match(
            pattern,
            original,
            re.IGNORECASE,
        )

        if match:

            return {
                "intent": "remember",
                "key": normalize_key(key),
                "value": match.group(1).strip(),
            }

    # -------------------------
    # Forget
    # -------------------------

    forget = re.match(
        r"^forget my (.+)$",
        text,
    )

    if forget:

        return {
            "intent": "forget",
            "key": normalize_key(
                forget.group(1),
            ),
        }

    # -------------------------
    # List Memory
    # -------------------------

    if text in (
        "what do you know about me",
        "what do you remember about me",
        "show my memory",
        "show what you know about me",
        "list my memory",
    ):

        return {
            "intent": "list",
        }

    # -------------------------
    # Recall
    # -------------------------

    recall = re.match(
        r"^(what|who|where)\s+is\s+my\s+(.+?)\??$",
        text,
    )

    if recall:

        return {
            "intent": "recall",
            "key": normalize_key(
                recall.group(2),
            ),
        }

    return None
