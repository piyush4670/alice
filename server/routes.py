"""REST routes: auth, system, tasks, memory, board and artifacts."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel


from core.config import WORKSPACE_DIR
from memory import manager as memory
from plugins.notes import load_notes
from plugins.reminder import load_reminders
from plugins.todo import load_tasks as load_todos
from tools.manage import remember as remember_tool
from tools.workspace import sanitise

from server import auth, telemetry
from server.runtime import orchestrator

router = APIRouter(prefix="/api")


class PasscodeBody(BaseModel):
    passcode: str = ""


class RememberBody(BaseModel):
    pair: str = ""
    key: str = ""
    value: str = ""


class MissionBody(BaseModel):
    goal: str


class AnswerBody(BaseModel):
    text: str


# ===========
# Auth
# ===========

@router.get("/auth/check")
def auth_check(request: Request):
    return {
        "required": auth.enabled(),
        "authorised": auth.authorised(request),
    }


@router.post("/auth")
def auth_passcode(request: Request, body: PasscodeBody):

    if not auth.enabled():
        return {"ok": True, "required": False}

    ip = request.client.host if request.client else "unknown"

    if not auth.allowed_to_attempt(ip):
        raise HTTPException(429, "Too many attempts. Wait a minute.")

    if not auth.check_passcode(body.passcode):
        raise HTTPException(401, "Wrong passcode.")

    response = JSONResponse({"ok": True, "required": True})

    response.set_cookie(
        auth.COOKIE_NAME,
        auth.token(),
        httponly=True,
        samesite="lax",
        max_age=auth.COOKIE_MAX_AGE,
    )

    return response


# ===========
# System
# ===========

@router.get("/system")
def system():
    return {
        "identity": telemetry.identity(orchestrator.brain_info()),
        "telemetry": telemetry.snapshot(),
    }


@router.get("/health")
def health():
    return {"ok": True}


# ===========
# Missions
# ===========

@router.get("/tasks")
def tasks():
    return {"tasks": orchestrator.snapshots()}


@router.post("/tasks")
def start_task(body: MissionBody):

    goal = body.goal.strip()

    if not goal:
        raise HTTPException(400, "A mission needs a goal.")

    orchestrator.refresh_brain()

    task = orchestrator.start_mission(goal)

    return {"task": task.snapshot()}


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str):

    if not orchestrator.cancel(task_id):
        raise HTTPException(404, "No cancellable mission with that id.")

    return {"ok": True}


@router.post("/tasks/{task_id}/answer")
def answer_task(task_id: str, body: AnswerBody):

    if not orchestrator.answer(task_id, body.text):
        raise HTTPException(404, "Alice is not waiting on that mission.")

    return {"ok": True}


# ===========
# Memory
# ===========

@router.get("/memory")
def get_memory():
    return {"items": memory.all_memory()}


@router.post("/memory")
def set_memory(body: RememberBody):

    pair = body.pair.strip() or f"{body.key} is {body.value}".strip()

    if pair.endswith(" is"):
        raise HTTPException(400, "Give me both a key and a value.")

    result = remember_tool(pair)

    if not result.ok:
        raise HTTPException(400, result.output)

    return {"items": memory.all_memory()}


@router.delete("/memory/{key}")
def delete_memory(key: str):

    memory.forget(key.lower())

    return {"items": memory.all_memory()}


# ===========
# Board: notes, todos, reminders
# ===========

@router.get("/board")
def board():
    return {
        "notes": load_notes(),
        "todos": load_todos(),
        "reminders": load_reminders(),
    }


# ===========
# Artifacts
# ===========

@router.get("/artifacts")
def artifacts():

    files = []

    if WORKSPACE_DIR.exists():

        for path in sorted(WORKSPACE_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):

            if path.is_file():
                files.append(
                    {
                        "name": path.name,
                        "size": path.stat().st_size,
                        "modified": path.stat().st_mtime,
                    }
                )

    return {"files": files}


@router.get("/artifacts/{name}")
def artifact(name: str):

    filename = sanitise(name)

    path = WORKSPACE_DIR / filename

    if not path.exists():
        raise HTTPException(404, "No such artifact.")

    return PlainTextResponse(path.read_text(encoding="utf-8"))
