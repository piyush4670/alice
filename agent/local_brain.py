"""LocalBrain: Alice's offline reasoning core.

No API key, no problem. The local brain plans missions with the same
tools the linked brain uses — parsing is deterministic, so reminders,
notes, to-dos, memory, maths, time, Wikipedia lookups and web searches
all still execute. Only free-form conversation explains its limits.
"""

import re

from core.personality import AI_NO_KEY, boss
from tools.registry import execute

from agent.brain import (
    ACTION_REPLY,
    ACTION_TOOL,
    Action,
    Brain,
    Decision,
    Plan,
)

# ===========
# Fragmenting a goal
# ===========

STRONG_SPLITS = (
    " and then ",
    " then also ",
    "; ",
    " after that ",
    " following that, ",
)

QUESTION_STARTERS = (
    "who is ",
    "who was ",
    "who are ",
    "what is ",
    "what was ",
    "what are ",
    "tell me about ",
    "search for ",
    "look up ",
)

SEARCH_HINTS = (
    "search",
    "find out",
    "look up",
    "research",
    "latest on",
    "news about",
    "google ",
)

# Phrases that mean "open a website in the web deck".
OPEN_STARTERS = (
    "open ",
    "go to ",
    "take me to ",
    "browse ",
    "load ",
    "launch ",
    "show me ",
)

OPEN_TRAILERS = (
    " in the browser",
    " in the web deck",
    " in a new tab",
    " on the web",
    " on the internet",
    " in my browser",
    " for me",
    " please",
)

KNOWN_SITES = (
    "youtube",
    "youtube.com",
    "google",
    "google.com",
    "wikipedia",
    "wikipedia.org",
    "duckduckgo",
    "duckduckgo.com",
    "bing",
    "bing.com",
    "github",
    "github.com",
    "gmail",
    "maps",
    "maps.google.com",
    "news",
    "news.google.com",
    "arxiv",
    "arxiv.org",
    "reddit",
    "reddit.com",
    "twitter",
    "x.com",
    "instagram",
)

# "open the web deck" / "open the browser" -> a sensible default homepage.
BROWSER_DEFAULTS = ("web deck", "webdeck", "the web", "browser", "the browser", "a browser")


def _looks_like_site(target: str) -> bool:
    """True when a fragment names a website/domain rather than a topic."""

    lowered = (target or "").lower()
    trimmed = lowered.removeprefix("the ").strip()

    if "." in lowered:
        return True

    for site in KNOWN_SITES:
        if site in lowered:
            return True

    for phrase in BROWSER_DEFAULTS:
        if lowered == phrase or trimmed == phrase:
            return True

    return False


def normalise(text: str) -> str:

    text = (text or "").strip()

    text = re.sub(r"^(?:hey |ok |okay |please |could you |can you |would you |alice[,]? )+", "", text, flags=re.IGNORECASE).strip()

    return text


def strip_lead(text: str, *leads: str) -> str:

    lowered = text.lower()

    for lead in leads:

        if lowered.startswith(lead):
            return text[len(lead):].strip(" .,:!")

    return text.strip(" .,:!")


