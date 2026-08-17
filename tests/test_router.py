"""End-to-end routing tests through the public route() entry point."""

import pytest

from core.models import Response
from core.router import route


@pytest.mark.parametrize(
    "message",
    [
        "hello",
        "bye",
        "what is the time",
        "2+2",
        "my name is Piyush",
        "what is my name",
        "remind me to call mom at 5pm",
        "show my reminders",
        "note that the sky is blue",
        "add task write the report",
        "show my tasks",
        "",
    ],
)
def test_every_route_returns_a_valid_response(message):
    reply = route(message)

    assert isinstance(reply, Response)
    assert isinstance(reply.message, str)
    assert reply.message
    assert isinstance(reply.success, bool)


def test_calculator_through_the_router():
    assert "4" in route("what is 2+2").message


def test_calculator_attack_through_the_router():
    reply = route("calculate (1).__class__.__mro__[1].__subclasses__()")

    assert reply.success is False
    assert "class" not in reply.message


def test_memory_through_the_router():
    route("my name is Piyush")

    assert "Piyush" in route("what is my name").message


def test_greeting_prefixed_calculation_through_the_router():
    assert "10" in route("hey can you calculate 5+5").message


def test_ai_without_a_key_gives_a_clear_message(monkeypatch):
    import core.config as config

    monkeypatch.setattr(config, "API_KEY", None)

    reply = route("tell me about the solar system")

    assert reply.success is False
    assert "API_KEY" in reply.message or "isn't configured" in reply.message


def test_router_never_raises_on_odd_input():
    for message in ["???", "!!!", "a" * 5000, "🙂", "1/0", "my  is  "]:
        assert isinstance(route(message), Response)
