"""The passcode gate.

When ALICE_PASSCODE is set, every API route and the WebSocket refuse
strangers until they present a session cookie that only the correct
passcode can produce. The cookie is an HMAC of the passcode, so there
is no session store to lose and changing the passcode logs everyone
out instantly.
"""

import hashlib
import hmac
import time

from core import config

COOKIE_NAME = "alice_key"

TOKEN_MESSAGE = b"alice-session-v1"

COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # thirty days

MAX_ATTEMPTS = 5

WINDOW_SECONDS = 60

_attempts = {}  # ip -> [attempt timestamps]


def enabled() -> bool:
    """Read dynamically so tests and env reloads are honoured."""

    return bool(getattr(config, "PASSCODE", ""))


def token() -> str:
    return hmac.new(
        config.PASSCODE.encode("utf-8"),
        TOKEN_MESSAGE,
        hashlib.sha256,
    ).hexdigest()


def valid_token(value) -> bool:

    if not enabled():
        return True

    return bool(value) and hmac.compare_digest(str(value), token())


def authorised(request) -> bool:

    if not enabled():
        return True

    return valid_token(request.cookies.get(COOKIE_NAME))


def check_passcode(candidate: str) -> bool:

    if not enabled():
        return True

    candidate = (candidate or "").strip()

    if not candidate:
        return False

    return hmac.compare_digest(candidate, config.PASSCODE)


def allowed_to_attempt(ip: str) -> bool:
    """Simple in-memory throttle: MAX_ATTEMPTS per window per IP."""

    now = time.time()

    recent = [
        stamp
        for stamp in _attempts.get(ip, [])
        if now - stamp < WINDOW_SECONDS
    ]

    recent.append(now)

    _attempts[ip] = recent

    return len(recent) <= MAX_ATTEMPTS
