"""Prompt construction and reasoning tests."""

from ai.prompts import build_history, build_memory, build_prompt
from ai.reasoning import analyze, detect_active_subject, detect_topic


def test_memory_is_rendered_as_prose_not_a_python_dict():
    rendered = build_memory({"name": "Piyush", "city": "Kolkata"})

    assert "- name: Piyush" in rendered
    assert "{" not in rendered
    assert "'" not in rendered


def test_history_is_rendered_as_a_transcript():
    history = [
        {"role": "user", "message": "hi"},
        {"role": "assistant", "message": "Hello."},
    ]

    rendered = build_history(history)

    assert "User: hi" in rendered
    assert "ALICE: Hello." in rendered
    assert "{" not in rendered


def test_current_message_is_excluded_from_history():
    """main.py records the message before routing; it must not be echoed."""

    history = [{"role": "user", "message": "explain quantum computing"}]

    rendered = build_history(history, "explain quantum computing")

    assert "explain quantum computing" not in rendered


def test_current_message_is_not_reported_as_the_previous_topic():
    history = [{"role": "user", "message": "explain quantum computing"}]

    assert detect_topic(history, "explain quantum computing") is None
    assert detect_active_subject(history, "explain quantum computing") is None


def test_previous_topic_is_found_when_it_exists():
    history = [
        {"role": "user", "message": "tell me about the solar system"},
        {"role": "assistant", "message": "Sure."},
        {"role": "user", "message": "tell me more"},
    ]

    assert detect_topic(history, "tell me more") == "tell me about the solar system"


def test_prompt_does_not_repeat_the_message_four_times():
    history = [{"role": "user", "message": "explain quantum computing"}]

    reasoning = analyze("explain quantum computing", history, {})

    prompt = build_prompt(history, {}, reasoning, "explain quantum computing")

    assert prompt.count("explain quantum computing") == 1


def test_history_is_budgeted():
    history = [
        {"role": "user", "message": "x" * 500}
        for _ in range(50)
    ]

    rendered = build_history(history)

    assert len(rendered) < 4200


def test_analyze_has_no_dead_fields():
    result = analyze("hello", [], {})

    assert "notes" not in result
    assert result["detail_level"] == "normal"


def test_detail_level_detection():
    assert analyze("explain in detail", [], {})["detail_level"] == "detailed"
    assert analyze("give me a brief summary", [], {})["detail_level"] == "brief"


def test_pronoun_resolution_still_works():
    history = [{"role": "user", "message": "my sister is Riya"}]

    resolved = analyze("where does she study", history, {})["resolved_entities"]

    assert resolved["she"]["name"] == "Riya"
    assert resolved["she"]["relation"] == "sister"
