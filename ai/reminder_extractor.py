import re


def extract(message: str):

    original = message.strip()
    lower = original.lower()

    # -------------------------
    # Add Reminder
    # -------------------------

    patterns = (
        r"^remind me to (.+?) at (.+)$",
        r"^remind me to (.+?) on (.+)$",
        r"^remind me to (.+?) tomorrow(?: at (.+))?$",
        r"^remind me to (.+)$",
    )

    for pattern in patterns:

        match = re.match(
            pattern,
            original,
            re.IGNORECASE,
        )

        if not match:
            continue

        task = match.group(1).strip()

        reminder_time = None

        if len(match.groups()) > 1:
            reminder_time = match.group(2)

        if reminder_time:
            reminder_time = reminder_time.strip()

        return {
            "intent": "reminder_add",
            "task": task,
            "time": reminder_time,
        }

    # -------------------------
    # List Reminders
    # -------------------------

    if lower in (
        "show my reminders",
        "list my reminders",
        "show reminders",
        "list reminders",
    ):

        return {
            "intent": "reminder_list",
        }

    # -------------------------
    # Delete Reminder
    # -------------------------

    delete = re.match(
        r"^(?:delete|remove) reminder (\d+)$",
        lower,
    )

    if delete:

        return {
            "intent": "reminder_delete",
            "index": int(delete.group(1)) - 1,
        }

    return None
