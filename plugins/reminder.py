from ai.extractor import extract
from core.config import REMINDER_FILE
from core.response import error, success
from utils.store import load_list, save_list, valid_index


def load_reminders():
    return load_list(REMINDER_FILE)


def save_reminders(reminders):
    save_list(REMINDER_FILE, reminders)


def add(reminder) -> bool:

    reminders = load_reminders()

    for existing in reminders:

        same_task = existing.get("task", "").lower() == reminder["task"].lower()
        same_time = existing.get("time") == reminder["time"]

        if same_task and same_time:
            return False

    reminders.append(reminder)

    save_reminders(reminders)

    return True


def format_reminder(index: int, reminder: dict) -> str:

    task = reminder.get("task", "Unknown")

    when = reminder.get("time")

    if when:
        return f"{index}. {task} ({when})"

    return f"{index}. {task}"


def format_all(reminders) -> str:

    lines = [
        format_reminder(number, reminder)
        for number, reminder in enumerate(reminders, start=1)
    ]

    return "\n".join(lines)


def list_all():
    """Return a printable message plus the structured list in data."""

    reminders = load_reminders()

    if not reminders:
        return success(
            "You don't have any reminders.",
            source="reminder",
            data=[],
        )

    return success(
        format_all(reminders),
        source="reminder",
        data=reminders,
    )


def remove(index):

    reminders = load_reminders()

    if not valid_index(index, reminders):
        return error(
            "I couldn't find that reminder.",
            source="reminder",
        )

    removed = reminders.pop(index)

    save_reminders(reminders)

    return success(
        f"Removed reminder: {removed.get('task', 'Unknown')}",
        source="reminder",
    )


def handle(message: str, intent: dict = None):

    data = intent if intent is not None else extract(message)

    if data is None:
        return error(
            "I couldn't understand that reminder request.",
            source="reminder",
        )

    name = data.get("intent")

    if name == "reminder_add":

        added = add({
            "task": data["task"],
            "time": data.get("time"),
        })

        if added:
            return success("Reminder saved.", source="reminder")

        return success("That reminder already exists.", source="reminder")

    if name == "reminder_list":
        return list_all()

    if name == "reminder_delete":
        return remove(data["index"])

    return error("Unknown reminder operation.", source="reminder")
