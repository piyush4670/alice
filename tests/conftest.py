import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Point every store at a temp directory so tests never touch real data."""

    import core.config as config
    import memory.storage as storage
    import plugins.notes as notes
    import plugins.reminder as reminder
    import plugins.todo as todo

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "MEMORY_FILE", tmp_path / "profile.json")
    monkeypatch.setattr(config, "REMINDER_FILE", tmp_path / "reminders.json")
    monkeypatch.setattr(config, "NOTES_FILE", tmp_path / "notes.json")
    monkeypatch.setattr(config, "TODO_FILE", tmp_path / "todos.json")

    monkeypatch.setattr(storage, "MEMORY_FILE", tmp_path / "profile.json")
    monkeypatch.setattr(reminder, "REMINDER_FILE", tmp_path / "reminders.json")
    monkeypatch.setattr(notes, "NOTES_FILE", tmp_path / "notes.json")
    monkeypatch.setattr(todo, "TODO_FILE", tmp_path / "todos.json")

    yield tmp_path


@pytest.fixture(autouse=True)
def clean_context():
    from core.context import clear_history

    clear_history()
    yield
    clear_history()
