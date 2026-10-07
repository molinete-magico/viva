from tests.conftest import auth_headers, create_character, register


def test_create_own_character(client):
    headers = auth_headers(client)
    data = create_character(client, headers)
    assert data["name"] == "Ana"
    assert data["is_me"] is True
    assert data["money"] == 300


def test_cannot_create_second_character(client):
    headers = auth_headers(client)
    create_character(client, headers)
    response = client.post(
        "/api/characters",
        json={"name": "Outra", "age": 30},
        headers=headers,
    )
    assert response.status_code == 409


def test_character_age_validation(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/characters",
        json={"name": "Jovem", "age": 12},
        headers=headers,
    )
    assert response.status_code == 422


def test_post_requires_character(client):
    headers = auth_headers(client)
    response = client.post("/api/posts", json={"content": "oi"}, headers=headers)
    assert response.status_code == 403
    assert "personagem" in response.json()["detail"]


def test_character_detail_visibility(client):
    headers = auth_headers(client)
    me = create_character(client, headers)

    other = register(client, email="bruno@viva.app")
    other_headers = {"Authorization": f"Bearer {other['token']}"}
    response = client.get(f"/api/characters/{me['id']}", headers=other_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_me"] is False
    assert body["money"] is None

    own = client.get(f"/api/characters/{me['id']}", headers=headers)
    assert own.json()["money"] == 300


def test_character_list_includes_created(client):
    headers = auth_headers(client)
    create_character(client, headers)
    response = client.get("/api/characters", headers=headers)
    names = [c["name"] for c in response.json()["items"]]
    assert "Ana" in names


def test_character_not_found(client):
    headers = auth_headers(client)
    response = client.get("/api/characters/9999", headers=headers)
    assert response.status_code == 404
