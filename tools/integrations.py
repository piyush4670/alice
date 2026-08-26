"""Web and device integration tools.

These let ALICE surface things in the browser UI rather than only through
text — opening a website in the embedded view, or raising a notification.
Each returns a structured ``ToolResult`` whose ``data`` carries a key the
mission engine translates into a live UI event.
"""

import re
from urllib.parse import quote_plus

from tools.results import ToolResult

# Quick app shortcuts so "open youtube" / "search google" resolve instantly.
SITES = {
    "youtube": "https://www.youtube.com",
    "youtube search": "https://www.youtube.com/results?search_query={query}",
    "google": "https://www.google.com",
    "google search": "https://www.google.com/search?q={query}",
    "wikipedia": "https://en.wikipedia.org/wiki/{query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
    "news": "https://news.google.com",
    "maps search": "https://www.google.com/maps/search/{query}",
}

SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)

# Anything that looks like a bare domain, e.g. "example.com" or "arxiv.org".
DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(:\d+)?(/.*)?$", re.IGNORECASE)


def _as_url(target: str) -> str:
    target = (target or "").strip()

    if not target:
        return None

    if SCHEME_RE.match(target):
        return target

    if DOMAIN_RE.match(target):
        return "https://" + target

    return None


def open_website(target: str) -> ToolResult:
    """Open a site in ALICE's embedded browser view, or web-search target."""

    target = (target or "").strip()

    if not target:
        return ToolResult(False, "Give me a site or something to look up.")

    lowered = target.lower().rstrip("?")

    # "open youtube" / "search google" style shortcut.
    for phrase in SITES:
        if lowered == phrase or lowered == phrase.replace(" ", ""):
            return ToolResult(
                True,
                f"Opening {phrase} in the web deck.",
                {"web": {"url": SITES[phrase].format(query=""), "title": phrase.title()}},
            )

    url = _as_url(target)

    if url:
        return ToolResult(True, f"Opening {url}", {"web": {"url": url, "title": target}})

    # Otherwise treat it as a search query on DuckDuckGo.
    query = quote_plus(target)
    search_url = f"https://duckduckgo.com/?q={query}"

    return ToolResult(
        True,
        f"Searching the web for \"{target}\" — opened in the web deck.",
        {"web": {"url": search_url, "title": target}},
    )


def notify(title: str, body: str = "") -> ToolResult:
    """Raise a browser notification for the user."""

    title = (title or "Alice").strip()
    body = (body or "").strip()

    if not body:
        body = title or "Alice has something to tell you."

    return ToolResult(
        True,
        f"Notification sent: {title}",
        {"notify": {"title": title, "body": body}},
    )
