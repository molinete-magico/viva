from sqlmodel import Session

from app.database.session import engine
from app.services.social_service import npc_social_reactions
from tests.conftest import auth_headers, create_character, register


def test_npc_returns_follow(client):
    headers = auth_headers(client)
    create_character(client, headers)
    npcs = [c for c in client.get("/api/characters", headers=headers).json()["items"] if c["is_npc"]]
    caio = next(c for c in npcs if c["name"] == "Caio")

    client.post(f"/api/characters/{caio['id']}/follow", headers=headers)

    me_id = client.get("/api/auth/me", headers=headers).json()["active_character"]["id"]
    me = client.get(f"/api/characters/{me_id}", headers=headers).json()
    assert me["stats"]["followers"] == 1, "seguir um NPC deveria fazer o morador seguir de volta"

    notifs = client.get("/api/notifications?unread=true", headers=headers).json()["items"]
    assert any(n["type"] == "NEW_FOLLOWER" and n["payload"]["name"] == "Caio" for n in notifs)


def test_npc_reactions_to_player_post(client):
    headers = auth_headers(client)
    create_character(client, headers)
    post = client.post("/api/posts", json={"content": "Café novo na praça, quem vai?"}, headers=headers).json()

    npcs = [c for c in client.get("/api/characters", headers=headers).json()["items"] if c["is_npc"]]
    caio = next(c for c in npcs if c["name"] == "Caio")
    client.post(f"/api/characters/{caio['id']}/follow", headers=headers)

    with Session(engine) as session:
        likes, comments = npc_social_reactions(session)

    assert likes >= 1, "NPC seguidor deveria curtir o post do morador"
    assert comments >= 1, "um NPC deveria comentar o post do morador"

    detail = client.get(f"/api/posts/{post['id']}", headers=headers).json()
    assert detail["likes_count"] >= 1
    assert detail["comments_count"] == 1

    notifs = client.get("/api/notifications?unread=true", headers=headers).json()["items"]
    assert any(n["type"] == "POST_LIKE" and n["payload"]["post_id"] == post["id"] for n in notifs)
    assert any(n["type"] == "POST_COMMENT" and n["payload"]["post_id"] == post["id"] for n in notifs)


def test_like_flow(client):
    headers = auth_headers(client)
    create_character(client, headers)
    post = client.post("/api/posts", json={"content": "Bom dia, Vila Serena!"}, headers=headers).json()

    liked = client.post(f"/api/posts/{post['id']}/like", headers=headers).json()
    assert liked == {"liked": True, "likes_count": 1}

    again = client.post(f"/api/posts/{post['id']}/like", headers=headers).json()
    assert again["liked"] is True and again["likes_count"] == 1

    unliked = client.delete(f"/api/posts/{post['id']}/like", headers=headers).json()
    assert unliked == {"liked": False, "likes_count": 0}

    assert client.post("/api/posts/999999/like", headers=headers).status_code == 404


def test_like_requires_character(client):
    headers = auth_headers(client)
    client.post("/api/posts", json={"content": "sem personagem"}, headers=headers)
    assert client.post("/api/posts/1/like", headers=headers).status_code == 403


def test_comment_and_notification(client):
    d1 = register(client, email="ana@viva.app")
    h1 = {"Authorization": f"Bearer {d1['token']}"}
    create_character(client, h1, name="Ana")
    post = client.post("/api/posts", json={"content": "Chuva na serra hoje."}, headers=h1).json()

    d2 = register(client, email="bia@viva.app")
    h2 = {"Authorization": f"Bearer {d2['token']}"}
    create_character(client, h2, name="Bia")

    created = client.post(
        f"/api/posts/{post['id']}/comments",
        json={"content": "Traga guarda-chuva!"},
        headers=h2,
    )
    assert created.status_code == 201, created.text
    comment = created.json()
    assert comment["author"]["name"] == "Bia"

    comments = client.get(f"/api/posts/{post['id']}/comments", headers=h1).json()
    assert len(comments) == 1
    assert comments[0]["content"] == "Traga guarda-chuva!"

    notifs = client.get("/api/notifications", headers=h1).json()["items"]
    assert any(n["type"] == "POST_COMMENT" and n["payload"]["post_id"] == post["id"] for n in notifs)

    self_comment = client.post(
        f"/api/posts/{post['id']}/comments",
        json={"content": "resposta minha"},
        headers=h1,
    )
    assert self_comment.status_code == 201
    assert len(client.get("/api/notifications", headers=h1).json()["items"]) == len(notifs)


def test_comment_like_and_delete(client):
    d1 = register(client, email="ana@viva.app")
    h1 = {"Authorization": f"Bearer {d1['token']}"}
    create_character(client, h1, name="Ana")
    post = client.post("/api/posts", json={"content": "post"}, headers=h1).json()
    comment = client.post(f"/api/posts/{post['id']}/comments", json={"content": "oi"}, headers=h1).json()

    assert client.post(f"/api/comments/{comment['id']}/like", headers=h1).json()["likes_count"] == 1
    assert client.delete(f"/api/comments/{comment['id']}/like", headers=h1).json()["likes_count"] == 0
    assert client.post("/api/comments/999999/like", headers=h1).status_code == 404

    d2 = register(client, email="bia@viva.app")
    h2 = {"Authorization": f"Bearer {d2['token']}"}
    create_character(client, h2, name="Bia")
    assert client.delete(f"/api/comments/{comment['id']}", headers=h2).status_code == 403
    assert client.delete(f"/api/comments/{comment['id']}", headers=h1).status_code == 204
    assert len(client.get(f"/api/posts/{post['id']}/comments", headers=h1).json()) == 0


