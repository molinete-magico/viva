import pytest

from tests.conftest import auth_headers, create_character, register


def _location_id(client, headers):
    return client.get("/api/world/locations", headers=headers).json()["items"][0]["id"]


def _second_user_with_character(client, email):
    data = register(client, email=email)
    headers = {"Authorization": f"Bearer {data['token']}"}
    character = create_character(client, headers, name="Bruna")
    return headers, character


def test_create_event_and_list(client):
    headers = auth_headers(client)
    character = create_character(client, headers)
    location_id = _location_id(client, headers)
    from datetime import datetime, timedelta, timezone

    response = client.post(
        "/api/events",
        json={
            "title": "Rolê do ramen",
            "description": "Mesa da esquina, caldo e conversa.",
            "location_id": location_id,
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "invitees": [],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    event = response.json()
    assert event["title"] == "Rolê do ramen"
    assert event["host_name"] == character["name"]
    assert event["my_status"] == "JOINED"

    listing = client.get("/api/events", headers=headers).json()
    assert any(item["id"] == event["id"] for item in listing["items"])

    detail = client.get(f"/api/events/{event['id']}", headers=headers).json()
    assert detail["participants"][0]["name"] == character["name"]


def test_invitee_rsvp_and_notification(client):
    owner_headers, owner_character = _second_user_with_character(client, "bruna@viva.app")
    guest_headers, guest_character = _second_user_with_character(client, "cecilia@viva.app")
    location_id = _location_id(client, owner_headers)
    from datetime import datetime, timedelta, timezone

    response = client.post(
        "/api/events",
        json={
            "title": "Festinha surpresa",
            "location_id": location_id,
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "invitees": [guest_character["id"]],
        },
        headers=owner_headers,
    )
    event_id = response.json()["id"]

    notifs = client.get("/api/notifications", headers=guest_headers).json()
    assert any(n["type"] == "EVENT_INVITE" and n["payload"].get("event_id") == event_id for n in notifs["items"])

    rsvp = client.post(f"/api/events/{event_id}/rsvp", json={"accept": True}, headers=guest_headers)
    assert rsvp.status_code == 200, rsvp.text
    my_status = next(
        p["status"] for p in rsvp.json()["participants"] if p["character_id"] == guest_character["id"]
    )
    assert my_status == "ACCEPTED"


def test_event_session_playthrough_and_outcome(client):
    headers = auth_headers(client)
    character = create_character(client, headers)
    char_id = character["id"]
    location_id = _location_id(client, headers)
    from datetime import datetime, timedelta, timezone

    event = client.post(
        "/api/events",
        json={
            "title": "Noite de forró",
            "location_id": location_id,
            "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            "invitees": [],
        },
        headers=headers,
    ).json()

    session_state = client.post(f"/api/events/{event['id']}/sessions", headers=headers)
    assert session_state.status_code == 200, session_state.text
    body = session_state.json()
    session_id = body["session"]["id"]
    assert body["can_act"] is True
    assert body["turns"][0]["narrative"]
    first_actions = body["turns"][0]["available_actions"]

    action_id = first_actions[0]["id"]
    turn = client.post(
        f"/api/events/sessions/{session_id}/actions",
        json={"action_id": action_id},
        headers=headers,
    )
    assert turn.status_code == 200, turn.text
    assert turn.json()["player_action_id"] == action_id

    outcome = client.post(f"/api/events/sessions/{session_id}/end", headers=headers)
    assert outcome.status_code == 200, outcome.text
    data = outcome.json()
    assert data["summary"]
    assert data["memories"]

    memories = client.get(f"/api/characters/{char_id}/memories", headers=headers).json()
    assert memories["items"], "esperava memórias do evento"
    assert memories["items"][0]["category"] == "EVENT"

    milestones = client.get("/api/milestones", headers=headers).json()
    event_ms = next(m for m in milestones["items"] if m["key"] == "EVENT_PARTICIPATION")
    assert event_ms["count"] >= 1


def test_abandon_session_returns_event_to_open(client):
    headers = auth_headers(client)
    create_character(client, headers)
    location_id = _location_id(client, headers)
    from datetime import datetime, timedelta, timezone

    event = client.post(
        "/api/events",
        json={
            "title": "Ensaio da banda",
            "location_id": location_id,
            "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            "invitees": [],
        },
        headers=headers,
    ).json()
    session_id = client.post(f"/api/events/{event['id']}/sessions", headers=headers).json()["session"]["id"]
    response = client.post(f"/api/events/sessions/{session_id}/abandon", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ABANDONED"
    detail = client.get(f"/api/events/{event['id']}", headers=headers).json()
    assert detail["status"] == "OPEN"


def test_relationships_and_milestone_claim(client):
    headers = auth_headers(client)
    character = create_character(client, headers)
    char_id = character["id"]
    npc = client.get("/api/characters", headers=headers).json()["items"]
    npc_id = next(c["id"] for c in npc if c["is_npc"])

    rsvp = client.get(f"/api/characters/{npc_id}/relationship", headers=headers).json()
    assert rsvp["id"] is None

    response = client.post(f"/api/milestones/FIRST_MEETING/claim", headers=headers)
    assert response.status_code == 409, "sem progresso ainda, deve recusar"

    from sqlmodel import Session, select

    from app.database.session import engine
    from app.models import User
    from app.services import milestone_service, relationship_service

    with Session(engine) as session:
        relationship_service.bump_interaction(session, char_id, npc_id, {"friendship": 3})
        milestone_service.record_progress(session, "FIRST_MEETING", 1)
        milestone_service.record_progress(session, "FIRST_MEETING", 1)

    claim = client.post(f"/api/milestones/FIRST_MEETING/claim", headers=headers)
    assert claim.status_code == 200, claim.text
    assert claim.json()["reward"] > 0

    rel = client.get(f"/api/characters/{npc_id}/relationship", headers=headers).json()
    assert rel["friendship"] == 3
    assert rel["other_name"]


def test_catchup_advances_and_pays_bills(client):
    headers = auth_headers(client)
    create_character(client, headers)
    response = client.post("/api/simulation/catchup?minutes=120&with_social=false", headers=headers)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["elapsed_minutes"] == 120
    assert report["from"] and report["to"]

    logs = client.get("/api/simulation/logs", headers=headers).json()
    assert any(log["kind"] == "auto" for log in logs["items"])

    payments = report["payments"]
    assert payments, "esperava pagamento de salário de NPCs no horário"


def test_admin_routes_blocked_for_non_admin(client):
    register(client, email="responsavel@viva.app")
    headers, _ = _second_user_with_character(client, "naoadmin@viva.app")
    assert client.get("/api/admin/characters", headers=headers).status_code == 403


def test_admin_routes_list_and_update(client):
    data = register(client, email="admin@viva.app")
    headers = {"Authorization": f"Bearer {data['token']}"}
    create_character(client, headers, name="Rainha Admin")
    from sqlmodel import Session, select

    from app.database.session import engine
    from app.models import User

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "admin@viva.app")).one()
        user.is_admin = True
        session.add(user)
        session.commit()

    response = client.get("/api/admin/characters", headers=headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) >= 2

    jobs = client.get("/api/admin/jobs", headers=headers).json()
    assert jobs["items"]

    npc_id = next(c["id"] for c in response.json()["items"] if c["is_npc"])
    patch = client.patch(f"/api/admin/characters/{npc_id}", json={"money": 999}, headers=headers)
    assert patch.status_code == 200, patch.text
    assert patch.json()["money"] == 999