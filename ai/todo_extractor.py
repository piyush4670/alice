import re


def extract(message: str):

    original = message.strip()
    lower = original.lower()

    # -------------------------
    # Add Task
    # -------------------------

    patterns = (
        r"^add task (.+)$",
        r"^add a task (.+)$",
        r"^todo (.+)$",
        r"^to do (.+)$",
        r"^remember task (.+)$",
    )

    for pattern in patterns:

        match = re.match(
            pattern,
            original,
            re.IGNORECASE,
        )

        if match:

            return {
                "intent": "todo_add",
                "task": match.group(1).strip(),
            }

    # -------------------------
    # List Tasks
    # -------------------------

    if lower in (
        "show my tasks",
        "list my tasks",
        "show tasks",
        "list tasks",
        "show todo",
        "show to do",
    ):

        return {
            "intent": "todo_list",
        }

    # -------------------------
    # Complete Task
    # -------------------------

    complete = re.match(
        r"^complete task (\d+)$",
        lower,
    )

    if complete:

        return {
            "intent": "todo_complete",
            "index": int(complete.group(1)) - 1,
        }

    # -------------------------
    # Delete Task
    # -------------------------

    delete = re.match(
        r"^(?:delete|remove) task (\d+)$",
        lower,
    )

    if delete:

        return {
            "intent": "todo_delete",
            "index": int(delete.group(1)) - 1,
        }

    return None
