import json
from pathlib import Path

from ai.extractor import extract

from core.response import success, error


REMINDER_FILE = Path("data/reminders.json")


def load_reminders():

    if not REMINDER_FILE.exists():
        return []

    try:
        with open(REMINDER_FILE, "r") as file:
            return json.load(file)
    except Exception:
        return []


def save_reminders(reminders):

    REMINDER_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(REMINDER_FILE, "w") as file:
        json.dump(
            reminders,
            file,
            indent=4,
        )


def add(reminder):

    reminders = load_reminders()

    for existing in reminders:

        if (
            existing.get("task") == reminder.get("task")
            and existing.get("time") == reminder.get("time")
        ):
            return False

    reminders.append(reminder)

    save_reminders(reminders)

    return True


def list_all():

    reminders = load_reminders()

    return success(
        reminders,
        source="reminder",
        data=reminders,
    )


def remove(index):

    reminders = load_reminders()

    if index < 0 or index >= len(reminders):
        return error(
            "Reminder not found.",
            source="reminder",
        )

    removed = reminders.pop(index)

    save_reminders(reminders)

    return success(
        f"Removed reminder: {removed}",
        source="reminder",
    )


def handle(message: str):

    data = extract(message)

    if data is None:
        return error(
            "I couldn't understand that reminder request.",
            source="reminder",
        )

    if data["intent"] == "reminder_add":

        if add(
            {
                "task": data["task"],
                "time": data["time"],
            }
        ):
            return success(
                "Reminder saved.",
                source="reminder",
            )

        return success(
            "That reminder already exists.",
            source="reminder",
        )

    if data["intent"] == "reminder_list":

        reminders = list_all()

        if not reminders.data:
            return success(
                "You don't have any reminders.",
                source="reminder",
            )

        lines = []

        for index, reminder in enumerate(reminders.data, start=1):

            task = reminder.get("task", "Unknown")
            reminder_time = reminder.get("time")

            if reminder_time:
                lines.append(f"{index}. {task} ({reminder_time})")
            else:
                lines.append(f"{index}. {task}")

        return success(
            "\n".join(lines),
            source="reminder",
        )

    if data["intent"] == "reminder_delete":

        return remove(data["index"])

    return error(
        "Unknown reminder operation.",
        source="reminder",
    )
