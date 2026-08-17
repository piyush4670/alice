from ai.extractor import extract
from core.config import NOTES_FILE
from core.response import error, success
from utils.store import load_list, save_list, valid_index


def load_notes():
    return load_list(NOTES_FILE)


def save_notes(notes):
    save_list(NOTES_FILE, notes)


def add(note: str) -> bool:

    note = note.strip()

    if not note:
        return False

    notes = load_notes()

    for existing in notes:

        if str(existing).lower() == note.lower():
            return False

    notes.append(note)

    save_notes(notes)

    return True


def format_all(notes) -> str:

    lines = [
        f"{number}. {note}"
        for number, note in enumerate(notes, start=1)
    ]

    return "\n".join(lines)


def list_all():
    """Return a printable message plus the structured list in data."""

    notes = load_notes()

    if not notes:
        return success(
            "You don't have any notes.",
            source="notes",
            data=[],
        )

    return success(
        format_all(notes),
        source="notes",
        data=notes,
    )


def remove(index):

    notes = load_notes()

    if not valid_index(index, notes):
        return error(
            "I couldn't find that note.",
            source="notes",
        )

    removed = notes.pop(index)

    save_notes(notes)

    return success(
        f"Removed note: {removed}",
        source="notes",
    )


def handle(message: str, intent: dict = None):

    data = intent if intent is not None else extract(message)

    if data is None:
        return error(
            "I couldn't understand that note request.",
            source="notes",
        )

    name = data.get("intent")

    if name == "note_add":

        if add(data["note"]):
            return success("Note saved.", source="notes")

        return success("That note already exists.", source="notes")

    if name == "note_list":
        return list_all()

    if name == "note_delete":
        return remove(data["index"])

    return error("Unknown note operation.", source="notes")
