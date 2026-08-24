"""Data structures shared by the agent engine.

Pure data, no behaviour beyond simple helpers, so any module can import
these without pulling in the engine.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


def new_id(prefix: str) -> str:

    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ===========
# Steps
# ===========

STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_DONE = "done"
STEP_FAILED = "failed"
STEP_SKIPPED = "skipped"


@dataclass
class Step:
    id: str
    title: str
    detail: str = ""
    status: str = STEP_PENDING
    tool_hint: str = ""
    result: str = ""
    attempts: int = 0

    @staticmethod
    def create(title, detail="", tool_hint=""):
        return Step(
            id=new_id("step"),
            title=title,
            detail=detail,
            tool_hint=tool_hint,
        )

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "detail": self.detail,
            "status": self.status,
            "result": self.result,
            "attempts": self.attempts,
        }


# ===========
# Questions Alice asks the user mid-mission
# ===========

@dataclass
class Question:
    id: str
    text: str
    answer: Optional[str] = None

    @staticmethod
    def create(text):
        return Question(id=new_id("q"), text=text)

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "answered": self.answer is not None,
        }


# ===========
# Artifacts (files Alice produces in her workspace)
# ===========

@dataclass
class Artifact:
    name: str
    path: str
    kind: str = "file"

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "kind": self.kind,
        }


# ===========
# The mission itself
# ===========

TASK_PLANNING = "planning"
TASK_WORKING = "working"
TASK_WAITING = "waiting_user"
TASK_DONE = "done"
TASK_FAILED = "failed"
TASK_CANCELLED = "cancelled"


@dataclass
class Task:
    goal: str
    id: str = field(default_factory=lambda: new_id("task"))
    status: str = TASK_PLANNING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    steps: list = field(default_factory=list)
    summary: str = ""
    question: Optional[Question] = None
    artifacts: list = field(default_factory=list)
    events: list = field(default_factory=list)
    transcript: list = field(default_factory=list)

    def touch(self):
        self.updated_at = time.time()

    def pending_steps(self):
        return [step for step in self.steps if step.status == STEP_PENDING]

    def finished_steps(self):
        return [
            step
            for step in self.steps
            if step.status in (STEP_DONE, STEP_FAILED, STEP_SKIPPED)
        ]

    def record_event(self, kind: str, text: str, detail: Any = None):

        entry = {
            "kind": kind,
            "text": text,
            "detail": detail,
            "at": time.time(),
        }

        self.events.append(entry)

        # Keep the in-memory log bounded; the UI receives everything live.
        if len(self.events) > 400:
            del self.events[:200]

    def log_exchange(self, role: str, text: str):

        self.transcript.append({"role": role, "text": text})

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [step.snapshot() for step in self.steps],
            "summary": self.summary,
            "question": self.question.snapshot() if self.question else None,
            "artifacts": [item.snapshot() for item in self.artifacts],
            "events": self.events[-60:],
        }
