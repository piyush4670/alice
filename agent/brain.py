"""The brain contract.

Two implementations exist: LinkedBrain (an OpenAI-compatible model) and
LocalBrain (offline rules). The engine never knows which one it holds,
so Alice degrades gracefully instead of going dark.
"""

from dataclasses import dataclass, field

from core.config import has_api_key


# What a brain may choose to do next.
ACTION_TOOL = "tool"
ACTION_REPLY = "reply"
ACTION_QUESTION = "question"
ACTION_FINAL = "final"


@dataclass
class Action:
    kind: str
    thought: str = ""
    tool: str = ""
    args: dict = field(default_factory=dict)
    text: str = ""


@dataclass
class Decision:
    decision: str  # continue | replan | ask_user | complete
    reason: str = ""
    question: str = ""
    steps: list = field(default_factory=list)


@dataclass
class Plan:
    message: str
    steps: list  # [{title, detail, tool_hint}]


class Brain:

    mode = "abstract"
    label = "brain"

    def plan(self, goal: str, memory: dict) -> Plan:
        raise NotImplementedError

    def act(self, context: dict) -> Action:
        raise NotImplementedError

    def reflect(self, context: dict) -> Decision:
        raise NotImplementedError

    def summarize(self, context: dict) -> str:
        raise NotImplementedError

    def converse(self, message: str, history: list, memory: dict):
        """Yield chunks of a conversational reply."""
        raise NotImplementedError


def create_brain() -> Brain:

    if has_api_key():
        from agent.llm_brain import LinkedBrain

        return LinkedBrain()

    from agent.local_brain import LocalBrain

    return LocalBrain()
