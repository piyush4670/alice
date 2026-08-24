"""Workspace tools: artifacts Alice writes for the user.

Every file lives inside the configured workspace directory. Names are
sanitised so no tool call can ever escape it.
"""

import re

from core.config import WORKSPACE_DIR

from tools.results import ToolResult

SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")

MAX_FILE_CHARS = 200_000


def sanitise(name: str) -> str:

    name = (name or "").strip().replace("\\", "/").split("/")[-1]

    name = SAFE_NAME.sub("-", name).strip(".-")

    if not name:
        name = "artifact"

    if "." not in name:
        name += ".md"

    return name


def write_file(name: str, body: str) -> ToolResult:

    filename = sanitise(name)
    body = str(body or "")[:MAX_FILE_CHARS]

    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    path = WORKSPACE_DIR / filename

    path.write_text(body, encoding="utf-8")

    return ToolResult(
        True,
        f"Wrote {filename} ({len(body)} characters) to the workspace.",
        {
            "artifact": {
                "name": filename,
                "path": str(path),
            }
        },
    )


def read_file(name: str) -> ToolResult:

    filename = sanitise(name)

    path = WORKSPACE_DIR / filename

    if not path.exists():
        return ToolResult(False, f"No file named {filename} in the workspace.")

    body = path.read_text(encoding="utf-8")

    if len(body) > 20_000:
        body = body[:20_000] + "\n... (truncated)"

    return ToolResult(True, body)