def classify(fragment: str):
    """Return (tool_hint, payload) for one fragment of a goal."""

    text = normalise(fragment)
    lowered = text.lower()

    if not text:
        return ("answer", "")

    # Clock and calendar.
    if re.search(r"\b(what(?:'s| is)? the time|what time is it|current time|time now)\b", lowered):
        return ("time", "")

    if re.search(r"\b(what(?:'s| is)? (?:the |today's )?date|what day is it|today's date)\b", lowered):
        return ("date", "")

    # Reminders.
    if "remind" in lowered:
        payload = strip_lead(
            lowered,
            "remind me to ",
            "remind me ",
            "set a reminder to ",
            "set a reminder for ",
            "add a reminder to ",
            "reminder to ",
            "reminder ",
        )
        payload = payload or lowered
        return ("reminder", f"remind me to {payload}")

    # Notes.
    if re.match(r"^(?:add a? ?note|note down|jot down|make a note|note that)\b", lowered):
        payload = strip_lead(
            lowered,
            "note that ",
            "note down ",
            "jot down ",
            "add a note ",
            "add note ",
            "make a note that ",
            "make a note ",
            "add a note that ",
        )
        return ("note", f"note that {payload or lowered}")

    # Memory.
    if re.match(r"^(?:please )?remember (?:that )?(?:my |our )", lowered):
        return ("memory", lowered)

    if re.match(r"^my [a-z ]+ is .+$", lowered):
        return ("memory", lowered)

    if re.match(r"^i (?:am |live in |work at |study at |like |love |enjoy )", lowered):
        return ("memory", lowered)

    # To-dos. "remember to X" reads as a task, not a fact.
    if re.match(r"^remember to ", lowered):
        return ("todo", f"add task {strip_lead(lowered, 'remember to ')}")

    if re.search(r"\b(task|to-do|todo|to do list)\b", lowered):
        payload = strip_lead(
            lowered,
            "add a task to ",
            "add a task ",
            "add task ",
            "add to my to-do list ",
            "add to my todo list ",
            "add to my task list ",
            "add a to-do ",
        )
        return ("todo", f"add task {payload or lowered}")

    # Maths before factual lookup, so "what is 2+2" never reaches Wikipedia.
    if lowered.startswith(("calculate ", "compute ", "solve ", "what is ", "what's ", "convert ")):

        expression = strip_lead(
            lowered,
            "calculate ",
            "compute ",
            "solve ",
            "what is ",
            "what's ",
            "convert ",
        ).rstrip(" ?")

        if any(ch.isdigit() for ch in expression) and any(op in expression for op in "+-*/%^"):
            return ("calculator", expression)

    if re.match(r"^[\d\s+\-*/%().^]+$", lowered) and any(op in lowered for op in "+-*/%^"):
        return ("calculator", lowered)

    # Browser: "open arxiv.org", "go to youtube", "take me to wikipedia".
    if lowered.startswith(OPEN_STARTERS):

        target = text

        for starter in OPEN_STARTERS:
            if lowered.startswith(starter):
                target = text[len(starter):]
                break

        for trailer in OPEN_TRAILERS:
            if target.lower().endswith(trailer):
                target = target[: -len(trailer)]
                break

        target = target.strip(" .,!?:")

        if target and _looks_like_site(target):
            lowered_target = target.lower().removeprefix("the ").strip()

            for phrase in BROWSER_DEFAULTS:
                if lowered_target == phrase:
                    target = "duckduckgo"
                    break

            return ("browser", target)

    # Research.
    for starter in QUESTION_STARTERS:

        if lowered.startswith(starter):

            topic = text[len(starter):].strip(" ?.")

            if topic and not any(ch.isdigit() for ch in topic[:2]):
                return ("wikipedia", topic)

    if re.match(
        r"^(?:write|save|store|export|put)\b.+\b(?:file|document|report|artifact|summary)\b",
        lowered,
    ):
        return ("save_results", text)

    if any(hint in lowered for hint in SEARCH_HINTS):

        payload = lowered

        for lead in (
            "search for ",
            "search ",
            "find out about ",
            "find out ",
            "look up ",
            "research ",
            "google ",
            "latest on ",
            "news about ",
        ):
            payload = strip_lead(payload, lead)

            if payload != lowered:
                break

        return ("search", payload or lowered)

    return ("answer", text)


