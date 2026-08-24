"""Tests for the agent layer: tools, triage, local brain and the engine."""

from agent.brain import (
    ACTION_REPLY,
    ACTION_TOOL,
    Brain,
)
from agent.engine import MissionEngine
from agent.local_brain import LocalBrain, classify, fragment_goal
from agent.models import TASK_DONE, Task
from agent.triage import looks_like_mission, strip_mission_prefix
from tools import registry


# ===========
# Tool registry
# ===========

def test_calculator_tool():

    result = registry.execute("calculator", {"expression": "(3 + 4) * 2"})

    assert result.ok
    assert "= 14" in result.output


def test_unknown_tool_is_an_observation():

    result = registry.execute("does_not_exist", {})

    assert not result.ok
    assert "Unknown tool" in result.output


def test_bad_arguments_do_not_raise():

    result = registry.execute("calculator", {"expression": None})

    assert not result.ok


def test_write_file_creates_artifact():

    result = registry.execute(
        "write_file",
        {"name": "report", "body": "hello"},
    )

    assert result.ok
    assert result.data["artifact"]["name"] == "report.md"


def test_write_file_name_cannot_escape_workspace():

    result = registry.execute(
        "write_file",
        {"name": "../../etc/evil", "body": "no"},
    )

    assert result.ok
    assert ".." not in result.data["artifact"]["name"]


def test_schema_lists_every_tool():

    names = {item["name"] for item in registry.schema()}

    assert {"calculator", "web_search", "wikipedia", "add_reminder", "list_todos"} <= names


# ===========
# Triage
# ===========

def test_mission_prefix_is_stripped():

    goal, explicit = strip_mission_prefix("mission: plan my week")

    assert goal == "plan my week"
    assert explicit


def test_simple_questions_stay_chat():

    assert not looks_like_mission("what is my name?")
    assert not looks_like_mission("what is 2+2")
    assert not looks_like_mission("hello")


def test_big_requests_become_missions():

    assert looks_like_mission("research the mars rover programme")
    assert looks_like_mission("write a report on solar power and then save it")
    assert looks_like_mission("mission: organise my week")


# ===========
# Local brain
# ===========

def test_classify_reminder():

    hint, payload = classify("remind me to call mom tomorrow at 5pm")

    assert hint == "reminder"
    assert "call mom" in payload


def test_classify_math_beats_wikipedia():

    hint, payload = classify("what is 2 + 2")

    assert hint == "calculator"
    assert payload == "2 + 2"


def test_fragment_goal_splits_intents():

    fragments = fragment_goal(
        "calculate 5*5 and then note that the test passed"
    )

    assert len(fragments) == 2


def test_local_brain_plans_multiple_steps():

    brain = LocalBrain()

    plan = brain.plan(
        "remind me to hydrate at 6pm and add task finish the report",
        memory={},
    )

    titles = [step["title"] for step in plan.steps]

    assert any("reminder" in title.lower() for title in titles)
    assert any("to-do" in title.lower() for title in titles)


def test_local_brain_summarises_done_steps():

    brain = LocalBrain()

    summary = brain.summarize(
        {"done": [{"title": "Save the reminder", "result": "Reminder saved."}]}
    )

    assert "Reminder saved" in summary


# ===========
# Engine
# ===========

class BrokenBrain(Brain):
    """Simulates a linked brain that cannot be reached."""

    mode = "linked"

    def plan(self, goal, memory):
        raise RuntimeError("provider down")

    def act(self, context):
        raise RuntimeError("provider down")

    def reflect(self, context):
        raise RuntimeError("provider down")

    def summarize(self, context):
        raise RuntimeError("provider down")

    def converse(self, message, history, memory):
        raise RuntimeError("provider down")


def test_engine_completes_local_mission():

    events = []
    engine = MissionEngine(lambda event: events.append(event))

    task = Task(goal="calculate 40 + 2")

    engine.run(task, ask=lambda t, q: None, cancelled=lambda: False, brain=LocalBrain())

    assert task.status == TASK_DONE
    assert any("42" in step.result for step in task.steps)

    kinds = {event["type"] for event in events}

    assert "task.snapshot" in kinds
    assert "task.delta" in kinds


def test_engine_falls_back_when_linked_brain_dies():

    engine = MissionEngine(lambda event: None)

    task = Task(goal="calculate 40 + 2")

    engine.run(task, ask=lambda t, q: None, cancelled=lambda: False, brain=BrokenBrain())

    assert task.status == TASK_DONE
    assert any("42" in step.result for step in task.steps)


def test_engine_records_artifacts():

    events = []
    engine = MissionEngine(lambda event: events.append(event))

    task = Task(goal="note that artefacts work")

    engine.run(task, ask=lambda t, q: None, cancelled=lambda: False, brain=LocalBrain())

    assert task.status == TASK_DONE


def test_local_brain_act_returns_tool_first_then_reply():

    brain = LocalBrain()

    context = {
        "goal": "calculate 2*21",
        "step": {"title": "Run the calculation", "detail": "calculate 2*21", "tool_hint": "calculator"},
        "done": [],
        "tool_log": [],
        "round": 1,
    }

    first = brain.act(context)

    assert first.kind == ACTION_TOOL
    assert first.tool == "calculator"

    context["tool_log"] = [{"tool": "calculator", "args": {}, "ok": True, "output": "2*21 = 42"}]

    second = brain.act(context)

    assert second.kind == ACTION_REPLY
    assert "42" in second.text
