from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from tests.conftest import auth_headers, create_character, register


def _location_id(client, headers):
    return client.get("/api/world/locations", headers=headers).json()["items"][0]["id"]


def test_stale_event_session_recovered_on_catchup(client):
    headers = auth_headers(client)
    create_character(client, headers)
    location_id = _location_id(client, headers)

    event = client.post(
        "/api/events",
        json={
            "title": "Feira da madrugada",
            "location_id": location_id,
            "scheduled_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "invitees": [],
        },
        headers=headers,
    ).json()
    session_id = client.post(f"/api/events/{event['id']}/sessions", headers=headers).json()["session"]["id"]
    assert client.get(f"/api/events/sessions/{session_id}", headers=headers).json()["session"]["status"] == "ACTIVE"

    from app.database.session import engine
    from app.models import Event, EventSession

    with Session(engine) as session:
        row = session.get(EventSession, session_id)
        row.last_activity_at = datetime.now(timezone.utc) - timedelta(days=2)
        session.add(row)
        event_row = session.get(Event, event["id"])
        event_row.status = "ACTIVE"
        session.add(event_row)
        session.commit()

    report = client.post("/api/simulation/catchup?minutes=60&with_social=false", headers=headers).json()
    assert report["elapsed_minutes"] == 60

    with Session(engine) as session:
        row = session.get(EventSession, session_id)
        assert row.status == "ABANDONED"
        assert row.ended_at is not None
        event_row = session.get(Event, event["id"])
        assert event_row.status == "OPEN"

    detail = client.get(f"/api/events/{event['id']}", headers=headers).json()
    assert any(p["status"] == "WITHDREW" for p in detail["participants"])


def test_conversation_session_goes_idle_on_catchup(client):
    headers = auth_headers(client)
    char_id = create_character(client, headers)["id"]
    npc = client.get("/api/characters", headers=headers).json()["items"]
    npc_id = next(c["id"] for c in npc if c["is_npc"])

    conversation = client.post(f"/api/characters/{npc_id}/dm", headers=headers).json()
    conversation_id = conversation["id"]

    from app.database.session import engine
    from app.models import Conversation, ConversationSession

    with Session(engine) as session:
        row = session.get(Conversation, conversation_id)
        row.last_message_at = datetime.now(timezone.utc) - timedelta(hours=3)
        session.add(row)
        session.commit()

    client.post("/api/simulation/catchup?minutes=60&with_social=false", headers=headers)

    with Session(engine) as session:
        statuses = session.exec(
            select(ConversationSession.status).where(ConversationSession.conversation_id == conversation_id)
        ).all()
        assert "IDLE" in statuses, statuses

    detail = client.get(f"/api/conversations/{conversation_id}", headers=headers).json()
    assert detail["active_session_id"] is None


def test_new_dm_after_idle_starts_fresh_active_session(client):
    headers = auth_headers(client)
    create_character(client, headers)
    npc = client.get("/api/characters", headers=headers).json()["items"]
    npc_id = next(c["id"] for c in npc if c["is_npc"])
    conversation_id = client.post(f"/api/characters/{npc_id}/dm", headers=headers).json()["id"]

    from app.database.session import engine
    from app.models import Conversation

    with Session(engine) as session:
        row = session.get(Conversation, conversation_id)
        row.last_message_at = datetime.now(timezone.utc) - timedelta(hours=3)
        session.add(row)
        session.commit()

    client.post("/api/simulation/catchup?minutes=60&with_social=false", headers=headers)

    reply = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "E aí, ainda por aqui?"},
        headers=headers,
    )
    assert reply.status_code == 200, reply.text
    detail = client.get(f"/api/conversations/{conversation_id}", headers=headers).json()
    assert detail["active_session_id"] is not None