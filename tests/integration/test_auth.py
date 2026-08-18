"""
tests/integration/test_auth.py

Covers Module 3 (Authentication): register, login, JWT-protected routes,
and logout/token revocation.
"""


def test_register_creates_recruiter(client):
    r = client.post("/api/v1/auth/register", json={
        "name": "Alex Kim", "email": "alex@company.com", "password": "SecurePass123",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    assert body["data"]["email"] == "alex@company.com"
    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]


def test_register_duplicate_email_rejected(client):
    payload = {"name": "Alex Kim", "email": "alex@company.com", "password": "SecurePass123"}
    client.post("/api/v1/auth/register", json=payload)
    r = client.post("/api/v1/auth/register", json={**payload, "name": "Someone Else"})
    assert r.status_code == 409


def test_register_rejects_short_password(client):
    r = client.post("/api/v1/auth/register", json={
        "name": "Alex Kim", "email": "alex@company.com", "password": "short",
    })
    assert r.status_code == 422


def test_login_wrong_password_rejected(client):
    client.post("/api/v1/auth/register", json={
        "name": "Alex Kim", "email": "alex@company.com", "password": "SecurePass123",
    })
    r = client.post("/api/v1/auth/login", json={"email": "alex@company.com", "password": "WrongPassword"})
    assert r.status_code == 401


def test_login_returns_token_pair(client):
    client.post("/api/v1/auth/register", json={
        "name": "Alex Kim", "email": "alex@company.com", "password": "SecurePass123",
    })
    r = client.post("/api/v1/auth/login", json={"email": "alex@company.com", "password": "SecurePass123"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "access_token" in data and "refresh_token" in data


def test_protected_route_without_token_rejected(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_protected_route_with_token_succeeds(client, auth_headers):
    r = client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "jane@company.com"


def test_logout_revokes_token(client, auth_headers):
    token = auth_headers["Authorization"].split(" ")[1]
    r = client.post("/api/v1/auth/logout", json={"access_token": token})
    assert r.status_code == 200

    r = client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 401


def test_refresh_rejects_access_token(client):
    client.post("/api/v1/auth/register", json={
        "name": "Alex Kim", "email": "alex@company.com", "password": "SecurePass123",
    })
    r = client.post("/api/v1/auth/login", json={"email": "alex@company.com", "password": "SecurePass123"})
    access_token = r.json()["data"]["access_token"]

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert r.status_code == 401


def test_expired_access_token_rejected(client):
    from app.core.security import create_access_token
    # Generate token that expired in the past
    expired_token = create_access_token(subject="1", expires_minutes=-10)
    headers = {"Authorization": f"Bearer {expired_token}"}

    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 401
    assert r.json()["success"] is False


def test_expired_refresh_token_rejected(client):
    from jose import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import get_settings
    settings = get_settings()

    expired_payload = {
        "sub": "1",
        "type": "refresh",
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
    }
    expired_refresh_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": expired_refresh_token})
    assert r.status_code == 401
    assert r.json()["success"] is False


def test_malformed_token_rejected(client):
    headers = {"Authorization": "Bearer not-a-valid-token-at-all"}
    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 401


def test_non_integer_sub_token_rejected(client):
    from jose import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import get_settings
    settings = get_settings()

    payload = {
        "sub": "not_an_int_id",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 401

