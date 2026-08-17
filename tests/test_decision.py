"""Routing tests.

Every misroute documented in docs/ANALYSIS.md is pinned here.
"""

import pytest

from core.decision import decide


def route_of(message):
    return decide(message).destination


@pytest.mark.parametrize(
    "message",
    ["hello", "hi", "hey", "Hello!", "good morning", "HI", "hey!"],
)
def test_pure_greetings(message):
    assert route_of(message) == "greeting"


@pytest.mark.parametrize(
    "message, expected",
    [
        # A greeting prefix must not swallow the real request.
        ("hey can you calculate 5+5", "calculator"),
        ("hello what is my name", "memory_recall"),
        ("hi, remind me to call mom at 5pm", "reminder"),
        ("hey what is the time", "time"),
        ("hello show my tasks", "todo"),
    ],
)
def test_greeting_prefix_does_not_swallow_request(message, expected):
    assert route_of(message) == expected


@pytest.mark.parametrize(
    "message, expected",
    [
        ("can you calculate 5+5", "calculator"),
        ("please show my tasks", "todo"),
        ("could you tell me the time", "time"),
    ],
)
def test_polite_wrappers_are_stripped(message, expected):
    assert route_of(message) == expected


@pytest.mark.parametrize(
    "message",
    ["bye", "goodbye", "exit", "quit", "Bye!", "good night"],
)
def test_exit(message):
    assert route_of(message) == "goodbye"


@pytest.mark.parametrize(
    "message",
    [
        "what is the time",
        "what's the time",
        "what time is it",
        "tell me the time",
        "what is the date",
        "what is today's date",
        "what day is it",
    ],
)
def test_genuine_time_requests(message):
    assert route_of(message) == "time"


@pytest.mark.parametrize(
    "message, expected",
    [
        # The substring bug: these all wrongly hit the time plugin before.
        ("remind me to call mom at 5 pm today", "reminder"),
        ("note that the meeting is today", "notes"),
        ("add task finish the report on time", "todo"),
        ("what is my birth date", "memory_recall"),
        ("what's the best time to visit Japan", "ai"),
        ("add task update the date field", "todo"),
        ("how do I update my profile", "ai"),
    ],
)
def test_time_keywords_do_not_hijack_routing(message, expected):
    assert route_of(message) == expected


@pytest.mark.parametrize(
    "message",
    ["calculate 5*3", "2+2", "what is 2+2", "10 / 4", "(2+3)*4", "5 - 3"],
)
def test_calculator(message):
    assert route_of(message) == "calculator"


@pytest.mark.parametrize(
    "message",
    [
        "I have 5 apples - is that enough?",
        "what is the best laptop",
        "tell me about python",
    ],
)
def test_conversation_goes_to_ai(message):
    assert route_of(message) == "ai"


@pytest.mark.parametrize(
    "message, expected",
    [
        ("my name is Piyush", "memory_learn"),
        ("what is my name", "memory_recall"),
        ("forget my name", "memory_forget"),
        ("what do you know about me", "memory_list"),
        ("remind me to buy milk", "reminder"),
        ("show my reminders", "reminder"),
        ("delete reminder 1", "reminder"),
        ("note that the sky is blue", "notes"),
        ("show my notes", "notes"),
        ("add task write the report", "todo"),
        ("show my tasks", "todo"),
        ("complete task 1", "todo"),
    ],
)
def test_structured_intents(message, expected):
    assert route_of(message) == expected


def test_empty_message():
    assert route_of("") == "empty"
    assert route_of("   ") == "empty"


def test_intent_is_returned_so_handlers_need_not_reparse():
    decision = decide("my name is Piyush")

    assert decision.intent is not None
    assert decision.intent["intent"] == "remember"
    assert decision.intent["value"] == "Piyush"


def test_greeting_prefix_is_stripped_from_forwarded_message():
    decision = decide("hey what is the time")

    assert decision.message == "what is the time"
