import os
from dotenv import load_dotenv

load_dotenv()

# ===========
# AI Provider
# ===========

API_KEY = os.getenv("API_KEY")

MODEL = "llama-3.3-70b-versatile"

BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# ===========
# Memory
# ===========

MEMORY_FILE = "data/profile.json"

# ===========
# Context
# ===========

MAX_HISTORY = 20

# ===========
# Personality
# ===========

ASSISTANT_NAME = "ALICE"

USER_TITLE = "Boss"
