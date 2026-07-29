import re


RELATION_PRONOUNS = {
    "mother": ("she", "her"),
    "mom": ("she", "her"),
    "father": ("he", "him"),
    "dad": ("he", "him"),
    "brother": ("he", "him"),
    "sister": ("she", "her"),
    "wife": ("she", "her"),
    "husband": ("he", "him"),
    "friend": ("they", "them"),
}


FOLLOW_UP_PHRASES = (
    "tell me more",
    "explain more",
    "go on",
    "continue",
    "why",
    "how",
    "and then",
    "what about that",
    "what about it",
    "elaborate",
    "more",
)


def detect_follow_up(message: str, history):

    message = message.lower().strip()

    if not history:
        return False

    return message in FOLLOW_UP_PHRASES


def detect_detail_level(message: str):

    message = message.lower()

    detailed = (
        "explain",
        "detailed",
        "in detail",
        "step by step",
        "teach me",
        "complete guide",
    )

    brief = (
        "brief",
        "briefly",
        "short",
        "summary",
        "in short",
    )

    if any(word in message for word in detailed):
        return "detailed"

    if any(word in message for word in brief):
        return "brief"

    return "normal"


def detect_topic(history):

    if not history:
        return None

    for item in reversed(history):

        if item["role"] == "user":
            return item["message"]

    return None


def detect_question_type(message: str):

    message = message.lower().strip()

    if message.startswith(("who", "what", "where", "when")):
        return "fact"

    if message.startswith("why"):
        return "reason"

    if message.startswith("how"):
        return "procedure"

    return "general"


def detect_user_goal(message: str):

    message = message.lower()

    if any(word in message for word in ("learn", "teach", "understand")):
        return "learning"

    if any(word in message for word in ("buy", "recommend", "best", "choose")):
        return "decision"

    return "general"


def detect_conversation_stage(message: str, history):

    text = message.lower().strip()

    if detect_follow_up(message, history):
        return "follow_up"

    clarification = (
        "what do you mean",
        "can you explain",
        "i don't understand",
    )

    if any(text.startswith(item) for item in clarification):
        return "clarification"

    continuation = (
        "what about",
        "also",
        "and",
        "then",
    )

    if any(text.startswith(item) for item in continuation):
        return "continuation"

    return "new_topic"


def detect_conversation_intent(message: str):

    text = message.lower()

    if any(word in text for word in ("learn", "teach", "explain", "understand")):
        return "learning"

    if any(word in text for word in ("plan", "planning", "trip", "schedule")):
        return "planning"

    if any(word in text for word in ("compare", "vs", "versus")):
        return "comparison"

    if any(
        phrase in text
        for phrase in (
            "error",
            "issue",
            "problem",
            "doesn't work",
            "not working",
        )
    ):
        return "troubleshooting"

    if any(word in text for word in ("recommend", "best", "buy", "choose")):
        return "decision"

    if any(
        text.startswith(word)
        for word in (
            "hi",
            "hello",
            "hey",
        )
    ):
        return "chat"

    return "general"


def detect_active_subject(history):

    if not history:
        return None

    for item in reversed(history):

        if item["role"] != "user":
            continue

        message = item["message"].strip()

        lower = message.lower()

        if lower in FOLLOW_UP_PHRASES:
            continue

        if lower.startswith(
            (
                "what about",
                "can you explain",
                "what do you mean",
            )
        ):
            continue

        if len(message.split()) < 3:
            continue

        return message

    return None


def resolve_entities(history):

    resolved = {}

    pattern = re.compile(
        r"my (mother|mom|father|dad|brother|sister|wife|husband|friend) is ([a-zA-Z]+)",
        re.IGNORECASE,
    )

    for item in history:

        if item["role"] != "user":
            continue

        match = pattern.search(item["message"])

        if not match:
            continue

        relation = match.group(1).lower()
        name = match.group(2)

        for pronoun in RELATION_PRONOUNS.get(relation, ()):

            resolved[pronoun] = {
                "name": name,
                "relation": relation,
            }

    return resolved


def analyze(message, history, memory):

    return {
        "follow_up": detect_follow_up(
            message,
            history,
        ),
        "detail_level": detect_detail_level(
            message,
        ),
        "topic": detect_topic(
            history,
        ),
        "active_subject": detect_active_subject(
            history,
        ),
        "conversation_stage": detect_conversation_stage(
            message,
            history,
        ),
        "conversation_intent": detect_conversation_intent(
            message,
        ),
        "question_type": detect_question_type(
            message,
        ),
        "user_goal": detect_user_goal(
            message,
        ),
        "resolved_entities": resolve_entities(
            history,
        ),
        "notes": [],
    }
