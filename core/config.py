"""Single source of truth for every configurable value.

Nothing in ALICE should re-declare these constants locally.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ===========
# Paths
# ===========

DATA_DIR = Path(os.getenv("ALICE_DATA_DIR", "data"))

MEMORY_FILE = DATA_DIR / "profile.json"

REMINDER_FILE = DATA_DIR / "reminders.json"

NOTES_FILE = DATA_DIR / "notes.json"

TODO_FILE = DATA_DIR / "todos.json"

# ===========
# AI Provider
# ===========

API_KEY = os.getenv("API_KEY")

MODEL = os.getenv("ALICE_MODEL", "llama-3.3-70b-versatile")

BASE_URL = os.getenv(
    "ALICE_BASE_URL",
    "https://api.groq.com/openai/v1/chat/completions",
)

REQUEST_TIMEOUT = 30

# ===========
# Server
# ===========

SERVER_HOST = os.getenv("ALICE_HOST", "0.0.0.0")

# Hosters inject their own port through PORT (Render, Hugging Face, Koyeb);
# ALICE_PORT always wins when set explicitly.
SERVER_PORT = int(os.getenv("ALICE_PORT") or os.getenv("PORT") or "8000")

# ===========
# Agent
# ===========

# Hard ceiling on executed steps per mission. Alice stops here and reports.
AGENT_MAX_STEPS = int(os.getenv("ALICE_AGENT_MAX_STEPS", "24"))

# How many tool/brain rounds one step may take before Alice moves on.
AGENT_ROUNDS_PER_STEP = int(os.getenv("ALICE_AGENT_ROUNDS_PER_STEP", "5"))

# How long Alice waits for the user's answer to a mission question.
AGENT_ASK_TIMEOUT = int(os.getenv("ALICE_AGENT_ASK_TIMEOUT", "600"))

WORKSPACE_DIR = DATA_DIR / "workspace"

ALICE_VERSION = "2.0"

# ===========
# Context
# ===========

MAX_HISTORY = 20

# How much conversation history may be sent to the model, in characters.
MAX_HISTORY_CHARS = 4000

# How much stored memory may be sent to the model, in characters.
MAX_MEMORY_CHARS = 1500

# ===========
# Personality
# ===========

ASSISTANT_NAME = "ALICE"

USER_TITLE = "Boss"


def has_api_key() -> bool:
    return bool(API_KEY and API_KEY.strip())
