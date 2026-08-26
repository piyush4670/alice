"""Runtime singletons.

The bus and orchestrator are created once and shared by routes,
sockets and background tasks.
"""

import time

from agent.orchestrator import Orchestrator
from server.bus import EventBus
from server.scheduler import ReminderScheduler

STARTED_AT = time.time()

bus = EventBus()
orchestrator = Orchestrator(bus.emit)
scheduler = ReminderScheduler(bus.emit)
