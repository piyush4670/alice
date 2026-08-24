"""Lightweight telemetry for the status deck.

No new dependencies: best-effort readings that degrade to nulls on any
platform that does not expose them.
"""

import os
import platform
import shutil

from core.config import ALICE_VERSION, ASSISTANT_NAME, MODEL

from server.runtime import STARTED_AT


def _load_average():
    try:
        return round(os.getloadavg()[0], 2)
    except (AttributeError, OSError):
        return None


def _memory_percent():
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as file:
            info = {}

            for line in file:
                parts = line.split(":")

                if len(parts) == 2:
                    info[parts[0]] = int(parts[1].strip().split()[0])

        total = info.get("MemTotal")

        available = info.get("MemAvailable")

        if total and available is not None:
            return round(100 * (total - available) / total, 1)

    except (OSError, ValueError):
        pass

    return None


def _disk_percent():
    try:
        usage = shutil.disk_usage(os.getcwd())

        return round(100 * usage.used / usage.total, 1)

    except OSError:
        return None


def snapshot() -> dict:
    return {
        "time": os.times(),
        "cpu_load": _load_average(),
        "memory": _memory_percent(),
        "disk": _disk_percent(),
        "python": platform.python_version(),
        "system": platform.platform(),
    }


def identity(brain: dict) -> dict:
    return {
        "name": ASSISTANT_NAME.title(),
        "version": ALICE_VERSION,
        "model": MODEL,
        "brain": brain,
        "started_at": STARTED_AT,
        "host": platform.node() or "local",
    }
