"""Triage: is this a chat message or a mission?

One responsibility: classify an incoming message so the server knows
whether to answer it directly or hand it to the mission engine.
"""

import re

MISSION_PREFIX = re.compile(r"^(?:mission|task)\s*[:,]\s*(.+)$", re.IGNORECASE | re.DOTALL)

# Verbs that usually open a multi-step request.
MISSION_VERBS = (
    "research ",
    "investigate ",
    "plan ",
    "build ",
    "create ",
    "prepare ",
    "organise ",
    "organize ",
    "write ",
    "draft ",
    "analyse ",
    "analyze ",
    "compare ",
    "gather ",
    "set up ",
    "put together ",
    "design ",
    "find out ",
    "look into ",
    "make me ",
    "make a ",
    "help me ",
)

CONNECTORS = (
    " and then ",
    " then ",
    " after that ",
    "; ",
    " and also ",
    " step by step ",
)


def strip_mission_prefix(message: str):
    """Return (goal, was_explicit)."""

    match = MISSION_PREFIX.search(message.strip())

    if match:
        return match.group(1).strip(), True

    return message.strip(), False


def looks_like_mission(message: str) -> bool:

    goal, explicit = strip_mission_prefix(message)

    if explicit:
        return True

    lowered = goal.lower()

    if any(lowered.startswith(verb) for verb in MISSION_VERBS):
        return True

    if any(connector in lowered for connector in CONNECTORS):

        # A connector only counts when an actionable verb opens the message.
        return any(lowered.startswith(verb) for verb in MISSION_VERBS) or any(
            connector in lowered for connector in (" and then ", " after that ", "; ")
        )

    return False
