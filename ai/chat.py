import requests

from ai.prompts import build_prompt
from ai.reasoning import analyze

from core.config import API_KEY, MODEL, BASE_URL
from core.response import success, error


def ask(message, history, memory):

    reasoning = analyze(
        message,
        history,
        memory,
    )

    prompt = build_prompt(
        history,
        memory,
        reasoning,
        message,
    )

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
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        reply = data["choices"][0]["message"]["content"].strip()

        return success(
            reply,
            source="ai",
        )

    except requests.RequestException:

        return error(
            "My AI brain is temporarily unavailable. Please try again in a moment.",
            source="ai",
        )
