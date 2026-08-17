"""System-level replies that belong to no single feature."""

from core.personality import boss
from core.response import error, info

STARTUP_BANNER = "=============================="

UNEXPECTED_ERROR = (
    "Something went wrong on my end, {title}. "
    "I've recovered - please try that again."
)


def empty_message():
    return info(
        "I'm listening.",
        source="system",
    )


def unexpected_error():
    return error(
        UNEXPECTED_ERROR.format(title=boss()),
        source="system",
    )