def test_comment_on_unknown_post(client):
    headers = auth_headers(client)
    create_character(client, headers)
    assert client.post("/api/posts/999999/comments", json={"content": "x"}, headers=headers).status_code == 404


def test_follow_and_discovery(client):
    d1 = register(client, email="ana@viva.app")
    h1 = {"Authorization": f"Bearer {d1['token']}"}
    create_character(client, h1, name="Ana")

    d2 = register(client, email="bia@viva.app")
    h2 = {"Authorization": f"Bearer {d2['token']}"}
    create_character(client, h2, name="Bia")

    assert client.post("/api/characters/999999/follow", headers=h1).status_code == 404

    bia_list = client.get("/api/characters", headers=h1).json()["items"]
    bia = next(c for c in bia_list if c["name"] == "Bia" and not c["is_npc"])

    result = client.post(f"/api/characters/{bia['id']}/follow", headers=h1).json()
    assert result == {"following": True, "followers_count": 1}

    twice = client.post(f"/api/characters/{bia['id']}/follow", headers=h1).json()
    assert twice["followers_count"] == 1

    detail = client.get(f"/api/characters/{bia['id']}", headers=h1).json()
    assert detail["is_following"] is True
    assert detail["stats"]["followers"] == 1

    unfollow = client.delete(f"/api/characters/{bia['id']}/follow", headers=h1).json()
    assert unfollow == {"following": False, "followers_count": 0}

    assert client.post(f"/api/characters/{bia['id']}/follow", headers=h2).status_code == 400  # aná? não: Bia segue Bia

    me_list = client.get("/api/characters", headers=h2).json()["items"]
    ana = next(c for c in me_list if c["name"] == "Ana" and not c["is_npc"])
    client.post(f"/api/characters/{ana['id']}/follow", headers=h2)
    notifs = client.get("/api/notifications?unread=true", headers=h1).json()["items"]
    assert any(n["type"] == "NEW_FOLLOWER" and n["payload"]["name"] == "Bia" for n in notifs)


def test_following_feed_scope(client):
    d1 = register(client, email="ana@viva.app")
    h1 = {"Authorization": f"Bearer {d1['token']}"}
    create_character(client, h1, name="Ana")

    d2 = register(client, email="bia@viva.app")
    h2 = {"Authorization": f"Bearer {d2['token']}"}
    create_character(client, h2, name="Bia")

    client.post("/api/posts", json={"content": "meu post"}, headers=h1)
    bia_post = client.post("/api/posts", json={"content": "post da bia"}, headers=h2).json()

    me_list = client.get("/api/characters", headers=h1).json()["items"]
    bia = next(c for c in me_list if c["name"] == "Bia" and not c["is_npc"])
    client.post(f"/api/characters/{bia['id']}/follow", headers=h1)

    feed = client.get("/api/feed?scope=following", headers=h1).json()["items"]
    ids = {p["id"] for p in feed}
    assert bia_post["id"] in ids

    client.delete(f"/api/characters/{bia['id']}/follow", headers=h1)
    feed_after = client.get("/api/feed?scope=following", headers=h1).json()["items"]
    assert bia_post["id"] not in {p["id"] for p in feed_after}


def test_follow_npc_unlocks_hobbies(client):
    headers = auth_headers(client)
    create_character(client, headers)
    npcs = [c for c in client.get("/api/characters", headers=headers).json()["items"] if c["is_npc"]]
    caio = next(c for c in npcs if c["name"] == "Caio")

    before = client.get(f"/api/characters/{caio['id']}", headers=headers).json()
    assert before["hobbies"] == []

    client.post(f"/api/characters/{caio['id']}/follow", headers=headers)
    after = client.get(f"/api/characters/{caio['id']}", headers=headers).json()
    assert after["hobbies"] != [], "Seguir um NPC deveria destravar os hobbies"


def test_notifications_read_flow(client):
    headers = auth_headers(client)
    create_character(client, headers)
    post = client.post("/api/posts", json={"content": "post"}, headers=headers).json()

    d2 = register(client, email="bia@viva.app")
    h2 = {"Authorization": f"Bearer {d2['token']}"}
    create_character(client, h2, name="Bia")
    client.post(f"/api/posts/{post['id']}/comments", json={"content": "oi"}, headers=h2)

    empty = client.get("/api/notifications?unread=false", headers=headers).json()["items"]
    assert empty == []

    unread = client.get("/api/notifications?unread=true", headers=headers).json()["items"]
    assert len(unread) == 1

    mark = client.post(f"/api/notifications/{unread[0]['id']}/read", headers=headers)
    assert mark.status_code == 200
    assert client.get("/api/notifications?unread=true", headers=headers).json()["items"] == []

    client.post(f"/api/posts/{post['id']}/comments", json={"content": "de novo"}, headers=h2)
    client.post("/api/notifications/read-all", headers=headers)
    assert client.get("/api/notifications?unread=true", headers=headers).json()["items"] == []

    assert client.post("/api/notifications/999999/read", headers=headers).status_code == 404