from tests.conftest import auth_headers, create_character


def test_world_returns_time(client):
    headers = auth_headers(client)
    response = client.get("/api/world", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["city_name"] == "Vila Serena"
    assert body["time"]
    assert 0 <= body["day_of_week"] <= 6
    assert body["day_name"]


def test_feed_empty_initially(client):
    headers = auth_headers(client)
    response = client.get("/api/feed", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_create_post_appears_in_feed_and_persists(client):
    from fastapi.testclient import TestClient
    from app.main import app

    headers = auth_headers(client)
    create_character(client, headers)
    created = client.post("/api/posts", json={"content": "Primeiro post da noite."}, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["author"]["name"] == "Ana"
    assert body["likes_count"] == 0

    feed = client.get("/api/feed", headers=headers).json()
    assert len(feed["items"]) == 1
    assert feed["items"][0]["content"] == "Primeiro post da noite."

    with TestClient(app) as second_client:
        again = second_client.get("/api/feed", headers=headers)
        assert again.status_code == 200
        assert len(again.json()["items"]) == 1


def test_whitespace_post_rejected(client):
    headers = auth_headers(client)
    create_character(client, headers)
    response = client.post("/api/posts", json={"content": "   "}, headers=headers)
    assert response.status_code == 400


def test_empty_social_lists(client):
    headers = auth_headers(client)
    create_character(client, headers)
    assert client.get("/api/conversations", headers=headers).json()["items"] == []
    assert client.get("/api/events", headers=headers).json()["items"] == []
    assert client.get("/api/notifications", headers=headers).json()["items"] == []


def test_character_posts_endpoint(client):
    headers = auth_headers(client)
    me = create_character(client, headers)
    client.post("/api/posts", json={"content": "Postando da rua."}, headers=headers)
    response = client.get(f"/api/characters/{me['id']}/posts", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
