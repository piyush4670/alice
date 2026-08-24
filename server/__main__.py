"""Launch Alice's web UI.

    python -m server
"""

import uvicorn

from core.config import SERVER_HOST, SERVER_PORT
from server.app import app


def main():

    print()
    print("  ╭──────────────────────────────────────────╮")
    print("  │   A L I C E   —   mission control online  │")
    print(f"  │   http://localhost:{SERVER_PORT:<22}│")
    print("  ╰──────────────────────────────────────────╯")
    print()

    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
