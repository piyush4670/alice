from collections import deque

from core.config import MAX_HISTORY

_history = deque(maxlen=MAX_HISTORY)


def add_message(role: str, message: str):
    _history.append({
        "role": role,
        "message": message,
    })


def get_history():
    return list(_history)


def clear_history():
    _history.clear()


def history_size():
    return len(_history)