def fragment_goal(goal: str) -> list:
    """Split a goal into independently executable intents."""

    text = normalise(goal)

    if not text:
        return []

    parts = [text]

    for splitter in STRONG_SPLITS:

        next_parts = []

        for part in parts:
            next_parts.extend(pieces for piece in part.split(splitter) if (pieces := piece.strip()))

        parts = next_parts

    # "and" only splits when both halves are actionable intents.
    final = []

    for part in parts:

        halves = [h.strip() for h in part.split(" and ") if h.strip()]

        if len(halves) > 1 and all(classify(h)[0] != "answer" for h in halves):
            final.extend(halves)

        else:
            final.append(part)

    return [p for p in final if p]


# ===========
# The brain
# ===========

class LocalBrain(Brain):

    mode = "local"
    label = "offline core"

    def plan(self, goal: str, memory: dict) -> Plan:

        fragments = fragment_goal(goal)

        if not fragments:
            fragments = [goal]

        steps = []
        counter = {}

        for fragment in fragments:

            hint, payload = classify(fragment)

            counter[hint] = counter.get(hint, 0) + 1

            title = {
                "reminder": "Save the reminder",
                "note": "Save the note",
                "memory": "Store the fact",
                "todo": "Add the to-do",
                "calculator": "Run the calculation",
                "time": "Check the time",
                "date": "Check the date",
                "wikipedia": f"Research: {payload[:60]}",
                "search": "Search the web",
                "save_results": "Write the results file",
                "browser": f"Open {payload[:40]}",
                "answer": "Handle the request",
            }.get(hint, "Handle the request")

            if counter[hint] > 1:
                title += f" ({counter[hint]})"

            steps.append(
                {
                    "title": title,
                    "detail": fragment,
                    "tool_hint": hint,
                }
            )

        message = f"On it, Boss. I've mapped {len(steps)} step{'s' if len(steps) != 1 else ''} and I'm starting now."

        return Plan(message=message, steps=steps)

    def act(self, context: dict) -> Action:

        step = context.get("step", {})
        hint = step.get("tool_hint", "answer")
        detail = step.get("detail", "")
        tool_log = context.get("tool_log", [])

        # Second round: report what the tools observed.
        if tool_log:

            outputs = [item["output"] for item in tool_log]

            return Action(ACTION_REPLY, text="\n".join(outputs))

        # First round: run the matching tool.
        if hint == "reminder":
            return Action(ACTION_TOOL, tool="add_reminder", args={"reminder": detail})

        if hint == "note":
            return Action(ACTION_TOOL, tool="add_note", args={"note": detail})

        if hint == "memory":
            return Action(ACTION_TOOL, tool="remember", args={"pair": detail})

        if hint == "todo":
            return Action(ACTION_TOOL, tool="add_todo", args={"task": detail})

        if hint == "calculator":
            payload = classify(detail)[1] or detail
            return Action(ACTION_TOOL, tool="calculator", args={"expression": payload})

        if hint == "time":
            return Action(ACTION_TOOL, tool="current_time", args={})

        if hint == "date":
            return Action(ACTION_TOOL, tool="current_date", args={})

        if hint == "save_results":

            done = context.get("done", [])

            lines = ["# Mission results", "", f"Goal: {context.get('goal', '')}", ""]

            for item in done:
                lines.append(f"## {item['title']}")
                lines.append(str(item.get("result", "")).strip())
                lines.append("")

            if len(lines) < 6:
                lines.append("(No step results were collected before the write.)")

            body = "\n".join(lines)

            words = [w for w in re.split(r"[^a-z0-9]+", context.get("goal", "").lower()) if len(w) > 3][:3]

            name = ("-".join(words) + ".md") if words else "results.md"

            return Action(ACTION_TOOL, tool="write_file", args={"name": name, "body": body})

        if hint == "wikipedia":
            payload = classify(detail)
            return Action(ACTION_TOOL, tool="wikipedia", args={"topic": payload[1] or detail})

        if hint == "search":
            payload = classify(detail)
            return Action(ACTION_TOOL, tool="web_search", args={"query": payload[1] or detail})

        if hint == "browser":
            payload = classify(detail)[1] or detail
            return Action(ACTION_TOOL, tool="open_website", args={"target": payload})

        # Open-ended fragment: try a factual lookup, else answer honestly.
        guess = classify(detail)

        if guess[0] == "wikipedia":
            return Action(ACTION_TOOL, tool="wikipedia", args={"topic": guess[1]})

        if guess[0] == "search":
            return Action(ACTION_TOOL, tool="web_search", args={"query": guess[1]})

        lowered = detail.lower()

        if lowered.endswith("?") or any(lowered.startswith(w) for w in ("who", "what", "when", "where", "why", "how")):

            subject = detail

            for starter in QUESTION_STARTERS:

                if lowered.startswith(starter):
                    subject = detail[len(starter):].strip(" ?.")
                    break

            return Action(ACTION_TOOL, tool="wikipedia", args={"topic": subject or detail})

        return Action(
            ACTION_REPLY,
            text=(
                f"'{detail}' needs my full reasoning core. Everything hands-on "
                "still worked; add an API key to .env and I'll take this "
                "kind of request end-to-end."
            ),
        )

    def reflect(self, context: dict) -> Decision:

        pending = context.get("pending", [])

        if pending:
            return Decision(decision="continue", reason="Steps remain.")

        return Decision(decision="complete", reason="All steps executed.")

    def summarize(self, context: dict) -> str:

        done = context.get("done", [])
        failed = context.get("failed", [])

        lines = []

        for item in done:

            result = str(item.get("result", "")).strip()

            first = result.splitlines()[0] if result else "done"

            lines.append(f"• {item['title']}: {first}")

        summary = "Mission complete, Boss."

        if lines:
            summary += "\n" + "\n".join(lines)

        if failed:
            summary += f"\n{len(failed)} step(s) could not finish; I've noted them."

        return summary

    def converse(self, message: str, history: list, memory: dict):

        text = (message or "").strip()
        lowered = text.lower()

        # Factual questions still work offline through Wikipedia.
        for starter in QUESTION_STARTERS:

            if lowered.startswith(starter):

                topic = text[len(starter):].strip(" ?.")

                if topic and not any(ch.isdigit() for ch in topic[:2]):

                    result = execute("wikipedia", {"topic": topic})

                    if result.ok:
                        yield result.output
                        return

                    yield result.output
                    return

        # Single-action helper commands (voice-friendly): open a site, do the
        # maths, set a reminder — run the tool instead of apologising for the
        # missing reasoning core.
        hint, payload = classify(text)
        self.last_side_effects = []

        if hint in ("browser", "calculator", "wikipedia", "search", "time", "date"):

            tool, args = self._single_tool(hint, payload, text)

            result = execute(tool, args)

            data = result.data if isinstance(result.data, dict) else {}

            # Surface live side-effects the same way missions do.
            if isinstance(data.get("web"), dict) and data["web"].get("url"):
                self.last_side_effects.append(
                    {"type": "web.open", "url": data["web"]["url"], "title": data["web"].get("title", "")}
                )

            if isinstance(data.get("notify"), dict):
                self.last_side_effects.append(
                    {"type": "system.notify", "title": data["notify"].get("title", "Alice"), "body": data["notify"].get("body", "")}
                )

            yield result.output if result.ok else result.output
            return

        yield AI_NO_KEY.format(title=boss())

    def _single_tool(self, hint: str, payload: str, detail: str):
        """Map a classified intent to (tool, args) for a hands-on command."""

        if hint == "browser":
            return ("open_website", {"target": payload or detail})

        if hint == "calculator":
            expression = (payload or detail).strip()
            return ("calculator", {"expression": expression})

        if hint == "wikipedia":
            topic = (payload or detail).strip(" ?.")
            return ("wikipedia", {"topic": topic})

        if hint == "search":
            return ("web_search", {"query": payload or detail})

        if hint == "time":
            return ("current_time", {})

        if hint == "date":
            return ("current_date", {})

        return ("answer", {})
