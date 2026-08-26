"""Regression tests: the offline brain routes browser goals to open_website."""

from agent.local_brain import LocalBrain, classify


def test_classify_open_browser_domain():
    hint, payload = classify("open arxiv.org in the browser")
    assert hint == "browser"
    assert payload == "arxiv.org"


def test_classify_go_to_site():
    hint, payload = classify("go to youtube")
    assert hint == "browser"
    assert payload == "youtube"


def test_classify_open_wikipedia():
    hint, payload = classify("open wikipedia")
    assert hint == "browser"
    assert payload == "wikipedia"


def test_classify_browser_default_maps_to_duckduckgo():
    hint, payload = classify("open the web deck")
    assert hint == "browser"
    assert payload == "duckduckgo"


def test_plan_builds_browser_step():
    brain = LocalBrain()
    plan = brain.plan("open arxiv.org in the browser", {})
    assert plan.steps
    assert plan.steps[0]["tool_hint"] == "browser"


def test_act_uses_open_website_tool():
    from agent.brain import ACTION_TOOL

    brain = LocalBrain()
    context = {
        "goal": "open arxiv.org",
        "step": {"title": "Open arxiv.org", "detail": "open arxiv.org", "tool_hint": "browser"},
        "done": [],
        "tool_log": [],
        "round": 1,
        "memory": {},
    }
    action = brain.act(context)
    assert action.kind == ACTION_TOOL
    assert action.tool == "open_website"
    assert action.args["target"] == "arxiv.org"
