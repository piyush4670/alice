"""Server-side speech-to-text.

Android Chrome's Web Speech API is unreliable (network errors, silent
drops, no continuous mode). The mic button records with MediaRecorder
(solid on every modern Android browser) and posts the clip here.

Transcription uses Groq's OpenAI-compatible Whisper endpoint when an
API key is configured — same free-tier key as the linked brain. Without
a key we return a clear error so the UI can fall back gracefully.
"""

from __future__ import annotations

import io
import logging

import requests

from core.config import API_KEY, has_api_key

log = logging.getLogger("alice.voice")

# Groq's OpenAI-compatible audio transcription endpoint.
WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
WHISPER_MODEL = "whisper-large-v3"
REQUEST_TIMEOUT = 45

# MIME → filename extension Whisper accepts.
EXT_FOR = {
    "audio/webm": "webm",
    "audio/webm;codecs=opus": "webm",
    "audio/ogg": "ogg",
    "audio/ogg;codecs=opus": "ogg",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
}


class TranscribeError(Exception):
    """Raised when audio cannot be turned into text."""


def _extension(content_type: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in EXT_FOR:
        return EXT_FOR[ct]
    # Some Android builds send bare "audio/webm; codecs=opus" already
    # normalised above; fall back to webm which Whisper always accepts.
    if "webm" in (content_type or "").lower():
        return "webm"
    if "ogg" in (content_type or "").lower():
        return "ogg"
    if "mp4" in (content_type or "").lower() or "m4a" in (content_type or "").lower():
        return "mp4"
    return "webm"


def transcribe(audio: bytes, content_type: str = "audio/webm", language: str = "en") -> str:
    """Turn a short audio clip into plain text.

    Raises TranscribeError on any failure the UI should surface.
    """

    if not audio or len(audio) < 64:
        raise TranscribeError("That recording was empty — try again.")

    if not has_api_key():
        raise TranscribeError(
            "Speech recognition needs an API key. "
            "Add API_KEY to your .env (free at console.groq.com) and restart."
        )

    ext = _extension(content_type)
    filename = f"alice-voice.{ext}"

    # Groq / OpenAI whisper endpoints accept multipart form uploads.
    files = {
        "file": (filename, io.BytesIO(audio), content_type or f"audio/{ext}"),
    }
    data = {
        "model": WHISPER_MODEL,
        "response_format": "json",
        "temperature": "0",
    }
    if language:
        data["language"] = language

    headers = {"Authorization": f"Bearer {API_KEY.strip()}"}

    try:
        response = requests.post(
            WHISPER_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        log.warning("whisper unreachable: %s", exc)
        raise TranscribeError("Speech service unreachable. Check your connection.") from exc

    if response.status_code >= 400:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "") or response.text[:200]
        except Exception:
            detail = response.text[:200]
        log.warning("whisper %s: %s", response.status_code, detail)
        raise TranscribeError(
            "Speech recognition failed"
            + (f": {detail}" if detail else ".")
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TranscribeError("Speech service returned an unreadable reply.") from exc

    text = str(payload.get("text") or "").strip()

    if not text:
        raise TranscribeError("I couldn't catch that — speak a little clearer and try again.")

    return text
