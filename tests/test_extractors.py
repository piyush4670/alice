import pytest

from ai.memory_extractor import extract as extract_memory
from ai.notes_extractor import extract as extract_notes
from ai.reminder_extractor import extract as extract_reminder
from ai.todo_extractor import extract as extract_todo


# ---------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------


@pytest.mark.parametrize(
    "message, task, when",
    [
        ("remind me to call mom at 5pm", "call mom", "5pm"),
        ("remind me to call mom tomorrow", "call mom", "tomorrow"),
        ("remind me to call mom tomorrow at 5pm", "call mom", "tomorrow 5pm"),
        # The first 'at' must not split the task.
        (
            "remind me to look at the report at 5pm",
            "look at the report",
            "5pm",
        ),
        ("remind me to buy milk", "buy milk", None),
        ("remind me to submit the form today", "submit the form", "today"),
        ("remind me to pay rent at 09:00", "pay rent", "09:00"),
    ],
)
def test_reminder_time_parsing(message, task, when):
    result = extract_reminder(message)

    assert result["intent"] == "reminder_add"
    assert result["task"] == task
    assert result["time"] == when


def test_reminder_list_and_delete():
    assert extract_reminder("show my reminders")["intent"] == "reminder_list"
    assert extract_reminder("delete reminder 2") == {
        "intent": "reminder_delete",
        "index": 1,
    }


# ---------------------------------------------------------------
# Memory
# ---------------------------------------------------------------


@pytest.mark.parametrize(
    "message, key, value",
    [
        ("my name is Piyush", "name", "Piyush"),
        ("I live in Kolkata", "city", "Kolkata"),
        ("my favourite colour is blue", "favourite colour", "blue"),
        ("My Favorite Color is blue", "favourite colour", "blue"),
        ("my birthday is 5 May", "birthday", "5 May"),
        ("I am a student", "about me", "a student"),
        ("remember that my locker code is 4417", "locker code", "4417"),
    ],
)
def test_memory_stores_real_facts(message, key, value):
    result = extract_memory(message)

    assert result["intent"] == "remember"
    assert result["key"] == key
    assert result["value"] == value


@pytest.mark.parametrize(
    "message",
    [
        # Ordinary conversation must never become a stored fact.
        "my biggest problem right now is that python is hard",
        "my question is why is the sky blue",
        "my code is not working",
        "my issue is that the app crashes",
        "I am tired",
        "I am planning a trip",
        "I am thinking about it",
        "I am not sure",
        "my understanding is that it works",
    ],
)
def test_memory_ignores_conversation(message):
    assert extract_memory(message) is None


@pytest.mark.parametrize(
    "message, key",
    [
        ("what is my name", "name"),
        ("what is my name?", "name"),
        ("where is my city", "city"),
        ("what is my birth date", "birthday"),
        ("what's my favourite colour", "favourite colour"),
    ],
)
def test_memory_recall(message, key):
    assert extract_memory(message) == {"intent": "recall", "key": key}


def test_memory_forget_and_list():
    assert extract_memory("forget my name") == {
        "intent": "forget",
        "key": "name",
    }
    assert extract_memory("what do you know about me")["intent"] == "list"


# ---------------------------------------------------------------
# Notes and to-dos
# ---------------------------------------------------------------


def test_notes():
    assert extract_notes("note that the sky is blue") == {
        "intent": "note_add",
        "note": "the sky is blue",
    }
    assert extract_notes("show my notes")["intent"] == "note_list"
    assert extract_notes("delete note 3")["index"] == 2


def test_todos():
    assert extract_todo("add task write the report") == {
        "intent": "todo_add",
        "task": "write the report",
    }
    assert extract_todo("show my tasks")["intent"] == "todo_list"
    assert extract_todo("complete task 1")["index"] == 0
    assert extract_todo("delete task 2")["index"] == 1
