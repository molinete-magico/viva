from tests.conftest import auth_headers, register


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_returns_token(client):
    data = register(client)
    assert data["token"]
    assert data["user"]["email"] == "ana@viva.app"


def test_first_user_becomes_admin(client):
    data = register(client)
    assert data["user"]["is_admin"] is True
    second = register(client, email="bruno@viva.app")
    assert second["user"]["is_admin"] is False


def test_duplicate_email_rejected(client):
    register(client)
    response = client.post(
        "/api/auth/register",
        json={"email": "ana@viva.app", "password": "outrasenha"},
    )
    assert response.status_code == 409
    assert "e-mail" in response.json()["detail"]


def test_short_password_rejected(client):
    response = client.post("/api/auth/register", json={"email": "x@viva.app", "password": "123"})
    assert response.status_code == 422


def test_login_success_and_failure(client):
    register(client)
    ok = client.post("/api/auth/login", json={"email": "ana@viva.app", "password": "senha123"})
    assert ok.status_code == 200
    bad = client.post("/api/auth/login", json={"email": "ana@viva.app", "password": "errada123"})
    assert bad.status_code == 401
    unknown = client.post("/api/auth/login", json={"email": "ninguem@viva.app", "password": "senha123"})
    assert unknown.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client):
    headers = auth_headers(client)
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "ana@viva.app"
    assert body["active_character"] is None


def test_session_persists_across_app_instances(client):
    from fastapi.testclient import TestClient
    from app.main import app

    register(client)
    with TestClient(app) as second_client:
        response = second_client.post(
            "/api/auth/login", json={"email": "ana@viva.app", "password": "senha123"}
        )
        assert response.status_code == 200
