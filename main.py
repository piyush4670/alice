"""ALICE entry point.

Starts ALICE, reads input, displays responses. No business logic here.
"""

from core.config import ASSISTANT_NAME
from core.context import add_message
from core.decision import is_exit
from core.personality import set_user
from core.response import Response
from core.router import route
from responses.greetings import goodbye, welcome
from responses.system import STARTUP_BANNER, unexpected_error


def show(reply: Response):
    print(f"\n{ASSISTANT_NAME.title()}: {reply.message}")


def banner():
    spaced = " ".join(ASSISTANT_NAME)

    print(STARTUP_BANNER)
    print(f"{spaced:^30}")
    print(STARTUP_BANNER)
    print()


def ask_name() -> str:
    try:
        return input("What's your name? ").strip()

    except (EOFError, KeyboardInterrupt):
        return ""


def read_input() -> str:
    return input("\nYou: ").strip()


def respond(message: str) -> Response:
    """Route one message, surviving any unexpected module failure."""

    try:
        return route(message)

    except Exception:
        return unexpected_error()


def conversation():

    while True:

        try:
            message = read_input()

        except (EOFError, KeyboardInterrupt):
            print()
            show(goodbye())
            return

        if not message:
            continue

        add_message("user", message)

        reply = respond(message)

        show(reply)

        add_message("assistant", reply.message)

        if is_exit(message):
            return


def main():

    banner()

    set_user(ask_name())

    show(welcome())

    conversation()


if __name__ == "__main__":
    main()
