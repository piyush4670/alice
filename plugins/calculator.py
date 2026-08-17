from core.personality import boss, CALCULATOR_REPLY
from core.response import error, success

from utils.safe_math import MathError, evaluate, format_result


PREFIXES = (
    "calculate",
    "what is",
    "what's",
    "compute",
    "solve",
)


def clean(expression: str) -> str:

    expression = expression.strip()

    lowered = expression.lower()

    for prefix in PREFIXES:

        if lowered.startswith(prefix):
            expression = expression[len(prefix):]
            break

    return expression.strip().rstrip("=?").strip()


def calculate(expression: str):

    cleaned = clean(expression)

    try:
        result = evaluate(cleaned)

    except MathError as problem:

        return error(
            str(problem),
            source="calculator",
        )

    return success(
        CALCULATOR_REPLY.format(
            result=format_result(result),
            title=boss(),
        ),
        source="calculator",
        data=result,
    )
