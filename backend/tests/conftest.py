"""Fixtures de tests : base SQLite isolée, données de démo, client HTTP."""
from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "test_primetv.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{DB_PATH}",
        "SECRET_KEY": "test-secret-key-0123456789abcdef",
        "ENV": "development",
        "SEED_DEMO_DATA": "true",
        "RATE_LIMIT_ENABLED": "false",
        "PUBLIC_BASE_URL": "http://testserver",
        "REDIS_URL": "",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.DEFAULT_ADMIN_EMAIL, "password": settings.DEFAULT_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def user_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "viewer@example.com",
            "username": "viewer",
            "password": "ViewerPass2026",
            "full_name": "Téléspectateur",
        },
    )
    assert response.status_code in (201, 409), response.text
    if response.status_code == 409:
        response = client.post(
            "/api/v1/auth/login", json={"email": "viewer@example.com", "password": "ViewerPass2026"}
        )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def demo_channel(client, admin_headers) -> dict:
    response = client.get("/api/v1/channels?page_size=1", headers=admin_headers)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items, "Le catalogue de démonstration doit contenir des chaînes"
    return items[0]
