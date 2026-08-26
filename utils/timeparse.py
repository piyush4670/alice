"""Resolve a human reminder time into a concrete :class:`datetime`.

ALICE stores reminders as human phrases ("tomorrow at 5pm", "next monday",
"tonight"). This module turns those phrases into a real wall-clock time so
the server scheduler knows exactly when to fire them. It is intentional and
small: relative day words, a clock, and a time-of-day qualifier are enough
to cover the reminder grammar.
"""

from datetime import datetime, timedelta

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

_WEEKDAY_INDEX = {name: i for i, name in enumerate(WEEKDAYS)}  # monday == 0

# Time-of-day words that imply a default hour when no clock is given.
QUALIFIERS = {
    "morning": 9,
    "afternoon": 15,
    "evening": 19,
    "tonight": 21,
    "night": 21,
    "this morning": 9,
    "this afternoon": 15,
    "this evening": 19,
}

DEFAULT_HOUR = 9


def _normalise(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.replace(" o'clock", "").replace(" oclock", "")
    text = text.replace(",", " ")
    return " ".join(text.split())


def _parse_day(text: str, now: datetime):
    """Return delta days from today, or ``None`` when no day word matched."""

    # "next week" -> +7 days
    if "next week" in text:
        return 7

    # "tomorrow"
    for marker in ("tomorrow", "tmrw", "tomorow"):
        if marker in text:
            return 1

    # "today"
    if text.startswith("today") or " today" in text:
        return 0

    # "next <weekday>"
    for name in WEEKDAYS:
        if f"next {name}" in text:
            offset = (_WEEKDAY_INDEX[name] - now.weekday()) % 7
            if offset == 0:
                offset = 7
            return offset

    # plain "<weekday>" -> the next occurrence (including today)
    for name in WEEKDAYS:
        if f" {name}" in text or text == name:
            offset = (_WEEKDAY_INDEX[name] - now.weekday()) % 7
            return offset

    if text in ("today",):
        return 0

    return None


def _parse_clock(text: str):
    """Return ``(hour, minute)`` for a clock phrase, else ``None``."""

    if "noon" in text:
        return (12, 0)
    if "midnight" in text:
        return (0, 0)

    # 12-hour, optional minutes and meridian: "5pm", "5:30 pm", "5 o'clock"
    hour, minute, meridian = _clock_12hr(text)

    # 24-hour: "17:30" (only if no meridian was matched)
    if hour is None:
        hour, minute, meridian = _clock_24hr(text)

    if hour is None:
        return None

    if meridian:
        meridian = meridian.lower()
        if meridian in ("pm", "p.m."):
            if hour < 12:
                hour += 12
        else:  # am
            if hour == 12:
                hour = 0

    if hour == 24:
        hour = 0

    return (hour % 24, minute % 60)


def _clock_12hr(text: str):
    import re

    match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)(?:\b|$)",
        text,
    )

    if not match:
        return (None, 0, None)

    return (int(match.group(1)), int(match.group(2) or 0), match.group(3))


def _clock_24hr(text: str):
    import re

    match = re.search(r"\b(\d{1,2}):(\d{2})\b", text)

    if not match:
        return (None, 0, None)

    return (int(match.group(1)), int(match.group(2)), None)


def _parse_qualifier(text: str):
    """Return a default hour from a time-of-day word, else ``None``."""

    for phrase, hour in QUALIFIERS.items():
        if phrase in text:
            return hour

    return None


def resolve(text: str, now: datetime = None) -> datetime:
    """Resolve a reminder phrase to a concrete :class:`datetime`.

    Returns ``None`` when the phrase cannot be interpreted.
    """

    now = now or datetime.now()
    text = _normalise(text)

    if not text:
        return None

    day_delta = _parse_day(text, now)
    clock = _parse_clock(text)
    qualifier = _parse_qualifier(text)

    if day_delta is None and clock is None and qualifier is None:
        return None

    target_date = now.date() + timedelta(days=day_delta or 0)

    if clock:
        hour, minute = clock
    elif qualifier is not None:
        hour, minute = qualifier, 0
    else:
        # a bare day word ("tomorrow") with no time -> default morning
        hour, minute = DEFAULT_HOUR, 0

    target = datetime.combine(target_date, datetime.min.time()).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    # A clock with no day word refers to today, unless that has already
    # passed, then it rolls to tomorrow (so "5pm" is always in the future).
    if day_delta is None and clock is not None and target <= now:
        target += timedelta(days=1)

    return target
