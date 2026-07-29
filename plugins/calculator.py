from core.response import success, error
from core.personality import boss


def calculate(expression: str):

    expression = expression.replace("calculate", "", 1).strip()

    try:

        result = eval(
            expression,
            {"__builtins__": {}},
            {},
        )

        return success(
            f"The result is {result}, {boss()}.",
            source="calculator",
            data=result,
        )

    except Exception:

        return error(
            "I couldn't calculate that expression.",
            source="calculator",
        )
