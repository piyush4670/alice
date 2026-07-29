import re


def extract(message: str):

    original = message.strip()
    lower = original.lower()

    # -------------------------
    # Add Note
    # -------------------------

    patterns = (
        r"^take a note that (.+)$",
        r"^note that (.+)$",
        r"^save a note (.+)$",
        r"^remember this note (.+)$",
    )

    for pattern in patterns:

        match = re.match(
            pattern,
            original,
            re.IGNORECASE,
        )

        if match:

            return {
                "intent": "note_add",
                "note": match.group(1).strip(),
            }

    # -------------------------
    # List Notes
    # -------------------------

    if lower in (
        "show my notes",
        "list my notes",
        "show notes",
        "list notes",
    ):

        return {
            "intent": "note_list",
        }

    # -------------------------
    # Delete Note
    # -------------------------

    delete = re.match(
        r"^(?:delete|remove) note (\d+)$",
        lower,
    )

    if delete:

        return {
            "intent": "note_delete",
            "index": int(delete.group(1)) - 1,
        }

    return None
