"""The WebSocket endpoint: Alice's live wire.

Protocol (client -> server):
  {"type": "user.message", "text": "...", "mode": "auto|chat|mission"}
  {"type": "task.reply",   "task_id": "...", "text": "..."}
  {"type": "task.cancel",  "task_id": "..."}
  {"type": "user.name",    "name": "..."}
  {"type": "ping"}

Everything the server sends is a typed event; see bus emitters.
"""

import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from agent import conversation, triage
from core.personality import boss, set_user
from memory import manager as memory

from server import auth, telemetry
from server.runtime import bus, orchestrator

HEARTBEAT_SECONDS = 15


async def _sender(ws: WebSocket, queue: asyncio.Queue):

    while True:

        event = await queue.get()

        await ws.send_text(json.dumps(event, ensure_ascii=False))


async def _heartbeat(ws: WebSocket):

    while True:

        await asyncio.sleep(HEARTBEAT_SECONDS)

        await ws.send_text(
            json.dumps(
                {
                    "type": "system.telemetry",
                    "telemetry": telemetry.snapshot(),
                    "brain": orchestrator.brain_info(),
                }
            )
        )


async def _receiver(ws: WebSocket):

    while True:

        raw = await ws.receive_text()

        try:
            message = json.loads(raw)

        except ValueError:
            continue

        kind = message.get("type")

        if kind == "ping":
            await ws.send_text(json.dumps({"type": "pong"}))

        elif kind == "user.name":
            set_user(message.get("name", ""))

            await ws.send_text(
                json.dumps({"type": "user.updated", "name": boss()})
            )

        elif kind == "task.cancel":
            orchestrator.cancel(message.get("task_id", ""))

        elif kind == "task.reply":

            text = str(message.get("text", "")).strip()

            if text:
                orchestrator.answer(message.get("task_id", ""), text)

        elif kind == "user.message":

            text = str(message.get("text", "")).strip()
            mode = message.get("mode", "auto")

            if not text:
                continue

            goal, explicit = triage.strip_mission_prefix(text)

            wants_mission = mode == "mission" or (
                mode == "auto" and triage.looks_like_mission(text)
            )

            if wants_mission:
                orchestrator.refresh_brain()
                orchestrator.start_mission(goal)

            else:
                # Chat replies may stream for a while; never block the socket.
                await asyncio.to_thread(conversation.respond, text, bus.emit, orchestrator.brain)


async def socket(ws: WebSocket):

    await ws.accept()

    if not auth.authorised(ws):

        await ws.send_text(json.dumps({"type": "auth.required"}))

        await ws.close()

        return

    queue = await bus.subscribe()

    hello = {
        "type": "hello",
        "identity": telemetry.identity(orchestrator.brain_info()),
        "telemetry": telemetry.snapshot(),
        "memory": memory.all_memory(),
        "tasks": orchestrator.snapshots()[:12],
        "user": boss(),
    }

    tasks = [
        asyncio.create_task(_sender(ws, queue)),
        asyncio.create_task(_heartbeat(ws)),
        asyncio.create_task(_receiver(ws)),
    ]

    try:

        await ws.send_text(json.dumps(hello, ensure_ascii=False))

        await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_EXCEPTION,
        )

    except WebSocketDisconnect:
        pass

    finally:

        for task in tasks:
            task.cancel()

        bus.unsubscribe(queue)
