"""
tests/integration/test_rate_limiting.py

Integration tests verifying rate limiting on sensitive and general endpoints,
verifying 429 Too Many Requests responses, Retry-After headers, and exemptions.
"""

from app.core.config import get_settings
from app.middlewares.rate_limit import limiter

settings = get_settings()


def test_rate_limit_auth_login_triggers_429(client):
    limiter.reset()
    auth_limit = settings.RATE_LIMIT_AUTH_PER_MINUTE

    # Perform requests up to the auth limit
    for _ in range(auth_limit):
        r = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
        assert r.status_code == 401
        assert "X-RateLimit-Limit" in r.headers

    # Next request must exceed rate limit
    r_blocked = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert r_blocked.status_code == 429
    assert "Retry-After" in r_blocked.headers
    assert int(r_blocked.headers["Retry-After"]) >= 1

    body = r_blocked.json()
    assert body["success"] is False
    assert "Rate limit exceeded" in body["message"]


def test_rate_limit_health_check_is_exempt(client):
    limiter.reset()
    # Sending more requests than any limit to health check
    for _ in range(25):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["success"] is True


def test_rate_limit_ip_isolation(client):
    limiter.reset()
    auth_limit = settings.RATE_LIMIT_AUTH_PER_MINUTE

    # Exhaust limit for IP 1.2.3.4
    headers_ip1 = {"X-Forwarded-For": "1.2.3.4"}
    for _ in range(auth_limit):
        r = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}, headers=headers_ip1)
        assert r.status_code == 401

    # IP 1.2.3.4 should now be blocked
    r_blocked = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}, headers=headers_ip1)
    assert r_blocked.status_code == 429

    # Different IP 5.6.7.8 should still be allowed
    headers_ip2 = {"X-Forwarded-For": "5.6.7.8"}
    r_allowed = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}, headers=headers_ip2)
    assert r_allowed.status_code == 401
