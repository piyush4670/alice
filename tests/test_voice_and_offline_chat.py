"""Voice endpoints + offline conversation improvements."""

from agent.local_brain import LocalBrain, _canned_reply, _offline_help
from voice.tts import clean_for_speech


def test_canned_who_are_you():
    reply = _canned_reply("who are you", "who are you", {})
    assert reply and "ALICE" in reply


def test_canned_what_can_you_do():
    reply = _canned_reply("what can you do", "what can you do", {})
    assert reply and "mission" in reply.lower()


def test_canned_thanks():
    reply = _canned_reply("thanks alice", "thanks alice", {"name": "Piyush"})
    assert reply and "Piyush" in reply


def test_offline_help_never_says_brain_unavailable():
    text = _offline_help("explain quantum computing please")
    assert "unavailable" not in text.lower()
    assert "API_KEY" in text or "api key" in text.lower()
    assert "quantum" in text.lower() or "explain" in text.lower()


def test_local_brain_converse_identity():
    brain = LocalBrain()
    chunks = list(brain.converse("who are you?", [], {}))
    assert chunks and "ALICE" in chunks[0]


def test_local_brain_converse_help():
    brain = LocalBrain()
    chunks = list(brain.converse("what can you do?", [], {}))
    assert chunks and "remind" in chunks[0].lower()


def test_local_brain_open_ended_is_helpful():
    brain = LocalBrain()
    chunks = list(brain.converse("write me a poem about the moon", [], {}))
    joined = "".join(chunks).lower()
    assert "unavailable" not in joined
    assert "api" in joined or "mission" in joined


def test_clean_for_speech_strips_markdown():
    raw = "**Hello** Boss 💙 — see [docs](https://x.test) and `code`."
    out = clean_for_speech(raw)
    assert "Hello" in out
    assert "💙" not in out
    assert "**" not in out
    assert "https" not in out


def test_fallback_local_on_linked_failure(monkeypatch):
    """When the linked brain raises, conversation falls back to local."""

    from agent.conversation import _reply_with_brain

    class BoomBrain:
        mode = "linked"
        label = "broken"
        last_side_effects = []

        def converse(self, message, history, memory):
            raise RuntimeError("provider down")
            yield  # make it a generator  # noqa: unreachable

    events = []
    monkeypatch.setattr("agent.conversation.get_history", lambda: [])
    monkeypatch.setattr("agent.conversation.memory.all_memory", lambda: {})
    monkeypatch.setattr("agent.conversation.add_message", lambda *a, **k: None)

    _reply_with_brain("who are you", events.append, BoomBrain())

    done = [e for e in events if e.get("type") == "chat.done"]
    assert done
    assert "ALICE" in done[0]["message"]
    assert "unavailable" not in done[0]["message"].lower()


def test_transcribe_rejects_empty():
    from voice.transcribe import TranscribeError, transcribe
    import pytest

    with pytest.raises(TranscribeError):
        transcribe(b"", "audio/webm")


def test_transcribe_requires_key(monkeypatch):
    from voice import transcribe as mod
    import pytest

    monkeypatch.setattr(mod, "has_api_key", lambda: False)

    with pytest.raises(mod.TranscribeError, match="API key"):
        mod.transcribe(b"x" * 200, "audio/webm")
