from datetime import datetime, timezone

from app.services.autonomous_world_service import _arc, _score, _social_fit
from app.models import Character, Relationship


def test_autonomous_score_is_deterministic_and_bounded():
    value = _score("viva-test-seed")
    assert 0 <= value <= 1
    assert value == _score("viva-test-seed")


def test_social_arc_prioritizes_romance_then_rivalry():
    assert _arc(Relationship(romance=45, tension=80)) == "romance"
    assert _arc(Relationship(romance=10, tension=50, friendship=20)) == "rivalry"
    assert _arc(Relationship(friendship=60, trust=40)) == "friendship"


def test_social_fit_rewards_shared_interests():
    a = Character(
        name="A",
        hobbies=["música", "cinema"],
        likes=["livros"],
        dislikes=[],
        is_npc=True,
    )
    b = Character(
        name="B",
        hobbies=["cinema"],
        likes=["livros"],
        dislikes=[],
        is_npc=True,
    )
    fit = _social_fit(a, b, Relationship(friendship=20, trust=10))
    assert fit > 0


def test_social_fit_penalizes_tension():
    a = Character(name="A", hobbies=["cinema"], is_npc=True)
    b = Character(name="B", hobbies=["cinema"], is_npc=True)
    calm = _social_fit(a, b, Relationship(friendship=20, tension=0))
    tense = _social_fit(a, b, Relationship(friendship=20, tension=60))
    assert tense < calm
