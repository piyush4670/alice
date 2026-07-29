from datetime import datetime

from core.response import success


def current_time():

    now = datetime.now()

    return success(
        f"The current time is {now.strftime('%I:%M %p')}.",
        source="time",
    )


def today():

    now = datetime.now()

    return success(
        f"Today is {now.strftime('%A, %d %B %Y')}.",
        source="time",
    )


def handle(message: str):

    message = message.lower().strip()

    if "time" in message:
        return current_time()

    if "date" in message or "today" in message:
        return today()

    return success(
        "I couldn't understand your time request.",
        source="time",
    )
