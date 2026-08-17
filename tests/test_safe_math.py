"""Security tests for the arithmetic evaluator.

These cover the eval() sandbox escape and denial-of-service that the
previous implementation allowed.
"""

import pytest

from utils.safe_math import MathError, evaluate, format_result


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("2+2", 4),
        ("10 - 3", 7),
        ("6 * 7", 42),
        ("10 / 4", 2.5),
        ("10 % 3", 1),
        ("2 ** 8", 256),
        ("(2 + 3) * 4", 20),
        ("-5 + 2", -3),
        ("2 + 3 * 4", 14),
        ("7 // 2", 3),
        ("1.5 + 1.5", 3.0),
    ],
)
def test_arithmetic(expression, expected):
    assert evaluate(expression) == expected


@pytest.mark.parametrize(
    "attack",
    [
        # The exact escape reproduced against the old eval() implementation.
        "(1).__class__.__mro__[1].__subclasses__()",
        "__import__('os').system('echo pwned')",
        "().__class__.__bases__[0].__subclasses__()",
        "open('/etc/passwd').read()",
        "eval('1+1')",
        "exec('x=1')",
        "[x for x in range(10)]",
        "lambda: 1",
        "print(1)",
        "globals()",
        "1 if True else 2",
        "'abc' * 3",
        "x",
        "True",
    ],
)
def test_rejects_code_execution(attack):
    with pytest.raises(MathError):
        evaluate(attack)


@pytest.mark.parametrize(
    "bomb",
    [
        "9**9**9",
        "10**1000000",
        "99999999 ** 99999",
    ],
)
def test_rejects_resource_exhaustion(bomb):
    """These hung the process for minutes under the old implementation."""

    with pytest.raises(MathError):
        evaluate(bomb)


def test_divide_by_zero_has_a_clear_message():
    with pytest.raises(MathError, match="divide by zero"):
        evaluate("1/0")


def test_empty_expression():
    with pytest.raises(MathError):
        evaluate("   ")


@pytest.mark.parametrize(
    "value, expected",
    [
        (4, "4"),
        (2.5, "2.5"),
        (6.0, "6"),
        (0.30000000000000004, "0.3"),
    ],
)
def test_format_result(value, expected):
    assert format_result(value) == expected
