"""Server-side text-to-speech so Alice can talk on every device.

Android Chrome's speechSynthesis is notoriously broken (voices never
load, utterances fire onend without audio, background tabs mute TTS).
When an API key is present we synthesise via Groq's OpenAI-compatible
TTS endpoint and stream an MP3 the browser plays with a plain <audio>
element — reliable on phones, tablets and desktops alike.

Without a key the frontend falls back to the browser synthesizer.
"""

from __future__ import annotations

import logging
import re

import requests

from core.config import API_KEY, has_api_key

log = logging.getLogger("alice.voice")

# Groq's OpenAI-compatible speech endpoint (PlayAI TTS).
TTS_URL = "https://api.groq.com/openai/v1/audio/speech"
TTS_MODEL = "playai-tts"
# A calm, clear female English voice that fits Alice.
DEFAULT_VOICE = "Celeste-PlayAI"
REQUEST_TIMEOUT = 45
MAX_CHARS = 1200

# Strip residual markdown / emoji noise that sounds awful when spoken.
CLEAN_RE = re.compile(
    r"("
    r"```[\s\S]*?```"          # fenced code
    r"|`[^`]+`"                 # inline code markers kept as text below
    r"|\*\*([^*]+)\*\*"         # bold
    r"|\*([^*]+)\*"             # italic
    r"|\[([^\]]+)\]\([^)]*\)"   # links
    r"|^#+\s*"                  # headings
    r"|^[-*•]\s*"               # bullets
    r"|💙|❤️|⏰|⏸"              # signature glyphs Alice uses in text
    r")",
    re.MULTILINE,
)


class SpeakError(Exception):
    """Raised when speech cannot be synthesised."""


def clean_for_speech(text: str) -> str:
    """Turn a chat reply into something that sounds natural out loud."""

    body = str(text or "")

    # Prefer targeted replacements so we keep the words inside markdown.
    body = re.sub(r"```[\s\S]*?```", " code block ", body)
    body = re.sub(r"`([^`]+)`", r"\1", body)
    body = re.sub(r"\*\*([^*]+)\*\*", r"\1", body)
    body = re.sub(r"\*([^*]+)\*", r"\1", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"^#+\s*", "", body, flags=re.MULTILINE)
    body = re.sub(r"^[-*•]\s*", "", body, flags=re.MULTILINE)
    body = re.sub(r"[💙❤️⏰⏸✅❌·•]+", " ", body)
    body = re.sub(r"\s+", " ", body).strip()

    return body[:MAX_CHARS]


def synthesize(text: str, voice: str = "") -> tuple[bytes, str]:
    """Return (audio_bytes, mime_type) for the given text.

    Raises SpeakError on any failure the route should surface as 502.
    """

    body = clean_for_speech(text)

    if not body:
        raise SpeakError("Nothing to speak.")

    if not has_api_key():
        raise SpeakError(
            "Speech synthesis needs an API key. "
            "Add API_KEY to your .env (free at console.groq.com)."
        )

    payload = {
        "model": TTS_MODEL,
        "voice": (voice or DEFAULT_VOICE).strip() or DEFAULT_VOICE,
        "input": body,
        "response_format": "mp3",
    }

    headers = {
        "Authorization": f"Bearer {API_KEY.strip()}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            TTS_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        log.warning("tts unreachable: %s", exc)
        raise SpeakError("Speech service unreachable. Check your connection.") from exc

    if response.status_code >= 400:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "") or response.text[:200]
        except Exception:
            detail = response.text[:200]
        log.warning("tts %s: %s", response.status_code, detail)
        raise SpeakError(
            "Speech synthesis failed" + (f": {detail}" if detail else ".")
        )

    audio = response.content or b""

    if len(audio) < 64:
        raise SpeakError("Speech service returned empty audio.")

    mime = response.headers.get("content-type") or "audio/mpeg"
    if "json" in mime:
        # Some providers return JSON errors with a 200 — treat as failure.
        raise SpeakError("Speech service returned an unexpected payload.")

    return audio, "audio/mpeg"
