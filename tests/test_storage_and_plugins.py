"""Persistence tests, including the first-run crash."""

import json

import pytest

from core.models import Response
from memory.manager import all_memory, forget, handle as memory_handle, recall, remember
from memory.storage import load_memory, save_memory
from plugins.notes import handle as notes_handle, list_all as notes_list
from plugins.reminder import handle as reminder_handle, list_all as reminder_list
from plugins.todo import handle as todo_handle, list_all as todo_list


def test_saving_memory_creates_missing_directory(isolated_data, monkeypatch):
    """The first-run FileNotFoundError: data/ does not exist in a fresh clone."""

    import memory.storage as storage

    target = isolated_data / "nested" / "deep" / "profile.json"
    monkeypatch.setattr(storage, "MEMORY_FILE", target)

    storage.save_memory({"name": "Piyush"})

    assert target.exists()
    assert json.loads(target.read_text())["name"] == "Piyush"


def test_first_message_of_a_new_user_does_not_crash():
    reply = memory_handle("my name is Piyush")

    assert reply.success
    assert "name" in reply.message


def test_corrupt_memory_file_degrades_gracefully(isolated_data, monkeypatch):
    import memory.storage as storage

    target = isolated_data / "profile.json"
    target.write_text("{ not json at all")
    monkeypatch.setattr(storage, "MEMORY_FILE", target)

    assert storage.load_memory() == {}


def test_memory_round_trip():
    assert remember("name", "Piyush") == "created"
    assert remember("name", "Piyush") == "unchanged"
    assert remember("name", "Alice") == "updated"
    assert recall("name") == "Alice"
    assert forget("name") is True
    assert forget("name") is False


def test_memory_recall_after_alias_normalisation():
    memory_handle("My Favorite Color is blue")
    reply = memory_handle("what is my favourite colour")

    assert "blue" in reply.message


# ---------------------------------------------------------------
# The message/data contract
# ---------------------------------------------------------------


@pytest.mark.parametrize(
    "list_function",
    [reminder_list, notes_list, todo_list],
)
def test_list_message_is_always_a_string(list_function):
    """message was previously assigned a raw list, violating Response."""

    reply = list_function()

    assert isinstance(reply, Response)
    assert isinstance(reply.message, str)
    assert isinstance(reply.data, list)


def test_reminder_lifecycle():
    assert reminder_handle("remind me to call mom at 5pm").success

    listed = reminder_handle("show my reminders")
    assert "call mom" in listed.message
    assert "5pm" in listed.message
    assert isinstance(listed.message, str)

    duplicate = reminder_handle("remind me to call mom at 5pm")
    assert "already exists" in duplicate.message

    removed = reminder_handle("delete reminder 1")
    assert removed.success
    assert "call mom" in removed.message

    assert "don't have any" in reminder_handle("show my reminders").message


def test_notes_lifecycle():
    assert notes_handle("note that the sky is blue").success

    listed = notes_handle("show my notes")
    assert "1. the sky is blue" in listed.message

    assert notes_handle("delete note 1").success
    assert "don't have any" in notes_handle("show my notes").message


def test_todo_lifecycle():
    assert todo_handle("add task write the report").success

    listed = todo_handle("show my tasks")
    assert "[ ] write the report" in listed.message

    assert todo_handle("complete task 1").success
    assert "[x] write the report" in todo_handle("show my tasks").message

    assert "already completed" in todo_handle("complete task 1").message
    assert todo_handle("delete task 1").success


@pytest.mark.parametrize(
    "handler, message",
    [
        (reminder_handle, "delete reminder 99"),
        (notes_handle, "delete note 99"),
        (todo_handle, "delete task 99"),
        (todo_handle, "complete task 99"),
    ],
)
def test_out_of_range_deletes_are_handled(handler, message):
    reply = handler(message)

    assert reply.success is False
    assert "couldn't find" in reply.message
