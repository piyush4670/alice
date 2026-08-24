"""Mission orchestration.

Owns every running task, its worker thread and any question Alice is
currently waiting on. The server talks only to this module.
"""

import threading

from core.config import AGENT_ASK_TIMEOUT
from agent.brain import create_brain
from agent.engine import MissionEngine
from agent.models import (
    TASK_CANCELLED,
    TASK_DONE,
    TASK_WAITING,
    TASK_WORKING,
    Question,
    Task,
)


class Orchestrator:

    def __init__(self, emit):

        self.emit = emit
        self.engine = MissionEngine(emit)
        self.brain = create_brain()

        self.tasks = {}
        self.order = []

        self._waits = {}  # task_id -> {"event": Event, "answer": None}
        self._lock = threading.Lock()

    # -----------------
    # Introspection
    # -----------------

    def brain_info(self) -> dict:

        return {
            "mode": self.brain.mode,
            "label": self.brain.label,
        }

    def refresh_brain(self):
        """Re-read configuration so a newly added key is honoured."""

        from core.config import has_api_key

        if has_api_key() and self.brain.mode != "linked":
            self.brain = create_brain()

    def snapshot(self, task_id: str):
        task = self.tasks.get(task_id)
        return task.snapshot() if task else None

    def snapshots(self) -> list:

        return [
            self.tasks[task_id].snapshot()
            for task_id in reversed(self.order)
            if task_id in self.tasks
        ]

    def open_task(self):
        """The mission the UI should focus on, if any."""

        for task_id in reversed(self.order):

            task = self.tasks.get(task_id)

            if task and task.status not in (TASK_DONE, TASK_CANCELLED):
                return task

        return None

    # -----------------
    # Control
    # -----------------

    def start_mission(self, goal: str) -> Task:

        task = Task(goal=goal.strip())

        with self._lock:
            self.tasks[task.id] = task
            self.order.append(task.id)

            if len(self.order) > 60:
                forgotten = self.order.pop(0)
                self.tasks.pop(forgotten, None)

        self.refresh_brain()

        worker = threading.Thread(
            target=self._safe_run,
            args=(task,),
            daemon=True,
            name=f"alice-mission-{task.id}",
        )

        worker.start()

        return task

    def _safe_run(self, task: Task):

        try:
            self.engine.run(
                task,
                brain=self.brain,
                ask=self._ask,
                cancelled=lambda: task.status == TASK_CANCELLED,
            )

        except BaseException:
            import traceback

            self.emit(
                {
                    "type": "task.log",
                    "task_id": task.id,
                    "level": "warn",
                    "text": "Mission thread crashed: " + traceback.format_exc(limit=1),
                }
            )

    def cancel(self, task_id: str) -> bool:

        task = self.tasks.get(task_id)

        if not task or task.status in (TASK_DONE, TASK_CANCELLED):
            return False

        task.status = TASK_CANCELLED
        task.question = None

        with self._lock:
            wait = self._waits.get(task_id)

        if wait:
            wait["event"].set()

        self.emit(
            {
                "type": "task.state",
                "task_id": task_id,
                "state": TASK_CANCELLED,
            }
        )

        return True

    # -----------------
    # Questions
    # -----------------

    def _ask(self, task: Task, text: str):
        """Engine callback: block until the user answers or timeout."""

        question = Question.create(text)
        task.question = question
        task.status = TASK_WAITING

        self.emit(
            {
                "type": "task.question",
                "task_id": task.id,
                "question": question.snapshot(),
                "text": text,
            }
        )

        self.emit({"type": "task.state", "task_id": task.id, "state": TASK_WAITING})
        self.emit({"type": "task.snapshot", "task": task.snapshot()})

        event = threading.Event()

        with self._lock:
            self._waits[task.id] = {"event": event, "answer": None}

        answered = event.wait(timeout=AGENT_ASK_TIMEOUT)

        with self._lock:
            wait = self._waits.pop(task.id, None)

        answer = wait["answer"] if wait else None

        task.question = None

        if task.status != TASK_CANCELLED:
            task.status = TASK_WORKING

        self.emit({"type": "task.snapshot", "task": task.snapshot()})

        return answer if answered else None

    def answer(self, task_id: str, text: str) -> bool:

        with self._lock:
            wait = self._waits.get(task_id)

        if not wait:
            return False

        wait["answer"] = text
        wait["event"].set()

        return True
