import json
from pathlib import Path

from ai.extractor import extract

from core.response import success, error


NOTES_FILE = Path("data/notes.json")


def load_notes():

    if not NOTES_FILE.exists():
        return []

    try:
        with open(NOTES_FILE, "r") as file:
            return json.load(file)
    except Exception:
        return []


def save_notes(notes):

    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(NOTES_FILE, "w") as file:
        json.dump(
            notes,
            file,
            indent=4,
        )


def add(note: str):

    note = note.strip()

    notes = load_notes()

    if note in notes:
        return False

    notes.append(note)

    save_notes(notes)

    return True


def list_all():

    notes = load_notes()

    return success(
        notes,
        source="notes",
        data=notes,
    )


def remove(index):

    notes = load_notes()

    if index < 0 or index >= len(notes):
        return error(
            "Note not found.",
            source="notes",
        )

    removed = notes.pop(index)

    save_notes(notes)

    return success(
        f"Removed note: {removed}",
        source="notes",
    )


def handle(message: str):

    data = extract(message)

    if data is None:

        return error(
            "I couldn't understand that note request.",
            source="notes",
        )

    if data["intent"] == "note_add":

        if add(data["note"]):

            return success(
                "Note saved.",
                source="notes",
            )

        return success(
            "That note already exists.",
            source="notes",
        )

    if data["intent"] == "note_list":

        notes = list_all()

        if not notes.data:

            return success(
                "You don't have any notes.",
                source="notes",
            )

        lines = []

        for index, note in enumerate(notes.data, start=1):
            lines.append(f"{index}. {note}")

        return success(
            "\n".join(lines),
            source="notes",
        )

    if data["intent"] == "note_delete":

        return remove(data["index"])

    return error(
        "Unknown note operation.",
        source="notes",
    )
