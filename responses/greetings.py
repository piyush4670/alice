from core.personality import (
    GOODBYE_MESSAGE,
    HELLO_MESSAGE,
    WELCOME_MESSAGE,
    friend,
)
from core.response import success


def welcome():
    return success(
        WELCOME_MESSAGE.format(name=friend()),
        source="greetings",
    )


def hello():
    return success(
        HELLO_MESSAGE.format(name=friend()),
        source="greetings",
    )


def goodbye():
    return success(
        GOODBYE_MESSAGE.format(name=friend()),
        source="greetings",
    )
