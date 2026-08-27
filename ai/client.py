"""Unified OpenAI-compatible chat client.

Every request Alice's linked brain makes goes through here: one place
for headers, timeouts, retries and JSON-safe parsing.
"""

import json
import re

import requests

from core.config import API_KEY, BASE_URL, MODEL, REQUEST_TIMEOUT, has_api_key

JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def headers() -> dict:

    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def payload(messages, json_mode=False, temperature=0.6) -> dict:

    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    if json_mode:
        body["response_format"] = {"type": "json_object"}

    return body


def extract_json(text: str):
    """Pull the first JSON object out of a model reply.

    Models wrap JSON in prose or code fences despite instructions;
    Alice should never crash because of decoration.
    """

    if not text:
        return None

    candidate = text.strip()

    fenced = JSON_FENCE.search(candidate)

    if fenced:
        candidate = fenced.group(1).strip()

    if not candidate.startswith("{"):

        match = re.search(r"\{.*\}", candidate, re.DOTALL)

        if not match:
            return None

        candidate = match.group(0)

    try:
        return json.loads(candidate)

    except ValueError:

        # Trailing commas are the most common offence.
        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)

        try:
            return json.loads(repaired)

        except ValueError:
            return None


def chat(messages, json_mode=False, temperature=0.6) -> str:
    """One-shot completion. Raises BrainUnavailable on any failure."""

    if not has_api_key():
        raise BrainUnavailable("No API key configured.")

    try:
        response = requests.post(
            BASE_URL,
            headers=headers(),
            json=payload(messages, json_mode, temperature),
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    except requests.RequestException as exc:
        raise BrainUnavailable(f"Provider unreachable: {exc}") from exc

    except (KeyError, IndexError, ValueError) as exc:
        raise BrainUnavailable(f"Unexpected provider reply: {exc}") from exc


def chat_stream(messages, temperature=0.6):
    """Yield text chunks as they arrive. Raises BrainUnavailable.

    Requests SSE streaming explicitly. If the provider returns a normal
    JSON body instead (some proxies strip `stream`), we still yield the
    full message so Alice never goes silent.
    """

    if not has_api_key():
        raise BrainUnavailable("No API key configured.")

    body = payload(messages, temperature=temperature)
    body["stream"] = True

    try:
        response = requests.post(
            BASE_URL,
            headers=headers(),
            json=body,
            timeout=REQUEST_TIMEOUT,
            stream=True,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise BrainUnavailable(f"Provider unreachable: {exc}") from exc

    collected = []
    content_type = (response.headers.get("content-type") or "").lower()

    # Non-SSE fallback: some gateways ignore stream=true and return JSON.
    if "application/json" in content_type and "text/event-stream" not in content_type:

        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise BrainUnavailable(f"Unexpected provider reply: {exc}") from exc

        if not text:
            raise BrainUnavailable("Model returned an empty reply.")

        yield text
        return

    try:
        for line in response.iter_lines(decode_unicode=True):

            if not line:
                continue

            if isinstance(line, bytes):
                try:
                    line = line.decode("utf-8", errors="replace")
                except Exception:
                    continue

            if not line.startswith("data:"):
                # Some providers send the whole JSON as one non-SSE body
                # chunk without a proper content-type — try once.
                if line.lstrip().startswith("{") and not collected:
                    try:
                        data = json.loads(line)
                        text = data["choices"][0]["message"]["content"].strip()
                        if text:
                            collected.append(text)
                            yield text
                            return
                    except (ValueError, KeyError, IndexError, TypeError):
                        pass
                continue

            data = line[5:].strip()

            if data == "[DONE]":
                break

            try:
                chunk = json.loads(data)
            except ValueError:
                continue

            try:
                delta = chunk["choices"][0].get("delta") or {}
                piece = delta.get("content") or ""
                # A few providers put the full message on the final chunk.
                if not piece:
                    msg = chunk["choices"][0].get("message") or {}
                    piece = msg.get("content") or ""
            except (KeyError, IndexError, TypeError):
                continue

            if piece:
                collected.append(piece)
                yield piece

    except requests.RequestException as exc:
        raise BrainUnavailable(f"Stream interrupted: {exc}") from exc

    if not "".join(collected).strip():
        # Last resort: non-stream completion so the user still gets an answer.
        try:
            text = chat(messages, temperature=temperature)
        except BrainUnavailable:
            raise BrainUnavailable("Model returned an empty reply.")

        if text:
            yield text
            return

        raise BrainUnavailable("Model returned an empty reply.")


def chat_json(messages, temperature=0.3) -> dict:
    """Completion that must return a JSON object."""

    for attempt in range(2):

        raw = chat(messages, json_mode=attempt == 0, temperature=temperature)

        parsed = extract_json(raw)

        if isinstance(parsed, dict):
            return parsed

    raise BrainUnavailable("Model did not return usable JSON.")


class BrainUnavailable(Exception):
    """Raised when the linked brain cannot be reached or understood."""
