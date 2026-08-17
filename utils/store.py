"""Shared JSON list storage.

Reminders, notes and to-dos all persist a JSON list. That loading and
saving logic lived in three places; it lives here now. This is a shared
utility, not a plugin, so plugins stay independent of one another.
"""

import json
import os
import tempfile


def load_list(path):

    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

    except (OSError, ValueError):
        return []

    if not isinstance(data, list):
        return []

    return data


def save_list(path, items):
    """Write atomically so an interrupted save cannot corrupt the file."""

    path.parent.mkdir(parents=True, exist_ok=True)

    handle, temporary_path = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
    )

    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(items, file, indent=4, ensure_ascii=False)

        os.replace(temporary_path, path)

    except BaseException:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)

        raise


def valid_index(index, items) -> bool:

    if not isinstance(index, int):
        return False

    return 0 <= index < len(items)
