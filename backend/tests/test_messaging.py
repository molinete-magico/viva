from app.llm import LLMProvider, RateLimitError, get_provider, reset_provider
from app.services import messaging_service
from tests.conftest import auth_headers, create_character


def _npc(client, headers, name):
    items = client.get("/api/characters", headers=headers).json()["items"]
    return next(c for c in items if c["is_npc"] and c["name"] == name)


def test_start_dm_requires_npc(client):
    headers = auth_headers(client)
    create_character(client, headers)
    me = client.get("/api/auth/me", headers=headers).json()["active_character"]
    response = client.post(f"/api/characters/{me['id']}/dm", headers=headers)
    assert response.status_code == 400


def test_dm_flow_with_npc(client):
    headers = auth_headers(client)
    create_character(client, headers, name="Ana")
    taro = _npc(client, headers, "Taro")

    conv = client.post(f"/api/characters/{taro['id']}/dm", headers=headers)
    assert conv.status_code == 200, conv.text
    data = conv.json()
    assert data["partner"]["name"] == "Taro"

    detail = client.get(f"/api/conversations/{data['id']}", headers=headers).json()
    assert detail["active_session_id"] is not None

    sent = client.post(
        f"/api/conversations/{data['id']}/messages",
        json={"content": "Boa tarde, Taro! Como anda o ramen?"},
        headers=headers,
    )
    assert sent.status_code == 200, sent.text
    result = sent.json()
    assert result["message"]["is_mine"] is True
    assert result["npc_reply"]["sender_character_id"] == taro["id"]
    assert len(result["npc_reply"]["content"].strip()) > 0

    history = client.get(f"/api/conversations/{data['id']}/messages", headers=headers).json()["items"]
    assert len(history) == 2
    assert history[0]["is_mine"] is True

    conversations = client.get("/api/conversations", headers=headers).json()["items"]
    assert len(conversations) == 1
    assert conversations[0]["partner"]["name"] == "Taro"


def test_dm_reuses_conversation(client):
    headers = auth_headers(client)
    create_character(client, headers, name="Bia")
    taro = _npc(client, headers, "Taro")

    first = client.post(f"/api/characters/{taro['id']}/dm", headers=headers).json()
    second = client.post(f"/api/characters/{taro['id']}/dm", headers=headers).json()
    assert first["id"] == second["id"]


def test_message_requires_partner_and_content(client):
    headers = auth_headers(client)
    create_character(client, headers, name="Ana")
    taro = _npc(client, headers, "Taro")
    conv = client.post(f"/api/characters/{taro['id']}/dm", headers=headers).json()

    empty = client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "   "}, headers=headers)
    assert empty.status_code == 400

    unknown = client.post("/api/conversations/999999/messages", json={"content": "oi"}, headers=headers)
    assert unknown.status_code == 404

    assert client.get("/api/conversations/999999/messages", headers=headers).status_code == 404
    assert client.get("/api/conversations/999999", headers=headers).status_code == 404


def test_end_session_and_session_rotation(client):
    headers = auth_headers(client)
    create_character(client, headers, name="Ana")
    taro = _npc(client, headers, "Taro")
    conv = client.post(f"/api/characters/{taro['id']}/dm", headers=headers).json()

    client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "oi"}, headers=headers)
    ended = client.post(f"/api/conversations/{conv['id']}/end-session", headers=headers)
    assert ended.status_code == 200

    detail = client.get(f"/api/conversations/{conv['id']}", headers=headers).json()
    assert detail["active_session_id"] is None

    client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "oi de novo"}, headers=headers)
    detail2 = client.get(f"/api/conversations/{conv['id']}", headers=headers).json()
    assert detail2["active_session_id"] is not None


def test_mock_provider_returns_style_consistent_reply(client):
    reset_provider()
    headers = auth_headers(client)
    create_character(client, headers, name="Ana")
    dede = _npc(client, headers, "Dedé")
    conv = client.post(f"/api/characters/{dede['id']}/dm", headers=headers).json()
    result = client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "E aí, Dedé?"},
        headers=headers,
    ).json()
    assert get_provider().__class__.__name__ == "MockLLMProvider"
    assert len(result["npc_reply"]["content"]) > 0


def test_rate_limit_warns_but_keeps_message(client, monkeypatch):
    reset_provider()
    headers = auth_headers(client)
    create_character(client, headers, name="Ana")
    taro = _npc(client, headers, "Taro")
    conv = client.post(f"/api/characters/{taro['id']}/dm", headers=headers).json()

    class LimitedProvider(LLMProvider):
        async def complete(self, *, system_prompt, user_prompt, personality=None, model=None):
            raise RateLimitError("limite")

        async def health(self):
            return False

    monkeypatch.setattr(messaging_service, "get_provider", lambda: LimitedProvider())
    response = client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Oi, Taro!"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["npc_reply"] is None
    assert "limite" in (data["warning"] or "").lower()

    history = client.get(f"/api/conversations/{conv['id']}/messages", headers=headers).json()["items"]
    assert len(history) == 1
    assert history[0]["is_mine"] is True
    assert history[0]["content"] == "Oi, Taro!"