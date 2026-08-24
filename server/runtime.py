"""Runtime singletons.

The bus and orchestrator are created once and shared by routes,
sockets and background tasks.
"""

import time

from agent.orchestrator import Orchestrator
from server.bus import EventBus

STARTED_AT = time.time()

bus = EventBus()
orchestrator = Orchestrator(bus.emit)
