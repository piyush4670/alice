from responses.greetings import welcome

from core.router import route
from core.context import add_message
from core.personality import set_user


def main():

    print("══════════════════════════════")
    print("         A L I C E")
    print("══════════════════════════════")
    print()

    name = input("What's your name? ").strip().title()

    set_user(name)

    greeting = welcome(name)

    print(greeting.message)

    while True:

        message = input("\nYou: ")

        add_message("user", message)

        reply = route(message, name)

        print(f"\nAlice: {reply.message}")

        add_message("assistant", reply.message)

        if message.lower() in (
            "bye",
            "goodbye",
            "exit",
            "quit",
        ):
            break


if __name__ == "__main__":
    main()
