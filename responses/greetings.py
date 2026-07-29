from core.response import success

from core.personality import (
    friend,
    WELCOME_MESSAGE,
    HELLO_MESSAGE,
    GOODBYE_MESSAGE,
)


def welcome(name):

    return success(
        WELCOME_MESSAGE.format(
            name=friend(),
        ),
        source="greetings",
    )


def hello(name):

    return success(
        HELLO_MESSAGE.format(
            name=friend(),
        ),
        source="greetings",
    )


def goodbye(name):

    return success(
        GOODBYE_MESSAGE.format(
            name=friend(),
        ),
        source="greetings",
    )
