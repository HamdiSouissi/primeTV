"""Tests d'authentification et de profils."""
from __future__ import annotations


def test_health(client):
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_register_login_me(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "username": "newbie", "password": "NewbiePass2026"},
    )
    assert register.status_code == 201, register.text
    tokens = register.json()
    assert tokens["token_type"] == "bearer"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"

    login = client.post("/api/v1/auth/login", json={"email": "new@example.com", "password": "NewbiePass2026"})
    assert login.status_code == 200

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]


def test_invalid_credentials(client):
    response = client.post("/api/v1/auth/login", json={"email": "new@example.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/channels").status_code == 401


def test_weak_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "username": "weak", "password": "12345678"},
    )
    assert response.status_code == 422


def test_projections_and_profiles(client, user_headers):
    created = client.post(
        "/api/v1/profiles",
        json={"name": "Enfant", "is_kids": True, "language": "fr", "pin": "1234"},
        headers=user_headers,
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    assert profile["is_kids"] is True
    assert profile["has_pin"] is True

    listing = client.get("/api/v1/profiles", headers=user_headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 2

    updated = client.patch(
        f"/api/v1/profiles/{profile['id']}", json={"name": "Enfant 2"}, headers=user_headers
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Enfant 2"

    deleted = client.delete(f"/api/v1/profiles/{profile['id']}", headers=user_headers)
    assert deleted.status_code == 200


def test_password_change(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "pwd@example.com", "username": "pwduser", "password": "OldPass2026"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "pwd@example.com", "password": "OldPass2026"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "OldPass2026", "new_password": "NewPass2026"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert (
        client.post("/api/v1/auth/login", json={"email": "pwd@example.com", "password": "NewPass2026"}).status_code
        == 200
    )
