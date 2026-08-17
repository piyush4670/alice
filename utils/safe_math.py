"""Safe arithmetic evaluation.

Replaces eval() with an AST walker that accepts only numeric literals and
the arithmetic operators ALICE documents. Every other syntax node is
rejected, so no attribute access, name lookup or function call can occur.
"""

import ast
import operator


MAX_EXPONENT = 100

MAX_POWER_BASE = 10 ** 15

MAX_RESULT_DIGITS = 4300


BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class MathError(Exception):
    """Raised when an expression cannot be evaluated safely."""


def evaluate(expression: str):

    expression = expression.strip()

    if not expression:
        raise MathError("There's no expression to calculate.")

    try:
        tree = ast.parse(expression, mode="eval")

    except (SyntaxError, ValueError, MemoryError):
        raise MathError("That doesn't look like a valid expression.")

    return evaluate_node(tree.body)


def evaluate_node(node):

    if isinstance(node, ast.Constant):
        return read_number(node)

    if isinstance(node, ast.BinOp):
        return apply_binary(node)

    if isinstance(node, ast.UnaryOp):
        return apply_unary(node)

    raise MathError("I can only handle plain arithmetic.")


def read_number(node):

    value = node.value

    if isinstance(value, bool):
        raise MathError("I can only handle numbers.")

    if not isinstance(value, (int, float)):
        raise MathError("I can only handle numbers.")

    return value


def apply_binary(node):

    action = BINARY_OPERATORS.get(type(node.op))

    if action is None:
        raise MathError("That operator isn't supported.")

    left = evaluate_node(node.left)
    right = evaluate_node(node.right)

    if isinstance(node.op, ast.Pow):
        guard_power(left, right)

    try:
        result = action(left, right)

    except ZeroDivisionError:
        raise MathError("I can't divide by zero.")

    except (OverflowError, ValueError):
        raise MathError("That number is too large for me to handle.")

    guard_size(result)

    return result


def apply_unary(node):

    action = UNARY_OPERATORS.get(type(node.op))

    if action is None:
        raise MathError("That operator isn't supported.")

    return action(evaluate_node(node.operand))


def guard_power(base, exponent):
    """Reject exponentiation that would hang the process."""

    if abs(exponent) > MAX_EXPONENT:
        raise MathError("That exponent is too large for me to handle.")

    if abs(base) > MAX_POWER_BASE:
        raise MathError("That number is too large for me to handle.")


def guard_size(result):

    if isinstance(result, int) and abs(result) > 10 ** MAX_RESULT_DIGITS:
        raise MathError("That number is too large for me to handle.")


def format_result(result):
    """Render 10 / 2 as '5' rather than '5.0'."""

    if isinstance(result, float) and result.is_integer():
        return str(int(result))

    if isinstance(result, float):
        return str(round(result, 10))

    return str(result)
