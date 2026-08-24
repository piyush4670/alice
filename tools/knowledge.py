"""Knowledge tools: web search and Wikipedia.

Both run without API keys. If the network is unreachable the tools fail
softly with a clear observation, so Alice can reason around the gap
instead of crashing the mission.
"""

import re
from html import unescape
from urllib.parse import quote_plus, unquote

import requests

from tools.results import ToolResult

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TIMEOUT = 12

RESULT_LINK = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)

RESULT_SNIPPET = re.compile(
    r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
    re.DOTALL,
)

TAGS = re.compile(r"<[^>]+>")


def clean(text: str) -> str:

    text = TAGS.sub("", text or "")
    text = unescape(text)

    return re.sub(r"\s+", " ", text).strip()


def real_url(href: str) -> str:

    # DuckDuckGo wraps destinations in a redirect parameter.
    if "uddg=" in href:
        quoted = href.split("uddg=", 1)[1].split("&", 1)[0]

        try:
            return unquote(quoted)
        except ValueError:
            return href

    return href


def web_search(query: str) -> ToolResult:

    query = (query or "").strip()

    if not query:
        return ToolResult(False, "No search query given.")

    try:
        response = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        return ToolResult(
            False,
            f"Web search is unreachable right now ({exc.__class__.__name__}). "
            "Continue with what you already know and say so in the final answer.",
        )

    links = RESULT_LINK.findall(response.text)
    snippets = RESULT_SNIPPET.findall(response.text)

    if not links:
        return ToolResult(
            False,
            "No results found. Try a different query or use the wikipedia tool.",
        )

    lines = []

    for index, (href, title) in enumerate(links[:6], start=1):

        snippet = clean(snippets[index - 1]) if index - 1 < len(snippets) else ""

        line = f"{index}. {clean(title)} — {real_url(href)}"

        if snippet:
            line += f"\n   {snippet[:280]}"

        lines.append(line)

    return ToolResult(
        True,
        "Search results:\n" + "\n".join(lines),
        {"query": query, "results": [clean(t) for _, t in links[:6]]},
    )


def wikipedia(topic: str) -> ToolResult:

    topic = (topic or "").strip()

    if not topic:
        return ToolResult(False, "No topic given.")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        search = session.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "srlimit": 1,
                "format": "json",
            },
            timeout=TIMEOUT,
        )

        search.raise_for_status()

        hits = search.json().get("query", {}).get("search", [])

        if not hits:
            return ToolResult(False, f"Wikipedia has no article matching '{topic}'.")

        title = hits[0]["title"]

        summary = session.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title.replace(' ', '_'))}",
            timeout=TIMEOUT,
        )

        summary.raise_for_status()

        data = summary.json()

        extract = data.get("extract") or "The article had no summary text."

        return ToolResult(
            True,
            f"{title} (Wikipedia):\n{extract}",
            {"title": title, "url": data.get("content_urls", {})
                .get("desktop", {})
                .get("page", "")},
        )

    except requests.RequestException as exc:
        return ToolResult(
            False,
            f"Wikipedia is unreachable right now ({exc.__class__.__name__}). "
            "Continue with existing knowledge and note the limitation.",
        )
