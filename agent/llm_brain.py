"""LinkedBrain: Alice powered by an OpenAI-compatible model.

Every reply is JSON-bounded; every failure surfaces as BrainUnavailable
so the engine can fall back to the local brain mid-mission.
"""

from ai import client
from ai.client import BrainUnavailable
from ai.prompts import build_prompt
from ai.reasoning import analyze
from agent import prompts
from agent.brain import (
    ACTION_FINAL,
    ACTION_QUESTION,
    ACTION_REPLY,
    ACTION_TOOL,
    Action,
    Brain,
    Decision,
    Plan,
)
from core.config import MODEL
from tools.registry import execute, has as has_tool


def _steps_from(raw) -> list:

    steps = []

    if isinstance(raw, list):

        for item in raw:

            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()

            if not title:
                continue

            steps.append(
                {
                    "title": title[:160],
                    "detail": str(item.get("detail", "")).strip()[:400],
                    "tool_hint": str(item.get("tool_hint", "")).strip(),
                }
            )

    return steps


def _normal_steps(raw) -> list:
    """Accept both {"steps": [...]} and a bare list."""

    if isinstance(raw, list):
        return _steps_from(raw)

    if isinstance(raw, dict):
        return _steps_from(raw.get("steps"))

    return []


class LinkedBrain(Brain):

    mode = "linked"
    label = MODEL

    # -----------------
    # Planning
    # -----------------

    def plan(self, goal: str, memory: dict) -> Plan:

        data = client.chat_json(prompts.plan_messages(goal, memory))

        steps = _normal_steps(data)

        if not steps:
            steps = [{"title": "Answer the request", "detail": goal, "tool_hint": ""}]

        message = str(data.get("message", "")).strip() if isinstance(data, dict) else ""

        if not message:
            message = "Plan ready, Boss. Working through it now."

        return Plan(message=message, steps=steps)

    # -----------------
    # Acting
    # -----------------

    def act(self, context: dict) -> Action:

        data = client.chat_json(prompts.act_messages(context), temperature=0.2)

        action = str(data.get("action", "")).strip().lower()
        thought = str(data.get("thought", "")).strip()

        if action == "tool":

            name = str(data.get("tool", "")).strip()

            if has_tool(name):

                args = data.get("args") or {}

                if not isinstance(args, dict):
                    args = {}

                return Action(ACTION_TOOL, thought, name, args)

            return Action(
                ACTION_REPLY,
                thought,
                text="That tool does not exist. I worked around it.",
            )

        if action == "question":
            return Action(ACTION_QUESTION, thought, text=str(data.get("text", "")).strip())

        if action == "final":
            return Action(ACTION_FINAL, thought, text=str(data.get("text", "")).strip())

        return Action(ACTION_REPLY, thought, text=str(data.get("text", "")).strip())

    # -----------------
    # Reflection
    # -----------------

    def reflect(self, context: dict) -> Decision:

        data = client.chat_json(prompts.reflect_messages(context), temperature=0.2)

        choice = str(data.get("decision", "")).strip().lower()

        if choice not in ("continue", "replan", "ask_user", "complete"):
            choice = "continue"

        decision = Decision(
            decision=choice,
            reason=str(data.get("reason", "")).strip(),
            question=str(data.get("question", "")).strip(),
        )

        if choice == "replan":

            steps = _normal_steps(data)

            if steps:
                decision.steps = steps
            else:
                decision.decision = "continue"

        return decision

    # -----------------
    # Summary
    # -----------------

    def summarize(self, context: dict) -> str:

        try:
            return client.chat(prompts.summarize_messages(context)).strip()

        except BrainUnavailable:
            done = context.get("done", [])

            lines = [f"- {item['title']}" for item in done]

            return "Mission complete, Boss. Steps finished:\n" + "\n".join(lines)

    # -----------------
    # Conversation
    # -----------------

    def converse(self, message: str, history: list, memory: dict):

        reasoning = analyze(message, history, memory)

        prompt = build_prompt(history, memory, reasoning, message)

        yield from client.chat_stream(
            [
                {"role": "user", "content": prompt},
            ]
        )


def safe_execute(name: str, args: dict):
    """Execute a tool, mapping every outcome into an observation."""

    result = execute(name, args)

    return result.observe()
