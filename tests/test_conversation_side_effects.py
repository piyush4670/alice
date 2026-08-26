"""Regression tests: chat replies can carry side-effect events.

A voice/typed single command like "open arxiv.org" should both answer in
chat AND emit a `web.open` event (the local brain records the side-effect
and the conversation module forwards it).
"""

from agent.conversation import _reply_with_brain
from agent.local_brain import LocalBrain


def test_reply_with_brain_forwards_web_open(monkeypatch):
    events = []

    brain = LocalBrain()

    monkeypatch.setattr(
        "agent.conversation.get_history", lambda: []
    )
    monkeypatch.setattr(
        "agent.conversation.memory.all_memory", lambda: {}
    )
    monkeypatch.setattr(
        "agent.conversation.add_message", lambda *a, **k: None
    )

    _reply_with_brain("open arxiv.org", events.append, brain)

    assert any(e["type"] == "web.open" and e["url"] == "https://arxiv.org" for e in events)
    # A chat.done should still be emitted so the stream finishes cleanly.
    assert any(e["type"] == "chat.done" for e in events)


def test_converse_runs_calculator_tool():
    brain = LocalBrain()
    chunks = list(brain.converse("calculate 2+2", [], {}))
    assert chunks and "4" in chunks[0]
