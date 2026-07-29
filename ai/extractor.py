from ai.memory_extractor import extract as extract_memory
from ai.reminder_extractor import extract as extract_reminder
from ai.notes_extractor import extract as extract_notes
from ai.todo_extractor import extract as extract_todo


EXTRACTORS = (
    extract_memory,
    extract_reminder,
    extract_notes,
    extract_todo,
)


def extract(message: str):

    for extractor in EXTRACTORS:

        result = extractor(message)

        if result is not None:
            return result

    return None
