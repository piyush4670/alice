"""The mission engine.

Alice's autonomy lives here: plan a goal, execute step by step with
tools, observe every result, reflect on progress, ask the user when a
decision belongs to them — and keep going until the mission is truly
finished. The engine is a pure worker: it emits events and never
touches sockets itself.
"""

import time

from core.config import (
    AGENT_MAX_STEPS,
    AGENT_ROUNDS_PER_STEP,
)
from agent.brain import (
    ACTION_FINAL,
    ACTION_QUESTION,
    ACTION_TOOL,
    create_brain,
)
from agent.models import (
    STEP_DONE,
    STEP_FAILED,
    STEP_RUNNING,
    STEP_SKIPPED,
    TASK_CANCELLED,
    TASK_DONE,
    TASK_FAILED,
    TASK_WORKING,
    Artifact,
    Step,
    Task,
    new_id,
)
from memory import manager as memory
from tools import registry


def shorten(text: str, limit: int = 900) -> str:

    text = str(text or "").strip()

    if len(text) <= limit:
        return text

    return text[:limit] + " …"


class MissionEngine:

    def __init__(self, emit):
        """emit: callable(dict) pushing one event to every client."""

        self.emit = emit

    # -----------------
    # Event helpers
    # -----------------

    def snapshot(self, task: Task):
        self.emit({"type": "task.snapshot", "task": task.snapshot()})

    def state(self, task: Task, status: str):
        task.status = status
        task.touch()
        self.emit({"type": "task.state", "task_id": task.id, "state": status})
        self.snapshot(task)

    def log(self, task: Task, level: str, text: str, detail=None):
        task.record_event(level, text, detail)
        self.emit(
            {
                "type": "task.log",
                "task_id": task.id,
                "level": level,
                "text": text,
                "detail": detail,
                "at": time.time(),
            }
        )

    def say(self, task: Task, text: str):
        """Alice narrates, chunked so the UI can stream her voice."""

        text = str(text or "").strip()

        if not text:
            return

        message_id = new_id("m")

        self.emit(
            {
                "type": "task.delta",
                "task_id": task.id,
                "mid": message_id,
                "text": text,
            }
        )

        self.emit({"type": "task.message_done", "task_id": task.id, "mid": message_id})

        task.log_exchange("assistant", text)

    def memory_sync(self, before: dict):

        after = memory.all_memory()

        if after != before:
            self.emit({"type": "memory.updated", "items": after})

    # -----------------
    # The loop
    # -----------------

    def run(self, task: Task, ask, cancelled, brain=None):
        """Execute one mission to completion. Blocking."""

        brain = brain or create_brain()

        self.emit({"type": "task.started", "task_id": task.id})
        self.snapshot(task)

        try:
            self._run(task, ask, cancelled, brain)

        except Exception as exc:

            self.log(task, "warn", f"Mission error: {exc}")

            if task.status not in (TASK_CANCELLED, TASK_DONE):
                task.summary = (
                    "I hit an internal fault and had to stop, Boss. "
                    "Everything already finished stays finished."
                )
                self.state(task, TASK_FAILED)

        finally:
            self.emit({"type": "task.snapshot", "task": task.snapshot()})

    def _run(self, task: Task, ask, cancelled, brain):

        goal = task.goal
        memory_before = memory.all_memory()

        # -----------------
        # 1. Plan
        # -----------------

        self.state(task, "planning")
        self.log(task, "thought", "Drafting a plan for the mission.")

        try:
            plan = brain.plan(goal, memory_before)

        except Exception:

            from agent.local_brain import LocalBrain

            self.log(task, "warn", "Linked brain unreachable. Local core taking over.")

            brain = LocalBrain()
            plan = brain.plan(goal, memory_before)

        task.steps = [
            Step.create(item["title"], item.get("detail", ""), item.get("tool_hint", ""))
            for item in plan.steps
        ]

        task.log_exchange("user", goal)

        self.log(
            task,
            "info",
            f"Plan ready — {len(task.steps)} step(s).",
            [step.title for step in task.steps],
        )

        self.snapshot(task)
        self.say(task, plan.message)

        # -----------------
        # 2. Work the plan
        # -----------------

        self.state(task, TASK_WORKING)

        executed = 0
        final_answer = None

        while executed < AGENT_MAX_STEPS:

            if cancelled():
                self.state(task, TASK_CANCELLED)
                self.say(task, "Mission cancelled. I've stopped where I was, Boss.")
                return

            pending = task.pending_steps()

            if not pending:
                break

            step = pending[0]
            step.status = STEP_RUNNING
            step.attempts += 1
            executed += 1

            self.snapshot(task)
            self.log(task, "step", f"Step {executed}: {step.title}")

            tool_log = []
            step_outcome = ""
            rounds = 0

            while rounds < AGENT_ROUNDS_PER_STEP:

                if cancelled():
                    break

                context = {
                    "goal": goal,
                    "step": {
                        "title": step.title,
                        "detail": step.detail,
                        "tool_hint": step.tool_hint,
                    },
                    "done": [
                        {"title": s.title, "result": shorten(s.result, 300)}
                        for s in task.finished_steps()
                    ],
                    "tool_log": tool_log,
                    "round": rounds + 1,
                    "memory": memory.all_memory(),
                }

                try:
                    action = brain.act(context)

                except Exception:

                    from agent.local_brain import LocalBrain

                    self.log(task, "warn", "Linked brain dropped mid-step. Local core resuming.")
                    brain = LocalBrain()
                    action = brain.act(context)

                # --- Ask the user ---
                if action.kind == ACTION_QUESTION and action.text:

                    answer = ask(task, action.text)

                    if cancelled():
                        break

                    if answer is None:
                        tool_log.append(
                            {
                                "tool": "ask_user",
                                "args": {"question": action.text},
                                "ok": True,
                                "output": "The user did not answer in time. Use your best judgement.",
                            }
                        )

                        self.log(task, "warn", "No answer in time — proceeding with best judgement.")

                    else:
                        tool_log.append(
                            {
                                "tool": "ask_user",
                                "args": {"question": action.text},
                                "ok": True,
                                "output": f"The user answered: {answer}",
                            }
                        )

                        task.log_exchange("user", answer)
                        self.log(task, "info", f"User: {answer}")

                    rounds += 1
                    continue

                # --- Use a tool ---
                if action.kind == ACTION_TOOL:

                    self.log(
                        task,
                        "tool",
                        f"{action.tool}({', '.join(f'{k}={str(v)[:60]}' for k, v in action.args.items())})",
                        {"tool": action.tool, "args": action.args},
                    )

                    result = registry.execute(action.tool, action.args)

                    tool_log.append(
                        {
                            "tool": action.tool,
                            "args": action.args,
                            "ok": result.ok,
                            "output": shorten(result.observe(), 1200),
                        }
                    )

                    self.log(
                        task,
                        "good" if result.ok else "warn",
                        shorten(result.observe(), 300),
                    )

                    artifact = (result.data or {}).get("artifact") if isinstance(result.data, dict) else None

                    if artifact:
                        task.artifacts.append(Artifact(artifact["name"], artifact["path"]))
                        self.emit(
                            {
                                "type": "task.artifact",
                                "task_id": task.id,
                                "artifact": artifact,
                            }
                        )

                    self.memory_sync(memory_before)
                    memory_before = memory.all_memory()

                    rounds += 1
                    continue

                # --- A reply ends the step; final ends the mission ---
                step_outcome = action.text or "(no output)"
                break

            if cancelled():
                self.state(task, TASK_CANCELLED)
                self.say(task, "Mission cancelled. I've stopped where I was, Boss.")
                return

            if action.kind == ACTION_FINAL and action.text:
                final_answer = action.text
                step.result = shorten(step_outcome)
                step.status = STEP_DONE

            elif step_outcome:
                step.result = shorten(step_outcome)
                step.status = STEP_DONE
                self.say(task, step.result)

            elif rounds >= AGENT_ROUNDS_PER_STEP:
                step.status = STEP_FAILED
                step.result = "Ran out of rounds before finishing."
                self.log(task, "warn", "Step stalled; moving on.")

            else:
                step.status = STEP_FAILED
                step.result = "Step ended without a result."
                self.log(task, "warn", "Step ended without a result.")

            self.snapshot(task)

            # -----------------
            # 3. Reflect
            # -----------------

            reflect_context = {
                "goal": goal,
                "done": [
                    {"title": s.title, "result": shorten(s.result, 300)}
                    for s in task.steps if s.status == STEP_DONE
                ],
                "failed": [
                    {"title": s.title, "result": s.result}
                    for s in task.steps if s.status == STEP_FAILED
                ],
                "pending": [{"title": s.title} for s in task.pending_steps()],
            }

            try:
                decision = brain.reflect(reflect_context)

            except Exception:
                from agent.local_brain import LocalBrain

                brain = LocalBrain()
                decision = brain.reflect(reflect_context)

            self.log(task, "thought", f"Reflection: {decision.decision} — {decision.reason}")

            if decision.decision == "ask_user" and decision.question:

                answer = ask(task, decision.question)

                if cancelled():
                    self.state(task, TASK_CANCELLED)
                    self.say(task, "Mission cancelled. I've stopped where I was, Boss.")
                    return

                task.log_exchange("user", answer or "(silence)")
                self.log(task, "info", f"User: {answer or '(no answer — proceeding)'}")

            elif decision.decision == "replan" and decision.steps:

                for step_left in task.pending_steps():
                    step_left.status = STEP_SKIPPED
                    step_left.result = "Superseded by a revised plan."

                task.steps.extend(
                    Step.create(item["title"], item.get("detail", ""), item.get("tool_hint", ""))
                    for item in decision.steps
                )

                self.log(task, "info", f"Plan revised — {len(decision.steps)} new step(s).")
                self.say(task, "I've reshaped the plan based on what I learned: " + decision.reason)
                self.snapshot(task)

            elif decision.decision == "complete":
                break

        # -----------------
        # 4. Close
        # -----------------

        if executed >= AGENT_MAX_STEPS and task.pending_steps():
            task.summary = (
                f"I reached my safety limit of {AGENT_MAX_STEPS} steps, Boss. "
                "Here is everything I completed — say 'continue the mission' and I'll carry on."
            )

        elif final_answer:
            task.summary = final_answer

        else:
            context = {
                "goal": goal,
                "done": [
                    {"title": s.title, "result": shorten(s.result, 400)}
                    for s in task.steps if s.status == STEP_DONE
                ],
                "failed": [
                    {"title": s.title, "result": s.result}
                    for s in task.steps if s.status == STEP_FAILED
                ],
            }

            try:
                task.summary = brain.summarize(context)

            except Exception:
                from agent.local_brain import LocalBrain

                task.summary = LocalBrain().summarize(context)

        self.state(task, TASK_DONE)
        self.say(task, task.summary)
        self.log(task, "good", "Mission complete.")

        task.question = None
