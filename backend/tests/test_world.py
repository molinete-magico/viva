from sqlmodel import Session, select

from app.config import DATA_DIR
from app.database.seed import run_seed
from app.database.session import engine
from app.models import CharacterPhoto, Job, SimulationLog
from tests.conftest import auth_headers, create_character, register


def _session() -> Session:
    return Session(engine)


def test_seed_is_idempotent(client):
    headers = auth_headers(client)
    before = client.get("/api/world/districts", headers=headers).json()["items"]
    run_seed()
    run_seed()
    after = client.get("/api/world/districts", headers=headers).json()["items"]
    assert len(before) == 4
    assert [d["slug"] for d in before] == [d["slug"] for d in after]


def test_districts_and_locations_require_auth(client):
    assert client.get("/api/world/districts").status_code == 401
    assert client.get("/api/world/locations").status_code == 401


def test_world_has_districts_and_locations(client):
    headers = auth_headers(client)
    districts = client.get("/api/world/districts", headers=headers).json()["items"]
    assert len(districts) == 4
    assert districts[0]["slug"] == "centro-velho"

    locations = client.get("/api/world/locations", headers=headers).json()["items"]
    assert len(locations) == 10
    ramen = next(loc for loc in locations if loc["slug"] == "ramen-da-esquina")
    assert ramen["district_name"] == "Centro Velho"
    assert ramen["opening_hours"]["ranges"]


def test_locations_filtered_by_district(client):
    headers = auth_headers(client)
    items = client.get("/api/world/locations", params={"district": "estacao"}, headers=headers).json()["items"]
    assert {loc["slug"] for loc in items} == {
        "padaria-estrela",
        "mercado-municipal",
        "oficina-boa-rosca",
        "praca-do-relogio",
    }


def test_seed_creates_npcs_jobs_and_photos(client):
    headers = auth_headers(client)
    characters = client.get("/api/characters", headers=headers).json()["items"]
    npcs = [c for c in characters if c["is_npc"]]
    assert len(npcs) == 10
    for npc in npcs:
        assert npc["photo_url"], f"{npc['name']} sem foto"
        assert npc["photo_url"].startswith("/static/photos/")

    with _session() as session:
        assert len(session.exec(select(Job)).all()) == 11
        photos = session.exec(select(CharacterPhoto)).all()
        assert len(photos) == 10
        for photo in photos:
            file_path = DATA_DIR / "photos" / photo.path.rsplit("/", 1)[-1]
            assert file_path.exists(), f"{file_path} não existe"


def test_npc_discovery_gates_bio_and_hobbies(client):
    headers = auth_headers(client)
    characters = client.get("/api/characters", headers=headers).json()["items"]
    by_name = {c["name"]: c for c in characters}

    taro = client.get(f"/api/characters/{by_name['Taro']['id']}", headers=headers).json()
    assert taro["bio"], "Taro (nível 2) deveria ter bio visível"
    assert taro["hobbies"] == [], "Hobbies de NPC exigem nível 3"

    caio = client.get(f"/api/characters/{by_name['Caio']['id']}", headers=headers).json()
    assert caio["bio"] == "", "Caio (nível 1) não deveria ter bio visível"
    assert caio["hobbies"] == []


def test_own_and_other_player_details(client):
    headers = auth_headers(client)
    create_character(client, headers)

    data = register(client, email="bia@viva.app")
    headers2 = {"Authorization": f"Bearer {data['token']}"}
    create_character(client, headers2, name="Bia", age=22)

    ana = next(
        c
        for c in client.get("/api/characters", headers=headers2).json()["items"]
        if c["name"] == "Ana" and not c["is_npc"]
    )
    detail = client.get(f"/api/characters/{ana['id']}", headers=headers2).json()
    assert detail["is_me"] is False
    assert detail["bio"], "Bio de outro jogador deveria ser visível"
    assert detail["money"] is None
    assert detail["hobbies"] == []

    own = client.get(f"/api/characters/{ana['id']}", headers=headers).json()
    assert own["is_me"] is True
    assert own["money"] is not None
    assert own["hobbies"] == []


def test_advance_clock_and_simulation_log(client):
    headers = auth_headers(client)
    before = client.get("/api/world", headers=headers).json()

    invalid = client.post("/api/simulation/advance", json={"minutes": 0}, headers=headers)
    assert invalid.status_code == 400

    response = client.post("/api/simulation/advance", json={"minutes": 90}, headers=headers)
    assert response.status_code == 200
    after = response.json()
    assert after["date"] != before["date"] or after["time"] != before["time"]

    logs = client.get("/api/simulation/logs", headers=headers).json()["items"]
    assert logs and logs[0]["elapsed_minutes"] == 90

    with _session() as session:
        db_logs = session.exec(select(SimulationLog)).all()
        assert len(db_logs) == len(logs)


def test_simulation_requires_auth(client):
    assert client.post("/api/simulation/advance", json={"minutes": 5}).status_code == 401
    assert client.get("/api/simulation/logs").status_code == 401
