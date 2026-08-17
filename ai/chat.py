import requests

from ai.prompts import build_prompt
from ai.reasoning import analyze
from core.config import API_KEY, BASE_URL, MODEL, REQUEST_TIMEOUT, has_api_key
from core.personality import AI_NO_KEY, AI_UNAVAILABLE, boss
from core.response import error, success


def ask(message, history, memory):

    if not has_api_key():
        return error(
            AI_NO_KEY.format(title=boss()),
            source="ai",
        )

    reasoning = analyze(message, history, memory)

    prompt = build_prompt(history, memory, reasoning, message)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    try:
        response = requests.post(
            BASE_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        reply = data["choices"][0]["message"]["content"].strip()

    except requests.RequestException:
        return error(
            AI_UNAVAILABLE.format(title=boss()),
            source="ai",
        )

    except (KeyError, IndexError, ValueError):
        return error(
            AI_UNAVAILABLE.format(title=boss()),
            source="ai",
        )

    if not reply:
        return error(
            AI_UNAVAILABLE.format(title=boss()),
            source="ai",
        )

    return success(reply, source="ai")
