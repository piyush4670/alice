"""Regression tests for reminder time resolution and web/device tools."""

from datetime import datetime

import server.scheduler as scheduler
from agent.engine import MissionEngine
from agent.models import Task
from tools.integrations import open_website, notify
from utils.timeparse import resolve


def _now():
    # A fixed "now": Wednesday 2026-08-26, 10:00 local.
    return datetime(2026, 8, 26, 10, 0, 0)


def test_resolve_clock_pm():
    assert resolve("5pm", _now()) == datetime(2026, 8, 26, 17, 0, 0)


def test_resolve_clock_pm_past_rolls_to_tomorrow():
    # 9am today already passed at 10am -> tomorrow.
    assert resolve("9am", _now()) == datetime(2026, 8, 27, 9, 0, 0)


def test_resolve_clock_24hr():
    assert resolve("17:30", _now()) == datetime(2026, 8, 26, 17, 30, 0)


def test_resolve_clock_24hr_past_rolls_to_tomorrow():
    assert resolve("08:15", _now()) == datetime(2026, 8, 27, 8, 15, 0)


def test_resolve_tomorrow_clock():
    assert resolve("tomorrow at 5pm", _now()) == datetime(2026, 8, 27, 17, 0, 0)


def test_resolve_clock_tomorrow():
    assert resolve("5pm tomorrow", _now()) == datetime(2026, 8, 27, 17, 0, 0)


def test_resolve_bare_tomorrow_defaults_to_morning():
    assert resolve("tomorrow", _now()) == datetime(2026, 8, 27, 9, 0, 0)


def test_resolve_tonight_defaults_evening():
    assert resolve("tonight", _now()) == datetime(2026, 8, 26, 21, 0, 0)


def test_resolve_next_weekday():
    # Wednesday -> next monday is +5 days.
    assert resolve("next monday", _now()) == datetime(2026, 8, 31, 9, 0, 0)


def test_resolve_plain_weekday_this_week():
    # Wednesday -> upcoming friday is +2 days.
    assert resolve("friday", _now()) == datetime(2026, 8, 28, 9, 0, 0)


def test_resolve_noon():
    assert resolve("noon tomorrow", _now()) == datetime(2026, 8, 27, 12, 0, 0)


def test_resolve_unknown_returns_none():
    assert resolve("", _now()) is None
    assert resolve("whenever you like", _now()) is None


def test_open_website_domain():
    result = open_website("arxiv.org")
    assert result.ok
    assert result.data["web"]["url"] == "https://arxiv.org"


def test_open_website_search():
    result = open_website("latest AI news")
    assert result.ok
    assert "duckduckgo.com/?q=" in result.data["web"]["url"]


def test_open_website_site_shortcut():
    result = open_website("youtube")
    assert result.ok
    assert "youtube.com" in result.data["web"]["url"]


def test_open_website_plain_url():
    result = open_website("https://wikipedia.org")
    assert result.ok
    assert result.data["web"]["url"] == "https://wikipedia.org"


def test_open_website_empty_fails():
    assert not open_website("  ").ok


def test_notify_carries_payload():
    result = notify("Done", "Your research finished.")
    assert result.ok
    assert result.data["notify"]["title"] == "Done"
    assert result.data["notify"]["body"] == "Your research finished."


# ===========
# Reminder scheduler
# ===========

def test_scheduler_fires_due_reminder(monkeypatch):
    events = []
    # 10:00 in the morning; a "9am" reminder is already past.
    now = datetime(2026, 8, 26, 10, 0, 0)
    monkeypatch.setattr(scheduler, "load_reminders", lambda: [{"task": "call mom", "time": "today 9am"}])
    sched = scheduler.ReminderScheduler(emit=events.append)
    sched._check(now)
    fired = [e for e in events if e["type"] == "reminder.fire"]
    assert len(fired) == 1
    assert fired[0]["task"] == "call mom"
    assert "chat.done" in [e["type"] for e in events]


def test_scheduler_fires_each_reminder_once(monkeypatch):
    events = []
    now = datetime(2026, 8, 26, 10, 0, 0)
    monkeypatch.setattr(scheduler, "load_reminders", lambda: [{"task": "call mom", "time": "today 9am"}])
    sched = scheduler.ReminderScheduler(emit=events.append)
    sched._check(now)
    sched._check(now)
    fired = [e for e in events if e["type"] == "reminder.fire"]
    assert len(fired) == 1


def test_scheduler_ignores_future_reminder(monkeypatch):
    events = []
    now = datetime(2026, 8, 26, 10, 0, 0)
    monkeypatch.setattr(scheduler, "load_reminders", lambda: [{"task": "call mom", "time": "tomorrow 5pm"}])
    sched = scheduler.ReminderScheduler(emit=events.append)
    sched._check(now)
    assert not any(e["type"] == "reminder.fire" for e in events)


def test_scheduler_skips_unparseable_time(monkeypatch):
    events = []
    now = datetime(2026, 8, 26, 10, 0, 0)
    monkeypatch.setattr(scheduler, "load_reminders", lambda: [{"task": "call mom", "time": "whenever"}])
    sched = scheduler.ReminderScheduler(emit=events.append)
    sched._check(now)
    assert not events


# ===========
# Engine side effects
# ===========

def test_engine_surfaces_web_open():
    events = []
    engine = MissionEngine(events.append)
    task = Task(goal="open arxiv")
    engine._side_effects(task, {"web": {"url": "https://arxiv.org", "title": "arxiv"}})
    assert any(e["type"] == "web.open" and e["url"] == "https://arxiv.org" for e in events)


def test_engine_surfaces_notify():
    events = []
    engine = MissionEngine(events.append)
    task = Task(goal="notify me")
    engine._side_effects(task, {"notify": {"title": "Done", "body": "Finished"}})
    assert any(e["type"] == "system.notify" and e["title"] == "Done" for e in events)


def test_engine_surfaces_artifact():
    events = []
    engine = MissionEngine(events.append)
    task = Task(goal="write file")
    engine._side_effects(task, {"artifact": {"name": "a.md", "path": "/tmp/a.md"}})
    assert any(e["type"] == "task.artifact" for e in events)
    assert any(a.name == "a.md" for a in task.artifacts)
