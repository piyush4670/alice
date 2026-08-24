"""Tests for the passcode gate."""

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")


from fastapi.testclient import TestClient  # noqa: E402

from core import config
from server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def no_passcode(monkeypatch):
    monkeypatch.setattr(config, "PASSCODE", "")

    from server import auth

    monkeypatch.setattr(auth, "_attempts", {})

    yield


def authed_client(monkeypatch, passcode="swordfish"):
    monkeypatch.setattr(config, "PASSCODE", passcode)

    return TestClient(create_app())


def test_gate_disabled_leaves_everything_open(client):

    response = client.get("/api/system")

    assert response.status_code == 200


def test_gate_blocks_api_without_cookie(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    blocked = TestClient(create_app())

    assert blocked.get("/api/system").status_code == 401
    assert blocked.get("/api/memory").status_code == 401
    assert blocked.get("/api/tasks").status_code == 401


def test_health_and_auth_stay_public(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    blocked = TestClient(create_app())

    assert blocked.get("/api/health").status_code == 200
    assert blocked.get("/api/auth/check").json()["required"] is True


def test_wrong_passcode_is_rejected(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    blocked = TestClient(create_app())

    assert blocked.post("/api/auth", json={"passcode": "nope"}).status_code == 401


def test_correct_passcode_unlocks_the_api(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    unlocked = TestClient(create_app())

    reply = unlocked.post("/api/auth", json={"passcode": "swordfish"})

    assert reply.status_code == 200
    assert reply.json()["ok"] is True

    assert unlocked.get("/api/system").status_code == 200
    assert unlocked.get("/api/auth/check").json()["authorised"] is True


def test_brute_force_is_throttled(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    blocked = TestClient(create_app())

    codes = [
        blocked.post("/api/auth", json={"passcode": "wrong"}).status_code
        for _ in range(7)
    ]

    assert 401 in codes
    assert 429 in codes


def test_websocket_demands_auth(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    blocked = TestClient(create_app())

    with blocked.websocket_connect("/ws") as ws:
        assert ws.receive_json() == {"type": "auth.required"}


def test_websocket_accepts_valid_cookie(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    unlocked = TestClient(create_app())

    unlocked.post("/api/auth", json={"passcode": "swordfish"})

    cookie = {name: value for name, value in unlocked.cookies.items()}

    with unlocked.websocket_connect("/ws", cookies=cookie) as ws:
        hello = ws.receive_json()

        assert hello["type"] == "hello"


def test_frontend_is_served_without_auth(monkeypatch):

    monkeypatch.setattr(config, "PASSCODE", "swordfish")

    blocked = TestClient(create_app())

    assert blocked.get("/").status_code == 200
    assert blocked.get("/js/main.js").status_code == 200
