"""
tests/integration/test_cors.py

Integration tests verifying CORS headers, origin validation, preflight handling,
and credentials support against frontend development origins.
"""


def test_cors_preflight_allowed_origin(client):
    headers = {
        "Origin": "http://localhost:8000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization,Content-Type",
    }
    r = client.options("/api/v1/auth/login", headers=headers)
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8000"
    assert r.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in r.headers.get("access-control-allow-methods", "")


def test_cors_get_allowed_origin(client):
    headers = {"Origin": "http://127.0.0.1:8000"}
    r = client.get("/health", headers=headers)
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:8000"
    assert r.headers.get("access-control-allow-credentials") == "true"


def test_cors_live_server_origin(client):
    headers = {"Origin": "http://127.0.0.1:5500"}
    r = client.get("/health", headers=headers)
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5500"


def test_cors_disallowed_origin_rejected(client):
    headers = {
        "Origin": "http://malicious-site.example.com",
        "Access-Control-Request-Method": "POST",
    }
    r = client.options("/api/v1/auth/login", headers=headers)
    # Disallowed origin should not have access-control-allow-origin echoing the attacker origin
    assert r.headers.get("access-control-allow-origin") != "http://malicious-site.example.com"
