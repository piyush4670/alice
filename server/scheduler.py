"""Background reminder scheduler.

ALICE's reminders are stored as human phrases. This thread wakes every few
seconds, resolves any reminder whose time has arrived, and emits a
``reminder.fire`` event so every connected client hears it ring.

Firing is idempotent per server run: once a (task, time) pair has fired it is
remembered in memory, so ALICE never nag-rings the same reminder twice from
the same process. The reminder itself stays in the list until the user
deletes it — firing is an alert, not a deletion.
"""

import threading

from datetime import datetime

from core.config import REMINDER_CHECK_SECONDS, REMINDER_GRACE_SECONDS
from plugins.reminder import load_reminders
from utils.timeparse import resolve

CHECK_SECONDS = REMINDER_CHECK_SECONDS
FIRE_GRACE_SECONDS = REMINDER_GRACE_SECONDS


class ReminderScheduler:

    def __init__(self, emit):
        self.emit = emit
        self._fired = set()
        self._stop = threading.Event()
        self._thread = None

    # -----------------
    # Lifecycle
    # -----------------

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="alice-reminders",
            daemon=True,
        )

        self._thread.start()

    def stop(self):
        self._stop.set()

    # -----------------
    # The loop
    # -----------------

    def _run(self):
        while not self._stop.is_set():

            try:
                self._check()
            except Exception:
                # A planner or resolve bug must never kill the thread.
                pass

            self._stop.wait(CHECK_SECONDS)

    def _check(self, now=None):
        now = now or datetime.now()

        for reminder in load_reminders():

            task = (reminder.get("task") or "").strip()
            phrase = (reminder.get("time") or "").strip()

            if not task or not phrase:
                continue

            target = resolve(phrase, now)

            if target is None:
                # We do not understand this reminder's time yet; leave it be.
                continue

            key = (task.lower(), phrase)

            due = target <= now
            within_grace = (now - target).total_seconds() <= FIRE_GRACE_SECONDS

            if due and within_grace and key not in self._fired:
                self._fired.add(key)
                self._fire(task, phrase, target)

    def _fire(self, task: str, phrase: str, target: datetime):

        message = f"Reminder: {task}"

        self.emit(
            {
                "type": "reminder.fire",
                "task": task,
                "time": phrase,
                "resolved": target.isoformat(),
                "text": message,
            }
        )

        # Also drop it into the conversation stream so it reads like ALICE
        # speaking, not a silent system alert.
        self.emit({"type": "chat.delta", "mid": f"r-{int(target.timestamp())}", "text": message})
        self.emit(
            {
                "type": "chat.done",
                "mid": f"r-{int(target.timestamp())}",
                "message": message,
                "source": "reminder",
            }
        )
