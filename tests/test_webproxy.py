"""Security tests for the embedded-web proxy endpoint."""

from fastapi.testclient import TestClient

from server.app import app

client = TestClient(app)


def test_proxy_rejects_private_host():
    r = client.get("/web/proxy", params={"url": "http://127.0.0.1:80/"})
    assert r.status_code == 400
    assert "not reachable" in r.json()["detail"]


def test_proxy_rejects_link_local_host():
    r = client.get("/web/proxy", params={"url": "http://169.254.1.1/"})
    assert r.status_code == 400


def test_proxy_rejects_private_ipv6():
    r = client.get("/web/proxy", params={"url": "http://[::1]/"})
    assert r.status_code == 400


def test_proxy_rejects_non_http_scheme():
    r = client.get("/web/proxy", params={"url": "file:///etc/passwd"})
    assert r.status_code == 400


def test_proxy_rejects_empty_url():
    r = client.get("/web/proxy", params={"url": ""})
    assert r.status_code == 400


def test_proxy_blocks_common_private_ranges():
    for url in ("http://10.0.0.1/", "http://192.168.0.1/", "http://172.16.0.1/", "http://localhost/"):
        r = client.get("/web/proxy", params={"url": url})
        assert r.status_code == 400, url
