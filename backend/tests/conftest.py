import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="viva_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db"
os.environ["JWT_SECRET"] = "test-secret-abcdefghijklmnopqrstuvwxyz-0123456789"
os.environ["AUTO_MIGRATE"] = "false"
os.environ["GROQ_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.database.migrate import run_migrations
from app.database.seed import run_seed
from app.database.session import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _schema():
    run_migrations()
    run_seed()


@pytest.fixture(autouse=True)
def _clean_tables():
    with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())
    run_seed()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def register(client, email="ana@viva.app", password="senha123"):
    response = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(client, email="ana@viva.app", password="senha123"):
    data = register(client, email, password)
    return {"Authorization": f"Bearer {data['token']}"}


def create_character(client, headers, name="Ana", age=26):
    response = client.post(
        "/api/characters",
        json={"name": name, "age": age, "bio": "Motorista de dia, garçom à noite.", "profession_label": "Motorista"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
