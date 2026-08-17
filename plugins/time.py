from datetime import datetime

from core.personality import DATE_REPLY, TIME_REPLY
from core.response import success

DATE_PATTERNS = (
    "date",
    "day",
)


def current_time():

    now = datetime.now()

    return success(
        TIME_REPLY.format(time=now.strftime("%I:%M %p").lstrip("0")),
        source="time",
    )


def today():

    now = datetime.now()

    return success(
        DATE_REPLY.format(date=now.strftime("%A, %d %B %Y")),
        source="time",
    )


def handle(message: str):

    text = (message or "").lower()

    if "time" in text:
        return current_time()

    return today()
