"""Built-in offline tools: maths and the clock."""

from datetime import datetime

from utils.safe_math import MathError, evaluate

from tools.results import ToolResult


def calculator(expression: str) -> ToolResult:

    try:
        result = evaluate(expression)

    except MathError as exc:
        return ToolResult(False, str(exc))

    pretty = f"{result:,}" if isinstance(result, int) else str(result)

    return ToolResult(True, f"{expression.strip()} = {pretty}", {"value": result})


def current_time() -> ToolResult:

    now = datetime.now()

    return ToolResult(
        True,
        now.strftime("It is %H:%M (%I:%M %p) on a 24-hour local clock."),
        {"iso": now.isoformat()},
    )


def current_date() -> ToolResult:

    now = datetime.now()

    return ToolResult(
        True,
        now.strftime("Today is %A, %d %B %Y."),
        {"iso": now.date().isoformat()},
    )
