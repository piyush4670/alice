import json
import os
import tempfile

from core.config import MEMORY_FILE


def load_memory():

    if not MEMORY_FILE.exists():
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

    except (OSError, ValueError):
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def save_memory(memory):
    """Write memory atomically so a crash can never truncate the profile."""

    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    handle, temporary_path = tempfile.mkstemp(
        dir=str(MEMORY_FILE.parent),
        suffix=".tmp",
    )

    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(memory, file, indent=4, ensure_ascii=False)

        os.replace(temporary_path, MEMORY_FILE)

    except BaseException:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)

        raise
