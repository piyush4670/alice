import json
from pathlib import Path


MEMORY_FILE = Path("data/profile.json")


def load_memory():

    if not MEMORY_FILE.exists():
        return {}

    try:
        with open(MEMORY_FILE, "r") as file:
            return json.load(file)

    except Exception:
        return {}


def save_memory(memory):

    with open(MEMORY_FILE, "w") as file:
        json.dump(memory, file, indent=4)
