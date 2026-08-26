"""A small HTML proxy so ALICE's embedded browser can show real websites.

Most sites send ``X-Frame-Options: SAMEORIGIN`` (or a ``frame-ancestors``
CSP) and refuse to render inside an iframe. This endpoint fetches a page
server-side, protects against SSRF, and re-serves it from ALICE's own origin
with the frame-busting headers gone and relative links re-anchored to the
target site. Only text/html is handled; everything else is fetched and passed
through for the still-useful case of simple assets.

Security is deliberately conservative:
- https/http only,
- private / loopback / link-local hosts rejected,
- response size capped,
- no cookies are forwarded.
"""

import re

import requests

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

router = APIRouter(prefix="/web")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TIMEOUT = 15
MAX_BYTES = 2_000_000

_BASE_RE = re.compile(r"<base\b[^>]*>", re.IGNORECASE)
_CSP_META_RE = re.compile(
    r'<meta[^>]+content=["\'][^"\']*Content-Security-Policy[^"\']*["\'][^>]*>',
    re.IGNORECASE,
)
_META_REFRESH_RE = re.compile(
    r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]*>', re.IGNORECASE
)


def _is_private_host(host: str) -> bool:
    if not host:
        return True

    host = host.lower()

    if host in ("localhost", "localhost.localdomain"):
        return True

    if host == "0.0.0.0":
        return True

    if host.startswith("127.") or host.startswith("169.254.") or host.startswith("10."):
        return True

    if host.startswith("192.168."):
        return True

    # 172.16.0.0 – 172.31.255.255
    match = re.match(r"^172\.(\d+)\.", host)
    if match and 16 <= int(match.group(1)) <= 31:
        return True

    # IPv6 loopback / link-local
    if host in ("::1", "::") or host.startswith("fe80:"):
        return True

    return False


def _safe_url(raw: str) -> str:
    from urllib.parse import urlparse

    if not raw:
        raise HTTPException(400, "No url given.")

    parsed = urlparse(raw)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Only http and https URLs are allowed.")

    if _is_private_host(parsed.hostname or ""):
        raise HTTPException(400, "That address is not reachable from here.")

    return raw


def _anchor(body: str, base_url: str) -> str:
    body = _BASE_RE.sub("", body)
    body = _CSP_META_RE.sub("", body)
    body = _META_REFRESH_RE.sub("", body)
    return (
        '<base href="%s"><!doctype html>\n<div id="__alice_proxy_note" '
        'style="position:fixed;top:0;left:0;right:0;background:rgba(4,14,28,.9);'
        'color:#7ba3c7;font:11px monospace;padding:4px 10px;z-index:9999">'
        "ALICE·browser (proxied)</div>\n" % base_url
    ) + body


@router.get("/proxy")
def proxy(url: str = Query(...)):
    raw = _safe_url(url)

    try:
        response = requests.get(
            raw,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=False,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(502, f"Could not load that page ({exc.__class__.__name__}).")

    content_type = response.headers.get("Content-Type", "")

    if "text/html" in content_type:
        base = response.url or raw
        html = _anchor(response.text[:MAX_BYTES], base)
        return HTMLResponse(html)

    if response.headers.get("Content-Type", "").startswith("text/"):
        return PlainTextResponse(response.text[:MAX_BYTES], media_type="text/plain; charset=utf-8")

    return Response(
        content=response.content[:MAX_BYTES],
        media_type=content_type or "application/octet-stream",
    )
